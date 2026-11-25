"""
Tests for require_jwt() (spec z_aud_3, Requirement 3.6) — parity with
`tenxyte.decorators.require_jwt`.
"""

import uuid

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _NoApplicationAuthProvider(EnvSettingsProvider):
    """These tests exercise `require_jwt` in isolation — ApplicationAuthMiddleware, which
    runs first in the stack, is disabled here since it has its own dedicated test suite in
    test_application_auth.py. Also pins a fixed HS256 signing key so token generation doesn't
    depend on the ambient environment."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-require-jwt-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_NoApplicationAuthProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())

    @app.get("/protected")
    async def protected(auth: AuthContext = Depends(require_jwt())):  # noqa: B008
        return {"user_id": auth.user.id, "scope": auth.scope}

    @app.get("/setup-only")
    async def setup_only(auth: AuthContext = Depends(require_jwt(allowed_scopes=["2fa_setup_only"]))):  # noqa: B008
        return {"user_id": auth.user.id, "scope": auth.scope}

    return app


async def _make_client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _create_user_and_token(app, extra_claims=None):
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        user = await repo.create(User(id=str(uuid.uuid4()), email=f"{uuid.uuid4().hex}@example.com", is_active=True))

    jwt_service = app.state.tenxyte_jwt_service
    pair = jwt_service.generate_new_token_pair(user_id=user.id, application_id="test-app", extra_claims=extra_claims)
    return user, pair.access_token


@pytest.mark.anyio
async def test_missing_authorization_header_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/protected")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_invalid_token_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/protected", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"


@pytest.mark.anyio
async def test_valid_full_scope_token_accepted_everywhere():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user, access_token = await _create_user_and_token(app)
        async with await _make_client(app) as client:
            protected = await client.get("/protected", headers={"Authorization": f"Bearer {access_token}"})
            setup_only = await client.get("/setup-only", headers={"Authorization": f"Bearer {access_token}"})

    assert protected.status_code == 200
    assert protected.json() == {"user_id": user.id, "scope": None}
    assert setup_only.status_code == 200


@pytest.mark.anyio
async def test_restricted_scope_token_accepted_only_on_matching_endpoint():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user, access_token = await _create_user_and_token(app, extra_claims={"scope": "2fa_setup_only"})
        async with await _make_client(app) as client:
            setup_only = await client.get("/setup-only", headers={"Authorization": f"Bearer {access_token}"})
            protected = await client.get("/protected", headers={"Authorization": f"Bearer {access_token}"})

    assert setup_only.status_code == 200
    assert setup_only.json() == {"user_id": user.id, "scope": "2fa_setup_only"}

    assert protected.status_code == 403
    assert protected.json()["code"] == "INSUFFICIENT_SCOPE"


@pytest.mark.anyio
async def test_unknown_user_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        jwt_service = app.state.tenxyte_jwt_service
        pair = jwt_service.generate_new_token_pair(user_id=str(uuid.uuid4()), application_id="test-app")
        async with await _make_client(app) as client:
            response = await client.get("/protected", headers={"Authorization": f"Bearer {pair.access_token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "USER_NOT_FOUND"


@pytest.mark.anyio
async def test_inactive_user_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            user = await repo.create(
                User(id=str(uuid.uuid4()), email=f"{uuid.uuid4().hex}@example.com", is_active=False)
            )
        jwt_service = app.state.tenxyte_jwt_service
        pair = jwt_service.generate_new_token_pair(user_id=user.id, application_id="test-app")
        async with await _make_client(app) as client:
            response = await client.get("/protected", headers={"Authorization": f"Bearer {pair.access_token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "USER_INACTIVE"
