import pytest

from flowspec import AgentNodeConfig, Edge, FlowSpec, InputNode, OutputNode
from flowspec.models import AgentNode


def simple_agent_flow() -> FlowSpec:
    return FlowSpec(
        id="simple-agent",
        name="Simple Agent",
        nodes=[
            InputNode(id="input-1", label="Input"),
            AgentNode(
                id="agent-1",
                label="Assistant",
                config=AgentNodeConfig(name="Assistant", instructions="Be helpful.", model="mock"),
            ),
            OutputNode(id="output-1", label="Output"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="agent-1"),
            Edge(id="e2", source="agent-1", target="output-1"),
        ],
    )


@pytest.mark.asyncio
async def test_simple_agent_flow_executes_end_to_end(runtime, checkpointer):
    compiled = await runtime.compile(simple_agent_flow(), checkpointer=checkpointer)
    events = [e async for e in runtime.execute(compiled, "run-1", {"query": "What is AgentQ?"})]

    types = [e.type for e in events]
    assert types[0] == "run.started"
    assert types[-1] == "run.completed"
    assert "node.started" in types
    assert "llm.started" in types
    assert "llm.completed" in types
    assert "node.completed" in types

    llm_event = next(e for e in events if e.type == "llm.completed")
    assert llm_event.data["total_tokens"] > 0
    assert llm_event.data["provider"] == "mock"

    output_completed = [e for e in events if e.type == "node.completed" and e.node_id == "output-1"]
    assert output_completed
    assert "What is AgentQ?" in output_completed[0].data["output"]

    status = await runtime.get_status(compiled, "run-1")
    assert status == "SUCCEEDED"


@pytest.mark.asyncio
async def test_agent_flow_failure_halts_run(runtime, checkpointer):
    flow = simple_agent_flow()
    flow.node_by_id("agent-1").config.model = "does-not-exist"
    compiled = await runtime.compile(flow, checkpointer=checkpointer)

    events = [e async for e in runtime.execute(compiled, "run-fail", {"query": "hi"})]
    assert events[-1].type == "run.failed"
    # the Output node must never have run on top of a failed Agent node
    assert not any(e.node_id == "output-1" for e in events)

    status = await runtime.get_status(compiled, "run-fail")
    assert status == "FAILED"
