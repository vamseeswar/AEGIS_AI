"""AEGIS AI — Pydantic v2 Schemas for Machine Learning Engine
Defines request and response data contracts for model training, evaluation,
time-series forecasting, and unsupervised anomaly detection.
"""

from typing import Any

from pydantic import BaseModel, Field


class MLBaseSchema(BaseModel):
    model_config = {"protected_namespaces": ()}


class MLModelTrainRequest(MLBaseSchema):
    name: str = Field(..., min_length=2, max_length=100, description="Model display name")
    model_type: str = Field(default="FORECASTING", description="FORECASTING or ANOMALY_DETECTION")
    algorithm: str = Field(default="ridge", description="ridge, random_forest, xgboost, or isolation_forest")
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    training_data: list[dict[str, Any]] | None = Field(default=None, description="Optional training rows")
    target_column: str = Field(default="value", description="Target metric column")
    time_column: str = Field(default="timestamp", description="Date/time column")


class MLModelResponse(MLBaseSchema):
    id: str
    organization_id: str
    name: str
    model_type: str
    version: str
    features_json: list[str] | None = None
    hyperparameters: dict[str, Any] | None = None
    metrics_json: dict[str, Any] | None = None
    model_artifact_path: str | None = None
    trained_at: str


class MLForecastRequest(MLBaseSchema):
    model_id: str | None = Field(default=None, description="Trained model ID from registry")
    horizon_steps: int = Field(default=14, ge=1, le=90, description="Forecast horizon in steps/days")
    input_data: list[dict[str, Any]] | None = Field(default=None, description="Recent historical observations")


class ForecastPoint(MLBaseSchema):
    date: str
    forecast: float
    ci_lower: float
    ci_upper: float


class MLForecastResponse(MLBaseSchema):
    model_id: str | None = None
    model_name: str
    horizon_steps: int
    metrics: dict[str, float]
    historical_points: list[dict[str, Any]]
    forecast_points: list[ForecastPoint]


class MLAnomalyDetectRequest(MLBaseSchema):
    model_id: str | None = Field(default=None, description="Trained anomaly model ID")
    input_data: list[dict[str, Any]] | None = Field(default=None, description="Telemetry/metric observations")
    contamination: float = Field(default=0.05, ge=0.01, le=0.5, description="Expected fraction of outliers")


class AnomalyPoint(MLBaseSchema):
    index: int
    is_anomaly: bool
    anomaly_score: float
    top_contributing_feature: str
    feature_z_score: float
    value: float | None = None
    timestamp: str | None = None


class MLAnomalyDetectResponse(MLBaseSchema):
    total_samples: int
    anomaly_count: int
    anomaly_rate_percent: float
    results: list[AnomalyPoint]


class MLPredictionResponse(MLBaseSchema):
    id: str
    ml_model_id: str | None = None
    prediction_type: str
    confidence_score: float | None = None
    created_at: str
