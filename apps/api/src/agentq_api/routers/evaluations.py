from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.base import get_db_session
from agentq_api.db.models import Workspace
from agentq_api.deps import get_app_settings, get_checkpointer, get_current_workspace, get_tool_registry
from agentq_api.schemas.evaluation import (
    AddTestCasesRequest,
    CreateDatasetRequest,
    DatasetResponse,
    EvaluationResultResponse,
    EvaluationRunResponse,
    RunEvaluationRequest,
    TestCaseResponse,
)
from agentq_api.services.evaluation_service import DatasetService, EvaluationService
from agentq_api.services.flow_service import FlowService
from agentq_api.services.model_gateway_factory import build_model_gateway
from agentq_api.services.run_service import build_run_execution_service
from agentq_api.services.secrets_service import SecretsService
from agentq_runtime.tools import ToolRegistry

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


def _dataset_response(dataset) -> DatasetResponse:
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        test_case_count=len(dataset.test_cases),
        created_at=dataset.created_at,
    )


def _test_case_response(case) -> TestCaseResponse:
    return TestCaseResponse(id=case.id, inputs=case.inputs, expected_output=case.expected_output)


def _evaluation_run_response(run) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        flow_id=run.flow_id,
        dataset_id=run.dataset_id,
        evaluators=run.evaluators,
        status=run.status,
        total_cases=run.total_cases,
        passed_cases=run.passed_cases,
        created_at=run.created_at,
        results=[
            EvaluationResultResponse(
                id=r.id,
                test_case_id=r.test_case_id,
                run_id=r.run_id,
                passed=r.passed,
                evaluator_results=r.evaluator_results,
                actual_output=r.actual_output,
                error=r.error,
            )
            for r in run.results
        ],
    )


@router.get("/evaluations/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[DatasetResponse]:
    datasets = await DatasetService(session).list_datasets(workspace.id)
    return [_dataset_response(d) for d in datasets]


@router.post("/evaluations/datasets", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    payload: CreateDatasetRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    dataset = await DatasetService(session).create_dataset(workspace.id, payload.name, payload.description)
    return _dataset_response(dataset)


@router.get("/evaluations/datasets/{dataset_id}/cases", response_model=list[TestCaseResponse])
async def list_test_cases(
    dataset_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[TestCaseResponse]:
    service = DatasetService(session)
    dataset = await service.get_dataset(workspace.id, dataset_id)
    return [_test_case_response(c) for c in dataset.test_cases]


@router.post(
    "/evaluations/datasets/{dataset_id}/cases", response_model=list[TestCaseResponse], status_code=201
)
async def add_test_cases(
    dataset_id: uuid.UUID,
    payload: AddTestCasesRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[TestCaseResponse]:
    service = DatasetService(session)
    dataset = await service.get_dataset(workspace.id, dataset_id)
    rows = await service.add_test_cases(dataset, [(c.inputs, c.expected_output) for c in payload.cases])
    return [_test_case_response(c) for c in rows]


@router.get("/evaluations/runs", response_model=list[EvaluationRunResponse])
async def list_evaluation_runs(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> list[EvaluationRunResponse]:
    runs = await EvaluationService(session, workspace.id).list_runs(workspace.id)
    return [_evaluation_run_response(r) for r in runs]


@router.get("/evaluations/runs/{evaluation_run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    evaluation_run_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationRunResponse:
    run = await EvaluationService(session, workspace.id).get_run(workspace.id, evaluation_run_id)
    return _evaluation_run_response(run)


@router.post("/evaluations/runs", response_model=EvaluationRunResponse, status_code=201)
async def run_evaluation(
    payload: RunEvaluationRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_app_settings),
) -> EvaluationRunResponse:
    flow_service = FlowService(session)
    flow = await flow_service.get_flow(workspace.id, payload.flow_id)
    flow_version = await flow_service.get_latest_version(flow)

    dataset_service = DatasetService(session)
    dataset = await dataset_service.get_dataset(workspace.id, payload.dataset_id)

    run_service = await build_run_execution_service(session, workspace, checkpointer, tools, settings)
    secrets = SecretsService(session, settings)
    gateway = await build_model_gateway(session, workspace.id, secrets)

    evaluation_run = await EvaluationService(session, workspace.id).run_evaluation(
        flow,
        flow_version,
        dataset,
        [e.model_dump() for e in payload.evaluators],
        run_service=run_service,
        gateway=gateway,
        judge_model=payload.judge_model,
    )
    return _evaluation_run_response(evaluation_run)
