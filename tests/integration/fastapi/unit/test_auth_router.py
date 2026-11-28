from tenxyte.core.auth_service import hash_password

"""
Tests for the Wave A auth router (spec z_aud_3, task 5.1) — register, login/email, refresh,
logout, logout/all, me (GET/PATCH), me/roles — against a real app, a real ephemeral aiosqlite
database, and real signed tokens (no mocks).
"""

import uuid

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
    """Application auth disabled (this suite targets the auth router in isolation — application
    auth has its own dedicated suite) and a fixed JWT signing key."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-auth-router-tests"
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
    is_active: bool = True,
    is_superuser: bool = False,
    is_staff: bool = False,
    mfa_type: MFAType = MFAType.NONE,
    mfa_secret: str | None = None,
    phone_country_code: str | None = None,
    phone_number: str | None = None,
) -> User:
    session_factory = app.state.tenxyte_session_factory
    hashed = hash_password(password)
    metadata = {}
    if phone_country_code and phone_number:
        metadata = {"phone_country_code": phone_country_code, "phone_number": phone_number}
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=hashed,
                is_active=is_active,
                is_superuser=is_superuser,
                is_staff=is_staff,
                mfa_type=mfa_type,
                mfa_secret=mfa_secret,
                metadata=metadata,
            )
        )


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_success_without_login():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/register/",
            json={"email": "new@example.com", "password": "correct-horse-battery-staple"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Registration successful"
    assert body["user"]["email"] == "new@example.com"
    assert body["verification_required"] == {"email": True, "phone": False}
    assert "access_token" not in body


@pytest.mark.anyio
async def test_register_with_login_issues_tokens():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/register/",
            json={"email": "new2@example.com", "password": "correct-horse-battery-staple", "login": True},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "Bearer"


@pytest.mark.anyio
async def test_register_duplicate_email_is_anti_enumeration():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="taken@example.com")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/register/",
                json={"email": "taken@example.com", "password": "another-password-1"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Registration successful"
    assert body["user"]["email"] == "taken@example.com"
    assert body["verification_required"] == {"email": True, "phone": False}
    assert "access_token" not in body


@pytest.mark.anyio
async def test_register_validation_error_is_canonical():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/register/", json={"email": "bad-email", "password": "short"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_register_password_over_72_bytes_is_canonical_400_not_a_crash():
    """Regression: bcrypt.hashpw hard-fails past 72 bytes (not characters — a multi-byte-char
    password well under any character-count limit can still exceed this), which crashed the
    handler as an unhandled 500 before this was caught explicitly."""
    app = _build_app()
    long_password = "a" * 73
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/register/", json={"email": "longpw@example.com", "password": long_password}
        )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# login/email
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_success():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="alice@example.com", password="correct-horse-battery-staple")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "alice@example.com", "password": "correct-horse-battery-staple"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["requires_2fa"] is False
    assert body["must_change_password"] is False
    assert body["session_id"] is None
    assert body["device_id"] is None
    assert body["user"]["email"] == "alice@example.com"


@pytest.mark.anyio
async def test_login_unknown_and_wrong_password_are_anti_enumeration():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="bob@example.com", password="correct-horse-battery-staple")
        async with await _client(app) as client:
            unknown = await client.post(
                "/api/v1/login/email/", json={"email": "nobody@example.com", "password": "whatever12"}
            )
            wrong = await client.post(
                "/api/v1/login/email/", json={"email": "bob@example.com", "password": "wrong-password"}
            )

    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["error"] == wrong.json()["error"] == "Invalid email or password"
    assert unknown.json()["code"] == wrong.json()["code"] == "LOGIN_FAILED"


@pytest.mark.anyio
async def test_login_inactive_user():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="inactive@example.com", is_active=False)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "inactive@example.com", "password": "correct-horse-battery-staple"},
            )

    assert response.status_code == 401
    assert response.json() == {"error": "Account is inactive", "code": "LOGIN_FAILED"}


@pytest.mark.anyio
async def test_login_password_over_72_bytes_is_rejected_not_a_crash():
    """Regression: bcrypt.checkpw hard-fails past 72 bytes — an over-long password on an
    existing account must fail auth cleanly (401), not crash the handler."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="longpwlogin@example.com")
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "longpwlogin@example.com", "password": "a" * 73},
            )

    assert response.status_code == 401
    assert response.json()["code"] == "LOGIN_FAILED"


@pytest.mark.anyio
async def test_login_lockout_after_max_attempts():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="lockme@example.com", password="correct-horse-battery-staple")
        async with await _client(app) as client:
            settings = app.state.tenxyte_settings
            for _ in range(settings.max_login_attempts):
                r = await client.post("/api/v1/login/email/", json={"email": "lockme@example.com", "password": "wrong"})
                assert r.status_code == 401

            locked = await client.post(
                "/api/v1/login/email/",
                json={"email": "lockme@example.com", "password": "correct-horse-battery-staple"},
            )

    assert locked.status_code == 423
    body = locked.json()
    assert body["code"] == "ACCOUNT_LOCKED"
    assert body["retry_after"] == app.state.tenxyte_settings.lockout_duration


@pytest.mark.anyio
async def test_login_admin_without_mfa_gets_2fa_bootstrap_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="admin@example.com", is_superuser=True, mfa_type=MFAType.NONE)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["token_scope"] == "2fa_setup_only"
    assert body["requires_2fa_setup"] is True
    assert body["expires_in"] == 900
    assert "refresh_token" not in body
    assert "user" not in body


@pytest.mark.anyio
async def test_login_with_2fa_enabled_requires_code():
    app = _build_app()
    secret = pyotp.random_base32()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="has2fa@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "has2fa@example.com", "password": "correct-horse-battery-staple"},
            )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "2FA_REQUIRED"
    assert body["requires_2fa"] is True


@pytest.mark.anyio
async def test_login_with_2fa_valid_code_succeeds():
    app = _build_app()
    secret = pyotp.random_base32()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="has2fa2@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        async with await _client(app) as client:
            code = pyotp.TOTP(secret).now()
            response = await client.post(
                "/api/v1/login/email/",
                json={"email": "has2fa2@example.com", "password": "correct-horse-battery-staple", "totp_code": code},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["requires_2fa"] is True
    assert body["access_token"]


@pytest.mark.anyio
async def test_login_with_2fa_invalid_code_rejected():
    app = _build_app()
    secret = pyotp.random_base32()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="has2fa3@example.com", mfa_type=MFAType.TOTP, mfa_secret=secret)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/",
                json={
                    "email": "has2fa3@example.com",
                    "password": "correct-horse-battery-staple",
                    "totp_code": "000000",
                },
            )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_2FA_CODE"


# ---------------------------------------------------------------------------
# login/phone
# ---------------------------------------------------------------------------
# Registration itself is still email-only (see routers/auth.py's module docstring), and the
# Reference_Stack's UserDB.email is NOT NULL + unique (unlike Django, where email is nullable
# for a phone-only account) — so phone-login test users get a synthetic placeholder email,
# a Reference_Stack storage detail invisible to the login/phone contract itself.


@pytest.mark.anyio
async def test_login_phone_success():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(
            app,
            email=f"phone-user-{uuid.uuid4().hex}@example.invalid",
            phone_country_code="33",
            phone_number="612345678",
        )
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/phone/",
                json={
                    "phone_country_code": "33",
                    "phone_number": "612345678",
                    "password": "correct-horse-battery-staple",
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["requires_2fa"] is False


@pytest.mark.anyio
async def test_login_phone_unknown_and_wrong_password_are_anti_enumeration():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(
            app,
            email=f"phone-user-{uuid.uuid4().hex}@example.invalid",
            phone_country_code="33",
            phone_number="612345679",
        )
        async with await _client(app) as client:
            unknown = await client.post(
                "/api/v1/login/phone/",
                json={"phone_country_code": "33", "phone_number": "699999999", "password": "whatever12"},
            )
            wrong = await client.post(
                "/api/v1/login/phone/",
                json={"phone_country_code": "33", "phone_number": "612345679", "password": "wrong-password"},
            )

    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["error"] == wrong.json()["error"] == "Invalid phone number or password"
    assert unknown.json()["code"] == wrong.json()["code"] == "LOGIN_FAILED"


@pytest.mark.anyio
async def test_login_phone_and_email_response_shapes_are_identical():
    """Parity: Django's own snapshot tests assert /login/email/ and /login/phone/ return the
    same key set — this Reference_Stack port should hold the same invariant."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="cross-email@example.com")
        await _create_user(
            app,
            email=f"phone-user-{uuid.uuid4().hex}@example.invalid",
            phone_country_code="33",
            phone_number="612345680",
        )
        async with await _client(app) as client:
            email_response = await client.post(
                "/api/v1/login/email/",
                json={"email": "cross-email@example.com", "password": "correct-horse-battery-staple"},
            )
            phone_response = await client.post(
                "/api/v1/login/phone/",
                json={
                    "phone_country_code": "33",
                    "phone_number": "612345680",
                    "password": "correct-horse-battery-staple",
                },
            )

    assert email_response.status_code == phone_response.status_code == 200
    assert set(email_response.json().keys()) == set(phone_response.json().keys())


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_refresh_success_rotates_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="refresh@example.com")
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/",
                json={"email": "refresh@example.com", "password": "correct-horse-battery-staple"},
            )
            old_refresh = login.json()["refresh_token"]

            response = await client.post("/api/v1/refresh/", json={"refresh_token": old_refresh})
            assert response.status_code == 200
            new_refresh = response.json()["refresh_token"]
            assert new_refresh != old_refresh

            reused = await client.post("/api/v1/refresh/", json={"refresh_token": old_refresh})

    assert reused.status_code == 401
    assert reused.json()["code"] == "REFRESH_FAILED"


@pytest.mark.anyio
async def test_refresh_missing_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/refresh/", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "MISSING_REFRESH_TOKEN"


@pytest.mark.anyio
async def test_refresh_unknown_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/refresh/", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["code"] == "REFRESH_FAILED"


# ---------------------------------------------------------------------------
# logout / logout/all
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_logout_success_and_refresh_is_revoked():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="logout@example.com")
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/",
                json={"email": "logout@example.com", "password": "correct-horse-battery-staple"},
            )
            refresh_token = login.json()["refresh_token"]

            response = await client.post("/api/v1/logout/", json={"refresh_token": refresh_token})
            assert response.status_code == 200
            assert response.json() == {"message": "Logged out successfully"}

            reused = await client.post("/api/v1/refresh/", json={"refresh_token": refresh_token})

    assert reused.status_code == 401


@pytest.mark.anyio
async def test_logout_missing_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/logout/", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "MISSING_REFRESH_TOKEN"


@pytest.mark.anyio
async def test_logout_succeeds_with_only_access_token_no_refresh_token():
    """A client holding only an access token (no refresh token at all -- e.g. the
    2fa_setup_only bootstrap token issued to an admin with no 2FA configured yet, which never
    issues a refresh token) must still be able to log out by blacklisting that access token
    alone -- parity with the Django_Adapter's LogoutView fix. Previously this always 400'd,
    since refresh_token was unconditionally required regardless of an access token being
    present."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="bootstrap-logout@example.com")
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/",
                json={"email": "bootstrap-logout@example.com", "password": "correct-horse-battery-staple"},
            )
            access_token = login.json()["access_token"]

            response = await client.post(
                "/api/v1/logout/", json={}, headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200

            me = await client.get("/api/v1/me/", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 401


@pytest.mark.anyio
async def test_logout_all_revokes_every_session():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="logoutall@example.com")
        async with await _client(app) as client:
            login1 = await client.post(
                "/api/v1/login/email/",
                json={"email": "logoutall@example.com", "password": "correct-horse-battery-staple"},
            )
            login2 = await client.post(
                "/api/v1/login/email/",
                json={"email": "logoutall@example.com", "password": "correct-horse-battery-staple"},
            )
            access_token = login1.json()["access_token"]
            refresh1 = login1.json()["refresh_token"]
            refresh2 = login2.json()["refresh_token"]

            response = await client.post("/api/v1/logout/all/", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 200
            assert response.json() == {"message": "Logged out from 2 devices"}

            reuse1 = await client.post("/api/v1/refresh/", json={"refresh_token": refresh1})
            reuse2 = await client.post("/api/v1/refresh/", json={"refresh_token": refresh2})

    assert reuse1.status_code == 401
    assert reuse2.status_code == 401


@pytest.mark.anyio
async def test_logout_all_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post("/api/v1/logout/all/")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


# ---------------------------------------------------------------------------
# me / me/roles
# ---------------------------------------------------------------------------


async def _login(client, email, password="correct-horse-battery-staple"):
    response = await client.post("/api/v1/login/email/", json={"email": email, "password": password})
    return response.json()["access_token"]


@pytest.mark.anyio
async def test_get_me():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="me@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "me@example.com")
            response = await client.get("/api/v1/me/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.anyio
async def test_patch_me_resets_email_verified_on_email_change():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="patchme@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "patchme@example.com")
            response = await client.patch(
                "/api/v1/me/",
                json={"email": "new-email@example.com", "first_name": "Ada"},
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Profile updated successfully"
    assert set(body["updated_fields"]) == {"email", "first_name"}
    assert body["user"]["email"] == "new-email@example.com"
    assert body["user"]["first_name"] == "Ada"
    assert body["user"]["is_email_verified"] is False
    assert body["verification_required"]["email_changed"] is True


@pytest.mark.anyio
async def test_my_roles_returns_empty_lists_for_full_scope_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="roles@example.com")
        async with await _client(app) as client:
            access_token = await _login(client, "roles@example.com")
            response = await client.get("/api/v1/me/roles/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json() == {"roles": [], "permissions": []}


@pytest.mark.anyio
async def test_my_roles_rejects_restricted_scope_token_but_me_accepts_it():
    """Parity trap: Django's MyRolesView uses bare @require_jwt (scope-enforced), while MeView
    uses plain IsAuthenticated (no scope enforcement at all). A 2fa_setup_only bootstrap token
    must be rejected by me/roles/ but accepted by me/."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="bootstrap-admin@example.com", is_superuser=True, mfa_type=MFAType.NONE)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/",
                json={"email": "bootstrap-admin@example.com", "password": "correct-horse-battery-staple"},
            )
            bootstrap_token = login.json()["access_token"]
            assert login.json()["token_scope"] == "2fa_setup_only"

            roles_response = await client.get(
                "/api/v1/me/roles/", headers={"Authorization": f"Bearer {bootstrap_token}"}
            )
            me_response = await client.get("/api/v1/me/", headers={"Authorization": f"Bearer {bootstrap_token}"})

    assert roles_response.status_code == 403
    assert roles_response.json()["code"] == "INSUFFICIENT_SCOPE"
    assert me_response.status_code == 200
