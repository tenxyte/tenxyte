"""
Async database engine/session management for the FastAPI Reference_Stack (spec z_aud_3,
Requirement 3.2).

Default: `aiosqlite` (development). Production Postgres: pass a `database_url` starting with
`postgresql+asyncpg://` — install the `asyncpg` driver yourself (documented, not a hard
dependency of the `[fastapi]` extra, per Requirement 8.4).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from tenxyte.adapters.fastapi.models_sa import Base

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./tenxyte.db"


def create_engine(database_url: str = DEFAULT_DATABASE_URL, **engine_kwargs) -> AsyncEngine:
    return create_async_engine(database_url, **engine_kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all_tables(engine: AsyncEngine) -> None:
    """
    Convenience for development/tests: creates the Reference_Stack's tables directly from the
    ORM metadata. Production deployments use the Alembic migrations under `migrations/` instead
    (Requirement 3.2) — this is not a substitute for them.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
