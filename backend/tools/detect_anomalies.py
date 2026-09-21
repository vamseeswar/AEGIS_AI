"""AEGIS AI — Detect Anomalies MCP Tool
Detects operational outliers and anomalous events using unsupervised Isolation Forest with feature explainability.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.ml import MLAnomalyDetectRequest
from backend.services.ml_service import MLService
from backend.tools.base import BaseTool, ToolExecutionContext


class DetectAnomaliesArgs(BaseModel):
    model_config = {"protected_namespaces": ()}

    contamination: float = Field(default=0.05, ge=0.01, le=0.5, description="Expected proportion of outliers")
    model_id: str | None = Field(default=None, description="Optional ID of trained anomaly model")
    input_data: list[dict[str, Any]] | None = Field(default=None, description="Optional series records to evaluate for anomalies")


class DetectAnomaliesTool(BaseTool):
    name = "detect_anomalies"
    description = (
        "Evaluates telemetry, financial, or operational metrics for anomalies using an Isolation Forest. "
        "Returns anomaly flags, normalized risk scores (0.0 to 1.0), and top contributing feature attribution."
    )
    category = "ML"
    required_permission = "ml.execute"
    args_schema = DetectAnomaliesArgs

    def __init__(self):
        self.ml_service = MLService()

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        args = self.args_schema(**arguments)
        req = MLAnomalyDetectRequest(
            model_id=args.model_id,
            contamination=args.contamination,
            input_data=args.input_data,
        )

        res = await self.ml_service.detect_anomalies(
            request=req,
            org_id=context.organization_id,
            db=context.db,
        )

        anomalies_only = [p.model_dump() for p in res.results if p.is_anomaly]

        return {
            "total_samples": res.total_samples,
            "anomaly_count": res.anomaly_count,
            "anomaly_rate_percent": res.anomaly_rate_percent,
            "detected_anomalies": anomalies_only,
            "all_results": [p.model_dump() for p in res.results],
        }
