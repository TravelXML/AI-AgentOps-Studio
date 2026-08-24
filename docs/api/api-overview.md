# API Overview

Base path: `/api/v1`. Interactive docs (OpenAPI/Swagger UI) are always live at `/docs` when the
API is running; this page is a map, not a replacement for it.

## Auth

Development mode: every request is scoped to a single auto-provisioned "Default Workspace" - see
`agentq_api.services.bootstrap`. No login is required yet (spec section 39); the data model is
already workspace-scoped throughout so real auth is additive, not a migration.

## Resources

| Resource | Routes |
|---|---|
| Projects | `GET /projects` |
| Flows | `GET/POST /flows`, `GET /flows/{id}`, `GET /flows/{id}/versions/latest`, `POST /flows/{id}/versions`, `POST /flows/{id}/validate`, `POST /flows/{id}/publish` |
| Runs | `POST /flows/{id}/runs` (creates + streams SSE), `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events`, `POST /runs/{id}/resume` (streams SSE), `POST /runs/{id}/replay` (streams SSE) |
| Models | `GET/POST /models` |
| Tools | `GET /tools` |

Plus `GET /health`, `GET /ready`, `GET /metrics` (Prometheus text format) at the root, not under
`/api/v1`.

## Streaming runs

`POST /flows/{id}/runs`, `POST /runs/{id}/resume`, and `POST /runs/{id}/replay` all return
`text/event-stream`, not JSON - the run/resume/replay *is* the SSE stream. The new/replayed run's
id comes back as the `X-Run-Id` response header (exposed via CORS `expose_headers` - see
`docs/development/local-development.md` for why that matters). Each SSE frame's `data:` payload
is a `RunEvent`:

```json
{"type": "node.completed", "run_id": "...", "node_id": "agent-1", "data": {"output": "..."}, "timestamp": "..."}
```

Event types: `run.started`, `node.started`, `llm.started`, `llm.completed`, `tool.started`,
`tool.completed`, `node.completed`, `node.failed`, `run.waiting`, `run.completed`, `run.failed`.
(`llm.token` is reserved for future token-level streaming - not emitted yet.)

Browsers can't use `EventSource` for a POST request; the frontend reads the stream via
`fetch()` + a `ReadableStream` reader instead (`apps/web/lib/api-client.ts`, `parseSse()`).

## Errors

Every error response is a consistent envelope, never a bare stack trace:

```json
{"error": {"code": "FLOW_NOT_FOUND", "message": "Flow '...' was not found.", "details": [], "request_id": "..."}}
```

## Example: run the "Simple Agent" example end-to-end

```bash
FLOW_ID=$(curl -s http://localhost:8000/api/v1/flows | jq -r '.[] | select(.name=="Simple Agent") | .id')
curl -N -X POST "http://localhost:8000/api/v1/flows/$FLOW_ID/runs" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"query": "What is AgentQ?"}}'
```
