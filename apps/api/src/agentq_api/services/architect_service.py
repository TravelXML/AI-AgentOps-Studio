"""AI Architect (Phase 3): natural language -> FlowSpec, through the same ModelGateway every
other node uses - no separate "architect model" concept, no hard-coded provider SDK calls.

The repair loop is real, not cosmetic: on a JSON parse failure or a FlowSpec schema validation
failure, the exact error is fed back to the model and it is asked to correct its own previous
output, up to MAX_ATTEMPTS total calls. LLMs reliably self-correct given a precise Pydantic error
even when they rarely produce perfect structured output on the first try. If a real model still
can't produce a valid flow, generation fails loudly with the last validation error rather than
returning something broken. MockLLM (the zero-key default) cannot follow structured-output
instructions at all - it will exhaust the repair loop and fail, which is the honest outcome.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from flowspec import FlowSpec
from model_gateway import ChatMessage, ModelGateway, ModelGatewayError

MAX_ATTEMPTS = 3

SYSTEM_PROMPT = """You are the AI Architect for AgentQ, a visual agent-workflow builder. Convert the \
user's natural-language description into a single JSON object matching this FlowSpec shape exactly:

{
  "name": string,
  "description": string,
  "nodes": [ {"id": string, "type": one of "input"/"output"/"agent"/"llm"/"router"/"supervisor"/\
"tool"/"mcp"/"rag"/"memory"/"human_approval"/"guardrail", "label": string, \
"position": {"x": number, "y": number}, "config": {...type-specific, see below}} ],
  "edges": [ {"id": string, "source": node_id, "target": node_id} ]
}

Node config shapes (omit fields you don't need - defaults apply):
- input: {"mode": "text", "fields": []}
- output: {"format": "text"}
- agent: {"name": string, "description": string, "instructions": string, "model": "default", \
"temperature": number, "max_tokens": number, "tools": []}
- llm: {"model": "default", "prompt_template": "{input}", "temperature": number}
- router: {"mode": "rule", "rules": [{"when": expression_string, "target": node_id}], \
"default_target": node_id}
- supervisor: {"agents": [node_id, ...], "routing_instructions": string, "fallback_agent": node_id}
- tool: {"tool_id": "http_get"|"http_post"|"calculator"|"current_datetime"|"json_transform", \
"arguments": {}}
- human_approval: {"message_template": string, "condition": expression_string_or_null}

Hard rules:
- Exactly one input node, at least one output node, and every node reachable from input.
- Node ids: short kebab-case, e.g. "input-1", "agent-1", "output-1". Edge ids: "e1", "e2", ...
- Leave "model" as the literal string "default" unless the user names a specific provider/model.
- Position nodes left-to-right in execution order, spaced ~220 apart on x, using {"x": N*220, "y": 80}.
- Output ONLY the JSON object - no markdown code fences, no commentary, no explanation text.
"""

_REPAIR_INSTRUCTION = (
    "Reply with ONLY the corrected JSON object. No markdown fences, no commentary - just the JSON."
)


class ArchitectError(RuntimeError):
    def __init__(self, message: str, *, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(message)


def _extract_json(text: str) -> str:
    """Models often wrap JSON in ```json fences despite instructions not to - strip them."""
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return fence.group(1) if fence else stripped


def _format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors(include_url=False)[:8]:
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"- {loc}: {err['msg']}")
    return "\n".join(lines)


def _scaffold_defaults(parsed: dict) -> dict:
    """Fields the platform owns, not the model - reduces the JSON surface the LLM must get right.
    `flow_service.save_version` overwrites id/version again on save regardless."""
    parsed.setdefault("schema_version", 1)
    parsed.setdefault("id", "generated")
    parsed.setdefault("version", 1)
    parsed.setdefault("inputs", [])
    parsed.setdefault("variables", {})
    parsed.setdefault("policies", {})
    parsed.setdefault("metadata", {})
    return parsed


async def generate_flowspec(gateway: ModelGateway, model_id: str, description: str) -> tuple[FlowSpec, int]:
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=description),
    ]
    last_error = "no attempts made"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await gateway.complete(model_id, messages, temperature=0.2, max_tokens=4000)
        except ModelGatewayError as exc:
            raise ArchitectError(str(exc), attempts=attempt) from exc

        raw = _extract_json(response.content)

        try:
            parsed = _scaffold_defaults(json.loads(raw))
        except (json.JSONDecodeError, AttributeError) as exc:
            last_error = f"response was not a valid JSON object ({exc})"
            messages.append(ChatMessage(role="assistant", content=response.content))
            messages.append(
                ChatMessage(role="user", content=f"That was not valid JSON: {exc}. {_REPAIR_INSTRUCTION}")
            )
            continue

        try:
            return FlowSpec.model_validate(parsed), attempt
        except ValidationError as exc:
            last_error = _format_validation_error(exc)
            messages.append(ChatMessage(role="assistant", content=response.content))
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"That JSON failed schema validation:\n{last_error}\n{_REPAIR_INSTRUCTION}",
                )
            )

    raise ArchitectError(
        f"Could not produce a valid flow after {MAX_ATTEMPTS} attempts. Last error:\n{last_error}",
        attempts=MAX_ATTEMPTS,
    )
