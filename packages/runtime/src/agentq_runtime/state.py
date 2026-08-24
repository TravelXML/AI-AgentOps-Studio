from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {**a, **b}


class WorkflowState(TypedDict, total=False):
    """Shared state threaded through every LangGraph node. `node_outputs` and `variables` use a
    merge reducer so each node can return just its own delta."""

    input: dict[str, Any]
    variables: Annotated[dict[str, Any], _merge_dicts]
    node_outputs: Annotated[dict[str, Any], _merge_dicts]
    output: Any
    error: str | None
