import pytest

from flowspec import (
    AgentNodeConfig,
    Edge,
    FlowSpec,
    InputNode,
    OutputNode,
    RouterNode,
    RouterNodeConfig,
    RouterRule,
    ToolNode,
    ToolNodeConfig,
)
from flowspec.models import AgentNode


def router_flow() -> FlowSpec:
    return FlowSpec(
        id="router-flow",
        name="Router Flow",
        nodes=[
            InputNode(id="input-1"),
            RouterNode(
                id="router-1",
                config=RouterNodeConfig(
                    mode="rule",
                    rules=[RouterRule(when="input.intent == 'billing'", target="billing-agent")],
                    default_target="support-agent",
                ),
            ),
            AgentNode(
                id="billing-agent",
                config=AgentNodeConfig(name="Billing", instructions="Handle billing.", model="mock"),
            ),
            AgentNode(
                id="support-agent",
                config=AgentNodeConfig(name="Support", instructions="Handle support.", model="mock"),
            ),
            OutputNode(id="output-1"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="router-1"),
            Edge(id="e2", source="router-1", target="billing-agent"),
            Edge(id="e3", source="router-1", target="support-agent"),
            Edge(id="e4", source="billing-agent", target="output-1"),
            Edge(id="e5", source="support-agent", target="output-1"),
        ],
    )


@pytest.mark.asyncio
async def test_router_picks_billing_agent(runtime, checkpointer):
    compiled = await runtime.compile(router_flow(), checkpointer=checkpointer)
    events = [e async for e in runtime.execute(compiled, "run-billing", {"intent": "billing"})]
    assert events[-1].type == "run.completed"
    ran_nodes = {e.node_id for e in events if e.type == "node.completed"}
    assert "billing-agent" in ran_nodes
    assert "support-agent" not in ran_nodes


@pytest.mark.asyncio
async def test_router_default_target(runtime, checkpointer):
    compiled = await runtime.compile(router_flow(), checkpointer=checkpointer)
    events = [e async for e in runtime.execute(compiled, "run-support", {"intent": "returns"})]
    assert events[-1].type == "run.completed"
    ran_nodes = {e.node_id for e in events if e.type == "node.completed"}
    assert "support-agent" in ran_nodes
    assert "billing-agent" not in ran_nodes


def tool_flow() -> FlowSpec:
    return FlowSpec(
        id="tool-flow",
        name="Tool Flow",
        nodes=[
            InputNode(id="input-1"),
            ToolNode(
                id="calc-1",
                config=ToolNodeConfig(tool_id="calculator", arguments={"expression": "6 * 7"}),
            ),
            OutputNode(id="output-1"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="calc-1"),
            Edge(id="e2", source="calc-1", target="output-1"),
        ],
    )


@pytest.mark.asyncio
async def test_tool_node_executes_calculator(runtime, checkpointer):
    compiled = await runtime.compile(tool_flow(), checkpointer=checkpointer)
    events = [e async for e in runtime.execute(compiled, "run-calc", {})]
    assert events[-1].type == "run.completed"
    tool_completed = next(e for e in events if e.type == "tool.completed")
    assert tool_completed.data["result"]["result"] == 42
