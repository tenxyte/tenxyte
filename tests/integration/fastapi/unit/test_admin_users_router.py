"""
Tests for the Wave D Admin Users router (spec z_aud_3, Wave D chunk 3/5, task 10.1) —
admin/users/* — against a real app, a real ephemeral aiosqlite database, and real signed tokens
(no mocks).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
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
            return "test-secret-key-for-admin-users-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email=None, is_superuser=False) -> tuple[str, dict]:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password("correct-horse-battery-staple")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        created = await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email or f"user-{uuid.uuid4().hex}@example.com",
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
async def test_list_and_get_user_detail():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        target_id, _ = await _create_user(app, email="target@example.com")
        async with await _client(app) as client:
            listing = await client.get("/api/v1/admin/users/", headers=admin_headers)
            assert listing.status_code == 200
            assert listing.json()["count"] >= 2

            detail = await client.get(f"/api/v1/admin/users/{target_id}/", headers=admin_headers)
            assert detail.status_code == 200
            body = detail.json()
            assert body["email"] == "target@example.com"
            assert body["is_banned"] is False
            assert body["is_locked"] is False
            assert body["roles"] == []
            assert body["permissions"] == []

            missing = await client.get(f"/api/v1/admin/users/{uuid.uuid4()}/", headers=admin_headers)
            assert missing.status_code == 404
            assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_update_user_drops_privilege_fields_like_django():
    """Real Django finding (see admin_user_service.py docstring): is_staff/is_superuser/
    max_sessions/max_devices pass validation but are never persisted by the admin endpoint."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        target_id, _ = await _create_user(app)
        async with await _client(app) as client:
            update = await client.patch(
                f"/api/v1/admin/users/{target_id}/",
                json={
                    "first_name": "Jane",
                    "is_staff": True,
                    "is_superuser": True,
                    "max_sessions": 9,
                },
                headers=admin_headers,
            )
            assert update.status_code == 200
            body = update.json()
            assert body["first_name"] == "Jane"
            assert body["is_staff"] is False
            assert body["is_superuser"] is False
            assert body["max_sessions"] == 1


@pytest.mark.anyio
async def test_soft_delete_anonymizes_and_blocks_double_delete():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        target_id, _ = await _create_user(app, email="deleteme@example.com")
        async with await _client(app) as client:
            delete = await client.delete(f"/api/v1/admin/users/{target_id}/", headers=admin_headers)
            assert delete.status_code == 200
            assert delete.json()["message"] == "User soft-deleted successfully"

            again = await client.delete(f"/api/v1/admin/users/{target_id}/", headers=admin_headers)
            assert again.status_code == 400
            assert again.json()["code"] == "ALREADY_DELETED"


@pytest.mark.anyio
async def test_ban_unban_lifecycle():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        target_id, _ = await _create_user(app)
        async with await _client(app) as client:
            ban = await client.post(
                f"/api/v1/admin/users/{target_id}/ban/", json={"reason": "spam"}, headers=admin_headers
            )
            assert ban.status_code == 200
            assert ban.json()["user"]["is_banned"] is True
            assert ban.json()["user"]["is_active"] is False

            already = await client.post(f"/api/v1/admin/users/{target_id}/ban/", json={}, headers=admin_headers)
            assert already.status_code == 400
            assert already.json()["code"] == "ALREADY_BANNED"

            unban = await client.post(f"/api/v1/admin/users/{target_id}/unban/", headers=admin_headers)
            assert unban.status_code == 200
            assert unban.json()["user"]["is_banned"] is False
            assert unban.json()["user"]["is_active"] is True

            not_banned = await client.post(f"/api/v1/admin/users/{target_id}/unban/", headers=admin_headers)
            assert not_banned.status_code == 400
            assert not_banned.json()["code"] == "NOT_BANNED"


@pytest.mark.anyio
async def test_lock_unlock_lifecycle_and_escalation():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        target_id, _ = await _create_user(app)
        async with await _client(app) as client:
            lock = await client.post(
                f"/api/v1/admin/users/{target_id}/lock/", json={"duration_minutes": 10}, headers=admin_headers
            )
            assert lock.status_code == 200
            assert lock.json()["message"] == "User locked for 10 minutes"
            assert lock.json()["user"]["is_locked"] is True

            already = await client.post(f"/api/v1/admin/users/{target_id}/lock/", json={}, headers=admin_headers)
            assert already.status_code == 400
            assert already.json()["code"] == "ALREADY_LOCKED"

            unlock = await client.post(f"/api/v1/admin/users/{target_id}/unlock/", headers=admin_headers)
            assert unlock.status_code == 200
            assert unlock.json()["user"]["is_locked"] is False

            # 2nd consecutive lock escalates: 10 * 2^(2-1) = 20 minutes.
            second_lock = await client.post(
                f"/api/v1/admin/users/{target_id}/lock/", json={"duration_minutes": 10}, headers=admin_headers
            )
            assert second_lock.status_code == 200
            assert second_lock.json()["message"] == "User locked for 20 minutes"

            not_locked_again = await client.post(f"/api/v1/admin/users/{target_id}/unlock/", headers=admin_headers)
            assert not_locked_again.status_code == 200
            still_not_locked = await client.post(f"/api/v1/admin/users/{target_id}/unlock/", headers=admin_headers)
            assert still_not_locked.status_code == 400
            assert still_not_locked.json()["code"] == "NOT_LOCKED"


@pytest.mark.anyio
async def test_admin_users_endpoints_require_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, regular_headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/admin/users/", headers=regular_headers)

    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
