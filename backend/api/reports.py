"""AEGIS AI — Executive Reports API Router
REST endpoints for compiling, listing, inspecting, and downloading PDF executive intelligence reports:
  GET    /api/v1/reports             - List all tenant reports
  POST   /api/v1/reports             - Create & compile new executive report
  GET    /api/v1/reports/{id}        - Get report detail with markdown content
  GET    /api/v1/reports/{id}/pdf    - Stream/download rendered ReportLab PDF
  DELETE /api/v1/reports/{id}        - Delete report
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import ResourceNotFoundError
from backend.db.session import get_db
from backend.schemas.report import ReportCreateRequest, ReportListResponse, ReportResponse
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services import report_service

reports_router = APIRouter(prefix="/reports", tags=["Executive Reports"])


@reports_router.get(
    "",
    response_model=ReportListResponse,
    summary="List all executive reports for tenant",
)
async def list_reports(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """Returns paginated executive reports belonging to the user's organization."""
    result = await report_service.list_reports(
        db=db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    reports_out = [ReportResponse.model_validate(r) for r in result["reports"]]
    return ReportListResponse(reports=reports_out, total=result["total"])


@reports_router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compile and persist a new executive report",
)
async def create_report(
    payload: ReportCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Compiles Markdown content into an executive report and renders a publication-grade PDF."""
    report = await report_service.create_report(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        title=payload.title,
        summary=payload.summary,
        content_markdown=payload.content_markdown,
        format=payload.format,
        agent_run_id=payload.agent_run_id,
        charts_data=payload.charts_data,
        metrics_data=payload.metrics_data,
    )
    return ReportResponse.model_validate(report)


@reports_router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get single report details with full markdown",
)
async def get_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Fetches single report detail, enforcing multi-tenant isolation."""
    try:
        report = await report_service.get_report(
            db=db,
            report_id=report_id,
            organization_id=current_user.organization_id,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ReportResponse.model_validate(report)


@reports_router.get(
    "/{report_id}/pdf",
    summary="Download compiled publication-grade PDF artifact",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Executive report PDF document binary stream",
        }
    },
)
async def download_report_pdf(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Streams the compiled PDF binary artifact, updating tenant audit records."""
    try:
        pdf_bytes, filename = await report_service.get_report_pdf_bytes(
            db=db,
            report_id=report_id,
            organization_id=current_user.organization_id,
            requesting_user_id=current_user.id,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@reports_router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report and associated PDF artifact",
)
async def delete_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes report from database and removes filesystem artifact."""
    try:
        await report_service.delete_report(
            db=db,
            report_id=report_id,
            organization_id=current_user.organization_id,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return None
