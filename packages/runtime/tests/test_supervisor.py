import pytest

from flowspec import (
    AgentNodeConfig,
    Edge,
    FlowSpec,
    InputNode,
    OutputNode,
    SupervisorNode,
    SupervisorNodeConfig,
)
from flowspec.models import AgentNode


def supervisor_flow() -> FlowSpec:
    return FlowSpec(
        id="supervisor-flow",
        name="Supervisor Flow",
        nodes=[
            InputNode(id="input-1"),
            SupervisorNode(
                id="supervisor-1",
                config=SupervisorNodeConfig(agents=["research-agent", "writer-agent"]),
            ),
            AgentNode(
                id="research-agent",
                label="Researcher",
                config=AgentNodeConfig(
                    name="Researcher",
                    description="Finds facts and research data.",
                    instructions="Research the topic.",
                    model="mock",
                ),
            ),
            AgentNode(
                id="writer-agent",
                label="Writer",
                config=AgentNodeConfig(
                    name="Writer",
                    description="Writes prose and articles.",
                    instructions="Write the article.",
                    model="mock",
                ),
            ),
            OutputNode(id="output-1"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="supervisor-1"),
            Edge(id="e2", source="supervisor-1", target="research-agent"),
            Edge(id="e3", source="supervisor-1", target="writer-agent"),
            Edge(id="e4", source="research-agent", target="output-1"),
            Edge(id="e5", source="writer-agent", target="output-1"),
        ],
    )


@pytest.mark.asyncio
async def test_supervisor_delegates_to_one_agent_and_records_reason(runtime, checkpointer):
    compiled = await runtime.compile(supervisor_flow(), checkpointer=checkpointer)
    events = [e async for e in runtime.execute(compiled, "run-sup", {"query": "write an article"})]
    assert events[-1].type == "run.completed"

    supervisor_completed = next(
        e for e in events if e.type == "node.completed" and e.node_id == "supervisor-1"
    )
    assert supervisor_completed.data["target"] in ("research-agent", "writer-agent")
    assert supervisor_completed.data["reason"]

    ran_agents = {
        e.node_id
        for e in events
        if e.type == "node.completed" and e.node_id in ("research-agent", "writer-agent")
    }
    assert len(ran_agents) == 1
    assert ran_agents.pop() == supervisor_completed.data["target"]
