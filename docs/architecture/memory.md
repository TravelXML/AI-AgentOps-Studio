# Memory

**Not implemented in this MVP phase.** `MemoryNodeConfig` exists in FlowSpec
(`memory_type: conversation | semantic`, `scope: run | agent | workspace`, `ttl_seconds`) and a
Memory node compiles and runs today as a labeled pass-through
(`agentq_runtime.nodes.build_passthrough_fn`).

## Planned (Phase 4)

- **Conversation memory**: per-agent, per-scope message history, persisted in a `memories` table,
  with an inspect/search/delete API so the UI can answer "what does this agent remember, why, who
  created it, which agent can access it, when does it expire" (spec section 20).
- **Semantic memory**: embedding-backed recall via pgvector, sharing the same retriever
  abstraction as RAG (`RAGNodeConfig`) so both features reuse one pluggable
  embeddings/vector-store/chunker/retriever layer rather than duplicating it.

Working Memory and Episodic Memory are named in the spec conceptually but have no committed
implementation date - they are not on the V0.2–V0.4 roadmap yet.
