# ADR-003: LiteLLM as the Model Gateway

**Status:** Accepted

## Context

The product must never hard-code a single LLM provider's SDK into business logic (spec section 8),
must support OpenAI/Anthropic/Gemini/Groq/OpenRouter/NVIDIA NIM/Azure/Bedrock/Ollama/custom
endpoints, and must boot and pass every test with zero API keys.

## Decision

Route every model call through `packages/model_gateway`: `ModelGateway.complete(model_id, ...)`
resolves a `model_id` to a `ModelConfig` and dispatches to either `MockLLM` (zero network,
deterministic) or `LiteLLMProvider` (one call path for every real provider, via LiteLLM). Model
configuration lives in the `model_configs` table, referencing secrets only by `secret_id`.

## Consequences

- Every node that calls a model (`Agent`, `LLM`, `Router` in `llm` mode, `Supervisor`) goes
  through one interface; a provider outage or API change is isolated to `litellm_provider.py`.
- `default` always resolves to MockLLM unless a workspace explicitly configures otherwise -
  automated tests and a fresh `docker compose up` never require a credential.
- Cost accounting (`estimated_cost_usd`) is only as accurate as LiteLLM's own pricing tables;
  local-model calls are correctly represented as `$0` *API* cost, not zero total economic cost
  (spec section 34) - this distinction is called out explicitly in the dashboard UI copy.
