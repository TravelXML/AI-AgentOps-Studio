"""Memory (Phase 4): conversation memory (scope="agent", the default) persists across separate
runs of the same flow keyed by node id - proven by running the same flow twice and checking the
second run's output contains both turns. Semantic memory reuses the same MockEmbedding + pgvector
mechanism RAG uses, scoped to memory entries rather than a knowledge base."""


async def _create_memory_flow(client, memory_type="conversation", scope="agent"):
    spec = {
        "id": "placeholder",
        "name": "Memory Flow",
        "nodes": [
            {"id": "input-1", "type": "input", "label": "Input", "config": {}},
            {
                "id": "memory-1",
                "type": "memory",
                "label": "Memory",
                "config": {"memory_type": memory_type, "scope": scope},
            },
            {"id": "output-1", "type": "output", "label": "Output", "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "input-1", "target": "memory-1"},
            {"id": "e2", "source": "memory-1", "target": "output-1"},
        ],
    }
    response = await client.post("/api/v1/flows", json={"name": "Memory Flow", "spec": spec})
    return response.json()["id"]


async def _run(client, flow_id, text):
    response = await client.post(f"/api/v1/flows/{flow_id}/runs", json={"inputs": {"text": text}})
    assert response.status_code == 200, response.text
    run_id = response.headers["x-run-id"]
    run = await client.get(f"/api/v1/runs/{run_id}")
    body = run.json()
    assert body["status"] == "SUCCEEDED", body
    return body["output"]


async def test_conversation_memory_persists_across_runs_scoped_by_agent(client):
    flow_id = await _create_memory_flow(client, memory_type="conversation", scope="agent")

    first_output = await _run(client, flow_id, "my first message")
    assert "my first message" in first_output

    second_output = await _run(client, flow_id, "my second message")
    assert "my first message" in second_output
    assert "my second message" in second_output


async def test_conversation_memory_scoped_by_run_does_not_leak_between_runs(client):
    flow_id = await _create_memory_flow(client, memory_type="conversation", scope="run")

    await _run(client, flow_id, "run one only")
    second_output = await _run(client, flow_id, "run two only")

    assert "run one only" not in second_output
    assert "run two only" in second_output


async def test_semantic_memory_recalls_the_fact_just_stored(client):
    flow_id = await _create_memory_flow(client, memory_type="semantic", scope="agent")

    output = await _run(client, flow_id, "the sky is blue and vast")
    assert "the sky is blue and vast" in output
