# RAG Agent Example

Retrieval-augmented Q&A. `make seed` (or `infrastructure/scripts/seed_examples.py`) creates a
small "AgentQ Docs" knowledge base, ingests one short document into it, then loads this flow with
its real knowledge base id filled in - no manual setup needed to try it.

Ask it something covered by the seeded document (e.g. "what is a flow made of", "how does human
approval work") and it will answer from the retrieved context; ask something unrelated and it will
say the context doesn't cover it, since the agent is instructed to answer only from what RAG
retrieved.
