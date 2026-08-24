from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.deps import get_app_settings, get_current_workspace
from agentq_api.schemas.knowledge import (
    CreateKnowledgeBaseRequest,
    DocumentResponse,
    KnowledgeBaseResponse,
)
from agentq_api.services.knowledge_service import KnowledgeService, extract_text
from agentq_api.services.model_gateway_factory import build_model_gateway
from agentq_api.services.secrets_service import SecretsService

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


async def _service(session: AsyncSession, workspace: Workspace, settings: Settings) -> KnowledgeService:
    secrets = SecretsService(session, settings)
    gateway = await build_model_gateway(session, workspace.id, secrets)
    return KnowledgeService(session, gateway)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[KnowledgeBaseResponse]:
    service = await _service(session, workspace, settings)
    kbs = await service.list_knowledge_bases(workspace.id)
    return [KnowledgeBaseResponse.model_validate(kb) for kb in kbs]


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    payload: CreateKnowledgeBaseRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> KnowledgeBaseResponse:
    service = await _service(session, workspace, settings)
    kb = await service.create_knowledge_base(workspace.id, payload.name, payload.description)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[DocumentResponse]:
    service = await _service(session, workspace, settings)
    await service.get_knowledge_base(workspace.id, kb_id)
    docs = await service.list_documents(kb_id)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse, status_code=201)
async def ingest_document(
    kb_id: uuid.UUID,
    name: str = Form(...),
    text: str | None = Form(None),
    embedding_model: str | None = Form(None),
    file: UploadFile | None = File(None),
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> DocumentResponse:
    service = await _service(session, workspace, settings)
    kb = await service.get_knowledge_base(workspace.id, kb_id)

    if file is not None:
        raw = await file.read()
        content = extract_text(file.filename or "", raw)
    else:
        content = text or ""

    document = await service.ingest_document(kb, name, content, embedding_model=embedding_model)
    return DocumentResponse.model_validate(document)
