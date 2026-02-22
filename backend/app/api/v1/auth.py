"""Authentication endpoints for login and current-user introspection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.core.config import settings
from app.core.security import create_access_token
from app.db.models.user import User
from app.repositories import users as user_repository

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and issue an access token."""
    user = await user_repository.authenticate_user(
        db,
        email=payload.username,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    await user_repository.record_login(db, user.id)

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
        }
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Return the currently authenticated active user."""
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at,
    )
