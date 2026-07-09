"""
Bug condition exploration test for the Super Admin 2FA Bootstrap circular dependency.

Spec: .kiro/specs/super-admin-2fa-bootstrap/

Property 1 (Bug Condition / Expected Behavior):
    For any login request where the user is an admin (is_superuser OR is_staff)
    and the user does not have 2FA enabled (mfa_type == "none"), the login flow
    SHALL issue a restricted-scope bootstrap token:
        - success (HTTP 200)
        - token_scope == "2fa_setup_only"
        - requires_2fa_setup == true
        - access_token IS NOT NULL
        - token_lifetime <= 900 seconds
        - the token can call /2fa/setup/ and /2fa/confirm/
        - the token CANNOT call /2fa/status/ (or other protected endpoints)

IMPORTANT (bugfix workflow):
    This test is EXPECTED TO FAIL on the UNFIXED codebase. The failure confirms the
    bug exists: admins without 2FA currently receive 403 ADMIN_2FA_SETUP_REQUIRED and
    no token is issued, which creates the circular bootstrap dependency.

    This same test will validate the fix once implemented (it must PASS after the fix).

    DO NOT "fix" this test to make it pass on unfixed code.

Scoped PBT approach: the bug is deterministic, so the property is scoped to the
concrete failing configurations (superuser / staff / role-elevated admin, across
both the email and phone login paths).

Validates: Requirements 2.1, 2.2, 2.5
"""

import secrets

import pytest
from unittest.mock import patch
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.views.auth_views import LoginEmailView, LoginPhoneView
from tenxyte.views.twofa_views import (
    TwoFactorSetupView,
    TwoFactorConfirmView,
    TwoFactorStatusView,
)

PASSWORD = "BootstrapPass123!"

# Bootstrap token requirements.
BOOTSTRAP_SCOPE = "2fa_setup_only"
MAX_BOOTSTRAP_LIFETIME_SECONDS = 900


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(name):
    app, _ = Application.create_application(name=name)
    return app


def _make_admin_user(email, *, is_superuser=False, is_staff=False, phone=None):
    """Create an admin user WITHOUT 2FA enabled (mfa_type == 'none')."""
    kwargs = {
        "email": email,
        "is_active": True,
        "is_superuser": is_superuser,
        "is_staff": is_staff,
        "is_2fa_enabled": False,  # mfa_type == "none"
    }
    if phone is not None:
        kwargs["phone_country_code"] = phone[0]
        kwargs["phone_number"] = phone[1]
    user = User.objects.create(**kwargs)
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


def _response_payload(response):
    """Return the response data dict (DRF Response or JsonResponse)."""
    if hasattr(response, "data"):
        return response.data
    import json

    return json.loads(response.content.decode("utf-8"))


def _token_lifetime_seconds(access_token):
    """Decode the access token and return its lifetime (exp - iat) in seconds."""
    from tenxyte.core.jwt_service import JWTService
    from tenxyte.adapters.django import get_django_settings
    from tenxyte.adapters.django.cache_service import DjangoCacheService

    svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
    decoded = svc.decode_token(access_token, check_blacklist=False)
    assert decoded is not None, "Bootstrap access token could not be decoded"
    return (decoded.exp - decoded.iat).total_seconds()


def _token_scope(access_token):
    from tenxyte.core.jwt_service import JWTService
    from tenxyte.adapters.django import get_django_settings
    from tenxyte.adapters.django.cache_service import DjangoCacheService

    svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
    decoded = svc.decode_token(access_token, check_blacklist=False)
    assert decoded is not None, "Bootstrap access token could not be decoded"
    return decoded.claims.get("scope")


def _can_call_endpoint(view_cls, path, app, access_token, method="post", data=None):
    """
    Return True if the token is accepted by the endpoint (not rejected for
    auth/scope reasons), False if rejected with 401/403.
    """
    if method == "get":
        resp = _get(view_cls, path, app, access_token=access_token)
    else:
        resp = _post(view_cls, path, data or {}, app, access_token=access_token)
    return resp.status_code not in (401, 403)


def _login(login_path, app, user):
    """Drive the appropriate login view and return its response."""
    if login_path == "email":
        return _post(
            LoginEmailView,
            "/api/v1/auth/login/email/",
            {"email": user.email, "password": PASSWORD},
            app,
        )
    else:
        return _post(
            LoginPhoneView,
            "/api/v1/auth/login/phone/",
            {
                "phone_country_code": user.phone_country_code,
                "phone_number": user.phone_number,
                "password": PASSWORD,
            },
            app,
        )


def _assert_bootstrap_behavior(response, app):
    """
    Assert the Expected Behavior Properties for the bug/expected-behavior property.

    On UNFIXED code this fails at the first assertion (login returns 403
    ADMIN_2FA_SETUP_REQUIRED), which is the documented counterexample.
    """
    payload = _response_payload(response)

    # ASSERT result.success = true
    assert response.status_code == 200, (
        f"Expected 200 bootstrap token issuance, got {response.status_code}: {payload}"
    )

    # ASSERT result.requires_2fa_setup = true
    assert payload.get("requires_2fa_setup") is True, (
        f"Expected requires_2fa_setup=true, got: {payload}"
    )

    # ASSERT result.access_token IS NOT NULL
    access_token = payload.get("access_token")
    assert access_token, f"Expected a non-null access_token, got: {payload}"

    # ASSERT result.token_scope = "2fa_setup_only"
    reported_scope = payload.get("token_scope") or _token_scope(access_token)
    assert reported_scope == BOOTSTRAP_SCOPE, (
        f"Expected token_scope='{BOOTSTRAP_SCOPE}', got '{reported_scope}'"
    )

    # ASSERT result.token_lifetime <= 900
    lifetime = _token_lifetime_seconds(access_token)
    assert lifetime <= MAX_BOOTSTRAP_LIFETIME_SECONDS, (
        f"Expected token lifetime <= {MAX_BOOTSTRAP_LIFETIME_SECONDS}s, got {lifetime}s"
    )

    # ASSERT can_call_endpoint(token, "/2fa/setup/") = true
    assert _can_call_endpoint(
        TwoFactorSetupView, "/api/v1/auth/2fa/setup/", app, access_token, method="post"
    ), "Bootstrap token should be able to call /2fa/setup/"

    # ASSERT can_call_endpoint(token, "/2fa/confirm/") = true
    assert _can_call_endpoint(
        TwoFactorConfirmView,
        "/api/v1/auth/2fa/confirm/",
        app,
        access_token,
        method="post",
        data={"code": "000000"},
    ), "Bootstrap token should be able to call /2fa/confirm/"

    # ASSERT can_call_endpoint(token, "/2fa/status/") = false
    assert not _can_call_endpoint(
        TwoFactorStatusView, "/api/v1/auth/2fa/status/", app, access_token, method="get"
    ), "Bootstrap token must NOT be able to call /2fa/status/"


# ---------------------------------------------------------------------------
# Property 1: Bug Condition / Expected Behavior - Bootstrap Token Issuance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSuperAdminBootstrapTokenIssuance:
    """
    Validates: Requirements 2.1, 2.2, 2.5

    Expected to FAIL on unfixed code (proves the bug); will PASS after the fix.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=12,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        admin_kind=st.sampled_from(["superuser", "staff", "role_elevated"]),
        login_path=st.sampled_from(["email", "phone"]),
    )
    def test_admin_without_2fa_receives_bootstrap_token(self, admin_kind, login_path):
        """
        For all admin users without 2FA, across both login paths, the system
        should issue a restricted 2fa_setup_only bootstrap token.
        """
        # Unique names/emails per generated example to avoid collisions.
        nonce = secrets.token_hex(4)
        app = _make_app(f"BootstrapApp-{nonce}")

        is_superuser = admin_kind == "superuser"
        # "role_elevated" models a previously-regular user elevated to admin
        # (the login flow gates on is_staff/is_superuser).
        is_staff = admin_kind in ("staff", "role_elevated")

        phone = None
        if login_path == "phone":
            # Generate a unique-ish phone number per example.
            phone = ("1", f"5{secrets.randbelow(10**9):09d}")

        user = _make_admin_user(
            f"admin-{admin_kind}-{nonce}@tenxyte.test",
            is_superuser=is_superuser,
            is_staff=is_staff,
            phone=phone,
        )

        response = _login(login_path, app, user)
        _assert_bootstrap_behavior(response, app)

    @pytest.mark.django_db
    def test_superuser_email_login_concrete_counterexample(self):
        """
        Concrete deterministic counterexample (superuser via createsuperuser,
        email login). Documents the exact failing output on unfixed code.
        """
        app = _make_app("BootstrapApp-superuser-email")
        user = _make_admin_user(
            "superadmin@tenxyte.test", is_superuser=True, is_staff=True
        )
        response = _login("email", app, user)
        _assert_bootstrap_behavior(response, app)

    @pytest.mark.django_db
    def test_staff_phone_login_concrete_counterexample(self):
        """
        Concrete deterministic counterexample (staff user, phone login).
        """
        app = _make_app("BootstrapApp-staff-phone")
        user = _make_admin_user(
            "staff@tenxyte.test",
            is_staff=True,
            phone=("1", "5550000001"),
        )
        response = _login("phone", app, user)
        _assert_bootstrap_behavior(response, app)
