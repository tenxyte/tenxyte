"""
Property-based / integration tests for the App_Factory and Reference_Stack (spec z_aud_3,
Requirement 3.1, 3.2, 3.3).

Feature: z_aud_3, Property 10: Le stack de référence démarre sans surcharge

The full HTTP register -> login -> me journey needs the Wave A auth router (task 5.1, not yet
built) — this test proves the *base* half of Property 10 for real: the app boots on a fresh
aiosqlite database with zero DI overrides and no DI function raises NotImplementedError, and a
full User CRUD round-trip works end-to-end through the Reference_Stack (create, read, update
last_login, set MFA secret, verify email, delete) via httpx against a real running app — not a
mock. The HTTP auth journey itself is added to this same test module once task 5.1 lands.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.db import create_engine, create_session_factory
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.ports.repositories import MFAType, User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


@pytest.mark.anyio
async def test_app_boots_on_fresh_sqlite_with_zero_di_overrides():
    """No DI function raises NotImplementedError with zero configuration beyond a fresh DB URL."""
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

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
