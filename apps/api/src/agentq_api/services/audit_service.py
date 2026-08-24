"""Audit log (Phase 6): a plain, queryable record of who did what to which resource. Recording is
best-effort by design - writing the audit row shares the caller's transaction (so it commits or
rolls back atomically with the action it describes) but never gates the action on the log write
succeeding independently.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.models import AuditLog

SYSTEM_ACTOR = "dev@agentq.local"


async def record_audit_log(
    session: AsyncSession,
    workspace_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    *,
    actor: str = SYSTEM_ACTOR,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            audit_metadata=metadata or {},
        )
    )
    await session.flush()
