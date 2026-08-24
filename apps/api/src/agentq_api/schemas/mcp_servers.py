from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class McpServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    status: str
    last_error: str | None
    tools: list[dict[str, Any]]
    has_secret: bool
    created_at: datetime


class RegisterMcpServerRequest(BaseModel):
    name: str
    url: str
    api_key: str | None = None
