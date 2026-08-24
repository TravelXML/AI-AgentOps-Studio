"""Evaluation (Phase 5): a real evaluation run drives the exact same flow execution path as the
canvas Run button - every test case becomes a genuine Run/RunStep row, not a simulated one - and
grades the result with the configured evaluators. MockLLM's response always echoes the input text
verbatim, so a "contains" evaluator checking for that text is a real, deterministic pass/fail
signal without needing a real model."""

SIMPLE_SPEC = {
    "id": "placeholder",
    "name": "Eval Flow",
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


async def _create_eval_flow(client):
    response = await client.post("/api/v1/flows", json={"name": "Eval Flow", "spec": SIMPLE_SPEC})
    return response.json()["id"]


async def test_create_dataset_and_add_test_cases(client):
    create = await client.post("/api/v1/evaluations/datasets", json={"name": "QA Set"})
    assert create.status_code == 201, create.text
    dataset_id = create.json()["id"]
    assert create.json()["test_case_count"] == 0

    add = await client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/cases",
        json={
            "cases": [{"inputs": {"query": "hello"}}, {"inputs": {"query": "world"}, "expected_output": "x"}]
        },
    )
    assert add.status_code == 201, add.text
    assert len(add.json()) == 2

    listing = await client.get("/api/v1/evaluations/datasets")
    assert any(d["id"] == dataset_id and d["test_case_count"] == 2 for d in listing.json())


async def test_run_evaluation_with_contains_evaluator_passes(client):
    flow_id = await _create_eval_flow(client)
    dataset = await client.post("/api/v1/evaluations/datasets", json={"name": "Contains Set"})
    dataset_id = dataset.json()["id"]
    await client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/cases",
        json={"cases": [{"inputs": {"query": "unique-marker-42"}}]},
    )

    run = await client.post(
        "/api/v1/evaluations/runs",
        json={
            "flow_id": flow_id,
            "dataset_id": dataset_id,
            "evaluators": [{"type": "contains", "config": {"value": "unique-marker-42"}}],
        },
    )
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["status"] == "completed"
    assert body["total_cases"] == 1
    assert body["passed_cases"] == 1
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["passed"] is True
    assert result["run_id"] is not None

    # the evaluation run left a real, browsable Run behind
    real_run = await client.get(f"/api/v1/runs/{result['run_id']}")
    assert real_run.status_code == 200
    assert real_run.json()["status"] == "SUCCEEDED"


async def test_run_evaluation_with_failing_evaluator(client):
    flow_id = await _create_eval_flow(client)
    dataset = await client.post("/api/v1/evaluations/datasets", json={"name": "Fail Set"})
    dataset_id = dataset.json()["id"]
    await client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/cases",
        json={"cases": [{"inputs": {"query": "hello"}}]},
    )

    run = await client.post(
        "/api/v1/evaluations/runs",
        json={
            "flow_id": flow_id,
            "dataset_id": dataset_id,
            "evaluators": [{"type": "contains", "config": {"value": "text that will never appear"}}],
        },
    )
    body = run.json()
    assert body["passed_cases"] == 0
    assert body["results"][0]["passed"] is False


async def test_run_evaluation_on_empty_dataset_fails_honestly(client):
    flow_id = await _create_eval_flow(client)
    dataset = await client.post("/api/v1/evaluations/datasets", json={"name": "Empty Set"})
    dataset_id = dataset.json()["id"]

    run = await client.post(
        "/api/v1/evaluations/runs",
        json={"flow_id": flow_id, "dataset_id": dataset_id, "evaluators": [{"type": "exact_match"}]},
    )
    assert run.status_code == 422
    assert run.json()["error"]["code"] == "EMPTY_DATASET"


async def test_multiple_evaluators_all_must_pass(client):
    flow_id = await _create_eval_flow(client)
    dataset = await client.post("/api/v1/evaluations/datasets", json={"name": "Multi Set"})
    dataset_id = dataset.json()["id"]
    await client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/cases",
        json={"cases": [{"inputs": {"query": "checkme"}}]},
    )

    run = await client.post(
        "/api/v1/evaluations/runs",
        json={
            "flow_id": flow_id,
            "dataset_id": dataset_id,
            "evaluators": [
                {"type": "contains", "config": {"value": "checkme"}},
                {"type": "cost", "config": {"max_usd": 0.0}},
            ],
        },
    )
    body = run.json()
    result = body["results"][0]
    evaluator_names = {r["evaluator"] for r in result["evaluator_results"]}
    assert evaluator_names == {"contains", "cost"}
    # MockLLM has $0 cost, so both evaluators should pass
    assert result["passed"] is True
