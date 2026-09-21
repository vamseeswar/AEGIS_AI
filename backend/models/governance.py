"""AEGIS AI — Governance, Evaluations, Usage Tracking, and Audit Logs
"""

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TenantScopedMixin, generate_uuid


class Evaluation(Base, TenantScopedMixin):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    eval_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # RAG, AGENT, SQL
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # context_precision, recall, faithfulness, task_success
    score: Mapped[float] = mapped_column(Float, nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(100), default="synthetic_benchmark", nullable=False)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evaluated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class UsageEvent(Base, TenantScopedMixin):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # LLM_CALL, EMBEDDING, TOOL_EXECUTION, RAG_QUERY
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # gemini, openai, local
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class AuditLog(Base, TenantScopedMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # AUTH_LOGIN, DOC_UPLOAD, TOOL_EXECUTE, APPROVAL_GRANTED, SQL_EXECUTE
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, DENIED
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
