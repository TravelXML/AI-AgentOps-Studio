"""Phase 6 integration tests: guardrails and tool policy actually run as part of a real flow
execution (not just the pure evaluator unit tests in packages/security), and key actions leave a
real audit log row behind."""


def _flow_with_guardrail(on_fail: str, checks: list[dict]) -> dict:
    return {
        "id": "placeholder",
        "name": "Guardrail Flow",
        "nodes": [
            {"id": "input-1", "type": "input", "label": "Input", "config": {}},
            {
                "id": "guard-1",
                "type": "guardrail",
                "label": "Guard",
                "config": {"stage": "pre", "checks": checks, "on_fail": on_fail},
            },
            {"id": "output-1", "type": "output", "label": "Output", "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "input-1", "target": "guard-1"},
            {"id": "e2", "source": "guard-1", "target": "output-1"},
        ],
    }


async def _run_flow(client, spec, inputs):
    create = await client.post("/api/v1/flows", json={"name": spec["name"], "spec": spec})
    flow_id = create.json()["id"]
    response = await client.post(f"/api/v1/flows/{flow_id}/runs", json={"inputs": inputs})
    run_id = response.headers["x-run-id"]
    run = await client.get(f"/api/v1/runs/{run_id}")
    return run.json()


async def test_guardrail_blocks_flow_on_violation(client):
    spec = _flow_with_guardrail(
        "block", [{"type": "blocked_keywords", "config": {"keywords": ["forbidden"]}}]
    )
    body = await _run_flow(client, spec, {"text": "this contains a forbidden word"})
    assert body["status"] == "FAILED"
    assert "forbidden" in body["error"]


async def test_guardrail_allows_clean_input(client):
    spec = _flow_with_guardrail(
        "block", [{"type": "blocked_keywords", "config": {"keywords": ["forbidden"]}}]
    )
    body = await _run_flow(client, spec, {"text": "this is fine"})
    assert body["status"] == "SUCCEEDED"


async def test_guardrail_warn_mode_does_not_block(client):
    spec = _flow_with_guardrail("warn", [{"type": "blocked_keywords", "config": {"keywords": ["forbidden"]}}])
    body = await _run_flow(client, spec, {"text": "this contains a forbidden word"})
    assert body["status"] == "SUCCEEDED"


async def test_guardrail_pii_detection_blocks_email(client):
    spec = _flow_with_guardrail("block", [{"type": "pii_detection"}])
    body = await _run_flow(client, spec, {"text": "reach me at someone@example.com"})
    assert body["status"] == "FAILED"


TOOL_FLOW_SPEC = {
    "id": "placeholder",
    "name": "Tool Policy Flow",
    "nodes": [
        {"id": "input-1", "type": "input", "label": "Input", "config": {}},
        {
            "id": "tool-1",
            "type": "tool",
            "label": "Calc",
            "config": {"tool_id": "calculator", "arguments": {"expression": "1 + 1"}},
        },
        {"id": "output-1", "type": "output", "label": "Output", "config": {}},
    ],
    "edges": [
        {"id": "e1", "source": "input-1", "target": "tool-1"},
        {"id": "e2", "source": "tool-1", "target": "output-1"},
    ],
}


async def test_tool_policy_denies_configured_tool(client):
    update = await client.put("/api/v1/settings/policy", json={"denied_tools": ["calculator"]})
    assert update.status_code == 200
    try:
        body = await _run_flow(client, TOOL_FLOW_SPEC, {})
        assert body["status"] == "FAILED"
        assert "denied" in body["error"]
    finally:
        await client.put("/api/v1/settings/policy", json={"denied_tools": []})


async def test_tool_policy_allows_when_not_denied(client):
    await client.put("/api/v1/settings/policy", json={"denied_tools": ["some_other_tool"]})
    body = await _run_flow(client, TOOL_FLOW_SPEC, {})
    assert body["status"] == "SUCCEEDED"


async def test_get_policy_returns_current_state(client):
    await client.put("/api/v1/settings/policy", json={"denied_tools": ["http_post"]})
    response = await client.get("/api/v1/settings/policy")
    assert response.json()["denied_tools"] == ["http_post"]


async def test_flow_creation_writes_audit_log(client):
    await client.post("/api/v1/flows", json={"name": "Audited Flow"})
    log = await client.get("/api/v1/settings/audit-log")
    actions = [entry["action"] for entry in log.json()]
    assert "flow.created" in actions


async def test_flow_publish_writes_audit_log(client):
    create = await client.post(
        "/api/v1/flows",
        json={
            "name": "Publish Audit Flow",
            "spec": {
                "id": "x",
                "name": "Publish Audit Flow",
                "nodes": [
                    {"id": "input-1", "type": "input", "label": "Input", "config": {}},
                    {"id": "output-1", "type": "output", "label": "Output", "config": {}},
                ],
                "edges": [{"id": "e1", "source": "input-1", "target": "output-1"}],
            },
        },
    )
    flow_id = create.json()["id"]
    await client.post(f"/api/v1/flows/{flow_id}/publish")

    log = await client.get("/api/v1/settings/audit-log")
    entries = [e for e in log.json() if e["resource_id"] == flow_id]
    actions = {e["action"] for e in entries}
    assert "flow.created" in actions
    assert "flow.published" in actions


async def test_run_creation_writes_audit_log(client):
    result = await _run_flow(client, TOOL_FLOW_SPEC, {})
    log = await client.get("/api/v1/settings/audit-log")
    entries = [e for e in log.json() if e["resource_id"] == result["id"]]
    assert any(e["action"] == "run.created" for e in entries)
