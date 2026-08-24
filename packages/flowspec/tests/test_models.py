import pytest
from pydantic import ValidationError

from flowspec import AgentNodeConfig, Edge, FlowSpec, InputField, InputNode, OutputNode


def make_simple_flow() -> FlowSpec:
    return FlowSpec(
        id="simple-agent",
        name="Simple Agent",
        inputs=[InputField(name="query", type="string")],
        nodes=[
            InputNode(id="input-1", label="Input"),
            {
                "id": "agent-1",
                "type": "agent",
                "label": "Agent",
                "config": AgentNodeConfig(name="Assistant", model="mock"),
            },
            OutputNode(id="output-1", label="Output"),
        ],
        edges=[
            Edge(id="e1", source="input-1", target="agent-1"),
            Edge(id="e2", source="agent-1", target="output-1"),
        ],
    )


def test_flowspec_round_trips_through_json():
    flow = make_simple_flow()
    payload = flow.model_dump_json()
    restored = FlowSpec.model_validate_json(payload)
    assert restored == flow
    assert restored.node_by_id("agent-1").config.name == "Assistant"


def test_node_discriminated_union_rejects_unknown_type():
    with pytest.raises(ValidationError):
        FlowSpec(
            id="bad",
            name="Bad",
            nodes=[{"id": "x", "type": "not-a-real-type", "config": {}}],
        )


def test_agent_node_requires_config():
    with pytest.raises(ValidationError):
        FlowSpec(id="bad", name="Bad", nodes=[{"id": "a", "type": "agent"}])


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        FlowSpec(id="bad", name="Bad", nodes=[], not_a_field=True)
