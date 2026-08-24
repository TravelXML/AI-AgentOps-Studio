"""Builds one async LangGraph node function per FlowSpec node. Every node function reads/writes
`WorkflowState` and emits `RunEvent`s via the event sink stashed in `config["configurable"]`.

On failure a node raises `NodeExecutionError` rather than returning an error value - LangGraph
then halts the run immediately instead of letting downstream nodes execute on top of a failed
step (which would be exactly the kind of "fake success" the platform must not produce).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agentq_runtime.expressions import ExpressionError, evaluate_expression, render_template
from agentq_runtime.mcp_client import McpError, McpToolCaller
from agentq_runtime.retrieval import MemoryService, MemoryServiceError, RetrievalError, RetrievalService
from agentq_runtime.routing import Candidate, choose_candidate
from agentq_runtime.state import WorkflowState
from agentq_runtime.tools import ToolExecutionError, ToolRegistry
from flowspec import FlowSpec, Node, NodeType
from model_gateway import ChatMessage, ModelGateway, ModelGatewayError
from security import ToolPolicy, run_checks
from security.policy import PolicyViolation

NodeFn = Callable[[WorkflowState, RunnableConfig], Awaitable[dict[str, Any]]]


class NodeExecutionError(RuntimeError):
    def __init__(self, node_id: str, message: str) -> None:
        self.node_id = node_id
        super().__init__(message)


def _emit(config: RunnableConfig, event_type: str, node_id: str | None, data: dict[str, Any]) -> None:
    sink = config.get("configurable", {}).get("event_sink")
    if sink is not None:
        sink(event_type, node_id, data)


def _fail(config: RunnableConfig, node_id: str, message: str) -> None:
    _emit(config, "node.failed", node_id, {"error": message})
    raise NodeExecutionError(node_id, message)


def _predecessors(flow: FlowSpec, node_id: str) -> list[str]:
    return [e.source for e in flow.edges if e.target == node_id]


def _upstream_value(state: WorkflowState, flow: FlowSpec, node_id: str) -> Any:
    preds = _predecessors(flow, node_id)
    outputs = state.get("node_outputs", {})
    if not preds:
        return state.get("input")
    if len(preds) == 1:
        return outputs.get(preds[0])
    return {p: outputs.get(p) for p in preds}


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value)


def _context(state: WorkflowState) -> dict[str, Any]:
    return {
        "input": state.get("input", {}),
        "variables": state.get("variables", {}),
        "node_outputs": state.get("node_outputs", {}),
    }


def build_input_fn(node: Node) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        _emit(config, "node.started", node.id, {})
        payload = state.get("input", {})
        variables = payload if isinstance(payload, dict) else {"value": payload}
        _emit(config, "node.completed", node.id, {"output": payload})
        return {"node_outputs": {node.id: payload}, "variables": variables}

    return fn


def build_output_fn(node: Node, flow: FlowSpec) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        _emit(config, "node.started", node.id, {})
        source = node.config.source_node or next(iter(_predecessors(flow, node.id)), None)
        value = state.get("node_outputs", {}).get(source) if source else None
        _emit(config, "node.completed", node.id, {"output": value})
        return {"output": value, "node_outputs": {node.id: value}}

    return fn


def build_agent_fn(node: Node, flow: FlowSpec, gateway: ModelGateway) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"model": cfg.model})
        upstream = _upstream_value(state, flow, node.id)
        user_text = _as_text(upstream)
        messages = [
            ChatMessage(role="system", content=cfg.instructions),
            ChatMessage(role="user", content=user_text),
        ]
        _emit(config, "llm.started", node.id, {"model": cfg.model})
        try:
            response = await gateway.complete(
                cfg.model, messages, temperature=cfg.temperature, max_tokens=cfg.max_tokens
            )
        except ModelGatewayError as exc:
            _fail(config, node.id, str(exc))

        _emit(
            config,
            "llm.completed",
            node.id,
            {
                "provider": response.provider,
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
                "latency_ms": response.latency_ms,
            },
        )
        _emit(config, "node.completed", node.id, {"output": response.content})
        return {"node_outputs": {node.id: response.content}}

    return fn


def build_llm_fn(node: Node, flow: FlowSpec, gateway: ModelGateway) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"model": cfg.model})
        upstream_text = _as_text(_upstream_value(state, flow, node.id))
        prompt = render_template(cfg.prompt_template, {**_context(state), "input": upstream_text})
        _emit(config, "llm.started", node.id, {"model": cfg.model})
        try:
            response = await gateway.complete(
                cfg.model,
                [ChatMessage(role="user", content=prompt)],
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
        except ModelGatewayError as exc:
            _fail(config, node.id, str(exc))

        _emit(
            config,
            "llm.completed",
            node.id,
            {
                "provider": response.provider,
                "model": response.model,
                "total_tokens": response.usage.total_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
                "latency_ms": response.latency_ms,
            },
        )
        _emit(config, "node.completed", node.id, {"output": response.content})
        return {"node_outputs": {node.id: response.content}}

    return fn


def build_router_fn(node: Node) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"mode": cfg.mode})
        ctx = _context(state)
        target = None
        reason = ""

        for rule in cfg.rules:
            try:
                if evaluate_expression(rule.when, ctx):
                    target = rule.target
                    reason = f"Matched rule: {rule.when}"
                    break
            except ExpressionError as exc:
                _fail(config, node.id, str(exc))
        if target is None:
            target = cfg.default_target
            reason = "No rule matched; used default target."

        if target is None:
            _fail(config, node.id, f'Router "{node.id}" found no matching route and no default_target.')

        _emit(config, "node.completed", node.id, {"target": target, "reason": reason})
        return {"node_outputs": {node.id: {"target": target, "reason": reason}}}

    return fn


def build_llm_router_fn(node: Node, flow: FlowSpec, gateway: ModelGateway) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"mode": "llm"})
        targets = {r.target for r in cfg.rules} | ({cfg.default_target} if cfg.default_target else set())
        candidates = [
            Candidate(id=t, label=(flow.node_by_id(t).label if flow.node_by_id(t) else t)) for t in targets
        ]
        upstream_text = _as_text(_upstream_value(state, flow, node.id))
        try:
            decision = await choose_candidate(
                gateway=gateway,
                model_id=cfg.model,
                instructions=cfg.llm_instructions or "Choose the best target for this input.",
                input_text=upstream_text,
                candidates=candidates,
                default_target=cfg.default_target,
            )
        except ModelGatewayError as exc:
            _fail(config, node.id, str(exc))

        _emit(config, "node.completed", node.id, {"target": decision.target, "reason": decision.reason})
        return {"node_outputs": {node.id: {"target": decision.target, "reason": decision.reason}}}

    return fn


def build_supervisor_fn(node: Node, flow: FlowSpec, gateway: ModelGateway) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"agents": cfg.agents})
        candidates = []
        for agent_id in cfg.agents:
            agent_node = flow.node_by_id(agent_id)
            label = (agent_node.label or agent_id) if agent_node else agent_id
            description = getattr(agent_node.config, "description", "") if agent_node else ""
            candidates.append(Candidate(id=agent_id, label=label, description=description))

        upstream_text = _as_text(_upstream_value(state, flow, node.id))
        try:
            decision = await choose_candidate(
                gateway=gateway,
                model_id=cfg.model,
                instructions=cfg.routing_instructions,
                input_text=upstream_text,
                candidates=candidates,
                default_target=cfg.fallback_agent,
            )
        except ModelGatewayError as exc:
            _fail(config, node.id, str(exc))

        _emit(
            config,
            "node.completed",
            node.id,
            {"target": decision.target, "reason": decision.reason},
        )
        return {"node_outputs": {node.id: {"target": decision.target, "reason": decision.reason}}}

    return fn


def build_tool_fn(
    node: Node, flow: FlowSpec, tools: ToolRegistry, policy: ToolPolicy | None = None
) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"tool_id": cfg.tool_id})
        if policy is not None:
            try:
                policy.check(cfg.tool_id)
            except PolicyViolation as exc:
                _fail(config, node.id, str(exc))
        ctx = _context(state)
        resolved_args = {
            key: (render_template(value, ctx) if isinstance(value, str) else value)
            for key, value in cfg.arguments.items()
        }
        upstream = _upstream_value(state, flow, node.id)
        if upstream is not None and "input" not in resolved_args:
            resolved_args.setdefault("_upstream", upstream)

        _emit(config, "tool.started", node.id, {"tool_id": cfg.tool_id, "arguments": resolved_args})
        try:
            result = await tools.execute(cfg.tool_id, resolved_args)
        except ToolExecutionError as exc:
            _emit(config, "tool.completed", node.id, {"error": str(exc)})
            _fail(config, node.id, str(exc))

        _emit(config, "tool.completed", node.id, {"result": result})
        _emit(config, "node.completed", node.id, {"output": result})
        return {"node_outputs": {node.id: result}}

    return fn


def build_human_approval_fn(node: Node) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        ctx = _context(state)

        if cfg.condition:
            try:
                should_pause = evaluate_expression(cfg.condition, ctx)
            except ExpressionError as exc:
                _fail(config, node.id, str(exc))
            if not should_pause:
                _emit(config, "node.started", node.id, {})
                _emit(config, "node.completed", node.id, {"approved": True, "skipped": True})
                return {"node_outputs": {node.id: {"approved": True, "skipped": True}}}

        _emit(config, "node.started", node.id, {"message": cfg.message_template})
        decision = interrupt({"node_id": node.id, "message": render_template(cfg.message_template, ctx)})
        approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)

        if not approved:
            _emit(config, "node.failed", node.id, {"reason": "rejected_by_human"})
            raise NodeExecutionError(node.id, "Rejected by human approval")

        _emit(config, "node.completed", node.id, {"approved": True})
        return {"node_outputs": {node.id: {"approved": True, "decision": decision}}}

    return fn


def build_rag_fn(node: Node, flow: FlowSpec, retrieval: RetrievalService) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"knowledge_base_id": cfg.knowledge_base_id})
        query = _as_text(_upstream_value(state, flow, node.id))

        try:
            chunks = await retrieval.retrieve(
                cfg.knowledge_base_id,
                query,
                top_k=cfg.top_k,
                min_score=cfg.min_score,
                embedding_model=cfg.embedding_model,
            )
        except RetrievalError as exc:
            _fail(config, node.id, str(exc))

        if chunks:
            context_block = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
            output = f"Relevant context:\n{context_block}\n\nQuestion: {query}"
        else:
            output = query

        _emit(
            config,
            "node.completed",
            node.id,
            {
                "output": output,
                "retrieved": [
                    {"content": c.content, "score": c.score, "document": c.document_name} for c in chunks
                ],
            },
        )
        return {"node_outputs": {node.id: output}}

    return fn


def build_memory_fn(node: Node, flow: FlowSpec, memory: MemoryService) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"memory_type": cfg.memory_type, "scope": cfg.scope})
        text = _as_text(_upstream_value(state, flow, node.id))
        run_id = config.get("configurable", {}).get("thread_id", "unknown-run")
        key = {"run": f"run:{run_id}", "workspace": "workspace"}.get(cfg.scope, f"agent:{node.id}")

        try:
            if cfg.memory_type == "semantic":
                output = await memory.remember_and_recall_semantic(
                    key, text, embedding_model=None, ttl_seconds=cfg.ttl_seconds
                )
            else:
                output = await memory.remember_and_recall_conversation(
                    key, "user", text, ttl_seconds=cfg.ttl_seconds
                )
        except MemoryServiceError as exc:
            _fail(config, node.id, str(exc))

        _emit(config, "node.completed", node.id, {"output": output})
        return {"node_outputs": {node.id: output}}

    return fn


def build_mcp_fn(
    node: Node, flow: FlowSpec, caller: McpToolCaller, policy: ToolPolicy | None = None
) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"server_id": cfg.server_id, "tool_name": cfg.tool_name})
        if policy is not None:
            try:
                policy.check(cfg.tool_name)
            except PolicyViolation as exc:
                _fail(config, node.id, str(exc))
        ctx = _context(state)
        resolved_args = {
            key: (render_template(value, ctx) if isinstance(value, str) else value)
            for key, value in cfg.arguments.items()
        }
        upstream = _upstream_value(state, flow, node.id)
        if upstream is not None and "input" not in resolved_args:
            resolved_args.setdefault("_upstream", upstream)

        _emit(
            config, "tool.started", node.id, {"tool_id": f"mcp:{cfg.tool_name}", "arguments": resolved_args}
        )
        try:
            result = await caller.call(cfg.server_id, cfg.tool_name, resolved_args)
        except McpError as exc:
            _emit(config, "tool.completed", node.id, {"error": str(exc)})
            _fail(config, node.id, str(exc))

        _emit(config, "tool.completed", node.id, {"result": result})
        _emit(config, "node.completed", node.id, {"output": result})
        return {"node_outputs": {node.id: result}}

    return fn


def build_guardrail_fn(node: Node, flow: FlowSpec) -> NodeFn:
    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config
        _emit(config, "node.started", node.id, {"stage": cfg.stage})
        text = _as_text(_upstream_value(state, flow, node.id))
        checks = [{"type": c.type, "config": c.config} for c in cfg.checks]
        violations = run_checks(text, checks)

        if violations:
            detail = [{"check": v.check_type, "message": v.message} for v in violations]
            if cfg.on_fail == "block":
                _emit(config, "node.failed", node.id, {"violations": detail})
                raise NodeExecutionError(
                    node.id, "Guardrail blocked: " + "; ".join(v.message for v in violations)
                )
            _emit(config, "node.completed", node.id, {"output": text, "warnings": detail})
            return {"node_outputs": {node.id: text}}

        _emit(config, "node.completed", node.id, {"output": text})
        return {"node_outputs": {node.id: text}}

    return fn


def build_passthrough_fn(node: Node, flow: FlowSpec, label: str) -> NodeFn:
    """Used for node types not yet executable in this phase - records that the node ran, is
    honest that it did not perform its real function yet, and passes the upstream value through
    unchanged."""

    async def fn(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        _emit(config, "node.started", node.id, {})
        value = _upstream_value(state, flow, node.id)
        _emit(
            config,
            "node.completed",
            node.id,
            {"output": value, "note": f"{label}: not implemented in this MVP phase"},
        )
        return {"node_outputs": {node.id: value}}

    return fn


def build_node_fn(
    node: Node,
    flow: FlowSpec,
    gateway: ModelGateway,
    tools: ToolRegistry,
    *,
    retrieval: RetrievalService | None = None,
    memory: MemoryService | None = None,
    mcp_caller: McpToolCaller | None = None,
    policy: ToolPolicy | None = None,
) -> NodeFn:
    match node.type:
        case NodeType.INPUT:
            return build_input_fn(node)
        case NodeType.OUTPUT:
            return build_output_fn(node, flow)
        case NodeType.AGENT:
            return build_agent_fn(node, flow, gateway)
        case NodeType.ROUTER:
            return (
                build_llm_router_fn(node, flow, gateway)
                if node.config.mode == "llm"
                else build_router_fn(node)
            )
        case NodeType.SUPERVISOR:
            return build_supervisor_fn(node, flow, gateway)
        case NodeType.TOOL:
            return build_tool_fn(node, flow, tools, policy)
        case NodeType.HUMAN_APPROVAL:
            return build_human_approval_fn(node)
        case NodeType.LLM:
            return build_llm_fn(node, flow, gateway)
        case NodeType.RAG if retrieval is not None:
            return build_rag_fn(node, flow, retrieval)
        case NodeType.MEMORY if memory is not None:
            return build_memory_fn(node, flow, memory)
        case NodeType.MCP if mcp_caller is not None:
            return build_mcp_fn(node, flow, mcp_caller, policy)
        case NodeType.GUARDRAIL:
            return build_guardrail_fn(node, flow)
        case _:
            return build_passthrough_fn(node, flow, node.type.value)
