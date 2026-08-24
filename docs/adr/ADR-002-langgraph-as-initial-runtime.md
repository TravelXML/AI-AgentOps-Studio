# ADR-002: LangGraph as the Initial Runtime

**Status:** Accepted

## Context

The MVP needs one working execution engine, not a framework-agnostic execution layer built before
anything has actually run. Candidates considered: LangGraph, CrewAI, a hand-rolled state machine.

## Decision

Use LangGraph for MVP execution, wrapped behind the `WorkflowRuntime` interface
(`packages/runtime/src/agentq_runtime/base.py`). Use its native capabilities directly rather
than re-implementing them: checkpointing, `interrupt()`/`Command(resume=...)` for human-in-the-loop,
conditional edges for routing, and `stream_mode="updates"` for node-level event streaming.

## Consequences

- Human Approval got a *real* pause/resume backed by durable state almost for free, instead of a
  bespoke, likely-buggier state machine.
- LangGraph's API moves fast between versions; `packages/runtime` isolates that churn behind
  `WorkflowRuntime` so the rest of the platform doesn't feel every LangGraph upgrade.
- A LangGraph-specific quirk (code before `interrupt()` re-runs on resume) is now the platform's
  problem to manage - documented in `docs/architecture/execution-engine.md` rather than hidden.
