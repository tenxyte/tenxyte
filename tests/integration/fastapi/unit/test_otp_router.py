"""
Tests for the Wave C OTP-verification router (spec z_aud_3, task 7.1) — otp/request,
otp/verify/email, otp/verify/phone — against a real app, a real ephemeral aiosqlite database, and
real signed tokens (no mocks).
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
            return "test-secret-key-for-otp-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(
    app, *, email: str, phone_country_code: str | None = None, phone_number: str | None = None
) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password("correct-horse-battery-staple")
    metadata = {}
    if phone_country_code and phone_number:
        metadata = {"phone_country_code": phone_country_code, "phone_number": phone_number}
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(id=str(uuid.uuid4()), email=email, password_hash=password_hash, is_active=True, metadata=metadata)
        )


async def _login(client, email: str) -> str:
    response = await client.post(
        "/api/v1/login/email/", json={"email": email, "password": "correct-horse-battery-staple"}
    )
    return response.json()["access_token"]


async def _request_otp_and_get_raw_code(app, session, user_id: str, otp_type: str) -> str:
    """Tests don't have a real email/SMS backend to intercept — pull the raw code directly from
    otp_service.generate_otp instead of going through the (log-only) delivery path."""
    from tenxyte.adapters.fastapi import otp_service

    _row, raw_code = await otp_service.generate_otp(session, user_id, otp_type, app.state.tenxyte_settings)
    return raw_code


@pytest.mark.anyio
async def test_otp_request_email_success():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="otpreq@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "otpreq@example.com")
            response = await client.post(
                "/api/v1/otp/request/",
                json={"otp_type": "email"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "OTP sent"
    assert body["channel"] == "email"
    assert body["masked_recipient"].endswith("@example.com")
    assert body["masked_recipient"] != "otpreq@example.com"


@pytest.mark.anyio
async def test_otp_request_phone_without_phone_on_account():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="nophone@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "nophone@example.com")
            response = await client.post(
                "/api/v1/otp/request/",
                json={"otp_type": "phone"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "NO_PHONE"


@pytest.mark.anyio
async def test_otp_request_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/otp/request/", json={"otp_type": "email"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_verify_email_otp_success_marks_verified():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="verifyme@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            raw_code = await _request_otp_and_get_raw_code(app, session, user.id, "email_verification")

        async with await _client(app) as client:
            access_token = await _login(client, "verifyme@example.com")
            response = await client.post(
                "/api/v1/otp/verify/email/",
                json={"code": raw_code},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["email_verified"] is True

            me_response = await client.get("/api/v1/me/", headers={"Authorization": f"Bearer {access_token}"})

    assert me_response.json()["is_email_verified"] is True


@pytest.mark.anyio
async def test_verify_email_otp_wrong_code_reports_remaining_attempts():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="wrongcode@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            await _request_otp_and_get_raw_code(app, session, user.id, "email_verification")

        async with await _client(app) as client:
            access_token = await _login(client, "wrongcode@example.com")
            response = await client.post(
                "/api/v1/otp/verify/email/",
                json={"code": "000000"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "OTP_VERIFICATION_FAILED"
    assert "attempt(s) remaining" in body["error"]


@pytest.mark.anyio
async def test_verify_email_otp_no_code_requested_yet():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="nocodeyet@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "nocodeyet@example.com")
            response = await client.post(
                "/api/v1/otp/verify/email/",
                json={"code": "123456"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "OTP_VERIFICATION_FAILED"
    assert body["error"] == "No verification code found"


@pytest.mark.anyio
async def test_verify_email_otp_exhausts_attempts_then_locked():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="exhaust@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            await _request_otp_and_get_raw_code(app, session, user.id, "email_verification")

        async with await _client(app) as client:
            access_token = await _login(client, "exhaust@example.com")
            headers = {"Authorization": f"Bearer {access_token}"}

            # max_attempts=3 — three wrong guesses burns the code entirely.
            for _ in range(3):
                r = await client.post("/api/v1/otp/verify/email/", json={"code": "000000"}, headers=headers)
                assert r.status_code == 400

            locked_response = await client.post("/api/v1/otp/verify/email/", json={"code": "000000"}, headers=headers)

    assert locked_response.status_code == 400
    assert locked_response.json()["error"] == "Code expired or too many attempts. Please request a new code."


@pytest.mark.anyio
async def test_verify_phone_otp_success_marks_verified_and_returns_full_number():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(
            app, email="phoneverify@example.com", phone_country_code="33", phone_number="612345678"
        )
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            raw_code = await _request_otp_and_get_raw_code(app, session, user.id, "phone_verification")

        async with await _client(app) as client:
            access_token = await _login(client, "phoneverify@example.com")
            response = await client.post(
                "/api/v1/otp/verify/phone/",
                json={"code": raw_code},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["phone_verified"] is True
    assert body["phone_number"] == "+33612345678"
