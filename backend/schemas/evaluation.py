"""AEGIS AI — Evaluation & Quality Benchmarking Schemas
Pydantic v2 schemas for automated RAG, Agent, and SQL evaluation suites.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRunRequest(BaseModel):
    """Payload to trigger an evaluation benchmark run."""

    eval_type: str = Field(default="ALL", description="Evaluation target: RAG, AGENT, SQL, or ALL")
    dataset_name: str = Field(default="synthetic_benchmark_v1", description="Benchmark dataset to evaluate against")
    sample_limit: int = Field(default=10, ge=1, le=100, description="Max test cases to evaluate")


class EvaluationMetricDetail(BaseModel):
    """Result for a single evaluation metric."""

    metric_name: str
    score: float = Field(description="Score between 0.0 and 1.0 (or percentage)")
    threshold: float = Field(description="Enterprise SLA benchmark threshold")
    passed: bool
    description: str
    sample_breakdown: list[dict[str, Any]] | None = None


class EvaluationRunResponse(BaseModel):
    """Result of an evaluation benchmark suite execution."""

    run_id: str
    organization_id: str
    eval_type: str
    dataset_name: str
    overall_score: float
    total_metrics: int
    passed_metrics: int
    all_passed: bool
    metrics: list[EvaluationMetricDetail]
    executed_at: datetime


class EvaluationListItem(BaseModel):
    """Individual persisted evaluation record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    eval_type: str
    metric_name: str
    score: float
    dataset_name: str
    details_json: dict[str, Any] | None = None
    evaluated_by_user_id: str | None = None
    created_at: datetime


class EvaluationListResponse(BaseModel):
    """Paginated collection of evaluation runs and aggregate summary."""

    evaluations: list[EvaluationListItem]
    total: int
    metric_averages: dict[str, float]


class EvaluationSummaryMetric(BaseModel):
    """Current live benchmark metric status."""

    name: str
    key: str
    current_score: float
    target_threshold: float
    status: str  # PASSED, WARNING, FAILED
    category: str  # RAG, AGENT, SQL


class EvaluationSummaryResponse(BaseModel):
    """High-level evaluation health overview across all platform dimensions."""

    overall_health: str  # HEALTHY, DEGRADED
    average_score: float
    metrics: list[EvaluationSummaryMetric]
    last_evaluated_at: datetime | None = None
