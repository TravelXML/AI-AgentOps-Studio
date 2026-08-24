# Security

## Reporting a vulnerability

Please open a private security advisory (GitHub: Security → Advisories → Report a vulnerability)
rather than a public issue. We'll acknowledge within a reasonable timeframe and coordinate
disclosure.

## What's implemented today

- **SSRF protection** on the built-in HTTP GET/POST tools - requests to loopback, link-local,
  private, reserved, or multicast addresses are blocked by resolving the hostname and checking
  every resolved IP (`packages/runtime/src/agentq_runtime/tools/ssrf_guard.py`), not just
  string-matching the hostname.
- **No `eval()` on user input.** Router rules, human-approval conditions, and template
  interpolation run through a restricted `ast`-based evaluator
  (`packages/runtime/src/agentq_runtime/expressions.py`) with an explicit node-type allow-list.
- **No arbitrary Python execution** in the API process. There is no "Python sandbox" tool in this
  MVP; the spec explicitly requires isolating any future one behind an explicit interface.
- **Secrets** are stored encrypted at rest (Fernet, keyed from `APP_SECRET`) and referenced only
  by `secret_id` - never embedded in FlowSpec, logs, traces, or API responses.
  (`apps/api/src/agentq_api/services/secrets_service.py`)
- **Workspace-scoped data model.** Every resource-bearing table carries `workspace_id` even
  though MVP auth is a single dev workspace - multi-tenancy is not a later retrofit.
- **Consistent error envelope**; stack traces are never returned to API clients.

## Known MVP limitations (tracked, not hidden)

- Auth is "development mode": a single auto-provisioned workspace/user, no login. Full
  RBAC/OIDC/SAML is `docs/adr/ADR-007-multi-tenant-data-model.md` + the V1.0 roadmap.
- PolicyEngine, guardrails (PII/prompt-injection detection), and the audit log UI ship in Phase 6
  - see `IMPLEMENTATION_PLAN.md`.
- Heuristic prompt-injection detection, when it ships, will not be represented as complete
  protection against prompt injection - no heuristic is.
