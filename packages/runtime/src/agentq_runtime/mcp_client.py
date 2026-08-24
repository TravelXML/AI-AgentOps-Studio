"""A minimal MCP (Model Context Protocol, https://modelcontextprotocol.io) client.

Implements the protocol's JSON-RPC 2.0 wire format directly rather than depending on an SDK,
since the wire format is the stable, versioned contract - `initialize` -> `notifications/initialized`
-> `tools/list` / `tools/call`, with an `Mcp-Session-Id` response header echoed back on every
subsequent request once the server issues one (Streamable HTTP transport, spec revision
2024-11-05). This supports the common case of a server that answers each request with a single
JSON object; a server that upgrades to an SSE stream mid-response is not supported in this phase.
"""

from __future__ import annotations

import itertools
from typing import Any, Protocol

import httpx

MCP_PROTOCOL_VERSION = "2024-11-05"
_ACCEPT_HEADER = "application/json, text/event-stream"


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, base_url: str, *, bearer_token: str | None = None, timeout: float = 15.0) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._session_id: str | None = None
        self._id_counter = itertools.count(1)
        self._headers = {"Content-Type": "application/json", "Accept": _ACCEPT_HEADER}
        if bearer_token:
            self._headers["Authorization"] = f"Bearer {bearer_token}"

    def _headers_for_request(self) -> dict[str, str]:
        headers = dict(self._headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    self._base_url, json=payload, headers=self._headers_for_request()
                )
            except httpx.HTTPError as exc:
                raise McpError(f"could not reach MCP server: {exc}") from exc
        if response.status_code >= 400:
            raise McpError(f"MCP server returned HTTP {response.status_code}: {response.text[:300]}")
        if "Mcp-Session-Id" in response.headers:
            self._session_id = response.headers["Mcp-Session-Id"]
        return response

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {"jsonrpc": "2.0", "id": next(self._id_counter), "method": method, "params": params or {}}
        response = await self._post(payload)
        try:
            body = response.json()
        except ValueError as exc:
            raise McpError(f"MCP server returned a non-JSON response: {exc}") from exc
        if "error" in body:
            message = body["error"].get("message", "MCP server returned an error")
            raise McpError(message)
        return body.get("result")

    async def _notify(self, method: str) -> None:
        await self._post({"jsonrpc": "2.0", "method": method})

    async def initialize(self) -> dict[str, Any]:
        result = await self._rpc(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agentq", "version": "0.1.0"},
            },
        )
        await self._notify("notifications/initialized")
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._rpc("tools/list")
        return result.get("tools", []) if result else []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        if result and result.get("isError"):
            content = result.get("content") or []
            message = (
                content[0].get("text") if content and isinstance(content[0], dict) else "tool call failed"
            )
            raise McpError(str(message))
        return result.get("content") if result else None


class McpToolCaller(Protocol):
    """Resolves a registered MCP server (by the id the workspace assigned it, not the raw URL)
    and calls a tool on it - the runtime never sees server URLs/credentials directly."""

    async def call(self, server_id: str, tool_name: str, arguments: dict[str, Any]) -> Any: ...
