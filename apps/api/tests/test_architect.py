import json

import pytest

from agentq_api.services.architect_service import ArchitectError, generate_flowspec
from model_gateway import ChatMessage, ModelResponse, TokenUsage

VALID_FLOW = {
    "name": "Simple Agent",
    "description": "",
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


class _StubGateway:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, model_id, messages, *, temperature=None, max_tokens=None) -> ModelResponse:
        self.calls.append(list(messages))
        content = self._replies.pop(0)
        return ModelResponse(
            content=content,
            provider="mock",
            model=model_id,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            estimated_cost_usd=0.0,
            latency_ms=1.0,
        )


async def test_generates_valid_flow_on_first_try():
    gateway = _StubGateway([json.dumps(VALID_FLOW)])

    spec, attempts = await generate_flowspec(gateway, "default", "a simple Q&A agent")

    assert attempts == 1
    assert len(spec.nodes) == 3
    assert len(gateway.calls) == 1


async def test_repairs_json_fence_wrapped_response():
    fenced = "```json\n" + json.dumps(VALID_FLOW) + "\n```"
    gateway = _StubGateway([fenced])

    spec, attempts = await generate_flowspec(gateway, "default", "a simple Q&A agent")

    assert attempts == 1
    assert spec.name == "Simple Agent"


async def test_repairs_invalid_json_then_succeeds():
    gateway = _StubGateway(["not json at all", json.dumps(VALID_FLOW)])

    spec, attempts = await generate_flowspec(gateway, "default", "a simple Q&A agent")

    assert attempts == 2
    assert len(spec.nodes) == 3
    # the repair prompt actually carries the parse error back to the model
    second_call_messages = gateway.calls[1]
    assert "not valid JSON" in second_call_messages[-1].content


async def test_repairs_schema_violation_then_succeeds():
    broken = json.dumps({**VALID_FLOW, "nodes": [{"id": "agent-1", "type": "agent", "config": {}}]})
    gateway = _StubGateway([broken, json.dumps(VALID_FLOW)])

    spec, attempts = await generate_flowspec(gateway, "default", "a simple Q&A agent")

    assert attempts == 2
    second_call_messages = gateway.calls[1]
    assert "failed schema validation" in second_call_messages[-1].content


async def test_gives_up_after_max_attempts():
    gateway = _StubGateway(["nope", "still nope", "nope again"])

    with pytest.raises(ArchitectError) as exc_info:
        await generate_flowspec(gateway, "default", "a simple Q&A agent")

    assert exc_info.value.attempts == 3
    assert len(gateway.calls) == 3


async def test_endpoint_with_mock_llm_fails_honestly(client):
    """MockLLM can't follow structured-output instructions - generation should fail with a clear
    error rather than fabricate a flow, proving the repair loop doesn't paper over a bad model."""
    response = await client.post(
        "/api/v1/architect/generate", json={"description": "a customer support agent", "model": "default"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ARCHITECT_GENERATION_FAILED"
