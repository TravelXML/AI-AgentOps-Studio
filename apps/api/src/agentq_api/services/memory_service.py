"""Conversation + semantic memory (Phase 4): implements the runtime's `MemoryService` Protocol
against Postgres. Conversation memory appends one turn and replays the scoped transcript back;
semantic memory embeds and stores a fact, then retrieves the most relevant facts in that scope via
pgvector cosine search - the same retrieval mechanism RAG uses, just scoped to memory entries
instead of a knowledge base's document chunks.

Runs during flow execution, inside LangGraph's background task (`langgraph_runtime.py` drives the
graph via `asyncio.create_task` while the request's own session is concurrently used to persist
events) - reusing the request-scoped `AsyncSession` here races with that and raises "concurrent
operations are not permitted". Each method opens its own short-lived session instead, the standard
SQLAlchemy async pattern for a unit of work off the request's task.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from agentq_api.db.base import get_session_factory
from agentq_api.db.models import MemoryEntry
from agentq_runtime import MemoryServiceError
from model_gateway import ModelGateway

CONVERSATION_HISTORY_LIMIT = 20
SEMANTIC_RECALL_TOP_K = 5


class PgVectorMemoryService:
    def __init__(self, workspace_id: uuid.UUID, gateway: ModelGateway) -> None:
        self._workspace_id = workspace_id
        self._gateway = gateway

    def _expiry(self, ttl_seconds: int | None) -> datetime | None:
        if ttl_seconds is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    async def remember_and_recall_conversation(
        self, memory_key: str, role: str, content: str, *, ttl_seconds: int | None
    ) -> str:
        entry = MemoryEntry(
            workspace_id=self._workspace_id,
            memory_key=memory_key,
            role=role,
            content=content,
            expires_at=self._expiry(ttl_seconds),
        )
        now = datetime.now(UTC)
        async with get_session_factory()() as session:
            session.add(entry)
            await session.flush()

            result = await session.execute(
                select(MemoryEntry)
                .where(
                    MemoryEntry.workspace_id == self._workspace_id,
                    MemoryEntry.memory_key == memory_key,
                    MemoryEntry.role != "fact",
                )
                .order_by(MemoryEntry.created_at.desc())
                .limit(CONVERSATION_HISTORY_LIMIT)
            )
            rows = list(reversed(result.scalars().all()))
            await session.commit()

        rows = [r for r in rows if r.expires_at is None or r.expires_at > now]
        return "\n".join(f"{r.role}: {r.content}" for r in rows)

    async def remember_and_recall_semantic(
        self, memory_key: str, content: str, *, embedding_model: str | None, ttl_seconds: int | None
    ) -> str:
        try:
            [vector] = await self._gateway.embed(embedding_model, [content])
        except Exception as exc:  # noqa: BLE001 - normalize every embedding provider failure
            raise MemoryServiceError(f"could not embed memory content: {exc}") from exc

        entry = MemoryEntry(
            workspace_id=self._workspace_id,
            memory_key=memory_key,
            role="fact",
            content=content,
            embedding=vector,
            expires_at=self._expiry(ttl_seconds),
        )
        now = datetime.now(UTC)
        distance = MemoryEntry.embedding.cosine_distance(vector)
        stmt = (
            select(MemoryEntry, (1 - distance).label("score"))
            .where(
                MemoryEntry.workspace_id == self._workspace_id,
                MemoryEntry.memory_key == memory_key,
                MemoryEntry.role == "fact",
                MemoryEntry.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(SEMANTIC_RECALL_TOP_K)
        )
        async with get_session_factory()() as session:
            session.add(entry)
            await session.flush()
            result = await session.execute(stmt)
            rows = result.all()
            await session.commit()

        rows = [(r, score) for r, score in rows if r.expires_at is None or r.expires_at > now]
        if not rows:
            return content
        return "\n".join(f"- {r.content}" for r, _ in rows)
