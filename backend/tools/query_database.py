"""AEGIS AI — Query Database MCP Tool
Compiles and executes read-only SQL queries with strict AST safety validation and tenant boundaries.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.services.sql_service import SQLService
from backend.tools.base import BaseTool, ToolExecutionContext


class QueryDatabaseArgs(BaseModel):
    query: str = Field(..., description="SQL query or natural language data question")
    is_natural_language: bool = Field(default=False, description="Whether query is natural language or raw SQL")
    limit: int = Field(default=50, ge=1, le=100, description="Max rows to return")


class QueryDatabaseTool(BaseTool):
    name = "query_database"
    description = (
        "Executes a validated read-only SQL query against tenant database tables. "
        "Strictly forbids DDL/DML, enforces LIMIT, and bounds queries to tenant organization_id."
    )
    category = "DATABASE"
    required_permission = "database.query"
    args_schema = QueryDatabaseArgs

    def __init__(self):
        self.sql_service = SQLService()

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        args = self.args_schema(**arguments)

        raw_sql = args.query
        if args.is_natural_language:
            raw_sql = await self.sql_service.compile_nl_to_sql(prompt=args.query)

        exec_res = await self.sql_service.execute_query(
            query=raw_sql,
            org_id=context.organization_id,
            user_id=context.user_id,
            db=context.db,
            is_raw_sql=True,
        )

        return {
            "executed_sql": exec_res.sanitized_sql,
            "row_count": exec_res.row_count,
            "columns": exec_res.columns,
            "rows": exec_res.rows[:args.limit],
            "execution_time_ms": exec_res.duration_ms,
        }
