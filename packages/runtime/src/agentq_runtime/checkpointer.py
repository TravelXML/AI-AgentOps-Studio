"""Checkpointer factory. Postgres-backed persistence means a paused (WAITING_FOR_HUMAN) run
survives an API process restart - MemorySaver is used only for tests, where a fresh saver per
test is exactly what's wanted."""

from __future__ import annotations

from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def memory_checkpointer() -> MemorySaver:
    return MemorySaver()


@asynccontextmanager
async def postgres_checkpointer(database_url: str):
    async with AsyncPostgresSaver.from_conn_string(database_url) as saver:
        await saver.setup()
        yield saver
