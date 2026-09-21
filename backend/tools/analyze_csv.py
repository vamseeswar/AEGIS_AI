"""AEGIS AI — Analyze CSV MCP Tool
Performs in-memory statistical profiling, correlation analysis, and grouped aggregations on tabular data.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.analytics.csv_analyzer import CSVAnalyticsEngine
from backend.tools.base import BaseTool, ToolExecutionContext


class AnalyzeCSVArgs(BaseModel):
    csv_content: str = Field(..., description="Raw CSV string or tabular records to profile")
    operation: str = Field(default="profile", description="Operation: 'profile' (descriptive statistics) or 'aggregate'")
    group_by: str | None = Field(default=None, description="Column name for grouped aggregation (when operation is aggregate)")
    agg_col: str | None = Field(default=None, description="Metric column to aggregate (when operation is aggregate)")
    agg_func: str | None = Field(default="mean", description="Aggregation function: 'mean', 'sum', 'count', 'min', 'max'")


class AnalyzeCSVTool(BaseTool):
    name = "analyze_csv"
    description = (
        "Analyzes tabular CSV datasets in memory. Generates summary statistics, null counts, "
        "Pearson correlation matrix, IQR outlier detection, or grouped aggregations."
    )
    category = "ANALYTICS"
    required_permission = "analytics.view"
    args_schema = AnalyzeCSVArgs

    def __init__(self):
        self.engine = CSVAnalyticsEngine()

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        args = self.args_schema(**arguments)

        if args.operation == "aggregate" and args.group_by and args.agg_col:
            agg_results = self.engine.aggregate(
                csv_content=args.csv_content,
                group_by=args.group_by,
                agg_col=args.agg_col,
                agg_func=args.agg_func or "mean",
            )
            return {
                "operation": "aggregate",
                "group_by": args.group_by,
                "agg_col": args.agg_col,
                "agg_func": args.agg_func,
                "data": agg_results,
            }

        profile = self.engine.profile(args.csv_content)
        return {
            "operation": "profile",
            "total_rows": profile.total_rows,
            "total_columns": profile.total_columns,
            "columns": [c.model_dump() for c in profile.columns],
            "correlation_matrix": profile.correlation_matrix.model_dump() if profile.correlation_matrix else None,
            "outliers": [o.model_dump() for o in profile.outliers],
            "suggested_chart": profile.suggested_chart.model_dump() if profile.suggested_chart else None,
        }
