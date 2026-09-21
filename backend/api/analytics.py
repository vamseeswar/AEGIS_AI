"""AEGIS AI — SQL Analyst & Data Analytics API Endpoints
Provides schema exploration, natural language SQL compilation, safe query execution,
and in-memory CSV profiling with visualization outputs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analytics.csv_analyzer import CSVAnalyticsEngine, CSVProfileResult
from backend.analytics.schema import DatabaseSchemaInspector
from backend.analytics.sql_validator import SQLASTValidator
from backend.db.session import get_db
from backend.schemas.analytics import (
    CSVAggregateRequest,
    CSVAggregateResponse,
    CSVProfileRequest,
    SchemaSummaryResponse,
    SQLCompileRequest,
    SQLCompileResponse,
    SQLExecuteRequest,
    SQLExecuteResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services.sql_service import SQLService

analytics_router = APIRouter(prefix="/analytics", tags=["Data Analytics & SQL"])

schema_inspector = DatabaseSchemaInspector()
sql_validator = SQLASTValidator()
sql_service = SQLService()
csv_engine = CSVAnalyticsEngine()


@analytics_router.get(
    "/schema",
    response_model=SchemaSummaryResponse,
    summary="Get tenant-accessible database schema and column metadata",
)
async def get_database_schema(
    current_user: CurrentUser = Depends(get_current_user),
) -> SchemaSummaryResponse:
    """Returns accessible database tables, columns, data types, and primary/foreign keys."""
    summary = schema_inspector.get_schema_summary()
    return SchemaSummaryResponse(**summary)


@analytics_router.post(
    "/sql/compile",
    response_model=SQLCompileResponse,
    summary="Translate natural language to validated SQL without executing",
)
async def compile_sql(
    request: SQLCompileRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SQLCompileResponse:
    """Compiles a user prompt into safe SQL and verifies AST safety rules."""
    compiled_sql = await sql_service.compile_nl_to_sql(
        prompt=request.prompt,
        dialect=request.dialect,
    )
    validation = sql_validator.validate(compiled_sql, raise_on_error=True)

    return SQLCompileResponse(
        prompt=request.prompt,
        compiled_sql=validation.sanitized_sql,
        statement_type=validation.statement_type,
        tables_referenced=validation.tables_referenced,
        limit_applied=validation.limit_applied,
        safety_verdict=validation.reason or "PASSED",
    )


@analytics_router.post(
    "/sql/execute",
    response_model=SQLExecuteResponse,
    summary="Execute validated read-only SQL query and generate visualization",
)
async def execute_sql(
    request: SQLExecuteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SQLExecuteResponse:
    """Translates (if NL) or takes raw SQL, verifies AST safety, executes with 5s timeout, and returns charts."""
    return await sql_service.execute_query(
        query=request.query,
        org_id=current_user.org_id,
        user_id=current_user.id,
        db=db,
        is_raw_sql=request.is_raw_sql,
    )


@analytics_router.post(
    "/csv/profile",
    response_model=CSVProfileResult,
    summary="Generate statistical profile, correlation matrix, and outliers for CSV data",
)
async def profile_csv(
    request: CSVProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CSVProfileResult:
    """Computes distributions, percentiles, correlation matrix, and IQR outliers on CSV data."""
    if not request.csv_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV data string must be provided for profiling.",
        )
    return csv_engine.profile(request.csv_data)


@analytics_router.post(
    "/csv/aggregate",
    response_model=CSVAggregateResponse,
    summary="Aggregate CSV data and format series for Recharts visualization",
)
async def aggregate_csv(
    request: CSVAggregateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CSVAggregateResponse:
    """Performs grouped aggregations on CSV columns and formats chart configuration."""
    if not request.csv_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV data string must be provided for aggregation.",
        )
    result = csv_engine.aggregate(
        csv_content=request.csv_data,
        group_by=request.group_by,
        metric_column=request.metric_column,
        agg_func=request.agg_func,
    )
    return CSVAggregateResponse(**result)
