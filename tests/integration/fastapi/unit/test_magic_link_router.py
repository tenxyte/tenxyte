"""
Tests for the Wave C magic-link (passwordless email) router (spec z_aud_3, task 7.1) —
magic-link/request, magic-link/verify — against a real app, a real ephemeral aiosqlite database,
and real signed tokens (no mocks).
"""

import uuid

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import UserDB
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
            return "test-secret-key-for-magic-link-router-tests"
        return super().get(name, default)


class _ForcedPasswordChangeProvider(EnvSettingsProvider):
    """Feature: force_password_change_on_first_login, enabled — for the gating test below."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-magic-link-forced-tests"
        if name == "TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED":
            return True
        return super().get(name, default)


def _build_app(provider=None):
    settings = Settings(provider=provider or _TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email: str, is_active: bool = True) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(id=str(uuid.uuid4()), email=email, password_hash=password_hash, is_active=is_active)
        )


async def _request_and_get_raw_token(app, client, email: str) -> str:
    """Tests don't have a real email backend to intercept — go through the real HTTP endpoint
    (exactly as a caller would) but capture the URL the (console-logging) `ConsoleEmailService`
    would have sent, and pull the raw token out of its query string. No private/internal API
    used — only what `magic-link/request/` itself already does."""
    from urllib.parse import parse_qs, urlparse

    from tenxyte.core.email_service import ConsoleEmailService, EmailService

    captured: dict = {}
    original_send_async = ConsoleEmailService.send_magic_link_async

    async def _capturing_send_async(self, to_email, magic_link_url, expires_in_minutes=15, from_email=None):
        captured["url"] = magic_link_url
        return await original_send_async(self, to_email, magic_link_url, expires_in_minutes, from_email)

    ConsoleEmailService.send_magic_link_async = _capturing_send_async
    try:
        response = await client.post(
            "/api/v1/magic-link/request/", json={"email": email, "validation_url": "https://a.example/verify"}
        )
        assert response.status_code == 200
    finally:
        ConsoleEmailService.send_magic_link_async = EmailService.send_magic_link_async

    query = parse_qs(urlparse(captured["url"]).query)
    return query["token"][0]


@pytest.mark.anyio
async def test_request_missing_email():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/magic-link/request/", json={"validation_url": "https://a.example/v"})
    assert response.status_code == 400
    assert response.json()["code"] == "EMAIL_REQUIRED"


@pytest.mark.anyio
async def test_request_missing_validation_url():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/magic-link/request/", json={"email": "a@example.com"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_URL_REQUIRED"


@pytest.mark.anyio
async def test_request_success_for_known_account():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="known@example.com")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/magic-link/request/",
                json={"email": "known@example.com", "validation_url": "https://a.example/verify"},
            )
    assert response.status_code == 200
    assert response.json() == {"message": "If this email is registered, a magic link has been sent."}


@pytest.mark.anyio
async def test_request_anti_enumeration_unknown_account_same_shape():
    """Property 3 (spec z_aud_3): identical response shape/status whether the account exists or
    not — no code is generated or sent for an unknown email."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="known2@example.com")
        async with await _client(app) as client:
            known_response = await client.post(
                "/api/v1/magic-link/request/",
                json={"email": "known2@example.com", "validation_url": "https://a.example/verify"},
            )
            unknown_response = await client.post(
                "/api/v1/magic-link/request/",
                json={"email": "unknown@example.com", "validation_url": "https://a.example/verify"},
            )
    assert known_response.status_code == unknown_response.status_code == 200
    assert known_response.json() == unknown_response.json()


@pytest.mark.anyio
async def test_request_inactive_account_same_shape_as_unknown():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="inactive@example.com", is_active=False)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/magic-link/request/",
                json={"email": "inactive@example.com", "validation_url": "https://a.example/verify"},
            )
    assert response.status_code == 200
    assert response.json() == {"message": "If this email is registered, a magic link has been sent."}


@pytest.mark.anyio
async def test_verify_missing_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/magic-link/verify/")
    assert response.status_code == 400
    assert response.json()["code"] == "TOKEN_REQUIRED"


@pytest.mark.anyio
async def test_verify_invalid_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/magic-link/verify/", params={"token": "does-not-exist"})
    assert response.status_code == 401
    assert response.json()["code"] == "MAGIC_LINK_INVALID"


@pytest.mark.anyio
async def test_verify_success_issues_tokens_and_is_single_use():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="verifyme@example.com")
        async with await _client(app) as client:
            raw_token = await _request_and_get_raw_token(app, client, "verifyme@example.com")

            first = await client.get("/api/v1/magic-link/verify/", params={"token": raw_token})
            assert first.status_code == 200
            body = first.json()
            assert body["access"]
            assert body["refresh"]
            assert body["user"]["email"] == "verifyme@example.com"
            assert body["message"] == "Magic link verified successfully"
            assert first.headers["Referrer-Policy"] == "no-referrer"

            # Single-use: the same token can't be verified twice.
            second = await client.get("/api/v1/magic-link/verify/", params={"token": raw_token})

    assert second.status_code == 401
    assert second.json()["code"] == "MAGIC_LINK_INVALID"


@pytest.mark.anyio
async def test_verify_issued_refresh_token_can_be_redeemed():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="refreshme@example.com")
        async with await _client(app) as client:
            raw_token = await _request_and_get_raw_token(app, client, "refreshme@example.com")
            verify_response = await client.get("/api/v1/magic-link/verify/", params={"token": raw_token})
            refresh_token = verify_response.json()["refresh"]

            refresh_response = await client.post("/api/v1/refresh/", json={"refresh_token": refresh_token})

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]


@pytest.mark.anyio
async def test_verify_forced_account_gets_restricted_token():
    """Feature: force_password_change_on_first_login — magic-link login previously bypassed this
    entirely (no gating call anywhere on this path); an account provisioned with
    must_change_password=True must now get the same restricted password_change_only token a
    forced-change email/phone login gets."""
    app = _build_app(provider=_ForcedPasswordChangeProvider())
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="forced-magic@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            db_user = await session.get(UserDB, user.id)
            db_user.must_change_password = True
            await session.commit()

        async with await _client(app) as client:
            raw_token = await _request_and_get_raw_token(app, client, "forced-magic@example.com")
            verify_resp = await client.get("/api/v1/magic-link/verify/", params={"token": raw_token})

    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["access"]
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True
