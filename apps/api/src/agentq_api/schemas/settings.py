from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WorkspacePolicyResponse(BaseModel):
    denied_tools: list[str]


class UpdateWorkspacePolicyRequest(BaseModel):
    denied_tools: list[str]


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, Any]
    created_at: datetime
