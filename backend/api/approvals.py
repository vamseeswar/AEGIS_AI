"""AEGIS AI — Human-in-the-Loop (HITL) Approvals API Router
REST endpoints for the approval ticket lifecycle:
  GET  /api/v1/approvals                     - List all tenant approval tickets
  GET  /api/v1/approvals/pending             - List only PENDING tickets
  GET  /api/v1/approvals/{id}               - Get single ticket detail
  POST /api/v1/approvals                     - Create approval ticket (agent/tool trigger)
  POST /api/v1/approvals/{id}/approve        - Human approves a pending ticket
  POST /api/v1/approvals/{id}/reject         - Human rejects a pending ticket
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import ResourceNotFoundError
from backend.db.session import get_db
from backend.schemas.approval import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services import approval_service

approvals_router = APIRouter(prefix="/approvals", tags=["HITL Approvals"])


@approvals_router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List all approval tickets for the tenant",
)
async def list_approvals(
    status_filter: str | None = Query(default=None, description="Filter by status: PENDING, APPROVED, REJECTED, EXPIRED"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """Returns paginated approval tickets for the authenticated user's organization."""
    result = await approval_service.list_approvals(
        db=db,
        organization_id=current_user.organization_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    approvals_out = [ApprovalResponse.model_validate(a) for a in result["approvals"]]
    return ApprovalListResponse(
        approvals=approvals_out,
        total=result["total"],
        pending_count=result["pending_count"],
    )


@approvals_router.get(
    "/pending",
    response_model=ApprovalListResponse,
    summary="List only PENDING approval tickets requiring human decision",
)
async def list_pending_approvals(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """Shortcut endpoint returning only tickets in PENDING status."""
    result = await approval_service.list_approvals(
        db=db,
        organization_id=current_user.organization_id,
        status_filter="PENDING",
        limit=100,
        offset=0,
    )
    approvals_out = [ApprovalResponse.model_validate(a) for a in result["approvals"]]
    return ApprovalListResponse(
        approvals=approvals_out,
        total=result["total"],
        pending_count=result["pending_count"],
    )


@approvals_router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    summary="Get a single approval ticket by ID",
)
async def get_approval(
    approval_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Returns full detail for a single approval ticket, enforcing tenant isolation."""
    try:
        ticket = await approval_service.get_approval(
            db=db,
            approval_id=approval_id,
            organization_id=current_user.organization_id,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ApprovalResponse.model_validate(ticket)


@approvals_router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HITL approval ticket (agent/tool trigger)",
)
async def create_approval(
    payload: ApprovalCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Creates a PENDING approval ticket for a sensitive action requiring human authorization."""
    try:
        ticket = await approval_service.create_approval_ticket(
            db=db,
            organization_id=current_user.organization_id,
            agent_run_id=payload.agent_run_id,
            tool_call_id=payload.tool_call_id,
            requested_by_agent=payload.requested_by_agent,
            action_name=payload.action_name,
            action_payload=payload.action_payload,
            risk_level=payload.risk_level,
            reason=payload.reason,
            requesting_user_id=current_user.id,
            expires_in_minutes=payload.expires_in_minutes,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ApprovalResponse.model_validate(ticket)


@approvals_router.post(
    "/{approval_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve a pending approval ticket and resume the agent workflow",
)
async def approve_ticket(
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Human reviewer approves the pending sensitive action. Records decision in audit log."""
    try:
        ticket = await approval_service.approve_ticket(
            db=db,
            approval_id=approval_id,
            organization_id=current_user.organization_id,
            decided_by_user_id=current_user.id,
            decision_notes=body.decision_notes,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return ApprovalResponse.model_validate(ticket)


@approvals_router.post(
    "/{approval_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject a pending approval ticket and block the agent action",
)
async def reject_ticket(
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Human reviewer rejects the pending sensitive action. Records decision in audit log."""
    try:
        ticket = await approval_service.reject_ticket(
            db=db,
            approval_id=approval_id,
            organization_id=current_user.organization_id,
            decided_by_user_id=current_user.id,
            decision_notes=body.decision_notes,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return ApprovalResponse.model_validate(ticket)
