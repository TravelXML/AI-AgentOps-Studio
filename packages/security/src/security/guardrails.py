"""Guardrail checks (Phase 6): the pre/post content checks a GuardrailNode applies to text
flowing through a workflow. PII detection is regex-based (email/phone/SSN/credit-card patterns),
prompt-injection detection is a keyword/phrase heuristic - both are honestly limited (a determined
adversary can evade a heuristic), documented as such rather than oversold as a guarantee.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GuardrailViolation:
    check_type: str
    message: str


_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

_PROMPT_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore your instructions",
    "disregard the above",
    "disregard previous instructions",
    "you are now",
    "reveal your instructions",
    "reveal your system prompt",
    "act as if",
    "jailbreak",
    "new instructions:",
    "do anything now",
)


def check_pii(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    types = config.get("types") or list(_PII_PATTERNS)
    for kind in types:
        pattern = _PII_PATTERNS.get(kind)
        if pattern and pattern.search(text):
            return GuardrailViolation("pii_detection", f"detected a possible {kind} in the content")
    return None


def check_blocked_keywords(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    lowered = text.lower()
    for keyword in config.get("keywords", []):
        if keyword.lower() in lowered:
            return GuardrailViolation("blocked_keywords", f"contains blocked keyword '{keyword}'")
    return None


def check_prompt_injection(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    lowered = text.lower()
    for phrase in _PROMPT_INJECTION_PHRASES:
        if phrase in lowered:
            return GuardrailViolation(
                "prompt_injection_heuristic", f"matched a known prompt-injection phrase: '{phrase}'"
            )
    return None


def check_max_input_size(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    max_chars = config.get("max_chars", 10_000)
    if len(text) > max_chars:
        return GuardrailViolation(
            "max_input_size", f"content is {len(text)} characters, exceeds max of {max_chars}"
        )
    return None


def check_output_validation(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    if config.get("non_empty", True) and not text.strip():
        return GuardrailViolation("output_validation", "output is empty")
    return None


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
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not _check_type(value, expected_type):
        errors.append(f"expected type {expected_type}, got {type(value).__name__}")
        return errors
    if expected_type == "object" and isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"missing required field '{field}'")
    return errors


def check_json_schema(text: str, config: dict[str, Any]) -> GuardrailViolation | None:
    schema = config.get("schema", {})
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return GuardrailViolation("json_schema", "content is not valid JSON")
    errors = _validate_schema(value, schema)
    if errors:
        return GuardrailViolation("json_schema", "; ".join(errors))
    return None


CHECKS = {
    "pii_detection": check_pii,
    "blocked_keywords": check_blocked_keywords,
    "prompt_injection_heuristic": check_prompt_injection,
    "max_input_size": check_max_input_size,
    "output_validation": check_output_validation,
    "json_schema": check_json_schema,
}


def run_checks(text: str, checks: list[dict[str, Any]]) -> list[GuardrailViolation]:
    violations = []
    for check in checks:
        fn = CHECKS.get(check.get("type", ""))
        if fn is None:
            continue
        violation = fn(text, check.get("config", {}))
        if violation:
            violations.append(violation)
    return violations
