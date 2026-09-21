"""AEGIS AI — Centralized Pytest Configuration & Reusable Fixtures
Provides:
  - client: Clean database state with seeded roles/admin and TestClient
  - auth_factory: Callable to register & authenticate new tenants on demand
  - two_isolated_tenants: Yields two pre-configured isolated organizations (Tenant Alpha, Tenant Beta)
"""

import asyncio
from typing import Any, Callable
import pytest
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.init_db import initialize_database
from backend.db.session import engine
from backend.main import app
from backend.security.rate_limiter import rate_limiter




@pytest.fixture(scope="module")
def client():
    """Provides a TestClient with clean database state, seeded tables, and reset rate limiter."""
    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await initialize_database()

    asyncio.run(_reset())
    rate_limiter.reset_all()

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


@pytest.fixture
def auth_factory(client: TestClient) -> Callable[[str, str, str], dict[str, Any]]:
    """Factory helper to register and login users for test isolation."""
    def _create_tenant(email: str, password: str = "SecurePass123!", org_name: str = "Test Org") -> dict[str, Any]:
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": f"User {email}",
                "organization_name": org_name,
            },
        )
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, f"Login failed: {login.text}"
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/api/v1/auth/me", headers=headers).json()
        return {
            "token": token,
            "headers": headers,
            "user_id": me["id"],
            "organization_id": me["organization_id"],
            "email": email,
            "org_name": org_name,
        }
    return _create_tenant


@pytest.fixture
def two_isolated_tenants(auth_factory) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convenience fixture creating two completely separate tenant organizations."""
    tenant_a = auth_factory("tenant_alpha_admin@aegis.ai", "AlphaPass123!", "Enterprise Alpha Corp")
    tenant_b = auth_factory("tenant_beta_admin@aegis.ai", "BetaPass123!", "Enterprise Beta LLC")
    return tenant_a, tenant_b
