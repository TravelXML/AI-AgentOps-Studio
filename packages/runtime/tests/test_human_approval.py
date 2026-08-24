import pytest

from flowspec import (
    AgentNodeConfig,
    Edge,
    FlowSpec,
    HumanApprovalNode,
    HumanApprovalNodeConfig,
    InputNode,
    OutputNode,
)
from flowspec.models import AgentNode


def approval_flow() -> FlowSpec:
    return FlowSpec(
        id="approval-flow",
        name="Approval Flow",
        nodes=[
            InputNode(id="input-1"),
            AgentNode(
                id="agent-1",
                config=AgentNodeConfig(name="Refund Agent", instructions="Process refunds.", model="mock"),
            ),
            HumanApprovalNode(
                id="approval-1",
                config=HumanApprovalNodeConfig(message_template="Approve refund?"),
            ),
            OutputNode(id="output-1"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="agent-1"),
            Edge(id="e2", source="agent-1", target="approval-1"),
            Edge(id="e3", source="approval-1", target="output-1"),
        ],
    )


@pytest.mark.asyncio
async def test_run_pauses_for_approval_then_resumes_on_approve(runtime, checkpointer):
    compiled = await runtime.compile(approval_flow(), checkpointer=checkpointer)

    events = [e async for e in runtime.execute(compiled, "run-approve", {"amount": 600})]
    assert events[-1].type in ("run.waiting",)
    status = await runtime.get_status(compiled, "run-approve")
    assert status == "WAITING_FOR_HUMAN"
    assert not any(e.node_id == "output-1" for e in events)

    resume_events = [e async for e in runtime.resume(compiled, "run-approve", {"approved": True})]
    assert resume_events[-1].type == "run.completed"
    status = await runtime.get_status(compiled, "run-approve")
    assert status == "SUCCEEDED"
    assert any(e.node_id == "output-1" and e.type == "node.completed" for e in resume_events)


@pytest.mark.asyncio
async def test_run_fails_when_rejected(runtime, checkpointer):
    compiled = await runtime.compile(approval_flow(), checkpointer=checkpointer)
    _ = [e async for e in runtime.execute(compiled, "run-reject", {"amount": 900})]

    resume_events = [e async for e in runtime.resume(compiled, "run-reject", {"approved": False})]
    assert resume_events[-1].type == "run.failed"
    status = await runtime.get_status(compiled, "run-reject")
    assert status == "FAILED"
    assert not any(e.node_id == "output-1" for e in resume_events)
