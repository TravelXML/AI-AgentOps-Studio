"""Workflow validation: turns structural problems into actionable, human-readable errors.

Never surface raw exception text like `ValidationError 0x7823` to the user - every issue here
carries a stable `code` and a plain-English `message` naming the offending node.
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from flowspec.models import FlowSpec, NodeType


class ValidationIssue(BaseModel):
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None
    severity: str = "error"  # error | warning


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = []

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]


def validate_flowspec(flow: FlowSpec) -> ValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = {n.id for n in flow.nodes}

    input_nodes = [n for n in flow.nodes if n.type == NodeType.INPUT]
    output_nodes = [n for n in flow.nodes if n.type == NodeType.OUTPUT]

    if not input_nodes:
        issues.append(ValidationIssue(code="MISSING_INPUT", message="Workflow has no Input node."))
    elif len(input_nodes) > 1:
        issues.append(
            ValidationIssue(
                code="MULTIPLE_INPUT",
                message="Workflow has more than one Input node; only one is supported.",
            )
        )

    if not output_nodes:
        issues.append(ValidationIssue(code="MISSING_OUTPUT", message="Workflow has no Output node."))

    # Edges must reference known nodes.
    for edge in flow.edges:
        if edge.source not in node_ids:
            issues.append(
                ValidationIssue(
                    code="INVALID_EDGE",
                    message=f'Edge "{edge.id}" references unknown source node "{edge.source}".',
                    edge_id=edge.id,
                )
            )
        if edge.target not in node_ids:
            issues.append(
                ValidationIssue(
                    code="INVALID_EDGE",
                    message=f'Edge "{edge.id}" references unknown target node "{edge.target}".',
                    edge_id=edge.id,
                )
            )

    valid_edges = [e for e in flow.edges if e.source in node_ids and e.target in node_ids]

    # Orphan nodes: unreachable from Input, excluding the Input node itself.
    adjacency: dict[str, list[str]] = {n.id: [] for n in flow.nodes}
    reverse_adjacency: dict[str, list[str]] = {n.id: [] for n in flow.nodes}
    for e in valid_edges:
        adjacency[e.source].append(e.target)
        reverse_adjacency[e.target].append(e.source)

    if input_nodes:
        reachable: set[str] = set()
        queue = deque([input_nodes[0].id])
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            queue.extend(adjacency.get(current, []))

        for n in flow.nodes:
            if n.id not in reachable:
                issues.append(
                    ValidationIssue(
                        code="ORPHAN_NODE",
                        message=f'Node "{n.label or n.id}" is not reachable from the Input node.',
                        node_id=n.id,
                    )
                )

    # Output nodes must have at least one predecessor.
    for n in output_nodes:
        if not reverse_adjacency.get(n.id):
            issues.append(
                ValidationIssue(
                    code="UNCONNECTED_OUTPUT",
                    message=f'Output node "{n.label or n.id}" has no incoming connection.',
                    node_id=n.id,
                )
            )

    # Agent nodes must have a model configured.
    for n in flow.nodes:
        if n.type == NodeType.AGENT and not n.config.model:
            issues.append(
                ValidationIssue(
                    code="MISSING_MODEL",
                    message=f'Agent "{n.label or n.config.name}" has no model configured.',
                    node_id=n.id,
                )
            )
        if n.type == NodeType.SUPERVISOR:
            for agent_id in n.config.agents:
                if agent_id not in node_ids:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_SUPERVISOR_AGENT",
                            message=(
                                f'Supervisor "{n.label or n.id}" references unknown agent node "{agent_id}".'
                            ),
                            node_id=n.id,
                        )
                    )
        if n.type == NodeType.ROUTER:
            targets = [r.target for r in n.config.rules]
            if n.config.default_target:
                targets.append(n.config.default_target)
            for target in targets:
                if target not in node_ids:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_ROUTE_TARGET",
                            message=(f'Router "{n.label or n.id}" routes to unknown node "{target}".'),
                            node_id=n.id,
                        )
                    )
        if n.type == NodeType.TOOL and not n.config.tool_id:
            issues.append(
                ValidationIssue(
                    code="INVALID_TOOL",
                    message=f'Tool node "{n.label or n.id}" has no tool selected.',
                    node_id=n.id,
                )
            )
        if n.type == NodeType.MCP and (not n.config.server_id or not n.config.tool_name):
            issues.append(
                ValidationIssue(
                    code="MISSING_MCP_SERVER",
                    message=f'MCP node "{n.label or n.id}" has no server/tool selected.',
                    node_id=n.id,
                )
            )

    errors = [i for i in issues if i.severity == "error"]
    return ValidationResult(valid=len(errors) == 0, issues=issues)
