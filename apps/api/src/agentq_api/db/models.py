"""SQLAlchemy models (spec section 43). Every resource-bearing table carries a `workspace_id`
even though MVP auth is single-workspace-dev-mode - multi-tenancy must never be retrofitted."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentq_api.db.base import Base
from model_gateway import EMBEDDING_DIM


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    denied_tools: Mapped[list[str]] = mapped_column(JSONB, default=list)


class WorkspaceMember(TimestampMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="owner")  # owner|admin|developer|viewer


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000), default="")

    flows: Mapped[list[Flow]] = relationship(back_populates="project")


class Flow(TimestampMixin, Base):
    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|published|archived
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("flow_versions.id", use_alter=True, name="fk_flow_latest_version"), nullable=True
    )

    project: Mapped[Project] = relationship(back_populates="flows")
    versions: Mapped[list[FlowVersion]] = relationship(
        back_populates="flow",
        foreign_keys="FlowVersion.flow_id",
        order_by="FlowVersion.version",
        lazy="selectin",
    )


class FlowVersion(TimestampMixin, Base):
    __tablename__ = "flow_versions"
    __table_args__ = (UniqueConstraint("flow_id", "version", name="uq_flow_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flows.id"), index=True)
    version: Mapped[int] = mapped_column()
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    flow: Mapped[Flow] = relationship(back_populates="versions", foreign_keys=[flow_id])


class Run(TimestampMixin, Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flows.id"), index=True)
    flow_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flow_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replayed_from_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id"), nullable=True)

    steps: Mapped[list[RunStep]] = relationship(
        back_populates="run", order_by="RunStep.started_at", lazy="selectin"
    )
    events: Mapped[list[RunEvent]] = relationship(
        back_populates="run", order_by="RunEvent.created_at", lazy="selectin"
    )


class RunStep(Base):
    __tablename__ = "run_steps"
    __table_args__ = (Index("ix_run_steps_run_id_node_id", "run_id", "node_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(255))
    node_type: Mapped[str] = mapped_column(String(64))
    parent_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("run_steps.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(default=0.0)
    tool_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_arguments: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    routing_decision: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    input_data: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    run: Mapped[Run] = relationship(back_populates="steps")


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_events_run_id_created_at", "run_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), index=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("run_steps.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(64))
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[Run] = relationship(back_populates="events")


class ModelConfigRow(TimestampMixin, Base):
    __tablename__ = "model_configs"
    __table_args__ = (UniqueConstraint("workspace_id", "model_key", name="uq_model_config_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    model_key: Mapped[str] = mapped_column(String(255))  # the id agents reference, e.g. "default"
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    secret_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("secrets.id"), nullable=True)
    temperature_default: Mapped[float] = mapped_column(default=0.2)
    timeout_seconds: Mapped[float] = mapped_column(default=60.0)
    max_retries: Mapped[int] = mapped_column(default=2)


class Secret(TimestampMixin, Base):
    __tablename__ = "secrets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    ciphertext: Mapped[bytes] = mapped_column()


class KnowledgeBase(TimestampMixin, Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000), default="")

    documents: Mapped[list[Document]] = relationship(back_populates="knowledge_base", lazy="selectin")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default="processing")  # processing|ready|failed
    chunk_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_document_chunks_kb_id", "knowledge_base_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id"))
    ordinal: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(String(8000))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    __table_args__ = (Index("ix_memory_entries_workspace_key", "workspace_id", "memory_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    memory_key: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(32))  # user|assistant|fact
    content: Mapped[str] = mapped_column(String(8000))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class McpServer(TimestampMixin, Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000))
    secret_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("secrets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown")  # unknown|connected|error
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000), default="")

    test_cases: Mapped[list[TestCase]] = relationship(back_populates="dataset", lazy="selectin")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"), index=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    expected_output: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped[Dataset] = relationship(back_populates="test_cases")


class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flows.id"), index=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"), index=True)
    evaluators: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|completed|failed
    total_cases: Mapped[int] = mapped_column(default=0)
    passed_cases: Mapped[int] = mapped_column(default=0)

    results: Mapped[list[EvaluationResult]] = relationship(back_populates="evaluation_run", lazy="selectin")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    passed: Mapped[bool] = mapped_column(default=False)
    evaluator_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    actual_output: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evaluation_run: Mapped[EvaluationRun] = relationship(back_populates="results")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(128))
    resource_id: Mapped[str] = mapped_column(String(255))
    audit_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
