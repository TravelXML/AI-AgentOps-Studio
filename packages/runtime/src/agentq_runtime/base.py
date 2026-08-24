"""WorkflowRuntime abstraction (spec section 6). `LangGraphRuntime` is the only implementation for
MVP; the interface exists so CrewAI/AutoGen/custom-Python adapters can be added later without the
API layer or FlowSpec ever changing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from agentq_runtime.compiler import CompiledWorkflow
from agentq_runtime.events import RunEvent
from flowspec import FlowSpec


class WorkflowRuntime(ABC):
    @abstractmethod
    async def compile(self, flow: FlowSpec) -> CompiledWorkflow: ...

    @abstractmethod
    def execute(
        self, compiled: CompiledWorkflow, run_id: str, inputs: dict[str, Any]
    ) -> AsyncIterator[RunEvent]: ...

    @abstractmethod
    def resume(
        self, compiled: CompiledWorkflow, run_id: str, resume_value: Any
    ) -> AsyncIterator[RunEvent]: ...

    @abstractmethod
    async def get_status(self, compiled: CompiledWorkflow, run_id: str) -> str: ...
