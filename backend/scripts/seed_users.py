"""
Seed initial users for development.
Run: python -m scripts.seed_insurees  (from backend/)
"""

import asyncio

from app.db.session import async_session
from app.repositories.users import create_user


SEED_USERS = [
    {
        "email": "admin@superclaims.ai",
        "password": "admin123",  # Change in production!
        "full_name": "System Admin",
        "role": "ADMIN",
    },
    {
        "email": "operator@superclaims.ai",
        "password": "operator123",
        "full_name": "TPA Operator",
        "role": "OPERATOR",
    },
    {
        "email": "viewer@superclaims.ai",
        "password": "viewer123",
        "full_name": "Dashboard Viewer",
        "role": "VIEWER",
    },
]


async def seed():
    """Insert seed users."""
    async with async_session() as session:
        for data in SEED_USERS:
            user = await create_user(db=session, **data)
            print(f"  Created user: {user.email} ({user.role})")
        await session.commit()
    print(f"Seeded {len(SEED_USERS)} users.")


if __name__ == "__main__":
    asyncio.run(seed())
