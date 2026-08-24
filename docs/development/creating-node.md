# Creating a New Node Type

Adding a node type touches four layers. Using a hypothetical `webhook` node as an example:

## 1. FlowSpec (`packages/flowspec/src/flowspec/models.py`)

- Add `WEBHOOK = "webhook"` to `NodeType`.
- Add a `WebhookNodeConfig(BaseModel)` with `extra="forbid"` and sane defaults.
- Add a `WebhookNode(_NodeBase)` with `type: Literal[NodeType.WEBHOOK]` and `config: WebhookNodeConfig`.
- Add `WebhookNode` to the `Node` discriminated union.
- Export the new names from `packages/flowspec/src/flowspec/__init__.py`.
- Add validation rules to `validate_flowspec()` in `validation.py` if the node has invariants
  (e.g. a router's `default_target` must reference a real node id).

## 2. Runtime (`packages/runtime/src/agentq_runtime/nodes.py`)

- Write `build_webhook_fn(node, flow, ...) -> NodeFn` following the existing pattern: emit
  `node.started`, do the work, emit `node.completed` with `{"output": ...}` on success, or call
  `_fail(config, node.id, message)` on failure (which emits `node.failed` and raises
  `NodeExecutionError` - never return an error value, since that would let downstream nodes run on
  stale data).
- Add a `case NodeType.WEBHOOK:` arm to `build_node_fn()`.
- If the node needs conditional routing (like Router/Supervisor), wire it into
  `FlowCompiler.compile()` in `compiler.py` instead of a plain edge.

## 3. Frontend node library + inspector

- Add an icon + `NODE_CATEGORY`/`NODE_LABEL` entry in `apps/web/lib/flowspec.ts`.
- Add a config form in `apps/web/components/canvas/inspector.tsx` (or fall back to the generic
  `FuturePhaseConfig` JSON editor if the node isn't executable yet).

## 4. Tests

- `packages/flowspec/tests/test_validation.py` - any new validation rule.
- `packages/runtime/tests/` - a small flow exercising the new node end-to-end with MockLLM,
  following `test_router_and_tool.py` as a template.
- Optionally an example under `examples/` if the node is genuinely useful to demo.

## Honesty rule

If the node isn't fully implemented yet, it must say so - see `build_passthrough_fn()` for the
pattern (executes as a pass-through, emits a `note` field, and the Inspector shows a "Not
implemented in this MVP phase" badge). Never make a node's UI claim behavior the backend doesn't
perform (spec section 77).
