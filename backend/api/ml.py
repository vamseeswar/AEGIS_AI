"""AEGIS AI — Machine Learning Studio API Endpoints
Provides model training, catalog inspection, time-series forecasting, and anomaly detection.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.ml import (
    MLAnomalyDetectRequest,
    MLAnomalyDetectResponse,
    MLForecastRequest,
    MLForecastResponse,
    MLModelResponse,
    MLModelTrainRequest,
    MLPredictionResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services.ml_service import MLService

ml_router = APIRouter(prefix="/ml", tags=["Machine Learning"])
ml_service = MLService()


@ml_router.post(
    "/models/train",
    response_model=MLModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Train and register a time-series forecasting or anomaly detection model",
)
async def train_model(
    request: MLModelTrainRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MLModelResponse:
    """Trains a Ridge/RandomForest/XGBoost or IsolationForest model and registers it."""
    return await ml_service.train_model(request=request, org_id=current_user.organization_id, db=db)


@ml_router.get(
    "/models",
    response_model=list[MLModelResponse],
    summary="List all registered models for the tenant",
)
async def list_models(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MLModelResponse]:
    """Returns catalog of models trained within caller's organization."""
    return await ml_service.list_models(org_id=current_user.organization_id, db=db)


@ml_router.get(
    "/models/{model_id}",
    response_model=MLModelResponse,
    summary="Get details and metrics for a registered model",
)
async def get_model(
    model_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MLModelResponse:
    """Retrieves hyperparameters, feature list, and evaluation metrics for a model."""
    return await ml_service.get_model(model_id=model_id, org_id=current_user.organization_id, db=db)


@ml_router.post(
    "/forecast",
    response_model=MLForecastResponse,
    summary="Generate future time-series forecasts with 95% confidence intervals",
)
async def forecast(
    request: MLForecastRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MLForecastResponse:
    """Generates multi-step recursive forecasts with confidence bands."""
    return await ml_service.run_forecast(request=request, org_id=current_user.organization_id, db=db)


@ml_router.post(
    "/anomalies/detect",
    response_model=MLAnomalyDetectResponse,
    summary="Detect operational outliers and anomalies with explainability attribution",
)
async def detect_anomalies(
    request: MLAnomalyDetectRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MLAnomalyDetectResponse:
    """Evaluates telemetry with Isolation Forest, scoring risk and top contributing features."""
    return await ml_service.detect_anomalies(request=request, org_id=current_user.organization_id, db=db)


@ml_router.get(
    "/predictions",
    response_model=list[MLPredictionResponse],
    summary="List historical prediction audit records for tenant",
)
async def list_predictions(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MLPredictionResponse]:
    """Returns recent prediction and anomaly logs."""
    return await ml_service.list_predictions(org_id=current_user.organization_id, db=db)
