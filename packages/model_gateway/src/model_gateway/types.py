from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Provider = Literal[
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "openrouter",
    "nvidia_nim",
    "azure_openai",
    "bedrock",
    "ollama",
    "custom",
    "mock",
]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None


class ModelConfig(BaseModel):
    """Resolved model configuration. `secret_id` is a reference - never a raw API key."""

    model_config = ConfigDict(extra="forbid")
    id: str
    provider: Provider
    model: str
    base_url: str | None = None
    secret_id: str | None = None
    temperature_default: float = 0.2
    timeout_seconds: float = 60.0
    max_retries: int = 2


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelGatewayError(RuntimeError):
    """Raised when a model call fails after retries or a model_id cannot be resolved."""
