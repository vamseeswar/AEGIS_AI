"""Unit Tests for Phase 7: Streaming AI Chat, History, & Source Cards.
Tests multi-turn conversations, tenant isolation, RAG grounding, citation verification, and token streaming.
"""

import asyncio
import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.ai.providers.mock_provider import MockLLMProvider
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


def parse_sse_events(raw_text: str) -> list[dict]:
    """Helper to parse SSE lines formatted as 'data: {...}\\n\\n'."""
    events = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:") :].strip()
            if payload:
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
    return events


def test_mock_llm_provider_generation():
    """Verify deterministic mock LLM response and streaming generator."""
    provider = MockLLMProvider(model_name="mock-test")

    messages = [
        {"role": "system", "content": "You are AEGIS AI."},
        {"role": "user", "content": "What is the status of the database?"},
    ]

    async def _run():
        resp = await provider.generate_response(messages)
        assert "AEGIS Autonomous Assistant response" in resp
        assert "What is the status of the database?" in resp

        tokens = []
        async for token in provider.generate_stream(messages):
            tokens.append(token)
        return resp, "".join(tokens)

    resp, streamed = asyncio.run(_run())
    assert resp == streamed


def test_conversation_lifecycle(client: TestClient):
    """Verify conversation creation, retrieval, listing, and deletion."""
    token = get_auth_token(client, "chat_user1@alpha.com", "Password123!", "Alpha Org")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create conversation
    create_res = client.post(
        "/api/v1/chat/conversations",
        json={"title": "Operations Incident Alpha"},
        headers=headers,
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    assert conv["title"] == "Operations Incident Alpha"
    conv_id = conv["id"]

    # 2. Get conversation
    get_res = client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conv_id

    # 3. List conversations
    list_res = client.get("/api/v1/chat/conversations", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert any(c["id"] == conv_id for c in data["conversations"])

    # 4. Delete conversation
    del_res = client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 204

    # 5. Confirm deleted
    get_after = client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert get_after.status_code == 404


def test_conversation_tenant_isolation(client: TestClient):
    """Verify strict tenant isolation: Org B cannot access Org A's conversations."""
    token_a = get_auth_token(client, "alice_chat@org-a.com", "Password123!", "Org A")
    token_b = get_auth_token(client, "bob_chat@org-b.com", "Password123!", "Org B")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a conversation
    create_res = client.post(
        "/api/v1/chat/conversations",
        json={"title": "Confidential A Session"},
        headers=headers_a,
    )
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # User B tries to view User A's conversation -> 403 Forbidden
    get_res = client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers_b)
    assert get_res.status_code in (403, 404)

    # User B tries to delete User A's conversation -> 403 Forbidden
    del_res = client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=headers_b)
    assert del_res.status_code in (403, 404)

    # User B tries to view messages of User A's conversation -> 403 Forbidden
    msg_res = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers_b)
    assert msg_res.status_code in (403, 404)


def test_chat_stream_auto_create_conversation(client: TestClient):
    """Verify chat stream automatically provisions a conversation and saves user & assistant messages."""
    token = get_auth_token(client, "stream_user@gamma.com", "Password123!", "Gamma Org")
    headers = {"Authorization": f"Bearer {token}"}

    # Call streaming endpoint without conversation_id
    stream_res = client.post(
        "/api/v1/chat/stream",
        json={"message": "Explain the autonomous supervisor agent dispatch mechanism."},
        headers=headers,
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")

    events = parse_sse_events(stream_res.text)
    assert len(events) >= 3

    # Check metadata event
    meta_events = [e for e in events if e.get("type") == "metadata"]
    assert len(meta_events) == 1
    conv_id = meta_events[0]["conversation_id"]

    # Check token events
    token_events = [e for e in events if e.get("type") == "token"]
    assert len(token_events) > 0
    full_text = "".join(e["content"] for e in token_events)
    assert "autonomous supervisor agent dispatch" in full_text.lower()

    # Check done event
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1

    # Check message history in DB
    msg_res = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers)
    assert msg_res.status_code == 200
    messages = msg_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_chat_stream_grounded_rag_with_citations(client: TestClient):
    """Verify RAG-grounded chat streaming yields citation tokens and saves verified source citations."""
    token = get_auth_token(client, "rag_stream@delta.com", "Password123!", "Delta Org")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload and ingest a document into Delta Org
    file_bytes = b"Database Failover SOP: In case of primary disk threshold reaching 90%, initiate secondary replication failover."
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("failover_sop.txt", io.BytesIO(file_bytes), "text/plain")},
        data={"title": "Failover Standard Operating Procedure"},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # Ingest and index
    reindex_res = client.post(f"/api/v1/documents/{doc_id}/reindex", headers=headers)
    assert reindex_res.status_code == 200

    # 2. Query chat stream with question about failover SOP
    stream_res = client.post(
        "/api/v1/chat/stream",
        json={"message": "What is the procedure when primary disk threshold reaches 90%?"},
        headers=headers,
    )
    assert stream_res.status_code == 200
    events = parse_sse_events(stream_res.text)

    # 3. Check citations event
    citation_events = [e for e in events if e.get("type") == "citations"]
    assert len(citation_events) >= 1
    citations = citation_events[0]["citations"]
    assert len(citations) >= 1
    assert citations[0]["document_title"] == "Failover Standard Operating Procedure"
    assert citations[0]["page_number"] == 1

    # 4. Check conversation history
    meta_event = [e for e in events if e.get("type") == "metadata"][0]
    conv_id = meta_event["conversation_id"]

    msg_res = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers)
    assert msg_res.status_code == 200
    messages = msg_res.json()["messages"]
    assistant_msg = messages[1]
    assert assistant_msg["citations_json"] is not None
    assert len(assistant_msg["citations_json"]) >= 1
    assert assistant_msg["citations_json"][0]["document_title"] == "Failover Standard Operating Procedure"
