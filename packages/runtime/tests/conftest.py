import pytest

from agentq_runtime import FlowCompiler, LangGraphRuntime, build_default_registry
from agentq_runtime.checkpointer import memory_checkpointer
from model_gateway import ModelGateway


@pytest.fixture
def gateway() -> ModelGateway:
    return ModelGateway()


@pytest.fixture
def tools():
    return build_default_registry()


@pytest.fixture
def runtime(gateway, tools) -> LangGraphRuntime:
    return LangGraphRuntime(FlowCompiler(gateway, tools))


@pytest.fixture
def checkpointer():
    return memory_checkpointer()
