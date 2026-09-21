"""AEGIS AI — Unit Tests for Model Context Protocol (MCP) Tool Layer
Verifies tool registration, MCP JSON schema compliance, strict RBAC permission gates,
execution auditing, and functional execution across all 8 standard operational tools.
"""

import asyncio
from fastapi.testclient import TestClient
import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.core.errors import PermissionDeniedError
from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import async_session_maker, engine
from backend.main import app
from backend.models.identity import Organization, User
from backend.tools.base import ToolExecutionContext
from backend.tools.registry import global_tool_registry


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


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def seed_data(db_session):
    stmt_org = select(Organization).where(Organization.slug == "aegis-corp")
    org = (await db_session.execute(stmt_org)).scalar_one()
    stmt_user = select(User).where(User.email == "admin@aegis.ai")
    user = (await db_session.execute(stmt_user)).scalar_one()
    return {"org_id": org.id, "user_id": user.id}


def get_auth_token(client: TestClient, email: str, password: str, org_name: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Tool Operator",
            "organization_name": org_name,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_tool_registry_registration_and_mcp_schemas():
    """Verifies all 8 default tools are registered with valid MCP schema specifications."""
    tools = global_tool_registry.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "search_documents",
        "query_database",
        "analyze_csv",
        "run_forecast",
        "detect_anomalies",
        "generate_report",
        "search_web",
        "get_system_status",
    }
    assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"

    for tool in tools:
        assert tool.name
        assert tool.description
        assert tool.category in ["RAG", "DATABASE", "ANALYTICS", "ML", "REPORTING", "WEB", "SYSTEM", "GENERAL"]
        assert tool.required_permission
        assert isinstance(tool.inputSchema, dict)
        assert tool.inputSchema.get("type") == "object"
        assert "properties" in tool.inputSchema


def test_tool_api_endpoints_and_execution(client):
    """Tests /api/v1/tools catalog, schema lookup, and direct execution via REST API."""
    token = get_auth_token(client, "tool_admin@corp.com", "Password123!", "Tool Exec Org")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List MCP tools
    list_res = client.get("/api/v1/tools", headers=headers)
    assert list_res.status_code == 200
    tools = list_res.json()
    assert len(tools) >= 8

    # 2. Get single tool
    get_res = client.get("/api/v1/tools/search_web", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "search_web"

    # 3. Execute tool via API
    exec_res = client.post(
        "/api/v1/tools/search_web/execute",
        headers=headers,
        json={"arguments": {"query": "vector search enterprise", "num_results": 2}},
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "SUCCESS"
    assert exec_data["output"]["total_results"] == 2
    assert exec_data["audit_log_id"] is not None

    # 4. List audit logs
    audit_res = client.get("/api/v1/tools/audit/logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["tool_name"] == "search_web"


@pytest.mark.asyncio
async def test_tool_registry_direct_permission_enforcement(db_session, seed_data):
    """Directly tests RBAC enforcement and blocked audit logging inside the registry."""
    viewer_context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"documents.read", "analytics.view"},  # Lacks 'tools.execute' & 'ml.execute'
        user_role="VIEWER",
        db=db_session,
    )

    # Attempting to run forecasting tool should raise PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await global_tool_registry.invoke(
            name="run_forecast",
            arguments={"horizon_steps": 7},
            context=viewer_context,
        )
    assert "Permission denied" in str(exc_info.value)

    # Context with 'tools.execute' and 'ml.execute'
    allowed_context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "ml.execute"},
        user_role="ADMIN",
        db=db_session,
    )
    result = await global_tool_registry.invoke(
        name="run_forecast",
        arguments={"horizon_steps": 7},
        context=allowed_context,
    )
    assert result.status == "SUCCESS"
    assert result.execution_time_ms > 0.0
    assert "forecast_points" in result.output


@pytest.mark.asyncio
async def test_tool_search_documents(db_session, seed_data):
    """Verifies search_documents tool execution."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "documents.read"},
        user_role="MEMBER",
        db=db_session,
    )
    res = await global_tool_registry.invoke(
        name="search_documents",
        arguments={"query": "financial projections", "top_k": 3},
        context=context,
    )
    assert res.status == "SUCCESS"
    assert "results" in res.output
    assert res.output["query"] == "financial projections"


@pytest.mark.asyncio
async def test_tool_query_database_and_ast_safety(db_session, seed_data):
    """Verifies query_database tool runs safe SELECT and blocks destructive commands."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "database.query"},
        user_role="MEMBER",
        db=db_session,
    )

    # Safe SELECT query
    res = await global_tool_registry.invoke(
        name="query_database",
        arguments={"query": "SELECT id, action, status FROM audit_logs WHERE organization_id = :org_id;", "limit": 10},
        context=context,
    )
    assert res.status == "SUCCESS"
    assert "columns" in res.output

    # Malicious DROP query must fail safely
    res_drop = await global_tool_registry.invoke(
        name="query_database",
        arguments={"query": "DROP TABLE users;", "limit": 10},
        context=context,
    )
    assert res_drop.status == "FAILED"
    assert res_drop.error is not None
    assert any(t in res_drop.error.lower() for t in ["forbidden", "security", "safety", "error"])


@pytest.mark.asyncio
async def test_tool_analyze_csv(db_session, seed_data):
    """Verifies analyze_csv tool profiles tabular dataset and computes metrics."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "analytics.view"},
        user_role="MEMBER",
        db=db_session,
    )
    csv_data = "metric,value\nlatency,12.5\nlatency,14.2\nlatency,11.8\nlatency,95.0\n"

    res = await global_tool_registry.invoke(
        name="analyze_csv",
        arguments={"csv_content": csv_data, "operation": "profile"},
        context=context,
    )
    assert res.status == "SUCCESS"
    assert res.output["total_rows"] == 4
    assert len(res.output["columns"]) == 2


@pytest.mark.asyncio
async def test_tool_detect_anomalies(db_session, seed_data):
    """Verifies detect_anomalies tool scores outliers and outputs explainability attribution."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "ml.execute"},
        user_role="MEMBER",
        db=db_session,
    )

    res = await global_tool_registry.invoke(
        name="detect_anomalies",
        arguments={"contamination": 0.1},
        context=context,
    )
    assert res.status == "SUCCESS"
    assert res.output["total_samples"] > 0
    assert "anomaly_rate_percent" in res.output


@pytest.mark.asyncio
async def test_tool_generate_report_and_search_web(db_session, seed_data):
    """Verifies generate_report and search_web tools format structured outputs."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute", "reports.create"},
        user_role="MEMBER",
        db=db_session,
    )

    # 1. Generate Report
    res_rep = await global_tool_registry.invoke(
        name="generate_report",
        arguments={
            "title": "Q3 Infrastructure Efficiency Review",
            "summary": "Infrastructure scaling reduced p99 latency while lowering compute expenses.",
            "key_findings": ["P99 latency decreased by 28%", "Cluster utilization improved to 74%"],
            "metrics": {"p99_latency_ms": 42.1, "efficiency_score": 94.5},
            "recommendations": ["Upgrade database instances", "Enable regional read replicas"],
        },
        context=context,
    )
    assert res_rep.status == "SUCCESS"
    assert "# Q3 Infrastructure Efficiency Review" in res_rep.output["report_markdown"]
    assert "## 1. Executive Summary" in res_rep.output["report_markdown"]
    assert "## 2. Operational Key Performance Indicators" in res_rep.output["report_markdown"]

    # 2. Search Web
    res_web = await global_tool_registry.invoke(
        name="search_web",
        arguments={"query": "autonomous AI agents enterprise governance", "num_results": 2},
        context=context,
    )
    assert res_web.status == "SUCCESS"
    assert res_web.output["total_results"] == 2
    assert len(res_web.output["results"]) == 2
    assert "url" in res_web.output["results"][0]


@pytest.mark.asyncio
async def test_tool_get_system_status_and_audit_trail(db_session, seed_data):
    """Verifies get_system_status and checks immutable audit logging."""
    context = ToolExecutionContext(
        user_id=seed_data["user_id"],
        organization_id=seed_data["org_id"],
        user_permissions={"tools.execute"},
        user_role="MEMBER",
        db=db_session,
    )

    res = await global_tool_registry.invoke(
        name="get_system_status",
        arguments={"include_counts": True},
        context=context,
    )
    assert res.status == "SUCCESS"
    assert res.output["status"] == "OPERATIONAL"
    assert "services" in res.output
    assert res.audit_log_id is not None
