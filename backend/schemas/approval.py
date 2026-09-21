"""AEGIS AI — Human-in-the-Loop (HITL) Approval Schemas
Pydantic v2 schemas for approval ticket lifecycle: creation, listing, and decision payloads.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApprovalCreateRequest(BaseModel):
    """Request payload for creating a HITL approval ticket."""

    agent_run_id: str = Field(description="Agent run that triggered this approval gate")
    tool_call_id: str | None = Field(default=None, description="Associated ToolCall record if applicable")
    requested_by_agent: str = Field(description="Name of the agent that requested approval")
    action_name: str = Field(description="The sensitive action requiring authorization")
    action_payload: dict[str, Any] = Field(description="Parameters/payload of the pending action")
    risk_level: str = Field(default="HIGH", description="Risk classification: LOW, MEDIUM, HIGH, CRITICAL")
    reason: str = Field(description="Human-readable justification for why approval is required")
    expires_in_minutes: int = Field(default=60, ge=1, le=1440, description="Ticket TTL in minutes")


class ApprovalDecisionRequest(BaseModel):
    """Request payload for approving or rejecting a pending ticket."""

    decision_notes: str | None = Field(default=None, description="Optional reviewer notes for the audit record")


class ApprovalResponse(BaseModel):
    """Serialized approval ticket for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    tool_call_id: str | None = None
    requested_by_agent: str
    action_name: str
    action_payload: dict[str, Any]
    risk_level: str
    reason: str
    status: str  # PENDING, APPROVED, REJECTED, EXPIRED
    decided_by_user_id: str | None = None
    decision_notes: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    organization_id: str


class ApprovalListResponse(BaseModel):
    """Paginated list of approval tickets."""

    approvals: list[ApprovalResponse]
    total: int
    pending_count: int
