"""
User repository — all database operations for the `users` table.

Follows the repository pattern:
    - Pure data-access logic, no HTTP/business concerns
    - Every function takes an AsyncSession explicitly
    - Returns model instances or None
    - Raises nothing beyond SQLAlchemy exceptions
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User


# ─── Create ──────────────────────────────────────────────
async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str = "VIEWER",
) -> User:
    """
    Create a new user with a hashed password.
    Caller is responsible for committing the session.
    """
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role=role.upper(),
    )
    db.add(user)
    await db.flush()  # populates user.id without committing
    return user


# ─── Read ────────────────────────────────────────────────
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch a single user by primary key."""
    return await db.get(User, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a single user by email (case-insensitive)."""
    stmt = select(User).where(User.email == email.lower().strip())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    is_active: bool | None = None,
    role: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[User]:
    """
    List users with optional filters.
    Returns at most `limit` rows starting from `offset`.
    """
    stmt = select(User).order_by(User.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if role is not None:
        stmt = stmt.where(User.role == role.upper())
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Update ──────────────────────────────────────────────
async def update_user(
    db: AsyncSession,
    user_id: int,
    **fields: dict,
) -> User | None:
    """
    Update arbitrary fields on a user.
    Accepted keys: full_name, email, role.
    Returns the updated user or None if not found.
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None

    allowed = {"full_name", "email", "role"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            if key == "email":
                value = value.lower().strip()
            if key == "role":
                value = value.upper()
            setattr(user, key, value)

    await db.flush()
    return user


async def update_password(
    db: AsyncSession,
    user_id: int,
    new_password: str,
) -> bool:
    """Change a user's password. Returns True if user existed."""
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
    """Activate or deactivate a user. Returns updated user or None."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.is_active = is_active
    await db.flush()
    return user


async def record_login(db: AsyncSession, user_id: int) -> None:
    """Stamp `last_login_at` on successful authentication."""
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.flush()


# ─── Delete ──────────────────────────────────────────────
async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """
    Hard-delete a user. Prefer `set_active_status(…, False)` for soft-delete.
    Returns True if user existed and was deleted.
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        return False
    await db.delete(user)
    await db.flush()
    return True
