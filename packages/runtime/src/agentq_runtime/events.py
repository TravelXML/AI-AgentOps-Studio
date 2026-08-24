"""Typed run event schema (spec section 31). One event type per stream message so the frontend
never has to guess at shape."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RunEventType = Literal[
    "run.started",
    "node.started",
    "llm.started",
    "llm.token",
    "llm.completed",
    "tool.started",
    "tool.completed",
    "node.completed",
    "node.failed",
    "run.waiting",
    "run.completed",
    "run.failed",
]


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: RunEventType
    run_id: str
    node_id: str | None = None
    step_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
