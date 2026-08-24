# Execution Engine

## WorkflowRuntime abstraction

```python
class WorkflowRuntime(ABC):
    async def compile(self, flow: FlowSpec) -> CompiledWorkflow: ...
    def execute(self, compiled, run_id: str, inputs: dict) -> AsyncIterator[RunEvent]: ...
    def resume(self, compiled, run_id: str, resume_value: Any) -> AsyncIterator[RunEvent]: ...
    async def get_status(self, compiled, run_id: str) -> str: ...
```

`LangGraphRuntime` is the only implementation today (`packages/runtime/src/agentq_runtime/langgraph_runtime.py`).
Everything above this interface - the API layer, the flight recorder, the UI - depends only on
`RunEvent` and the four methods above, never on LangGraph types directly.

## Graph shape

`FlowCompiler.compile()` builds one LangGraph node per FlowSpec node
(`packages/runtime/src/agentq_runtime/nodes.py`), threading a shared `WorkflowState`
(`input`, `variables`, `node_outputs`, `output`) with a merge reducer on the dict fields so each
node can return just its own delta.

- **Router / Supervisor** nodes don't get plain edges to their targets - they get
  `add_conditional_edges`, keyed by a `target` value the node itself writes into
  `node_outputs[node_id]`. This is how "the LLM picked agent X, and only agent X runs" is
  enforced structurally, not just by convention.
- **Every other node type** gets plain edges straight from the FlowSpec edge list.
- Nodes with no outgoing edge get an edge to `END`.

## Failure semantics

A node raises `NodeExecutionError` on failure rather than returning an error value. This matters:
LangGraph halts the run immediately on an unhandled exception, so a failed Agent node can never be
silently followed by an Output node running on top of stale/missing data - the platform doesn't
fake a downstream success after an upstream failure.

## Human Approval

Human Approval nodes call LangGraph's `interrupt()`. The compiled graph is built with a
**Postgres-backed checkpointer** (`AsyncPostgresSaver`, one process-lifetime instance, entered in
`main.py`'s lifespan), keyed by `thread_id = run_id`. Consequences:

- The pause is real graph state on disk, not a frontend illusion - killing the API process and
  restarting it leaves the run paused exactly where it was.
- Resuming calls `compiled.graph.astream(Command(resume=value), config={"configurable":{"thread_id":run_id}})`.
- Known LangGraph quirk: any code *before* the `interrupt()` call inside a node function re-runs
  on resume (LangGraph re-enters the node from the top). Side effects in Human Approval nodes are
  therefore placed *after* `interrupt()` wherever possible; the one exception is the
  `node.started` event, which - as a documented, harmless quirk - can be emitted twice (once
  before the pause, once on resume) since it lands in two different SSE streams a client would
  never observe as literally duplicated.

## Streaming

`LangGraphRuntime._drive()` runs `compiled.graph.astream(..., stream_mode="updates")` in a
background asyncio task and forwards each node-emitted event through an `asyncio.Queue`, which
`_stream()` drains and turns into synthetic run-level events (`run.started`, `run.waiting`,
`run.completed`, `run.failed`). The API layer (`RunExecutionService`) persists each event and
writes it to the HTTP response as an SSE frame in the same pass - see
[`system-overview.md`](system-overview.md) for the full request lifecycle.

## Known limitations (honestly, not hidden)

- **LLM-mode routing / Supervisor delegation** currently use deterministic keyword-overlap
  scoring for the actual target selection, while still calling the configured model so its
  response is recorded as the human-readable rationale. Real structured-output/tool-calling-driven
  selection is a documented future enhancement (`packages/runtime/src/agentq_runtime/routing.py`).
- **Supervisor delegation is single-shot** for MVP - one decision per run, not an iterative
  multi-round delegation loop (`max_iterations`/`max_delegation_depth` are modeled in FlowSpec for
  forward compatibility but not yet enforced as a loop).
- RAG / Memory / MCP / Guardrail nodes execute as a labeled pass-through today
  (`build_passthrough_fn`) - they run, but not by doing their real named function yet (Phase 4/6).
