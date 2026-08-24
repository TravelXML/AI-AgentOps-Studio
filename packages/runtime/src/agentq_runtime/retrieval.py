"""Retrieval/memory service contracts the runtime calls at execution time. Concrete
implementations live in `apps/api` (backed by Postgres + pgvector) - the runtime package stays
framework-neutral and only depends on these Protocols, the same separation `ToolRegistry` and
`ModelGateway` already keep."""

from __future__ import annotations

from typing import Protocol


class RetrievalError(RuntimeError):
    pass


class MemoryServiceError(RuntimeError):
    pass


class RetrievedChunk:
    def __init__(self, content: str, score: float, document_name: str) -> None:
        self.content = content
        self.score = score
        self.document_name = document_name


class RetrievalService(Protocol):
    async def retrieve(
        self, knowledge_base_id: str, query: str, *, top_k: int, min_score: float, embedding_model: str | None
    ) -> list[RetrievedChunk]: ...


class MemoryService(Protocol):
    async def remember_and_recall_conversation(
        self, memory_key: str, role: str, content: str, *, ttl_seconds: int | None
    ) -> str:
        """Appends one turn and returns the formatted conversation so far."""
        ...

    async def remember_and_recall_semantic(
        self, memory_key: str, content: str, *, embedding_model: str | None, ttl_seconds: int | None
    ) -> str:
        """Stores `content` as a fact and returns the top relevant facts (including it) as text."""
        ...
