"""A restricted boolean-expression evaluator for Router rules and Human Approval conditions.

Spec section 80 forbids `eval()` on user input, so router/guardrail expressions are parsed with
`ast` and walked against an explicit allow-list of node types instead of executed.
"""

from __future__ import annotations

import ast
from typing import Any


class ExpressionError(ValueError):
    pass


_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Attribute,
    ast.List,
    ast.Tuple,
)


def _resolve_name(name: str, context: dict[str, Any]) -> Any:
    parts = name.split(".")
    value: Any = context
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
    return value


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

    def visit(self, node: ast.AST) -> Any:
        if not isinstance(node, _ALLOWED_NODES):
            raise ExpressionError(f"Disallowed expression element: {type(node).__name__}")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        values = [self.visit(v) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        return not self.visit(node.operand)

    def visit_Compare(self, node: ast.Compare) -> bool:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            else:  # pragma: no cover - guarded by _ALLOWED_NODES
                raise ExpressionError(f"Unsupported comparison: {type(op).__name__}")
            if not ok:
                return False
            left = right
        return True

    def visit_Name(self, node: ast.Name) -> Any:
        return _resolve_name(node.id, self.context)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        base = self.visit(node.value)
        if isinstance(base, dict):
            return base.get(node.attr)
        return getattr(base, node.attr, None)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(e) for e in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(e) for e in node.elts)


def evaluate_expression(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a restricted boolean expression such as `intent == 'billing'` against `context`."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Invalid expression syntax: {expression!r}") from exc
    return bool(_SafeEvaluator(context).visit(tree))


def render_template(template: str, context: dict[str, Any]) -> str:
    """Render `{{var}}` / `{{a.b}}` placeholders using dotted lookups against `context`."""
    import re

    def replace(match: re.Match[str]) -> str:
        value = _resolve_name(match.group(1).strip(), context)
        return "" if value is None else str(value)

    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", replace, template)
