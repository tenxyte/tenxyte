"""
Preservation property tests for the Super Admin 2FA Bootstrap bugfix.

Spec: .kiro/specs/super-admin-2fa-bootstrap/

Property 2 (Preservation) — Existing Authentication Flows Unchanged:
    For ALL login requests where the bug condition does NOT hold
    (i.e. NOT (admin AND mfa_type == "none")), the fixed login flow must
    produce the SAME result as the original. In particular, such requests
    must NEVER receive a restricted "2fa_setup_only" bootstrap token.

    isBugCondition(X) == (X.user.is_superuser OR X.user.is_staff)
                         AND X.user.mfa_type == "none"
                         AND X.attempting_login

    The non-bug-condition input space is therefore:
        - regular (non-admin) users, 2FA enabled or disabled
        - admin users (is_superuser OR is_staff) WITH 2FA enabled

OBSERVATION-FIRST METHODOLOGY:
    These tests encode behavior OBSERVED on the UNFIXED codebase for non-buggy
    inputs. They MUST PASS on unfixed code (they establish the baseline that the
    fix must preserve). After the fix they must STILL pass (no regressions).

    Observed baseline (unfixed code, src/tenxyte/views/auth_views.py):
        - regular user, 2FA disabled, valid credentials  -> 200, full token,
          requires_2fa == False, NO bootstrap markers
        - any user, 2FA enabled, no TOTP code provided    -> 401 "2FA_REQUIRED",
          requires_2fa == True
        - admin (superuser/staff), 2FA enabled, no TOTP    -> 401 "2FA_REQUIRED"
          (admins with 2FA must still provide a TOTP code; NOT a bootstrap token)
        - invalid credentials                              -> 401 "LOGIN_FAILED"
        - 2FA disable endpoint without auth                -> 401 (stays restricted)
        - token refresh with a valid refresh token         -> 200, new access token

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import secrets

import pytest
from unittest.mock import patch
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.views.auth_views import LoginEmailView, LoginPhoneView, RefreshTokenView
from tenxyte.views.twofa_views import TwoFactorDisableView

PASSWORD = "PreservePass123!"

BOOTSTRAP_SCOPE = "2fa_setup_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(name):
    app, _ = Application.create_application(name=name)
    return app


def _make_user(
    email,
    *,
    is_superuser=False,
    is_staff=False,
    twofa_enabled=False,
    phone=None,
):
    """Create a user. When twofa_enabled, set a TOTP secret (mfa_type != none)."""
    kwargs = {
        "email": email,
        "is_active": True,
        "is_superuser": is_superuser,
        "is_staff": is_staff,
        "is_2fa_enabled": twofa_enabled,
    }
    if twofa_enabled:
        kwargs["totp_secret"] = "JBSWY3DPEHPK3PXP"
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


def _response_payload(response):
    """Return the response data dict (DRF Response or JsonResponse)."""
    if hasattr(response, "data"):
        return response.data
    import json

    return json.loads(response.content.decode("utf-8"))


def _is_bootstrap_response(response):
    """True if the response looks like a restricted 2fa_setup_only bootstrap token."""
    if response.status_code != 200:
        return False
    payload = _response_payload(response)
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("requires_2fa_setup") is True
        or payload.get("token_scope") == BOOTSTRAP_SCOPE
    )


def _login(login_path, app, user, totp_code=None):
    """Drive the appropriate login view and return its response."""
    if login_path == "email":
        data = {"email": user.email, "password": PASSWORD}
        if totp_code is not None:
            data["totp_code"] = totp_code
        return _post(LoginEmailView, "/api/v1/auth/login/email/", data, app)
    else:
        data = {
            "phone_country_code": user.phone_country_code,
            "phone_number": user.phone_number,
            "password": PASSWORD,
        }
        if totp_code is not None:
            data["totp_code"] = totp_code
        return _post(LoginPhoneView, "/api/v1/auth/login/phone/", data, app)


def _new_phone():
    return ("1", f"5{secrets.randbelow(10**9):09d}")


# ---------------------------------------------------------------------------
# Property 2: Preservation - Non-bug-condition logins are unchanged
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPreservationLoginFlows:
    """
    Validates: Requirements 3.1, 3.2

    Must PASS on unfixed code (baseline) and continue to PASS after the fix.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        # Non-bug-condition user kinds only:
        #   - "regular": non-admin (bug condition never applies)
        #   - "admin_superuser_2fa" / "admin_staff_2fa": admin WITH 2FA enabled
        user_kind=st.sampled_from(
            ["regular", "admin_superuser_2fa", "admin_staff_2fa"]
        ),
        twofa_enabled=st.booleans(),
        login_path=st.sampled_from(["email", "phone"]),
    )
    def test_non_bug_condition_login_preserved(
        self, user_kind, twofa_enabled, login_path
    ):
        """
        For every NON-bug-condition login (no TOTP code supplied):
          - the response is NEVER a 2fa_setup_only bootstrap token, AND
          - 2FA-disabled (non-admin) users get a full token (200, requires_2fa False), AND
          - 2FA-enabled users are asked for a TOTP code (401 2FA_REQUIRED).
        """
        is_admin = user_kind in ("admin_superuser_2fa", "admin_staff_2fa")
        # Admins are only in the non-bug-condition space when 2FA is enabled.
        effective_2fa = True if is_admin else twofa_enabled

        nonce = secrets.token_hex(4)
        app = _make_app(f"PreserveApp-{nonce}")
        phone = _new_phone() if login_path == "phone" else None

        user = _make_user(
            f"{user_kind}-{nonce}@tenxyte.test",
            is_superuser=(user_kind == "admin_superuser_2fa"),
            is_staff=(user_kind == "admin_staff_2fa"),
            twofa_enabled=effective_2fa,
            phone=phone,
        )

        response = _login(login_path, app, user)
        payload = _response_payload(response)

        # PRESERVATION INVARIANT: never a bootstrap token for non-bug inputs.
        assert not _is_bootstrap_response(response), (
            f"Non-bug-condition login must not yield a bootstrap token: {payload}"
        )

        if effective_2fa:
            # 2FA enabled -> must be asked for a TOTP code (Req 3.1, 3.2).
            assert response.status_code == 401, (
                f"Expected 401 2FA challenge, got {response.status_code}: {payload}"
            )
            assert payload.get("code") == "2FA_REQUIRED", (
                f"Expected code=2FA_REQUIRED, got: {payload}"
            )
            assert payload.get("requires_2fa") is True
        else:
            # Non-admin without 2FA -> normal full-token login (Req 3.2).
            assert response.status_code == 200, (
                f"Expected 200 full-token login, got {response.status_code}: {payload}"
            )
            assert payload.get("access_token"), f"Expected access_token, got: {payload}"
            assert payload.get("requires_2fa") is False
            assert "requires_2fa_setup" not in payload


@pytest.mark.django_db
class TestPreservationAdminWith2FAStillRequiresTOTP:
    """
    Validates: Requirement 3.1

    Admins with 2FA enabled must CONTINUE to be challenged for a TOTP code on
    login (they must not silently receive a bootstrap or full token). This is
    the key discriminator from the bug-condition (admin WITHOUT 2FA) path.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=12,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        admin_kind=st.sampled_from(["superuser", "staff"]),
        login_path=st.sampled_from(["email", "phone"]),
    )
    def test_admin_with_2fa_still_challenged(self, admin_kind, login_path):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PreserveAdmin2FA-{nonce}")
        phone = _new_phone() if login_path == "phone" else None

        user = _make_user(
            f"admin-{admin_kind}-{nonce}@tenxyte.test",
            is_superuser=(admin_kind == "superuser"),
            is_staff=(admin_kind == "staff"),
            twofa_enabled=True,
            phone=phone,
        )

        response = _login(login_path, app, user)
        payload = _response_payload(response)

        assert response.status_code == 401, (
            f"Admin with 2FA must be challenged for TOTP, got {response.status_code}: {payload}"
        )
        assert payload.get("code") == "2FA_REQUIRED"
        assert payload.get("requires_2fa") is True
        assert not _is_bootstrap_response(response)


@pytest.mark.django_db
class TestPreservationInvalidCredentials:
    """
    Validates: Requirement 3.2 (authentication preserved)

    Invalid credentials are rejected with 401 LOGIN_FAILED regardless of the
    admin/2FA state - the bootstrap path must never be reachable without a
    successful password authentication.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        is_admin=st.booleans(),
        login_path=st.sampled_from(["email", "phone"]),
    )
    def test_wrong_password_rejected(self, is_admin, login_path):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PreserveBadCreds-{nonce}")
        phone = _new_phone() if login_path == "phone" else None

        user = _make_user(
            f"badcreds-{nonce}@tenxyte.test",
            is_superuser=is_admin,
            twofa_enabled=False,
            phone=phone,
        )

        if login_path == "email":
            response = _post(
                LoginEmailView,
                "/api/v1/auth/login/email/",
                {"email": user.email, "password": "WrongPassword999!"},
                app,
            )
        else:
            response = _post(
                LoginPhoneView,
                "/api/v1/auth/login/phone/",
                {
                    "phone_country_code": user.phone_country_code,
                    "phone_number": user.phone_number,
                    "password": "WrongPassword999!",
                },
                app,
            )

        payload = _response_payload(response)
        assert response.status_code == 401, (
            f"Expected 401 for wrong password, got {response.status_code}: {payload}"
        )
        assert not _is_bootstrap_response(response)


# ---------------------------------------------------------------------------
# Preservation - 2FA disable endpoint stays restricted (Req 3.3)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPreservation2FADisableRestricted:
    """
    Validates: Requirement 3.3

    The 2FA disable endpoint must remain authentication-restricted: an
    unauthenticated request is rejected with 401 and never granted access.
    """

    @pytest.mark.django_db
    def test_disable_requires_authentication(self):
        app = _make_app("PreserveDisable")
        factory = APIRequestFactory()
        req = factory.post("/api/v1/auth/2fa/disable/", data={"code": "123456"}, format="json")
        req.application = app
        with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
            response = TwoFactorDisableView.as_view()(req)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Preservation - token refresh issues a new access token (Req 3.6)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPreservationTokenRefresh:
    """
    Validates: Requirement 3.6

    Token refresh must continue to issue a new access token. The refresh token
    is obtained through the real login flow (a regular, non-admin user without
    2FA - a non-bug-condition input) so the observed refresh behavior is the
    genuine end-to-end path. The refreshed response must remain a normal,
    full-scope token (never a bootstrap token).
    """

    @pytest.mark.django_db
    def test_refresh_issues_new_access_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PreserveRefresh-{nonce}")
        user = _make_user(
            f"refresh-{nonce}@tenxyte.test",
            twofa_enabled=False,  # regular non-admin, non-bug condition
        )

        # Obtain a real refresh token via the genuine login flow.
        login_response = _login("email", app, user)
        login_payload = _response_payload(login_response)
        assert login_response.status_code == 200, (
            f"Setup login should succeed, got {login_response.status_code}: {login_payload}"
        )
        refresh_token = login_payload.get("refresh_token")
        assert refresh_token, f"Expected a refresh_token from login, got: {login_payload}"

        response = _post(
            RefreshTokenView,
            "/api/v1/auth/refresh/",
            {"refresh_token": refresh_token},
            app,
        )
        payload = _response_payload(response)

        assert response.status_code == 200, (
            f"Expected 200 on refresh, got {response.status_code}: {payload}"
        )
        assert payload.get("access_token"), f"Expected new access_token, got: {payload}"
        assert payload.get("token_scope") != BOOTSTRAP_SCOPE
        assert "requires_2fa_setup" not in payload
