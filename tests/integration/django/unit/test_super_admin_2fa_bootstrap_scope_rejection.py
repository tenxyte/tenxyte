"""
Scope-rejection tests for the Super Admin 2FA Bootstrap bootstrap token.

Spec: .kiro/specs/super-admin-2fa-bootstrap/  (Task 3.7)

Bug_Condition:
    A restricted bootstrap token (scope="2fa_setup_only") must NOT be able to
    access any endpoint other than /2fa/setup/ and /2fa/confirm/.

Expected_Behavior:
    can_access(bootstrap_token, endpoint) == false for every protected endpoint
    except the two 2FA bootstrap endpoints. Such attempts are rejected with
    HTTP 403 and code "INSUFFICIENT_SCOPE".

Preservation:
    Full-scope tokens (no "scope" claim) keep accessing those same endpoints
    exactly as before (they are NOT rejected for scope reasons).

This focuses on the default `@require_jwt` behavior: any endpoint that does not
explicitly opt-in via `allowed_scopes=["2fa_setup_only"]` rejects the bootstrap
token. Representative endpoints used here are TwoFactorStatusView (GET) and
TwoFactorDisableView (POST).

Validates: Requirements 2.4
"""

import json
import secrets

import pytest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.core.jwt_service import JWTService
from tenxyte.adapters.django import get_django_settings
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.views.twofa_views import (
    TwoFactorStatusView,
    TwoFactorDisableView,
)

BOOTSTRAP_SCOPE = "2fa_setup_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(name):
    app, _ = Application.create_application(name=name)
    return app


def _make_admin_user(email):
    """Create an admin user with 2FA enabled (full-scope path)."""
    user = User.objects.create(
        email=email,
        is_active=True,
        is_superuser=True,
        is_staff=True,
        is_2fa_enabled=True,
    )
    user.set_password("ScopeTestPass123!")
    user.save()
    return user


def _jwt_service():
    return JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())


def _make_token(user, app, *, scope=None):
    """Mint an access token for the user/app, optionally with a restricted scope."""
    extra_claims = {"scope": scope} if scope else None
    token, _jti, _exp = _jwt_service().generate_access_token(
        user_id=str(user.id),
        application_id=str(app.id),
        extra_claims=extra_claims,
    )
    return token


def _payload(response):
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode("utf-8"))


def _get(view_cls, path, app, access_token):
    factory = APIRequestFactory()
    req = factory.get(path, HTTP_AUTHORIZATION=f"Bearer {access_token}")
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


def _post(view_cls, path, data, app, access_token):
    factory = APIRequestFactory()
    req = factory.post(path, data=data, format="json", HTTP_AUTHORIZATION=f"Bearer {access_token}")
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


# ---------------------------------------------------------------------------
# Bug_Condition: bootstrap token rejected on non-bootstrap endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBootstrapTokenRejectedOnOtherEndpoints:
    """Validates: Requirements 2.4"""

    def test_status_endpoint_rejects_bootstrap_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ScopeApp-status-{nonce}")
        user = _make_admin_user(f"status-{nonce}@tenxyte.test")
        bootstrap_token = _make_token(user, app, scope=BOOTSTRAP_SCOPE)

        resp = _get(TwoFactorStatusView, "/api/v1/auth/2fa/status/", app, bootstrap_token)

        assert resp.status_code == 403, (
            f"Bootstrap token must be rejected on /2fa/status/, got {resp.status_code}: {_payload(resp)}"
        )
        assert _payload(resp).get("code") == "INSUFFICIENT_SCOPE", (
            f"Expected INSUFFICIENT_SCOPE, got: {_payload(resp)}"
        )

    def test_disable_endpoint_rejects_bootstrap_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ScopeApp-disable-{nonce}")
        user = _make_admin_user(f"disable-{nonce}@tenxyte.test")
        bootstrap_token = _make_token(user, app, scope=BOOTSTRAP_SCOPE)

        resp = _post(
            TwoFactorDisableView,
            "/api/v1/auth/2fa/disable/",
            {"code": "123456", "password": "ScopeTestPass123!"},
            app,
            bootstrap_token,
        )

        assert resp.status_code == 403, (
            f"Bootstrap token must be rejected on /2fa/disable/, got {resp.status_code}: {_payload(resp)}"
        )
        assert _payload(resp).get("code") == "INSUFFICIENT_SCOPE", (
            f"Expected INSUFFICIENT_SCOPE, got: {_payload(resp)}"
        )


# ---------------------------------------------------------------------------
# Preservation: full-scope token access unchanged
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullScopeTokenAccessUnchanged:
    """Preservation: full-scope tokens are NOT rejected for scope reasons."""

    def test_status_endpoint_accepts_full_scope_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ScopeApp-full-{nonce}")
        user = _make_admin_user(f"full-{nonce}@tenxyte.test")
        full_token = _make_token(user, app, scope=None)

        resp = _get(TwoFactorStatusView, "/api/v1/auth/2fa/status/", app, full_token)

        assert resp.status_code == 200, (
            f"Full-scope token should access /2fa/status/, got {resp.status_code}: {_payload(resp)}"
        )
        # Sanity: the response carries the 2FA status payload, not a scope error.
        assert "is_enabled" in _payload(resp)
