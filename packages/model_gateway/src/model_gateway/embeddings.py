"""Embedding providers, mirroring the chat completion provider split: a zero-network MockEmbedding
so RAG/Memory work with no API key, and a LiteLLM-backed provider for real embedding models.

A fixed vector dimension (EMBEDDING_DIM) is required because pgvector columns are fixed-width.
Real providers are asked to truncate to it via LiteLLM's `dimensions` kwarg (supported by OpenAI's
text-embedding-3-* and Gemini's embedding models) - not every provider honors this, which is a
known, documented scope limit for this phase rather than a silent correctness bug.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Protocol

import litellm

from model_gateway.types import ModelConfig, ModelGatewayError

EMBEDDING_DIM = 384


class EmbeddingProvider(Protocol):
    async def embed(self, config: ModelConfig, texts: list[str]) -> list[list[float]]: ...


def _hash_vector(text: str) -> list[float]:
    """A stable, deterministic pseudo-embedding derived from the text's SHA-256 hash - not
    semantically meaningful (no notion of synonymy), but identical/near-duplicate text always
    lands at the same point, which is enough for the pipeline (chunk, store, cosine search,
    retrieve) to run and be tested end-to-end without any network call or API key."""
    values: list[float] = []
    counter = 0
    while len(values) < EMBEDDING_DIM:
        digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        values.extend(b / 127.5 - 1.0 for b in digest)
        counter += 1
    values = values[:EMBEDDING_DIM]
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


class MockEmbedding:
    async def embed(self, config: ModelConfig, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(t) for t in texts]


class LiteLLMEmbedding:
    def __init__(self, secret_resolver: Callable[[str], str | None] | None = None) -> None:
        self._secret_resolver = secret_resolver or (lambda _secret_id: None)

    async def embed(self, config: ModelConfig, texts: list[str]) -> list[list[float]]:
        api_key = self._secret_resolver(config.secret_id) if config.secret_id else None
        try:
            response = await litellm.aembedding(
                model=config.model,
                input=texts,
                api_key=api_key,
                api_base=config.base_url,
                dimensions=EMBEDDING_DIM,
                timeout=config.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - normalize every provider failure
            raise ModelGatewayError(f"embedding call failed for '{config.id}': {exc}") from exc

        vectors = [item["embedding"] for item in response.data]
        # Providers that ignore `dimensions` return their native width - pad/truncate so every
        # row written to the fixed-width pgvector column is well-formed rather than erroring.
        return [_fit_dim(v) for v in vectors]


def _fit_dim(vector: list[float]) -> list[float]:
    if len(vector) == EMBEDDING_DIM:
        return vector
    if len(vector) > EMBEDDING_DIM:
        return vector[:EMBEDDING_DIM]
    return vector + [0.0] * (EMBEDDING_DIM - len(vector))
