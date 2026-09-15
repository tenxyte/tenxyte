"""
Tests for the Wave D Dashboard router (spec z_aud_3, Wave D chunk 5/5, task 10.1) —
dashboard/stats, dashboard/auth, dashboard/security, dashboard/gdpr, dashboard/organizations —
against a real app, a real ephemeral aiosqlite database, and real signed tokens (no mocks).
"""

import uuid

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import AuditLogDB, LoginAttemptDB, UserDB
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
            return "test-secret-key-for-dashboard-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, is_superuser=False, is_locked=False, is_banned=False) -> tuple[str, dict]:
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
        if is_locked or is_banned:
            db_user = await session.get(UserDB, created.id)
            db_user.is_locked = is_locked
            db_user.is_banned = is_banned
            await session.commit()
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=created.id, application_id="default"
    ).access_token
    return created.id, {"Authorization": f"Bearer {token}"}


async def _admin_headers(app) -> dict:
    _, headers = await _create_user(app, is_superuser=True)
    return headers


@pytest.mark.anyio
async def test_dashboard_stats_reflects_real_data():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        await _create_user(app, is_locked=True)
        await _create_user(app, is_banned=True)

        async with await _client(app) as client:
            response = await client.get("/api/v1/dashboard/stats/", headers=admin_headers)
            assert response.status_code == 200
            body = response.json()
            assert body["users"]["total"] >= 3
            assert body["users"]["locked"] >= 1
            assert body["users"]["banned"] >= 1
            assert body["gdpr"] == {"pending": 0, "confirmed": 0, "expiring_7d": 0}
            assert "applications" in body
            assert "security" in body


@pytest.mark.anyio
async def test_dashboard_auth_login_stats_and_failure_reasons():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            session.add(LoginAttemptDB(identifier="a@example.com", ip_address="10.0.0.1", success=True))
            session.add(
                LoginAttemptDB(
                    identifier="b@example.com", ip_address="10.0.0.2", success=False, failure_reason="bad_password"
                )
            )
            session.add(
                LoginAttemptDB(
                    identifier="c@example.com", ip_address="10.0.0.3", success=False, failure_reason="bad_password"
                )
            )
            session.add(AuditLogDB(action="login", details={"method": "email"}))
            await session.commit()

        async with await _client(app) as client:
            response = await client.get("/api/v1/dashboard/auth/", headers=admin_headers)
            assert response.status_code == 200
            body = response.json()
            assert body["login_stats"]["today"]["total"] == 3
            assert body["login_stats"]["today"]["success"] == 1
            assert body["login_stats"]["today"]["failed"] == 2
            assert body["login_by_method"] == {"email": 1}
            assert {"reason": "bad_password", "count": 2} in body["top_login_failure_reasons"]
            assert len(body["charts"]["logins_per_day_7d"]) == 1
            assert body["charts"]["logins_per_day_7d"][0]["success"] == 1
            assert body["charts"]["logins_per_day_7d"][0]["failed"] == 2


@pytest.mark.anyio
async def test_dashboard_security_blacklist_and_account_security():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        user_id, headers = await _create_user(app)
        await _create_user(app, is_locked=True)
        await _create_user(app, is_banned=True)
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            raw_refresh = await issue_refresh_token(session, user_id, lifetime_seconds=3600)

        async with await _client(app) as client:
            logout = await client.post("/api/v1/logout/", json={"refresh_token": raw_refresh}, headers=headers)
            assert logout.status_code == 200

            response = await client.get("/api/v1/dashboard/security/", headers=admin_headers)
            assert response.status_code == 200
            body = response.json()
            assert body["blacklisted_tokens"]["total_active"] >= 1
            assert body["blacklisted_tokens"]["by_reason"].get("logout") == 1
            assert body["account_security"]["locked_accounts"] >= 1
            assert body["account_security"]["banned_accounts"] >= 1
            assert body["account_security"]["2fa_adoption_rate"] == 0.0


@pytest.mark.anyio
async def test_dashboard_gdpr_and_organizations_return_documented_shapes():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        async with await _client(app) as client:
            gdpr = await client.get("/api/v1/dashboard/gdpr/", headers=admin_headers)
            assert gdpr.status_code == 200
            assert gdpr.json() == {
                "deletion_requests": {"total": 0, "by_status": {}, "grace_period_expiring_7d": 0},
                "data_exports": {"total_today": 0, "total_this_month": 0},
            }

            orgs = await client.get("/api/v1/dashboard/organizations/", headers=admin_headers)
            assert orgs.status_code == 200
            assert orgs.json() == {"enabled": False}


@pytest.mark.anyio
async def test_dashboard_endpoints_require_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, regular_headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/dashboard/stats/", headers=regular_headers)

    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
