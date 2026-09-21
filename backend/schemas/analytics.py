"""AEGIS AI — Pydantic v2 Schemas for SQL & Data Analytics Engine
Defines request and response models for schema exploration, SQL compilation,
safe query execution, and CSV tabular analytics.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.analytics.charts import ChartConfig


class ColumnMeta(BaseModel):
    name: str
    type: str
    primary_key: bool
    nullable: bool
    foreign_keys: list[str] = Field(default_factory=list)
    description: str = ""


class TableMeta(BaseModel):
    table_name: str
    has_tenant_scope: bool
    columns: list[ColumnMeta]
    comment: str = ""


class SchemaSummaryResponse(BaseModel):
    tables: list[TableMeta]
    table_count: int
    tenant_isolation_rule: str


class SQLCompileRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000, description="Natural language analytics question")
    dialect: str = Field(default="postgresql", description="Target SQL dialect")


class SQLCompileResponse(BaseModel):
    prompt: str
    compiled_sql: str
    statement_type: str
    tables_referenced: list[str]
    limit_applied: int
    safety_verdict: str


class SQLExecuteRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Natural language question or raw SQL")
    is_raw_sql: bool = Field(default=False, description="True if query is already raw SQL, False if natural language")


class SQLExecuteResponse(BaseModel):
    sanitized_sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    duration_ms: float
    safety_audit: str
    visualization: ChartConfig | None = None


class CSVProfileRequest(BaseModel):
    csv_data: str | None = Field(default=None, description="Raw CSV text content")
    document_id: str | None = Field(default=None, description="Optional document ID in storage")


class CSVAggregateRequest(BaseModel):
    csv_data: str | None = Field(default=None, description="Raw CSV text content")
    document_id: str | None = Field(default=None, description="Optional document ID in storage")
    group_by: str = Field(..., description="Categorical column to group by")
    metric_column: str = Field(..., description="Numerical column to aggregate")
    agg_func: str = Field(default="sum", description="Aggregation function: sum, mean, count, min, max")


class CSVAggregateResponse(BaseModel):
    group_by: str
    metric_column: str
    aggregation: str
    records: list[dict[str, Any]]
    chart_config: ChartConfig | None = None
