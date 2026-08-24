# Roadmap

Status of each item lives in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); this file is the
longer-horizon shape.

## V0.1 - Current

- Visual builder (canvas, node library, inspector, live execution status)
- FlowSpec (typed, versioned, validated)
- LangGraph runtime: Input, Output, Agent, LLM, Router, Supervisor, Tool, Human Approval
- LiteLLM model gateway + MockLLM + Ollama
- Agent flight recorder (Run/RunStep/RunEvent) + trace UI
- Replay
- Docker Compose one-command local stack

## V0.2

- AI Architect (natural language → FlowSpec, with schema validation + bounded repair loop)
- RAG: document ingestion (TXT/MD/PDF), chunking, pgvector retrieval
- Conversation + semantic memory, with inspect/search/delete APIs
- MCP Server Registry + tool discovery (stdio/HTTP)
- Model router (rule-based cost/latency/privacy routing)

## V0.3

- PolicyEngine enforcing agent-level tool permissions
- Guardrails (PII detection, blocked keywords, prompt-injection heuristics, schema validation)
- Audit log surfaced in the UI
- Evaluation module: datasets, evaluators (exact/contains/schema/regex/latency/cost/LLM-judge),
  evaluation runs and dashboard
- Full workspace/role UI (Owner/Admin/Developer/Viewer)
- Deployment environments (dev/staging/prod flow versions)

## V0.4

- Temporal-backed durable execution for scheduled workflows, large evaluations, and long-running
  jobs (see `docs/adr/ADR-008-when-to-introduce-temporal.md`)
- Distributed workers for concurrent agent execution at scale
- Secure sandboxed Python tool execution
- Git integration + Agent CI/CD (evaluation suite as a merge gate)

## V1.0 - Enterprise

- SSO (OIDC/SAML), SCIM provisioning
- True multi-tenancy, data residency controls
- Enterprise secrets backends (Vault, AWS/Azure/GCP secret managers)
- Advanced policies, private networking, deployment governance
- High availability

## Explicitly out of scope for now

Kubernetes operator, full SAML/SCIM, billing system, agent marketplace, mobile app, hundreds of
pre-built integrations, custom vector database, custom LLM inference engine, custom distributed
scheduler - see `promots.md` section 72.
