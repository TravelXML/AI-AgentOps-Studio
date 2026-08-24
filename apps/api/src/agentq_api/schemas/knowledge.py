from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: str = ""


class DocumentResponse(BaseModel):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    name: str
    status: str
    chunk_count: int
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
