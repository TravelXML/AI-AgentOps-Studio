"""FlowSpec -> LangGraph compiler (spec section 26).

    FlowSpec -> Validation -> Normalization -> Graph analysis -> LangGraph compilation

Graph definition is kept separate from runtime execution: `FlowCompiler.compile()` returns a
`CompiledStateGraph` plus the FlowSpec it was built from; `LangGraphRuntime` (langgraph_runtime.py)
is what actually drives execution/streaming/resume against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agentq_runtime.mcp_client import McpToolCaller
from agentq_runtime.nodes import build_node_fn
from agentq_runtime.retrieval import MemoryService, RetrievalService
from agentq_runtime.state import WorkflowState
from agentq_runtime.tools import ToolRegistry
from flowspec import FlowSpec, NodeType, ValidationResult, validate_flowspec
from model_gateway import ModelGateway
from security import ToolPolicy


class CompilationError(RuntimeError):
    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        messages = "; ".join(i.message for i in result.errors)
        super().__init__(f"FlowSpec failed validation: {messages}")


@dataclass
class CompiledWorkflow:
    flow: FlowSpec
    graph: Any  # CompiledStateGraph[WorkflowState]
    input_node_id: str


class FlowCompiler:
    def __init__(
        self,
        gateway: ModelGateway,
        tools: ToolRegistry,
        *,
        retrieval: RetrievalService | None = None,
        memory: MemoryService | None = None,
        mcp_caller: McpToolCaller | None = None,
        policy: ToolPolicy | None = None,
    ) -> None:
        self._gateway = gateway
        self._tools = tools
        self._retrieval = retrieval
        self._memory = memory
        self._mcp_caller = mcp_caller
        self._policy = policy

    def validate(self, flow: FlowSpec) -> ValidationResult:
        return validate_flowspec(flow)

    def normalize(self, flow: FlowSpec) -> FlowSpec:
        # MVP: FlowSpec is already normalized on construction (Pydantic defaults). Reserved for
        # future normalization passes (e.g. auto-inserting implicit guardrail nodes).
        return flow

    def compile(self, flow: FlowSpec, *, checkpointer: BaseCheckpointSaver | None = None) -> CompiledWorkflow:
        result = self.validate(flow)
        if not result.valid:
            raise CompilationError(result)

        flow = self.normalize(flow)
        graph: StateGraph = StateGraph(WorkflowState)

        for node in flow.nodes:
            graph.add_node(
                node.id,
                build_node_fn(
                    node,
                    flow,
                    self._gateway,
                    self._tools,
                    retrieval=self._retrieval,
                    memory=self._memory,
                    mcp_caller=self._mcp_caller,
                    policy=self._policy,
                ),
            )

        router_or_supervisor_ids = {
            n.id for n in flow.nodes if n.type in (NodeType.ROUTER, NodeType.SUPERVISOR)
        }

        for edge in flow.edges:
            if edge.source in router_or_supervisor_ids:
                continue
            graph.add_edge(edge.source, edge.target)

        def make_condition(node_id: str):
            def condition(state: WorkflowState) -> str:
                decision = state.get("node_outputs", {}).get(node_id, {})
                target = decision.get("target") if isinstance(decision, dict) else None
                if target is None:
                    raise RuntimeError(f"Router/Supervisor node '{node_id}' produced no target.")
                return target

            return condition

        for node in flow.nodes:
            if node.type == NodeType.ROUTER:
                targets = {r.target for r in node.config.rules}
                if node.config.default_target:
                    targets.add(node.config.default_target)
                graph.add_conditional_edges(node.id, make_condition(node.id), {t: t for t in targets})
            elif node.type == NodeType.SUPERVISOR:
                targets = set(node.config.agents)
                if node.config.fallback_agent:
                    targets.add(node.config.fallback_agent)
                graph.add_conditional_edges(node.id, make_condition(node.id), {t: t for t in targets})

        input_node = next(n for n in flow.nodes if n.type == NodeType.INPUT)
        graph.add_edge(START, input_node.id)

        nodes_with_outgoing = {e.source for e in flow.edges} | router_or_supervisor_ids
        for node in flow.nodes:
            if node.id not in nodes_with_outgoing:
                graph.add_edge(node.id, END)

        compiled = graph.compile(checkpointer=checkpointer)
        return CompiledWorkflow(flow=flow, graph=compiled, input_node_id=input_node.id)
