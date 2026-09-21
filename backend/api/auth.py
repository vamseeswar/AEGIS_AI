"""AEGIS AI — Authentication API Routes
Endpoints: register, login, logout, me, refresh
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services.auth_service import login_user, refresh_access_token, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their organization."""
    return await register_user(request, db)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT access + refresh tokens."""
    return await login_user(request.email, request.password, db)


@router.post("/logout")
async def logout(current_user: CurrentUser = Depends(get_current_user)):
    """Logout the current user (client-side token invalidation)."""
    return {"message": "Logged out successfully.", "user_id": current_user.id}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Return the currently authenticated user's profile and organization context."""
    return current_user.to_response()


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    return await refresh_access_token(request.refresh_token, db)
