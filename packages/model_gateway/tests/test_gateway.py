import pytest

from model_gateway import ChatMessage, ModelGateway, ModelGatewayError


@pytest.mark.asyncio
async def test_default_model_id_resolves_to_mock():
    gateway = ModelGateway()
    response = await gateway.complete(
        "default",
        [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="hello"),
        ],
    )
    assert response.provider == "mock"
    assert "hello" in response.content
    assert response.estimated_cost_usd == 0.0
    assert response.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_mock_is_deterministic():
    gateway = ModelGateway()
    messages = [ChatMessage(role="user", content="what is 2+2?")]
    r1 = await gateway.complete("mock", messages)
    r2 = await gateway.complete("mock", messages)
    assert r1.content == r2.content


@pytest.mark.asyncio
async def test_unknown_model_id_raises_actionable_error():
    gateway = ModelGateway()
    with pytest.raises(ModelGatewayError, match="not configured"):
        await gateway.complete("does-not-exist", [ChatMessage(role="user", content="hi")])
