from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import ModelConfigRow, Workspace
from agentq_api.deps import get_app_settings, get_current_workspace
from agentq_api.schemas.model_configs import CreateModelConfigRequest, ModelConfigResponse
from agentq_api.services.audit_service import record_audit_log
from agentq_api.services.model_catalog_service import (
    PROVIDER_VENDOR_MAP,
    CatalogEntry,
    get_catalog,
    search_catalog,
)
from agentq_api.services.secrets_service import SecretsService

router = APIRouter(prefix="/api/v1", tags=["models"])


def _response(row: ModelConfigRow) -> ModelConfigResponse:
    return ModelConfigResponse(
        id=row.id,
        model_key=row.model_key,
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        has_secret=row.secret_id is not None,
        temperature_default=row.temperature_default,
        timeout_seconds=row.timeout_seconds,
        max_retries=row.max_retries,
        created_at=row.created_at,
    )


@router.get("/models", response_model=list[ModelConfigResponse])
async def list_models(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[ModelConfigResponse]:
    result = await session.execute(select(ModelConfigRow).where(ModelConfigRow.workspace_id == workspace.id))
    return [_response(r) for r in result.scalars().all()]


@router.post("/models", response_model=ModelConfigResponse, status_code=201)
async def create_model(
    payload: CreateModelConfigRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> ModelConfigResponse:
    secret_id: uuid.UUID | None = None
    if payload.api_key:
        secrets = SecretsService(session, settings)
        secret = await secrets.create(workspace.id, f"{payload.model_key}-api-key", payload.api_key)
        secret_id = secret.id

    row = ModelConfigRow(
        workspace_id=workspace.id,
        model_key=payload.model_key,
        provider=payload.provider,
        model=payload.model,
        base_url=payload.base_url,
        secret_id=secret_id,
        temperature_default=payload.temperature_default,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
    )
    session.add(row)
    await session.flush()
    await record_audit_log(session, workspace.id, "model_config.created", "model_config", str(row.id))
    await session.commit()
    await session.refresh(row)
    return _response(row)


@router.get("/models/catalog", response_model=list[CatalogEntry])
async def search_model_catalog(
    response: Response,
    q: str | None = Query(default=None, description="Search text matched against model id/name"),
    provider: str | None = Query(default=None, description="Scope results to this provider's vendor"),
    free_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, description="For paging through the full catalog"),
) -> list[CatalogEntry]:
    entries = await get_catalog()
    vendor = PROVIDER_VENDOR_MAP.get(provider) if provider else None
    page, total = search_catalog(
        entries, query=q, vendor=vendor, free_only=free_only, limit=limit, offset=offset
    )
    # A header, not a body-shape change, so the existing plain-array response (what the model
    # combobox already depends on) keeps working unchanged for callers that don't need paging.
    # (Exposed to browser JS via CORSMiddleware's expose_headers in main.py.)
    response.headers["X-Total-Count"] = str(total)
    return page
