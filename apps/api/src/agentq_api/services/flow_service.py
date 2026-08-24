from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.models import Flow, FlowVersion
from agentq_api.schemas.errors import ApiError
from agentq_api.services.audit_service import record_audit_log
from flowspec import FlowSpec, ValidationResult, validate_flowspec


class FlowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_flows(self, workspace_id: uuid.UUID) -> list[Flow]:
        result = await self._session.execute(
            select(Flow).where(Flow.workspace_id == workspace_id).order_by(Flow.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_flow(self, workspace_id: uuid.UUID, flow_id: uuid.UUID) -> Flow:
        result = await self._session.execute(
            select(Flow).where(Flow.id == flow_id, Flow.workspace_id == workspace_id)
        )
        flow = result.scalar_one_or_none()
        if flow is None:
            raise ApiError(404, "FLOW_NOT_FOUND", f"Flow '{flow_id}' was not found.")
        return flow

    async def create_flow(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str,
        spec: FlowSpec | None,
    ) -> Flow:
        flow = Flow(workspace_id=workspace_id, project_id=project_id, name=name, description=description)
        self._session.add(flow)
        await self._session.flush()

        if spec is not None:
            await self.save_version(flow, spec)
        await record_audit_log(self._session, workspace_id, "flow.created", "flow", str(flow.id))
        await self._session.commit()
        await self._session.refresh(flow)
        return flow

    async def save_version(self, flow: Flow, spec: FlowSpec) -> FlowVersion:
        result = await self._session.execute(
            select(FlowVersion.version)
            .where(FlowVersion.flow_id == flow.id)
            .order_by(FlowVersion.version.desc())
            .limit(1)
        )
        last_version = result.scalar_one_or_none() or 0
        spec = spec.model_copy(update={"id": str(flow.id), "version": last_version + 1})

        version = FlowVersion(flow_id=flow.id, version=last_version + 1, spec=spec.model_dump(mode="json"))
        self._session.add(version)
        await self._session.flush()
        flow.latest_version_id = version.id
        await self._session.flush()
        return version

    async def get_latest_version(self, flow: Flow) -> FlowVersion:
        if flow.latest_version_id is None:
            raise ApiError(409, "NO_FLOW_VERSION", f'Flow "{flow.name}" has no saved version yet.')
        result = await self._session.execute(
            select(FlowVersion).where(FlowVersion.id == flow.latest_version_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise ApiError(409, "NO_FLOW_VERSION", f'Flow "{flow.name}" has no saved version yet.')
        return version

    async def get_version_by_id(self, flow_version_id: uuid.UUID) -> FlowVersion:
        result = await self._session.execute(select(FlowVersion).where(FlowVersion.id == flow_version_id))
        version = result.scalar_one_or_none()
        if version is None:
            raise ApiError(404, "FLOW_VERSION_NOT_FOUND", f"Flow version '{flow_version_id}' was not found.")
        return version

    async def get_version(self, flow_id: uuid.UUID, version_number: int) -> FlowVersion:
        result = await self._session.execute(
            select(FlowVersion).where(FlowVersion.flow_id == flow_id, FlowVersion.version == version_number)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise ApiError(404, "FLOW_VERSION_NOT_FOUND", f"Version {version_number} was not found.")
        return version

    def validate(self, spec: FlowSpec) -> ValidationResult:
        return validate_flowspec(spec)

    async def publish(self, flow: Flow) -> Flow:
        await self.get_latest_version(flow)  # raises if nothing saved yet
        flow.status = "published"
        await record_audit_log(self._session, flow.workspace_id, "flow.published", "flow", str(flow.id))
        await self._session.commit()
        await self._session.refresh(flow)
        return flow
