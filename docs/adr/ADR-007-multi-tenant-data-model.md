# ADR-007: Multi-Tenant Data Model From Day One

**Status:** Accepted

## Context

MVP auth is intentionally minimal - a single auto-provisioned "dev mode" workspace, no login
(spec section 39). It would be faster to build the schema single-tenant and add `workspace_id`
later. Spec section 38 explicitly forbids that shortcut: "do NOT bake single-user assumptions
into the database model."

## Decision

Every resource-bearing table (`projects`, `flows`, `flow_versions`, `runs`, `run_steps`,
`run_events`, `model_configs`, `secrets`, `audit_logs`, ...) carries `workspace_id` from the first
migration. `User`, `Workspace`, `WorkspaceMember` (with `role: owner|admin|developer|viewer`)
exist as real tables today, even though nothing enforces role-based permissions yet.

## Consequences

- Adding real auth (OIDC/SAML, roles, tenant isolation) is a query-filter + auth-middleware
  change, not a data migration touching every table.
- Every service method that reads/writes a resource takes a `workspace_id` and filters by it
  (see `FlowService`, `RunExecutionService`) - this discipline has to be maintained by every new
  service going forward, or the isolation guarantee silently erodes.
- MVP "dev mode" (`ensure_dev_workspace()`) is explicitly a placeholder auth layer, not a design
  the schema depends on.
