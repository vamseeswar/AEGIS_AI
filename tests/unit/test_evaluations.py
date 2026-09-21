"""Unit Tests for Phase 14: RAG & Agent Evaluation Subsystem.
Tests mathematical scoring algorithms for Context Precision, Recall, Faithfulness,
Answer Relevancy, Tool Accuracy, benchmark execution via REST API, and multi-tenant isolation.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.evaluations.metrics import (
    compute_answer_relevance,
    compute_context_precision,
    compute_context_recall,
    compute_faithfulness,
    compute_task_success_rate,
    compute_tool_accuracy,
)
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

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


def get_auth_token(client: TestClient, email: str, password: str, org_name: str) -> str:
    """Helper to register and login a user, returning access_token."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"User {email}",
            "organization_name": org_name,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return login.json()["access_token"]


def test_evaluation_metrics_mathematical_algorithms():
    """Verify precision, recall, faithfulness, and tool accuracy calculations."""
    ground_truth = [
        "The server port is 8080.",
        "Maximum connection limit is 500.",
    ]
    retrieved_contexts = [
        "The server port is configured as 8080 for web traffic.",
        "Unrelated log data from yesterday morning.",
        "Connection pool limit is 500 simultaneous users.",
    ]

    # Context Precision
    precision = compute_context_precision(retrieved_contexts, ground_truth)
    assert precision > 0.8, f"Unexpected precision: {precision}"

    # Context Recall
    recall = compute_context_recall(retrieved_contexts, ground_truth)
    assert recall >= 0.9, f"Unexpected recall: {recall}"

    # Faithfulness (Grounded vs Hallucinated)
    faithful_answer = "The server port is 8080 and maximum connection limit is 500."
    f_score, f_claims = compute_faithfulness(faithful_answer, retrieved_contexts)
    assert f_score == 1.0
    assert len(f_claims) >= 1

    hallucinated_answer = "The database uses Oracle Cloud with secret passwords stored on floppy disk."
    h_score, _ = compute_faithfulness(hallucinated_answer, retrieved_contexts)
    assert h_score == 0.0

    # Answer Relevancy
    relevance = compute_answer_relevance("What is the server port?", "The server port is 8080.")
    assert relevance > 0.6

    # Tool Accuracy
    tool_acc_perfect = compute_tool_accuracy("query_database", "query_database", {"query": "SELECT 1"}, ["query"])
    assert tool_acc_perfect == 1.0

    tool_acc_wrong_tool = compute_tool_accuracy("run_forecast", "query_database", {"query": "SELECT 1"}, ["query"])
    assert tool_acc_wrong_tool == 0.0

    # Task Success
    task_rate = compute_task_success_rate(["SUCCESS", "SUCCESS", "FAILED"])
    assert round(task_rate, 2) == 0.67


def test_run_evaluation_suite_api(client: TestClient):
    """Verify executing complete automated benchmark suite via POST /api/v1/evaluations/run."""
    token = get_auth_token(client, "eval_admin@corp.com", "SecurePass123!", "Evaluation Corp")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "eval_type": "ALL",
        "dataset_name": "synthetic_benchmark_v1",
        "sample_limit": 5,
    }

    res = client.post("/api/v1/evaluations/run", headers=headers, json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "run_id" in data
    assert data["eval_type"] == "ALL"
    assert data["total_metrics"] == 7
    assert data["passed_metrics"] >= 5
    assert data["overall_score"] >= 0.85
    assert len(data["metrics"]) == 7

    metric_names = {m["metric_name"] for m in data["metrics"]}
    assert "context_precision" in metric_names
    assert "context_recall" in metric_names
    assert "faithfulness" in metric_names
    assert "answer_relevance" in metric_names
    assert "tool_accuracy" in metric_names
    assert "task_success_rate" in metric_names
    assert "sql_safety_compliance" in metric_names


def test_list_evaluations_api(client: TestClient):
    """Verify listing evaluation records and aggregate metric averages."""
    token = get_auth_token(client, "eval_viewer@corp.com", "SecurePass123!", "Evaluation Corp")
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/v1/evaluations/run",
        headers=headers,
        json={"eval_type": "ALL", "sample_limit": 5},
    )

    res = client.get("/api/v1/evaluations", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 7
    assert len(data["evaluations"]) >= 7
    assert "context_precision" in data["metric_averages"]
    assert "faithfulness" in data["metric_averages"]


def test_get_evaluation_summary_api(client: TestClient):
    """Verify SLA radar health scorecard via GET /api/v1/evaluations/summary."""
    token = get_auth_token(client, "eval_summary@corp.com", "SecurePass123!", "Evaluation Corp")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/evaluations/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_health"] in ("HEALTHY", "DEGRADED")
    assert data["average_score"] > 0.80
    assert len(data["metrics"]) == 7
    for m in data["metrics"]:
        assert m["current_score"] >= 0.0
        assert m["target_threshold"] > 0.0
        assert m["status"] in ("PASSED", "FAILED")


def test_tenant_isolation_evaluations(client: TestClient):
    """Verify Tenant B does not see Tenant A's evaluation records."""
    token_a = get_auth_token(client, "user_eval_a@tenantA.com", "SecurePass123!", "Tenant Eval A")
    token_b = get_auth_token(client, "user_eval_b@tenantB.com", "SecurePass123!", "Tenant Eval B")

    # Tenant A runs evaluation
    run_res = client.post(
        "/api/v1/evaluations/run",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"eval_type": "RAG", "sample_limit": 2},
    )
    assert run_res.status_code == 200

    # Tenant B lists evaluations -> should have 0 records
    list_b = client.get(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0
    assert len(list_b.json()["evaluations"]) == 0
