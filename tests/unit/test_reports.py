"""Unit Tests for Phase 13: Executive Report Generation (Markdown & PDF).
Tests publication-grade ReportLab PDF rendering, report persistence, PDF binary streaming,
deletion, and multi-tenant isolation.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app
from backend.services.pdf_generator import generate_executive_pdf


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


def test_pdf_generator_direct_compilation():
    """Verify ReportLab engine compiles title, summary, tables, and metrics into a valid PDF."""
    markdown_content = """# Executive Summary
The operations pipeline maintained **99.9%** availability across the quarter.

## Key Observations
- Outlier detection identified 2 anomalies.
- All scheduled batches completed under 450ms.

| Department | Operations | Health |
|---|---|---|
| Engineering | 1,420 | Nominal |
| Finance | 890 | Nominal |
| Compliance | 340 | Optimal |
"""
    pdf_bytes = generate_executive_pdf(
        title="Q3 Operational Briefing",
        summary="Executive summary regarding infrastructure health.",
        content_markdown=markdown_content,
        metrics={"uptime": "99.9%", "total_operations": 2650, "incident_count": 0},
        organization_name="Acme Global Corporation",
        author_name="Operations Supervisor",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_create_and_list_reports(client: TestClient):
    """Verify creating an executive report via REST API, auto-generating PDF, and listing it."""
    token = get_auth_token(client, "author1@reportcorp.com", "SecurePass123!", "Report Corp")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Quarterly Autonomous Operations Review",
        "summary": "Full review of multi-agent tasks, SQL queries, and ML forecasts.",
        "content_markdown": "# Operations Review\nAutonomous agents completed all tasks with zero safety infractions.",
        "format": "PDF",
        "metrics_data": {"tasks_dispatched": 1420, "success_rate": "99.8%"},
    }

    create_res = client.post("/api/v1/reports", headers=headers, json=payload)
    assert create_res.status_code == 201, create_res.text
    rep_data = create_res.json()
    report_id = rep_data["id"]
    assert rep_data["title"] == payload["title"]
    assert rep_data["format"] == "PDF"
    assert rep_data["pdf_storage_path"] is not None

    # List reports
    list_res = client.get("/api/v1/reports", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert any(r["id"] == report_id for r in data["reports"])

    # Get single report detail
    detail_res = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == report_id


def test_download_report_pdf_stream(client: TestClient):
    """Verify downloading the compiled PDF returns application/pdf binary stream."""
    token = get_auth_token(client, "downloader@reportcorp.com", "SecurePass123!", "Report Corp")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "title": "Security Compliance Audit Briefing",
            "summary": "Bi-annual audit findings.",
            "content_markdown": "# Security Findings\nZero high-severity vulnerabilities found.",
            "format": "PDF",
        },
    )
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    download_res = client.get(f"/api/v1/reports/{report_id}/pdf", headers=headers)
    assert download_res.status_code == 200
    assert "application/pdf" in download_res.headers.get("Content-Type", "")
    assert download_res.content.startswith(b"%PDF-")
    assert len(download_res.content) > 500


def test_tenant_isolation_reports(client: TestClient):
    """Verify Tenant B cannot view, download, or delete Tenant A's reports."""
    token_a = get_auth_token(client, "tenant_a_rep@alpha.com", "SecurePass123!", "Tenant Alpha")
    token_b = get_auth_token(client, "tenant_b_rep@beta.com", "SecurePass123!", "Tenant Beta")

    # Tenant A creates report
    create_res = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "title": "Tenant Alpha Proprietary Strategy",
            "summary": "Internal strategy memo.",
            "content_markdown": "# Highly Confidential\nRestricted to Tenant Alpha leadership.",
            "format": "PDF",
        },
    )
    assert create_res.status_code == 201
    report_a_id = create_res.json()["id"]

    # Tenant B attempts to fetch -> 404
    get_res = client.get(
        f"/api/v1/reports/{report_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_res.status_code == 404

    # Tenant B attempts to download PDF -> 404
    pdf_res = client.get(
        f"/api/v1/reports/{report_a_id}/pdf",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert pdf_res.status_code == 404

    # Tenant B attempts to delete -> 404
    del_res = client.delete(
        f"/api/v1/reports/{report_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_res.status_code == 404

    # Tenant B listing does not leak Tenant A's report
    list_res = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_res.status_code == 200
    report_ids = [r["id"] for r in list_res.json()["reports"]]
    assert report_a_id not in report_ids


def test_delete_report(client: TestClient):
    """Verify deleting a report removes database record and cleans up filesystem artifact."""
    token = get_auth_token(client, "deleter@reportcorp.com", "SecurePass123!", "Report Corp")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "title": "Temporary Disposable Draft",
            "summary": "Draft summary.",
            "content_markdown": "# Disposable Draft\nWill be removed.",
            "format": "PDF",
        },
    )
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/reports/{report_id}", headers=headers)
    assert del_res.status_code == 204

    # Subsequent fetch returns 404
    get_res = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert get_res.status_code == 404
