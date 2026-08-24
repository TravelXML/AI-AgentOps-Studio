"""Evaluation (Phase 5): runs a dataset's test cases through a flow and grades each result with
the configured evaluators. Reuses `RunExecutionService` - evaluation is not a separate execution
path, it is the exact same flow execution the canvas Run button drives, looped over a dataset and
graded afterward, so every evaluation run leaves a real, browsable Run/RunStep/RunEvent trail.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.db.models import Dataset, EvaluationResult, EvaluationRun, Flow, FlowVersion, TestCase
from agentq_api.schemas.errors import ApiError
from agentq_api.services.run_service import RunExecutionService
from evaluation import EvalContext, run_evaluator
from model_gateway import ModelGateway
from observability import metrics


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_datasets(self, workspace_id: uuid.UUID) -> list[Dataset]:
        result = await self._session.execute(
            select(Dataset).where(Dataset.workspace_id == workspace_id).order_by(Dataset.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_dataset(self, workspace_id: uuid.UUID, name: str, description: str) -> Dataset:
        dataset = Dataset(workspace_id=workspace_id, name=name, description=description)
        self._session.add(dataset)
        await self._session.commit()
        await self._session.refresh(dataset)
        return dataset

    async def get_dataset(self, workspace_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
        result = await self._session.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise ApiError(404, "DATASET_NOT_FOUND", f"Dataset '{dataset_id}' was not found.")
        return dataset

    async def add_test_cases(
        self, dataset: Dataset, cases: list[tuple[dict, object | None]]
    ) -> list[TestCase]:
        rows = [
            TestCase(dataset_id=dataset.id, inputs=inputs, expected_output=expected)
            for inputs, expected in cases
        ]
        self._session.add_all(rows)
        await self._session.commit()
        for row in rows:
            await self._session.refresh(row)
        return rows


class EvaluationService:
    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID) -> None:
        self._session = session
        self._workspace_id = workspace_id

    async def list_runs(self, workspace_id: uuid.UUID) -> list[EvaluationRun]:
        result = await self._session.execute(
            select(EvaluationRun)
            .where(EvaluationRun.workspace_id == workspace_id)
            .order_by(EvaluationRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_run(self, workspace_id: uuid.UUID, evaluation_run_id: uuid.UUID) -> EvaluationRun:
        result = await self._session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == evaluation_run_id, EvaluationRun.workspace_id == workspace_id
            )
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise ApiError(
                404, "EVALUATION_RUN_NOT_FOUND", f"Evaluation run '{evaluation_run_id}' was not found."
            )
        return run

    async def run_evaluation(
        self,
        flow: Flow,
        flow_version: FlowVersion,
        dataset: Dataset,
        evaluators: list[dict],
        *,
        run_service: RunExecutionService,
        gateway: ModelGateway,
        judge_model: str,
    ) -> EvaluationRun:
        if not dataset.test_cases:
            raise ApiError(422, "EMPTY_DATASET", f"Dataset '{dataset.name}' has no test cases.")

        evaluation_run = EvaluationRun(
            workspace_id=self._workspace_id,
            flow_id=flow.id,
            dataset_id=dataset.id,
            evaluators=evaluators,
            status="running",
            total_cases=len(dataset.test_cases),
        )
        self._session.add(evaluation_run)
        await self._session.flush()

        passed_count = 0
        for case in dataset.test_cases:
            result = await self._evaluate_case(
                evaluation_run, flow, flow_version, case, evaluators, run_service, gateway, judge_model
            )
            if result.passed:
                passed_count += 1

        evaluation_run.passed_cases = passed_count
        evaluation_run.status = "completed"
        metrics.evaluation_runs_total.inc()
        await self._session.commit()
        await self._session.refresh(evaluation_run)
        return evaluation_run

    async def _evaluate_case(
        self,
        evaluation_run: EvaluationRun,
        flow: Flow,
        flow_version: FlowVersion,
        case: TestCase,
        evaluators: list[dict],
        run_service: RunExecutionService,
        gateway: ModelGateway,
        judge_model: str,
    ) -> EvaluationResult:
        run = await run_service.create_run(flow, flow_version, case.inputs)
        async for _chunk in run_service.stream_execution(run, flow_version):
            pass  # draining drives execution; persistence is a side effect of the generator

        await self._session.refresh(run)
        duration_ms = None
        if run.started_at and run.completed_at:
            duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000
        total_cost = sum(step.estimated_cost_usd for step in run.steps)
        run_error = None if run.status == "SUCCEEDED" else (run.error or f"run ended in status {run.status}")

        ctx = EvalContext(
            actual_output=run.output,
            expected_output=case.expected_output,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
            run_error=run_error,
        )

        evaluator_results = []
        overall_passed = run_error is None
        for ev in evaluators:
            res = await run_evaluator(ev["type"], ev.get("config", {}), ctx, gateway, judge_model)
            evaluator_results.append({"evaluator": res.evaluator, "passed": res.passed, "detail": res.detail})
            overall_passed = overall_passed and res.passed

        result = EvaluationResult(
            evaluation_run_id=evaluation_run.id,
            test_case_id=case.id,
            run_id=run.id,
            passed=overall_passed,
            evaluator_results=evaluator_results,
            actual_output=run.output,
            error=run_error,
        )
        self._session.add(result)
        await self._session.flush()
        return result
