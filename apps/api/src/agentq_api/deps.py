from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings, get_settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.services.bootstrap import ensure_dev_workspace
from agentq_runtime.tools import ToolRegistry, build_default_registry

_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = build_default_registry()
    return _tool_registry


async def get_session(session: AsyncSession = Depends(get_db_session)) -> AsyncIterator[AsyncSession]:
    yield session


async def get_current_workspace(
    session: AsyncSession = Depends(get_db_session),
) -> Workspace:
    return await ensure_dev_workspace(session)


def get_checkpointer(request: Request):
    return request.app.state.checkpointer


def get_app_settings() -> Settings:
    return get_settings()
