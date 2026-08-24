from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from flowspec import FlowSpec, ValidationIssue


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime


class FlowResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str
    status: str
    latest_version: int | None
    created_at: datetime
    updated_at: datetime


class FlowCreateRequest(BaseModel):
    name: str
    description: str = ""
    project_id: uuid.UUID | None = None
    spec: FlowSpec | None = None


class FlowVersionResponse(BaseModel):
    id: uuid.UUID
    flow_id: uuid.UUID
    version: int
    spec: FlowSpec
    created_at: datetime


class SaveFlowVersionRequest(BaseModel):
    spec: FlowSpec


class ValidateFlowResponse(BaseModel):
    valid: bool
    issues: list[ValidationIssue]
