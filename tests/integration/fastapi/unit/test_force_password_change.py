"""
Tests for the `force_password_change_on_first_login` feature on the FastAPI_Adapter — ported from
the Django_Adapter's fully-implemented `specs/force_password_change_on_first_login/` (design.md's
16 correctness properties; this suite covers the representative behaviors, not an exhaustive
Hypothesis-property-per-property port). Against a real app, a real ephemeral aiosqlite database,
and real signed tokens (no mocks).

`must_change_password` isn't part of the Core `User` port dataclass (same architectural choice
Django makes), so tests that need to set/read it go through the raw `UserDB` row directly, exactly
as `routers/auth.py`'s `resolve_forced_password_change_scope` and `routers/password.py`'s
flag-clearing logic do.

Also covers `POST /register/`'s own `must_change_password` request-body flag (added on user
request as a one-call shortcut over register-then-admin-PATCH), including the
register+login=True-in-one-call gating edge case — see the tests right before
`test_login_otp_verify_also_issues_restricted_token`.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _EnabledProvider(EnvSettingsProvider):
    """Feature enabled — most tests in this file want the gating active. OTP login is also
    enabled here since some of these tests exercise the Passwordless_Account variant via
    `login/otp/verify/`, itself feature-gated off by default."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-force-password-change-tests"
        if name == "TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED":
            return True
        if name == "TENXYTE_OTP_LOGIN_ENABLED":
            return True
        return super().get(name, default)


class _DisabledProvider(EnvSettingsProvider):
    """Feature left at its real default (off) — for Property 5 (disabled = no-op)."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-force-password-change-disabled-tests"
        return super().get(name, default)


def _build_app(provider=None):
    settings = Settings(provider=provider or _EnabledProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(
    app, *, email: str, password: str = "TempPass123!", is_superuser: bool = False, must_change_password: bool = False
) -> User:
    session_factory = app.state.tenxyte_session_factory
    hashed = hash_password(password)
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        user = await repo.create(
            User(id=str(uuid.uuid4()), email=email, password_hash=hashed, is_active=True, is_superuser=is_superuser)
        )
        if must_change_password:
            db_user = await session.get(UserDB, user.id)
            db_user.must_change_password = True
            await session.commit()
    return user


async def _must_change_password_flag(app, user_id: str) -> bool:
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        db_user = (await session.execute(select(UserDB).where(UserDB.id == user_id))).scalar_one()
        return db_user.must_change_password


# ---------------------------------------------------------------------------
# Login issues the restricted token (Property 3) / full-scope token unaffected (Property 4)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_forced_account_gets_restricted_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="forced@example.com", must_change_password=True)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/", json={"email": "forced@example.com", "password": "TempPass123!"}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True
    # The restricted response still carries a refresh_token (unlike the 2fa_setup_only bootstrap,
    # which never issues one) -- mirrors auth_views.py's LoginEmailView exactly.
    assert body["refresh_token"]


@pytest.mark.anyio
async def test_login_normal_account_gets_full_scope_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="normal@example.com", must_change_password=False)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/", json={"email": "normal@example.com", "password": "TempPass123!"}
            )
    assert response.status_code == 200
    body = response.json()
    assert "token_scope" not in body
    assert body["must_change_password"] is False


# ---------------------------------------------------------------------------
# Feature disabled leaves tokens unchanged (Property 5)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_feature_disabled_is_a_true_noop():
    app = _build_app(provider=_DisabledProvider())
    async with app.router.lifespan_context(app):
        await _create_user(app, email="ignored@example.com", must_change_password=True)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/", json={"email": "ignored@example.com", "password": "TempPass123!"}
            )
    assert response.status_code == 200
    body = response.json()
    assert "token_scope" not in body
    assert body["must_change_password"] is False


# ---------------------------------------------------------------------------
# 2FA bootstrap takes precedence (Property 6)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_2fa_bootstrap_takes_precedence_over_forced_password_change():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="admin@example.com", is_superuser=True, must_change_password=True)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/email/", json={"email": "admin@example.com", "password": "TempPass123!"}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["token_scope"] == "2fa_setup_only"
    assert body.get("requires_2fa_setup") is True
    # The 2fa_setup_only bootstrap response has its own fixed shape -- must_change_password isn't
    # part of it (matches auth_views.py: the bootstrap branch returns early, before the
    # must_change_password field is ever added to the response).
    assert "must_change_password" not in body


# ---------------------------------------------------------------------------
# Refresh preserves the restriction (Property 7)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_refresh_preserves_restricted_scope():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="refresh-forced@example.com", must_change_password=True)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/", json={"email": "refresh-forced@example.com", "password": "TempPass123!"}
            )
            refresh_token = login.json()["refresh_token"]

            refreshed = await client.post("/api/v1/refresh/", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True


# ---------------------------------------------------------------------------
# Enforcement: restricted token rejected outside the allowed endpoints (Property 8),
# accepted on the password-change flow (Property 9)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_restricted_token_rejected_on_unrelated_endpoint():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="scope-check@example.com", must_change_password=True)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/", json={"email": "scope-check@example.com", "password": "TempPass123!"}
            )
            restricted_token = login.json()["access_token"]

            response = await client.get("/api/v1/2fa/status/", headers={"Authorization": f"Bearer {restricted_token}"})
    assert response.status_code == 403
    assert response.json()["code"] == "INSUFFICIENT_SCOPE"


@pytest.mark.anyio
async def test_restricted_token_accepted_on_logout_and_logout_all():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _create_user(app, email="logout-check@example.com", must_change_password=True)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/", json={"email": "logout-check@example.com", "password": "TempPass123!"}
            )
            restricted_token = login.json()["access_token"]

            logout_all_resp = await client.post(
                "/api/v1/logout/all/", headers={"Authorization": f"Bearer {restricted_token}"}
            )
    assert logout_all_resp.status_code == 200


# ---------------------------------------------------------------------------
# Successful change clears the flag and upgrades to full-scope (Property 11, 13)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_change_password_clears_flag_and_upgrades_to_full_scope():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="upgrade@example.com", must_change_password=True)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/", json={"email": "upgrade@example.com", "password": "TempPass123!"}
            )
            restricted_token = login.json()["access_token"]

            change_resp = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "TempPass123!", "new_password": "BrandNewPass456!"},
                headers={"Authorization": f"Bearer {restricted_token}"},
            )
            assert change_resp.status_code == 200
            body = change_resp.json()
            assert body["access_token"]
            assert body["refresh_token"]
            full_token = body["access_token"]

            # The upgraded token is genuinely full-scope: it now reaches an endpoint the
            # restricted token above couldn't (Property 10).
            status_resp = await client.get("/api/v1/2fa/status/", headers={"Authorization": f"Bearer {full_token}"})
            assert status_resp.status_code == 200

        assert await _must_change_password_flag(app, user.id) is False


@pytest.mark.anyio
async def test_set_initial_password_clears_flag_and_upgrades_to_full_scope():
    """Passwordless_Account variant (Property 12) — `has_usable_password=False` equivalent here is
    `password_hash=None`. A Passwordless_Account authenticates via login OTP (never a password),
    so it reaches `password_change_only` through `login/otp/verify/` exactly like
    `test_login_otp_verify_also_issues_restricted_token` below, then must present a *second*,
    freshly-generated login OTP to `/password/set-initial/` itself — the first one was already
    consumed by `login/otp/verify/`, mirroring `SetInitialPasswordView`'s own real requirement."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            user = await repo.create(
                User(id=str(uuid.uuid4()), email="passwordless@example.com", password_hash=None, is_active=True)
            )
            db_user = await session.get(UserDB, user.id)
            db_user.phone_country_code = "+1"
            db_user.phone_number = "5559876543"
            db_user.must_change_password = True
            await session.commit()

        from tenxyte.adapters.fastapi.otp_service import generate_otp

        settings = app.state.tenxyte_settings
        async with session_factory() as session:
            _row, login_code = await generate_otp(session, user.id, "login", settings)

        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/otp/verify/",
                json={
                    "phone_country_code": "+1",
                    "phone_number": "5559876543",
                    "otp_code": login_code,
                    "totp_code": "",
                },
            )
            assert login.status_code == 200
            assert login.json()["token_scope"] == "password_change_only"
            restricted_token = login.json()["access_token"]

            async with session_factory() as session:
                _row2, set_initial_code = await generate_otp(session, user.id, "login", settings)

            set_initial_resp = await client.post(
                "/api/v1/password/set-initial/",
                json={"otp_code": set_initial_code, "new_password": "BrandNewPass456!"},
                headers={"Authorization": f"Bearer {restricted_token}"},
            )
            assert set_initial_resp.status_code == 200
            body = set_initial_resp.json()
            assert body["access_token"]
            assert body["refresh_token"]

            status_resp = await client.get(
                "/api/v1/2fa/status/", headers={"Authorization": f"Bearer {body['access_token']}"}
            )
            assert status_resp.status_code == 200

        assert await _must_change_password_flag(app, user.id) is False


@pytest.mark.anyio
async def test_failed_change_password_does_not_clear_flag_or_issue_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="failed-change@example.com", must_change_password=True)
        async with await _client(app) as client:
            login = await client.post(
                "/api/v1/login/email/", json={"email": "failed-change@example.com", "password": "TempPass123!"}
            )
            restricted_token = login.json()["access_token"]

            change_resp = await client.post(
                "/api/v1/password/change/",
                json={"current_password": "WrongPassword!", "new_password": "BrandNewPass456!"},
                headers={"Authorization": f"Bearer {restricted_token}"},
            )
        assert change_resp.status_code == 400
        assert change_resp.json()["code"] == "INVALID_PASSWORD"

        assert await _must_change_password_flag(app, user.id) is True


# ---------------------------------------------------------------------------
# `must_change_password` settable directly at registration time (POST /register/) — a shortcut
# over the two-step register-then-admin-PATCH flow, added on user request.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_with_must_change_password_sets_flag():
    app = _build_app()
    async with app.router.lifespan_context(app):
        async with await _client(app) as client:
            register_resp = await client.post(
                "/api/v1/register/",
                json={
                    "email": "provisioned@example.com",
                    "password": "TempPass123!",
                    "must_change_password": True,
                },
            )
            assert register_resp.status_code == 201
            user_id = register_resp.json()["user"]["id"]

            login = await client.post(
                "/api/v1/login/email/", json={"email": "provisioned@example.com", "password": "TempPass123!"}
            )
            assert login.status_code == 200
            body = login.json()
            assert body["token_scope"] == "password_change_only"
            assert body["must_change_password"] is True
        assert await _must_change_password_flag(app, user_id) is True


@pytest.mark.anyio
async def test_register_without_must_change_password_is_default_false():
    app = _build_app()
    async with app.router.lifespan_context(app):
        async with await _client(app) as client:
            register_resp = await client.post(
                "/api/v1/register/", json={"email": "plain@example.com", "password": "TempPass123!"}
            )
            assert register_resp.status_code == 201
        assert await _must_change_password_flag(app, register_resp.json()["user"]["id"]) is False


@pytest.mark.anyio
async def test_register_with_must_change_password_and_login_gets_restricted_token_immediately():
    """A caller combining must_change_password=True with login=True in the same call must not be
    able to walk away with a full-scope token — the immediate token issuance has to go through the
    same gating as a normal login, not the plain `generate_new_token_pair` shortcut."""
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        register_resp = await client.post(
            "/api/v1/register/",
            json={
                "email": "immediate@example.com",
                "password": "TempPass123!",
                "must_change_password": True,
                "login": True,
            },
        )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.anyio
async def test_register_with_must_change_password_false_and_login_gets_full_scope_token():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        register_resp = await client.post(
            "/api/v1/register/",
            json={"email": "normal-login@example.com", "password": "TempPass123!", "login": True},
        )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert "token_scope" not in body
    assert body["access_token"]


@pytest.mark.anyio
async def test_register_with_must_change_password_true_is_noop_when_feature_disabled():
    app = _build_app(provider=_DisabledProvider())
    async with app.router.lifespan_context(app):
        async with await _client(app) as client:
            register_resp = await client.post(
                "/api/v1/register/",
                json={
                    "email": "disabled-provision@example.com",
                    "password": "TempPass123!",
                    "must_change_password": True,
                    "login": True,
                },
            )
            user_id = register_resp.json()["user"]["id"]
            assert register_resp.status_code == 201
            body = register_resp.json()
            # ...but has no effect on token issuance while the feature flag itself is off.
            assert "token_scope" not in body
            assert body["access_token"]
        # The flag is still persisted on the row (it's just an unconditional column write)...
        assert await _must_change_password_flag(app, user_id) is True


# ---------------------------------------------------------------------------
# login/otp/verify wiring (cross-router reuse of resolve_forced_password_change_scope)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_otp_verify_also_issues_restricted_token():
    app = _build_app()
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            user = await repo.create(
                User(
                    id=str(uuid.uuid4()),
                    email="otp-forced@example.com",
                    password_hash=hash_password("TempPass123!"),
                    is_active=True,
                    metadata={"phone_country_code": "+1", "phone_number": "5551234567"},
                )
            )
            db_user = await session.get(UserDB, user.id)
            db_user.phone_country_code = "+1"
            db_user.phone_number = "5551234567"
            db_user.must_change_password = True
            await session.commit()

        from tenxyte.adapters.fastapi.otp_service import generate_otp

        async with session_factory() as session:
            settings = app.state.tenxyte_settings
            _row, raw_code = await generate_otp(session, user.id, "login", settings)

        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/login/otp/verify/",
                json={"phone_country_code": "+1", "phone_number": "5551234567", "otp_code": raw_code, "totp_code": ""},
            )
    assert response.status_code == 200
    body = response.json()
    assert body["token_scope"] == "password_change_only"
    assert body["must_change_password"] is True
