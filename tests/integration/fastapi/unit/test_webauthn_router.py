"""
Tests for the Wave G WebAuthn/Passkeys router (spec z_aud_3, task 12.1) — against a real app, a
real ephemeral aiosqlite database, real signed tokens, and a real (if synthetic) FIDO2
authenticator (`_webauthn_authenticator.py`) — no mocks anywhere, including no mocked crypto.
"""

import json
import uuid

import pytest
from _webauthn_authenticator import VirtualAuthenticator
from httpx import ASGITransport, AsyncClient
from webauthn.helpers import base64url_to_bytes

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

RP_ID = "localhost"
ORIGIN = "http://localhost"


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _WebAuthnEnabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-webauthn-router-tests"
        if name == "TENXYTE_WEBAUTHN_ENABLED":
            return True
        return super().get(name, default)


class _WebAuthnDisabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-webauthn-router-tests"
        return super().get(name, default)


def _build_app(*, webauthn_enabled: bool = True):
    provider = _WebAuthnEnabledProvider() if webauthn_enabled else _WebAuthnDisabledProvider()
    settings = Settings(provider=provider)
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email=None) -> tuple[str, dict]:
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
            )
        )
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=created.id, application_id="default"
    ).access_token
    return created.id, {"Authorization": f"Bearer {token}"}


def _extract_challenge(options_response: dict) -> bytes:
    options = json.loads(options_response["options"])
    return base64url_to_bytes(options["challenge"])


async def _register_passkey(client, headers, authenticator: VirtualAuthenticator) -> dict:
    begin = await client.post("/api/v1/webauthn/register/begin/", headers=headers)
    assert begin.status_code == 200
    challenge = _extract_challenge(begin.json())

    credential = authenticator.registration_credential(challenge=challenge, rp_id=RP_ID, origin=ORIGIN)
    complete = await client.post(
        "/api/v1/webauthn/register/complete/",
        json={"credential": credential, "device_name": "Test Key", "challenge_id": begin.json()["challenge_id"]},
        headers=headers,
    )
    return complete


@pytest.mark.anyio
async def test_webauthn_disabled_by_default_rejects_begin():
    """`webauthn_enabled` defaults False (fixed from a stale True default this chunk — see
    core/settings.py) — matching Django's own conf default exactly."""
    app = _build_app(webauthn_enabled=False)
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.post("/api/v1/webauthn/register/begin/", headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "WebAuthn is not enabled", "code": "WEBAUTHN_ERROR"}


@pytest.mark.anyio
async def test_register_begin_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/webauthn/register/begin/")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_full_register_and_authenticate_roundtrip():
    """Real end-to-end: register a passkey with a genuine (synthetic) authenticator, then use it
    to authenticate and receive a real, working access/refresh token pair."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        user_id, headers = await _create_user(app, email="passkey-user@example.com")
        authenticator = VirtualAuthenticator()
        async with await _client(app) as client:
            register = await _register_passkey(client, headers, authenticator)
            assert register.status_code == 200
            body = register.json()
            assert body["message"] == "Passkey registered successfully"
            assert body["credential"]["device_name"] == "Test Key"
            assert body["credential"]["created_at"] is not None

            listing = await client.get("/api/v1/webauthn/credentials/", headers=headers)
            assert listing.status_code == 200
            assert listing.json()["count"] == 1
            assert listing.json()["credentials"][0]["device_name"] == "Test Key"

            auth_begin = await client.post(
                "/api/v1/webauthn/authenticate/begin/", json={"email": "passkey-user@example.com"}
            )
            assert auth_begin.status_code == 200
            auth_challenge = _extract_challenge(auth_begin.json())

            auth_credential = authenticator.authentication_credential(
                challenge=auth_challenge, rp_id=RP_ID, origin=ORIGIN
            )
            auth_complete = await client.post(
                "/api/v1/webauthn/authenticate/complete/",
                json={
                    "credential": auth_credential,
                    "challenge_id": auth_begin.json()["challenge_id"],
                },
            )
            assert auth_complete.status_code == 200
            auth_body = auth_complete.json()
            # Real Django bug fixed, not replicated (see webauthn_service.py's module docstring):
            # "access" here must be a plain JWT string, not a [token, jti, iso-datetime] array.
            assert isinstance(auth_body["access"], str)
            assert auth_body["access"].count(".") == 2  # a real JWT has 3 dot-separated segments
            assert isinstance(auth_body["refresh"], str)
            assert auth_body["user"]["id"] == user_id
            assert auth_body["message"] == "Authentication successful"
            assert auth_body["credential_used"] == auth_credential["id"]

            # The refresh token must actually work, unlike Django's never-persisted one.
            refresh = await client.post("/api/v1/refresh/", json={"refresh_token": auth_body["refresh"]})
            assert refresh.status_code == 200


@pytest.mark.anyio
async def test_authenticate_with_unknown_credential_fails():
    app = _build_app()
    async with app.router.lifespan_context(app):
        stranger = VirtualAuthenticator()
        async with await _client(app) as client:
            begin = await client.post("/api/v1/webauthn/authenticate/begin/", json={})
            challenge = _extract_challenge(begin.json())
            credential = stranger.authentication_credential(challenge=challenge, rp_id=RP_ID, origin=ORIGIN)
            response = await client.post(
                "/api/v1/webauthn/authenticate/complete/",
                json={"credential": credential, "challenge_id": begin.json()["challenge_id"]},
            )
    assert response.status_code == 401
    assert response.json() == {"error": "Unknown credential", "code": "WEBAUTHN_AUTH_FAILED"}


@pytest.mark.anyio
async def test_register_complete_missing_credential_field():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.post("/api/v1/webauthn/register/complete/", json={}, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "credential is required", "code": "MISSING_FIELDS"}


@pytest.mark.anyio
async def test_register_complete_rejects_mismatched_challenge_user():
    """A challenge issued to user A cannot be completed for user B."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers_a = await _create_user(app)
        _, headers_b = await _create_user(app)
        authenticator = VirtualAuthenticator()
        async with await _client(app) as client:
            begin = await client.post("/api/v1/webauthn/register/begin/", headers=headers_a)
            challenge = _extract_challenge(begin.json())
            credential = authenticator.registration_credential(challenge=challenge, rp_id=RP_ID, origin=ORIGIN)

            response = await client.post(
                "/api/v1/webauthn/register/complete/",
                json={"credential": credential, "challenge_id": begin.json()["challenge_id"]},
                headers=headers_b,
            )
    assert response.status_code == 400
    assert response.json() == {"error": "Challenge does not match user", "code": "REGISTRATION_FAILED"}


@pytest.mark.anyio
async def test_delete_credential_scoped_to_owner():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers_a = await _create_user(app)
        _, headers_b = await _create_user(app)
        authenticator = VirtualAuthenticator()
        async with await _client(app) as client:
            register = await _register_passkey(client, headers_a, authenticator)
            credential_id = register.json()["credential"]["id"]

            stolen = await client.delete(f"/api/v1/webauthn/credentials/{credential_id}/", headers=headers_b)
            assert stolen.status_code == 404
            assert stolen.json() == {"error": "Credential not found", "code": "CREDENTIAL_NOT_FOUND"}

            owned = await client.delete(f"/api/v1/webauthn/credentials/{credential_id}/", headers=headers_a)
            assert owned.status_code == 204

            listing = await client.get("/api/v1/webauthn/credentials/", headers=headers_a)
            assert listing.json()["count"] == 0


@pytest.mark.anyio
async def test_credentials_list_and_delete_work_even_when_webauthn_disabled():
    """Real Django finding (see webauthn_service.py's module docstring): list/delete have no
    webauthn_enabled gate at all, unlike register/authenticate."""
    app = _build_app(webauthn_enabled=False)
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            listing = await client.get("/api/v1/webauthn/credentials/", headers=headers)
            assert listing.status_code == 200
            assert listing.json() == {"credentials": [], "count": 0}

            delete = await client.delete(f"/api/v1/webauthn/credentials/{uuid.uuid4()}/", headers=headers)
            assert delete.status_code == 404
