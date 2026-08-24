"""Built-in MVP tools (spec section 17): HTTP GET/POST, Calculator, Current Date/Time,
JSON Transform. No unrestricted Python execution tool is registered - the spec explicitly forbids
running arbitrary Python in the main API process."""

from __future__ import annotations

import ast
import operator
from datetime import UTC, datetime
from typing import Any

import httpx

from agentq_runtime.tools.registry import ToolDefinition, ToolExecutionError, ToolRegistry
from agentq_runtime.tools.ssrf_guard import assert_safe_url

_ARITHMETIC_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_arithmetic(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ARITHMETIC_OPS:
        return _ARITHMETIC_OPS[type(node.op)](
            _safe_eval_arithmetic(node.left), _safe_eval_arithmetic(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ARITHMETIC_OPS:
        return _ARITHMETIC_OPS[type(node.op)](_safe_eval_arithmetic(node.operand))
    raise ToolExecutionError(f"Unsupported expression element: {type(node).__name__}")


async def _calculator(arguments: dict[str, Any]) -> Any:
    expression = arguments.get("expression")
    if not expression or not isinstance(expression, str):
        raise ToolExecutionError("Calculator requires a string 'expression' argument.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolExecutionError(f"Invalid arithmetic expression: {expression!r}") from exc
    return {"result": _safe_eval_arithmetic(tree)}


async def _current_datetime(arguments: dict[str, Any]) -> Any:
    now = datetime.now(UTC)
    return {"iso8601": now.isoformat(), "unix": int(now.timestamp())}


async def _http_get(arguments: dict[str, Any]) -> Any:
    url = arguments.get("url")
    if not url:
        raise ToolExecutionError("HTTP GET requires a 'url' argument.")
    assert_safe_url(url)
    params = arguments.get("params") or {}
    headers = arguments.get("headers") or {}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.get(url, params=params, headers=headers)
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text[:100_000],
    }


async def _http_post(arguments: dict[str, Any]) -> Any:
    url = arguments.get("url")
    if not url:
        raise ToolExecutionError("HTTP POST requires a 'url' argument.")
    assert_safe_url(url)
    headers = arguments.get("headers") or {}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.post(url, json=arguments.get("json"), headers=headers)
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text[:100_000],
    }


async def _json_transform(arguments: dict[str, Any]) -> Any:
    data = arguments.get("data")
    path = arguments.get("path", "")
    if data is None:
        raise ToolExecutionError("JSON Transform requires a 'data' argument.")
    current: Any = data
    if path:
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.lstrip("-").isdigit():
                idx = int(part)
                current = current[idx] if -len(current) <= idx < len(current) else None
            else:
                current = None
            if current is None:
                break
    return {"result": current}


def register_builtin_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            id="http_get",
            name="HTTP GET",
            description="Fetch a URL via HTTP GET. Blocked for localhost/private/metadata addresses.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "params": {"type": "object"},
                    "headers": {"type": "object"},
                },
                "required": ["url"],
            },
            output_schema={"type": "object"},
            permissions=["net.http.get"],
            handler=_http_get,
        )
    )
    registry.register(
        ToolDefinition(
            id="http_post",
            name="HTTP POST",
            description="Send a JSON POST to a URL. Blocked for localhost/private/metadata addresses.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "json": {"type": "object"},
                    "headers": {"type": "object"},
                },
                "required": ["url"],
            },
            output_schema={"type": "object"},
            permissions=["net.http.post"],
            handler=_http_post,
        )
    )
    registry.register(
        ToolDefinition(
            id="calculator",
            name="Calculator",
            description="Evaluate a basic arithmetic expression (+ - * / // % **).",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
            permissions=[],
            handler=_calculator,
        )
    )
    registry.register(
        ToolDefinition(
            id="current_datetime",
            name="Current Date/Time",
            description="Return the current UTC date and time.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            permissions=[],
            handler=_current_datetime,
        )
    )
    registry.register(
        ToolDefinition(
            id="json_transform",
            name="JSON Transform",
            description="Extract a value from JSON data via a dotted path, e.g. 'items.0.name'.",
            input_schema={
                "type": "object",
                "properties": {"data": {}, "path": {"type": "string"}},
                "required": ["data"],
            },
            output_schema={"type": "object"},
            permissions=[],
            handler=_json_transform,
        )
    )


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    return registry
