"""
Tests for auth_views.py — coverage for new security remediation code:
cookie helpers, phone registration duplicate, RefreshToken cookie fallback,
logout cookie clearing, LogoutAll exception path.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

from tenxyte.models import User, Application, RefreshToken
from tenxyte.views.auth_views import (
    _set_refresh_cookie,
    _clear_refresh_cookie,
    validate_application_required,
    get_application_from_request,
    RegisterView,
    RefreshTokenView,
    LogoutView,
    LogoutAllView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="CoverageApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, password="TestPass123!"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _post(view_cls, path, data, app, user=None, access_token=None, cookies=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.post(path, data=data, format="json", **headers)
    req.application = app
    if user:
        req.user = user
    if cookies:
        req.COOKIES = cookies
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = view_cls.as_view()
        return view(req)


def _refresh_token(user, app):
    return RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4")


def _jwt_token(user, app):
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


# ===========================================================================
# get_application_from_request (line 95)
# ===========================================================================

class TestGetApplicationFromRequest:

    def test_returns_application(self):
        req = MagicMock()
        req.application = "my_app"
        assert get_application_from_request(req) == "my_app"

    def test_returns_none_when_missing(self):
        req = MagicMock(spec=[])
        assert get_application_from_request(req) is None


# ===========================================================================
# _set_refresh_cookie (lines 100-111)
# ===========================================================================

class TestSetRefreshCookie:

    def test_noop_when_disabled(self):
        """Returns response unchanged when cookie mode disabled (default)."""
        response = Response({"data": "ok"})
        result = _set_refresh_cookie(response, "token")
        assert result is response

    @pytest.mark.django_db
    def test_sets_cookie_when_enabled(self):
        """Sets HttpOnly cookie with correct params when enabled."""
        response = Response({"data": "ok"})
        with patch("tenxyte.views.auth_views.auth_settings") as ms, \
             patch("tenxyte.views.auth_views.get_core_settings") as mc:
            ms.REFRESH_TOKEN_COOKIE_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_NAME = "rt"
            ms.REFRESH_TOKEN_COOKIE_SAMESITE = "Lax"
            ms.REFRESH_TOKEN_COOKIE_PATH = "/api/"
            mc.return_value.jwt_refresh_token_lifetime = 604800
            result = _set_refresh_cookie(response, "my_token")

        assert "rt" in result.cookies
        assert result.cookies["rt"].value == "my_token"


# ===========================================================================
# _clear_refresh_cookie (lines 118-123)
# ===========================================================================

class TestClearRefreshCookie:

    def test_noop_when_disabled(self):
        response = Response({"data": "ok"})
        result = _clear_refresh_cookie(response)
        assert result is response

    @pytest.mark.django_db
    def test_deletes_cookie_when_enabled(self):
        response = Response({"data": "ok"})
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.REFRESH_TOKEN_COOKIE_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_NAME = "rt"
            ms.REFRESH_TOKEN_COOKIE_SAMESITE = "Lax"
            ms.REFRESH_TOKEN_COOKIE_PATH = "/api/"
            result = _clear_refresh_cookie(response)
        assert "rt" in result.cookies


# ===========================================================================
# validate_application_required (lines 128-130)
# ===========================================================================

class TestValidateApplicationRequired:

    @pytest.mark.django_db
    def test_returns_401_when_required_and_missing(self):
        req = MagicMock(spec=[])
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = True
            result = validate_application_required(req)
        assert result is not None
        assert result.status_code == 401

    @pytest.mark.django_db
    def test_returns_none_when_disabled(self):
        req = MagicMock()
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = False
            result = validate_application_required(req)
        assert result is None


# ===========================================================================
# RegisterView — phone duplicate (lines 161-167)
# ===========================================================================

class TestRegisterPhoneDuplicate:

    @pytest.mark.django_db
    def test_duplicate_phone_returns_201(self):
        """Duplicate phone → anti-enumeration 201."""
        app = _app("RegPhoneDup")
        u = User.objects.create(
            email="phone_orig@test.com", phone_country_code="33",
            phone_number="612345678", is_active=True,
        )
        u.set_password("TestPass123!")
        u.save()
        resp = _post(RegisterView, "/auth/register/", {
            "email": "phone_new@test.com", "password": "TestPass123!",
            "phone_country_code": "33", "phone_number": "612345678",
        }, app)
        assert resp.status_code == 201


# ===========================================================================
# RefreshTokenView — app auth + cookie fallback (lines 1062, 1075, 1077)
# ===========================================================================

class TestRefreshTokenCoverage:

    @pytest.mark.django_db
    def test_app_auth_required_401(self):
        """Returns 401 when app auth required but no application."""
        factory = APIRequestFactory()
        req = factory.post("/auth/refresh/", {"refresh_token": "x"}, format="json")
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_ENABLED = False
            with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
                resp = RefreshTokenView.as_view()(req)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_reads_from_cookie(self):
        """Cookie fallback when body empty (line 1075)."""
        app = _app("RefCookie1")
        user = _user("refcookie@test.com")
        rt = _refresh_token(user, app)

        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_NAME = "rt"
            ms.REFRESH_TOKEN_COOKIE_SAMESITE = "Lax"
            ms.REFRESH_TOKEN_COOKIE_PATH = "/api/"
            resp = _post(RefreshTokenView, "/auth/refresh/",
                         {"refresh_token": ""}, app,
                         cookies={"rt": rt._raw_token})
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_missing_token_400(self):
        """No token anywhere → 400 MISSING_REFRESH_TOKEN (line 1077)."""
        app = _app("RefCookie2")
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = False
            ms.REFRESH_TOKEN_COOKIE_ENABLED = False
            resp = _post(RefreshTokenView, "/auth/refresh/",
                         {"refresh_token": ""}, app)
        assert resp.status_code == 400
        assert resp.data["code"] == "MISSING_REFRESH_TOKEN"


# ===========================================================================
# LogoutView — cookie + exception (lines 1195-1196, 1216-1217)
# ===========================================================================

class TestLogoutCoverage:

    @pytest.mark.django_db
    def test_clears_cookie(self):
        app = _app("LogoutCk1")
        user = _user("logoutck@test.com")
        rt = _refresh_token(user, app)
        with patch("tenxyte.views.auth_views.auth_settings") as ms:
            ms.APPLICATION_AUTH_ENABLED = False
            ms.REFRESH_TOKEN_COOKIE_ENABLED = True
            ms.REFRESH_TOKEN_COOKIE_NAME = "rt"
            ms.REFRESH_TOKEN_COOKIE_SAMESITE = "Lax"
            ms.REFRESH_TOKEN_COOKIE_PATH = "/api/"
            resp = _post(LogoutView, "/auth/logout/",
                         {"refresh_token": rt._raw_token}, app)
        assert resp.status_code == 200
        assert "rt" in resp.cookies

    @pytest.mark.django_db
    def test_access_token_blacklist_exception(self):
        """Exception blacklisting access token is swallowed (L1216-1217)."""
        app = _app("LogoutExc1")
        user = _user("logoutexc@test.com")
        rt = _refresh_token(user, app)
        access_token = _jwt_token(user, app)
        with patch("tenxyte.core.jwt_service.JWTService.blacklist_token",
                    side_effect=Exception("boom")):
            resp = _post(LogoutView, "/auth/logout/",
                         {"refresh_token": rt._raw_token}, app,
                         access_token=access_token)
        assert resp.status_code == 200


# ===========================================================================
# LogoutAllView — exception (line 1294)
# ===========================================================================

class TestLogoutAllCoverage:

    @pytest.mark.django_db
    def test_revoke_exception_swallowed(self):
        app = _app("LAExc1")
        user = _user("laexc@test.com")
        access_token = _jwt_token(user, app)

        factory = APIRequestFactory()
        req = factory.post("/auth/logout/all/",
                           HTTP_AUTHORIZATION=f"Bearer {access_token}")
        req.application = app
        req.user = user

        with patch("tenxyte.models.RefreshToken.objects") as mqs:
            mqs.filter.side_effect = Exception("DB error")
            resp = LogoutAllView.as_view()(req)
        assert resp.status_code == 200
