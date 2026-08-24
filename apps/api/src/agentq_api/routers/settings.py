from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.base import get_db_session
from agentq_api.db.models import AuditLog, Workspace
from agentq_api.deps import get_current_workspace
from agentq_api.schemas.settings import (
    AuditLogEntryResponse,
    UpdateWorkspacePolicyRequest,
    WorkspacePolicyResponse,
)

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings/policy", response_model=WorkspacePolicyResponse)
async def get_policy(workspace: Workspace = Depends(get_current_workspace)) -> WorkspacePolicyResponse:
    return WorkspacePolicyResponse(denied_tools=workspace.denied_tools or [])


@router.put("/settings/policy", response_model=WorkspacePolicyResponse)
async def update_policy(
    payload: UpdateWorkspacePolicyRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspacePolicyResponse:
    workspace.denied_tools = payload.denied_tools
    await session.commit()
    return WorkspacePolicyResponse(denied_tools=workspace.denied_tools)


@router.get("/settings/audit-log", response_model=list[AuditLogEntryResponse])
async def list_audit_log(
    limit: int = 100,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditLogEntryResponse]:
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace.id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
    )
    return [
        AuditLogEntryResponse(
            id=row.id,
            actor=row.actor,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            metadata=row.audit_metadata,
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]
