"""ModelGateway: the single entry point agents/routers/supervisors use to talk to an LLM.
Never hard-code provider SDK calls in business logic (spec section 8) - call this instead.
"""

from __future__ import annotations

from collections.abc import Callable

from model_gateway.base import ModelProvider
from model_gateway.embeddings import EmbeddingProvider, LiteLLMEmbedding, MockEmbedding
from model_gateway.litellm_provider import LiteLLMProvider
from model_gateway.mock import MockLLM
from model_gateway.types import ChatMessage, ModelConfig, ModelGatewayError, ModelResponse

DEFAULT_MOCK_MODEL_ID = "mock"


class ModelGateway:
    def __init__(
        self,
        configs: dict[str, ModelConfig] | None = None,
        *,
        secret_resolver: Callable[[str], str | None] | None = None,
        default_model_id: str = DEFAULT_MOCK_MODEL_ID,
    ) -> None:
        self._configs: dict[str, ModelConfig] = dict(configs or {})
        self._configs.setdefault(
            DEFAULT_MOCK_MODEL_ID,
            ModelConfig(id=DEFAULT_MOCK_MODEL_ID, provider="mock", model="mock-1"),
        )
        self._default_model_id = default_model_id
        self._mock = MockLLM()
        self._litellm = LiteLLMProvider(secret_resolver=secret_resolver)
        self._mock_embedding: EmbeddingProvider = MockEmbedding()
        self._litellm_embedding: EmbeddingProvider = LiteLLMEmbedding(secret_resolver=secret_resolver)

    def register(self, config: ModelConfig) -> None:
        self._configs[config.id] = config

    def resolve(self, model_id: str) -> ModelConfig:
        if model_id in ("default", "", None):
            model_id = self._default_model_id
        config = self._configs.get(model_id)
        if config is None:
            raise ModelGatewayError(
                f"Model '{model_id}' is not configured. Configure it under Settings -> Models."
            )
        return config

    def _provider_for(self, config: ModelConfig) -> ModelProvider:
        return self._mock if config.provider == "mock" else self._litellm

    async def complete(
        self,
        model_id: str,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        config = self.resolve(model_id)
        provider = self._provider_for(config)
        return await provider.complete(config, messages, temperature=temperature, max_tokens=max_tokens)

    async def embed(self, model_id: str | None, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not model_id or model_id in ("default", "mock"):
            config = self.resolve(DEFAULT_MOCK_MODEL_ID)
            return await self._mock_embedding.embed(config, texts)
        config = self.resolve(model_id)
        provider = self._mock_embedding if config.provider == "mock" else self._litellm_embedding
        return await provider.embed(config, texts)
