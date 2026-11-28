"""
Tests for the Wave G GDPR user router (spec z_aud_3, Wave G chunk 3/4, task 12.1) — request/
confirm/cancel/status/export — against a real app, a real ephemeral aiosqlite database, real
bcrypt password hashes, and real TOTP codes (`pyotp`) for the 2FA-gate fix. No mocks.
"""

import uuid

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.rbac_service import assign_role_async, create_permission_async, create_role_async
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import MFAType, User

PASSWORD = "correct-horse-battery-staple"


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-gdpr-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(
    app,
    *,
    email: str,
    password: str = PASSWORD,
    mfa_type: MFAType = MFAType.NONE,
    mfa_secret: str | None = None,
) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password(password)
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=password_hash,
                is_active=True,
                mfa_type=mfa_type,
                mfa_secret=mfa_secret,
            )
        )


def _auth_headers(app, user: User) -> dict:
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=user.id, application_id="default"
    ).access_token
    return {"Authorization": f"Bearer {token}"}


async def _grant_permission(app, user: User, *, code: str) -> None:
    """Assigns `user` a fresh role carrying one real permission — used to reproduce the real
    Django `export_user_data` permissions crash (bug #1) and prove this port's fix instead."""
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        await create_permission_async(session, code=code, name=code, description="")
        role = await create_role_async(
            session, code=f"role-{uuid.uuid4().hex[:8]}", name="Test role", permission_codes=[code]
        )
        await assign_role_async(session, user.id, role.code)


@pytest.mark.anyio
async def test_request_deletion_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/request-account-deletion/", json={"password": PASSWORD})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_request_deletion_missing_reauth_is_reauth_required():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="noreauth@example.com")
        async with await _client(app) as client:
            response = await client.post("/api/v1/request-account-deletion/", json={}, headers=_auth_headers(app, user))
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "REAUTH_REQUIRED"


@pytest.mark.anyio
async def test_request_deletion_wrong_password_has_no_code():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="wrongpw@example.com")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/request-account-deletion/",
                json={"password": "not-the-password"},
                headers=_auth_headers(app, user),
            )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Invalid password"
    assert "code" not in body


@pytest.mark.anyio
async def test_request_deletion_success_creates_and_supersedes_active_request():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="delme@example.com")
        async with await _client(app) as client:
            headers = _auth_headers(app, user)
            first = await client.post("/api/v1/request-account-deletion/", json={"password": PASSWORD}, headers=headers)
            assert first.status_code == 201
            body = first.json()
            assert set(body.keys()) == {"request_id", "message", "grace_period_days"}
            assert body["grace_period_days"] == 30

            # A second request supersedes (cancels) the first — no DELETION_ALREADY_PENDING
            # exists in the real code (see gdpr_service.py's module docstring).
            second = await client.post(
                "/api/v1/request-account-deletion/", json={"password": PASSWORD}, headers=headers
            )
            assert second.status_code == 201

            status_resp = await client.get("/api/v1/account-deletion-status/", headers=headers)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["total_requests"] == 2
    assert status_body["active_request"]["status"] == "confirmation_sent"
    statuses = {h["status"] for h in status_body["history"]}
    assert "cancelled" in statuses


@pytest.mark.anyio
async def test_request_deletion_with_2fa_requires_and_verifies_real_totp_code():
    """Reproduces bug #2's fix: Django's own equivalent gate crashes with `AttributeError` for
    every 2FA-enabled user (verified empirically against live Django code) — this port implements
    a real, working TOTP gate instead."""
    secret = pyotp.random_base32()
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="has2fa@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            missing_code = await client.post(
                "/api/v1/request-account-deletion/", json={"password": PASSWORD}, headers=headers
            )
            assert missing_code.status_code == 400
            assert missing_code.json()["error"] == "Two-factor authentication code required"

            wrong_code = await client.post(
                "/api/v1/request-account-deletion/",
                json={"password": PASSWORD, "otp_code": "000000"},
                headers=headers,
            )
            assert wrong_code.status_code == 400
            assert wrong_code.json()["error"] == "Invalid two-factor authentication code"

            valid_code = pyotp.TOTP(secret).now()
            success = await client.post(
                "/api/v1/request-account-deletion/",
                json={"password": PASSWORD, "otp_code": valid_code},
                headers=headers,
            )
    assert success.status_code == 201


@pytest.mark.anyio
async def test_confirm_deletion_success_starts_grace_period():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="confirm@example.com")
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            request_resp = await client.post(
                "/api/v1/request-account-deletion/", json={"password": PASSWORD}, headers=headers
            )
            request_id = request_resp.json()["request_id"]

            # Fetch the real token directly from the DB (no email backend is wired in — see
            # module docstring — so the test reads it the same way a real user would from their
            # inbox: it's simply not delivered over HTTP).
            session_factory = app.state.tenxyte_session_factory
            from tenxyte.adapters.fastapi.models_sa import AccountDeletionRequestDB

            async with session_factory() as session:
                row = await session.get(AccountDeletionRequestDB, request_id)
                token = row.confirmation_token

            confirm = await client.post("/api/v1/confirm-account-deletion/", json={"token": token})
            assert confirm.status_code == 200
            body = confirm.json()
            assert set(body.keys()) == {"message", "grace_period_ends_at", "days_remaining"}

            # No expiry check exists in the real code — reusing an already-confirmed token just
            # falls through to the generic "not found" error, same as any other invalid token.
            reuse = await client.post("/api/v1/confirm-account-deletion/", json={"token": token})
    assert reuse.status_code == 400
    assert reuse.json() == {"error": "Invalid or expired confirmation token"}


@pytest.mark.anyio
async def test_confirm_deletion_unknown_token_is_400_not_404():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/confirm-account-deletion/", json={"token": "does-not-exist"})
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid or expired confirmation token"}


@pytest.mark.anyio
async def test_cancel_deletion_requires_reauth_and_active_request():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="cancelme@example.com")
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            no_reauth = await client.post("/api/v1/cancel-account-deletion/", json={}, headers=headers)
            assert no_reauth.status_code == 400
            assert no_reauth.json()["code"] == "REAUTH_REQUIRED"

            no_active = await client.post(
                "/api/v1/cancel-account-deletion/", json={"password": PASSWORD}, headers=headers
            )
            assert no_active.status_code == 400
            assert no_active.json() == {"error": "No active deletion requests found"}

            await client.post("/api/v1/request-account-deletion/", json={"password": PASSWORD}, headers=headers)
            cancel = await client.post("/api/v1/cancel-account-deletion/", json={"password": PASSWORD}, headers=headers)
    assert cancel.status_code == 200
    assert cancel.json() == {"message": "Cancelled 1 deletion request(s).", "cancelled_count": 1}


@pytest.mark.anyio
async def test_export_user_data_with_real_permission_does_not_crash():
    """Reproduces bug #1's fix: the real Django `export_user_data` 500s for any user holding an
    effective permission (verified empirically against live Django code) — this port resolves
    the effective codes back to real rows instead of crashing."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="hasperm@example.com")
        await _grant_permission(app, user, code="test.export.permission")
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            response = await client.post("/api/v1/export-user-data/", json={"password": PASSWORD}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["permissions"] == [
        {
            "code": "test.export.permission",
            "name": "test.export.permission",
            "granted_at": body["permissions"][0]["granted_at"],
        }
    ]
    assert body["user_info"]["email"] == "hasperm@example.com"
    assert body["user_info"]["is_restricted"] is False
    assert body["login_attempts"] == []
    assert body["applications"] == []
    assert body["export_metadata"]["compliance"] == ["RGPD", "GDPR", "CCPA"]


@pytest.mark.anyio
async def test_export_user_data_reauth_failure_carries_code():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="exportwrongpw@example.com")
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            missing = await client.post("/api/v1/export-user-data/", json={}, headers=headers)
            assert missing.status_code == 400
            assert missing.json()["code"] == "REAUTH_REQUIRED"

            wrong = await client.post("/api/v1/export-user-data/", json={"password": "nope"}, headers=headers)
    assert wrong.status_code == 400
    assert wrong.json() == {"error": "Current password is incorrect", "code": "INVALID_PASSWORD"}


@pytest.mark.anyio
async def test_export_user_data_writes_audit_log():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="auditexport@example.com")
        await _grant_permission(app, user, code="dashboard.view")
        headers = _auth_headers(app, user)
        async with await _client(app) as client:
            response = await client.post("/api/v1/export-user-data/", json={"password": PASSWORD}, headers=headers)
            assert response.status_code == 200

            gdpr_stats = await client.get("/api/v1/dashboard/gdpr/", headers=headers)
    assert gdpr_stats.status_code == 200
    stats_body = gdpr_stats.json()
    assert stats_body["data_exports"]["total_today"] == 1
