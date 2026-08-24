from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agentq:agentq@localhost:5432/agentq_test")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import get_settings
from agentq_api.db.base import Base, get_engine, get_session_factory
from agentq_api.main import create_app


@pytest_asyncio.fixture(autouse=True)
async def _clean_database():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    app = create_app()
    from agentq_runtime.checkpointer import memory_checkpointer

    app.state.checkpointer = memory_checkpointer()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
