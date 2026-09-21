"""AEGIS AI — Observability, Metrics & Telemetry API Router
REST endpoints for inspecting audit logs, LLM token usage, DLP guardrails,
Prometheus metrics, and system diagnostics:
  GET  /api/v1/observability/audit/logs      - List tenant audit event logs
  POST /api/v1/observability/audit/logs      - Record an audit event
  GET  /api/v1/observability/usage/summary   - Aggregate token and cost breakdown
  POST /api/v1/observability/guardrails/sanitize - Sanitize and test prompt guardrails
  GET  /api/v1/observability/metrics         - Prometheus text exposition format
  GET  /api/v1/observability/health          - System component health diagnostics
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.observability import (
    AuditLogCreate,
    AuditLogListResponse,
    AuditLogResponse,
    GuardrailCheckRequest,
    GuardrailCheckResponse,
    SystemHealthResponse,
    UsageSummaryResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.security.guardrails import GuardrailsEngine
from backend.services import observability_service

observability_router = APIRouter(prefix="/observability", tags=["Observability & Audit"])


@observability_router.get(
    "/audit/logs",
    response_model=AuditLogListResponse,
    summary="List tenant-scoped audit event logs",
)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Retrieves immutable security audit logs for the authenticated organization."""
    records, total = await observability_service.list_audit_logs(
        db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        action=action,
        resource_type=resource_type,
        status=status,
    )
    return AuditLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[AuditLogResponse.model_validate(r) for r in records],
    )


@observability_router.post(
    "/audit/logs",
    response_model=AuditLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an immutable audit event",
)
async def create_audit_log(
    payload: AuditLogCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    """Explicitly records an audit event in the governance ledger."""
    record = await observability_service.record_audit_log(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        status=payload.status,
        details_json=payload.details_json,
    )
    return AuditLogResponse.model_validate(record)


@observability_router.get(
    "/usage/summary",
    response_model=UsageSummaryResponse,
    summary="Aggregate LLM token usage and estimated cost",
)
async def get_usage_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageSummaryResponse:
    """Aggregates cumulative LLM token telemetry and dollar costs by model and provider."""
    summary = await observability_service.get_usage_summary(
        db,
        organization_id=current_user.organization_id,
    )
    return UsageSummaryResponse(**summary)


@observability_router.post(
    "/guardrails/sanitize",
    response_model=GuardrailCheckResponse,
    summary="Inspect text for PII, secrets, and prompt injection",
)
async def sanitize_and_inspect_text(
    payload: GuardrailCheckRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuardrailCheckResponse:
    """Evaluates text against enterprise DLP rules (SSN, credit card, API keys) and injection heuristics."""
    result = GuardrailsEngine.sanitize_and_inspect(
        text=payload.text,
        mask_pii=payload.mask_pii,
        check_injection=payload.check_injection,
    )

    # If injection or sensitive PII is detected, log a security audit event
    if result.has_injection or result.has_pii:
        audit_status = "BLOCKED" if result.has_injection else "REDACTED"
        await observability_service.record_audit_log(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="GUARDRAIL_INSPECTION",
            resource_type="PROMPT_PAYLOAD",
            status=audit_status,
            details_json={
                "pii_types_found": result.pii_types_found,
                "injection_flags": result.injection_flags,
                "redactions_count": result.redactions_count,
            },
        )

    return GuardrailCheckResponse(
        is_safe=result.is_safe,
        has_pii=result.has_pii,
        pii_types_found=result.pii_types_found,
        has_injection=result.has_injection,
        injection_flags=result.injection_flags,
        sanitized_text=result.sanitized_text,
        redactions_count=result.redactions_count,
    )


@observability_router.get(
    "/metrics",
    summary="Export Prometheus plain text metrics",
)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Prometheus exposition format endpoint for scraping system metrics."""
    metrics_text = await observability_service.get_prometheus_metrics(db)
    return Response(content=metrics_text, media_type="text/plain; version=0.0.4")


@observability_router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System component health diagnostics",
)
async def get_health(
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    """Comprehensive health check across database, storage vault, guardrails, and LLM gateway."""
    health_data = await observability_service.get_system_health(db)
    return SystemHealthResponse(**health_data)
