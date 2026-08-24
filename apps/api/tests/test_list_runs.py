import pytest

SIMPLE_SPEC = {
    "id": "placeholder",
    "name": "Simple Agent",
    "nodes": [
        {"id": "input-1", "type": "input", "config": {}},
        {
            "id": "agent-1",
            "type": "agent",
            "config": {"name": "A", "instructions": "Be helpful.", "model": "mock"},
        },
        {"id": "output-1", "type": "output", "config": {}},
    ],
    "edges": [
        {"id": "e1", "source": "input-1", "target": "agent-1"},
        {"id": "e2", "source": "agent-1", "target": "output-1"},
    ],
}


@pytest.mark.asyncio
async def test_list_runs_returns_recent_runs_newest_first(client):
    flow = (await client.post("/api/v1/flows", json={"name": "F", "spec": SIMPLE_SPEC})).json()

    run_ids = []
    for _ in range(2):
        async with client.stream(
            "POST", f"/api/v1/flows/{flow['id']}/runs", json={"inputs": {"query": "hi"}}
        ) as response:
            run_ids.append(response.headers["x-run-id"])
            async for _ in response.aiter_lines():
                pass

    listed = await client.get("/api/v1/runs")
    assert listed.status_code == 200
    body = listed.json()
    listed_ids = [r["id"] for r in body]
    assert listed_ids[0] == run_ids[-1]
    assert set(run_ids).issubset(set(listed_ids))

    scoped = await client.get("/api/v1/runs", params={"flow_id": flow["id"]})
    assert len(scoped.json()) == 2
