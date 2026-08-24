from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.deps import get_app_settings, get_current_workspace
from agentq_api.schemas.architect import GenerateFlowRequest, GenerateFlowResponse
from agentq_api.schemas.errors import ApiError
from agentq_api.services.architect_service import ArchitectError, generate_flowspec
from agentq_api.services.model_gateway_factory import build_model_gateway
from agentq_api.services.secrets_service import SecretsService

router = APIRouter(prefix="/api/v1", tags=["architect"])


@router.post("/architect/generate", response_model=GenerateFlowResponse)
async def generate_flow(
    payload: GenerateFlowRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> GenerateFlowResponse:
    secrets = SecretsService(session, settings)
    gateway = await build_model_gateway(session, workspace.id, secrets)
    try:
        spec, attempts = await generate_flowspec(gateway, payload.model, payload.description)
    except ArchitectError as exc:
        raise ApiError(422, "ARCHITECT_GENERATION_FAILED", str(exc)) from exc
    return GenerateFlowResponse(spec=spec, attempts=attempts)
