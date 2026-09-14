"""
Tests for the Wave B password router (spec z_aud_3, task 6.1) — password/strength,
password/requirements, password/change — against a real app, a real ephemeral aiosqlite database,
and real signed tokens. No mocks except the one unavoidable third-party network boundary (the
HIBP breach-check HTTP call), never the adapter's own logic.
"""

import uuid
from unittest.mock import patch

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
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
            return "test-secret-key-for-password-router-tests"
        if name == "TENXYTE_BREACH_CHECK_ENABLED":
            return False  # no real network calls in tests by default
        return super().get(name, default)


class _BreachCheckEnabledProvider(_TestProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_BREACH_CHECK_ENABLED":
            return True
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(
    app, *, email: str, password: str = "correct-horse-battery-staple", password_hash: str | None = "SET"
) -> User:
    session_factory = app.state.tenxyte_session_factory
    if password_hash == "SET":
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(User(id=str(uuid.uuid4()), email=email, password_hash=password_hash, is_active=True))


async def _login(client, email: str, password: str = "correct-horse-battery-staple") -> str:
    response = await client.post("/api/v1/login/email/", json={"email": email, "password": password})
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# password/strength, password/requirements
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_password_strength_weak_password_is_invalid():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/password/strength/", json={"password": "abc"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["errors"]
    assert "requirements" in body
    assert isinstance(body["requirements"], list)


@pytest.mark.anyio
async def test_password_strength_strong_password_is_valid():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/password/strength/", json={"password": "Correct-Horse-Battery-Staple-1"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert body["score"] > 0
    assert body["strength"] in {"weak", "fair", "good", "strong", "excellent"}


@pytest.mark.anyio
async def test_password_strength_missing_password_defaults_empty_and_is_invalid():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/password/strength/", json={})

    assert response.status_code == 200
    assert response.json()["is_valid"] is False


@pytest.mark.anyio
async def test_password_requirements_no_auth_needed():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/password/requirements/")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["requirements"], list)
    assert isinstance(body["min_length"], int)
    assert isinstance(body["max_length"], int)


# ---------------------------------------------------------------------------
# password/change
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_change_password_success_revokes_sessions_and_new_password_works():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="change@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "change@example.com")

            response = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "correct-horse-battery-staple", "new_password": "New-Correct-Horse-1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["message"] == "Password changed successfully"
            assert body["password_strength"] in {"weak", "fair", "good", "strong", "excellent"}
            assert isinstance(body["sessions_revoked"], int)

            old_password_login = await client.post(
                "/api/v1/login/email/", json={"email": "change@example.com", "password": "correct-horse-battery-staple"}
            )
            new_password_login = await client.post(
                "/api/v1/login/email/", json={"email": "change@example.com", "password": "New-Correct-Horse-1"}
            )

    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200


@pytest.mark.anyio
async def test_change_password_wrong_current_password_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="wrongcurrent@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "wrongcurrent@example.com")
            response = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "not-the-right-password", "new_password": "New-Correct-Horse-1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PASSWORD"


@pytest.mark.anyio
async def test_change_password_missing_proof_requires_reauth():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="noproof@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "noproof@example.com")
            response = await client.post(
                "/api/v1/password/change/",
                json={"new_password": "New-Correct-Horse-1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "REAUTH_REQUIRED"


@pytest.mark.anyio
async def test_change_password_otp_only_is_reauth_required_not_implemented():
    """OTP-based reauth isn't implemented yet (no OTP storage in the Reference_Stack) — an
    otp_code-only request is treated the same as no proof at all, not silently accepted."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="otponly@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "otponly@example.com")
            response = await client.post(
                "/api/v1/password/change/",
                json={"otp_code": "123456", "new_password": "New-Correct-Horse-1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "REAUTH_REQUIRED"


@pytest.mark.anyio
async def test_change_password_passwordless_account_rejected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="passwordless@example.com", password_hash=None)
        async with await _client(app) as client:
            # No password to log in with — issue a token directly via the app's own jwt_service.
            jwt_service = app.state.tenxyte_jwt_service
            pair = jwt_service.generate_new_token_pair(user_id=user.id, application_id="default")
            response = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "anything", "new_password": "New-Correct-Horse-1"},
                headers={"Authorization": f"Bearer {pair.access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD"


@pytest.mark.anyio
async def test_change_password_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/password/change/", json={"current_password": "x", "new_password": "New-Correct-Horse-1"}
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_change_password_validation_error_is_canonical():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="shortnew@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "shortnew@example.com")
            response = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "correct-horse-battery-staple", "new_password": "short"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_change_password_breached_password_hard_rejected():
    """The one third-party network boundary in this router (HIBP) is mocked — everything else
    (auth, reauth, hashing, revocation) runs for real."""
    import hashlib

    new_password = "Breached-Password-1"
    sha1_hash = hashlib.sha1(new_password.encode("utf-8")).hexdigest().upper()
    suffix = sha1_hash[5:]

    settings = Settings(provider=_BreachCheckEnabledProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())

    async with app.router.lifespan_context(app):
        await _create_user(app, email="breached@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "breached@example.com")

            fake_response = type("FakeResponse", (), {"text": f"{suffix}:42", "raise_for_status": lambda self: None})()
            with patch("tenxyte.adapters.fastapi.breach_check.requests.get", return_value=fake_response):
                response = await client.post(
                    "/api/v1/password/change/",
                    json={"current_password": "correct-horse-battery-staple", "new_password": new_password},
                    headers={"Authorization": f"Bearer {access_token}"},
                )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "PASSWORD_BREACHED"
    assert "42" in body["error"]
