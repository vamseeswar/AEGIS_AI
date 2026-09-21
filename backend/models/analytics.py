"""AEGIS AI — Reports, ML Models, Predictions, and Long/Short-Term Memory
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TenantScopedMixin, generate_uuid


class Report(Base, TenantScopedMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="MARKDOWN", nullable=False)  # MARKDOWN, PDF
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    charts_data: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    metrics_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class MLModel(Base, TenantScopedMixin):
    __tablename__ = "ml_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # FORECASTING, ANOMALY_DETECTION, REGRESSION
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    features_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    hyperparameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # MAE, RMSE, MAPE, Accuracy
    model_artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    predictions: Mapped[list["MLPrediction"]] = relationship(
        "MLPrediction", back_populates="model", cascade="all, delete-orphan"
    )


class MLPrediction(Base, TenantScopedMixin):
    __tablename__ = "ml_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ml_model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=True, index=True)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # FORECAST, ANOMALY
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prediction_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    model: Mapped["MLModel"] = relationship("MLModel", back_populates="predictions")


class Memory(Base, TenantScopedMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(20), default="SHORT_TERM", nullable=False)  # SHORT_TERM, LONG_TERM
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
