"""
Tests twofa_views.py — TwoFactorStatusView, TwoFactorSetupView,
TwoFactorConfirmView, TwoFactorDisableView, TwoFactorBackupCodesView.

Coverage cible : views/twofa_views.py (46% → 80%)
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application
from tenxyte.core.totp_service import TOTPSetupResult
from tenxyte.views.twofa_views import (
    TwoFactorStatusView, TwoFactorSetupView, TwoFactorConfirmView,
    TwoFactorDisableView, TwoFactorBackupCodesView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="TwoFAApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, twofa=False):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.is_2fa_enabled = twofa
    u.save()
    return u


def _jwt_token(user, app):
    from tenxyte.services.jwt_service import JWTService
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]


def _authed_get(view_cls, path, user, app):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req)


def _authed_post(view_cls, path, user, app, data=None):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.post(path, data=data or {}, format="json",
                       HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req)


def _unauthed_post(view_cls, path, app, data=None):
    factory = APIRequestFactory()
    req = factory.post(path, data=data or {}, format="json")
    req.application = app
    return view_cls.as_view()(req)


# ===========================================================================
# TwoFactorStatusView
# ===========================================================================

class TestTwoFactorStatusView:

    @pytest.mark.django_db
    def test_status_2fa_disabled(self):
        app = _app("2FAStatus1")
        user = _user("status2fa1@test.com", twofa=False)

        resp = _authed_get(TwoFactorStatusView, "/auth/2fa/status/", user, app)

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False
        assert resp.data["backup_codes_remaining"] == 0

    @pytest.mark.django_db
    def test_status_2fa_enabled_with_backup_codes(self):
        app = _app("2FAStatus2")
        user = _user("status2fa2@test.com", twofa=True)
        user.backup_codes = ["code1", "code2", "code3"]
        user.save()

        resp = _authed_get(TwoFactorStatusView, "/auth/2fa/status/", user, app)

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is True
        assert resp.data["backup_codes_remaining"] == 3

    @pytest.mark.django_db
    def test_status_requires_jwt(self):
        app = _app("2FAStatus3")
        factory = APIRequestFactory()
        req = factory.get("/auth/2fa/status/")
        req.application = app
        resp = TwoFactorStatusView.as_view()(req)
        assert resp.status_code == 401


# ===========================================================================
# TwoFactorSetupView
# ===========================================================================

class TestTwoFactorSetupView:

    @pytest.mark.django_db
    def test_setup_returns_secret_and_qr(self):
        app = _app("2FASetup1")
        user = _user("setup2fa1@test.com", twofa=False)

        setup_data = TOTPSetupResult(
            secret="JBSWY3DPEHPK3PXP",
            qr_code="data:image/png;base64,abc",
            provisioning_uri="otpauth://totp/...",
            backup_codes=["code1", "code2"],
        )
        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.setup_2fa.return_value = setup_data
            resp = _authed_post(TwoFactorSetupView, "/auth/2fa/setup/", user, app)

        assert resp.status_code == 200
        assert "secret" in resp.data
        assert "qr_code" in resp.data
        assert "backup_codes" in resp.data

    @pytest.mark.django_db
    def test_setup_already_enabled_returns_400(self):
        app = _app("2FASetup2")
        user = _user("setup2fa2@test.com", twofa=True)

        resp = _authed_post(TwoFactorSetupView, "/auth/2fa/setup/", user, app)

        assert resp.status_code == 400
        assert resp.data["code"] == "2FA_ALREADY_ENABLED"

    @pytest.mark.django_db
    def test_setup_requires_jwt(self):
        app = _app("2FASetup3")
        resp = _unauthed_post(TwoFactorSetupView, "/auth/2fa/setup/", app)
        assert resp.status_code == 401


# ===========================================================================
# TwoFactorConfirmView
# ===========================================================================

class TestTwoFactorConfirmView:

    @pytest.mark.django_db
    def test_confirm_success(self):
        app = _app("2FAConfirm1")
        user = _user("confirm2fa1@test.com", twofa=False)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.confirm_2fa_setup.return_value = (True, "")
            resp = _authed_post(TwoFactorConfirmView, "/auth/2fa/confirm/", user, app,
                                {"code": "123456"})

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is True

    @pytest.mark.django_db
    def test_confirm_invalid_code_returns_400(self):
        app = _app("2FAConfirm2")
        user = _user("confirm2fa2@test.com", twofa=False)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.confirm_2fa_setup.return_value = (False, "Invalid TOTP code")
            resp = _authed_post(TwoFactorConfirmView, "/auth/2fa/confirm/", user, app,
                                {"code": "000000"})

        assert resp.status_code == 400
        assert resp.data["code"] == "INVALID_CODE"

    @pytest.mark.django_db
    def test_confirm_missing_code_returns_400(self):
        app = _app("2FAConfirm3")
        user = _user("confirm2fa3@test.com", twofa=False)

        resp = _authed_post(TwoFactorConfirmView, "/auth/2fa/confirm/", user, app, {})
        assert resp.status_code == 400
        assert resp.data["code"] == "CODE_REQUIRED"

    @pytest.mark.django_db
    def test_confirm_requires_jwt(self):
        app = _app("2FAConfirm4")
        resp = _unauthed_post(TwoFactorConfirmView, "/auth/2fa/confirm/", app, {"code": "123456"})
        assert resp.status_code == 401


# ===========================================================================
# TwoFactorDisableView
# ===========================================================================

class TestTwoFactorDisableView:

    @pytest.mark.django_db
    def test_disable_success(self):
        app = _app("2FADisable1")
        user = _user("disable2fa1@test.com", twofa=True)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.disable_2fa.return_value = (True, "")
            resp = _authed_post(TwoFactorDisableView, "/auth/2fa/disable/", user, app,
                                {"code": "123456"})

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False

    @pytest.mark.django_db
    def test_disable_invalid_code_returns_400(self):
        app = _app("2FADisable2")
        user = _user("disable2fa2@test.com", twofa=True)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.disable_2fa.return_value = (False, "Invalid code")
            resp = _authed_post(TwoFactorDisableView, "/auth/2fa/disable/", user, app,
                                {"code": "000000"})

        assert resp.status_code == 400
        assert resp.data["code"] == "INVALID_CODE"

    @pytest.mark.django_db
    def test_disable_missing_code_returns_400(self):
        app = _app("2FADisable3")
        user = _user("disable2fa3@test.com", twofa=True)

        resp = _authed_post(TwoFactorDisableView, "/auth/2fa/disable/", user, app, {})
        assert resp.status_code == 400
        assert resp.data["code"] == "CODE_REQUIRED"

    @pytest.mark.django_db
    def test_disable_requires_jwt(self):
        app = _app("2FADisable4")
        resp = _unauthed_post(TwoFactorDisableView, "/auth/2fa/disable/", app, {"code": "123456"})
        assert resp.status_code == 401


# ===========================================================================
# TwoFactorBackupCodesView
# ===========================================================================

class TestTwoFactorBackupCodesView:

    @pytest.mark.django_db
    def test_regenerate_backup_codes_success(self):
        app = _app("2FABackup1")
        user = _user("backup2fa1@test.com", twofa=True)
        new_codes = ["new1", "new2", "new3", "new4", "new5"]

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.regenerate_backup_codes.return_value = (True, new_codes, "")
            resp = _authed_post(TwoFactorBackupCodesView, "/auth/2fa/backup-codes/", user, app,
                                {"code": "123456"})

        assert resp.status_code == 200
        assert resp.data["backup_codes"] == new_codes
        assert "warning" in resp.data

    @pytest.mark.django_db
    def test_regenerate_invalid_code_returns_400(self):
        app = _app("2FABackup2")
        user = _user("backup2fa2@test.com", twofa=True)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.regenerate_backup_codes.return_value = (False, None, "Invalid TOTP")
            resp = _authed_post(TwoFactorBackupCodesView, "/auth/2fa/backup-codes/", user, app,
                                {"code": "000000"})

        assert resp.status_code == 400
        assert resp.data["code"] == "INVALID_CODE"

    @pytest.mark.django_db
    def test_regenerate_missing_code_returns_400(self):
        app = _app("2FABackup3")
        user = _user("backup2fa3@test.com", twofa=True)

        resp = _authed_post(TwoFactorBackupCodesView, "/auth/2fa/backup-codes/", user, app, {})
        assert resp.status_code == 400
        assert resp.data["code"] == "CODE_REQUIRED"

    @pytest.mark.django_db
    def test_regenerate_requires_jwt(self):
        app = _app("2FABackup4")
        resp = _unauthed_post(TwoFactorBackupCodesView, "/auth/2fa/backup-codes/", app,
                              {"code": "123456"})
        assert resp.status_code == 401
