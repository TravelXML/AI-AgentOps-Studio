# FlowSpec

`packages/flowspec` defines the canonical, runtime-independent representation of a workflow.
Source of truth: `packages/flowspec/src/flowspec/models.py`.

## Shape

```json
{
  "schema_version": 1,
  "id": "customer-support-v1",
  "name": "Customer Support Agent",
  "version": 1,
  "inputs": [{ "name": "query", "type": "string", "required": true }],
  "nodes": [ /* discriminated union on `type` */ ],
  "edges": [{ "id": "e1", "source": "input-1", "target": "agent-1", "condition": null }],
  "variables": {},
  "policies": {},
  "metadata": {}
}
```

`nodes` is a Pydantic discriminated union keyed on `type` (`input | output | agent | llm | router |
supervisor | tool | mcp | rag | memory | human_approval | guardrail`), each with its own typed
`config` model (`AgentNodeConfig`, `RouterNodeConfig`, ...). Unknown node types or malformed config
fail validation immediately - there's no silent fallback to a dict.

## Validation vs. compilation

These are two distinct passes, both required before a flow can run:

- **`validate_flowspec()`** (`packages/flowspec/src/flowspec/validation.py`) checks structural
  correctness - exactly one Input node, at least one Output node, no dangling edges, no orphaned
  nodes, agents have a model, routers/supervisors point at real node ids. Every issue carries a
  stable `code` and a human-readable `message` naming the offending node - never a raw exception.
- **`FlowCompiler.compile()`** (`packages/runtime`) turns an already-valid FlowSpec into a
  LangGraph `StateGraph`. It re-validates first (so compiling directly is always safe) and raises
  `CompilationError` with the same structured issues on failure.

## Versioning

Every `POST /flows/{id}/versions` call creates a new immutable `FlowVersion` row - the FlowSpec
JSON is snapshotted, not mutated in place. `Run.flow_version_id` always points at one specific
immutable version, so replaying or auditing a past run always reconstructs the exact graph that
actually ran, even if the flow has since been edited further.

## What's NOT in FlowSpec

Nothing LangGraph-specific. No Python callables, no LangGraph node/edge objects, no checkpointer
references. If you find yourself wanting to put a LangGraph concept into FlowSpec, it belongs in
the compiler instead.
