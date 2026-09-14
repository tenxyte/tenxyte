"""
Tests for the Wave C passwordless-login-via-SMS-OTP router (spec z_aud_3, task 7.1) —
login/otp/request, login/otp/verify — against a real app, a real ephemeral aiosqlite database, and
real signed tokens (no mocks).

`Settings.otp_login_enabled` defaults off (matching Django's `OTP_LOGIN_ENABLED`), so every test
here runs against a `_TestProvider` that turns it on — the default-off gate itself is covered by
`test_feature_disabled_by_default`.
"""

import uuid

import bcrypt
import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.otp_service import generate_otp
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import MFAType, User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _EnabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-login-otp-router-tests"
        if name == "TENXYTE_OTP_LOGIN_ENABLED":
            return True
        return super().get(name, default)


class _DisabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-login-otp-router-tests"
        return super().get(name, default)


def _build_app(*, enabled: bool = True):
    provider = _EnabledProvider() if enabled else _DisabledProvider()
    settings = Settings(provider=provider)
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(
    app,
    *,
    email: str,
    phone_country_code: str,
    phone_number: str,
    is_active: bool = True,
    is_superuser: bool = False,
    is_staff: bool = False,
    mfa_type: MFAType = MFAType.NONE,
    mfa_secret: str | None = None,
) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=password_hash,
                is_active=is_active,
                is_superuser=is_superuser,
                is_staff=is_staff,
                mfa_type=mfa_type,
                mfa_secret=mfa_secret,
                metadata={"phone_country_code": phone_country_code, "phone_number": phone_number},
            )
        )


async def _generate_login_code(app, user_id: str) -> str:
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        _row, raw_code = await generate_otp(session, user_id, "login", app.state.tenxyte_settings)
        return raw_code


@pytest.mark.anyio
async def test_feature_disabled_by_default():
    app = _build_app(enabled=False)
    async with app.router.lifespan_context(app), await _client(app) as client:
        request_response = await client.post(
            "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "612345678"}
        )
        verify_response = await client.post(
            "/api/v1/login/otp/verify/",
            json={"phone_country_code": "33", "phone_number": "612345678", "otp_code": "123456"},
        )

    for response in (request_response, verify_response):
        assert response.status_code == 404
        assert response.json()["code"] == "FEATURE_DISABLED"


@pytest.mark.anyio
async def test_request_missing_fields():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/login/otp/request/", json={"phone_country_code": "33"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_request_existing_account_sends_code():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="existing@example.com", phone_country_code="33", phone_number="611111111")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "611111111"}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "OTP sent"
    assert body["channel"] == "sms"
    assert uuid.UUID(body["otp_id"])


@pytest.mark.anyio
async def test_request_unknown_number_auto_registers_by_default():
    app = _build_app()
    async with app.router.lifespan_context(app):
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "622222222"}
            )
        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "OTP sent"

        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            user = await repo.get_by_phone("33", "622222222")
    assert user is not None
    assert user.is_active is True


@pytest.mark.anyio
async def test_request_anti_enumeration_when_auto_register_disabled():
    """Property 3 (spec z_aud_3): with auto-register off, an unknown number gets an
    identically-shaped response and no account/code is created."""

    class _NoAutoRegisterProvider(_EnabledProvider):
        def get(self, name, default=None):
            if name == "TENXYTE_OTP_LOGIN_AUTO_REGISTER":
                return False
            return super().get(name, default)

    settings = Settings(provider=_NoAutoRegisterProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app):
        await _create_user(app, email="real@example.com", phone_country_code="33", phone_number="633333333")
        async with await _client(app) as client:
            known_response = await client.post(
                "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "633333333"}
            )
            unknown_response = await client.post(
                "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "699999999"}
            )

        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            unknown_number_created = await repo.get_by_phone("33", "699999999")

    assert known_response.status_code == unknown_response.status_code == 200
    assert set(known_response.json().keys()) == set(unknown_response.json().keys())
    for body in (known_response.json(), unknown_response.json()):
        assert body["message"] == "OTP sent"
        assert body["channel"] == "sms"
        assert uuid.UUID(body["otp_id"])
    assert unknown_number_created is None


@pytest.mark.anyio
async def test_verify_unknown_account_and_wrong_code_both_401_otp_invalid():
    """The CODE (not necessarily the message) matches between an unregistered number and a
    registered number with no outstanding/valid code — see routers/login_otp.py's module
    docstring for the message-content caveat inherited from Django's own real behavior."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="wrongcode@example.com", phone_country_code="33", phone_number="644444444")
        async with await _client(app) as client:
            unknown_response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "655555555", "otp_code": "000000"},
            )
            no_code_yet_response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "644444444", "otp_code": "000000"},
            )

    assert unknown_response.status_code == no_code_yet_response.status_code == 401
    assert unknown_response.json()["code"] == no_code_yet_response.json()["code"] == "OTP_INVALID"


@pytest.mark.anyio
async def test_verify_success_issues_tokens():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="verifyme@example.com", phone_country_code="33", phone_number="666666666")
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "666666666", "otp_code": raw_code},
            )

        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            refreshed = await repo.get_by_id(user.id)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "verifyme@example.com"
    assert body["requires_2fa"] is False
    assert body["must_change_password"] is False
    assert refreshed.phone_verified is True


@pytest.mark.anyio
async def test_verify_code_is_single_use():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="singleuse@example.com", phone_country_code="33", phone_number="677777777")
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            first = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "677777777", "otp_code": raw_code},
            )
            second = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "677777777", "otp_code": raw_code},
            )

    assert first.status_code == 200
    assert second.status_code == 401
    assert second.json()["code"] == "OTP_INVALID"


@pytest.mark.anyio
async def test_verify_admin_without_mfa_gets_bootstrap_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(
            app,
            email="admin@example.com",
            phone_country_code="33",
            phone_number="688888888",
            is_superuser=True,
        )
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "688888888", "otp_code": raw_code},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["token_scope"] == "2fa_setup_only"
    assert body["requires_2fa_setup"] is True
    assert "refresh_token" not in body


@pytest.mark.anyio
async def test_verify_2fa_enabled_requires_totp_code_before_consuming_otp():
    app = _build_app()
    async with app.router.lifespan_context(app):
        secret = pyotp.random_base32()
        user = await _create_user(
            app,
            email="mfa@example.com",
            phone_country_code="33",
            phone_number="699000000",
            mfa_type=MFAType.TOTP,
            mfa_secret=secret,
        )
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            no_totp_response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "699000000", "otp_code": raw_code},
            )
            assert no_totp_response.status_code == 401
            assert no_totp_response.json()["code"] == "2FA_REQUIRED"

            # The OTP must NOT have been consumed by the rejected first attempt — the same code
            # plus a valid TOTP code now succeeds.
            totp_code = pyotp.TOTP(secret).now()
            success_response = await client.post(
                "/api/v1/login/otp/verify/",
                json={
                    "phone_country_code": "33",
                    "phone_number": "699000000",
                    "otp_code": raw_code,
                    "totp_code": totp_code,
                },
            )

    assert success_response.status_code == 200
    body = success_response.json()
    assert body["access_token"]
    assert body["requires_2fa"] is True


@pytest.mark.anyio
async def test_verify_2fa_enabled_wrong_totp_code_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        secret = pyotp.random_base32()
        user = await _create_user(
            app,
            email="mfawrong@example.com",
            phone_country_code="33",
            phone_number="699000001",
            mfa_type=MFAType.TOTP,
            mfa_secret=secret,
        )
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/verify/",
                json={
                    "phone_country_code": "33",
                    "phone_number": "699000001",
                    "otp_code": raw_code,
                    "totp_code": "000000",
                },
            )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_2FA_CODE"


@pytest.mark.anyio
async def test_verify_inactive_account_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(
            app,
            email="inactive@example.com",
            phone_country_code="33",
            phone_number="699000002",
            is_active=False,
        )
        raw_code = await _generate_login_code(app, user.id)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "33", "phone_number": "699000002", "otp_code": raw_code},
            )

    assert response.status_code == 401
    assert response.json()["code"] == "ACCOUNT_INACTIVE"
