"""AEGIS AI — Observability, Telemetry, and Audit Log Schemas
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: str
    details_json: dict[str, Any] | None = None
    created_at: datetime


class AuditLogCreate(BaseModel):
    action: str = Field(..., min_length=2, max_length=100)
    resource_type: str = Field(..., min_length=2, max_length=50)
    resource_id: str | None = None
    status: str = Field(default="SUCCESS", max_length=50)
    details_json: dict[str, Any] | None = None


class AuditLogListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogResponse]


class UsageSummaryItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str
    model_name: str
    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class UsageSummaryResponse(BaseModel):
    total_events: int
    total_tokens: int
    total_estimated_cost_usd: float
    by_provider_model: list[UsageSummaryItem]


class GuardrailCheckRequest(BaseModel):
    text: str = Field(..., min_length=1)
    mask_pii: bool = True
    check_injection: bool = True


class GuardrailCheckResponse(BaseModel):
    is_safe: bool
    has_pii: bool
    pii_types_found: list[str]
    has_injection: bool
    injection_flags: list[str]
    sanitized_text: str
    redactions_count: int


class ComponentHealth(BaseModel):
    name: str
    status: str  # healthy, degraded, error
    latency_ms: float | None = None
    details: dict[str, Any] | None = None


class SystemHealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    timestamp: datetime
    components: list[ComponentHealth]
