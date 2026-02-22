"""
User repository containing all data-access operations for the users table.

Repository rules:
- Pure data-access logic only
- Every function receives AsyncSession explicitly
- Functions flush, but never commit
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.security import hash_password, verify_password
from app.db.models.user import User


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str = UserRole.VIEWER.value,
) -> User:
    """Create a new user with a hashed password."""
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role=role.upper(),
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    return await db.get(User, user_id)


async def get_active_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch an active user by primary key."""
    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address (case-insensitive)."""
    stmt = select(User).where(User.email == email.lower().strip())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Validate credentials and return active user on success."""
    user = await get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def list_users(
    db: AsyncSession,
    *,
    is_active: bool | None = None,
    role: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[User]:
    """List users with optional active/role filters."""
    stmt = select(User).order_by(User.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if role is not None:
        stmt = stmt.where(User.role == role.upper())
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession,
    user_id: int,
    **fields: object,
) -> User | None:
    """Update mutable user fields and return updated user."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None

    allowed = {"full_name", "email", "role"}
    for key, value in fields.items():
        if key not in allowed or value is None:
            continue

        if key == "email" and isinstance(value, str):
            value = value.lower().strip()
        if key == "role" and isinstance(value, str):
            value = value.upper()

        setattr(user, key, value)

    await db.flush()
    return user


async def update_password(
    db: AsyncSession,
    user_id: int,
    new_password: str,
) -> bool:
    """Change a user's password. Returns True when user exists."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return False
    user.hashed_password = hash_password(new_password)
    await db.flush()
    return True


async def set_active_status(
    db: AsyncSession,
    user_id: int,
    is_active: bool,
) -> User | None:
    """Activate or deactivate a user and return updated row."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.is_active = is_active
    await db.flush()
    return user


async def record_login(db: AsyncSession, user_id: int) -> None:
    """Stamp last_login_at on successful authentication."""
    stmt = update(User).where(User.id == user_id).values(last_login_at=datetime.now(timezone.utc))
    await db.execute(stmt)
    await db.flush()


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Hard-delete a user. Returns True if a row was deleted."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return False
    await db.delete(user)
    await db.flush()
    return True
