"""Unit Tests for Phase 3: Authentication, RBAC, Multi-Tenancy, and Tenant Isolation."""

import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient within the application lifespan and a clean test database."""
    import asyncio

    async def _reset_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await initialize_database()

    asyncio.run(_reset_db())

    with TestClient(app) as test_client:
        yield test_client


def test_register_new_user(client: TestClient):
    """Register a fresh user with a new organization."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@test.com",
            "password": "Passw0rd!",
            "full_name": "Alice Tester",
            "organization_name": "Alice Corp",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["full_name"] == "Alice Tester"
    assert data["role"] == "ADMIN"
    assert data["organization_name"] == "Alice Corp"
    assert "id" in data
    assert "organization_id" in data


def test_register_duplicate_email(client: TestClient):
    """Reject duplicate registration with same email."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@test.com",
            "password": "Passw0rd!",
            "full_name": "Alice Again",
            "organization_name": "Another Corp",
        },
    )
    assert resp.status_code == 403
    assert "already exists" in resp.json()["error"]["message"]


def test_register_weak_password(client: TestClient):
    """Reject registration with weak password (no uppercase or digit)."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@test.com",
            "password": "nodigits",
            "full_name": "Weak User",
            "organization_name": "Weak Corp",
        },
    )
    assert resp.status_code == 422


def test_login_success(client: TestClient):
    """Login with valid credentials returns tokens."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "Passw0rd!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    """Login with wrong password returns 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "WrongPass1"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_login_nonexistent_user(client: TestClient):
    """Login with nonexistent email returns 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "Passw0rd!"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_me_endpoint(client: TestClient):
    """Authenticated /me returns correct user profile."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "Passw0rd!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "alice@test.com"
    assert data["role"] == "ADMIN"
    assert data["organization_name"] == "Alice Corp"


def test_me_without_token(client: TestClient):
    """Unauthenticated /me returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_me_with_invalid_token(client: TestClient):
    """Invalid token on /me returns 401."""
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_refresh_token_flow(client: TestClient):
    """Refresh token returns a new valid access token."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "Passw0rd!"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify new access token works
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200


def test_logout_endpoint(client: TestClient):
    """Logout returns success message."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "Passw0rd!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert "Logged out" in logout_resp.json()["message"]


def test_tenant_isolation_between_organizations(client: TestClient):
    """Two users in different organizations cannot see each other's data context."""
    # Register second user in a different org
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@test.com",
            "password": "Passw0rd!",
            "full_name": "Bob Tester",
            "organization_name": "Bob Corp",
        },
    )
    assert reg_resp.status_code == 201

    # Login as Alice and Bob
    alice_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "Passw0rd!"},
    )
    bob_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@test.com", "password": "Passw0rd!"},
    )
    assert alice_resp.status_code == 200
    assert bob_resp.status_code == 200

    alice_token = alice_resp.json()["access_token"]
    bob_token = bob_resp.json()["access_token"]

    # Verify they belong to different organizations
    alice_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {alice_token}"},
    ).json()
    bob_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bob_token}"},
    ).json()

    assert alice_me["organization_id"] != bob_me["organization_id"]
    assert alice_me["organization_name"] == "Alice Corp"
    assert bob_me["organization_name"] == "Bob Corp"


def test_admin_default_user_login(client: TestClient):
    """Default seeded admin user can log in successfully."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aegis.ai", "password": "Admin123!"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["is_superuser"] is True
    assert data["role"] == "ADMIN"


def test_tenant_isolation_helper_enforcement():
    """Verify enforce_tenant_access rejects cross-tenant access and permits same-tenant / superuser."""
    from backend.core.errors import TenantIsolationError
    from backend.security.dependencies import CurrentUser, enforce_tenant_access

    regular_user = CurrentUser(
        id="user-1",
        email="user@org1.com",
        full_name="Org1 User",
        is_active=True,
        is_superuser=False,
        organization_id="org-1",
        organization_name="Org 1",
        role="MEMBER",
        permissions={"documents.read"},
    )

    # Same tenant access should succeed
    enforce_tenant_access("org-1", regular_user)

    # Cross tenant access must raise TenantIsolationError
    with pytest.raises(TenantIsolationError):
        enforce_tenant_access("org-2", regular_user)

    # Superuser access across tenants should succeed
    admin_user = CurrentUser(
        id="admin-1",
        email="admin@root.com",
        full_name="Root Admin",
        is_active=True,
        is_superuser=True,
        organization_id="org-system",
        organization_name="System",
        role="ADMIN",
        permissions=set(),
    )
    enforce_tenant_access("org-2", admin_user)


@pytest.mark.asyncio
async def test_require_permission_dependency():
    """Verify require_permission dependency check."""
    from backend.core.errors import PermissionDeniedError
    from backend.security.dependencies import CurrentUser, require_permission

    user_with_permission = CurrentUser(
        id="user-1",
        email="user@org1.com",
        full_name="Org1 User",
        is_active=True,
        is_superuser=False,
        organization_id="org-1",
        organization_name="Org 1",
        role="ANALYST",
        permissions={"analytics.view"},
    )

    check_analytics = require_permission("analytics.view")
    checked_user = await check_analytics(current_user=user_with_permission)
    assert checked_user.id == "user-1"

    check_admin = require_permission("system.admin")
    with pytest.raises(PermissionDeniedError):
        await check_admin(current_user=user_with_permission)

