"""AEGIS AI — Data Analytics & SQL Analyst Engine Test Suite
Verifies AST SQL safety validator, schema inspection, in-memory CSV profiling,
Recharts visualization formatting, and multi-tenant SQL execution.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.analytics.charts import generate_chart_config
from backend.analytics.csv_analyzer import CSVAnalyticsEngine
from backend.analytics.schema import DatabaseSchemaInspector
from backend.analytics.sql_validator import SQLASTValidator
from backend.core.errors import SQLSafetyViolationError
from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient with clean database state and initialized tables."""
    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await initialize_database()

    asyncio.run(_reset())

    with TestClient(app) as test_client:
        yield test_client


def get_auth_token(client: TestClient, email: str, password: str, org_name: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "organization_name": org_name,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.fixture
def sql_validator():
    return SQLASTValidator(default_limit=100, max_limit=500, require_tenant_filter=True)


@pytest.fixture
def schema_inspector():
    return DatabaseSchemaInspector()


@pytest.fixture
def csv_engine():
    return CSVAnalyticsEngine()


# 1. AST SQL Safety Validator Tests
def test_ast_validator_permits_safe_select(sql_validator):
    sql = "SELECT id, event_type, total_tokens FROM usage_events WHERE organization_id = :org_id"
    res = sql_validator.validate(sql, tenant_scoped_tables={"usage_events"})
    assert res.is_safe is True
    assert res.statement_type == "SELECT"
    assert "LIMIT 100" in res.sanitized_sql
    assert res.limit_applied == 100
    assert "usage_events" in res.tables_referenced


def test_ast_validator_clamps_excessive_limit(sql_validator):
    sql = "SELECT * FROM usage_events WHERE organization_id = :org_id LIMIT 9999"
    res = sql_validator.validate(sql, tenant_scoped_tables={"usage_events"})
    assert res.is_safe is True
    assert "LIMIT 500" in res.sanitized_sql
    assert res.limit_applied == 500


@pytest.mark.parametrize(
    "malicious_sql",
    [
        "DROP TABLE users;",
        "ALTER TABLE usage_events ADD COLUMN hack TEXT;",
        "INSERT INTO users (id, email) VALUES ('1', 'hack@aegis.ai');",
        "UPDATE users SET email = 'pwned@aegis.ai' WHERE id = '1';",
        "DELETE FROM audit_logs WHERE id = '1';",
        "TRUNCATE TABLE usage_events;",
        "SELECT 1; DROP TABLE users;",
        "EXEC sp_executesql 'SELECT 1';",
        "PRAGMA table_info(users);",
        "SELECT * FROM pg_shadow;",
        "SELECT * FROM usage_events INTO OUTFILE '/tmp/dump.csv';",
    ],
)
def test_ast_validator_blocks_forbidden_commands(sql_validator, malicious_sql):
    with pytest.raises(SQLSafetyViolationError):
        sql_validator.validate(malicious_sql, raise_on_error=True)


def test_ast_validator_enforces_tenant_filter(sql_validator):
    sql = "SELECT id, event_type FROM usage_events WHERE event_type = 'LLM_CALL'"
    with pytest.raises(SQLSafetyViolationError) as exc_info:
        sql_validator.validate(sql, tenant_scoped_tables={"usage_events"})
    assert "organization_id" in str(exc_info.value)


# 2. Database Schema Inspector Tests
def test_schema_inspector_hides_sensitive_columns(schema_inspector):
    summary = schema_inspector.get_schema_summary()
    assert summary["table_count"] > 0
    tables = {t["table_name"]: t for t in summary["tables"]}

    assert "usage_events" in tables
    assert "users" in tables

    user_cols = [c["name"] for c in tables["users"]["columns"]]
    assert "email" in user_cols
    assert "hashed_password" not in user_cols


def test_schema_inspector_generates_prompt_context(schema_inspector):
    prompt_text = schema_inspector.get_schema_prompt(dialect="postgresql")
    assert "DATABASE SCHEMA (POSTGRESQL)" in prompt_text
    assert "CRITICAL SECURITY RULES" in prompt_text
    assert "TABLE usage_events" in prompt_text


# 3. In-Memory CSV Analytics Engine Tests
def test_csv_profiler_statistics(csv_engine):
    csv_data = (
        "month,revenue,users\n"
        "2024-01,10000,100\n"
        "2024-02,15000,150\n"
        "2024-03,20000,200\n"
        "2024-04,25000,250\n"
        "2024-05,100000,999\n"
    )
    result = csv_engine.profile(csv_data)
    assert result.total_rows == 5
    assert result.total_columns == 3

    col_names = [c.name for c in result.columns]
    assert "revenue" in col_names
    assert "users" in col_names

    rev_col = next(c for c in result.columns if c.name == "revenue")
    assert rev_col.mean is not None
    assert rev_col.min == 10000
    assert rev_col.max == 100000

    assert result.correlation_matrix is not None
    assert len(result.correlation_matrix.columns) == 2
    assert result.correlation_matrix.matrix[0][0] == 1.0


def test_csv_grouped_aggregation(csv_engine):
    csv_data = (
        "region,latency_ms\n"
        "us-east-1,40\n"
        "us-east-1,60\n"
        "eu-central-1,100\n"
        "eu-central-1,120\n"
    )
    result = csv_engine.aggregate(csv_data, group_by="region", metric_column="latency_ms", agg_func="mean")
    assert result["aggregation"] == "mean"
    assert len(result["records"]) == 2
    regions = {r["region"]: r["latency_ms"] for r in result["records"]}
    assert regions["us-east-1"] == 50.0
    assert regions["eu-central-1"] == 110.0


# 4. Chart Generator Tests
def test_chart_generator_auto_detection():
    time_series_rows = [
        {"month": "2024-01", "revenue": 12000},
        {"month": "2024-02", "revenue": 14000},
    ]
    chart = generate_chart_config(time_series_rows)
    assert chart is not None
    assert chart.chart_type in ("area", "line")
    assert chart.x_axis_key == "month"
    assert "revenue" in chart.y_axis_keys


# 5. Full End-to-End API Endpoints Tests
def test_analytics_api_endpoints(client):
    token = get_auth_token(client, "analyst@analytics.com", "Password123!", "Analytics Corp")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Schema Endpoint
    schema_res = client.get("/api/v1/analytics/schema", headers=headers)
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert schema_data["table_count"] > 0

    # 2. SQL Compile Endpoint
    compile_res = client.post(
        "/api/v1/analytics/sql/compile",
        headers=headers,
        json={"prompt": "Show total revenue and user signup count aggregated by month"},
    )
    assert compile_res.status_code == 200
    compile_data = compile_res.json()
    assert "SELECT" in compile_data["compiled_sql"]
    assert compile_data["statement_type"] == "SELECT"

    # 3. SQL Execute Endpoint (Safe Execution)
    exec_res = client.post(
        "/api/v1/analytics/sql/execute",
        headers=headers,
        json={
            "query": "SELECT id, action, status FROM audit_logs WHERE organization_id = :org_id",
            "is_raw_sql": True,
        },
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["sanitized_sql"].startswith("SELECT")
    assert "columns" in exec_data
    assert "rows" in exec_data
    assert "duration_ms" in exec_data

    # 4. SQL Execute Endpoint (Rejection of Malicious SQL)
    malicious_res = client.post(
        "/api/v1/analytics/sql/execute",
        headers=headers,
        json={"query": "DROP TABLE users;", "is_raw_sql": True},
    )
    assert malicious_res.status_code == 400
    assert "SQL_SAFETY_VIOLATION" in malicious_res.json()["error"]["code"]

    # 5. CSV Profiler Endpoint
    csv_res = client.post(
        "/api/v1/analytics/csv/profile",
        headers=headers,
        json={"csv_data": "x,y\n1,10\n2,20\n3,30"},
    )
    assert csv_res.status_code == 200
    csv_data = csv_res.json()
    assert csv_data["total_rows"] == 3
    assert csv_data["total_columns"] == 2
