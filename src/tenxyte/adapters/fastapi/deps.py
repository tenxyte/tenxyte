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
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings
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
