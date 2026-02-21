"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import UserRole


class LoginRequest(BaseModel):
    """Request payload for login endpoint."""

    username: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """Bearer access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., ge=1)


class CurrentUserResponse(BaseModel):
    """Authenticated user profile returned by /auth/me."""

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
