"""
Tests auth_views.py — RegisterView, LoginEmailView, LoginPhoneView,
RefreshTokenView, LogoutView, LogoutAllView.

Coverage cible : views/auth_views.py (37% → 80%)
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, RefreshToken
from tenxyte.views.auth_views import (
    RegisterView, LoginEmailView, LoginPhoneView,
    RefreshTokenView, LogoutView, LogoutAllView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="AuthViewApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, password="Pass123!"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _jwt_token(user, app):
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


def _post(view_cls, path, data, app, user=None, access_token=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.post(path, data=data, format="json", **headers)
    req.application = app
    if user:
        req.user = user
    # Bypass throttling in tests
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = view_cls.as_view()
        return view(req)


def _get(view_cls, path, user, app):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = view_cls.as_view()
        return view(req)


def _refresh_token(user, app):
    return RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4")


# ===========================================================================
# RegisterView
# ===========================================================================

class TestRegisterView:

    @pytest.mark.django_db
    def test_register_success(self):
        app = _app("RegView1")
        resp = _post(RegisterView, "/auth/register/", {
            "email": "newreg@test.com",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 201
        assert "user" in resp.data

    @pytest.mark.django_db
    def test_register_invalid_data_returns_400(self):
        app = _app("RegView2")
        resp = _post(RegisterView, "/auth/register/", {}, app)
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_register_duplicate_email_returns_201_for_anti_enumeration(self):
        app = _app("RegView3")
        _user("dup_reg@test.com")
        resp = _post(RegisterView, "/auth/register/", {
            "email": "dup_reg@test.com",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 201

    @pytest.mark.django_db
    def test_register_with_login_returns_tokens(self):
        app = _app("RegView4")
        resp = _post(RegisterView, "/auth/register/", {
            "email": "loginreg@test.com",
            "password": "Pass123!",
            "login": True,
        }, app)
        assert resp.status_code == 201
        assert "access_token" in resp.data
        assert "refresh_token" in resp.data

    @pytest.mark.django_db
    def test_register_sends_otp_for_email(self):
        app = _app("RegView5")
        with patch("tenxyte.services.OTPService") as MockOTP:
            mock_instance = MagicMock()
            MockOTP.return_value = mock_instance
            mock_instance.generate_email_verification_otp.return_value = (MagicMock(), "123456")
            resp = _post(RegisterView, "/auth/register/", {
                "email": "otpreg@test.com",
                "password": "Pass123!",
            }, app)
        assert resp.status_code == 201
        mock_instance.generate_email_verification_otp.assert_called_once()


# ===========================================================================
# LoginEmailView
# ===========================================================================

class TestLoginEmailView:

    @pytest.mark.django_db
    def test_login_success(self):
        app = _app("LoginEmailApp1")
        _user("loginemail1@test.com", "Pass123!")
        resp = _post(LoginEmailView, "/auth/login/email/", {
            "email": "loginemail1@test.com",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 200
        assert "access_token" in resp.data

    @pytest.mark.django_db
    def test_login_wrong_password_returns_401(self):
        app = _app("LoginEmailApp2")
        _user("loginemail2@test.com", "Pass123!")
        resp = _post(LoginEmailView, "/auth/login/email/", {
            "email": "loginemail2@test.com",
            "password": "WrongPass!",
        }, app)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_login_unknown_user_returns_401(self):
        app = _app("LoginEmailApp3")
        resp = _post(LoginEmailView, "/auth/login/email/", {
            "email": "nobody@test.com",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_login_invalid_data_returns_400(self):
        app = _app("LoginEmailApp4")
        resp = _post(LoginEmailView, "/auth/login/email/", {}, app)
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_login_2fa_required_returns_401_with_flag(self):
        app = _app("LoginEmailApp5")
        user = _user("loginemail5@test.com", "Pass123!")
        user.is_2fa_enabled = True
        user.save()

        with patch("tenxyte.views.auth_views.authenticate_by_email_with_core") as mock_auth:
            mock_auth.return_value = (True, {"_user": user, "requires_2fa": True}, "")
            resp = _post(LoginEmailView, "/auth/login/email/", {
                "email": "loginemail5@test.com",
                "password": "Pass123!",
            }, app)

        assert resp.status_code == 401
        assert resp.data.get("code") == "2FA_REQUIRED"

    @pytest.mark.django_db
    def test_login_2fa_invalid_code_returns_401(self):
        app = _app("LoginEmailApp6")
        user = _user("loginemail6@test.com", "Pass123!")
        user.is_2fa_enabled = True
        user.save()

        with patch("tenxyte.views.auth_views.authenticate_by_email_with_core") as mock_auth, \
             patch("tenxyte.core.TOTPService.verify_2fa", return_value=(False, "Invalid code")):
            mock_auth.return_value = (True, {"_user": user, "requires_2fa": True}, "")
            resp = _post(LoginEmailView, "/auth/login/email/", {
                "email": "loginemail6@test.com",
                "password": "Pass123!",
                "totp_code": "000000",
            }, app)

        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_login_inactive_user_returns_401(self):
        app = _app("LoginEmailApp7")
        user = _user("loginemail7@test.com", "Pass123!")
        user.is_active = False
        user.save()

        resp = _post(LoginEmailView, "/auth/login/email/", {
            "email": "loginemail7@test.com",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 401


# ===========================================================================
# LoginPhoneView
# ===========================================================================

class TestLoginPhoneView:

    @pytest.mark.django_db
    def test_login_phone_success(self):
        app = _app("LoginPhoneApp1")
        user = User.objects.create(
            phone_country_code="33",
            phone_number="600000001",
            is_active=True
        )
        user.set_password("Pass123!")
        user.save()

        resp = _post(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "600000001",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 200
        assert "access_token" in resp.data

    @pytest.mark.django_db
    def test_login_phone_wrong_password_returns_401(self):
        app = _app("LoginPhoneApp2")
        user = User.objects.create(
            phone_country_code="33",
            phone_number="600000002",
            is_active=True
        )
        user.set_password("Pass123!")
        user.save()

        resp = _post(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "600000002",
            "password": "WrongPass!",
        }, app)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_login_phone_invalid_data_returns_400(self):
        app = _app("LoginPhoneApp3")
        resp = _post(LoginPhoneView, "/auth/login/phone/", {}, app)
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_login_phone_unknown_number_returns_401(self):
        app = _app("LoginPhoneApp4")
        resp = _post(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "699999999",
            "password": "Pass123!",
        }, app)
        assert resp.status_code == 401



# ===========================================================================
# RefreshTokenView
# ===========================================================================

class TestRefreshTokenView:

    @pytest.mark.django_db
    def test_refresh_success(self):
        app = _app("RefreshView1")
        user = _user("refreshview1@test.com")
        rt = _refresh_token(user, app)

        resp = _post(RefreshTokenView, "/auth/refresh/", {
            # R1: rt.token is SHA-256 hash in DB; API expects raw token value
            "refresh_token": rt._raw_token
        }, app)
        assert resp.status_code == 200
        assert "access_token" in resp.data

    @pytest.mark.django_db
    def test_refresh_invalid_token_returns_401(self):
        app = _app("RefreshView2")
        resp = _post(RefreshTokenView, "/auth/refresh/", {
            "refresh_token": "invalid-token-xyz"
        }, app)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_refresh_missing_token_returns_400(self):
        app = _app("RefreshView3")
        resp = _post(RefreshTokenView, "/auth/refresh/", {}, app)
        assert resp.status_code == 400


# ===========================================================================
# LogoutView
# ===========================================================================

class TestLogoutView:

    @pytest.mark.django_db
    def test_logout_success(self):
        app = _app("LogoutView1")
        user = _user("logoutview1@test.com")
        rt = _refresh_token(user, app)

        resp = _post(LogoutView, "/auth/logout/", {
            # R1: rt.token is SHA-256 hash in DB; API expects raw token value
            "refresh_token": rt._raw_token
        }, app)
        assert resp.status_code == 200
        assert "Logged out" in resp.data["message"]

    @pytest.mark.django_db
    def test_logout_invalid_token_still_200(self):
        app = _app("LogoutView2")
        # Logout is idempotent — invalid token doesn't crash
        resp = _post(LogoutView, "/auth/logout/", {
            "refresh_token": "bad-token"
        }, app)
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_logout_missing_token_returns_400(self):
        app = _app("LogoutView3")
        resp = _post(LogoutView, "/auth/logout/", {}, app)
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_logout_blacklists_access_token_from_header(self):
        app = _app("LogoutView4")
        user = _user("logoutview4@test.com")
        rt = _refresh_token(user, app)
        access_token = _jwt_token(user, app)

        with patch("tenxyte.core.jwt_service.JWTService.blacklist_token") as mock_blacklist:
            # Recreate post with the correct signature
            resp = _post(LogoutView, "/auth/logout/", {
                "refresh_token": getattr(rt, "token", getattr(rt, "_raw_token", "dummy"))
            }, app, access_token=access_token)

        # Blacklist should be called twice: once for refresh token (if JWT), and once for access token.
        # But for DB tokens, it's revoked in DB, so blacklist might only be called for access token.
        assert mock_blacklist.called
        # Check that access_token was blacklisted (or at least decode was attempted).
        # We can just verify it returned 200 indicating logout processed the access token header.
        assert resp.status_code == 200


# ===========================================================================
# LogoutAllView
# ===========================================================================

class TestLogoutAllView:

    @pytest.mark.django_db
    def test_logout_all_success(self):
        app = _app("LogoutAllView1")
        user = _user("logoutallview1@test.com")
        _refresh_token(user, app)
        _refresh_token(user, app)
        access_token = _jwt_token(user, app)

        factory = APIRequestFactory()
        req = factory.post(
            "/auth/logout/all/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        req.application = app
        req.user = user

        view = LogoutAllView.as_view()
        resp = view(req)

        assert resp.status_code == 200
        assert "devices" in resp.data["message"]

    @pytest.mark.django_db
    def test_logout_all_requires_jwt(self):
        app = _app("LogoutAllView2")
        factory = APIRequestFactory()
        req = factory.post("/auth/logout/all/")
        req.application = app

        view = LogoutAllView.as_view()
        resp = view(req)

        assert resp.status_code == 401
