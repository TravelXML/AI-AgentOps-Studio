from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from model_gateway import Provider


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    model_key: str
    provider: Provider
    model: str
    base_url: str | None
    has_secret: bool
    temperature_default: float
    timeout_seconds: float
    max_retries: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateModelConfigRequest(BaseModel):
    model_key: str
    provider: Provider
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature_default: float = 0.2
    timeout_seconds: float = 60.0
    max_retries: int = 2
