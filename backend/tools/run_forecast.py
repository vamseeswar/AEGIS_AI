"""AEGIS AI — Run Forecast MCP Tool
Generates recursive multi-step time-series projections with 95% confidence intervals.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.ml import MLForecastRequest
from backend.services.ml_service import MLService
from backend.tools.base import BaseTool, ToolExecutionContext


class RunForecastArgs(BaseModel):
    model_config = {"protected_namespaces": ()}

    horizon_steps: int = Field(default=14, ge=1, le=90, description="Number of future time steps to project")
    model_id: str | None = Field(default=None, description="Optional ID of pre-trained forecasting model")
    input_data: list[dict[str, Any]] | None = Field(default=None, description="Optional time-series historical records with timestamp and value")


class RunForecastTool(BaseTool):
    name = "run_forecast"
    description = (
        "Projects future time-series values with expanding 95% confidence interval bounds "
        "using Ridge, Random Forest, or XGBoost autoregressive models."
    )
    category = "ML"
    required_permission = "ml.execute"
    args_schema = RunForecastArgs

    def __init__(self):
        self.ml_service = MLService()

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        args = self.args_schema(**arguments)
        req = MLForecastRequest(
            model_id=args.model_id,
            horizon_steps=args.horizon_steps,
            input_data=args.input_data,
        )

        res = await self.ml_service.run_forecast(
            request=req,
            org_id=context.organization_id,
            db=context.db,
        )

        return {
            "model_id": res.model_id,
            "model_name": res.model_name,
            "horizon_steps": res.horizon_steps,
            "metrics": res.metrics,
            "forecast_points": [p.model_dump() for p in res.forecast_points],
            "total_forecast_points": len(res.forecast_points),
        }
