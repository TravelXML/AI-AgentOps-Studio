"""LiteLLM-backed provider: one code path for OpenAI, Anthropic, Gemini, Groq, OpenRouter,
NVIDIA NIM, Azure OpenAI, Bedrock, Ollama, and custom OpenAI-compatible endpoints (spec section 8).
"""

from __future__ import annotations

import time
from collections.abc import Callable

import litellm

from model_gateway.base import ModelProvider
from model_gateway.types import (
    ChatMessage,
    ModelConfig,
    ModelGatewayError,
    ModelResponse,
    TokenUsage,
)

litellm.suppress_debug_info = True


class LiteLLMProvider(ModelProvider):
    def __init__(self, secret_resolver: Callable[[str], str | None] | None = None) -> None:
        self._secret_resolver = secret_resolver or (lambda _secret_id: None)

    async def complete(
        self,
        config: ModelConfig,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        start = time.perf_counter()
        api_key = self._secret_resolver(config.secret_id) if config.secret_id else None

        try:
            response = await litellm.acompletion(
                model=config.model,
                messages=[m.model_dump(exclude_none=True) for m in messages],
                api_key=api_key,
                api_base=config.base_url,
                temperature=temperature if temperature is not None else config.temperature_default,
                max_tokens=max_tokens,
                timeout=config.timeout_seconds,
                num_retries=config.max_retries,
            )
        except Exception as exc:  # noqa: BLE001 - normalize every provider failure
            raise ModelGatewayError(f"model call failed for '{config.id}': {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage

        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:  # noqa: BLE001 - cost lookup is best-effort
            cost = 0.0

        return ModelResponse(
            content=content,
            provider=config.provider,
            model=config.model,
            usage=TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
                cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            ),
            estimated_cost_usd=float(cost or 0.0),
            latency_ms=latency_ms,
            raw={"finish_reason": getattr(choice, "finish_reason", None)},
        )
