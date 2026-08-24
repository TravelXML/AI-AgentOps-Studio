"""Phase 7: /metrics must reflect real activity, not just expose empty counters - a run through
the API should visibly move workflow/LLM counters in the Prometheus text output."""

SIMPLE_SPEC = {
    "id": "placeholder",
    "name": "Metrics Flow",
    "nodes": [
        {"id": "input-1", "type": "input", "label": "Input", "config": {}},
        {
            "id": "agent-1",
            "type": "agent",
            "label": "Assistant",
            "config": {"name": "Assistant", "instructions": "Be helpful.", "model": "default"},
        },
        {"id": "output-1", "type": "output", "label": "Output", "config": {}},
    ],
    "edges": [
        {"id": "e1", "source": "input-1", "target": "agent-1"},
        {"id": "e2", "source": "agent-1", "target": "output-1"},
    ],
}


async def test_metrics_endpoint_is_prometheus_text(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "workflow_runs_total" in response.text


async def test_running_a_flow_increments_workflow_and_llm_counters(client):
    before = (await client.get("/metrics")).text

    create = await client.post("/api/v1/flows", json={"name": "Metrics Flow", "spec": SIMPLE_SPEC})
    flow_id = create.json()["id"]
    response = await client.post(f"/api/v1/flows/{flow_id}/runs", json={"inputs": {"query": "hi"}})
    assert response.status_code == 200

    after = (await client.get("/metrics")).text

    assert _counter_increased(before, after, 'workflow_runs_total{status="SUCCEEDED"}')
    assert _counter_increased(before, after, 'llm_requests_total{model="mock-1",provider="mock"}')


def _counter_value(text: str, metric_line_prefix: str) -> float:
    for line in text.splitlines():
        if line.startswith(metric_line_prefix):
            return float(line.split()[-1])
    return 0.0


def _counter_increased(before: str, after: str, metric_line_prefix: str) -> bool:
    return _counter_value(after, metric_line_prefix) > _counter_value(before, metric_line_prefix)
