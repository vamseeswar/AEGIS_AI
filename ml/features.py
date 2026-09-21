"""AEGIS AI — Time-Series Feature Engineering Module
Generates automated lag features, rolling statistics, calendar seasonality,
and enforces chronological train/test splitting without future data leakage.
"""

import numpy as np
import pandas as pd
from pydantic import BaseModel


class FeatureEngineeringResult(BaseModel):
    feature_names: list[str]
    total_samples: int
    train_samples: int
    test_samples: int


class TimeSeriesFeatureEngineer:
    """Extracts lag and rolling features from sequential time-series data."""

    def __init__(
        self,
        lags: list[int] | None = None,
        rolling_windows: list[int] | None = None,
        target_col: str = "value",
        time_col: str = "timestamp",
    ):
        self.lags = lags or [1, 2, 3, 7]
        self.rolling_windows = rolling_windows or [3, 7]
        self.target_col = target_col
        self.time_col = time_col

    def create_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Transforms raw time series into a rich tabular feature set."""
        data = df.copy()

        # Handle datetime if present
        if self.time_col in data.columns:
            data[self.time_col] = pd.to_datetime(data[self.time_col])
            data = data.sort_values(by=self.time_col).reset_index(drop=True)
            data["day_of_week"] = data[self.time_col].dt.dayofweek
            data["day_of_month"] = data[self.time_col].dt.day
            data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)

        feature_cols = []
        if "day_of_week" in data.columns:
            feature_cols.extend(["day_of_week", "day_of_month", "is_weekend"])

        # Lag features
        for lag in self.lags:
            if len(data) > lag:
                col_name = f"lag_{lag}"
                data[col_name] = data[self.target_col].shift(lag)
                feature_cols.append(col_name)

        # Rolling statistics
        for window in self.rolling_windows:
            if len(data) > window:
                # Shift by 1 so current value is not in rolling mean (avoids target leakage)
                rolling_mean_col = f"rolling_mean_{window}"
                rolling_std_col = f"rolling_std_{window}"
                data[rolling_mean_col] = data[self.target_col].shift(1).rolling(window=window).mean()
                data[rolling_std_col] = data[self.target_col].shift(1).rolling(window=window).std().fillna(0.0)
                feature_cols.extend([rolling_mean_col, rolling_std_col])

        # Drop rows with NaN resulting from shifts
        clean_df = data.dropna(subset=feature_cols + [self.target_col]).reset_index(drop=True)
        return clean_df, feature_cols

    def chronological_split(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        test_ratio: float = 0.2,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Splits time series chronologically without shuffling."""
        n = len(df)
        split_idx = int(n * (1.0 - test_ratio))

        X = df[feature_cols].values
        y = df[self.target_col].values

        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        return X_train, X_test, y_train, y_test

    @staticmethod
    def generate_synthetic_series(
        n_days: int = 90,
        trend: float = 0.5,
        base: float = 100.0,
        noise_scale: float = 5.0,
    ) -> pd.DataFrame:
        """Generates realistic daily operational metrics (revenue, traffic, tokens)."""
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="D")
        t = np.arange(n_days)

        # Weekly seasonality
        seasonality = 15.0 * np.sin(2 * np.pi * t / 7.0)
        noise = np.random.normal(0, noise_scale, n_days)
        values = np.maximum(10.0, base + trend * t + seasonality + noise)

        # Add realistic anomalies safely within array bounds
        if n_days > 20:
            values[15] += 45.0  # Spike
        if n_days > 50:
            values[45] -= 35.0  # Dip
        if n_days > 75:
            values[70] += 55.0  # Spike

        return pd.DataFrame({
            "timestamp": dates.strftime("%Y-%m-%d"),
            "value": np.round(values, 2),
        })
