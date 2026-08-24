"""LangGraphRuntime: the MVP `WorkflowRuntime` implementation. Drives a compiled graph in a
background task and forwards node-emitted events plus synthesized run-level events (run.started,
run.waiting, run.completed, run.failed) through an async generator, so the API layer can persist
each event and fan it out over SSE without knowing anything about LangGraph itself.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from agentq_runtime.base import WorkflowRuntime
from agentq_runtime.compiler import CompiledWorkflow, FlowCompiler
from agentq_runtime.events import RunEvent
from flowspec import FlowSpec

_SENTINEL = object()


class LangGraphRuntime(WorkflowRuntime):
    def __init__(self, compiler: FlowCompiler) -> None:
        self._compiler = compiler

    async def compile(
        self, flow: FlowSpec, *, checkpointer: BaseCheckpointSaver | None = None
    ) -> CompiledWorkflow:
        return self._compiler.compile(flow, checkpointer=checkpointer)

    def _thread_config(self, run_id: str, queue: asyncio.Queue) -> dict[str, Any]:
        def sink(event_type: str, node_id: str | None, data: dict[str, Any]) -> None:
            queue.put_nowait((event_type, node_id, data))

        return {"configurable": {"thread_id": run_id, "event_sink": sink}}

    async def _drive(
        self, compiled: CompiledWorkflow, run_id: str, graph_input: Any, queue: asyncio.Queue
    ) -> Exception | None:
        error: Exception | None = None
        try:
            async for chunk in compiled.graph.astream(
                graph_input, config=self._thread_config(run_id, queue), stream_mode="updates"
            ):
                if "__interrupt__" in chunk:
                    for intr in chunk["__interrupt__"]:
                        payload = intr.value if isinstance(intr.value, dict) else {"payload": intr.value}
                        queue.put_nowait(("run.waiting", payload.get("node_id"), payload))
        except Exception as exc:  # noqa: BLE001 - surfaced as run.failed below
            error = exc
        finally:
            queue.put_nowait(_SENTINEL)
        return error

    async def _stream(
        self, compiled: CompiledWorkflow, run_id: str, graph_input: Any
    ) -> AsyncIterator[RunEvent]:
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(self._drive(compiled, run_id, graph_input, queue))
        saw_waiting = False

        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            event_type, node_id, data = item
            if event_type == "run.waiting":
                saw_waiting = True
            yield RunEvent(type=event_type, run_id=run_id, node_id=node_id, data=data)

        error = await task
        status = await self.get_status(compiled, run_id)

        if status == "FAILED":
            error_message = str(error) if error else "Unknown error"
            yield RunEvent(type="run.failed", run_id=run_id, data={"error": error_message})
        elif status == "WAITING_FOR_HUMAN":
            if not saw_waiting:
                yield RunEvent(type="run.waiting", run_id=run_id, data={})
        else:
            yield RunEvent(type="run.completed", run_id=run_id, data={})

    async def execute(
        self, compiled: CompiledWorkflow, run_id: str, inputs: dict[str, Any]
    ) -> AsyncIterator[RunEvent]:
        yield RunEvent(type="run.started", run_id=run_id, data={"inputs": inputs})
        graph_input = {"input": inputs, "variables": {}, "node_outputs": {}}
        async for event in self._stream(compiled, run_id, graph_input):
            yield event

    async def resume(
        self, compiled: CompiledWorkflow, run_id: str, resume_value: Any
    ) -> AsyncIterator[RunEvent]:
        async for event in self._stream(compiled, run_id, Command(resume=resume_value)):
            yield event

    async def get_status(self, compiled: CompiledWorkflow, run_id: str) -> str:
        config = {"configurable": {"thread_id": run_id}}
        snapshot = await compiled.graph.aget_state(config)
        if any(t.error for t in snapshot.tasks):
            return "FAILED"
        if snapshot.next:
            return "WAITING_FOR_HUMAN"
        return "SUCCEEDED"
