"""Unit tests mock the wire (httpx) so they're deterministic and need no real server - proving
McpClient's JSON-RPC handling, session handling, and error handling in isolation. A genuine live
round trip against a real MCP server (infrastructure/scripts/demo_mcp_server.py) is verified
separately in the browser, the same split used for the model catalog and architect features."""

import pytest

from agentq_runtime.mcp_client import McpClient, McpError

TOOLS = [{"name": "echo", "description": "Echoes input back", "inputSchema": {}}]


class _FakeResponse:
    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = str(body)

    def json(self):
        return self._body


class _FakeAsyncClient:
    def __init__(self, calls, fail=False):
        self._calls = calls
        self._fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self._calls.append((url, json, headers))
        method = json.get("method")
        req_id = json.get("id")

        if self._fail:
            return _FakeResponse({}, status_code=500)
        if method == "initialize":
            return _FakeResponse(
                {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05"}},
                headers={"Mcp-Session-Id": "sess-abc"},
            )
        if method == "notifications/initialized":
            return _FakeResponse({}, status_code=202)
        if method == "tools/list":
            return _FakeResponse({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        if method == "tools/call":
            args = json["params"]["arguments"]
            if json["params"]["name"] == "unknown":
                return _FakeResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"isError": True, "content": [{"text": "no such tool"}]},
                    }
                )
            text = args.get("text", "")
            return _FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}], "isError": False},
                }
            )
        return _FakeResponse({"jsonrpc": "2.0", "id": req_id, "error": {"message": "unknown method"}})


def _patch_httpx(monkeypatch, calls, *, fail=False):
    monkeypatch.setattr(
        "agentq_runtime.mcp_client.httpx.AsyncClient", lambda timeout=None: _FakeAsyncClient(calls, fail=fail)
    )


async def test_full_handshake_list_and_call(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls)

    client = McpClient("https://example.com/mcp")
    await client.initialize()
    tools = await client.list_tools()
    result = await client.call_tool("echo", {"text": "hi"})

    assert tools == TOOLS
    assert result == [{"type": "text", "text": "hi"}]
    # session id captured after initialize is echoed back on every later request
    assert calls[1][2]["Mcp-Session-Id"] == "sess-abc"
    assert calls[-1][2]["Mcp-Session-Id"] == "sess-abc"


async def test_call_tool_error_result_raises(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls)
    client = McpClient("https://example.com/mcp")
    await client.initialize()

    with pytest.raises(McpError, match="no such tool"):
        await client.call_tool("unknown", {})


async def test_http_error_raises_mcp_error(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls, fail=True)
    client = McpClient("https://example.com/mcp")

    with pytest.raises(McpError, match="HTTP 500"):
        await client.initialize()


async def test_register_server_discovers_tools(client, monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls)

    response = await client.post(
        "/api/v1/mcp-servers", json={"name": "demo", "url": "https://example.com/mcp"}
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "connected"
    assert body["tools"] == TOOLS


async def test_register_unreachable_server_records_error(client, monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls, fail=True)

    response = await client.post(
        "/api/v1/mcp-servers", json={"name": "broken", "url": "https://unreachable.example.com/mcp"}
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "error"
    assert "HTTP 500" in body["last_error"]
    assert body["tools"] == []


async def test_flow_run_calls_mcp_tool_end_to_end(client, monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, calls)

    register = await client.post(
        "/api/v1/mcp-servers", json={"name": "demo", "url": "https://example.com/mcp"}
    )
    server_id = register.json()["id"]

    spec = {
        "id": "placeholder",
        "name": "MCP Echo Flow",
        "nodes": [
            {"id": "input-1", "type": "input", "label": "Input", "config": {}},
            {
                "id": "mcp-1",
                "type": "mcp",
                "label": "Echo",
                "config": {
                    "server_id": server_id,
                    "tool_name": "echo",
                    "arguments": {"text": "{{input.text}}"},
                },
            },
            {"id": "output-1", "type": "output", "label": "Output", "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "input-1", "target": "mcp-1"},
            {"id": "e2", "source": "mcp-1", "target": "output-1"},
        ],
    }
    create = await client.post("/api/v1/flows", json={"name": "MCP Echo Flow", "spec": spec})
    flow_id = create.json()["id"]

    run_response = await client.post(f"/api/v1/flows/{flow_id}/runs", json={"inputs": {"text": "hello mcp"}})
    assert run_response.status_code == 200
    run_id = run_response.headers["x-run-id"]

    run = await client.get(f"/api/v1/runs/{run_id}")
    body = run.json()
    assert body["status"] == "SUCCEEDED", body
    assert body["output"] == [{"type": "text", "text": "hello mcp"}]
