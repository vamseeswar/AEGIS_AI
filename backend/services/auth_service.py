"""AEGIS AI — Authentication & Authorization Service
Implements registration, login, token refresh, and multi-tenant user resolution.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AuthenticationError, PermissionDeniedError
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.models.identity import (
    Organization,
    OrganizationMember,
    Permission,
    Role,
    RolePermission,
    User,
)
from backend.schemas.auth import RegisterRequest, TokenResponse, UserResponse


def _slugify(name: str) -> str:
    """Converts an organization name to a URL-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug


async def register_user(request: RegisterRequest, db: AsyncSession) -> UserResponse:
    """Registers a new user, creates their organization, assigns ADMIN role."""
    # 1. Check email uniqueness
    email_check = await db.execute(select(User).where(User.email == request.email))
    if email_check.scalar_one_or_none():
        raise PermissionDeniedError("An account with this email address already exists.")

    # 2. Create organization with unique slug
    base_slug = _slugify(request.organization_name)
    slug = base_slug
    counter = 1
    while True:
        slug_check = await db.execute(select(Organization).where(Organization.slug == slug))
        if not slug_check.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=request.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    # 3. Create user with hashed password
    user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # 4. Resolve ADMIN role
    admin_role_result = await db.execute(select(Role).where(Role.name == "ADMIN"))
    admin_role = admin_role_result.scalar_one_or_none()
    if not admin_role:
        raise AuthenticationError("Platform roles not seeded. Run init_db first.")

    # 5. Create organization membership
    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        organization_id=org.id,
        organization_name=org.name,
        role="ADMIN",
    )


async def authenticate_user(
    email: str, password: str, db: AsyncSession
) -> tuple[User, OrganizationMember, Role]:
    """Verifies credentials, returns user + org membership + role."""
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated. Contact your administrator.")

    # Resolve active membership
    membership_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        raise AuthenticationError("No active organization membership found for this account.")

    role_result = await db.execute(select(Role).where(Role.id == membership.role_id))
    role = role_result.scalar_one_or_none()
    if not role:
        raise AuthenticationError("User role configuration is invalid.")

    return user, membership, role


async def login_user(email: str, password: str, db: AsyncSession) -> TokenResponse:
    """Authenticates user and returns JWT access + refresh tokens."""
    user, membership, role = await authenticate_user(email, password, db)

    access_token = create_access_token(
        subject=user.id,
        organization_id=membership.organization_id,
        role=role.name,
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        organization_id=membership.organization_id,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
    """Validates a refresh token and issues a new access token."""
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise AuthenticationError(f"Refresh token invalid: {str(e)}") from e

    if payload.get("type") != "refresh":
        raise AuthenticationError("Provided token is not a refresh token.")

    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    user_result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalar_one_or_none()
    if not user:
        raise AuthenticationError("User not found or account deactivated.")

    membership_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        raise AuthenticationError("Organization membership is no longer active.")

    role_result = await db.execute(select(Role).where(Role.id == membership.role_id))
    role = role_result.scalar_one_or_none()

    new_access_token = create_access_token(
        subject=user_id,
        organization_id=org_id,
        role=role.name if role else "MEMBER",
    )
    new_refresh_token = create_refresh_token(subject=user_id, organization_id=org_id)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


async def get_user_permissions(user_id: str, org_id: str, db: AsyncSession) -> set[str]:
    """Returns the set of permission names for a user within an organization."""
    membership_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        return set()

    rp_result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == membership.role_id)
    )
    return {row[0] for row in rp_result.all()}
