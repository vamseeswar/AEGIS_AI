"""Unit Tests for Phase 8: LangGraph Multi-Agent Runtime & Supervisor System.
Tests agent fleet discovery, LangGraph execution, step tracing, tool call auditing, and tenant isolation.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.agents.graph import supervisor_graph
from backend.agents.registry import list_available_agents
from backend.agents.state import SupervisorState
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
    """Helper to register and login a user, returning access token."""
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


def test_list_available_agents():
    """Verify fleet registry returns all 8 specialized agents with correct roles and capabilities."""
    agents = list_available_agents()
    assert len(agents) == 8
    agent_ids = {a["id"] for a in agents}
    expected_ids = {
        "supervisor",
        "rag_agent",
        "sql_agent",
        "data_agent",
        "ml_agent",
        "doc_intel_agent",
        "validation_agent",
        "report_agent",
    }
    assert agent_ids == expected_ids

    for agent in agents:
        assert len(agent["name"]) > 0
        assert len(agent["role"]) > 0
        assert len(agent["capabilities"]) >= 2
        assert len(agent["default_tools"]) >= 1


def test_supervisor_graph_direct_execution():
    """Verify LangGraph StateGraph compiles and executes autonomous DAG with state accumulation."""
    initial_state: SupervisorState = {
        "task": "Investigate database latency spike and forecast weekend query volume.",
        "organization_id": "org-test-1",
        "user_id": "user-test-1",
        "agent_run_id": "run-test-1",
        "lead_agent": "supervisor",
        "plan": [],
        "plan_descriptions": [],
        "next_agent": "supervisor",
        "current_step_index": 0,
        "completed_steps": [],
        "agent_outputs": {},
        "final_synthesis": "",
        "status": "RUNNING",
        "errors": [],
    }

    async def _run():
        return await supervisor_graph.ainvoke(initial_state, config={"recursion_limit": 50})

    result = asyncio.run(_run())
    assert result["status"] == "COMPLETED"
    assert len(result["plan"]) >= 3
    # Plan should have auto-detected sql and ml keywords
    assert "sql_agent" in result["plan"]
    assert "ml_agent" in result["plan"]
    assert "report_agent" in result["plan"]
    assert len(result["completed_steps"]) == len(result["plan"])
    assert "Executive Operations Briefing" in result["final_synthesis"]


def test_agent_run_api_lifecycle(client: TestClient):
    """Verify full HTTP API workflow: dispatch run, trace steps, audit tools, list runs, get run trace."""
    token = get_auth_token(client, "agent_lead@aegis-fleet.com", "Password123!", "Fleet Corp")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Query available agents via API
    agents_res = client.get("/api/v1/agents", headers=headers)
    assert agents_res.status_code == 200
    assert len(agents_res.json()) == 8

    # 2. Dispatch multi-agent run
    prompt = "Review customer churn metrics, execute SQL aggregation on usage events, and prepare executive briefing."
    dispatch_res = client.post(
        "/api/v1/agents/runs",
        json={
            "prompt": prompt,
            "lead_agent": "supervisor",
            "workflow_name": "autonomous_supervisor",
        },
        headers=headers,
    )
    assert dispatch_res.status_code == 201
    run_data = dispatch_res.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["request_prompt"] == prompt
    assert run_data["total_duration_ms"] > 0
    assert len(run_data["steps"]) >= 3
    assert len(run_data["tool_calls"]) >= 3
    run_id = run_data["id"]

    # 3. List agent runs for tenant
    list_res = client.get("/api/v1/agents/runs", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == run_id for r in list_data["runs"])

    # 4. Get detailed execution trace
    detail_res = client.get(f"/api/v1/agents/runs/{run_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == run_id
    assert len(detail["steps"]) == len(run_data["steps"])
    assert detail["steps"][0]["step_number"] == 1
    assert detail["execution_summary"] is not None


def test_agent_run_tenant_isolation(client: TestClient):
    """Verify multi-tenant isolation: Org B cannot access Org A's agent runs."""
    token_a = get_auth_token(client, "org_a_user@alpha-agent.com", "Password123!", "Alpha Agent Org")
    token_b = get_auth_token(client, "org_b_user@beta-agent.com", "Password123!", "Beta Agent Org")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A creates an agent run
    create_res = client.post(
        "/api/v1/agents/runs",
        json={
            "prompt": "Classified operational analysis for Alpha Corporation only.",
            "lead_agent": "supervisor",
        },
        headers=headers_a,
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # Org B attempts to inspect Org A's run -> 403 / 404 Forbidden
    get_res = client.get(f"/api/v1/agents/runs/{run_id}", headers=headers_b)
    assert get_res.status_code in (403, 404)

    # Org B attempts to cancel Org A's run -> 403 / 404 Forbidden
    cancel_res = client.post(f"/api/v1/agents/runs/{run_id}/cancel", headers=headers_b)
    assert cancel_res.status_code in (403, 404)
