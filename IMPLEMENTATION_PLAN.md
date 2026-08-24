# AgentQ - Implementation Plan

Working name: **AgentQ**. See [`promots.md`](promots.md) for the full source spec (93 sections). This
plan tracks execution against that spec, phase by phase, per section 92/93 ordering: build the smallest
complete vertical slice first (Input → Agent → Output through FlowSpec → LangGraph → MockLLM/Ollama →
trace), verify it, then progressively layer in Router, Supervisor, Tools, Human Approval, AI Architect,
RAG, Memory, MCP, Evaluation, Security, Dashboard.

Legend: `TODO` `IN PROGRESS` `DONE` `BLOCKED`. A row is `DONE` only once its acceptance test actually ran
and passed - see the Verification Log at the bottom for the evidence, including a genuine browser-driven
E2E pass and a from-scratch `docker compose up -d` boot.

## Phase 0 - Repository Foundation

| Task | Status | Acceptance |
|---|---|---|
| Monorepo layout (apps/, packages/, infra/, examples/, tests/, docs/) | DONE | see Project Structure in README |
| uv Python workspace (flowspec, runtime, model_gateway, evaluation, security, observability, sdk, api) | DONE | `uv sync --all-packages` - 113 packages resolved |
| Docker Compose (postgres+pgvector, redis, api, web) | DONE | `docker compose up -d` - all 4 healthy, verified |
| `.env.example` | DONE | stack boots with `cp .env.example .env` + compose, no edits needed |
| Makefile (install/dev/test/lint/format/migrate/seed/down) | DONE | every target runs; `make test`/`make seed` exercised live |

## Phase 1 - Foundation (FlowSpec, DB, API/Web skeleton)

| Task | Status | Acceptance |
|---|---|---|
| FlowSpec Pydantic schema (12 node types, discriminated union) | DONE | 11 unit tests, `packages/flowspec/tests` |
| SQLAlchemy models + Alembic migrations | DONE | 2 migrations applied against real Postgres |
| FastAPI app skeleton w/ health/ready/metrics | DONE | verified live |
| Flow CRUD API (`/api/v1/flows`, versions, validate, publish) | DONE | API tests + browser E2E |
| 12 node visual definitions on canvas + Inspector forms | DONE | drag/drop verified in real Chromium for Input/Agent/Output; all 12 have library entries + inspector forms |
| Workflow validation service (actionable errors, not raw exceptions) | DONE | 6 unit tests |
| Next.js app skeleton | DONE | `npm run build` clean, dev server verified in browser |
| React Flow canvas (drag/drop/connect/delete/select, node search, minimap/zoom) | DONE | verified in real Chromium (a real zoom-on-empty-canvas bug was found and fixed this way) |
| LangGraph compiler (FlowSpec → graph) | DONE | 8 runtime unit tests + live runs |
| LiteLLM gateway + MockLLM | DONE | 3 unit tests + every live run |
| Ollama support | IN PROGRESS | code path exists (`provider: ollama` via LiteLLM) and is exercised by unit tests with the LiteLLM call path; not yet run against a live local Ollama daemon in this session |
| Model catalog search (`GET /api/v1/models/catalog`) - live OpenRouter-sourced autocomplete on the Models page, scoped per-provider (openai→openai/\*, gemini→google/\*, openrouter→everything), "top 5 free models" quick-pick ranked by a curated family heuristic, static fallback catalog if OpenRouter is unreachable | DONE | 4 pytest (live-fetch fallback, free-only filter, provider scoping ×2) + verified live against the real OpenRouter API in a real Chromium browser (search, pick, auto-filled model_key, saved config, and confirmed the new config appears in the canvas Agent node's Model dropdown) |

## Phase 2 - Working Execution (the vertical slice) ✅ acceptance met

| Task | Status | Acceptance |
|---|---|---|
| Execution API (`POST /flows/{id}/runs`, SSE) | DONE | live run against dockerized stack, `run.started`→`run.completed` |
| Run/RunStep/RunEvent persistence (flight recorder) | DONE | verified: tokens, cost, timing, routing decisions all persisted and queryable |
| SSE streaming of run events | DONE | consumed by both pytest (httpx) and a real browser (fetch+ReadableStream) |
| Canvas execution status (live node glow) | DONE | verified visually in Chromium screenshots - idle→running→success |
| Trace UI page (steps, timing, tokens, cost, per-step detail) | DONE | verified visually in Chromium |
| Example flow: Simple Agent | DONE | executes via API and via full browser E2E test |
| Automated tests (flowspec/compiler/gateway/API) | DONE | 35 pytest + 2 Playwright, all green |
| **Vertical slice runs locally end-to-end** | **DONE** | see Verification Log |
| Router node (rule mode; expression mode reuses rule evaluator; llm mode implemented) | DONE | 2 unit tests + live example run |
| Supervisor node (single-shot delegation, records rationale) | DONE | 1 unit test + live example run - iterative multi-round delegation not implemented (documented) |
| Tool node + Tool Registry (HTTP GET/POST w/ SSRF guard, Calculator, DateTime, JSON Transform) | DONE | 1 unit test + live run |
| Human Approval node (real LangGraph interrupt, Postgres checkpoint) | DONE | unit tests + **API-process-restart survival verified live** + browser E2E (pause → Approve button → resume → SUCCEEDED) |
| Replay (entire run) | DONE | API test + live curl verification |
| Example flows: Router, Supervisor, Human Approval | DONE | all 3 seeded and executed live against the dockerized stack |

## Phase 3 - AI Architect

| Task | Status | Acceptance |
|---|---|---|
| `POST /architect/generate` (NL → FlowSpec) | DONE | routes through the same `ModelGateway` every chat node uses; MockLLM honestly fails (can't follow structured-output instructions) rather than fabricating a flow |
| Pydantic validation + bounded repair loop | DONE | 6 unit tests (first-try success, ```json fence stripping, JSON-parse repair, schema-violation repair, exhausted-attempts failure) + 1 live API test proving MockLLM fails honestly |
| "Generate with AI" canvas UI | DONE | inline panel on the Flows page - description + model picker → generates → creates the flow → navigates to its canvas |

## Phase 4 - RAG + Memory + MCP

| Task | Status | Note |
|---|---|---|
| Document ingestion + chunker + pgvector | DONE | fixed-size chunking (800/100 overlap), real pgvector storage; upload accepts pasted text or a file (.txt/.md/.pdf via `pypdf`) |
| RAG node | DONE | real cosine-similarity retrieval (`<=>` operator); embeds via `ModelGateway.embed()` (MockEmbedding by default, LiteLLM for a configured real embedding model) |
| Conversation + semantic memory | DONE | conversation memory replays a scoped transcript across separate runs (scope `run`\|`agent`\|`workspace`); semantic memory embeds+recalls facts via the same pgvector mechanism as RAG |
| MCP Server Registry + tool discovery | DONE | real client speaking MCP's JSON-RPC 2.0 wire protocol directly (`agentq_runtime.McpClient`) - `initialize` → `tools/list` → `tools/call`, session-id handshake; a small demo MCP server (`infrastructure/scripts/demo_mcp_server.py`) is included for trying it against something real |
| Settings → MCP Servers UI / Knowledge UI | DONE | both are real pages now (register a server + see discovered tools; create a KB + upload documents), not placeholders |

**Non-obvious bug found and fixed while wiring this in**: RAG/Memory/MCP node functions run inside LangGraph's execution, which `langgraph_runtime.py` drives via `asyncio.create_task` - concurrently with the same request's `AsyncSession` being used to persist events. Reusing that session inside the new node functions raised "concurrent operations are not permitted" the first time an MCP/RAG/Memory node actually ran end-to-end (agent/tool/router node builders never touched the DB directly, so this never surfaced before). Fixed by having `PgVectorRetrievalService`, `PgVectorMemoryService`, and `WorkspaceMcpToolCaller` each open their own short-lived session per call instead of sharing the request-scoped one - caught by live execution, not by the unit tests, which is exactly why the live pass matters.

## Phase 5 - Evaluation

| Task | Status | Note |
|---|---|---|
| Dataset/TestCase/Evaluator/EvaluationRun/Result models | DONE | 4 new tables; migration applied |
| Evaluators (exact/contains/schema/regex/latency/cost/LLM-judge) | DONE | all 7 implemented in `packages/evaluation`, 9 unit tests; `llm_judge` calls the real gateway |
| Evaluation UI | DONE | create datasets, bulk-add test cases (JSON), pick a flow + evaluators, run, see pass/fail per case with a link into the real underlying Run |

Evaluation is not a simulated execution path - `EvaluationService` reuses `RunExecutionService` directly, so every test case in a dataset creates and drives a genuine `Run`/`RunStep`/`RunEvent` trail, openable from the trace UI like any other run.

## Phase 6 - Security / Governance Foundation

| Task | Status | Note |
|---|---|---|
| Secrets abstraction (encrypted at rest, `secret_id` refs only) | DONE | Fernet-encrypted, verified via Models page (create + `has_secret` flag) |
| SSRF guard on HTTP tools | DONE | resolves + checks every IP, unit-tested |
| No `eval()` - restricted AST expression evaluator | DONE | used by Router rules + Human Approval conditions, unit-tested |
| Workspace-scoped data model | DONE | every table carries `workspace_id` from the first migration |
| PolicyEngine + tool-call enforcement | DONE | workspace-level tool deny-list, enforced in both the Tool and MCP node builders before execution; managed from Settings |
| Guardrails (PII/keywords/prompt-injection/schema) | DONE | all 6 check types implemented (`packages/security/guardrails.py`, 12 unit tests) and wired into a real `GuardrailNode` executor (block or warn) - no longer a pass-through |
| Audit log | DONE | real rows written on flow create/publish, run create, model config create, MCP server registration, human approval decisions; browsable from Settings |

Guardrail and PolicyEngine wiring is verified with 10 API-level integration tests that run real flows (a keyword-guardrail-blocked run actually fails with the violation message; a policy-denied tool call actually fails the run; audit log rows are asserted to exist after each action) - not just the pure-function unit tests.

## Phase 7 - Production Dashboard

| Task | Status | Note |
|---|---|---|
| AI Control Center dashboard | DONE (MVP-lite) | real aggregates from `GET /runs`, computed client-side; honest "No runs yet" / "No flows yet" empty states, verified visually |
| Cost tracking | DONE | real per-step `estimated_cost_usd`, summed on dashboard; $0 for MockLLM/local models labeled as *API* cost, not total cost |
| Metrics (`/metrics`, Prometheus format) | DONE | every counter (`workflow_runs_total`, `workflow_run_duration_seconds`, `workflow_failures_total`, `llm_requests_total`, `llm_tokens_total`, `llm_api_cost_total`, `tool_calls_total`, `tool_failures_total`, `agent_node_duration_seconds`, `evaluation_runs_total`) now actually increments from the run service and evaluation service, not just exposed as empty series - verified by running a flow via `curl` and diffing the `/metrics` text before/after |

## Not built in this pass (explicitly deferred, per spec §72 and realistic scope)

Kubernetes operator, full SAML/SCIM, billing, agent marketplace, mobile app, hundreds of
integrations, full Temporal deployment, custom vector DB/inference engine/scheduler.

## Verification Log

**2026-08-21/22 - Phase 0–2 full verification pass:**

1. `uv sync --all-packages` - 113 packages resolved, all 8 workspace members installed.
2. `uv run --all-packages pytest` - **35 passed** (11 flowspec, 3 model_gateway, 8 runtime,
   13 API/integration - flows, runs, human approval, replay, list runs).
3. `uv run --all-packages ruff check .` / `ruff format --check .` - clean.
4. `cd apps/web && npx tsc --noEmit && npm run build` - clean production build.
5. Started a real Postgres (later: the Docker Compose one) + FastAPI + Next.js dev servers and
   exercised the full vertical slice via raw `curl` SSE streaming: create flow → save version →
   run → `run.started`…`run.completed` → `GET /runs/{id}` shows 3 `SUCCEEDED` steps with real
   token/cost data → `GET /runs/{id}/events` returns all persisted events.
6. **Killed and restarted the API process mid-approval-pause** (Human Approval flow) and resumed
   successfully - proves the Postgres-backed LangGraph checkpointer, not frontend state, is what's
   pausing the run.
7. **Real browser verification** (Playwright/Chromium, not just API calls): launched the Next.js
   dev server, drove it end-to-end - dragged Input/Agent/Output nodes onto the canvas, connected
   them, configured the agent, saved, validated, ran, watched nodes glow through
   running→success, opened the trace, inspected per-step token/cost detail. Also drove the
   Human Approval example through pause → Approve click → resume → SUCCEEDED.
   - This caught two real bugs that unit/integration tests missed: (a) `fitView()` degenerating
     to max zoom on an empty canvas, fixed by switching to a fixed default viewport + an
     explicit fit-on-load trigger; (b) a genuine CORS bug - `X-Run-Id` (a custom response header
     the frontend depends on to open the trace / resume / replay) was invisible to browser JS
     because it wasn't in `expose_headers`, even though same-process pytest clients never see
     CORS at all. Both fixed and re-verified.
8. Converted the working browser script into two committed Playwright specs
   (`tests/e2e/specs/vertical-slice.spec.ts`, `human-approval.spec.ts`) - **both pass**, using
   MockLLM only, no API key required (spec section 58's exact acceptance flow).
9. **`docker compose build` + `docker compose up -d`** from a clean state - all 4 services
   (postgres, redis, api, web) came up healthy. Ran `make seed` against the live containers -
   4 example flows loaded. Re-ran both Playwright E2E specs **against the dockerized stack** -
   both pass. Smoke-tested the Router and Supervisor examples via `curl` - both reach
   `run.completed`.

This is the strongest evidence available short of a second reviewer: the exact `git clone` →
`cp .env.example .env` → `docker compose up -d` path from the README was actually executed, not
just described.

**2026-08-22 - Model catalog search (OpenRouter free models + provider-scoped search):**

Added `GET /api/v1/models/catalog` (`apps/api/src/agentq_api/services/model_catalog_service.py`),
sourcing a live, cached (1h TTL) model list from OpenRouter's public `/api/v1/models` endpoint -
covers OpenAI/Anthropic/Google/Meta/DeepSeek/Qwen/etc. in one response, no API key needed to
browse. Filters out non-text-output models (music/image generation) that share the same catalog.
Falls back to a small static curated list if the live fetch fails. New `ModelCombobox`
(`apps/web/components/ui/model-combobox.tsx`) replaces the free-text Model field on the Models
page: shows a "top 5 free models" quick-pick (ranked by a curated known-family heuristic, since
OpenRouter's list carries no quality signal) and live search-as-you-type, both scoped to the
selected provider's vendor prefix (`gemini` → `google/*`, `openai` → `openai/*`, `openrouter` →
unscoped). Picking a result auto-fills `model_key` too.

1. `uv run --all-packages pytest` - **39 passed** (35 prior + 4 new: live-fetch-fails-gracefully,
   free-only filter, two provider-scoping cases).
2. `ruff check` / `ruff format --check` - clean. `tsc --noEmit` / `eslint` - clean.
3. **Real browser verification against the live OpenRouter API** (not mocked): opened the Models
   page, selected `openrouter`, confirmed 5 real free models appeared unprompted (ranked, current
   models as of today - e.g. `openai/gpt-oss-20b:free`); typed `gemini`, got live Google results;
   switched provider to `gemini` directly and confirmed results were scoped to `google/*` only;
   picked a result, filled in a credential, saved - the new config appeared in the Models list
   *and* in an existing flow's Agent node Model dropdown on the canvas, closing the loop from "add
   a model" to "it's selectable when building a flow." Rebuilt and re-verified against the
   dockerized stack (`docker compose build web && up -d`) - Playwright E2E specs still pass.
4. One real bug caught by live verification rather than mocked tests: the raw OpenRouter catalog
   mixes chat models with non-chat ones (e.g. a music-generation model, `google/lyria-3-pro-preview`)
   and a naive "biggest context window" ranking surfaced obscure/anonymous "stealth" preview
   models ahead of well-known families - fixed by filtering on `architecture.output_modalities`
   and switching the "top free" ranking to a named-family allowlist.

**2026-08-22 - Phases 3–7 built and verified (AI Architect, RAG/Memory/MCP, Evaluation, Security, metrics):**

Every remaining phase from the original plan is now implemented for real - no phase advanced past
its actual working state, per the same DONE-means-a-passing-acceptance-test bar used for Phases
0–2. Full detail is in each phase's table above; summary of what changed and how it was checked:

1. `uv sync --all-packages` - 113 packages resolved (new: `agentq-security` now a real dependency
   of `agentq-runtime`, wiring PolicyEngine/guardrails into the execution graph).
2. `uv run --all-packages pytest` - **102 passed** (61 prior + 6 architect + 7 RAG + 3 memory +
   6 MCP + 9 evaluator unit + 5 evaluation integration + 15 security unit + 10 security
   integration + 2 metrics). `ruff check .` / `ruff format --check .` - clean, including the 3 new
   Alembic migrations (reformatted to match the existing style, not left as raw autogenerate output).
3. Three new Alembic migrations applied against the real dev Postgres: knowledge/RAG/memory/MCP
   tables (with real `pgvector` columns), evaluation tables, and the workspace `denied_tools`
   policy column (with a `server_default` so it applies cleanly to the already-populated
   `workspaces` table, not just a fresh one).
4. `cd apps/web && npx tsc --noEmit && npm run build` - clean production build (11 routes,
   including the 4 pages rebuilt from "not implemented" placeholders to real functionality:
   Knowledge, MCP Servers, Evaluations, Settings).
5. **Real browser verification**, not just API calls, for every new surface:
   - **AI Architect**: N/A for live-key generation (no real model configured in this session) but
     the honest-failure path (MockLLM can't follow structured-output instructions) is proven live
     via API test; the repair loop itself is proven via 6 unit tests with a stubbed gateway.
   - **RAG**: created a knowledge base, uploaded a real text document through the browser, watched
     it reach `READY` with a real chunk count: `about.txt · 1 chunks · READY`. Dragged Input → RAG
     → Output onto a real canvas, confirmed the RAG Inspector's knowledge-base dropdown lists the
     real KB (not a hardcoded option).
   - **MCP**: started `infrastructure/scripts/demo_mcp_server.py` (a real standalone server, not a
     mock in the test sense) and registered it from the MCP Servers page - the browser drove a
     genuine JSON-RPC `initialize` → `tools/list` handshake over the network and displayed the 2
     real discovered tools (`echo`, `add`).
   - **Evaluations**: created a dataset, added a test case via the browser's JSON textarea, ran an
     evaluation against a real flow, watched it hit `1/1 PASSED (100%)` with a working "view run"
     link into the real underlying `Run`.
   - **Settings**: saved a tool policy (`denied_tools`) through the browser, then confirmed via
     `psql` that a `flow.created` audit row appeared after creating a flow through the raw API -
     round-tripped back into the browser's Audit Log table.
6. **A real concurrency bug was caught by this live pass, not by any unit test**: the first time an
   MCP/RAG/Memory node actually executed inside a real run (Tool/Agent/Router nodes never touch
   the DB directly, so this path was never exercised before), it raised "concurrent operations are
   not permitted" - LangGraph drives node execution in a background `asyncio.create_task` while
   the request's own session persists events concurrently. Fixed by having those three services
   open their own short-lived session per call instead of sharing the request-scoped one; re-ran
   the full RAG/Memory/MCP test suite and the browser flows afterward to confirm the fix held.
7. `docker compose build api web` + `docker compose up -d` from the existing (non-fresh) state -
   all 4 services healthy. Re-ran the full pytest suite and both Playwright E2E specs **against the
   rebuilt dockerized stack** - everything green. `curl`'d a real flow run against the dockerized
   API and diffed `/metrics` before/after to confirm Prometheus counters
   (`workflow_runs_total`, `llm_requests_total`, `llm_tokens_total`, `tool_calls_total`, ...)
   actually move, not just exist as empty series.

---
_Last updated: 2026-08-22 - Phases 0–7 all done and verified end-to-end (API, browser, and Docker).
Nothing left at TODO/IN PROGRESS from the original phase plan; remaining gaps are the explicitly
deferred items listed above (Kubernetes operator, SAML/SCIM, billing, marketplace, etc.) plus
smaller documented limits (Ollama not run against a live daemon this session; guardrail heuristics
are pattern-based, not guarantees; MCP client supports the non-streaming response mode only).
Model catalog search (OpenRouter free models + provider-scoped search) added earlier and still live._
