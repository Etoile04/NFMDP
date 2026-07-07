"""Async PostgreSQL connection pool via asyncpg."""

from __future__ import annotations

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the singleton connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        from nfm_backend.config import settings

        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    """Close the connection pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
