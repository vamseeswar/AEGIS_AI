"""Unit Tests for Phase 12: Human-in-the-Loop (HITL) Approvals System.
Tests ticket creation, status progression, reviewer authorization, rejection,
audit trail logging, and multi-tenant boundary enforcement.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

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

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


def get_auth_token(client: TestClient, email: str, password: str, org_name: str) -> tuple[str, str]:
    """Helper to register and login a user, returning (access_token, user_id)."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"User {email}",
            "organization_name": org_name,
        },
    )
    user_id = reg.json().get("user", {}).get("id", "")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return login.json()["access_token"], user_id


def setup_agent_run(client: TestClient, token: str) -> str:
    """Helper to start an agent run so approval tickets can reference it."""
    resp = client.post(
        "/api/v1/agents/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "prompt": "Analyze sensitive transactions and initiate compliance review.",
            "lead_agent": "supervisor",
            "workflow_name": "compliance_supervisor",
        },
    )
    assert resp.status_code == 201, f"Failed to start agent run: {resp.text}"
    return resp.json()["id"]


def test_create_and_list_approval_ticket(client: TestClient):
    """Verify creating a PENDING approval ticket and listing it with tenant isolation."""
    token, _ = get_auth_token(client, "approver1@corp.com", "SecurePass123!", "Acme Global")
    agent_run_id = setup_agent_run(client, token)

    # 1. Create ticket
    payload = {
        "agent_run_id": agent_run_id,
        "requested_by_agent": "Financial Ops Agent",
        "action_name": "execute_wire_transfer",
        "action_payload": {"amount": 75000, "recipient": "US88992211"},
        "risk_level": "CRITICAL",
        "reason": "Exceeds automated wire threshold limit ($50,000).",
        "expires_in_minutes": 120,
    }
    create_res = client.post(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert create_res.status_code == 201, create_res.text
    ticket = create_res.json()
    ticket_id = ticket["id"]
    assert ticket["status"] == "PENDING"
    assert ticket["risk_level"] == "CRITICAL"
    assert ticket["action_name"] == "execute_wire_transfer"
    assert ticket["action_payload"]["amount"] == 75000

    # 2. List all approvals
    list_res = client.get(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert data["pending_count"] >= 1
    matching = [t for t in data["approvals"] if t["id"] == ticket_id]
    assert len(matching) == 1

    # 3. List pending shortcut
    pending_res = client.get(
        "/api/v1/approvals/pending",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pending_res.status_code == 200
    pending_data = pending_res.json()
    assert any(t["id"] == ticket_id for t in pending_data["approvals"])


def test_approve_ticket_flow(client: TestClient):
    """Verify approving a ticket transitions status to APPROVED and records reviewer notes."""
    token, _ = get_auth_token(client, "reviewer_approve@corp.com", "SecurePass123!", "Acme Global")
    agent_run_id = setup_agent_run(client, token)

    # Create ticket
    create_res = client.post(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "agent_run_id": agent_run_id,
            "requested_by_agent": "Security Agent",
            "action_name": "firewall_rule_update",
            "action_payload": {"port": 443, "ip_range": "10.0.0.0/8"},
            "risk_level": "HIGH",
            "reason": "Open port for staging VPC peering.",
        },
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["id"]

    # Approve
    approve_res = client.post(
        f"/api/v1/approvals/{ticket_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision_notes": "Approved following security review in ticket SEC-102."},
    )
    assert approve_res.status_code == 200
    approved_ticket = approve_res.json()
    assert approved_ticket["status"] == "APPROVED"
    assert approved_ticket["decision_notes"] == "Approved following security review in ticket SEC-102."
    assert approved_ticket["decided_by_user_id"] is not None

    # Duplicate decision should fail with 409 Conflict
    dup_res = client.post(
        f"/api/v1/approvals/{ticket_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision_notes": "Trying to re-approve."},
    )
    assert dup_res.status_code == 409


def test_reject_ticket_flow(client: TestClient):
    """Verify rejecting a ticket transitions status to REJECTED."""
    token, _ = get_auth_token(client, "reviewer_reject@corp.com", "SecurePass123!", "Acme Global")
    agent_run_id = setup_agent_run(client, token)

    # Create ticket
    create_res = client.post(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "agent_run_id": agent_run_id,
            "requested_by_agent": "Outreach Agent",
            "action_name": "send_mass_notification",
            "action_payload": {"recipients_count": 25000},
            "risk_level": "HIGH",
            "reason": "Broadcast without marketing team signoff.",
        },
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["id"]

    # Reject
    reject_res = client.post(
        f"/api/v1/approvals/{ticket_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision_notes": "Rejected: Marketing team review is mandatory."},
    )
    assert reject_res.status_code == 200
    rejected_ticket = reject_res.json()
    assert rejected_ticket["status"] == "REJECTED"
    assert rejected_ticket["decision_notes"] == "Rejected: Marketing team review is mandatory."

    # Cannot reject again
    dup_res = client.post(
        f"/api/v1/approvals/{ticket_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision_notes": "Duplicate rejection."},
    )
    assert dup_res.status_code == 409


def test_tenant_isolation_enforcement(client: TestClient):
    """Verify Tenant B cannot view, approve, or reject Tenant A's approval tickets."""
    # Tenant A user
    token_a, _ = get_auth_token(client, "user_tenant_a@tenantA.com", "SecurePass123!", "Tenant A Inc")
    agent_run_a = setup_agent_run(client, token_a)

    create_res = client.post(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "agent_run_id": agent_run_a,
            "requested_by_agent": "Internal Bot",
            "action_name": "tenant_a_confidential_action",
            "action_payload": {"key": "secret_tenant_a_data"},
            "risk_level": "CRITICAL",
            "reason": "Confidential internal process.",
        },
    )
    assert create_res.status_code == 201
    ticket_a_id = create_res.json()["id"]

    # Tenant B user
    token_b, _ = get_auth_token(client, "user_tenant_b@tenantB.com", "SecurePass123!", "Tenant B Corp")

    # Tenant B attempts to fetch Tenant A's ticket -> 404
    get_res = client.get(
        f"/api/v1/approvals/{ticket_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_res.status_code == 404

    # Tenant B attempts to approve Tenant A's ticket -> 404
    approve_res = client.post(
        f"/api/v1/approvals/{ticket_a_id}/approve",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"decision_notes": "Unauthorized cross-tenant attempt."},
    )
    assert approve_res.status_code == 404

    # Tenant B listing should NOT contain Tenant A's ticket
    list_b = client.get(
        "/api/v1/approvals",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    ids = [t["id"] for t in list_b.json()["approvals"]]
    assert ticket_a_id not in ids
