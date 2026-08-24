# ADR-004: PostgreSQL + pgvector

**Status:** Accepted

## Context

The platform needs one relational store for flows/runs/audit data *and* a vector store for RAG
(Phase 4) and semantic memory (Phase 4). Running two separate database systems locally adds
operational cost the MVP doesn't need to pay.

## Decision

Use PostgreSQL with the `pgvector` extension for everything: relational tables via SQLAlchemy 2
(async) + Alembic, and (in Phase 4) `document_chunks`/embedding columns via `pgvector`. LangGraph's
checkpointer also targets the same Postgres instance (`AsyncPostgresSaver`), so a single
`docker compose up -d postgres` covers app data, checkpoints, and (later) vectors.

## Consequences

- One database to run, back up, and reason about locally and in the initial deployment story.
- `pgvector` is adequate for MVP-scale RAG; a dedicated vector database is explicitly deferred
  (spec section 72) until there's a demonstrated scale need.
- JSONB is used deliberately (FlowSpec snapshots, run inputs/outputs/tool arguments) where the
  shape is genuinely dynamic, not as a substitute for relational modeling - see the `runs` /
  `run_steps` / `run_events` schema for the boundary (spec section 43).
