"""AEGIS AI — End-to-End Enterprise Integration Workflow Tests.
Tests comprehensive multi-system workflows:
  1. Document Vault Ingestion -> Vector Chunking -> Grounded Streaming RAG Chat with Verifiable Citations
  2. Autonomous Supervisor Fleet -> Specialized Execution -> HITL Governance Approval -> Executive Report Generation
  3. Quality Evaluation Benchmarks -> Audit Trail Ledger -> Token Telemetry & Prometheus Scrapes
"""

import io
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_e2e_rag_ingest_and_grounded_streaming_chat(client: TestClient, auth_factory):
    """Workflow 1: Ingest document, verify chunking, and run grounded RAG streaming chat."""
    tenant = auth_factory("rag_architect@tenant-flow.com", "SecureFlowPass123!", "RAG Enterprise Inc")
    headers = tenant["headers"]

    # 1. Ingest enterprise policy document
    doc_content = (
        "# Enterprise Security Policy 2026\n\n"
        "Section 1.1: Multi-Factor Authentication (MFA) is strictly mandatory for all employees.\n"
        "Section 1.2: All production database queries must enforce an execution timeout limit of 5000 milliseconds.\n"
        "Section 1.3: Data loss prevention rules require immediate redaction of all social security and payment card numbers.\n"
    )
    file_bytes = io.BytesIO(doc_content.encode("utf-8"))
    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("security_policy_2026.txt", file_bytes, "text/plain")},
        data={"title": "Enterprise Security Policy 2026", "tags": "security,compliance"},
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Trigger re-indexing / chunking
    index_resp = client.post(
        f"/api/v1/documents/{doc_id}/reindex",
        headers=headers,
    )
    assert index_resp.status_code in (200, 201)

    # 3. Create a chat conversation
    conv_resp = client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"title": "Security Policy Inquiry"},
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # 4. Query chat stream with RAG grounding enabled
    stream_resp = client.post(
        "/api/v1/chat/stream",
        headers=headers,
        json={
            "conversation_id": conv_id,
            "message": "What is the mandatory execution timeout limit for database queries?",
            "use_rag": True,
        },
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]

    events = stream_resp.text
    assert '"type": "token"' in events or "data:" in events
    assert '"type": "done"' in events or "[DONE]" in events or "data:" in events


@pytest.mark.integration
def test_e2e_agent_workflow_to_approval_and_report(client: TestClient, auth_factory):
    """Workflow 2: Dispatch supervisor agent, trigger approval, resolve ticket, compile report."""
    tenant = auth_factory("ops_lead@tenant-flow2.com", "SecureFlowPass123!", "Autonomous Ops Ltd")
    headers = tenant["headers"]

    # 1. Start Autonomous Agent Run
    run_resp = client.post(
        "/api/v1/agents/runs",
        headers=headers,
        json={
            "prompt": "Analyze Q3 transaction anomalies and propose policy adjustments.",
            "lead_agent": "supervisor",
            "workflow_name": "quarterly_audit_and_remediation",
        },
    )
    assert run_resp.status_code == 201, f"Agent run failed: {run_resp.text}"
    run_id = run_resp.json()["id"]

    # 2. Verify Agent Run details and step persistence
    run_detail = client.get(
        f"/api/v1/agents/runs/{run_id}",
        headers=headers,
    )
    assert run_detail.status_code == 200
    assert run_detail.json()["id"] == run_id

    # 3. Create an approval ticket for high-risk action
    ticket_resp = client.post(
        "/api/v1/approvals",
        headers=headers,
        json={
            "agent_run_id": run_id,
            "requested_by_agent": "supervisor",
            "action_name": "alter_vector_indexing_policy",
            "action_payload": {"new_dimension": 384, "metric": "cosine", "requires_reindex": True},
            "risk_level": "HIGH",
            "reason": "Performance optimization for Q3 audit search latency.",
        },
    )
    assert ticket_resp.status_code == 201, f"Approval creation failed: {ticket_resp.text}"
    ticket_id = ticket_resp.json()["id"]

    # 4. Review and approve ticket
    approve_resp = client.post(
        f"/api/v1/approvals/{ticket_id}/approve",
        headers=headers,
        json={"decision_notes": "Reviewed and authorized by Operations Lead."},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # 5. Synthesize and generate executive PDF report
    report_resp = client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "title": "Autonomous Remediation & Security Audit Report",
            "summary": "Autonomous audit executed successfully with zero compliance violations.",
            "content_markdown": (
                "# Autonomous Remediation & Security Audit\n\n"
                "## Executive Summary\n"
                "Autonomous audit executed successfully with zero compliance violations.\n\n"
                "### Findings\n"
                "- **AST SQL Safety**: Compliant with zero leaks.\n"
                "- **Vector Indexing**: Ticket authorized by Operations Lead.\n"
            ),
            "format": "PDF",
            "agent_run_id": run_id,
        },
    )
    assert report_resp.status_code == 201, f"Report creation failed: {report_resp.text}"
    report_id = report_resp.json()["id"]

    # 6. Stream and verify downloadable binary PDF
    pdf_resp = client.get(
        f"/api/v1/reports/{report_id}/pdf",
        headers=headers,
    )
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert pdf_resp.content.startswith(b"%PDF-")


@pytest.mark.integration
def test_e2e_quality_benchmark_and_telemetry_flow(client: TestClient, auth_factory):
    """Workflow 3: Run benchmark suite, verify SLA radar scorecard, and check Prometheus export."""
    tenant = auth_factory("qa_director@tenant-flow3.com", "SecureFlowPass123!", "Quality Assurance Corp")
    headers = tenant["headers"]

    # 1. Execute automated benchmark suite
    eval_resp = client.post(
        "/api/v1/evaluations/run",
        headers=headers,
        json={"eval_type": "ALL", "sample_limit": 5},
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["total_metrics"] >= 5

    # 2. Inspect high-level SLA scorecard
    summary_resp = client.get(
        "/api/v1/evaluations/summary",
        headers=headers,
    )
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["overall_health"] in ("HEALTHY", "DEGRADED")
    assert len(summary_data["metrics"]) >= 7

    # 3. Verify immutable audit log recorded the evaluation execution
    audit_resp = client.get(
        "/api/v1/observability/audit/logs?action=EVALUATION",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()["items"]) >= 1

    # 4. Scrape Prometheus exposition metrics
    prom_resp = client.get("/api/v1/observability/metrics")
    assert prom_resp.status_code == 200
    assert "aegis_audit_events_total" in prom_resp.text
    assert "aegis_system_info" in prom_resp.text
