"""AEGIS AI — FastAPI Dependency Injection for Auth, RBAC, and Tenant Isolation.
Provides get_current_user, require_permission, and enforce_tenant_access dependencies.
"""

from collections.abc import Callable

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AuthenticationError, PermissionDeniedError, TenantIsolationError
from backend.core.security import decode_token
from backend.db.session import get_db
from backend.models.identity import Organization, OrganizationMember, User
from backend.schemas.auth import UserResponse
from backend.services.auth_service import get_user_permissions

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Hydrated current user context passed through all authenticated endpoints."""

    def __init__(
        self,
        id: str,
        email: str,
        full_name: str,
        is_active: bool,
        is_superuser: bool,
        organization_id: str,
        organization_name: str,
        role: str,
        permissions: set[str],
    ):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.role = role
        self.permissions = permissions

    @property
    def user_id(self) -> str:
        return self.id

    @property
    def org_id(self) -> str:
        return self.organization_id

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or self.is_superuser

    def to_response(self) -> UserResponse:
        return UserResponse(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
            organization_id=self.organization_id,
            organization_name=self.organization_name,
            role=self.role,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """FastAPI dependency: validates JWT, resolves user, org, role, and permissions."""
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Authorization header with Bearer token is required.")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Provided token is not an access token.")

    user_id: str = payload.get("sub", "")
    org_id: str = payload.get("org_id", "")
    role_name: str = payload.get("role", "VIEWER")

    if not user_id or not org_id:
        raise AuthenticationError("Token is missing required claims (sub, org_id).")

    # Resolve User
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise AuthenticationError("Account not found or deactivated.")

    # Enforce tenant membership
    membership_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        raise TenantIsolationError("No active membership in specified organization.")

    # Resolve org name
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "Unknown Organization"

    # Load permissions set
    permissions = await get_user_permissions(user_id, org_id, db)

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        organization_id=org_id,
        organization_name=org_name,
        role=role_name,
        permissions=permissions,
    )


def require_permission(permission: str) -> Callable[..., CurrentUser]:
    """Dependency factory: enforces that the current user holds a specific permission."""

    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise PermissionDeniedError(
                f"Permission '{permission}' is required to access this resource."
            )
        return current_user

    return _check


def enforce_tenant_access(resource_org_id: str, current_user: CurrentUser) -> None:
    """Raises TenantIsolationError if the resource belongs to a different organization."""
    if resource_org_id != current_user.organization_id and not current_user.is_superuser:
        raise TenantIsolationError(
            "Cross-organization resource access is strictly prohibited."
        )
