"""AEGIS AI — Database Schema Inspector
Inspects database models and produces tenant-safe, sanitized relational schema representations
for LLM prompt context and frontend catalog exploration.
"""

from typing import Any

from sqlalchemy import Table

from backend.db.base import Base

# Sensitive columns that must never be exposed or queried
SENSITIVE_COLUMNS = {
    "hashed_password",
    "secret",
    "api_key",
    "token",
    "private_key",
}

# Tables that are exposed for analytics queries
ANALYTICS_TABLES = {
    "usage_events",
    "audit_logs",
    "reports",
    "ml_models",
    "ml_predictions",
    "agent_runs",
    "agent_steps",
    "tool_calls",
    "documents",
    "conversations",
    "messages",
    "users",
    "organizations",
}


class DatabaseSchemaInspector:
    """Extracts and sanitizes database schema metadata for analytics."""

    def __init__(self, allowed_tables: set[str] | None = None):
        self.allowed_tables = allowed_tables or ANALYTICS_TABLES

    def get_table_metadata(self, table: Table) -> dict[str, Any]:
        """Extracts column metadata for a single SQLAlchemy table."""
        columns = []
        has_tenant_scope = "organization_id" in table.c

        for col in table.c:
            if col.name in SENSITIVE_COLUMNS:
                continue

            foreign_keys = [
                f"{fk.column.table.name}.{fk.column.name}" for fk in col.foreign_keys
            ]

            columns.append(
                {
                    "name": col.name,
                    "type": str(col.type),
                    "primary_key": bool(col.primary_key),
                    "nullable": bool(col.nullable),
                    "foreign_keys": foreign_keys,
                    "description": col.comment or "",
                }
            )

        return {
            "table_name": table.name,
            "has_tenant_scope": has_tenant_scope,
            "columns": columns,
            "comment": table.comment or "",
        }

    def get_schema_summary(self) -> dict[str, Any]:
        """Returns structured dictionary of accessible tables and their columns."""
        tables_meta = []
        for name, table in Base.metadata.tables.items():
            if name in self.allowed_tables:
                tables_meta.append(self.get_table_metadata(table))

        # Sort tables by name for deterministic consistency
        tables_meta.sort(key=lambda t: t["table_name"])

        return {
            "tables": tables_meta,
            "table_count": len(tables_meta),
            "tenant_isolation_rule": "Queries against tenant-scoped tables must include 'WHERE organization_id = :org_id'.",
        }

    def get_schema_prompt(self, dialect: str = "postgresql") -> str:
        """Generates a compact, LLM-ready schema definition string."""
        summary = self.get_schema_summary()
        lines = [
            f"--- DATABASE SCHEMA ({dialect.upper()}) ---",
            "CRITICAL SECURITY RULES:",
            "1. ONLY write SELECT statements. DML (INSERT, UPDATE, DELETE) and DDL (DROP, CREATE, ALTER) are FORBIDDEN.",
            "2. For any table with 'organization_id', you MUST include 'WHERE organization_id = :org_id'.",
            "3. ALWAYS include a LIMIT clause (maximum 100 rows).",
            "4. Never expose passwords or internal tokens.",
            "",
            "TABLE DEFINITIONS:",
        ]

        for table in summary["tables"]:
            tname = table["table_name"]
            is_tenant = " (TENANT SCOPED)" if table["has_tenant_scope"] else ""
            lines.append(f"TABLE {tname}{is_tenant} (")
            col_defs = []
            for col in table["columns"]:
                fk_str = f" REFERENCES {col['foreign_keys'][0]}" if col["foreign_keys"] else ""
                pk_str = " PRIMARY KEY" if col["primary_key"] else ""
                col_defs.append(f"    {col['name']} {col['type']}{pk_str}{fk_str}")
            lines.append(",\n".join(col_defs))
            lines.append(");")
            lines.append("")

        return "\n".join(lines)
