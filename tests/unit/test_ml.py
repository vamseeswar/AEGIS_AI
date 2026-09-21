"""AEGIS AI — Machine Learning Engine Test Suite
Tests time-series feature engineering, Ridge/RandomForest/XGBoost regressors,
holdout metrics (MAE/RMSE/R2), multi-step recursive forecasting, Isolation Forest,
model artifact registry, and multi-tenant API endpoints.
"""

import asyncio
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app
from ml.anomaly import IsolationForestAnomalyDetector, RollingZScoreDetector
from ml.features import TimeSeriesFeatureEngineer
from ml.forecasting import TimeSeriesForecaster
from ml.registry import ModelArtifactRegistry


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient with initialized database tables."""
    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await initialize_database()

    asyncio.run(_reset())

    with TestClient(app) as test_client:
        yield test_client


def get_auth_token(client: TestClient, email: str, password: str, org_name: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "ML Engineer",
            "organization_name": org_name,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


# 1. Feature Engineering Tests
def test_feature_engineering_lags_and_splits():
    engineer = TimeSeriesFeatureEngineer(lags=[1, 2, 7], rolling_windows=[3, 7])
    df = engineer.generate_synthetic_series(n_days=60)
    assert len(df) == 60
    assert "timestamp" in df.columns
    assert "value" in df.columns

    feat_df, cols = engineer.create_features(df)
    assert "lag_1" in cols
    assert "lag_2" in cols
    assert "lag_7" in cols
    assert "rolling_mean_3" in cols
    assert "rolling_mean_7" in cols
    assert "day_of_week" in cols

    X_train, X_test, y_train, y_test = engineer.chronological_split(feat_df, cols, test_ratio=0.2)
    assert len(X_train) + len(X_test) == len(feat_df)
    assert len(y_train) + len(y_test) == len(feat_df)
    assert len(X_test) > 0


# 2. Time-Series Forecasting Models Tests (Ridge, Random Forest, XGBoost)
@pytest.mark.parametrize("algorithm", ["ridge", "random_forest", "xgboost"])
def test_forecasting_models_training_and_metrics(algorithm):
    engineer = TimeSeriesFeatureEngineer()
    df = engineer.generate_synthetic_series(n_days=60)
    feat_df, cols = engineer.create_features(df)
    X_train, X_test, y_train, y_test = engineer.chronological_split(feat_df, cols, test_ratio=0.2)

    forecaster = TimeSeriesForecaster(algorithm=algorithm)
    metrics = forecaster.fit(X_train, y_train, X_test, y_test, cols)

    assert "mae" in metrics
    assert "rmse" in metrics
    assert "mape" in metrics
    assert "r2" in metrics
    assert metrics["mae"] >= 0.0
    assert metrics["rmse"] >= 0.0

    # Multi-step forecasting into future
    future_points = forecaster.predict_future(df=df, engineer=engineer, horizon_steps=7)
    assert len(future_points) == 7
    for fp in future_points:
        assert "date" in fp
        assert "forecast" in fp
        assert "ci_lower" in fp
        assert "ci_upper" in fp
        assert fp["ci_lower"] <= fp["forecast"] <= fp["ci_upper"]


# 3. Anomaly Detection Tests (Isolation Forest & Rolling Z-Score)
def test_isolation_forest_anomaly_detection():
    engineer = TimeSeriesFeatureEngineer()
    df = engineer.generate_synthetic_series(n_days=60)
    feat_df, cols = engineer.create_features(df)

    detector = IsolationForestAnomalyDetector(contamination=0.05)
    summary = detector.fit(feat_df[cols].values, cols)

    assert summary["total_samples"] == len(feat_df)
    assert summary["outlier_count"] >= 0

    anomalies = detector.detect(feat_df, cols)
    assert len(anomalies) == len(feat_df)
    assert "is_anomaly" in anomalies[0]
    assert "anomaly_score" in anomalies[0]
    assert "top_contributing_feature" in anomalies[0]
    assert 0.0 <= anomalies[0]["anomaly_score"] <= 1.0


def test_rolling_z_score_detector():
    detector = RollingZScoreDetector(window=7, threshold_sigma=2.0)
    values = [10.0] * 20
    values[10] = 50.0  # Big spike
    series = pd.Series(values)

    results = detector.detect(series)
    assert len(results) == 20
    assert results[10]["is_anomaly"] is True
    assert results[10]["z_score"] > 2.0


# 4. Model Registry Serialization Test
def test_model_artifact_registry(tmp_path):
    registry = ModelArtifactRegistry(base_dir=tmp_path)
    forecaster = TimeSeriesForecaster(algorithm="ridge")
    forecaster.rmse = 3.5

    path = registry.save(forecaster, org_id="org-test", model_id="mod-test")
    assert "mod-test.joblib" in path

    loaded = registry.load(path)
    assert loaded.rmse == 3.5
    assert loaded.algorithm == "ridge"


# 5. Full End-to-End API Endpoints & Multi-Tenancy Tests
def test_ml_api_endpoints_and_tenant_isolation(client):
    token_a = get_auth_token(client, "alice@alpha.com", "Password123!", "Alpha Org")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = get_auth_token(client, "bob@beta.com", "Password123!", "Beta Org")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Train Model for Org A
    train_res = client.post(
        "/api/v1/ml/models/train",
        headers=headers_a,
        json={
            "name": "Alpha Revenue Ridge",
            "model_type": "FORECASTING",
            "algorithm": "ridge",
            "hyperparameters": {"alpha": 1.0},
        },
    )
    assert train_res.status_code == 201
    model_a = train_res.json()
    model_a_id = model_a["id"]
    assert model_a["name"] == "Alpha Revenue Ridge"
    assert "mae" in model_a["metrics_json"]

    # 2. List Models for Org A
    list_res_a = client.get("/api/v1/ml/models", headers=headers_a)
    assert list_res_a.status_code == 200
    models_a = list_res_a.json()
    assert any(m["id"] == model_a_id for m in models_a)

    # 3. Tenant Isolation Check: Org B must NOT see Org A's model
    list_res_b = client.get("/api/v1/ml/models", headers=headers_b)
    assert list_res_b.status_code == 200
    models_b = list_res_b.json()
    assert not any(m["id"] == model_a_id for m in models_b)

    get_b = client.get(f"/api/v1/ml/models/{model_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # 4. Run Forecast using Model A
    forecast_res = client.post(
        "/api/v1/ml/forecast",
        headers=headers_a,
        json={"model_id": model_a_id, "horizon_steps": 14},
    )
    assert forecast_res.status_code == 200
    forecast_data = forecast_res.json()
    assert len(forecast_data["forecast_points"]) == 14
    assert forecast_data["forecast_points"][0]["forecast"] >= 0.0

    # 5. Detect Anomalies Endpoint
    anomaly_res = client.post(
        "/api/v1/ml/anomalies/detect",
        headers=headers_a,
        json={"contamination": 0.05},
    )
    assert anomaly_res.status_code == 200, f"Anomaly detection failed: {anomaly_res.status_code} {anomaly_res.text}"
    anomaly_data = anomaly_res.json()
    assert anomaly_data["total_samples"] > 0
    assert "results" in anomaly_data

    # 6. List Predictions Endpoint
    preds_res = client.get("/api/v1/ml/predictions", headers=headers_a)
    assert preds_res.status_code == 200
    preds = preds_res.json()
    assert len(preds) >= 2  # One forecast + one anomaly
