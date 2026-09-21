"""AEGIS AI — Time-Series Forecasting Engine
Trains real regression models (Ridge, Random Forest, XGBoost),
evaluates holdout partitions (MAE, RMSE, MAPE, R2), and generates multi-step forecasts with confidence intervals.
"""

from typing import Any
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
import xgboost as xgb

from ml.features import TimeSeriesFeatureEngineer


class TimeSeriesForecaster:
    """Trains and executes time series regression models."""

    def __init__(
        self,
        algorithm: str = "ridge",
        hyperparameters: dict[str, Any] | None = None,
    ):
        self.algorithm = algorithm.lower()
        self.hyperparameters = hyperparameters or {}
        self.model: Any = None
        self.feature_names: list[str] = []
        self.metrics: dict[str, float] = {}
        self.rmse: float = 1.0

        self._init_model()

    def _init_model(self) -> None:
        """Initializes the underlying estimator."""
        if self.algorithm == "random_forest":
            n_est = int(self.hyperparameters.get("n_estimators", 50))
            max_d = int(self.hyperparameters.get("max_depth", 5))
            self.model = RandomForestRegressor(n_estimators=n_est, max_depth=max_d, random_state=42)
        elif self.algorithm == "xgboost":
            n_est = int(self.hyperparameters.get("n_estimators", 50))
            max_d = int(self.hyperparameters.get("max_depth", 4))
            lr = float(self.hyperparameters.get("learning_rate", 0.1))
            self.model = xgb.XGBRegressor(n_estimators=n_est, max_depth=max_d, learning_rate=lr, random_state=42)
        else:
            alpha = float(self.hyperparameters.get("alpha", 1.0))
            self.model = Ridge(alpha=alpha, random_state=42)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: list[str],
    ) -> dict[str, float]:
        """Trains the model and evaluates performance on holdout test partition."""
        self.feature_names = feature_names
        self.model.fit(X_train, y_train)

        # Evaluate on holdout test partition
        y_pred = self.model.predict(X_test)

        mae = float(mean_absolute_error(y_test, y_pred))
        mse = float(mean_squared_error(y_test, y_pred))
        rmse = float(np.sqrt(mse))
        mape = float(mean_absolute_percentage_error(y_test, y_pred) * 100)
        r2 = float(r2_score(y_test, y_pred))

        self.rmse = rmse if rmse > 0.0 else 1.0
        self.metrics = {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 4),
            "r2": round(r2, 4),
        }
        return self.metrics

    def predict_future(
        self,
        df: pd.DataFrame,
        engineer: TimeSeriesFeatureEngineer,
        horizon_steps: int = 14,
    ) -> list[dict[str, Any]]:
        """Performs multi-step recursive forecasting into the future."""
        current_data = df.copy()
        current_data[engineer.time_col] = pd.to_datetime(current_data[engineer.time_col])
        current_data = current_data.sort_values(by=engineer.time_col).reset_index(drop=True)

        forecasts = []
        last_date = current_data[engineer.time_col].iloc[-1]

        for step in range(1, horizon_steps + 1):
            next_date = last_date + pd.Timedelta(days=step)

            # Re-generate features for latest row
            feat_df, cols = engineer.create_features(current_data)
            if feat_df.empty:
                break

            latest_X = feat_df[self.feature_names].iloc[-1:].values
            pred_val = float(self.model.predict(latest_X)[0])
            pred_val = max(0.0, pred_val)

            # Confidence bounds: width expands with horizon uncertainty
            uncertainty_mult = np.sqrt(1.0 + 0.1 * step)
            ci_half_width = 1.96 * self.rmse * uncertainty_mult
            ci_lower = max(0.0, round(pred_val - ci_half_width, 2))
            ci_upper = round(pred_val + ci_half_width, 2)

            date_str = next_date.strftime("%Y-%m-%d")
            forecasts.append({
                "date": date_str,
                "forecast": round(pred_val, 2),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            })

            # Append new prediction to current data to support auto-regressive lags
            new_row = pd.DataFrame({
                engineer.time_col: [next_date],
                engineer.target_col: [pred_val],
            })
            current_data = pd.concat([current_data, new_row], ignore_index=True)

        return forecasts
