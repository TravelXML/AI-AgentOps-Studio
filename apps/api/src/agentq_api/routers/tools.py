from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agentq_api.deps import get_tool_registry
from agentq_runtime.tools import ToolRegistry

router = APIRouter(prefix="/api/v1", tags=["tools"])


class ToolResponse(BaseModel):
    id: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    permissions: list[str]


@router.get("/tools", response_model=list[ToolResponse])
async def list_tools(registry: ToolRegistry = Depends(get_tool_registry)) -> list[ToolResponse]:
    return [
        ToolResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            input_schema=t.input_schema,
            output_schema=t.output_schema,
            permissions=t.permissions,
        )
        for t in registry.list()
    ]
