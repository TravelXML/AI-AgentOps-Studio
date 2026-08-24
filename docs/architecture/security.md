# Security Architecture

See [`SECURITY.md`](../../SECURITY.md) at the repo root for the reporting process and a summary.
This document covers the design.

## Resource boundaries

`workspace → project → flow → run` (with `environment` reserved for Phase 3+ deployment targets).
Every table in `apps/api/src/agentq_api/db/models.py` carries `workspace_id`, even the ones
that today only ever see a single auto-provisioned dev workspace
(`agentq_api/services/bootstrap.py`). Multi-tenancy is a query-filter and auth change, not a
schema migration, when it's needed.

## Secrets

`Secret` rows store Fernet-encrypted ciphertext, keyed from `APP_SECRET`. `ModelConfigRow`
references a secret only by `secret_id` (a UUID). The decrypted value exists only transiently,
inside `ModelGateway`'s in-memory resolver closure, for the duration of a single request - it is
never serialized into FlowSpec, never logged, never returned from any API response.
`ModelConfigResponse` exposes `has_secret: bool`, never the value.

## SSRF

`packages/runtime/src/agentq_runtime/tools/ssrf_guard.py` resolves the target hostname via
`socket.getaddrinfo` and checks *every resolved address* - not just the literal hostname string -
against loopback/link-local/private/reserved/multicast ranges, so a DNS-rebinding style bypass
(pointing a public hostname at a private IP) is also blocked. Applies to both built-in HTTP tools.

## No `eval()`

Router rules (`RouterNodeConfig.rules[].when`), Human Approval conditions
(`HumanApprovalNodeConfig.condition`), and `{{template}}` interpolation all run through
`packages/runtime/src/agentq_runtime/expressions.py` - an `ast.parse` + explicit
node-type allow-list walker, not Python's `eval()`. Disallowed syntax (function calls, imports,
comprehensions, anything not on the allow-list) raises `ExpressionError` instead of executing.

## Guardrails, PolicyEngine, audit log

Modeled in FlowSpec today (`GuardrailNodeConfig`, `PolicyEngine` interface referenced in the
spec) but not yet enforced at runtime - Phase 6. See `IMPLEMENTATION_PLAN.md`.
