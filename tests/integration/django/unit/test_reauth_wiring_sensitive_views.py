"""
Unit tests for reauthentication wiring across sensitive action views (task 12.6).

Validates Requirements 6.4, 6.5, 6.6:
  - 6.4: OTP_Reauth_Challenge accepted as alternative to current password for
         every Sensitive_Password_Action
  - 6.5: No valid proof → request rejected with REAUTH_REQUIRED
  - 6.6: Correct current password continues to be accepted (backward compat)

Views under test:
  - TwoFactorDisableView            (twofa_views.py, task 12.3)
  - request_account_deletion        (account_deletion_views.py, task 12.4)
  - cancel_account_deletion         (account_deletion_views.py, task 12.4)
  - export_user_data                (account_deletion_views.py, task 12.4)
  - DeleteAccountView.delete        (user_views.py, task 12.5)

For each view the three wiring scenarios are tested:
  1. Correct current password is accepted  (Req 6.6)
  2. Valid OTP_Reauth_Challenge is accepted  (Req 6.4)
  3. Neither provided → HTTP 400/401 with REAUTH_REQUIRED  (Req 6.5)
"""

import pytest
from unittest.mock import patch, MagicMock

from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.views.twofa_views import TwoFactorDisableView
from tenxyte.views.account_deletion_views import (
    request_account_deletion,
    cancel_account_deletion,
    export_user_data,
)
from tenxyte.views.user_views import DeleteAccountView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, password="Pass123!"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _user_with_phone(email, password="Pass123!"):
    u = User.objects.create(
        email=email,
        is_active=True,
        phone_country_code="33",
        phone_number="612345678",
    )
    u.set_password(password)
    u.save()
    return u


def _jwt_token(user, app):
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


def _generate_login_otp(user) -> str:
    """Generate a fresh Login_OTP_Code and return the raw code string."""
    otp_service = OTPService()
    _otp, raw_code = otp_service.generate_login_otp(user)
    return raw_code


def _authed_post_view(view_cls_or_fn, path, user, app, data=None, **view_kwargs):
    """Build an authenticated POST request and dispatch to the view."""
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.post(
        path,
        data=data or {},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    req.user = user
    req.application = app
    if hasattr(view_cls_or_fn, "as_view"):
        return view_cls_or_fn.as_view()(req, **view_kwargs)
    return view_cls_or_fn(req)


def _authed_delete_view(view_cls, path, user, app, data=None, **view_kwargs):
    """Build an authenticated DELETE request with a JSON body and dispatch."""
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.delete(
        path,
        data=data or {},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    req.user = user
    req.application = app
    return view_cls.as_view()(req, **view_kwargs)


# ===========================================================================
# TwoFactorDisableView — task 12.3
# ===========================================================================

class TestTwoFactorDisableReauthWiring:
    """
    TwoFactorDisableView.post calls ReauthService.verify before the TOTP check.
    The TOTP check itself is patched out so tests focus exclusively on the
    reauth layer.
    """

    # ------------------------------------------------------------------
    # Req 6.6 — correct password is accepted
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_correct_password_accepted(self):
        """Req 6.6: A correct current password lets the view proceed past reauth."""
        app = _app("TFADisable_Pw_App")
        user = _user("tfa_disable_pw@test.com")

        # Patch the TOTP disable to succeed so we reach the 200 response
        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_totp:
            mock_totp.return_value.disable_2fa.return_value = (True, "")
            resp = _authed_post_view(
                TwoFactorDisableView,
                "/auth/2fa/disable/",
                user,
                app,
                {"code": "123456", "password": "Pass123!"},
            )

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False

    # ------------------------------------------------------------------
    # Req 6.4 — valid OTP accepted as alternative
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_valid_otp_accepted(self):
        """Req 6.4: A valid Login_OTP_Code is accepted instead of a password."""
        app = _app("TFADisable_OTP_App")
        user = _user_with_phone("tfa_disable_otp@test.com")
        raw_code = _generate_login_otp(user)

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_totp:
            mock_totp.return_value.disable_2fa.return_value = (True, "")
            resp = _authed_post_view(
                TwoFactorDisableView,
                "/auth/2fa/disable/",
                user,
                app,
                {"code": "123456", "otp_code": raw_code},
            )

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False

    # ------------------------------------------------------------------
    # Req 6.5 — neither proof → REAUTH_REQUIRED
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_no_proof_returns_reauth_required(self):
        """Req 6.5: Providing neither password nor otp_code returns REAUTH_REQUIRED."""
        app = _app("TFADisable_NoProof_App")
        user = _user("tfa_disable_noproof@test.com")

        resp = _authed_post_view(
            TwoFactorDisableView,
            "/auth/2fa/disable/",
            user,
            app,
            {"code": "123456"},  # TOTP code present but no reauth proof
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "REAUTH_REQUIRED"


# ===========================================================================
# request_account_deletion — task 12.4
# ===========================================================================

class TestRequestAccountDeletionReauthWiring:
    """
    `request_account_deletion` checks for password or reauth_otp_code before
    delegating to AccountDeletionService (which itself calls ReauthService).
    """

    # ------------------------------------------------------------------
    # Req 6.6 — correct password is accepted
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_correct_password_accepted(self):
        """Req 6.6: A correct current password reaches AccountDeletionService."""
        app = _app("ReqDel_Pw_App")
        user = _user("req_del_pw@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                True, {"request_id": 1, "grace_period_days": 30, "message": "ok"}, ""
            )
            resp = _authed_post_view(
                request_account_deletion,
                "/request-deletion/",
                user,
                app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 201
        MockSvc.return_value.request_deletion.assert_called_once()

    # ------------------------------------------------------------------
    # Req 6.4 — valid OTP accepted as alternative (reauth_otp_code)
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_valid_otp_accepted(self):
        """Req 6.4: A reauth_otp_code bypasses the password requirement."""
        app = _app("ReqDel_OTP_App")
        user = _user_with_phone("req_del_otp@test.com")
        raw_code = _generate_login_otp(user)

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                True, {"request_id": 2, "grace_period_days": 30, "message": "ok"}, ""
            )
            resp = _authed_post_view(
                request_account_deletion,
                "/request-deletion/",
                user,
                app,
                {"reauth_otp_code": raw_code},
            )

        assert resp.status_code == 201
        MockSvc.return_value.request_deletion.assert_called_once()

    # ------------------------------------------------------------------
    # Req 6.5 — neither proof → REAUTH_REQUIRED
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_no_proof_returns_reauth_required(self):
        """Req 6.5: No password and no reauth_otp_code returns REAUTH_REQUIRED before service."""
        app = _app("ReqDel_NoProof_App")
        user = _user("req_del_noproof@test.com")

        resp = _authed_post_view(
            request_account_deletion,
            "/request-deletion/",
            user,
            app,
            {},  # empty body
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "REAUTH_REQUIRED"


# ===========================================================================
# cancel_account_deletion — task 12.4
# ===========================================================================

class TestCancelAccountDeletionReauthWiring:

    # ------------------------------------------------------------------
    # Req 6.6 — correct password is accepted
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_correct_password_accepted(self):
        """Req 6.6: A correct current password reaches AccountDeletionService."""
        app = _app("CancelDel_Pw_App")
        user = _user("cancel_del_pw@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                True, {"cancelled_count": 1, "message": "Cancelled 1 deletion request(s)."}, ""
            )
            resp = _authed_post_view(
                cancel_account_deletion,
                "/cancel-deletion/",
                user,
                app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        MockSvc.return_value.cancel_deletion.assert_called_once()

    # ------------------------------------------------------------------
    # Req 6.4 — valid OTP accepted as alternative (otp_code)
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_valid_otp_accepted(self):
        """Req 6.4: An otp_code bypasses the password requirement."""
        app = _app("CancelDel_OTP_App")
        user = _user_with_phone("cancel_del_otp@test.com")
        raw_code = _generate_login_otp(user)

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                True, {"cancelled_count": 1, "message": "Cancelled 1 deletion request(s)."}, ""
            )
            resp = _authed_post_view(
                cancel_account_deletion,
                "/cancel-deletion/",
                user,
                app,
                {"otp_code": raw_code},
            )

        assert resp.status_code == 200
        MockSvc.return_value.cancel_deletion.assert_called_once()

    # ------------------------------------------------------------------
    # Req 6.5 — neither proof → REAUTH_REQUIRED
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_no_proof_returns_reauth_required(self):
        """Req 6.5: No password and no otp_code returns REAUTH_REQUIRED."""
        app = _app("CancelDel_NoProof_App")
        user = _user("cancel_del_noproof@test.com")

        resp = _authed_post_view(
            cancel_account_deletion,
            "/cancel-deletion/",
            user,
            app,
            {},
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "REAUTH_REQUIRED"


# ===========================================================================
# export_user_data — task 12.4
# ===========================================================================

class TestExportUserDataReauthWiring:
    """
    `export_user_data` calls ReauthService.verify directly before building the
    export payload.
    """

    # ------------------------------------------------------------------
    # Req 6.6 — correct password is accepted
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_correct_password_accepted(self):
        """Req 6.6: A correct current password passes the reauth gate."""
        app = _app("Export_Pw_App")
        user = _user("export_pw@test.com")

        resp = _authed_post_view(
            export_user_data,
            "/export-user-data/",
            user,
            app,
            {"password": "Pass123!"},
        )

        # 200 means reauth passed; export may partially fail on missing relations
        # but the response code should not be 400 with REAUTH_REQUIRED
        assert resp.status_code != 400 or resp.data.get("code") != "REAUTH_REQUIRED"
        # In the clean DB the export reaches 200
        assert resp.status_code == 200
        assert "user_info" in resp.data

    # ------------------------------------------------------------------
    # Req 6.4 — valid OTP accepted as alternative
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_valid_otp_accepted(self):
        """Req 6.4: A valid Login_OTP_Code is accepted instead of a password."""
        app = _app("Export_OTP_App")
        user = _user_with_phone("export_otp@test.com")
        raw_code = _generate_login_otp(user)

        resp = _authed_post_view(
            export_user_data,
            "/export-user-data/",
            user,
            app,
            {"otp_code": raw_code},
        )

        assert resp.status_code == 200
        assert "user_info" in resp.data

    # ------------------------------------------------------------------
    # Req 6.5 — neither proof → REAUTH_REQUIRED
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_no_proof_returns_reauth_required(self):
        """Req 6.5: No password and no otp_code returns REAUTH_REQUIRED."""
        app = _app("Export_NoProof_App")
        user = _user("export_noproof@test.com")

        resp = _authed_post_view(
            export_user_data,
            "/export-user-data/",
            user,
            app,
            {},
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "REAUTH_REQUIRED"


# ===========================================================================
# DeleteAccountView.delete — task 12.5
# ===========================================================================

class TestDeleteAccountViewReauthWiring:
    """
    DeleteAccountView.delete calls ReauthService.verify after the confirmation
    string check.  We patch soft_delete / org checks so the test focuses only
    on the reauth layer.
    """

    # ------------------------------------------------------------------
    # Req 6.6 — correct password is accepted
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_correct_password_accepted(self):
        """Req 6.6: A correct current password passes the reauth gate."""
        app = _app("DelAccount_Pw_App")
        user = _user("del_account_pw@test.com")

        # Patch org-ownership check (downstream of reauth) and soft_delete so we
        # reach the 200 response without hitting DB org queries.
        with patch("tenxyte.views.user_views.get_core_user_repo") as mock_repo, \
             patch.object(user.__class__, "get_owned_organizations", return_value=[], create=True):
            mock_repo.return_value.soft_delete.return_value = None

            resp = _authed_delete_view(
                DeleteAccountView,
                "/auth/me/",
                user,
                app,
                {"confirmation": "DELETE MY ACCOUNT", "password": "Pass123!"},
            )

        # Reauth passes, then soft_delete is called → 200
        assert resp.status_code == 200
        assert resp.data["account_deleted"] is True

    # ------------------------------------------------------------------
    # Req 6.4 — valid OTP accepted as alternative
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_valid_otp_accepted(self):
        """Req 6.4: A valid Login_OTP_Code is accepted instead of a password."""
        app = _app("DelAccount_OTP_App")
        user = _user_with_phone("del_account_otp@test.com")
        raw_code = _generate_login_otp(user)

        with patch("tenxyte.views.user_views.get_core_user_repo") as mock_repo, \
             patch.object(user.__class__, "get_owned_organizations", return_value=[], create=True):
            mock_repo.return_value.soft_delete.return_value = None

            resp = _authed_delete_view(
                DeleteAccountView,
                "/auth/me/",
                user,
                app,
                {"confirmation": "DELETE MY ACCOUNT", "otp_code": raw_code},
            )

        assert resp.status_code == 200
        assert resp.data["account_deleted"] is True

    # ------------------------------------------------------------------
    # Req 6.5 — neither proof → REAUTH_REQUIRED
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_no_proof_returns_reauth_required(self):
        """Req 6.5: No password and no otp_code returns REAUTH_REQUIRED."""
        app = _app("DelAccount_NoProof_App")
        user = _user("del_account_noproof@test.com")

        resp = _authed_delete_view(
            DeleteAccountView,
            "/auth/me/",
            user,
            app,
            {"confirmation": "DELETE MY ACCOUNT"},
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "REAUTH_REQUIRED"

    # ------------------------------------------------------------------
    # Missing confirmation string — baseline guard (not a reauth test)
    # ------------------------------------------------------------------
    @pytest.mark.django_db
    def test_missing_confirmation_returns_confirmation_required(self):
        """The confirmation guard runs before reauth; verify it still works."""
        app = _app("DelAccount_NoConf_App")
        user = _user("del_account_noconf@test.com")

        resp = _authed_delete_view(
            DeleteAccountView,
            "/auth/me/",
            user,
            app,
            {"password": "Pass123!"},
        )

        assert resp.status_code == 400
        assert resp.data["code"] == "CONFIRMATION_REQUIRED"
