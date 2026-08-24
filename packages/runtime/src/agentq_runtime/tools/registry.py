"""Tool Registry (spec section 17). Agents and Tool nodes never call external systems directly -
every call goes through a registered `ToolDefinition.handler`, so permissions/guardrails/audit can
sit in front of it uniformly."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


class ToolExecutionError(RuntimeError):
    pass


@dataclass
class ToolDefinition:
    id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: list[str]
    handler: Callable[[dict[str, Any]], Awaitable[Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute(self, tool_id: str, arguments: dict[str, Any]) -> Any:
        tool = self.get(tool_id)
        if tool is None:
            raise ToolExecutionError(f"Tool '{tool_id}' is not registered.")
        try:
            return await tool.handler(arguments)
        except ToolExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize every tool failure
            raise ToolExecutionError(f"Tool '{tool_id}' failed: {exc}") from exc
