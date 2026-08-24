# ADR-008: When to Introduce Temporal

**Status:** Accepted (deferred implementation)

## Context

Spec section 7 explicitly says not to require Temporal for the MVP, but to design interfaces so it
can be introduced later for scheduled workflows, large evaluations, deployments, batch processing,
and other durable/retryable orchestration.

## Decision

MVP execution runs synchronously within the HTTP request that triggers it (`POST
/flows/{id}/runs` streams the run to completion or to a pause point in the same request/response
cycle), backed by LangGraph's own checkpointing for human-approval durability - no external job
queue or workflow engine. This is sufficient because MVP runs are short-lived and interactive.

**Introduce Temporal when any of these becomes true:**

- Evaluation runs need to execute hundreds/thousands of test cases as a batch job that must
  survive API restarts and report progress incrementally (Phase 5+).
- Scheduled/recurring flow execution is needed (cron-triggered runs) rather than purely
  user-triggered.
- A run needs to survive the *initiating* API replica going down mid-execution - LangGraph's
  Postgres checkpointer already gives Human-Approval-pause durability, but an actively-executing
  run today still depends on the process that started it staying alive between checkpoints.
- Deployment pipelines (Agent CI/CD, spec section 37) need durable, retryable, multi-step
  orchestration (evaluate → quality gate → security check → deploy) with visibility into
  in-progress steps.

## Consequences

Until one of the above triggers, adding Temporal would be unused infrastructure. When it's
introduced, `WorkflowRuntime` and `RunExecutionService` are the seams: a Temporal-backed
implementation should be addable without changing FlowSpec, the FastAPI routes, or the frontend's
SSE contract for the interactive case.
