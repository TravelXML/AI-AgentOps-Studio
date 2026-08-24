from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.deps import (
    get_app_settings,
    get_checkpointer,
    get_current_workspace,
    get_tool_registry,
)
from agentq_api.schemas.errors import ApiError
from agentq_api.schemas.runs import (
    CreateRunRequest,
    ResumeRunRequest,
    RunEventResponse,
    RunResponse,
)
from agentq_api.services.audit_service import record_audit_log
from agentq_api.services.flow_service import FlowService
from agentq_api.services.run_service import RunExecutionService, build_run_execution_service
from agentq_runtime.tools import ToolRegistry

router = APIRouter(prefix="/api/v1", tags=["runs"])


async def _build_run_service(
    session: AsyncSession, workspace: Workspace, checkpointer, tools: ToolRegistry, settings: Settings
) -> RunExecutionService:
    return await build_run_execution_service(session, workspace, checkpointer, tools, settings)


@router.post("/flows/{flow_id}/runs")
async def create_and_stream_run(
    flow_id: uuid.UUID,
    payload: CreateRunRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    flow_service = FlowService(session)
    flow = await flow_service.get_flow(workspace.id, flow_id)
    flow_version = await flow_service.get_latest_version(flow)

    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    run = await run_service.create_run(flow, flow_version, payload.inputs)

    return StreamingResponse(
        run_service.stream_execution(run, flow_version),
        media_type="text/event-stream",
        headers={"X-Run-Id": str(run.id), "Cache-Control": "no-cache"},
    )


@router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    flow_id: uuid.UUID | None = None,
    limit: int = 50,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> list[RunResponse]:
    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    runs = await run_service.list_runs(flow_id=flow_id, limit=limit)
    return [RunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> RunResponse:
    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    run = await run_service.get_run(run_id)
    return RunResponse.model_validate(run)


@router.get("/runs/{run_id}/events", response_model=list[RunEventResponse])
async def get_run_events(
    run_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> list[RunEventResponse]:
    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    await run_service.get_run(run_id)  # 404s if missing/unowned
    events = await run_service.list_events(run_id)
    return [RunEventResponse.model_validate(e) for e in events]


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: uuid.UUID,
    payload: ResumeRunRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    run = await run_service.get_run(run_id)
    if run.status != "WAITING_FOR_HUMAN":
        raise ApiError(409, "RUN_NOT_WAITING", f"Run '{run_id}' is not waiting for approval.")
    flow_service = FlowService(session)
    flow_version = await flow_service.get_version_by_id(run.flow_version_id)
    await record_audit_log(
        session,
        workspace.id,
        "human_approval.approved" if payload.approved else "human_approval.rejected",
        "run",
        str(run.id),
        metadata={"note": payload.note} if payload.note else None,
    )
    await session.commit()

    return StreamingResponse(
        run_service.stream_resume(run, flow_version, payload.model_dump()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/runs/{run_id}/replay")
async def replay_run(
    run_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    run_service = await _build_run_service(session, workspace, checkpointer, tools, settings)
    original = await run_service.get_run(run_id)

    flow_service = FlowService(session)
    flow = await flow_service.get_flow(workspace.id, original.flow_id)
    flow_version = await flow_service.get_version_by_id(original.flow_version_id)

    new_run = await run_service.create_run(
        flow, flow_version, original.inputs, replayed_from_run_id=original.id
    )

    return StreamingResponse(
        run_service.stream_execution(new_run, flow_version),
        media_type="text/event-stream",
        headers={"X-Run-Id": str(new_run.id), "Cache-Control": "no-cache"},
    )
