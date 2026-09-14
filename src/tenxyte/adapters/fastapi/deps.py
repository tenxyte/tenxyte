"""
Default dependency injection for the FastAPI_Adapter (spec z_aud_3, Requirement 3.3): every
function here defaults to the Reference_Stack and is fully functional out of the box — no
`NotImplementedError` stub remains. Every function is overridable via FastAPI's own
`app.dependency_overrides` mechanism, exactly like any other FastAPI dependency.

State that must persist across requests (the engine, the session factory, the JWT blacklist)
lives on `app.state`, set once by the App_Factory's lifespan (`app.py`) — these functions just
read it back per-request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, Request
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.cache_service import CacheService
from tenxyte.core.email_service import EmailService
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService
from tenxyte.ports.async_repositories import AsyncUserRepository


def get_settings(request: Request) -> Settings:
    return request.app.state.tenxyte_settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.tenxyte_session_factory() as session:
        yield session


def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> AsyncUserRepository:  # noqa: B008
    return SQLAlchemyAsyncUserRepository(session)


def get_jwt_service(request: Request) -> JWTService:
    return request.app.state.tenxyte_jwt_service


def get_cache_service(request: Request) -> CacheService:
    return request.app.state.tenxyte_cache_service


def get_totp_service(request: Request) -> TOTPService:
    """A single shared instance (built once in the App_Factory's lifespan, not per-request) —
    its `replay_protection` must persist across requests to actually protect against replay."""
    return request.app.state.tenxyte_totp_service


def get_email_service(request: Request) -> EmailService:
    """`ConsoleEmailService` by default (spec z_aud_3, Wave C) — a Core-provided implementation
    that prints instead of sending, the same "no real backend wired in" posture `otp_service.py`
    already documents for its own delivery. Overridable via `app.dependency_overrides` like every
    other dependency here."""
    return request.app.state.tenxyte_email_service
