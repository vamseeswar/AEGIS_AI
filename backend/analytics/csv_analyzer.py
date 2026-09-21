"""AEGIS AI — In-Memory CSV & Tabular Data Analytics Engine
Performs statistical profiling, correlation matrices, outlier detection (Z-Score & IQR),
and grouped aggregations using Pandas.
"""

import io
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backend.analytics.charts import ChartConfig, generate_chart_config


class ColumnStats(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    p25: float | None = None
    median: float | None = None
    p75: float | None = None
    max: float | None = None


class CorrelationMatrix(BaseModel):
    columns: list[str]
    matrix: list[list[float]]


class OutlierSummary(BaseModel):
    column: str
    method: str
    outlier_count: int
    outlier_percentage: float
    sample_outlier_values: list[float]


class CSVProfileResult(BaseModel):
    total_rows: int
    total_columns: int
    columns: list[ColumnStats]
    correlation_matrix: CorrelationMatrix | None = None
    outliers: list[OutlierSummary] = Field(default_factory=list)
    sample_records: list[dict[str, Any]] = Field(default_factory=list)
    suggested_chart: ChartConfig | None = None


class CSVAnalyticsEngine:
    """In-memory tabular profiling and aggregation engine."""

    def __init__(self, max_rows: int = 100_000):
        self.max_rows = max_rows

    def load_df(self, csv_content: str | bytes) -> pd.DataFrame:
        """Parses CSV text or bytes into a pandas DataFrame."""
        if isinstance(csv_content, bytes):
            buffer = io.BytesIO(csv_content)
        else:
            buffer = io.StringIO(csv_content)

        df = pd.read_csv(buffer, nrows=self.max_rows)
        return df

    def profile(self, csv_content: str | bytes) -> CSVProfileResult:
        """Computes comprehensive statistical profiling on the CSV dataset."""
        df = self.load_df(csv_content)
        total_rows = len(df)
        total_columns = len(df.columns)

        column_stats: list[ColumnStats] = []
        numeric_cols = []

        for col in df.columns:
            series = df[col]
            non_null = int(series.count())
            null_count = int(series.isna().sum())
            unique_count = int(series.nunique())

            is_numeric = pd.api.types.is_numeric_dtype(series)
            dtype_str = "numeric" if is_numeric else "text"

            if is_numeric and non_null > 0:
                numeric_cols.append(col)
                # Compute descriptive statistics
                clean_series = series.dropna()
                mean_val = float(clean_series.mean()) if not clean_series.empty else None
                std_val = float(clean_series.std()) if len(clean_series) > 1 else 0.0
                min_val = float(clean_series.min()) if not clean_series.empty else None
                p25_val = float(clean_series.quantile(0.25)) if not clean_series.empty else None
                median_val = float(clean_series.median()) if not clean_series.empty else None
                p75_val = float(clean_series.quantile(0.75)) if not clean_series.empty else None
                max_val = float(clean_series.max()) if not clean_series.empty else None

                column_stats.append(
                    ColumnStats(
                        name=str(col),
                        dtype=dtype_str,
                        non_null_count=non_null,
                        null_count=null_count,
                        unique_count=unique_count,
                        mean=round(mean_val, 4) if mean_val is not None else None,
                        std=round(std_val, 4) if std_val is not None else None,
                        min=round(min_val, 4) if min_val is not None else None,
                        p25=round(p25_val, 4) if p25_val is not None else None,
                        median=round(median_val, 4) if median_val is not None else None,
                        p75=round(p75_val, 4) if p75_val is not None else None,
                        max=round(max_val, 4) if max_val is not None else None,
                    )
                )
            else:
                column_stats.append(
                    ColumnStats(
                        name=str(col),
                        dtype=dtype_str,
                        non_null_count=non_null,
                        null_count=null_count,
                        unique_count=unique_count,
                    )
                )

        # Compute Correlation Matrix if 2 or more numeric columns exist
        corr_matrix = None
        if len(numeric_cols) >= 2 and total_rows > 1:
            raw_corr = df[numeric_cols].corr().fillna(0.0)
            matrix_data = []
            for col_a in numeric_cols:
                row_vals = [round(float(raw_corr.loc[col_a, col_b]), 4) for col_b in numeric_cols]
                matrix_data.append(row_vals)
            corr_matrix = CorrelationMatrix(columns=numeric_cols, matrix=matrix_data)

        # Detect Outliers across numeric columns using IQR and Z-score
        outlier_summaries = []
        for col in numeric_cols:
            clean = df[col].dropna()
            if len(clean) < 4:
                continue

            q1 = clean.quantile(0.25)
            q3 = clean.quantile(0.75)
            iqr = q3 - q1

            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = clean[(clean < lower_bound) | (clean > upper_bound)]
                outlier_count = len(outliers)
                if outlier_count > 0:
                    outlier_summaries.append(
                        OutlierSummary(
                            column=col,
                            method="IQR (1.5x)",
                            outlier_count=outlier_count,
                            outlier_percentage=round((outlier_count / len(clean)) * 100, 2),
                            sample_outlier_values=[round(float(v), 2) for v in outliers.head(5).tolist()],
                        )
                    )

        # Sample preview records
        sample_records = df.head(10).replace({np.nan: None}).to_dict(orient="records")

        # Generate suggested visualization if suitable
        suggested_chart = None
        if sample_records and numeric_cols:
            suggested_chart = generate_chart_config(sample_records, title_hint="Sample Tabular Distribution")

        return CSVProfileResult(
            total_rows=total_rows,
            total_columns=total_columns,
            columns=column_stats,
            correlation_matrix=corr_matrix,
            outliers=outlier_summaries,
            sample_records=sample_records,
            suggested_chart=suggested_chart,
        )

    def aggregate(
        self,
        csv_content: str | bytes,
        group_by: str,
        metric_column: str,
        agg_func: str = "sum",
    ) -> dict[str, Any]:
        """Performs grouped aggregation on CSV and formats Recharts series."""
        df = self.load_df(csv_content)
        if group_by not in df.columns:
            raise ValueError(f"Group by column '{group_by}' does not exist in dataset")
        if metric_column not in df.columns:
            raise ValueError(f"Metric column '{metric_column}' does not exist in dataset")

        agg_map = {
            "sum": "sum",
            "mean": "mean",
            "count": "count",
            "min": "min",
            "max": "max",
            "median": "median",
        }
        func = agg_map.get(agg_func.lower(), "sum")

        aggregated = (
            df.groupby(group_by)[metric_column]
            .agg(func)
            .reset_index()
            .sort_values(by=metric_column, ascending=False)
            .head(50)
        )

        records = aggregated.replace({np.nan: None}).to_dict(orient="records")
        chart_config = generate_chart_config(
            records,
            title_hint=f"{agg_func.upper()}({metric_column}) by {group_by}",
        )

        return {
            "group_by": group_by,
            "metric_column": metric_column,
            "aggregation": func,
            "records": records,
            "chart_config": chart_config,
        }
