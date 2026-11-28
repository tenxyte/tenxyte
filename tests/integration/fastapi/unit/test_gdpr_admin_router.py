"""
Tests for the Wave G GDPR admin router (spec z_aud_3, Wave G chunk 4/4, task 12.1) —
admin/deletion-requests/* — against a real app, a real ephemeral aiosqlite database, and real
signed tokens. No mocks.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import AccountDeletionRequestDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

PASSWORD = "correct-horse-battery-staple"


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-gdpr-admin-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email: str | None = None, is_superuser: bool = False) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password(PASSWORD)
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email or f"user-{uuid.uuid4().hex}@example.com",
                password_hash=password_hash,
                is_active=True,
                is_superuser=is_superuser,
            )
        )


def _auth_headers(app, user: User) -> dict:
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=user.id, application_id="default"
    ).access_token
    return {"Authorization": f"Bearer {token}"}


async def _seed_request(app, user_id: str, *, status: str = "confirmed", grace_period_ends_at=None) -> str:
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        row = AccountDeletionRequestDB(
            user_id=user_id,
            status=status,
            confirmation_token=f"token-{uuid.uuid4().hex}",
            grace_period_ends_at=grace_period_ends_at,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


@pytest.mark.anyio
async def test_list_requires_gdpr_admin_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        non_admin = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/admin/deletion-requests/", headers=_auth_headers(app, non_admin))
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_REQUIRED"


@pytest.mark.anyio
async def test_list_returns_real_serializer_fields_no_user_agent():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        target = await _create_user(app, email="target@example.com")
        await _seed_request(app, target.id, status="pending")
        async with await _client(app) as client:
            response = await client.get("/api/v1/admin/deletion-requests/", headers=_auth_headers(app, admin))
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    row = body["results"][0]
    assert set(row.keys()) == {
        "id",
        "user",
        "user_email",
        "status",
        "requested_at",
        "confirmed_at",
        "grace_period_ends_at",
        "completed_at",
        "ip_address",
        "reason",
        "admin_notes",
        "processed_by",
        "processed_by_email",
        "is_grace_period_expired",
    }
    assert row["user_email"] == "target@example.com"


@pytest.mark.anyio
async def test_list_filters_by_status_and_user_id():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        user_a = await _create_user(app, email="a@example.com")
        user_b = await _create_user(app, email="b@example.com")
        await _seed_request(app, user_a.id, status="pending")
        await _seed_request(app, user_b.id, status="confirmed")
        headers = _auth_headers(app, admin)
        async with await _client(app) as client:
            by_status = await client.get(
                "/api/v1/admin/deletion-requests/", params={"status": "confirmed"}, headers=headers
            )
            by_user = await client.get(
                "/api/v1/admin/deletion-requests/", params={"user_id": user_a.id}, headers=headers
            )
    assert by_status.json()["count"] == 1
    assert by_status.json()["results"][0]["user_email"] == "b@example.com"
    assert by_user.json()["count"] == 1
    assert by_user.json()["results"][0]["user_email"] == "a@example.com"


@pytest.mark.anyio
async def test_list_unrecognized_ordering_falls_back_to_requested_at_desc():
    """Real Django behavior: `?ordering=user__email` (documented as valid) is never actually
    applied — see gdpr_service.py's `# GDPR admin` docstring."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        user_a = await _create_user(app, email="first@example.com")
        user_b = await _create_user(app, email="second@example.com")
        first_id = await _seed_request(app, user_a.id, status="pending")
        second_id = await _seed_request(app, user_b.id, status="pending")
        async with await _client(app) as client:
            response = await client.get(
                "/api/v1/admin/deletion-requests/",
                params={"ordering": "user__email"},
                headers=_auth_headers(app, admin),
            )
    assert response.status_code == 200
    ids = [r["id"] for r in response.json()["results"]]
    # Falls back to -requested_at: most recently created (second) comes first.
    assert ids == [second_id, first_id]


@pytest.mark.anyio
async def test_detail_not_found_is_404_with_code():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        async with await _client(app) as client:
            response = await client.get(
                "/api/v1/admin/deletion-requests/does-not-exist/", headers=_auth_headers(app, admin)
            )
    assert response.status_code == 404
    assert response.json() == {"error": "Deletion request not found", "code": "NOT_FOUND"}


@pytest.mark.anyio
async def test_process_requires_gdpr_process_not_gdpr_admin():
    """`gdpr.admin` (list/detail) and `gdpr.process` (process/process-expired) are genuinely
    different permissions in Django — a user with only the list/detail permission cannot process
    a deletion. Reproduced via the RBAC service directly rather than the superuser bypass, to
    actually distinguish the two permission codes."""
    from tenxyte.adapters.fastapi.rbac_service import assign_role_async, create_role_async

    app = _build_app()
    async with app.router.lifespan_context(app):
        target = await _create_user(app, email="willbedeleted@example.com")
        request_id = await _seed_request(app, target.id, status="confirmed")

        list_only_admin = await _create_user(app, email="listonly@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            from tenxyte.adapters.fastapi.rbac_service import create_permission_async

            await create_permission_async(session, code="gdpr.admin", name="GDPR admin", description="")
            role = await create_role_async(
                session, code="gdpr-list-only", name="GDPR list-only", permission_codes=["gdpr.admin"]
            )
            await assign_role_async(session, list_only_admin.id, role.code)

        async with await _client(app) as client:
            response = await client.post(
                f"/api/v1/admin/deletion-requests/{request_id}/process/",
                json={"confirmation": "PERMANENTLY DELETE"},
                headers=_auth_headers(app, list_only_admin),
            )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_process_requires_confirmed_status_and_exact_confirmation_text():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        target = await _create_user(app, email="pendingdel@example.com")
        pending_id = await _seed_request(app, target.id, status="pending")
        headers = _auth_headers(app, admin)
        async with await _client(app) as client:
            wrong_status = await client.post(
                f"/api/v1/admin/deletion-requests/{pending_id}/process/",
                json={"confirmation": "PERMANENTLY DELETE"},
                headers=headers,
            )
            assert wrong_status.status_code == 400
            assert wrong_status.json()["code"] == "REQUEST_NOT_CONFIRMED"

            confirmed_id = await _seed_request(app, target.id, status="confirmed")
            wrong_confirmation = await client.post(
                f"/api/v1/admin/deletion-requests/{confirmed_id}/process/",
                json={"confirmation": "delete please"},
                headers=headers,
            )
    assert wrong_confirmation.status_code == 400
    assert wrong_confirmation.json()["code"] == "CONFIRMATION_REQUIRED"


@pytest.mark.anyio
async def test_process_success_soft_deletes_user_and_includes_request_field():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        target = await _create_user(app, email="realdelete@example.com")
        confirmed_id = await _seed_request(app, target.id, status="confirmed")
        async with await _client(app) as client:
            response = await client.post(
                f"/api/v1/admin/deletion-requests/{confirmed_id}/process/",
                json={"confirmation": "PERMANENTLY DELETE", "admin_notes": "user requested via support"},
                headers=_auth_headers(app, admin),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["deletion_completed"] is True
            assert body["data_anonymized"] is True
            assert body["user_notified"] is True
            assert body["audit_log_id"] == confirmed_id
            # The undocumented extra field the real Django view's success response actually carries.
            assert body["request"]["status"] == "completed"
            assert body["request"]["admin_notes"] == "user requested via support"

            session_factory = app.state.tenxyte_session_factory
            from tenxyte.adapters.fastapi.models_sa import UserDB

            async with session_factory() as session:
                row = await session.get(UserDB, target.id)
                assert row.is_deleted is True
                assert row.email.startswith("deleted_")


@pytest.mark.anyio
async def test_process_expired_only_processes_past_grace_period():
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin = await _create_user(app, is_superuser=True)
        expired_user = await _create_user(app, email="expired@example.com")
        not_yet_user = await _create_user(app, email="notyet@example.com")
        now = datetime.now(timezone.utc)
        await _seed_request(app, expired_user.id, status="confirmed", grace_period_ends_at=now - timedelta(days=1))
        await _seed_request(app, not_yet_user.id, status="confirmed", grace_period_ends_at=now + timedelta(days=5))
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/admin/deletion-requests/process-expired/", headers=_auth_headers(app, admin)
            )
            assert response.status_code == 200
            assert response.json() == {"message": "1 deletion(s) processed, 0 failed", "processed": 1, "failed": 0}

            session_factory = app.state.tenxyte_session_factory
            from tenxyte.adapters.fastapi.models_sa import UserDB

            async with session_factory() as session:
                expired_row = await session.get(UserDB, expired_user.id)
                not_yet_row = await session.get(UserDB, not_yet_user.id)
                assert expired_row.is_deleted is True
                assert not_yet_row.is_deleted is False
