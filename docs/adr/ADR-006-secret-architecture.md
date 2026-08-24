# ADR-006: Secret Architecture

**Status:** Accepted

## Context

Spec sections 32/40 are explicit: never persist raw API keys in FlowSpec, never expose secrets
through frontend APIs, never include secrets in traces or logs.

## Decision

- Raw secret values are encrypted at rest (Fernet, key derived from `APP_SECRET`) in a `secrets`
  table (`apps/api/src/agentq_api/services/secrets_service.py`).
- `ModelConfigRow` (and, in future, any other credential-bearing config) references a secret only
  by `secret_id`.
- Decryption happens exactly once per request, inside `build_model_gateway()`, producing an
  in-memory closure (`secret_resolver`) that `LiteLLMProvider` calls at the point of an actual
  provider SDK call - the decrypted value is never attached to a persisted object.
- API responses expose `has_secret: bool`, never the value.

## Consequences

- A compromised read-only DB export leaks ciphertext, not plaintext credentials (though
  `APP_SECRET` itself must obviously be protected - MVP local dev ships an insecure default;
  the API logs a warning at startup if that default is still in place outside `APP_ENV=development`).
- Future enterprise secret backends (Vault, AWS/Azure/GCP secret managers - spec section 40) slot
  in as an alternate `SecretsService` implementation behind the same `resolve(secret_id)` contract,
  not a schema change.
