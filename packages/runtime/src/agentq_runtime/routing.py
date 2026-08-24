"""Shared routing/selection logic for Router (LLM mode) and Supervisor nodes.

Full tool-calling/structured-output-driven routing is a documented future enhancement (see
docs/architecture/execution-engine.md). For MVP, target selection uses deterministic keyword
overlap against candidate labels/descriptions, while the configured model is still called so its
response is recorded as the human-readable rationale - this keeps the "why was this agent
selected" trail genuinely populated (spec section 14) without pretending an LLM tool-call
happened when it did not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from model_gateway import ChatMessage, ModelGateway, ModelGatewayError


@dataclass
class Candidate:
    id: str
    label: str
    description: str = ""


@dataclass
class RoutingDecision:
    target: str
    reason: str


def _score(text: str, candidate: Candidate) -> int:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    candidate_words = set(re.findall(r"[a-z0-9]+", f"{candidate.label} {candidate.description}".lower()))
    return len(words & candidate_words)


async def choose_candidate(
    *,
    gateway: ModelGateway,
    model_id: str,
    instructions: str,
    input_text: str,
    candidates: list[Candidate],
    default_target: str | None = None,
) -> RoutingDecision:
    if not candidates:
        raise ModelGatewayError("No routing candidates available.")

    if len(candidates) == 1:
        scored_best = candidates[0]
    else:
        scored = sorted(candidates, key=lambda c: _score(input_text, c), reverse=True)
        best_score = _score(input_text, scored[0])
        scored_best = (
            scored[0]
            if best_score > 0
            else (next((c for c in candidates if c.id == default_target), scored[0]))
        )

    options = "\n".join(f"- {c.id}: {c.label} - {c.description}" for c in candidates)
    prompt = (
        f"{instructions}\n\nAvailable targets:\n{options}\n\n"
        f'Input: "{input_text}"\n\nWhich target should handle this, and why?'
    )
    try:
        response = await gateway.complete(
            model_id,
            [
                ChatMessage(role="system", content=instructions),
                ChatMessage(role="user", content=prompt),
            ],
        )
        reason = response.content
    except ModelGatewayError as exc:
        reason = f"Model call failed ({exc}); fell back to keyword-overlap selection."

    return RoutingDecision(target=scored_best.id, reason=reason)
