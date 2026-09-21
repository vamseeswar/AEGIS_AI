"""AEGIS AI — Data Analytics & SQL Analyst Engine
Provides AST-level SQL validation, schema inspection, in-memory tabular/CSV profiling,
and chart visualization generation.
"""

from backend.analytics.charts import ChartConfig, generate_chart_config
from backend.analytics.csv_analyzer import CSVAnalyticsEngine, CSVProfileResult
from backend.analytics.schema import DatabaseSchemaInspector
from backend.analytics.sql_validator import SQLASTValidator, SQLValidationResult

__all__ = [
    "DatabaseSchemaInspector",
    "SQLASTValidator",
    "SQLValidationResult",
    "CSVAnalyticsEngine",
    "CSVProfileResult",
    "ChartConfig",
    "generate_chart_config",
]
