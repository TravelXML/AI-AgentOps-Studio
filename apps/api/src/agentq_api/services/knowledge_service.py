"""Knowledge base ingestion + retrieval (Phase 4 RAG): naive fixed-size chunking, embeds each
chunk through the same ModelGateway every chat node uses, stores vectors in pgvector, and
retrieves by cosine similarity (`<=>` operator). `PgVectorRetrievalService` is the concrete
implementation of `agentq_runtime.RetrievalService` the RAG node calls at execution time.
"""

from __future__ import annotations

import io
import uuid

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.base import get_session_factory
from agentq_api.db.models import Document, DocumentChunk, KnowledgeBase
from agentq_api.schemas.errors import ApiError
from agentq_runtime import RetrievalError, RetrievedChunk
from model_gateway import ModelGateway

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def chunk_text(text: str, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def extract_text(filename: str, raw: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8", errors="replace")


class KnowledgeService:
    def __init__(self, session: AsyncSession, gateway: ModelGateway) -> None:
        self._session = session
        self._gateway = gateway

    async def list_knowledge_bases(self, workspace_id: uuid.UUID) -> list[KnowledgeBase]:
        result = await self._session.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.workspace_id == workspace_id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_knowledge_base(
        self, workspace_id: uuid.UUID, name: str, description: str
    ) -> KnowledgeBase:
        kb = KnowledgeBase(workspace_id=workspace_id, name=name, description=description)
        self._session.add(kb)
        await self._session.commit()
        await self._session.refresh(kb)
        return kb

    async def get_knowledge_base(self, workspace_id: uuid.UUID, kb_id: uuid.UUID) -> KnowledgeBase:
        result = await self._session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.workspace_id == workspace_id)
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise ApiError(404, "KNOWLEDGE_BASE_NOT_FOUND", f"Knowledge base '{kb_id}' was not found.")
        return kb

    async def ingest_document(
        self, kb: KnowledgeBase, name: str, text: str, *, embedding_model: str | None
    ) -> Document:
        document = Document(knowledge_base_id=kb.id, name=name, status="processing")
        self._session.add(document)
        await self._session.flush()

        pieces = chunk_text(text)
        if not pieces:
            document.status = "failed"
            document.error = "Document had no extractable text."
            await self._session.commit()
            await self._session.refresh(document)
            return document

        try:
            vectors = await self._gateway.embed(embedding_model, pieces)
        except Exception as exc:  # noqa: BLE001 - normalize every embedding provider failure
            document.status = "failed"
            document.error = str(exc)
            await self._session.commit()
            await self._session.refresh(document)
            return document

        for ordinal, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            self._session.add(
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=kb.id,
                    ordinal=ordinal,
                    content=piece,
                    embedding=vector,
                )
            )
        document.status = "ready"
        document.chunk_count = len(pieces)
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def list_documents(self, kb_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(Document).where(Document.knowledge_base_id == kb_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())


class PgVectorRetrievalService:
    """Runs during flow execution, inside LangGraph's background task (`langgraph_runtime.py`
    drives the graph via `asyncio.create_task` while the request's own session is concurrently
    used to persist events) - reusing the request-scoped `AsyncSession` here races with that and
    raises "concurrent operations are not permitted". Opens its own short-lived session per call
    instead, the standard SQLAlchemy async pattern for a unit of work off the request's task."""

    def __init__(self, gateway: ModelGateway) -> None:
        self._gateway = gateway

    async def retrieve(
        self,
        knowledge_base_id: str,
        query: str,
        *,
        top_k: int,
        min_score: float,
        embedding_model: str | None,
    ) -> list[RetrievedChunk]:
        try:
            kb_uuid = uuid.UUID(knowledge_base_id)
        except ValueError as exc:
            raise RetrievalError(f"'{knowledge_base_id}' is not a valid knowledge base id.") from exc

        try:
            [query_vector] = await self._gateway.embed(embedding_model, [query])
        except Exception as exc:  # noqa: BLE001 - normalize every embedding provider failure
            raise RetrievalError(f"could not embed query: {exc}") from exc

        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(DocumentChunk, Document.name, (1 - distance).label("score"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.knowledge_base_id == kb_uuid)
            .order_by(distance)
            .limit(top_k)
        )
        async with get_session_factory()() as session:
            result = await session.execute(stmt)
            rows = result.all()
        return [
            RetrievedChunk(content=chunk.content, score=float(score), document_name=doc_name)
            for chunk, doc_name, score in rows
            if score >= min_score
        ]
