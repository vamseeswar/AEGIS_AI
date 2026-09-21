"""AEGIS AI — Evaluations & Benchmarks API Router
REST endpoints for running and inspecting RAG, Agent, and SQL quality evaluation suites:
  POST /api/v1/evaluations/run       - Execute automated quality benchmark suite
  GET  /api/v1/evaluations           - List historical evaluation records
  GET  /api/v1/evaluations/summary   - High-level SLA radar & health scorecard
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.evaluation import (
    EvaluationListItem,
    EvaluationListResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationSummaryResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services import evaluation_service

evaluations_router = APIRouter(prefix="/evaluations", tags=["Quality Evaluations"])


@evaluations_router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an automated quality evaluation benchmark suite",
)
async def run_evaluation(
    payload: EvaluationRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Runs automated benchmarks measuring Context Precision, Recall, Faithfulness, Tool Accuracy, and SQL Safety."""
    result = await evaluation_service.run_evaluation_suite(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        eval_type=payload.eval_type,
        dataset_name=payload.dataset_name,
        sample_limit=payload.sample_limit,
    )
    return EvaluationRunResponse(**result)


@evaluations_router.get(
    "",
    response_model=EvaluationListResponse,
    summary="List historical evaluation metric runs",
)
async def list_evaluations(
    eval_type: str | None = Query(default=None, description="Filter by category: RAG, AGENT, SQL"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationListResponse:
    """Returns paginated evaluation runs and average scores for the tenant."""
    result = await evaluation_service.list_evaluations(
        db=db,
        organization_id=current_user.organization_id,
        eval_type=eval_type,
        limit=limit,
        offset=offset,
    )
    items = [EvaluationListItem.model_validate(e) for e in result["evaluations"]]
    return EvaluationListResponse(
        evaluations=items,
        total=result["total"],
        metric_averages=result["metric_averages"],
    )


@evaluations_router.get(
    "/summary",
    response_model=EvaluationSummaryResponse,
    summary="Get SLA radar summary and benchmark health",
)
async def get_evaluation_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummaryResponse:
    """Returns aggregated SLA health scorecard across all 7 evaluation dimensions."""
    summary_data = await evaluation_service.get_evaluation_summary(
        db=db,
        organization_id=current_user.organization_id,
    )
    return EvaluationSummaryResponse(**summary_data)
