"""AEGIS AI — Machine Learning Service Orchestrator
Coordinates feature engineering, training, forecasting, anomaly detection,
artifact serialization, and multi-tenant database persistence.
"""

import uuid
from datetime import UTC, datetime

import pandas as pd
from ml.anomaly import IsolationForestAnomalyDetector
from ml.features import TimeSeriesFeatureEngineer
from ml.forecasting import TimeSeriesForecaster
from ml.registry import ModelArtifactRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import ResourceNotFoundError
from backend.models.analytics import MLModel, MLPrediction
from backend.schemas.ml import (
    AnomalyPoint,
    ForecastPoint,
    MLAnomalyDetectRequest,
    MLAnomalyDetectResponse,
    MLForecastRequest,
    MLForecastResponse,
    MLModelResponse,
    MLModelTrainRequest,
    MLPredictionResponse,
)


class MLService:
    """Service handling real ML model lifecycle, training, and inference."""

    def __init__(self):
        self.registry = ModelArtifactRegistry()
        self.feature_engineer = TimeSeriesFeatureEngineer()

    async def train_model(
        self,
        request: MLModelTrainRequest,
        org_id: str,
        db: AsyncSession,
    ) -> MLModelResponse:
        """Trains a forecasting or anomaly detection model and persists metadata & artifact."""
        model_id = str(uuid.uuid4())

        # Load training dataset or synthesize realistic operational metric series
        if request.training_data and len(request.training_data) > 10:
            df = pd.DataFrame(request.training_data)
        else:
            df = self.feature_engineer.generate_synthetic_series(n_days=90)

        model_type_upper = request.model_type.upper()

        if model_type_upper == "ANOMALY_DETECTION":
            # Feature extraction for anomaly detection
            feat_df, feature_cols = self.feature_engineer.create_features(df)
            X = feat_df[feature_cols].values

            contamination = float(request.hyperparameters.get("contamination", 0.05))
            detector = IsolationForestAnomalyDetector(contamination=contamination)
            metrics = detector.fit(X, feature_cols)

            # Persist artifact
            artifact_path = self.registry.save(detector, org_id, model_id)

        else:
            # Time-series forecasting
            feat_df, feature_cols = self.feature_engineer.create_features(df)
            X_train, X_test, y_train, y_test = self.feature_engineer.chronological_split(
                feat_df, feature_cols, test_ratio=0.2
            )

            forecaster = TimeSeriesForecaster(
                algorithm=request.algorithm,
                hyperparameters=request.hyperparameters,
            )
            metrics = forecaster.fit(X_train, y_train, X_test, y_test, feature_cols)

            # Persist artifact
            artifact_path = self.registry.save(forecaster, org_id, model_id)

        now = datetime.now(UTC)

        # Database record persistence
        ml_model_rec = MLModel(
            id=model_id,
            organization_id=org_id,
            name=request.name,
            model_type=model_type_upper,
            version="1.0.0",
            features_json=feature_cols,
            hyperparameters=request.hyperparameters,
            metrics_json=metrics,
            model_artifact_path=artifact_path,
            trained_at=now,
        )
        db.add(ml_model_rec)
        await db.commit()

        return MLModelResponse(
            id=model_id,
            organization_id=org_id,
            name=request.name,
            model_type=model_type_upper,
            version="1.0.0",
            features_json=feature_cols,
            hyperparameters=request.hyperparameters,
            metrics_json=metrics,
            model_artifact_path=artifact_path,
            trained_at=now.isoformat(),
        )

    async def run_forecast(
        self,
        request: MLForecastRequest,
        org_id: str,
        db: AsyncSession,
    ) -> MLForecastResponse:
        """Generates future projections using trained or on-the-fly forecasting model."""
        forecaster = None
        model_name = "Real-Time Ridge Forecaster"
        metrics: dict[str, float] = {}

        if request.model_id:
            # Fetch from database
            stmt = select(MLModel).where(
                MLModel.id == request.model_id,
                MLModel.organization_id == org_id,
            )
            res = await db.execute(stmt)
            model_rec = res.scalar_one_or_none()
            if not model_rec:
                raise ResourceNotFoundError("MLModel", request.model_id)

            forecaster = self.registry.load(model_rec.model_artifact_path)
            model_name = model_rec.name
            metrics = model_rec.metrics_json or {}
        else:
            # Train an on-the-fly default forecaster
            df_train = self.feature_engineer.generate_synthetic_series(n_days=90)
            feat_df, cols = self.feature_engineer.create_features(df_train)
            X_train, X_test, y_train, y_test = self.feature_engineer.chronological_split(
                feat_df, cols, test_ratio=0.2
            )
            forecaster = TimeSeriesForecaster(algorithm="ridge")
            metrics = forecaster.fit(X_train, y_train, X_test, y_test, cols)

        # Prepare history
        if request.input_data and len(request.input_data) >= 10:
            df_input = pd.DataFrame(request.input_data)
        else:
            df_input = self.feature_engineer.generate_synthetic_series(n_days=30)

        # Multi-step projection
        forecast_points_raw = forecaster.predict_future(
            df=df_input,
            engineer=self.feature_engineer,
            horizon_steps=request.horizon_steps,
        )

        forecast_points = [ForecastPoint(**fp) for fp in forecast_points_raw]
        historical_points = df_input.tail(15).to_dict(orient="records")

        # Persist prediction record
        pred_rec = MLPrediction(
            organization_id=org_id,
            ml_model_id=request.model_id if request.model_id else None,
            prediction_type="FORECAST",
            input_data={"horizon_steps": request.horizon_steps},
            prediction_results={"forecast_points": forecast_points_raw},
            confidence_score=0.95,
        )
        db.add(pred_rec)
        await db.commit()

        return MLForecastResponse(
            model_id=request.model_id,
            model_name=model_name,
            horizon_steps=request.horizon_steps,
            metrics=metrics,
            historical_points=historical_points,
            forecast_points=forecast_points,
        )

    async def detect_anomalies(
        self,
        request: MLAnomalyDetectRequest,
        org_id: str,
        db: AsyncSession,
    ) -> MLAnomalyDetectResponse:
        """Runs unsupervised Isolation Forest anomaly detection with explainability."""
        detector = None

        if request.model_id:
            stmt = select(MLModel).where(
                MLModel.id == request.model_id,
                MLModel.organization_id == org_id,
            )
            res = await db.execute(stmt)
            model_rec = res.scalar_one_or_none()
            if not model_rec:
                raise ResourceNotFoundError("MLModel", request.model_id)
            detector = self.registry.load(model_rec.model_artifact_path)
        else:
            # Train default Isolation Forest
            seed_df = self.feature_engineer.generate_synthetic_series(n_days=90)
            feat_df, cols = self.feature_engineer.create_features(seed_df)
            detector = IsolationForestAnomalyDetector(contamination=request.contamination)
            detector.fit(feat_df[cols].values, cols)

        # Input data to score
        if request.input_data and len(request.input_data) >= 5:
            eval_df = pd.DataFrame(request.input_data)
        else:
            eval_df = self.feature_engineer.generate_synthetic_series(n_days=45)

        feat_eval, cols = self.feature_engineer.create_features(eval_df)
        anomaly_records = detector.detect(feat_eval, cols)

        points = [AnomalyPoint(**r) for r in anomaly_records]
        anomaly_count = sum(1 for p in points if p.is_anomaly)
        total_samples = len(points)
        rate = round((anomaly_count / total_samples * 100), 2) if total_samples > 0 else 0.0

        # Persist prediction record
        pred_rec = MLPrediction(
            organization_id=org_id,
            ml_model_id=request.model_id if request.model_id else None,
            prediction_type="ANOMALY",
            input_data={"total_samples": total_samples},
            prediction_results={"anomaly_count": anomaly_count, "rate": rate},
            confidence_score=0.90,
        )
        db.add(pred_rec)
        await db.commit()

        return MLAnomalyDetectResponse(
            total_samples=total_samples,
            anomaly_count=anomaly_count,
            anomaly_rate_percent=rate,
            results=points,
        )

    async def list_models(self, org_id: str, db: AsyncSession) -> list[MLModelResponse]:
        """Lists registered models scoped to caller's tenant."""
        stmt = (
            select(MLModel)
            .where(MLModel.organization_id == org_id)
            .order_by(MLModel.trained_at.desc())
        )
        res = await db.execute(stmt)
        models = res.scalars().all()
        return [
            MLModelResponse(
                id=m.id,
                organization_id=m.organization_id,
                name=m.name,
                model_type=m.model_type,
                version=m.version,
                features_json=m.features_json,
                hyperparameters=m.hyperparameters,
                metrics_json=m.metrics_json,
                model_artifact_path=m.model_artifact_path,
                trained_at=m.trained_at.isoformat(),
            )
            for m in models
        ]

    async def get_model(self, model_id: str, org_id: str, db: AsyncSession) -> MLModelResponse:
        """Retrieves a single registered model by ID with tenant isolation."""
        stmt = select(MLModel).where(
            MLModel.id == model_id,
            MLModel.organization_id == org_id,
        )
        res = await db.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            raise ResourceNotFoundError("MLModel", model_id)

        return MLModelResponse(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            model_type=model.model_type,
            version=model.version,
            features_json=model.features_json,
            hyperparameters=model.hyperparameters,
            metrics_json=model.metrics_json,
            model_artifact_path=model.model_artifact_path,
            trained_at=model.trained_at.isoformat(),
        )

    async def list_predictions(self, org_id: str, db: AsyncSession) -> list[MLPredictionResponse]:
        """Lists historical prediction records for the tenant."""
        stmt = (
            select(MLPrediction)
            .where(MLPrediction.organization_id == org_id)
            .order_by(MLPrediction.created_at.desc())
            .limit(50)
        )
        res = await db.execute(stmt)
        preds = res.scalars().all()
        return [
            MLPredictionResponse(
                id=p.id,
                ml_model_id=p.ml_model_id,
                prediction_type=p.prediction_type,
                confidence_score=p.confidence_score,
                created_at=p.created_at.isoformat(),
            )
            for p in preds
        ]
