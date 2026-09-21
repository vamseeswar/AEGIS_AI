"""Unit Tests for Phase 1 Foundation: Config, Security, Errors, and App Endpoints."""

from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.core.errors import (
    AuthenticationError,
    TenantIsolationError,
    SQLSafetyViolationError,
)


def test_settings_initialization():
    """Verify settings defaults and attributes."""
    assert settings.APP_NAME == "AEGIS AI"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0


def test_password_hashing():
    """Verify password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    """Verify JWT access and refresh token generation and decoding."""
    user_id = "u-123456"
    org_id = "org-9999"
    role = "ADMIN"

    token = create_access_token(subject=user_id, organization_id=org_id, role=role)
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["org_id"] == org_id
    assert payload["role"] == role
    assert payload["type"] == "access"

    # Refresh token
    refresh = create_refresh_token(subject=user_id, organization_id=org_id)
    refresh_payload = decode_token(refresh)
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["org_id"] == org_id
    assert refresh_payload["type"] == "refresh"


def test_custom_exceptions():
    """Verify custom Aegis exception codes and status codes."""
    auth_err = AuthenticationError("Session expired")
    assert auth_err.code == "AUTHENTICATION_FAILED"
    assert auth_err.status_code == 401

    tenant_err = TenantIsolationError()
    assert tenant_err.code == "TENANT_ISOLATION_VIOLATION"
    assert tenant_err.status_code == 403

    sql_err = SQLSafetyViolationError("Forbidden DROP statement")
    assert sql_err.code == "SQL_SAFETY_VIOLATION"
    assert "Forbidden DROP statement" in sql_err.message


def test_api_health_endpoints():
    """Verify FastAPI application health, ready, and root endpoints."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    
    # Test Root
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["platform"] == "AEGIS AI"

    # Test Health
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "healthy"
    assert "request_id" in data_health
    assert "X-Request-ID" in res_health.headers
    assert "X-Response-Time-MS" in res_health.headers

    # Test Ready
    res_ready = client.get("/api/v1/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] == "ready"

