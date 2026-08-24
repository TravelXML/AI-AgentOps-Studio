import json

import pytest

SIMPLE_SPEC = {
    "id": "placeholder",
    "name": "Simple Agent",
    "nodes": [
        {"id": "input-1", "type": "input", "label": "Input", "config": {}},
        {
            "id": "agent-1",
            "type": "agent",
            "label": "Assistant",
            "config": {"name": "Assistant", "instructions": "Be helpful.", "model": "mock"},
        },
        {"id": "output-1", "type": "output", "label": "Output", "config": {}},
    ],
    "edges": [
        {"id": "e1", "source": "input-1", "target": "agent-1"},
        {"id": "e2", "source": "agent-1", "target": "output-1"},
    ],
}


async def _create_flow(client, spec=SIMPLE_SPEC, name="Simple Agent"):
    response = await client.post("/api/v1/flows", json={"name": name, "spec": spec})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_health_and_ready(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/ready")).status_code == 200


@pytest.mark.asyncio
async def test_create_flow_creates_first_version(client):
    flow = await _create_flow(client)
    assert flow["status"] == "draft"
    assert flow["latest_version"] == 1

    version = await client.get(f"/api/v1/flows/{flow['id']}/versions/latest")
    assert version.status_code == 200
    assert version.json()["spec"]["nodes"][0]["type"] == "input"


@pytest.mark.asyncio
async def test_save_version_increments_version_number(client):
    flow = await _create_flow(client)
    response = await client.post(f"/api/v1/flows/{flow['id']}/versions", json={"spec": SIMPLE_SPEC})
    assert response.status_code == 201
    assert response.json()["version"] == 2


@pytest.mark.asyncio
async def test_validate_flow_reports_missing_output(client):
    flow = await _create_flow(client)
    broken_spec = json.loads(json.dumps(SIMPLE_SPEC))
    broken_spec["nodes"] = [n for n in broken_spec["nodes"] if n["type"] != "output"]
    response = await client.post(f"/api/v1/flows/{flow['id']}/validate", json={"spec": broken_spec})
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert any(issue["code"] == "MISSING_OUTPUT" for issue in body["issues"])


@pytest.mark.asyncio
async def test_publish_flow(client):
    flow = await _create_flow(client)
    response = await client.post(f"/api/v1/flows/{flow['id']}/publish")
    assert response.status_code == 200
    assert response.json()["status"] == "published"


@pytest.mark.asyncio
async def test_publish_without_version_fails_cleanly(client):
    response = await client.post("/api/v1/flows", json={"name": "Empty Flow", "description": ""})
    flow = response.json()
    publish = await client.post(f"/api/v1/flows/{flow['id']}/publish")
    assert publish.status_code == 409
    assert publish.json()["error"]["code"] == "NO_FLOW_VERSION"


@pytest.mark.asyncio
async def test_run_executes_end_to_end_via_sse(client):
    flow = await _create_flow(client)
    async with client.stream(
        "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {"query": "hello"}}
    ) as response:
        assert response.status_code == 200
        run_id = response.headers["x-run-id"]
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))

    types = [e["type"] for e in events]
    assert types[0] == "run.started"
    assert types[-1] == "run.completed"

    run = await client.get(f"/api/v1/runs/{run_id}")
    body = run.json()
    assert body["status"] == "SUCCEEDED"
    assert len(body["steps"]) == 3
    assert body["output"]

    run_events = await client.get(f"/api/v1/runs/{run_id}/events")
    assert len(run_events.json()) == len(events)


@pytest.mark.asyncio
async def test_run_replay_creates_new_run(client):
    flow = await _create_flow(client)
    async with client.stream(
        "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {"query": "hi"}}
    ) as response:
        run_id = response.headers["x-run-id"]
        async for _ in response.aiter_lines():
            pass

    async with client.stream("POST", f"/api/v1/runs/{run_id}/replay") as replay_response:
        assert replay_response.status_code == 200
        new_run_id = replay_response.headers["x-run-id"]
        async for _ in replay_response.aiter_lines():
            pass

    assert new_run_id != run_id
    replayed = await client.get(f"/api/v1/runs/{new_run_id}")
    assert replayed.json()["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_run_not_found_returns_error_envelope(client):
    response = await client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RUN_NOT_FOUND"
