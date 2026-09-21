"""AEGIS AI — AST-Level SQL Safety Validator
Uses `sqlparse` to parse, inspect, and enforce strict read-only safety,
tenant isolation boundaries, and query limit constraints.
"""

import re
from dataclasses import dataclass
from typing import Any

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Statement
from sqlparse.tokens import DDL, DML, Keyword

from backend.core.errors import SQLSafetyViolationError

# Forbidden SQL Command Keywords (DDL, DML, and Administrative)
FORBIDDEN_KEYWORDS = {
    # DML
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "REPLACE",
    "UPSERT",
    # DDL
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "RENAME",
    # Administrative & Execution
    "EXEC",
    "EXECUTE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "GRANT",
    "REVOKE",
    "SHUTDOWN",
    "LOAD_EXTENSION",
    "SYSTEM",
    "INTO OUTFILE",
    "INTO DUMPFILE",
}

# Forbidden System / Sensitive Tables
FORBIDDEN_TABLES = {
    "pg_shadow",
    "pg_authid",
    "pg_user",
    "sqlite_master",
    "sqlite_temp_master",
}

DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 500


@dataclass
class SQLValidationResult:
    is_safe: bool
    sanitized_sql: str
    statement_type: str
    limit_applied: int
    tables_referenced: list[str]
    reason: str | None = None
    details: dict[str, Any] | None = None


class SQLASTValidator:
    """Validates SQL statements at the AST / token level before execution."""

    def __init__(
        self,
        default_limit: int = DEFAULT_QUERY_LIMIT,
        max_limit: int = MAX_QUERY_LIMIT,
        require_tenant_filter: bool = True,
    ):
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.require_tenant_filter = require_tenant_filter

    def validate(
        self,
        sql: str,
        raise_on_error: bool = True,
        tenant_scoped_tables: set[str] | None = None,
    ) -> SQLValidationResult:
        """Inspects SQL text, validates AST tokens, enforces LIMIT, and verifies tenant scoping.

        Args:
            sql: Raw SQL query string.
            raise_on_error: If True, raises SQLSafetyViolationError when invalid.
            tenant_scoped_tables: Set of table names requiring organization_id filtering.

        Returns:
            SQLValidationResult containing sanitized query and validation metadata.
        """
        trimmed_sql = sql.strip()
        if not trimmed_sql:
            return self._fail("SQL query cannot be empty", raise_on_error)

        # 1. Reject multiple statements separated by semicolons
        statements = [s for s in sqlparse.parse(trimmed_sql) if str(s).strip()]
        if len(statements) == 0:
            return self._fail("No valid SQL statement found", raise_on_error)
        if len(statements) > 1:
            return self._fail(
                "Multiple statements detected. Only a single SELECT query is permitted.",
                raise_on_error,
            )

        statement = statements[0]
        statement_type = statement.get_type()

        # 2. Enforce SELECT type (or CTE with SELECT)
        raw_upper = trimmed_sql.upper()
        if statement_type != "SELECT":
            # Check for CTE (Common Table Expression: WITH ... SELECT)
            if not raw_upper.startswith("WITH ") or "SELECT" not in raw_upper:
                return self._fail(
                    f"Forbidden statement type '{statement_type}'. Only read-only SELECT queries are permitted.",
                    raise_on_error,
                )

        # 3. Check for file system exfiltration keywords
        if re.search(r"\bINTO\s+(?:OUTFILE|DUMPFILE)\b", trimmed_sql, re.IGNORECASE):
            return self._fail(
                "File system exfiltration keywords (INTO OUTFILE/DUMPFILE) detected. Query rejected.",
                raise_on_error,
            )

        # 4. Scan all tokens for forbidden keywords
        rejection_reason = self._scan_for_forbidden_keywords(statement)
        if rejection_reason:
            return self._fail(rejection_reason, raise_on_error)

        # 4. Extract referenced tables
        tables = self._extract_tables(statement)

        # 5. Check forbidden system tables
        for table in tables:
            if table.lower() in FORBIDDEN_TABLES:
                return self._fail(
                    f"Access to sensitive or system table '{table}' is prohibited.",
                    raise_on_error,
                )

        # 6. Verify Tenant Scoping if required
        if self.require_tenant_filter and tenant_scoped_tables:
            tenant_tables_in_query = [t for t in tables if t.lower() in tenant_scoped_tables]
            if tenant_tables_in_query:
                # Check for presence of organization_id or :org_id
                has_org_filter = bool(
                    re.search(r"\borganization_id\b", trimmed_sql, re.IGNORECASE)
                    or re.search(r":org_id\b", trimmed_sql, re.IGNORECASE)
                )
                if not has_org_filter:
                    return self._fail(
                        f"Tenant-scoped table(s) {tenant_tables_in_query} queried without organization_id filter.",
                        raise_on_error,
                    )

        # 7. Extract & Enforce LIMIT Clause
        sanitized_sql, limit_applied = self._enforce_limit(trimmed_sql, statement)

        return SQLValidationResult(
            is_safe=True,
            sanitized_sql=sanitized_sql,
            statement_type="SELECT",
            limit_applied=limit_applied,
            tables_referenced=tables,
            reason="PASSED: Read-only SELECT query verified with AST safety rails.",
        )

    def _scan_for_forbidden_keywords(self, statement: Statement) -> str | None:
        """Recursively checks tokens for forbidden DDL, DML, or administrative commands."""
        for token in statement.flatten():
            val = token.value.strip().upper()

            # Check exact forbidden keyword match
            if val in FORBIDDEN_KEYWORDS:
                return f"Forbidden keyword '{val}' detected. Query rejected."

            # Check token types
            if token.ttype in (DDL,):
                return f"DDL command '{val}' detected. Schema modifications are strictly forbidden."

            if token.ttype in (DML,) and val not in ("SELECT", ""):
                return f"DML command '{val}' detected. Data modifications are strictly forbidden."

            # Check into outfile / into dumpfile regex
            if re.search(r"INTO\s+(OUTFILE|DUMPFILE)", val):
                return "File system exfiltration keywords detected. Query rejected."

        return None

    def _extract_tables(self, statement: Statement) -> list[str]:
        """Extracts table identifiers from FROM and JOIN clauses."""
        tables = set()
        from_seen = False

        for token in statement.tokens:
            if token.is_whitespace:
                continue

            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        real_name = identifier.get_real_name()
                        if real_name:
                            tables.add(real_name)
                elif isinstance(token, Identifier):
                    real_name = token.get_real_name()
                    if real_name:
                        tables.add(real_name)
                elif token.ttype is Keyword and token.value.upper() in (
                    "WHERE",
                    "GROUP BY",
                    "ORDER BY",
                    "LIMIT",
                    "HAVING",
                ):
                    from_seen = False
                elif token.ttype is Keyword and token.value.upper() in ("JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN"):
                    continue

            if token.ttype is Keyword and token.value.upper() in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN"):
                from_seen = True

        # Fallback regex extraction in case of complex subqueries
        if not tables:
            regex_matches = re.findall(
                r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                str(statement),
                re.IGNORECASE,
            )
            for m in regex_matches:
                if m.upper() not in ("SELECT", "WHERE", "JOIN", "ON", "AS"):
                    tables.add(m)

        return sorted(tables)

    def _enforce_limit(self, sql: str, statement: Statement) -> tuple[str, int]:
        """Ensures the query ends with a valid LIMIT <= max_limit."""
        clean_sql = sql.rstrip(";").strip()

        # Match LIMIT <number> at the end of the query
        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", clean_sql, re.IGNORECASE)

        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > self.max_limit:
                # Cap to max limit
                capped_sql = re.sub(
                    r"\bLIMIT\s+\d+\b",
                    f"LIMIT {self.max_limit}",
                    clean_sql,
                    flags=re.IGNORECASE,
                )
                return capped_sql, self.max_limit
            return clean_sql, existing_limit

        # If no LIMIT clause found, append default limit
        capped_sql = f"{clean_sql} LIMIT {self.default_limit}"
        return capped_sql, self.default_limit

    def _fail(self, reason: str, raise_on_error: bool) -> SQLValidationResult:
        if raise_on_error:
            raise SQLSafetyViolationError(reason)
        return SQLValidationResult(
            is_safe=False,
            sanitized_sql="",
            statement_type="UNKNOWN",
            limit_applied=0,
            tables_referenced=[],
            reason=reason,
        )
