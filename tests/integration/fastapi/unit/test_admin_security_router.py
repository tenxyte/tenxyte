"""
Tests for the Wave D Admin Security router (spec z_aud_3, Wave D chunk 4/5, task 10.1) —
admin/audit-logs/*, admin/login-attempts/*, admin/blacklisted-tokens/*, admin/refresh-tokens/* —
against a real app, a real ephemeral aiosqlite database, and real signed tokens (no mocks).
"""

import uuid

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import AuditLogDB, LoginAttemptDB
from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-admin-security-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, is_superuser=False) -> tuple[str, dict]:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        created = await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=f"user-{uuid.uuid4().hex}@example.com",
                password_hash=password_hash,
                is_active=True,
                is_superuser=is_superuser,
            )
        )
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=created.id, application_id="default"
    ).access_token
    return created.id, {"Authorization": f"Bearer {token}"}


async def _admin_headers(app) -> dict:
    _, headers = await _create_user(app, is_superuser=True)
    return headers


@pytest.mark.anyio
async def test_logout_populates_blacklisted_tokens_admin_listing():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user_id, headers = await _create_user(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            raw_refresh = await issue_refresh_token(session, user_id, lifetime_seconds=3600)

        admin_headers = await _admin_headers(app)
        async with await _client(app) as client:
            logout = await client.post("/api/v1/logout/", json={"refresh_token": raw_refresh}, headers=headers)
            assert logout.status_code == 200

            listing = await client.get("/api/v1/admin/blacklisted-tokens/", headers=admin_headers)
            assert listing.status_code == 200
            body = listing.json()
            assert body["count"] >= 1
            entry = next(r for r in body["results"] if r["user"] == user_id)
            assert entry["reason"] == "logout"
            assert entry["is_expired"] is False


@pytest.mark.anyio
async def test_blacklisted_tokens_cleanup():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        user_id, headers = await _create_user(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            raw_refresh = await issue_refresh_token(session, user_id, lifetime_seconds=3600)

        async with await _client(app) as client:
            await client.post("/api/v1/logout/", json={"refresh_token": raw_refresh}, headers=headers)

            cleanup = await client.post("/api/v1/admin/blacklisted-tokens/cleanup/", headers=admin_headers)
            assert cleanup.status_code == 200
            # The token blacklisted above hasn't expired yet, so cleanup removes nothing.
            assert cleanup.json()["deleted_count"] == 0

            listing = await client.get("/api/v1/admin/blacklisted-tokens/?expired=true", headers=admin_headers)
            assert listing.json()["count"] == 0


@pytest.mark.anyio
async def test_refresh_tokens_list_and_revoke():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        user_id, _ = await _create_user(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            await issue_refresh_token(session, user_id, lifetime_seconds=3600)

        async with await _client(app) as client:
            listing = await client.get("/api/v1/admin/refresh-tokens/", headers=admin_headers)
            assert listing.status_code == 200
            results = listing.json()["results"]
            entry = next(r for r in results if r["user"] == user_id)
            assert entry["is_revoked"] is False
            assert entry["is_expired"] is False
            token_id = entry["id"]

            revoke = await client.post(f"/api/v1/admin/refresh-tokens/{token_id}/revoke/", headers=admin_headers)
            assert revoke.status_code == 200
            assert revoke.json()["token"]["is_revoked"] is True

            again = await client.post(f"/api/v1/admin/refresh-tokens/{token_id}/revoke/", headers=admin_headers)
            assert again.status_code == 400
            assert again.json()["code"] == "ALREADY_REVOKED"

            missing = await client.post(f"/api/v1/admin/refresh-tokens/{uuid.uuid4()}/revoke/", headers=admin_headers)
            assert missing.status_code == 404
            assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_audit_logs_list_and_detail():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        user_id, _ = await _create_user(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            log = AuditLogDB(user_id=user_id, action="login", ip_address="127.0.0.1", details={"method": "email"})
            session.add(log)
            await session.commit()
            await session.refresh(log)
            log_id = log.id

        async with await _client(app) as client:
            listing = await client.get("/api/v1/admin/audit-logs/?action=login", headers=admin_headers)
            assert listing.status_code == 200
            assert listing.json()["count"] == 1

            detail = await client.get(f"/api/v1/admin/audit-logs/{log_id}/", headers=admin_headers)
            assert detail.status_code == 200
            assert detail.json()["action"] == "login"
            assert detail.json()["details"] == {"method": "email"}

            missing = await client.get(f"/api/v1/admin/audit-logs/{uuid.uuid4()}/", headers=admin_headers)
            assert missing.status_code == 404
            assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_login_attempts_list_and_filter():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            session.add(LoginAttemptDB(identifier="user@example.com", ip_address="10.0.0.1", success=True))
            session.add(
                LoginAttemptDB(
                    identifier="user@example.com",
                    ip_address="10.0.0.2",
                    success=False,
                    failure_reason="bad_password",
                )
            )
            await session.commit()

        async with await _client(app) as client:
            listing = await client.get("/api/v1/admin/login-attempts/", headers=admin_headers)
            assert listing.status_code == 200
            assert listing.json()["count"] == 2

            failures = await client.get("/api/v1/admin/login-attempts/?success=false", headers=admin_headers)
            assert failures.json()["count"] == 1
            assert failures.json()["results"][0]["failure_reason"] == "bad_password"


@pytest.mark.anyio
async def test_blacklisted_token_unrecognized_ordering_is_silently_ignored():
    """Real Django finding (see admin_security_service.py docstring): an `ordering` value outside
    BlacklistedTokenListView's literal allow-list is silently ignored, not defaulted."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        async with await _client(app) as client:
            response = await client.get(
                "/api/v1/admin/blacklisted-tokens/?ordering=not_a_real_field", headers=admin_headers
            )
            assert response.status_code == 200


@pytest.mark.anyio
async def test_admin_security_endpoints_require_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, regular_headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/admin/audit-logs/", headers=regular_headers)

    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
