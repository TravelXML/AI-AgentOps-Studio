# ADR-005: Server-Sent Events over WebSocket

**Status:** Accepted

## Context

Run execution needs to stream events (`node.started`, `llm.completed`, ...) to the browser in
near-real-time so the canvas can show live node status and the trace can populate incrementally.
Spec section 31 explicitly asks for this decision.

## Decision

Use Server-Sent Events (one-directional, server → client) for run streaming, not WebSockets. A run
is triggered by `POST /flows/{id}/runs`, and the response *is* the event stream
(`text/event-stream`) - there's no separate connection handshake. Resume and replay work the same
way.

## Consequences

- Simpler server code: one async generator per request, no connection/room management, no
  reconnect/backoff protocol to design.
- Browsers can't use the native `EventSource` API for a POST-triggered stream (`EventSource` is
  GET-only), so the frontend reads the stream manually via `fetch()` + `ReadableStream`
  (`apps/web/lib/api-client.ts`). This is a documented, accepted trade-off, not an oversight.
- If a future feature needs true bidirectional real-time communication (e.g., live collaborative
  canvas editing), that specific feature can add a WebSocket endpoint without touching run
  streaming - this ADR only decides SSE for run execution.
