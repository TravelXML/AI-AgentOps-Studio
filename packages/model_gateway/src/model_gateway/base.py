from __future__ import annotations

from abc import ABC, abstractmethod

from model_gateway.types import ChatMessage, ModelConfig, ModelResponse


class ModelProvider(ABC):
    """One LLM provider backend. The gateway never calls provider SDKs directly from business
    logic - every call flows through this interface."""

    @abstractmethod
    async def complete(
        self,
        config: ModelConfig,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse: ...
