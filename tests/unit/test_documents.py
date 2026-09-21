"""Unit Tests for Phase 5: Storage Abstraction, File Validation, Document Management, and Tenant Isolation."""

import io
import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app
from backend.storage.local import LocalStorageProvider
from backend.storage.validation import (
    FileValidationError,
    sanitize_filename,
    validate_upload_file,
)


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient with clean database and lifespan initialization."""
    import asyncio

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await initialize_database()

    asyncio.run(_reset())

    with TestClient(app) as test_client:
        yield test_client


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    """Helper to authenticate and retrieve access token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ------------------------------------------------------------
# 1. Validation & Sanitization Tests
# ------------------------------------------------------------


def test_sanitize_filename():
    """Verify path traversal characters, directory separators, and null bytes are removed."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.exe") == "calc.exe"
    assert sanitize_filename("safe_document.pdf") == "safe_document.pdf"
    assert sanitize_filename("") == "unnamed_document.txt"
    assert sanitize_filename("null\x00byte.txt") == "nullbyte.txt"


def test_validate_upload_file_valid():
    """Valid files pass inspection and return correct metadata."""
    content = b"sample text content for test"
    clean_name, file_type, mime, size = validate_upload_file(
        filename="test_doc.txt",
        content=content,
        content_type="text/plain",
    )
    assert clean_name == "test_doc.txt"
    assert file_type == "TXT"
    assert mime == "text/plain"
    assert size == len(content)


def test_validate_upload_file_disallowed_extension():
    """Disallowed executable or script extensions must be rejected."""
    with pytest.raises(FileValidationError) as exc:
        validate_upload_file(
            filename="malicious.exe",
            content=b"executable binary",
        )
    assert "not permitted" in str(exc.value)

    with pytest.raises(FileValidationError):
        validate_upload_file(
            filename="script.py",
            content=b"print('hello')",
        )


def test_validate_upload_file_empty():
    """Empty files must be rejected."""
    with pytest.raises(FileValidationError) as exc:
        validate_upload_file(filename="empty.txt", content=b"")
    assert "0 bytes" in str(exc.value)


def test_validate_upload_file_oversized():
    """Files exceeding size limit must be rejected."""
    oversized_content = b"A" * (21 * 1024 * 1024)  # 21 MB
    with pytest.raises(FileValidationError) as exc:
        validate_upload_file(filename="large.pdf", content=oversized_content)
    assert "exceeds the maximum allowed limit" in str(exc.value)


# ------------------------------------------------------------
# 2. Storage Provider Unit Tests
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_storage_provider_lifecycle(tmp_path):
    """Test LocalStorageProvider save, read, exists, and delete methods."""
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    tenant_id = "org-test-123"
    document_id = "doc-999"
    filename = "report.txt"
    content = b"Autonomous Operations Report Content"

    # Save
    path = await storage.save_file(tenant_id, document_id, filename, content)
    assert "org-test-123" in path
    assert "doc-999" in path

    # Exists
    assert await storage.file_exists(path) is True

    # Read
    read_bytes = await storage.get_file(path)
    assert read_bytes == content

    # Delete
    assert await storage.delete_file(path) is True
    assert await storage.file_exists(path) is False


# ------------------------------------------------------------
# 3. Document API Endpoints & Multi-Tenancy Tests
# ------------------------------------------------------------


def test_document_upload_and_lifecycle(client: TestClient):
    """Full lifecycle: upload document, list, get, download, and delete."""
    # Register and login user
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "docowner@test.com",
            "password": "Passw0rd!",
            "full_name": "Doc Owner",
            "organization_name": "DocCorp",
        },
    )
    assert reg.status_code == 201
    token = get_auth_token(client, "docowner@test.com", "Passw0rd!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload a valid document
    file_content = b"This is a verified test document for knowledge ingestion."
    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("knowledge_manual.txt", io.BytesIO(file_content), "text/plain")},
        data={"title": "Knowledge Manual"},
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()["document"]
    doc_id = doc_data["id"]
    assert doc_data["title"] == "Knowledge Manual"
    assert doc_data["filename"] == "knowledge_manual.txt"
    assert doc_data["file_type"] == "TXT"
    assert doc_data["status"] == "INDEXED"

    # 2. List documents
    list_resp = client.get("/api/v1/documents", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == doc_id for d in list_data["items"])

    # 3. Search documents
    search_resp = client.get("/api/v1/documents?search=Knowledge", headers=headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()["items"]) >= 1

    # 4. Get document by ID
    get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == doc_id

    # 5. Download document
    download_resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert download_resp.status_code == 200
    assert download_resp.content == file_content
    assert "attachment" in download_resp.headers["content-disposition"]

    # 6. Delete document
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200

    # 7. Verify document is gone
    get_after_del = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_document_tenant_isolation(client: TestClient):
    """User in Org A cannot access, download, or delete documents uploaded in Org B."""
    # Register Alice (Org A)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice_docs@test.com",
            "password": "Passw0rd!",
            "full_name": "Alice Docs",
            "organization_name": "OrgAlpha",
        },
    )
    alice_token = get_auth_token(client, "alice_docs@test.com", "Passw0rd!")

    # Register Bob (Org B)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob_docs@test.com",
            "password": "Passw0rd!",
            "full_name": "Bob Docs",
            "organization_name": "OrgBeta",
        },
    )
    bob_token = get_auth_token(client, "bob_docs@test.com", "Passw0rd!")

    # Alice uploads document
    alice_content = b"Confidential Strategy Document OrgAlpha"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("alpha_secret.pdf", io.BytesIO(alice_content), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    alice_doc_id = upload_resp.json()["document"]["id"]

    # Bob tries to access Alice's document -> 403 Forbidden
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    get_resp = client.get(f"/api/v1/documents/{alice_doc_id}", headers=bob_headers)
    assert get_resp.status_code == 403

    download_resp = client.get(
        f"/api/v1/documents/{alice_doc_id}/download", headers=bob_headers
    )
    assert download_resp.status_code == 403

    delete_resp = client.delete(
        f"/api/v1/documents/{alice_doc_id}", headers=bob_headers
    )
    assert delete_resp.status_code == 403


def test_knowledge_base_endpoints(client: TestClient):
    """Create, list, and retrieve knowledge bases."""
    token = get_auth_token(client, "admin@aegis.ai", "Admin123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Create KB
    create_resp = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={
            "name": "Custom Financial KB",
            "description": "Financial reports repository",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunk_size": 800,
            "chunk_overlap": 100,
        },
    )
    assert create_resp.status_code == 201
    kb_data = create_resp.json()
    kb_id = kb_data["id"]
    assert kb_data["name"] == "Custom Financial KB"
    assert kb_data["chunk_size"] == 800

    # List KBs
    list_resp = client.get("/api/v1/knowledge-bases", headers=headers)
    assert list_resp.status_code == 200
    assert any(k["id"] == kb_id for k in list_resp.json()["items"])

    # Get KB by ID
    get_resp = client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == kb_id
