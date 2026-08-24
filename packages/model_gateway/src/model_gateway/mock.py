"""MockLLM: a deterministic, zero-network provider. Used by default so the whole platform
boots and every automated test runs without a paid API key (spec section 8/58)."""

from __future__ import annotations

import time

from model_gateway.base import ModelProvider
from model_gateway.types import ChatMessage, ModelConfig, ModelResponse, TokenUsage


def _count_tokens(text: str) -> int:
    # Not a real tokenizer - a stable, cheap approximation good enough for MockLLM accounting.
    return max(1, len(text.split()))


class MockLLM(ModelProvider):
    """Produces a deterministic reply derived from the system instructions and the latest user
    message, so the same input always yields the same output (useful for tests and demos)."""

    async def complete(
        self,
        config: ModelConfig,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        start = time.perf_counter()

        system = next((m.content for m in messages if m.role == "system"), "")
        user_messages = [m.content for m in messages if m.role == "user"]
        last_user = user_messages[-1] if user_messages else ""

        role_hint = system.strip().splitlines()[0] if system.strip() else "an assistant"
        content = f'[mock:{config.model}] As {role_hint.rstrip(".")}, here is a response to: "{last_user}"'

        prompt_tokens = sum(_count_tokens(m.content) for m in messages)
        completion_tokens = _count_tokens(content)
        latency_ms = (time.perf_counter() - start) * 1000

        return ModelResponse(
            content=content,
            provider="mock",
            model=config.model,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            estimated_cost_usd=0.0,
            latency_ms=latency_ms,
            raw={"mock": True},
        )
