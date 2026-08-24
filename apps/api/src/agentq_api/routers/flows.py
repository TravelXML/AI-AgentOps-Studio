from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.base import get_db_session
from agentq_api.db.models import Project, Workspace
from agentq_api.deps import get_current_workspace
from agentq_api.schemas.flows import (
    FlowCreateRequest,
    FlowResponse,
    FlowVersionResponse,
    ProjectResponse,
    SaveFlowVersionRequest,
    ValidateFlowResponse,
)
from agentq_api.services.bootstrap import get_default_project_id
from agentq_api.services.flow_service import FlowService

router = APIRouter(prefix="/api/v1", tags=["flows"])


def _flow_version_response(version) -> FlowVersionResponse:
    return FlowVersionResponse(
        id=version.id,
        flow_id=version.flow_id,
        version=version.version,
        spec=version.spec,
        created_at=version.created_at,
    )


def _flow_response(flow) -> FlowResponse:
    latest_version = None
    if flow.versions:
        latest_version = max(v.version for v in flow.versions)
    return FlowResponse(
        id=flow.id,
        project_id=flow.project_id,
        name=flow.name,
        description=flow.description,
        status=flow.status,
        latest_version=latest_version,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[Project]:
    result = await session.execute(select(Project).where(Project.workspace_id == workspace.id))
    return list(result.scalars().all())


@router.get("/flows", response_model=list[FlowResponse])
async def list_flows(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[FlowResponse]:
    service = FlowService(session)
    flows = await service.list_flows(workspace.id)
    return [_flow_response(f) for f in flows]


@router.post("/flows", response_model=FlowResponse, status_code=201)
async def create_flow(
    payload: FlowCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> FlowResponse:
    project_id = payload.project_id or await get_default_project_id(session, workspace.id)
    service = FlowService(session)
    flow = await service.create_flow(
        workspace.id, project_id, payload.name, payload.description, payload.spec
    )
    return _flow_response(flow)


@router.get("/flows/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> FlowResponse:
    service = FlowService(session)
    flow = await service.get_flow(workspace.id, flow_id)
    return _flow_response(flow)


@router.get("/flows/{flow_id}/versions/latest", response_model=FlowVersionResponse)
async def get_latest_flow_version(
    flow_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> FlowVersionResponse:
    service = FlowService(session)
    flow = await service.get_flow(workspace.id, flow_id)
    version = await service.get_latest_version(flow)
    return _flow_version_response(version)


@router.post("/flows/{flow_id}/versions", response_model=FlowVersionResponse, status_code=201)
async def save_flow_version(
    flow_id: uuid.UUID,
    payload: SaveFlowVersionRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> FlowVersionResponse:
    service = FlowService(session)
    flow = await service.get_flow(workspace.id, flow_id)
    version = await service.save_version(flow, payload.spec)
    await session.commit()
    return _flow_version_response(version)


@router.post("/flows/{flow_id}/validate", response_model=ValidateFlowResponse)
async def validate_flow(
    flow_id: uuid.UUID,
    payload: SaveFlowVersionRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> ValidateFlowResponse:
    service = FlowService(session)
    await service.get_flow(workspace.id, flow_id)  # 404s if not found/owned
    result = service.validate(payload.spec)
    return ValidateFlowResponse(valid=result.valid, issues=result.issues)


@router.post("/flows/{flow_id}/publish", response_model=FlowResponse)
async def publish_flow(
    flow_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> FlowResponse:
    service = FlowService(session)
    flow = await service.get_flow(workspace.id, flow_id)
    flow = await service.publish(flow)
    return _flow_response(flow)
