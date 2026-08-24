# Creating a New Built-in Tool

Tools live in `packages/runtime/src/agentq_runtime/tools/`. A tool is a `ToolDefinition`
(`registry.py`): `id`, `name`, `description`, `input_schema`, `output_schema`, `permissions`, and
an async `handler(arguments: dict) -> Any`.

## Steps

1. Write the handler in `builtin.py` (or a new module if it's substantial):

   ```python
   async def _my_tool(arguments: dict[str, Any]) -> Any:
       value = arguments.get("thing")
       if not value:
           raise ToolExecutionError("my_tool requires a 'thing' argument.")
       ...
       return {"result": ...}
   ```

   Raise `ToolExecutionError` for any expected failure - the Tool node catches it, emits
   `tool.completed` with an `error` field, and halts the run via `NodeExecutionError` rather than
   letting a broken tool call look like it succeeded.

2. Register it in `register_builtin_tools()`:

   ```python
   registry.register(
       ToolDefinition(
           id="my_tool",
           name="My Tool",
           description="...",
           input_schema={"type": "object", "properties": {...}, "required": [...]},
           output_schema={"type": "object"},
           permissions=[],  # or e.g. ["net.http.get"] if it reaches the network
           handler=_my_tool,
       )
   )
   ```

3. If the tool makes outbound HTTP requests, route them through
   `agentq_runtime.tools.ssrf_guard.assert_safe_url()` first - see `_http_get`/`_http_post`
   for the pattern. Never skip this for a "trusted" URL; the guard already supports an
   `allowed_hosts` escape hatch if a specific deployment needs one.

4. Add a test in `packages/runtime/tests/` (a Tool node flow using the new tool, following
   `test_router_and_tool.py`).

5. The tool automatically appears in `GET /api/v1/tools` and the Inspector's tool picker - no
   frontend changes needed unless it needs bespoke argument UI beyond the generic JSON editor.

## What NOT to build here

No unrestricted Python execution tool. If a future sandboxed-Python tool is added, it must be
explicitly isolated (subprocess/container boundary) and documented as requiring real sandboxing
before production use - never a bare `exec()`/`eval()` in the API process (spec sections 17, 80).
