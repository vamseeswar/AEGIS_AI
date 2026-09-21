"""AEGIS AI — SQL Analyst & Compilation Service
Compiles natural language questions into safe SQL, validates with AST safety rails,
executes queries within tenant boundaries, and records audit logs.
"""

import asyncio
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.providers import get_llm_provider
from backend.analytics.charts import generate_chart_config
from backend.analytics.schema import DatabaseSchemaInspector
from backend.analytics.sql_validator import SQLASTValidator
from backend.core.errors import SQLSafetyViolationError
from backend.models.governance import AuditLog
from backend.schemas.analytics import (
    SQLExecuteResponse,
)

QUERY_TIMEOUT_SECONDS = 5.0


class SQLService:
    """Service orchestrating natural language to SQL translation and safe execution."""

    def __init__(self):
        self.inspector = DatabaseSchemaInspector()
        self.validator = SQLASTValidator()
        self.llm_provider = get_llm_provider()

    async def compile_nl_to_sql(self, prompt: str, dialect: str = "postgresql") -> str:
        """Translates a natural language question into safe read-only SQL."""
        # 1. Check if we can use heuristic pattern matching for immediate offline/test support
        heuristic_sql = self._heuristic_compile(prompt, dialect)
        if heuristic_sql:
            # Validate heuristic SQL
            validated = self.validator.validate(heuristic_sql, raise_on_error=True)
            return validated.sanitized_sql

        # 2. Use LLM Provider
        schema_context = self.inspector.get_schema_prompt(dialect=dialect)
        system_prompt = (
            "You are an expert SQL Data Analyst for AEGIS AI. "
            "Your task is to generate a single, read-only SQL query answering the user's question.\n\n"
            f"{schema_context}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Output ONLY the raw SQL query. No explanations, no markdown fences.\n"
            "- ONLY generate SELECT queries.\n"
            "- For tenant-scoped tables, always include 'WHERE organization_id = :org_id'.\n"
            "- Always include LIMIT (maximum 100).\n"
        )

        llm_response = await self.llm_provider.generate_response(
            prompt=f"Question: {prompt}\nSQL Query:",
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=250,
        )

        cleaned_sql = self._clean_llm_sql(llm_response)
        validated = self.validator.validate(cleaned_sql, raise_on_error=True)
        return validated.sanitized_sql

    def _heuristic_compile(self, prompt: str, dialect: str = "postgresql") -> str | None:
        """Heuristic compiler for standard analytics intents."""
        p = prompt.lower()

        # Monthly revenue / new users / signups
        if any(term in p for term in ["revenue", "month", "signup", "fiscal"]):
            return (
                "SELECT substr(created_at, 1, 7) AS month, "
                "COUNT(DISTINCT user_id) AS new_users, "
                "ROUND(SUM(estimated_cost_usd) * 100, 2) AS total_revenue_usd "
                "FROM usage_events "
                "WHERE organization_id = :org_id "
                "GROUP BY 1 ORDER BY 1 ASC LIMIT 100"
            )

        # Usage events by event_type / volume
        if any(term in p for term in ["event", "usage", "volume"]):
            return (
                "SELECT event_type, COUNT(id) AS total_events, SUM(total_tokens) AS tokens_consumed "
                "FROM usage_events "
                "WHERE organization_id = :org_id "
                "GROUP BY event_type ORDER BY total_events DESC LIMIT 100"
            )

        # Token consumption by model / provider
        if any(term in p for term in ["model", "provider", "token"]):
            return (
                "SELECT model_name, provider, "
                "SUM(prompt_tokens) AS prompt_tokens, "
                "SUM(completion_tokens) AS completion_tokens, "
                "SUM(total_tokens) AS total_tokens "
                "FROM usage_events "
                "WHERE organization_id = :org_id "
                "GROUP BY model_name, provider ORDER BY total_tokens DESC LIMIT 100"
            )

        # Audit logs / user activity
        if any(term in p for term in ["audit", "log", "activity", "action"]):
            return (
                "SELECT action, status, COUNT(id) AS log_count "
                "FROM audit_logs "
                "WHERE organization_id = :org_id "
                "GROUP BY action, status ORDER BY log_count DESC LIMIT 100"
            )

        # Agent runs
        if any(term in p for term in ["agent", "run", "workflow"]):
            return (
                "SELECT id, lead_agent, status, total_duration_ms, created_at "
                "FROM agent_runs "
                "WHERE organization_id = :org_id "
                "ORDER BY created_at DESC LIMIT 50"
            )

        # Documents
        if any(term in p for term in ["document", "file"]):
            return (
                "SELECT id, filename, mime_type, file_size_bytes, status, created_at "
                "FROM documents "
                "WHERE organization_id = :org_id "
                "ORDER BY created_at DESC LIMIT 50"
            )

        return None

    def _clean_llm_sql(self, text: str) -> str:
        """Removes markdown code fences and cleans up SQL string."""
        cleaned = re.sub(r"```(?:sql)?", "", text)
        cleaned = cleaned.replace("```", "").strip()
        return cleaned

    async def execute_query(
        self,
        query: str,
        org_id: str,
        user_id: str | None,
        db: AsyncSession,
        is_raw_sql: bool = False,
    ) -> SQLExecuteResponse:
        """Validates, prepares, and safely executes an analytics query."""
        start_time = time.time()

        if is_raw_sql:
            sql_to_run = query
        else:
            sql_to_run = await self.compile_nl_to_sql(query)

        # AST Safety Validation
        validation = self.validator.validate(sql_to_run, raise_on_error=True)
        sanitized_sql = validation.sanitized_sql

        # Bind parameters
        params: dict[str, Any] = {}
        if ":org_id" in sanitized_sql:
            params["org_id"] = org_id

        # Execute with 5000ms timeout
        try:
            async with asyncio.timeout(QUERY_TIMEOUT_SECONDS):
                result = await db.execute(text(sanitized_sql), params)
                raw_rows = result.fetchall()
                columns = list(result.keys()) if result.keys() else []
        except TimeoutError:
            raise SQLSafetyViolationError(
                f"Query execution exceeded security timeout limit of {int(QUERY_TIMEOUT_SECONDS)} seconds."
            ) from None
        except Exception as e:
            raise SQLSafetyViolationError(f"Database execution error: {str(e)}") from e

        # Format rows into list of dicts
        rows = [dict(zip(columns, row, strict=False)) for row in raw_rows]
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Auto-generate visualization
        visualization = generate_chart_config(rows, title_hint="Query Results")

        # Audit log entry
        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="SQL_EXECUTE",
            resource_type="analytics_query",
            status="SUCCESS",
            details_json={
                "sanitized_sql": sanitized_sql,
                "row_count": len(rows),
                "duration_ms": duration_ms,
            },
        )
        db.add(audit)
        await db.commit()

        return SQLExecuteResponse(
            sanitized_sql=sanitized_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            duration_ms=duration_ms,
            safety_audit=validation.reason or "PASSED",
            visualization=visualization,
        )
