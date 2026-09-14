"""
Feature: z_aud_3, Property 8: feature-flag and scope parity (spec `design.md` Property 8, task
7.2) — for each feature flag currently gated in the Reference_Stack (`otp_login_enabled`,
`magic_link_enabled`) and each on/off state, the FastAPI_Adapter reproduces the Django_Adapter's
gating behavior; and for each restricted-token scope (`2fa_setup_only`, `password_change_only`),
`require_jwt`'s scope allow-list is enforced consistently across every JWT-protected endpoint in
the Reference_Stack, not just the ones each router's own test file happens to exercise directly.

`WEBAUTHN_ENABLED`/`AIRS_ENABLED`/`FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` (also named in
`design.md`'s Property 8) aren't covered here — none of Waves F/G/force-password-change exist in
the Reference_Stack yet (see `routers/auth.py`'s module docstring for the latter's explicit
out-of-scope rationale). This test covers exactly what's actually gated today; it'll grow as those
waves land.
"""

import uuid
from datetime import timedelta

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
    def __init__(self, *, otp_login_enabled: bool = False, magic_link_enabled: bool = True):
        super().__init__()
        self._otp_login_enabled = otp_login_enabled
        self._magic_link_enabled = magic_link_enabled

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-flag-scope-property"
        if name == "TENXYTE_OTP_LOGIN_ENABLED":
            return self._otp_login_enabled
        if name == "TENXYTE_MAGIC_LINK_ENABLED":
            return self._magic_link_enabled
        return super().get(name, default)


def _build_app(**flags):
    settings = Settings(provider=_TestProvider(**flags))
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
@pytest.mark.parametrize("otp_login_enabled", [True, False])
async def test_otp_login_feature_flag_gates_both_endpoints_consistently(otp_login_enabled):
    """Property 8: `otp_login_enabled` in a given state must gate `login/otp/request/` AND
    `login/otp/verify/` identically — never one 404 FEATURE_DISABLED while the other isn't."""
    app = _build_app(otp_login_enabled=otp_login_enabled)
    async with app.router.lifespan_context(app), await _client(app) as client:
        request_response = await client.post(
            "/api/v1/login/otp/request/", json={"phone_country_code": "33", "phone_number": "612345678"}
        )
        verify_response = await client.post(
            "/api/v1/login/otp/verify/",
            json={"phone_country_code": "33", "phone_number": "612345678", "otp_code": "000000"},
        )

    request_disabled = request_response.status_code == 404 and request_response.json().get("code") == "FEATURE_DISABLED"
    verify_disabled = verify_response.status_code == 404 and verify_response.json().get("code") == "FEATURE_DISABLED"

    assert request_disabled == verify_disabled == (not otp_login_enabled)


@pytest.mark.anyio
@pytest.mark.parametrize("magic_link_enabled", [True, False])
async def test_magic_link_feature_flag_gates_both_endpoints(magic_link_enabled):
    """Property 8, magic-link variant: `magic_link_enabled=False` gates both endpoints, but NOT
    with the same 404 FEATURE_DISABLED shape `login/otp` uses — verified, real Django behavior
    (see routers/magic_link.py's module docstring): the service-level `enabled` check surfaces as
    503 SERVICE_UNAVAILABLE on `request/` and folds into the generic 401 MAGIC_LINK_INVALID on
    `verify/` (a disabled service and an invalid token are indistinguishable to that endpoint).
    Documented divergence from design.md's generic "404 FEATURE_DISABLED" wording, not a bug."""
    app = _build_app(magic_link_enabled=magic_link_enabled)
    async with app.router.lifespan_context(app), await _client(app) as client:
        request_response = await client.post(
            "/api/v1/magic-link/request/",
            json={"email": "flag@example.com", "validation_url": "https://a.example/verify"},
        )
        verify_response = await client.get("/api/v1/magic-link/verify/", params={"token": "whatever"})

    if magic_link_enabled:
        assert request_response.status_code == 200
    else:
        assert request_response.status_code == 503
        assert request_response.json()["code"] == "SERVICE_UNAVAILABLE"

    # verify/ can't structurally distinguish "disabled" from "bad token" either way — always
    # 401 MAGIC_LINK_INVALID for a token that was never actually issued.
    assert verify_response.status_code == 401
    assert verify_response.json()["code"] == "MAGIC_LINK_INVALID"


# (method, path, json_body_or_None, required_scope_category) for every currently JWT-protected
# endpoint in the Reference_Stack. required_scope_category is one of:
#   "bare"                 — require_jwt() with no allowed_scopes: only a full-scope token passes.
#   "2fa_setup_only"       — require_jwt(allowed_scopes=["2fa_setup_only"])
#   "password_change_only" — require_jwt(allowed_scopes=["password_change_only"])
#   "any"                  — require_jwt(allow_any_scope=True): every scope passes.
_PROTECTED_ENDPOINTS = [
    ("POST", "/otp/request/", {"otp_type": "email"}, "bare"),
    ("POST", "/otp/verify/email/", {"code": "000000"}, "bare"),
    ("POST", "/otp/verify/phone/", {"code": "000000"}, "bare"),
    ("GET", "/2fa/status/", None, "bare"),
    ("POST", "/2fa/disable/", {"code": "000000", "password": "whatever"}, "bare"),
    ("POST", "/2fa/backup-codes/", {"code": "000000"}, "bare"),
    ("GET", "/me/roles/", None, "bare"),
    ("POST", "/logout/all/", None, "password_change_only"),
    ("POST", "/password/change/", {"current_password": "x", "new_password": "Xy1!aaaaaaaa"}, "password_change_only"),
    ("POST", "/password/set-initial/", {"otp_code": "000000", "new_password": "Xy1!aaaaaaaa"}, "password_change_only"),
    ("POST", "/2fa/setup/", None, "2fa_setup_only"),
    ("POST", "/2fa/confirm/", {"code": "000000"}, "2fa_setup_only"),
    ("GET", "/me/", None, "any"),
    ("PATCH", "/me/", {}, "any"),
]

_CANDIDATE_TOKEN_SCOPES = [None, "2fa_setup_only", "password_change_only", "some_unrelated_scope"]


def _scope_is_allowed(token_scope: str | None, category: str) -> bool:
    if category == "any":
        return True
    if token_scope is None:
        return True
    return token_scope == category


@pytest.mark.anyio
async def test_scope_allow_list_enforced_consistently_across_every_protected_endpoint():
    """Property 8: a token carrying scope X is accepted ONLY by the endpoints whose allow-list
    includes X (or by any endpoint, if the token is full-scope / has no scope claim at all) —
    checked against every currently JWT-protected endpoint in the Reference_Stack at once, not
    just the handful each router's own test file happens to probe."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            user = await repo.create(
                User(id=str(uuid.uuid4()), email="scopetest@example.com", password_hash=password_hash, is_active=True)
            )

        jwt_service = app.state.tenxyte_jwt_service

        def _mint(token_scope: str | None) -> str:
            extra_claims = {"scope": token_scope} if token_scope is not None else None
            access_token, _jti, _expires_at = jwt_service.generate_access_token(
                user_id=user.id, application_id="default", extra_claims=extra_claims, custom_lifetime=timedelta(hours=1)
            )
            return access_token

        failures = []
        async with await _client(app) as client:
            for method, path, json_body, category in _PROTECTED_ENDPOINTS:
                for token_scope in _CANDIDATE_TOKEN_SCOPES:
                    # A fresh token per call, never reused: some endpoints (logout/all/) have a
                    # legitimate side effect of blacklisting the very token that called them —
                    # reusing one token across the whole matrix would let that side effect poison
                    # unrelated later assertions.
                    headers = {"Authorization": f"Bearer {_mint(token_scope)}"}
                    request_kwargs = {"headers": headers}
                    if json_body is not None or method != "GET":
                        request_kwargs["json"] = json_body or {}
                    response = await client.request(method, f"/api/v1{path}", **request_kwargs)

                    is_insufficient_scope = (
                        response.status_code == 403 and response.json().get("code") == "INSUFFICIENT_SCOPE"
                    )
                    expected_allowed = _scope_is_allowed(token_scope, category)

                    if expected_allowed and is_insufficient_scope:
                        failures.append(
                            f"{method} {path}: scope={token_scope!r} (category={category}) was wrongly "
                            f"rejected as INSUFFICIENT_SCOPE"
                        )
                    elif not expected_allowed and not is_insufficient_scope:
                        failures.append(
                            f"{method} {path}: scope={token_scope!r} (category={category}) should have been "
                            f"rejected as INSUFFICIENT_SCOPE but got {response.status_code} "
                            f"{response.json().get('code')}"
                        )
                    elif expected_allowed and response.status_code in (401, 403):
                        failures.append(
                            f"{method} {path}: scope={token_scope!r} (category={category}) was allowed by scope "
                            f"but unexpectedly rejected: {response.status_code} {response.json().get('code')}"
                        )

    assert not failures, "\n".join(failures)
