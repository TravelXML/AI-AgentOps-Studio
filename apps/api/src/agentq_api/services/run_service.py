"""Execution orchestration: compiles a FlowSpec, drives it through LangGraphRuntime, persists the
Agent Flight Recorder data (Run/RunStep/RunEvent - spec section 28), and formats each event as an
SSE frame. This is the one place LangGraph and the database meet."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.models import Flow, FlowVersion, Run, RunEvent, RunStep, Workspace
from agentq_api.schemas.errors import ApiError
from agentq_api.services.audit_service import record_audit_log
from agentq_api.services.knowledge_service import PgVectorRetrievalService
from agentq_api.services.mcp_service import WorkspaceMcpToolCaller
from agentq_api.services.memory_service import PgVectorMemoryService
from agentq_api.services.model_gateway_factory import build_model_gateway
from agentq_api.services.secrets_service import SecretsService
from agentq_runtime import FlowCompiler, LangGraphRuntime, ToolRegistry
from agentq_runtime import RunEvent as EngineEvent
from flowspec import FlowSpec
from model_gateway import ModelGateway
from observability import metrics
from security import ToolPolicy


def _sse(event: EngineEvent) -> bytes:
    return f"data: {event.model_dump_json()}\n\n".encode()


async def build_run_execution_service(
    session: AsyncSession, workspace: Workspace, checkpointer, tools: ToolRegistry, settings: Settings
) -> RunExecutionService:
    """Wires the full execution path - model gateway, tools, the RAG/Memory/MCP services, and the
    workspace's tool policy - the same way for every caller that needs to run a flow to completion
    (the canvas Run button and the Evaluation runner both go through this)."""
    secrets = SecretsService(session, settings)
    gateway = await build_model_gateway(session, workspace.id, secrets)
    retrieval = PgVectorRetrievalService(gateway)
    memory = PgVectorMemoryService(workspace.id, gateway)
    mcp_caller = WorkspaceMcpToolCaller(workspace.id, settings)
    policy = ToolPolicy(denied_tools=set(workspace.denied_tools or []))
    return RunExecutionService(
        session,
        workspace.id,
        checkpointer,
        tools,
        gateway,
        retrieval=retrieval,
        memory=memory,
        mcp_caller=mcp_caller,
        policy=policy,
    )


class RunExecutionService:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        checkpointer: BaseCheckpointSaver,
        tools: ToolRegistry,
        gateway: ModelGateway,
        *,
        retrieval=None,
        memory=None,
        mcp_caller=None,
        policy: ToolPolicy | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._checkpointer = checkpointer
        self._runtime = LangGraphRuntime(
            FlowCompiler(
                gateway, tools, retrieval=retrieval, memory=memory, mcp_caller=mcp_caller, policy=policy
            )
        )

    async def create_run(
        self,
        flow: Flow,
        flow_version: FlowVersion,
        inputs: dict[str, Any],
        *,
        replayed_from_run_id: uuid.UUID | None = None,
    ) -> Run:
        run = Run(
            workspace_id=self._workspace_id,
            flow_id=flow.id,
            flow_version_id=flow_version.id,
            status="CREATED",
            inputs=inputs,
            replayed_from_run_id=replayed_from_run_id,
        )
        self._session.add(run)
        await self._session.flush()
        await record_audit_log(self._session, self._workspace_id, "run.created", "run", str(run.id))
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def get_run(self, run_id: uuid.UUID) -> Run:
        result = await self._session.execute(
            select(Run).where(Run.id == run_id, Run.workspace_id == self._workspace_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise ApiError(404, "RUN_NOT_FOUND", f"Run '{run_id}' was not found.")
        return run

    async def list_runs(self, *, flow_id: uuid.UUID | None = None, limit: int = 50) -> list[Run]:
        query = select(Run).where(Run.workspace_id == self._workspace_id)
        if flow_id is not None:
            query = query.where(Run.flow_id == flow_id)
        query = query.order_by(Run.created_at.desc()).limit(min(limit, 200))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_events(self, run_id: uuid.UUID) -> list[RunEvent]:
        result = await self._session.execute(
            select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.created_at)
        )
        return list(result.scalars().all())

    async def _get_or_create_step(self, run_id: uuid.UUID, node_id: str, node_type: str) -> RunStep:
        result = await self._session.execute(
            select(RunStep).where(RunStep.run_id == run_id, RunStep.node_id == node_id)
        )
        step = result.scalar_one_or_none()
        if step is None:
            step = RunStep(run_id=run_id, node_id=node_id, node_type=node_type, status="RUNNING")
            self._session.add(step)
            await self._session.flush()
        else:
            step.status = "RUNNING"
        return step

    async def _persist_event(self, run: Run, event: EngineEvent, node_type_by_id: dict[str, str]) -> None:
        row = RunEvent(run_id=run.id, type=event.type, node_id=event.node_id, data=event.data)
        self._session.add(row)

        if event.node_id:
            if event.type == "node.started":
                step = await self._get_or_create_step(
                    run.id, event.node_id, node_type_by_id.get(event.node_id, "unknown")
                )
            else:
                result = await self._session.execute(
                    select(RunStep).where(RunStep.run_id == run.id, RunStep.node_id == event.node_id)
                )
                step = result.scalar_one_or_none()

            if step is not None:
                row.step_id = step.id
                if event.type == "llm.completed":
                    step.model = event.data.get("model")
                    step.provider = event.data.get("provider")
                    step.input_tokens = event.data.get("prompt_tokens", step.input_tokens)
                    step.output_tokens = event.data.get("completion_tokens", step.output_tokens)
                    step.total_tokens = event.data.get("total_tokens", step.total_tokens)
                    step.estimated_cost_usd = event.data.get("estimated_cost_usd", step.estimated_cost_usd)
                    step.latency_ms = event.data.get("latency_ms", step.latency_ms)

                    provider = step.provider or "unknown"
                    model = step.model or "unknown"
                    metrics.llm_requests_total.labels(provider=provider, model=model).inc()
                    if "prompt_tokens" in event.data:
                        metrics.llm_tokens_total.labels(provider=provider, model=model, kind="prompt").inc(
                            event.data["prompt_tokens"]
                        )
                    if "completion_tokens" in event.data:
                        metrics.llm_tokens_total.labels(
                            provider=provider, model=model, kind="completion"
                        ).inc(event.data["completion_tokens"])
                    if "estimated_cost_usd" in event.data:
                        metrics.llm_api_cost_total.labels(provider=provider, model=model).inc(
                            event.data["estimated_cost_usd"]
                        )
                    if node_type_by_id.get(event.node_id) == "agent" and "latency_ms" in event.data:
                        metrics.agent_node_duration_seconds.labels(node_id=event.node_id).observe(
                            event.data["latency_ms"] / 1000
                        )
                elif event.type == "tool.started":
                    step.tool_id = event.data.get("tool_id")
                    step.tool_arguments = event.data.get("arguments")
                    metrics.tool_calls_total.labels(tool_id=step.tool_id or "unknown").inc()
                elif event.type == "tool.completed":
                    if "result" in event.data:
                        step.tool_result = event.data["result"]
                    if "error" in event.data:
                        metrics.tool_failures_total.labels(tool_id=step.tool_id or "unknown").inc()
                elif event.type == "node.completed":
                    step.status = "SUCCEEDED"
                    step.completed_at = datetime.now(UTC)
                    step.output_data = event.data.get("output")
                    if "target" in event.data:
                        step.routing_decision = {
                            "target": event.data.get("target"),
                            "reason": event.data.get("reason"),
                        }
                elif event.type == "node.failed":
                    step.status = "FAILED"
                    step.completed_at = datetime.now(UTC)
                    step.error = event.data.get("error")

        await self._session.commit()

    async def _finalize_run(self, run: Run, compiled) -> None:
        status = await self._runtime.get_status(compiled, str(run.id))
        run.status = status
        config = {"configurable": {"thread_id": str(run.id)}}

        if status == "SUCCEEDED":
            run.completed_at = datetime.now(UTC)
            snapshot = await compiled.graph.aget_state(config)
            run.output = snapshot.values.get("output")
        elif status == "FAILED":
            run.completed_at = datetime.now(UTC)
            snapshot = await compiled.graph.aget_state(config)
            errors = [t.error for t in snapshot.tasks if t.error]
            run.error = "; ".join(errors) if errors else "Run failed."

        if status in ("SUCCEEDED", "FAILED") and run.started_at is not None and run.completed_at is not None:
            metrics.workflow_runs_total.labels(status=status).inc()
            duration = (run.completed_at - run.started_at).total_seconds()
            metrics.workflow_run_duration_seconds.observe(duration)
            if status == "FAILED":
                metrics.workflow_failures_total.inc()

        await self._session.commit()

    async def _stream(self, run: Run, spec: FlowSpec, event_iter) -> AsyncIterator[bytes]:
        node_type_by_id = {n.id: n.type.value for n in spec.nodes}
        compiled = await self._runtime.compile(spec, checkpointer=self._checkpointer)
        async for event in event_iter(compiled):
            await self._persist_event(run, event, node_type_by_id)
            yield _sse(event)
        await self._finalize_run(run, compiled)

    async def stream_execution(self, run: Run, flow_version: FlowVersion) -> AsyncIterator[bytes]:
        spec = FlowSpec.model_validate(flow_version.spec)
        run.status = "RUNNING"
        run.started_at = datetime.now(UTC)
        await self._session.commit()

        async def event_iter(compiled):
            async for e in self._runtime.execute(compiled, str(run.id), run.inputs):
                yield e

        async for chunk in self._stream(run, spec, event_iter):
            yield chunk

    async def stream_resume(
        self, run: Run, flow_version: FlowVersion, resume_value: dict[str, Any]
    ) -> AsyncIterator[bytes]:
        if run.status != "WAITING_FOR_HUMAN":
            raise ApiError(409, "RUN_NOT_WAITING", f"Run '{run.id}' is not waiting for approval.")
        spec = FlowSpec.model_validate(flow_version.spec)
        run.status = "RUNNING"
        await self._session.commit()

        async def event_iter(compiled):
            async for e in self._runtime.resume(compiled, str(run.id), resume_value):
                yield e

        async for chunk in self._stream(run, spec, event_iter):
            yield chunk
