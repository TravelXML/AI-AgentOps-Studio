"""MCP server registry (Phase 4): register a server by URL, discover its tools via a real
JSON-RPC handshake (`agentq_runtime.McpClient`), and call tools from an MCP node at run time.
`WorkspaceMcpToolCaller` is the concrete implementation of `agentq_runtime.McpToolCaller`.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_session_factory
from agentq_api.db.models import McpServer
from agentq_api.schemas.errors import ApiError
from agentq_api.services.audit_service import record_audit_log
from agentq_api.services.secrets_service import SecretsService
from agentq_runtime import McpClient, McpError


class McpService:
    def __init__(self, session: AsyncSession, secrets: SecretsService) -> None:
        self._session = session
        self._secrets = secrets

    async def list_servers(self, workspace_id: uuid.UUID) -> list[McpServer]:
        result = await self._session.execute(
            select(McpServer)
            .where(McpServer.workspace_id == workspace_id)
            .order_by(McpServer.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_server(self, workspace_id: uuid.UUID, server_id: uuid.UUID) -> McpServer:
        result = await self._session.execute(
            select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == workspace_id)
        )
        server = result.scalar_one_or_none()
        if server is None:
            raise ApiError(404, "MCP_SERVER_NOT_FOUND", f"MCP server '{server_id}' was not found.")
        return server

    async def _token_for(self, server: McpServer) -> str | None:
        if server.secret_id is None:
            return None
        return await self._secrets.resolve(server.secret_id)

    async def register_and_discover(
        self, workspace_id: uuid.UUID, name: str, url: str, api_key: str | None
    ) -> McpServer:
        secret_id = None
        if api_key:
            secret = await self._secrets.create(workspace_id, f"mcp-{name}-token", api_key)
            secret_id = secret.id

        server = McpServer(workspace_id=workspace_id, name=name, url=url, secret_id=secret_id)
        self._session.add(server)
        await self._session.flush()

        await self.refresh_tools(server)
        await record_audit_log(
            self._session, workspace_id, "mcp_server.registered", "mcp_server", str(server.id)
        )
        await self._session.commit()
        await self._session.refresh(server)
        return server

    async def refresh_tools(self, server: McpServer) -> McpServer:
        token = await self._token_for(server)
        client = McpClient(server.url, bearer_token=token)
        try:
            await client.initialize()
            tools = await client.list_tools()
        except McpError as exc:
            server.status = "error"
            server.last_error = str(exc)
            return server

        server.status = "connected"
        server.last_error = None
        server.tools = tools
        return server


class WorkspaceMcpToolCaller:
    """Resolves a workspace-registered MCP server id to its URL/credential and calls a tool on
    it - the runtime layer (`build_mcp_fn`) only ever sees the opaque `server_id`.

    Runs during flow execution, inside LangGraph's background task (`langgraph_runtime.py` drives
    the graph via `asyncio.create_task` while the request's own session is concurrently used to
    persist events) - reusing the request-scoped `AsyncSession` here races with that and raises
    "concurrent operations are not permitted". Opens its own short-lived session per call instead.
    """

    def __init__(self, workspace_id: uuid.UUID, settings: Settings) -> None:
        self._workspace_id = workspace_id
        self._settings = settings

    async def call(self, server_id: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        try:
            server_uuid = uuid.UUID(server_id)
        except ValueError as exc:
            raise McpError(f"'{server_id}' is not a valid MCP server id.") from exc

        async with get_session_factory()() as session:
            result = await session.execute(
                select(McpServer).where(
                    McpServer.id == server_uuid, McpServer.workspace_id == self._workspace_id
                )
            )
            server = result.scalar_one_or_none()
            if server is None:
                raise McpError(f"MCP server '{server_id}' is not registered in this workspace.")

            token = None
            if server.secret_id is not None:
                token = await SecretsService(session, self._settings).resolve(server.secret_id)
            url = server.url

        client = McpClient(url, bearer_token=token)
        await client.initialize()
        return await client.call_tool(tool_name, arguments)
