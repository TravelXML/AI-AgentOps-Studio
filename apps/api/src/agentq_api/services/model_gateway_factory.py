from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.models import ModelConfigRow
from agentq_api.services.secrets_service import SecretsService
from model_gateway import ModelConfig, ModelGateway


async def build_model_gateway(
    session: AsyncSession, workspace_id: uuid.UUID, secrets: SecretsService
) -> ModelGateway:
    result = await session.execute(select(ModelConfigRow).where(ModelConfigRow.workspace_id == workspace_id))
    rows = result.scalars().all()

    resolved_secrets: dict[str, str] = {}
    for row in rows:
        if row.secret_id is not None:
            value = await secrets.resolve(row.secret_id)
            if value is not None:
                resolved_secrets[str(row.secret_id)] = value

    def secret_resolver(secret_id: str | None) -> str | None:
        return resolved_secrets.get(secret_id) if secret_id else None

    gateway = ModelGateway(secret_resolver=secret_resolver)
    for row in rows:
        gateway.register(
            ModelConfig(
                id=row.model_key,
                provider=row.provider,
                model=row.model,
                base_url=row.base_url,
                secret_id=str(row.secret_id) if row.secret_id else None,
                temperature_default=row.temperature_default,
                timeout_seconds=row.timeout_seconds,
                max_retries=row.max_retries,
            )
        )
    return gateway
