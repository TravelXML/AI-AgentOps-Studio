"""Evaluation module (Phase 5): built-in evaluators that check a flow run's actual output (and
run-level metrics) against a test case's expected output. Pure functions except `llm_judge`, which
needs a `ModelGateway` to ask a model whether the output satisfies free-form criteria - the same
gateway every chat node in the runtime uses, so it works with MockLLM (deterministically, if
crudely) and with any configured real model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

EvaluatorType = Literal["exact_match", "contains", "regex", "schema", "latency", "cost", "llm_judge"]


@dataclass
class EvalContext:
    actual_output: Any
    expected_output: Any | None
    total_cost_usd: float
    duration_ms: float | None
    run_error: str | None


@dataclass
class EvalResult:
    evaluator: str
    passed: bool
    detail: str


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value)


def evaluate_exact_match(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    passed = ctx.actual_output == ctx.expected_output
    return EvalResult("exact_match", passed, f"expected={ctx.expected_output!r} actual={ctx.actual_output!r}")


def evaluate_contains(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    needle = config.get("value")
    if needle is None:
        needle = ctx.expected_output
    haystack = _as_text(ctx.actual_output)
    passed = _as_text(needle) in haystack
    return EvalResult("contains", passed, f"looked for {needle!r} in output")


def evaluate_regex(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    pattern = config.get("pattern", "")
    try:
        passed = re.search(pattern, _as_text(ctx.actual_output)) is not None
        detail = f"pattern={pattern!r}"
    except re.error as exc:
        passed = False
        detail = f"invalid pattern {pattern!r}: {exc}"
    return EvalResult("regex", passed, detail)


def _check_type(value: Any, expected_type: str) -> bool:
    mapping = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    py_type = mapping.get(expected_type)
    return py_type is None or isinstance(value, py_type)


def _validate_schema(value: Any, schema: dict[str, Any]) -> list[str]:
    """A small, honest subset of JSON Schema: type checking + required/properties for objects -
    not a full validator. Good enough to catch "the agent forgot a field" or "returned a string
    instead of an object" without pulling in a JSON Schema dependency."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not _check_type(value, expected_type):
        errors.append(f"expected type {expected_type}, got {type(value).__name__}")
        return errors

    if expected_type == "object" and isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"missing required field '{field}'")
        for field, sub_schema in (schema.get("properties") or {}).items():
            if field in value:
                errors.extend(_validate_schema(value[field], sub_schema))
    return errors


def evaluate_schema(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    schema = config.get("schema", {})
    errors = _validate_schema(ctx.actual_output, schema)
    return EvalResult("schema", len(errors) == 0, "; ".join(errors) if errors else "matches schema")


def evaluate_latency(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    max_ms = config.get("max_ms")
    if max_ms is None or ctx.duration_ms is None:
        return EvalResult("latency", True, "no max_ms configured or duration unavailable")
    passed = ctx.duration_ms <= max_ms
    return EvalResult("latency", passed, f"{ctx.duration_ms:.0f}ms <= {max_ms}ms")


def evaluate_cost(ctx: EvalContext, config: dict[str, Any]) -> EvalResult:
    max_usd = config.get("max_usd")
    if max_usd is None:
        return EvalResult("cost", True, "no max_usd configured")
    passed = ctx.total_cost_usd <= max_usd
    return EvalResult("cost", passed, f"${ctx.total_cost_usd:.4f} <= ${max_usd}")


_JUDGE_SYSTEM_PROMPT = (
    "You are an evaluator. Given the criteria, the expected output (if any), and the actual "
    "output, respond with exactly one word: PASS or FAIL."
)


async def evaluate_llm_judge(
    ctx: EvalContext, config: dict[str, Any], gateway: Any, model_id: str
) -> EvalResult:
    from model_gateway import ChatMessage, ModelGatewayError

    criteria = config.get("criteria", "The actual output should reasonably answer the input.")
    prompt = (
        f"Criteria: {criteria}\n"
        f"Expected output: {_as_text(ctx.expected_output)}\n"
        f"Actual output: {_as_text(ctx.actual_output)}\n"
        "Does the actual output satisfy the criteria? Reply PASS or FAIL only."
    )
    try:
        response = await gateway.complete(
            model_id,
            [
                ChatMessage(role="system", content=_JUDGE_SYSTEM_PROMPT),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=0.0,
            max_tokens=10,
        )
    except ModelGatewayError as exc:
        return EvalResult("llm_judge", False, f"judge model call failed: {exc}")

    verdict = response.content.strip().upper()
    passed = verdict.startswith("PASS")
    return EvalResult("llm_judge", passed, f"judge said: {response.content.strip()!r}")


SYNC_EVALUATORS = {
    "exact_match": evaluate_exact_match,
    "contains": evaluate_contains,
    "regex": evaluate_regex,
    "schema": evaluate_schema,
    "latency": evaluate_latency,
    "cost": evaluate_cost,
}


async def run_evaluator(
    evaluator_type: str, config: dict[str, Any], ctx: EvalContext, gateway: Any, model_id: str
) -> EvalResult:
    if evaluator_type == "llm_judge":
        return await evaluate_llm_judge(ctx, config, gateway, model_id)
    fn = SYNC_EVALUATORS.get(evaluator_type)
    if fn is None:
        return EvalResult(evaluator_type, False, f"unknown evaluator type '{evaluator_type}'")
    return fn(ctx, config)
