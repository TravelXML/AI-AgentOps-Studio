from __future__ import annotations

from pydantic import BaseModel

from flowspec import FlowSpec


class GenerateFlowRequest(BaseModel):
    description: str
    model: str = "default"


class GenerateFlowResponse(BaseModel):
    spec: FlowSpec
    attempts: int
