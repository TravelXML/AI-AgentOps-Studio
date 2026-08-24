# ADR-001: FlowSpec as the Canonical Representation

**Status:** Accepted

## Context

A visual builder needs *some* serialized form of a workflow. The easy path is to store whatever
the execution engine natively understands (e.g., serialized LangGraph structures). That path
locks the product to one runtime forever and leaks implementation details into the UI, storage,
versioning, and any future "generate a flow from natural language" feature.

## Decision

Define FlowSpec (`packages/flowspec`) as a framework-neutral, Pydantic-validated schema. The
canvas persists FlowSpec. A `FlowCompiler` is the only thing that turns FlowSpec into a runtime
graph. Nothing upstream of the compiler (API, database, UI, AI Architect) ever sees LangGraph
types.

## Consequences

- Adding a second runtime adapter (CrewAI, AutoGen, custom Python) requires a new compiler/runtime
  pair, not a UI or database rewrite.
- FlowSpec versions cleanly as plain JSON (`FlowVersion` rows) independent of any runtime's own
  serialization format.
- Extra indirection: every new capability (e.g., a new node type) touches both FlowSpec and the
  compiler. Accepted as the cost of the neutrality guarantee.
