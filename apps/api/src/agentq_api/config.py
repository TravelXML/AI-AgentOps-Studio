from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret: str = "dev-insecure-secret-change-me"

    database_url: str = "postgresql+asyncpg://agentq:agentq@localhost:5432/agentq"
    redis_url: str = "redis://localhost:6379/0"

    default_model_provider: str = "mock"
    ollama_base_url: str = "http://localhost:11434"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None

    # Browsers send the Origin header as whatever hostname is in the address bar - "localhost"
    # and "127.0.0.1" are different origins even though they resolve to the same machine, so
    # both need to be listed or the browser silently drops every API response (the page shell
    # still renders since that's server-side/static; only the data-fetching calls fail).
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def use_postgres_checkpointer(self) -> bool:
        return self.app_env != "test"

    @property
    def checkpointer_database_url(self) -> str:
        """LangGraph's Postgres checkpointer uses psycopg, not asyncpg - strip the SQLAlchemy
        driver suffix so both libraries can share one DATABASE_URL setting."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
