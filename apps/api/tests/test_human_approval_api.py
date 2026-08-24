import json

import pytest

APPROVAL_SPEC = {
    "id": "placeholder",
    "name": "Refund Approval",
    "nodes": [
        {"id": "input-1", "type": "input", "label": "Input", "config": {}},
        {
            "id": "agent-1",
            "type": "agent",
            "label": "Refund Agent",
            "config": {"name": "Refund Agent", "instructions": "Summarize.", "model": "mock"},
        },
        {
            "id": "approval-1",
            "type": "human_approval",
            "label": "Approval",
            "config": {"message_template": "Approve?"},
        },
        {"id": "output-1", "type": "output", "label": "Output", "config": {}},
    ],
    "edges": [
        {"id": "e1", "source": "input-1", "target": "agent-1"},
        {"id": "e2", "source": "agent-1", "target": "approval-1"},
        {"id": "e3", "source": "approval-1", "target": "output-1"},
    ],
}


async def _stream(client, method, url, **kwargs):
    events = []
    async with client.stream(method, url, **kwargs) as response:
        headers = response.headers
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return headers, events


@pytest.mark.asyncio
async def test_run_pauses_and_resumes_on_approval(client):
    flow_response = await client.post(
        "/api/v1/flows", json={"name": "Refund Approval", "spec": APPROVAL_SPEC}
    )
    flow = flow_response.json()

    headers, events = await _stream(
        client, "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {"amount": 900}}
    )
    run_id = headers["x-run-id"]
    assert events[-1]["type"] == "run.waiting"

    run = await client.get(f"/api/v1/runs/{run_id}")
    assert run.json()["status"] == "WAITING_FOR_HUMAN"

    _, resume_events = await _stream(client, "POST", f"/api/v1/runs/{run_id}/resume", json={"approved": True})
    assert resume_events[-1]["type"] == "run.completed"

    run = await client.get(f"/api/v1/runs/{run_id}")
    assert run.json()["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_rejected_approval_fails_the_run(client):
    flow_response = await client.post(
        "/api/v1/flows", json={"name": "Refund Approval", "spec": APPROVAL_SPEC}
    )
    flow = flow_response.json()

    headers, _ = await _stream(
        client, "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {"amount": 900}}
    )
    run_id = headers["x-run-id"]

    _, resume_events = await _stream(
        client, "POST", f"/api/v1/runs/{run_id}/resume", json={"approved": False}
    )
    assert resume_events[-1]["type"] == "run.failed"

    run = await client.get(f"/api/v1/runs/{run_id}")
    assert run.json()["status"] == "FAILED"


@pytest.mark.asyncio
async def test_resume_before_waiting_is_rejected(client):
    flow_response = await client.post(
        "/api/v1/flows",
        json={
            "name": "Simple",
            "spec": {
                "id": "x",
                "name": "x",
                "nodes": [
                    {"id": "input-1", "type": "input", "config": {}},
                    {"id": "output-1", "type": "output", "config": {}},
                ],
                "edges": [{"id": "e1", "source": "input-1", "target": "output-1"}],
            },
        },
    )
    flow = flow_response.json()
    headers, _ = await _stream(client, "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {}})
    run_id = headers["x-run-id"]

    response = await client.post(f"/api/v1/runs/{run_id}/resume", json={"approved": True})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RUN_NOT_WAITING"
