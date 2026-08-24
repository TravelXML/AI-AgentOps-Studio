from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    test_case_count: int
    created_at: datetime


class CreateDatasetRequest(BaseModel):
    name: str
    description: str = ""


class TestCaseInput(BaseModel):
    inputs: dict[str, Any]
    expected_output: Any | None = None


class AddTestCasesRequest(BaseModel):
    cases: list[TestCaseInput]


class TestCaseResponse(BaseModel):
    id: uuid.UUID
    inputs: dict[str, Any]
    expected_output: Any | None


class EvaluatorConfig(BaseModel):
    type: Literal["exact_match", "contains", "regex", "schema", "latency", "cost", "llm_judge"]
    config: dict[str, Any] = {}


class RunEvaluationRequest(BaseModel):
    flow_id: uuid.UUID
    dataset_id: uuid.UUID
    evaluators: list[EvaluatorConfig]
    judge_model: str = "default"


class EvaluationResultResponse(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    run_id: uuid.UUID | None
    passed: bool
    evaluator_results: list[dict[str, Any]]
    actual_output: Any | None
    error: str | None


class EvaluationRunResponse(BaseModel):
    id: uuid.UUID
    flow_id: uuid.UUID
    dataset_id: uuid.UUID
    evaluators: list[dict[str, Any]]
    status: str
    total_cases: int
    passed_cases: int
    created_at: datetime
    results: list[EvaluationResultResponse] = []
