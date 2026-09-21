"""AEGIS AI — Operational Anomaly Detection Engine
Performs unsupervised anomaly detection using Isolation Forest and rolling z-scores,
computing normalized anomaly risk scores (0.0 - 1.0) and feature explainability attribution.
"""

from typing import Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class IsolationForestAnomalyDetector:
    """Unsupervised anomaly detection with feature-level attribution."""

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )
        self.feature_names: list[str] = []
        self.feature_means: np.ndarray | None = None
        self.feature_stds: np.ndarray | None = None

    def fit(self, X: np.ndarray, feature_names: list[str]) -> dict[str, Any]:
        """Fits the Isolation Forest on the feature matrix."""
        self.feature_names = feature_names
        self.model.fit(X)

        self.feature_means = np.mean(X, axis=0)
        self.feature_stds = np.std(X, axis=0)
        self.feature_stds[self.feature_stds == 0.0] = 1.0  # Prevent division by zero

        # Predict on training samples to calculate base metrics
        preds = self.model.predict(X)
        outlier_count = int(np.sum(preds == -1))
        outlier_rate = float(outlier_count / len(X))

        return {
            "total_samples": len(X),
            "outlier_count": outlier_count,
            "outlier_rate_percent": round(outlier_rate * 100, 2),
            "features_used": feature_names,
        }

    def detect(self, df: pd.DataFrame, feature_cols: list[str]) -> list[dict[str, Any]]:
        """Detects anomalies on dataset rows and computes explainability scores."""
        X = df[feature_cols].values
        preds = self.model.predict(X)  # 1 for inlier, -1 for outlier
        decision_scores = self.model.decision_function(X)

        # Normalize decision scores to risk scores in [0.0, 1.0]
        # In sklearn, lower decision score = more anomalous
        min_score = np.min(decision_scores)
        max_score = np.max(decision_scores)
        score_range = max_score - min_score if max_score > min_score else 1.0
        normalized_risk = 1.0 - ((decision_scores - min_score) / score_range)

        results = []
        for idx, (is_outlier_raw, risk) in enumerate(zip(preds, normalized_risk, strict=False)):
            is_anomaly = bool(is_outlier_raw == -1)

            # Feature explainability: find feature with highest z-score deviation
            top_feature = "unknown"
            highest_z = 0.0
            if self.feature_means is not None and self.feature_stds is not None:
                row_vals = X[idx]
                z_scores = np.abs((row_vals - self.feature_means) / self.feature_stds)
                max_z_idx = int(np.argmax(z_scores))
                top_feature = feature_cols[max_z_idx]
                highest_z = float(z_scores[max_z_idx])

            record = {
                "index": idx,
                "is_anomaly": is_anomaly,
                "anomaly_score": round(float(risk), 4),
                "top_contributing_feature": top_feature,
                "feature_z_score": round(highest_z, 2),
            }

            # If timestamp or id in df, include it
            for col in ("timestamp", "date", "id", "value"):
                if col in df.columns:
                    val = df[col].iloc[idx]
                    if pd.isna(val):
                        record[col] = None
                    elif isinstance(val, (pd.Timestamp, np.datetime64)):
                        record[col] = str(val)
                    elif isinstance(val, (np.floating, float)):
                        record[col] = round(float(val), 2)
                    elif isinstance(val, (np.integer, int)):
                        record[col] = int(val)
                    else:
                        record[col] = str(val)

            results.append(record)

        return results


class RollingZScoreDetector:
    """1D stream anomaly detector using rolling mean and standard deviation."""

    def __init__(self, window: int = 7, threshold_sigma: float = 2.5):
        self.window = window
        self.threshold_sigma = threshold_sigma

    def detect(self, series: pd.Series) -> list[dict[str, Any]]:
        """Detects points where value deviates beyond threshold sigmas."""
        rolling_mean = series.rolling(window=self.window, min_periods=3).mean()
        rolling_std = series.rolling(window=self.window, min_periods=3).std().fillna(1.0)
        rolling_std[rolling_std == 0.0] = 1.0

        z_scores = (series - rolling_mean) / rolling_std

        records = []
        for idx, (val, z) in enumerate(zip(series, z_scores, strict=False)):
            is_anomaly = bool(not np.isnan(z) and abs(z) > self.threshold_sigma)
            records.append({
                "index": idx,
                "value": float(val),
                "z_score": round(float(z), 2) if not np.isnan(z) else 0.0,
                "is_anomaly": is_anomaly,
            })
        return records
