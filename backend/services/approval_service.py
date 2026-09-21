"""AEGIS AI — Human-in-the-Loop (HITL) Approval Service
Manages the full lifecycle of sensitive-action approval tickets:
  - Creating PENDING approval gates from agent/tool triggers
  - Listing pending/resolved tickets with tenant isolation
  - Recording APPROVED / REJECTED decisions with audit trail
  - Expiring stale tickets that exceeded their TTL
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import ResourceNotFoundError
from backend.models.agent import AgentRun, Approval
from backend.models.governance import AuditLog

logger = logging.getLogger("aegis.approvals")


async def create_approval_ticket(
    *,
    db: AsyncSession,
    organization_id: str,
    agent_run_id: str,
    tool_call_id: str | None,
    requested_by_agent: str,
    action_name: str,
    action_payload: dict[str, Any],
    risk_level: str,
    reason: str,
    requesting_user_id: str,
    expires_in_minutes: int = 60,
) -> Approval:
    """Creates and persists a new PENDING approval ticket.

    Validates that the referenced agent_run belongs to the same organization
    before creating the ticket (tenant isolation).
    """
    # Tenant isolation: verify agent_run belongs to this org
    run_stmt = select(AgentRun).where(
        AgentRun.id == agent_run_id,
        AgentRun.organization_id == organization_id,
    )
    run_res = await db.execute(run_stmt)
    agent_run = run_res.scalar_one_or_none()
    if not agent_run:
        raise ResourceNotFoundError("AgentRun", agent_run_id)

    expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)

    ticket = Approval(
        organization_id=organization_id,
        agent_run_id=agent_run_id,
        tool_call_id=tool_call_id,
        requested_by_agent=requested_by_agent,
        action_name=action_name,
        action_payload=action_payload,
        risk_level=risk_level,
        reason=reason,
        status="PENDING",
        expires_at=expires_at,
    )
    db.add(ticket)

    # Audit log for ticket creation
    audit = AuditLog(
        organization_id=organization_id,
        user_id=requesting_user_id,
        action="APPROVAL_REQUESTED",
        resource_type="approval",
        resource_id=ticket.id,
        status="SUCCESS",
        details_json={
            "action_name": action_name,
            "risk_level": risk_level,
            "agent_run_id": agent_run_id,
            "expires_in_minutes": expires_in_minutes,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(ticket)
    logger.info(f"Created approval ticket {ticket.id} for action '{action_name}' (risk={risk_level})")
    return ticket


async def list_approvals(
    *,
    db: AsyncSession,
    organization_id: str,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lists approval tickets for a tenant with optional status filter."""
    # Auto-expire stale tickets first
    await _expire_stale_tickets(db=db, organization_id=organization_id)

    stmt = select(Approval).where(Approval.organization_id == organization_id)
    if status_filter:
        stmt = stmt.where(Approval.status == status_filter.upper())
    stmt = stmt.order_by(Approval.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    approvals = result.scalars().all()

    # Count totals
    count_stmt = select(func.count(Approval.id)).where(Approval.organization_id == organization_id)
    if status_filter:
        count_stmt = count_stmt.where(Approval.status == status_filter.upper())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    pending_stmt = select(func.count(Approval.id)).where(
        Approval.organization_id == organization_id,
        Approval.status == "PENDING",
    )
    pending_res = await db.execute(pending_stmt)
    pending_count = pending_res.scalar_one()

    return {"approvals": list(approvals), "total": total, "pending_count": pending_count}


async def get_approval(
    *,
    db: AsyncSession,
    approval_id: str,
    organization_id: str,
) -> Approval:
    """Fetches a single approval ticket, enforcing tenant isolation."""
    stmt = select(Approval).where(
        Approval.id == approval_id,
        Approval.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise ResourceNotFoundError("Approval", approval_id)
    return ticket


async def approve_ticket(
    *,
    db: AsyncSession,
    approval_id: str,
    organization_id: str,
    decided_by_user_id: str,
    decision_notes: str | None = None,
) -> Approval:
    """Marks an approval ticket as APPROVED and records the decision."""
    ticket = await get_approval(db=db, approval_id=approval_id, organization_id=organization_id)

    if ticket.status != "PENDING":
        raise ValueError(f"Approval ticket '{approval_id}' is not PENDING (current status: {ticket.status}).")

    # Check expiry
    if ticket.expires_at:
        exp = ticket.expires_at if ticket.expires_at.tzinfo is not None else ticket.expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > exp:
            ticket.status = "EXPIRED"
            await db.commit()
            raise ValueError(f"Approval ticket '{approval_id}' has already expired.")

    ticket.status = "APPROVED"
    ticket.decided_by_user_id = decided_by_user_id
    ticket.decision_notes = decision_notes

    audit = AuditLog(
        organization_id=organization_id,
        user_id=decided_by_user_id,
        action="APPROVAL_GRANTED",
        resource_type="approval",
        resource_id=approval_id,
        status="SUCCESS",
        details_json={
            "action_name": ticket.action_name,
            "risk_level": ticket.risk_level,
            "decision_notes": decision_notes,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(ticket)
    logger.info(f"Approval ticket {approval_id} APPROVED by user {decided_by_user_id}")
    return ticket


async def reject_ticket(
    *,
    db: AsyncSession,
    approval_id: str,
    organization_id: str,
    decided_by_user_id: str,
    decision_notes: str | None = None,
) -> Approval:
    """Marks an approval ticket as REJECTED and records the decision."""
    ticket = await get_approval(db=db, approval_id=approval_id, organization_id=organization_id)

    if ticket.status != "PENDING":
        raise ValueError(f"Approval ticket '{approval_id}' is not PENDING (current status: {ticket.status}).")

    if ticket.expires_at:
        exp = ticket.expires_at if ticket.expires_at.tzinfo is not None else ticket.expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > exp:
            ticket.status = "EXPIRED"
            await db.commit()
            raise ValueError(f"Approval ticket '{approval_id}' has already expired.")

    ticket.status = "REJECTED"
    ticket.decided_by_user_id = decided_by_user_id
    ticket.decision_notes = decision_notes

    audit = AuditLog(
        organization_id=organization_id,
        user_id=decided_by_user_id,
        action="APPROVAL_REJECTED",
        resource_type="approval",
        resource_id=approval_id,
        status="SUCCESS",
        details_json={
            "action_name": ticket.action_name,
            "risk_level": ticket.risk_level,
            "decision_notes": decision_notes,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(ticket)
    logger.info(f"Approval ticket {approval_id} REJECTED by user {decided_by_user_id}")
    return ticket


async def _expire_stale_tickets(*, db: AsyncSession, organization_id: str) -> int:
    """Marks all PENDING tickets past their expiry as EXPIRED. Returns count expired."""
    now = datetime.now(UTC)
    stmt = select(Approval).where(
        Approval.organization_id == organization_id,
        Approval.status == "PENDING",
        Approval.expires_at.isnot(None),
        Approval.expires_at < now,
    )
    result = await db.execute(stmt)
    stale = result.scalars().all()
    for ticket in stale:
        ticket.status = "EXPIRED"
    if stale:
        await db.commit()
        logger.info(f"Expired {len(stale)} stale approval tickets for org {organization_id}")
    return len(stale)
