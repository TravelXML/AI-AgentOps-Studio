from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.deps import get_app_settings, get_current_workspace
from agentq_api.schemas.mcp_servers import McpServerResponse, RegisterMcpServerRequest
from agentq_api.services.mcp_service import McpService
from agentq_api.services.secrets_service import SecretsService

router = APIRouter(prefix="/api/v1", tags=["mcp"])


def _response(server) -> McpServerResponse:
    return McpServerResponse(
        id=server.id,
        name=server.name,
        url=server.url,
        status=server.status,
        last_error=server.last_error,
        tools=server.tools or [],
        has_secret=server.secret_id is not None,
        created_at=server.created_at,
    )


async def _service(session: AsyncSession, settings: Settings) -> McpService:
    secrets = SecretsService(session, settings)
    return McpService(session, secrets)


@router.get("/mcp-servers", response_model=list[McpServerResponse])
async def list_mcp_servers(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[McpServerResponse]:
    service = await _service(session, settings)
    servers = await service.list_servers(workspace.id)
    return [_response(s) for s in servers]


@router.post("/mcp-servers", response_model=McpServerResponse, status_code=201)
async def register_mcp_server(
    payload: RegisterMcpServerRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> McpServerResponse:
    service = await _service(session, settings)
    server = await service.register_and_discover(workspace.id, payload.name, payload.url, payload.api_key)
    return _response(server)


@router.post("/mcp-servers/{server_id}/refresh", response_model=McpServerResponse)
async def refresh_mcp_server(
    server_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> McpServerResponse:
    service = await _service(session, settings)
    server = await service.get_server(workspace.id, server_id)
    await service.refresh_tools(server)
    await session.commit()
    await session.refresh(server)
    return _response(server)
