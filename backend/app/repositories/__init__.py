"""
Repositories package — data-access layer.

Each repository file handles all DB operations for one domain entity.
Repositories do NOT handle HTTP concerns or business logic beyond
basic data integrity.

Convention:
    - One file per aggregate root (e.g., users.py, insurees.py)
    - All functions accept `AsyncSession` as the first argument
    - Use `flush()` internally; the session commit/rollback is handled
      by the `get_db` dependency in the API layer
"""
