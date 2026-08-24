from flowspec import (
    AgentNodeConfig,
    Edge,
    FlowSpec,
    InputNode,
    OutputNode,
    RouterNode,
    RouterNodeConfig,
    RouterRule,
    validate_flowspec,
)
from flowspec.models import AgentNode


def valid_flow() -> FlowSpec:
    return FlowSpec(
        id="f1",
        name="F1",
        nodes=[
            InputNode(id="in"),
            AgentNode(id="agent", config=AgentNodeConfig(name="A", model="mock")),
            OutputNode(id="out"),
        ],
        edges=[
            Edge(id="e1", source="in", target="agent"),
            Edge(id="e2", source="agent", target="out"),
        ],
    )


def test_valid_flow_passes():
    result = validate_flowspec(valid_flow())
    assert result.valid, result.issues


def test_missing_input_reported():
    flow = valid_flow()
    flow.nodes = [n for n in flow.nodes if n.type != "input"]
    result = validate_flowspec(flow)
    assert not result.valid
    assert any(i.code == "MISSING_INPUT" for i in result.issues)


def test_missing_output_reported():
    flow = valid_flow()
    flow.nodes = [n for n in flow.nodes if n.type != "output"]
    result = validate_flowspec(flow)
    assert not result.valid
    assert any(i.code == "MISSING_OUTPUT" for i in result.issues)


def test_orphan_node_reported():
    flow = valid_flow()
    flow.nodes.append(AgentNode(id="orphan", config=AgentNodeConfig(name="O", model="mock")))
    result = validate_flowspec(flow)
    assert not result.valid
    assert any(i.code == "ORPHAN_NODE" and i.node_id == "orphan" for i in result.issues)


def test_missing_model_reported_with_actionable_message():
    flow = valid_flow()
    agent = flow.node_by_id("agent")
    agent.config.model = ""
    result = validate_flowspec(flow)
    assert not result.valid
    issue = next(i for i in result.issues if i.code == "MISSING_MODEL")
    assert "no model configured" in issue.message


def test_invalid_edge_reference_reported():
    flow = valid_flow()
    flow.edges.append(Edge(id="bad", source="agent", target="does-not-exist"))
    result = validate_flowspec(flow)
    assert not result.valid
    assert any(i.code == "INVALID_EDGE" for i in result.issues)


def test_router_invalid_target_reported():
    flow = valid_flow()
    flow.nodes.append(
        RouterNode(
            id="router",
            config=RouterNodeConfig(rules=[RouterRule(when="true", target="ghost")]),
        )
    )
    result = validate_flowspec(flow)
    assert any(i.code == "INVALID_ROUTE_TARGET" for i in result.issues)
