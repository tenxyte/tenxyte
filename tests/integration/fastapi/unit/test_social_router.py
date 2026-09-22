"""
Tests for the Wave G Social Auth router (spec z_aud_3, Wave G chunk 2/4, task 12.1) — against a
real app, a real ephemeral aiosqlite database, real signed tokens, and a real (if fake) OAuth2
provider server (`_fake_oauth_server.py`) reached via `httpx.ASGITransport` — no mocks anywhere,
including no mocked HTTP or crypto.
"""

import uuid

import bcrypt
import pytest
from _fake_oauth_server import FakeOAuthServer
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi import social_auth_service
from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

_APPLE_PRIVATE_KEY_PEM = (
    ec.generate_private_key(ec.SECP256R1())
    .private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    .decode()
)


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _SocialAuthProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-social-router-tests"
        if name == "TENXYTE_GOOGLE_CLIENT_ID":
            return "google-test-client-id"
        if name == "TENXYTE_APPLE_CLIENT_ID":
            return "apple-test-client-id"
        if name == "TENXYTE_APPLE_TEAM_ID":
            return "APPLETEAM1"
        if name == "TENXYTE_APPLE_KEY_ID":
            return "APPLEKEY123"
        if name == "TENXYTE_APPLE_PRIVATE_KEY":
            return _APPLE_PRIVATE_KEY_PEM
        return super().get(name, default)


class _ForcedPasswordChangeProvider(_SocialAuthProvider):
    """Feature: force_password_change_on_first_login, enabled, plus auto-merge so a social login
    with a verified email can link to an existing (pre-provisioned) account for the gating test
    below."""

    def get(self, name, default=None):
        if name == "TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED":
            return True
        if name == "TENXYTE_SOCIAL_AUTO_MERGE_ACCOUNTS":
            return True
        return super().get(name, default)


def _build_app(provider=None):
    settings = Settings(provider=provider or _SocialAuthProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email) -> str:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        created = await repo.create(
            User(id=str(uuid.uuid4()), email=email, password_hash=password_hash, is_active=True)
        )
    return created.id


@pytest.fixture
def fake_provider():
    server = FakeOAuthServer()
    social_auth_service._test_transport = ASGITransport(app=server.app)
    try:
        yield server
    finally:
        social_auth_service._test_transport = None


@pytest.mark.anyio
async def test_provider_not_supported():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/linkedin/", json={"access_token": "x"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "PROVIDER_NOT_SUPPORTED"
    assert body["supported_providers"] == ["google", "github", "microsoft", "facebook", "apple"]


@pytest.mark.anyio
async def test_missing_credentials():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/google/", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "MISSING_CREDENTIALS"


@pytest.mark.anyio
async def test_code_without_redirect_uri():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/google/", json={"code": "abc"})
    assert response.status_code == 400
    assert response.json()["code"] == "REDIRECT_URI_REQUIRED"


@pytest.mark.anyio
async def test_google_access_token_flow_creates_new_user(fake_provider):
    fake_provider.userinfo_responses["google"] = {
        "sub": "google-user-1",
        "email": "newuser@example.com",
        "email_verified": True,
        "given_name": "Ada",
        "family_name": "Lovelace",
        "picture": "https://example.com/ada.png",
    }
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/google/", json={"access_token": "fake-token"})
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "google"
        assert body["message"] == "Authentication successful"
        assert "device_summary" not in body
        assert body["is_new_user"] is True
        assert body["user"]["email"] == "newuser@example.com"
        assert body["user"]["first_name"] == "Ada"
        assert body["user"]["is_email_verified"] is True
        assert isinstance(body["access_token"], str)
        assert isinstance(body["refresh_token"], str)

        refresh = await client.post("/api/v1/refresh/", json={"refresh_token": body["refresh_token"]})
        assert refresh.status_code == 200


@pytest.mark.anyio
async def test_github_access_token_flow_with_email_fallback(fake_provider):
    fake_provider.userinfo_responses["github"] = {"id": 4242, "name": "Grace Hopper", "avatar_url": "https://x/g.png"}
    fake_provider.github_emails_response = [
        {"email": "secondary@example.com", "primary": False, "verified": True},
        {"email": "grace@example.com", "primary": True, "verified": True},
    ]
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/github/", json={"access_token": "gh-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "grace@example.com"
    assert body["user"]["first_name"] == "Grace"
    assert body["user"]["last_name"] == "Hopper"
    assert body["is_new_user"] is True


@pytest.mark.anyio
async def test_google_id_token_flow_via_real_jwks(fake_provider):
    id_token = fake_provider.sign_id_token(
        {
            "sub": "google-user-2",
            "email": "idtoken@example.com",
            "email_verified": True,
            "given_name": "Alan",
            "family_name": "Turing",
            "iss": "https://accounts.google.com",
            "aud": "google-test-client-id",
        }
    )
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/google/", json={"id_token": id_token})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "idtoken@example.com"
    assert body["user"]["first_name"] == "Alan"


@pytest.mark.anyio
async def test_apple_code_exchange_merges_first_auth_payload(fake_provider):
    apple_id_token = fake_provider.sign_id_token(
        {
            "sub": "apple-user-1",
            "email": "appleuser@example.com",
            "email_verified": "true",  # Apple sometimes sends this as a string, not a bool
            "iss": "https://appleid.apple.com",
            "aud": "apple-test-client-id",
        }
    )
    fake_provider.token_responses["apple"] = {"access_token": "unused", "id_token": apple_id_token}

    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/social/apple/",
            json={
                "code": "apple-auth-code",
                "redirect_uri": "https://app.example.com/callback",
                "user": {"name": {"firstName": "Grace", "lastName": "Hopper"}},
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "appleuser@example.com"
    assert body["user"]["first_name"] == "Grace"
    assert body["user"]["last_name"] == "Hopper"

    # Apple's client_secret is a real signed ES256 JWT this port generated -- verify the fake
    # server actually received one, not a placeholder.
    apple_request = next(r for r in fake_provider.received_requests if r["provider"] == "apple")
    assert apple_request["data"]["client_secret"].count(".") == 2


@pytest.mark.anyio
async def test_existing_social_connection_reuses_user_and_is_not_new(fake_provider):
    fake_provider.userinfo_responses["google"] = {
        "sub": "google-repeat-user",
        "email": "repeat@example.com",
        "email_verified": True,
    }
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        first = await client.post("/api/v1/social/google/", json={"access_token": "t1"})
        second = await client.post("/api/v1/social/google/", json={"access_token": "t2"})
    assert first.json()["is_new_user"] is True
    assert second.json()["is_new_user"] is False
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


@pytest.mark.anyio
async def test_unverified_email_refuses_fusion(fake_provider):
    fake_provider.userinfo_responses["google"] = {
        "sub": "google-unverified",
        "email": "unverified@example.com",
        "email_verified": False,
    }
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/social/google/", json={"access_token": "t"})
    assert response.status_code == 401
    assert response.json()["code"] == "SOCIAL_AUTH_FAILED"
    assert "not verified" in response.json()["error"]


@pytest.mark.anyio
async def test_verified_email_refuses_fusion_without_auto_merge(fake_provider):
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="existing@example.com")
        fake_provider.userinfo_responses["google"] = {
            "sub": "google-fusion-attempt",
            "email": "existing@example.com",
            "email_verified": True,
        }
        async with await _client(app) as client:
            response = await client.post("/api/v1/social/google/", json={"access_token": "t"})
    assert response.status_code == 401
    assert response.json()["code"] == "SOCIAL_AUTH_FAILED"
    assert "already exists" in response.json()["error"]


@pytest.mark.anyio
async def test_callback_endpoint_keeps_device_summary_and_has_no_message(fake_provider):
    fake_provider.token_responses["google"] = {"access_token": "exchanged-token"}
    fake_provider.userinfo_responses["google"] = {
        "sub": "google-callback-user",
        "email": "callback@example.com",
        "email_verified": True,
    }
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get(
            "/api/v1/social/google/callback/",
            params={"code": "cb-code", "redirect_uri": "https://app.example.com/cb"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "device_summary" in body
    assert "message" not in body
    assert body["provider"] == "google"


@pytest.mark.anyio
async def test_forced_account_gets_restricted_token_via_social_fusion(fake_provider):
    """Feature: force_password_change_on_first_login — social login previously bypassed this
    entirely (no gating call anywhere on this path); an account provisioned with
    must_change_password=True (e.g. to force setting a real password after a social signup, so the
    user isn't locked to that provider) must get the same restricted password_change_only token a
    forced-change email/phone login gets, even when reached by linking to an existing account via
    verified-email fusion."""
    app = _build_app(provider=_ForcedPasswordChangeProvider())
    async with app.router.lifespan_context(app):
        user_id = await _create_user(app, email="forced-social@example.com")
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            from tenxyte.adapters.fastapi.models_sa import UserDB

            db_user = await session.get(UserDB, user_id)
            db_user.must_change_password = True
            await session.commit()

        fake_provider.userinfo_responses["google"] = {
            "sub": "google-forced-user",
            "email": "forced-social@example.com",
            "email_verified": True,
        }
        async with await _client(app) as client:
            response = await client.post("/api/v1/social/google/", json={"access_token": "t"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True
