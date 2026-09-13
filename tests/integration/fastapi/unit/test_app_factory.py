"""
Property-based / integration tests for the App_Factory and Reference_Stack (spec z_aud_3,
Requirement 3.1, 3.2, 3.3).

Feature: z_aud_3, Property 10: Le stack de référence démarre sans surcharge

Two halves, both now proven for real: the app boots on a fresh aiosqlite database with zero DI
overrides and no DI function raises NotImplementedError, with a full User CRUD round-trip through
the Reference_Stack (create, read, update last_login, set MFA secret, verify email, delete); and
the full HTTP `register -> login -> me` journey works end-to-end against the Wave A auth router
(task 5.1) via httpx against a real running app — not a mock.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.db import create_engine, create_session_factory
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import MFAType, User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-property-10"
        return super().get(name, default)


@pytest.mark.anyio
async def test_app_boots_on_fresh_sqlite_with_zero_di_overrides():
    """No DI function raises NotImplementedError with zero configuration beyond a fresh DB URL."""
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_reference_stack_user_repository_full_roundtrip():
    """The Reference_Stack's AsyncUserRepository works end-to-end against a real aiosqlite DB —
    every method a Wave A auth router will call."""
    engine = create_engine(_fresh_sqlite_url())
    session_factory = create_session_factory(engine)

    from tenxyte.adapters.fastapi.db import create_all_tables

    await create_all_tables(engine)

    try:
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)

            created = await repo.create(User(id=str(uuid.uuid4()), email="alice@example.com", password_hash="hash"))
            assert created.email == "alice@example.com"

            fetched = await repo.get_by_id(created.id)
            assert fetched is not None
            assert fetched.email == "alice@example.com"

            by_email = await repo.get_by_email("alice@example.com")
            assert by_email is not None
            assert by_email.id == created.id

            assert await repo.update_last_login(created.id, datetime.now(timezone.utc)) is True
            assert await repo.set_mfa_secret(created.id, MFAType.TOTP, "topsecret") is True
            assert await repo.verify_email(created.id) is True

            refreshed = await repo.get_by_id(created.id)
            assert refreshed.mfa_secret == "topsecret"
            assert refreshed.email_verified is True
            assert refreshed.last_login is not None

            assert await repo.count() == 1
            all_users = await repo.list_all()
            assert len(all_users) == 1

            assert await repo.delete(created.id) is True
            assert await repo.get_by_id(created.id) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_property_10_http_register_login_me_journey():
    """Feature: z_aud_3, Property 10 (HTTP half) — register -> login -> me over real HTTP,
    against a fresh aiosqlite database, zero DI overrides."""
    settings = Settings(provider=_TestProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            register_response = await client.post(
                "/api/v1/register/",
                json={"email": "journey@example.com", "password": "correct-horse-battery-staple"},
            )
            assert register_response.status_code == 201

            login_response = await client.post(
                "/api/v1/login/email/",
                json={"email": "journey@example.com", "password": "correct-horse-battery-staple"},
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            me_response = await client.get("/api/v1/me/", headers={"Authorization": f"Bearer {access_token}"})

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "journey@example.com"
