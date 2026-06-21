"""
Edge-case / integration tests for the Super Admin 2FA Bootstrap bugfix.

Spec: .kiro/specs/super-admin-2fa-bootstrap/  (Task 4 - Checkpoint)

These tests cover the edge cases called out in the checkpoint that are NOT
already covered by the bug-condition, preservation, or scope-rejection suites:

  1. Restricted bootstrap tokens cannot be refreshed
       - The bootstrap login response carries NO refresh_token.
       - Presenting the bootstrap access token (scope="2fa_setup_only",
         type="access") to the refresh endpoint is rejected (401 REFRESH_FAILED),
         because refresh_tokens only accepts opaque DB refresh tokens or JWTs
         whose type == "refresh".

  2. Full end-to-end bootstrap flow (real services, no mocks):
       create admin without 2FA -> login (bootstrap token) -> /2fa/setup/ with
       bootstrap token -> /2fa/confirm/ with a VALID TOTP code -> receive a
       full-scope token pair -> use the full token to access a protected
       endpoint (/2fa/status/) successfully.

  3. After 2FA is enabled, subsequent logins require a TOTP code (no more
     bootstrap tokens are issued).

Validates: Requirements 2.2, 2.3, 2.4, 2.5, 3.1
"""

import secrets

import pyotp
import pytest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.core.jwt_service import JWTService
from tenxyte.adapters.django import get_django_settings
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.views.auth_views import LoginEmailView, RefreshTokenView
from tenxyte.views.twofa_views import (
    TwoFactorSetupView,
    TwoFactorConfirmView,
    TwoFactorStatusView,
)

PASSWORD = "EdgeCasePass123!"
BOOTSTRAP_SCOPE = "2fa_setup_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(name):
    app, _ = Application.create_application(name=name)
    return app


def _make_admin_user(email, *, is_superuser=True, is_staff=True):
    """Create an admin user WITHOUT 2FA enabled (mfa_type == 'none')."""
    user = User.objects.create(
        email=email,
        is_active=True,
        is_superuser=is_superuser,
        is_staff=is_staff,
        is_2fa_enabled=False,
    )
    user.set_password(PASSWORD)
    user.save()
    return user


def _post(view_cls, path, data, app, access_token=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.post(path, data=data, format="json", **headers)
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


def _get(view_cls, path, app, access_token=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.get(path, **headers)
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


def _payload(response):
    if hasattr(response, "data"):
        return response.data
    import json

    return json.loads(response.content.decode("utf-8"))


def _login_email(app, user, totp_code=None):
    data = {"email": user.email, "password": PASSWORD}
    if totp_code is not None:
        data["totp_code"] = totp_code
    return _post(LoginEmailView, "/api/v1/auth/login/email/", data, app)


def _decode_scope(access_token):
    svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
    decoded = svc.decode_token(access_token, check_blacklist=False)
    assert decoded is not None, "token could not be decoded"
    return decoded.claims.get("scope")


# ---------------------------------------------------------------------------
# Edge case 1: restricted bootstrap tokens cannot be refreshed
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBootstrapTokenCannotBeRefreshed:
    """Validates: Requirement 2.5 (restricted token is not a long-lived/refreshable credential)."""

    def test_bootstrap_login_returns_no_refresh_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"EdgeRefresh-norefresh-{nonce}")
        user = _make_admin_user(f"norefresh-{nonce}@tenxyte.test")

        response = _login_email(app, user)
        payload = _payload(response)

        assert response.status_code == 200, payload
        assert payload.get("token_scope") == BOOTSTRAP_SCOPE, payload
        # A bootstrap login must NOT hand out a refresh token.
        assert "refresh_token" not in payload or not payload.get("refresh_token"), (
            f"Bootstrap login must not issue a refresh token: {payload}"
        )

    def test_bootstrap_access_token_rejected_by_refresh_endpoint(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"EdgeRefresh-reject-{nonce}")
        user = _make_admin_user(f"refreshreject-{nonce}@tenxyte.test")

        login_resp = _login_email(app, user)
        login_payload = _payload(login_resp)
        bootstrap_token = login_payload["access_token"]
        assert _decode_scope(bootstrap_token) == BOOTSTRAP_SCOPE

        # Attempt to use the restricted bootstrap access token as a refresh token.
        refresh_resp = _post(
            RefreshTokenView,
            "/api/v1/auth/refresh/",
            {"refresh_token": bootstrap_token},
            app,
        )
        refresh_payload = _payload(refresh_resp)

        assert refresh_resp.status_code == 401, (
            f"Restricted bootstrap token must not be refreshable, got "
            f"{refresh_resp.status_code}: {refresh_payload}"
        )
        assert refresh_payload.get("code") == "REFRESH_FAILED", refresh_payload


# ---------------------------------------------------------------------------
# Edge case 2 + 3: full end-to-end bootstrap flow, then 2FA enforced on relogin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullBootstrapFlowEndToEnd:
    """Validates: Requirements 2.2, 2.3, 2.4, 3.1"""

    def test_login_setup_confirm_yields_full_token_and_enforces_2fa_next_login(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"EdgeE2E-{nonce}")
        user = _make_admin_user(f"e2e-{nonce}@tenxyte.test")

        # 1. Log in -> receive restricted bootstrap token.
        login_resp = _login_email(app, user)
        login_payload = _payload(login_resp)
        assert login_resp.status_code == 200, login_payload
        assert login_payload.get("requires_2fa_setup") is True, login_payload
        bootstrap_token = login_payload["access_token"]
        assert _decode_scope(bootstrap_token) == BOOTSTRAP_SCOPE

        # 2. Call /2fa/setup/ with the bootstrap token -> get the TOTP secret.
        setup_resp = _post(
            TwoFactorSetupView,
            "/api/v1/auth/2fa/setup/",
            {},
            app,
            access_token=bootstrap_token,
        )
        setup_payload = _payload(setup_resp)
        assert setup_resp.status_code == 200, setup_payload
        secret = setup_payload["secret"]
        assert secret, setup_payload

        # 3. Confirm with a VALID TOTP code -> receive a full-scope token pair.
        valid_code = pyotp.TOTP(secret).now()
        confirm_resp = _post(
            TwoFactorConfirmView,
            "/api/v1/auth/2fa/confirm/",
            {"code": valid_code},
            app,
            access_token=bootstrap_token,
        )
        confirm_payload = _payload(confirm_resp)
        assert confirm_resp.status_code == 200, confirm_payload
        assert confirm_payload.get("is_enabled") is True, confirm_payload

        full_token = confirm_payload.get("access_token")
        assert full_token, f"Confirmation with bootstrap token must return a full token: {confirm_payload}"
        # The upgraded token must be full-scope (no restricted scope claim).
        assert _decode_scope(full_token) != BOOTSTRAP_SCOPE, confirm_payload

        # 4. The full-scope token can access a protected endpoint the bootstrap
        #    token could not (/2fa/status/).
        status_resp = _get(
            TwoFactorStatusView,
            "/api/v1/auth/2fa/status/",
            app,
            access_token=full_token,
        )
        status_payload = _payload(status_resp)
        assert status_resp.status_code == 200, status_payload
        assert status_payload.get("is_enabled") is True, status_payload

        # 5. Subsequent login now REQUIRES a TOTP code (no more bootstrap token).
        relogin_resp = _login_email(app, user)
        relogin_payload = _payload(relogin_resp)
        assert relogin_resp.status_code == 401, (
            f"After 2FA is enabled, login must require a TOTP code, got "
            f"{relogin_resp.status_code}: {relogin_payload}"
        )
        assert relogin_payload.get("code") == "2FA_REQUIRED", relogin_payload
        assert relogin_payload.get("requires_2fa") is True, relogin_payload
        assert "requires_2fa_setup" not in relogin_payload, relogin_payload
