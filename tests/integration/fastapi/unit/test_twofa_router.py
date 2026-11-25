"""
Tests for the Wave C 2FA-enrollment router (spec z_aud_3, task 7.1) — 2fa/status, 2fa/setup,
2fa/confirm, 2fa/disable, 2fa/backup-codes — against a real app, a real ephemeral aiosqlite
database, and real signed tokens (no mocks).
"""

import uuid

import bcrypt
import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
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
            return "test-secret-key-for-twofa-router-tests"
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
    password: str = "correct-horse-battery-staple",
    mfa_type: MFAType = MFAType.NONE,
    mfa_secret: str | None = None,
) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
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


async def _login(client, email: str, password: str = "correct-horse-battery-staple") -> str:
    response = await client.post("/api/v1/login/email/", json={"email": email, "password": password})
    return response.json()["access_token"]


@pytest.mark.anyio
async def test_status_not_enabled():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="status1@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "status1@example.com")
            response = await client.get("/api/v1/2fa/status/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json() == {"is_enabled": False, "backup_codes_remaining": 0}


@pytest.mark.anyio
async def test_setup_then_confirm_full_flow():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="setupconfirm@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "setupconfirm@example.com")
            headers = {"Authorization": f"Bearer {access_token}"}

            setup_response = await client.post("/api/v1/2fa/setup/", headers=headers)
            assert setup_response.status_code == 200
            setup_body = setup_response.json()
            assert setup_body["secret"]
            assert setup_body["qr_code"]
            assert len(setup_body["backup_codes"]) == 10

            secret = setup_body["secret"]
            code = pyotp.TOTP(secret).now()
            confirm_response = await client.post("/api/v1/2fa/confirm/", json={"code": code}, headers=headers)
            assert confirm_response.status_code == 200
            confirm_body = confirm_response.json()
            assert confirm_body["is_enabled"] is True
            # Full-scope token used throughout — no bootstrap upgrade fields expected.
            assert "access_token" not in confirm_body

            status_response = await client.get("/api/v1/2fa/status/", headers=headers)

    assert status_response.json() == {"is_enabled": True, "backup_codes_remaining": 10}


@pytest.mark.anyio
async def test_setup_rejected_when_already_enabled():
    app = _build_app()
    async with app.router.lifespan_context(app):
        # A 2FA-enabled account can't complete a normal login without a TOTP code (out of scope
        # for this test) — issue a token directly instead.
        secret = pyotp.random_base32()
        user = await _create_user(app, email="alreadyon@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        access_token = app.state.tenxyte_jwt_service.generate_new_token_pair(
            user_id=user.id, application_id="default"
        ).access_token
        async with await _client(app) as client:
            response = await client.post("/api/v1/2fa/setup/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 400
    assert response.json()["code"] == "2FA_ALREADY_ENABLED"


@pytest.mark.anyio
async def test_confirm_wrong_code_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="wrongconfirm@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "wrongconfirm@example.com")
            headers = {"Authorization": f"Bearer {access_token}"}
            await client.post("/api/v1/2fa/setup/", headers=headers)
            response = await client.post("/api/v1/2fa/confirm/", json={"code": "000000"}, headers=headers)

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CODE"


@pytest.mark.anyio
async def test_bootstrap_token_confirm_upgrades_to_full_scope_and_blacklists_bootstrap():
    app = _build_app()
    async with app.router.lifespan_context(app):
        # A superuser with no MFA configured triggers the 2fa_setup_only bootstrap branch on login.
        session_factory = app.state.tenxyte_session_factory
        password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            await repo.create(
                User(
                    id=str(uuid.uuid4()),
                    email="bootstrapadmin@example.com",
                    password_hash=password_hash,
                    is_active=True,
                    is_superuser=True,
                )
            )

        async with await _client(app) as client:
            login_response = await client.post(
                "/api/v1/login/email/",
                json={"email": "bootstrapadmin@example.com", "password": "correct-horse-battery-staple"},
            )
            bootstrap_token = login_response.json()["access_token"]
            assert login_response.json()["token_scope"] == "2fa_setup_only"
            headers = {"Authorization": f"Bearer {bootstrap_token}"}

            setup_response = await client.post("/api/v1/2fa/setup/", headers=headers)
            secret = setup_response.json()["secret"]
            code = pyotp.TOTP(secret).now()

            confirm_response = await client.post("/api/v1/2fa/confirm/", json={"code": code}, headers=headers)
            assert confirm_response.status_code == 200
            confirm_body = confirm_response.json()
            assert confirm_body["access_token"]
            assert confirm_body["refresh_token"]

            # The bootstrap token itself should now be blacklisted/rejected.
            reuse_response = await client.get("/api/v1/2fa/status/", headers=headers)

    assert reuse_response.status_code == 401
    assert reuse_response.json()["code"] == "TOKEN_INVALID"


@pytest.mark.anyio
async def test_disable_success_with_password_reauth():
    app = _build_app()
    async with app.router.lifespan_context(app):
        secret = pyotp.random_base32()
        user = await _create_user(app, email="disableme@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        access_token = app.state.tenxyte_jwt_service.generate_new_token_pair(
            user_id=user.id, application_id="default"
        ).access_token
        async with await _client(app) as client:
            code = pyotp.TOTP(secret).now()
            response = await client.post(
                "/api/v1/2fa/disable/",
                json={"code": code, "password": "correct-horse-battery-staple"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {"message": "2FA disabled successfully", "is_enabled": False}

            status_response = await client.get(
                "/api/v1/2fa/status/", headers={"Authorization": f"Bearer {access_token}"}
            )

    assert status_response.json()["is_enabled"] is False


@pytest.mark.anyio
async def test_disable_missing_reauth_proof():
    app = _build_app()
    async with app.router.lifespan_context(app):
        secret = pyotp.random_base32()
        user = await _create_user(app, email="noreauthdisable@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        access_token = app.state.tenxyte_jwt_service.generate_new_token_pair(
            user_id=user.id, application_id="default"
        ).access_token
        async with await _client(app) as client:
            code = pyotp.TOTP(secret).now()
            response = await client.post(
                "/api/v1/2fa/disable/", json={"code": code}, headers={"Authorization": f"Bearer {access_token}"}
            )

    assert response.status_code == 400
    assert response.json()["code"] == "REAUTH_REQUIRED"


@pytest.mark.anyio
async def test_disable_wrong_password_reauth():
    app = _build_app()
    async with app.router.lifespan_context(app):
        secret = pyotp.random_base32()
        user = await _create_user(app, email="wrongreauth@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        access_token = app.state.tenxyte_jwt_service.generate_new_token_pair(
            user_id=user.id, application_id="default"
        ).access_token
        async with await _client(app) as client:
            code = pyotp.TOTP(secret).now()
            response = await client.post(
                "/api/v1/2fa/disable/",
                json={"code": code, "password": "wrong-password"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PASSWORD"


@pytest.mark.anyio
async def test_backup_codes_regeneration():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="backupcodes@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "backupcodes@example.com")
            headers = {"Authorization": f"Bearer {access_token}"}

            setup_response = await client.post("/api/v1/2fa/setup/", headers=headers)
            secret = setup_response.json()["secret"]
            totp = pyotp.TOTP(secret)
            code = totp.now()
            await client.post("/api/v1/2fa/confirm/", json={"code": code}, headers=headers)

            # A code from the *next* 30s step — still within the service's ±1-step tolerance,
            # but distinct from the one just consumed above (replay protection correctly rejects
            # reusing the identical code, which `now()` would produce again inside the same step).
            import time

            new_code = totp.at(time.time() + 30)
            regen_response = await client.post("/api/v1/2fa/backup-codes/", json={"code": new_code}, headers=headers)

    assert regen_response.status_code == 200
    body = regen_response.json()
    assert len(body["backup_codes"]) == 10


@pytest.mark.anyio
async def test_all_2fa_endpoints_require_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        status_r = await client.get("/api/v1/2fa/status/")
        setup_r = await client.post("/api/v1/2fa/setup/")
        confirm_r = await client.post("/api/v1/2fa/confirm/", json={"code": "123456"})
        disable_r = await client.post("/api/v1/2fa/disable/", json={"code": "123456"})
        backup_r = await client.post("/api/v1/2fa/backup-codes/", json={"code": "123456"})

    for response in (status_r, setup_r, confirm_r, disable_r, backup_r):
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH_REQUIRED"
