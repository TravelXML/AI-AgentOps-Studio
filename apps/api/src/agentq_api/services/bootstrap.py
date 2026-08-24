"""Development auth mode (spec section 39): a single dev user/workspace is ensured on startup.
The DB model already carries `workspace_id` on every resource, so multi-tenancy is not a later
retrofit - only the auth layer (currently: none, single dev workspace) needs to grow."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.models import Project, User, Workspace, WorkspaceMember

DEV_WORKSPACE_SLUG = "default"
DEV_USER_EMAIL = "dev@agentq.local"
DEV_PROJECT_NAME = "Default Project"


async def ensure_dev_workspace(session: AsyncSession) -> Workspace:
    result = await session.execute(select(Workspace).where(Workspace.slug == DEV_WORKSPACE_SLUG))
    workspace = result.scalar_one_or_none()
    if workspace is not None:
        return workspace

    workspace = Workspace(name="Default Workspace", slug=DEV_WORKSPACE_SLUG)
    user = User(email=DEV_USER_EMAIL, display_name="Dev User")
    session.add_all([workspace, user])
    await session.flush()

    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    session.add(Project(workspace_id=workspace.id, name=DEV_PROJECT_NAME, description=""))
    await session.commit()
    await session.refresh(workspace)
    return workspace


async def get_default_project_id(session: AsyncSession, workspace_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(select(Project).where(Project.workspace_id == workspace_id))
    project = result.scalars().first()
    if project is None:
        project = Project(workspace_id=workspace_id, name=DEV_PROJECT_NAME, description="")
        session.add(project)
        await session.flush()
    return project.id
