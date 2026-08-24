from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    inputs: dict[str, Any] = {}


class ResumeRunRequest(BaseModel):
    approved: bool
    note: str | None = None


class RunStepResponse(BaseModel):
    id: uuid.UUID
    node_id: str
    node_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    latency_ms: float | None
    model: str | None
    provider: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    tool_id: str | None
    tool_arguments: dict[str, Any] | None
    tool_result: Any | None
    routing_decision: dict[str, Any] | None
    output_data: Any | None
    error: str | None

    model_config = {"from_attributes": True}


class RunEventResponse(BaseModel):
    id: uuid.UUID
    type: str
    node_id: str | None
    data: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: uuid.UUID
    flow_id: uuid.UUID
    flow_version_id: uuid.UUID
    status: str
    inputs: dict[str, Any]
    output: Any | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    steps: list[RunStepResponse] = []

    model_config = {"from_attributes": True}
