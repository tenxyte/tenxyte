"""
Task 14.1 — Snapshot tests freezing documented response shapes of existing endpoints.

Fige la forme des réponses de :
  - POST /register/                    (RegisterView)
  - POST /login/email/                 (LoginEmailView)
  - POST /login/phone/                 (LoginPhoneView)
  - POST /password/change/             (ChangePasswordView)
  - POST /2fa/disable/                 (TwoFactorDisableView)
  - POST /request-deletion/            (request_account_deletion)
  - POST /cancel-deletion/             (cancel_account_deletion)
  - POST /export-user-data/            (export_user_data)

Garantit qu'aucun champ documenté n'a été retiré (backward-compat, Req 8.1, 8.2, 8.3).
Tous les tests utilisent des données déterministes (pas de Hypothesis).
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application
from tenxyte.views.auth_views import RegisterView, LoginEmailView, LoginPhoneView
from tenxyte.views.password_views import ChangePasswordView
from tenxyte.views.twofa_views import TwoFactorDisableView
from tenxyte.views.account_deletion_views import (
    request_account_deletion,
    cancel_account_deletion,
    export_user_data,
)


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


def _phone_user(country_code, phone_number, password="Pass123!"):
    u = User.objects.create(
        phone_country_code=country_code,
        phone_number=phone_number,
        is_active=True,
    )
    u.set_password(password)
    u.save()
    return u


def _jwt_token(user, app):
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


def _post_anon(view_cls_or_fn, path, data, app):
    """POST request without JWT, with throttle bypass."""
    factory = APIRequestFactory()
    req = factory.post(path, data=data, format="json")
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        if callable(view_cls_or_fn) and hasattr(view_cls_or_fn, "as_view"):
            return view_cls_or_fn.as_view()(req)
        else:
            return view_cls_or_fn(req)


def _post_authed(view_cls_or_fn, path, user, app, data):
    """POST request with JWT bearer token, with throttle bypass."""
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.post(
        path, data=data, format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    req.application = app
    req.user = user
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        if callable(view_cls_or_fn) and hasattr(view_cls_or_fn, "as_view"):
            return view_cls_or_fn.as_view()(req)
        else:
            return view_cls_or_fn(req)


# ===========================================================================
# 1. RegisterView — POST /register/
# ===========================================================================

REGISTER_REQUIRED_FIELDS = {"message", "user", "verification_required"}

# Sub-fields of the `user` object (documented in OpenAPI schema)
REGISTER_USER_FIELDS = {
    "id",
    "email",
    "is_email_verified",
    "is_phone_verified",
    "is_2fa_enabled",
}


class TestRegisterViewResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /register/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_documented_top_level_fields(self):
        app = _app("SnapRegApp1")
        resp = _post_anon(RegisterView, "/auth/register/", {
            "email": "snap_reg_1@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 201
        for field in REGISTER_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /register/ success response"
            )

    @pytest.mark.django_db
    def test_success_response_user_object_has_documented_fields(self):
        app = _app("SnapRegApp2")
        resp = _post_anon(RegisterView, "/auth/register/", {
            "email": "snap_reg_2@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 201
        user_data = resp.data["user"]
        for field in REGISTER_USER_FIELDS:
            assert field in user_data, (
                f"User field '{field}' missing from /register/ success response"
            )

    @pytest.mark.django_db
    def test_success_with_login_returns_token_fields(self):
        """When login=True, response must also contain token fields (documented)."""
        app = _app("SnapRegApp3")
        resp = _post_anon(RegisterView, "/auth/register/", {
            "email": "snap_reg_3@test.com",
            "password": "Pass123!",
            "login": True,
        }, app)

        assert resp.status_code == 201
        for field in ("access_token", "token_type", "expires_in"):
            assert field in resp.data, (
                f"Token field '{field}' missing from /register/?login=true success response"
            )

    @pytest.mark.django_db
    def test_verification_required_has_email_and_phone_flags(self):
        app = _app("SnapRegApp4")
        resp = _post_anon(RegisterView, "/auth/register/", {
            "email": "snap_reg_4@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 201
        vr = resp.data["verification_required"]
        assert "email" in vr, "'email' key missing from verification_required"
        assert "phone" in vr, "'phone' key missing from verification_required"


# ===========================================================================
# 2. LoginEmailView — POST /login/email/
# ===========================================================================

LOGIN_EMAIL_REQUIRED_FIELDS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "refresh_expires_in",
    "user",
    "requires_2fa",
    "session_id",
    "device_id",
}


class TestLoginEmailViewResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /login/email/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapLoginEmailApp1")
        _user("snap_login_email_1@test.com", "Pass123!")

        resp = _post_anon(LoginEmailView, "/auth/login/email/", {
            "email": "snap_login_email_1@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 200
        for field in LOGIN_EMAIL_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /login/email/ success response"
            )

    @pytest.mark.django_db
    def test_token_type_is_bearer(self):
        app = _app("SnapLoginEmailApp2")
        _user("snap_login_email_2@test.com", "Pass123!")

        resp = _post_anon(LoginEmailView, "/auth/login/email/", {
            "email": "snap_login_email_2@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 200
        assert resp.data["token_type"] == "Bearer"

    @pytest.mark.django_db
    def test_user_subobject_present_and_non_null(self):
        app = _app("SnapLoginEmailApp3")
        _user("snap_login_email_3@test.com", "Pass123!")

        resp = _post_anon(LoginEmailView, "/auth/login/email/", {
            "email": "snap_login_email_3@test.com",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 200
        assert resp.data["user"] is not None


# ===========================================================================
# 3. LoginPhoneView — POST /login/phone/
# ===========================================================================

LOGIN_PHONE_REQUIRED_FIELDS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "refresh_expires_in",
    "user",
    "requires_2fa",
    "session_id",
    "device_id",
}


class TestLoginPhoneViewResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /login/phone/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapLoginPhoneApp1")
        _phone_user("33", "620000001", "Pass123!")

        resp = _post_anon(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "620000001",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 200
        for field in LOGIN_PHONE_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /login/phone/ success response"
            )

    @pytest.mark.django_db
    def test_token_type_is_bearer(self):
        app = _app("SnapLoginPhoneApp2")
        _phone_user("33", "620000002", "Pass123!")

        resp = _post_anon(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "620000002",
            "password": "Pass123!",
        }, app)

        assert resp.status_code == 200
        assert resp.data["token_type"] == "Bearer"

    @pytest.mark.django_db
    def test_login_email_and_phone_response_shapes_are_identical(self):
        """
        /login/email/ and /login/phone/ must return the same set of keys.
        Documenting this cross-endpoint invariant preserves backward-compat.
        """
        app = _app("SnapLoginCrossApp")
        _user("snap_login_cross_email@test.com", "Pass123!")
        _phone_user("33", "620000010", "Pass123!")

        resp_email = _post_anon(LoginEmailView, "/auth/login/email/", {
            "email": "snap_login_cross_email@test.com",
            "password": "Pass123!",
        }, app)
        resp_phone = _post_anon(LoginPhoneView, "/auth/login/phone/", {
            "phone_country_code": "33",
            "phone_number": "620000010",
            "password": "Pass123!",
        }, app)

        assert resp_email.status_code == 200
        assert resp_phone.status_code == 200

        assert set(resp_email.data.keys()) == set(resp_phone.data.keys()), (
            "Response key sets of /login/email/ and /login/phone/ must be identical. "
            f"email-only={set(resp_email.data.keys()) - set(resp_phone.data.keys())}, "
            f"phone-only={set(resp_phone.data.keys()) - set(resp_email.data.keys())}"
        )


# ===========================================================================
# 4. ChangePasswordView — POST /password/change/
# ===========================================================================

CHANGE_PASSWORD_REQUIRED_FIELDS = {"message", "password_strength", "sessions_revoked"}


class TestChangePasswordViewResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /password/change/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapChangePwApp1")
        user = _user("snap_changepw_1@test.com", "OldPass123!")

        resp = _post_authed(ChangePasswordView, "/auth/password/change/", user, app, {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        })

        assert resp.status_code == 200
        for field in CHANGE_PASSWORD_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /password/change/ success response"
            )

    @pytest.mark.django_db
    def test_success_response_sessions_revoked_is_integer(self):
        app = _app("SnapChangePwApp2")
        user = _user("snap_changepw_2@test.com", "OldPass123!")

        resp = _post_authed(ChangePasswordView, "/auth/password/change/", user, app, {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        })

        assert resp.status_code == 200
        assert isinstance(resp.data["sessions_revoked"], int)

    @pytest.mark.django_db
    def test_success_response_message_is_non_empty_string(self):
        app = _app("SnapChangePwApp3")
        user = _user("snap_changepw_3@test.com", "OldPass123!")

        resp = _post_authed(ChangePasswordView, "/auth/password/change/", user, app, {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        })

        assert resp.status_code == 200
        assert isinstance(resp.data["message"], str)
        assert len(resp.data["message"]) > 0


# ===========================================================================
# 5. TwoFactorDisableView — POST /2fa/disable/
# ===========================================================================

TWOFA_DISABLE_REQUIRED_FIELDS = {"message", "is_enabled"}


class TestTwoFactorDisableViewResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /2fa/disable/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapDisable2FAApp1")
        user = _user("snap_disable2fa_1@test.com", "Pass123!")
        user.is_2fa_enabled = True
        user.save()

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.disable_2fa.return_value = (True, "")
            resp = _post_authed(TwoFactorDisableView, "/auth/2fa/disable/", user, app, {
                "code": "123456",
                "password": "Pass123!",
            })

        assert resp.status_code == 200
        for field in TWOFA_DISABLE_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /2fa/disable/ success response"
            )

    @pytest.mark.django_db
    def test_is_enabled_is_false_after_disable(self):
        app = _app("SnapDisable2FAApp2")
        user = _user("snap_disable2fa_2@test.com", "Pass123!")
        user.is_2fa_enabled = True
        user.save()

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.disable_2fa.return_value = (True, "")
            resp = _post_authed(TwoFactorDisableView, "/auth/2fa/disable/", user, app, {
                "code": "123456",
                "password": "Pass123!",
            })

        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False

    @pytest.mark.django_db
    def test_message_is_non_empty_string(self):
        app = _app("SnapDisable2FAApp3")
        user = _user("snap_disable2fa_3@test.com", "Pass123!")
        user.is_2fa_enabled = True
        user.save()

        with patch("tenxyte.views.twofa_views.get_core_totp_service") as mock_svc:
            mock_svc.return_value.disable_2fa.return_value = (True, "")
            resp = _post_authed(TwoFactorDisableView, "/auth/2fa/disable/", user, app, {
                "code": "123456",
                "password": "Pass123!",
            })

        assert resp.status_code == 200
        assert isinstance(resp.data["message"], str)
        assert len(resp.data["message"]) > 0


# ===========================================================================
# 6a. request_account_deletion — POST /request-deletion/
# ===========================================================================

REQUEST_DELETION_REQUIRED_FIELDS = {"request_id", "message", "grace_period_days"}


class TestRequestAccountDeletionResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /request-deletion/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapReqDelApp1")
        user = _user("snap_req_del_1@test.com", "Pass123!")

        with patch(
            "tenxyte.views.account_deletion_views.AccountDeletionService"
        ) as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                True,
                {
                    "request_id": 1,
                    "message": "Deletion request created.",
                    "grace_period_days": 30,
                },
                "",
            )
            resp = _post_authed(
                request_account_deletion, "/auth/request-deletion/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 201
        for field in REQUEST_DELETION_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /request-deletion/ success response"
            )

    @pytest.mark.django_db
    def test_grace_period_days_is_integer(self):
        app = _app("SnapReqDelApp2")
        user = _user("snap_req_del_2@test.com", "Pass123!")

        with patch(
            "tenxyte.views.account_deletion_views.AccountDeletionService"
        ) as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                True,
                {
                    "request_id": 2,
                    "message": "Deletion request created.",
                    "grace_period_days": 30,
                },
                "",
            )
            resp = _post_authed(
                request_account_deletion, "/auth/request-deletion/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 201
        assert isinstance(resp.data["grace_period_days"], int)


# ===========================================================================
# 6b. cancel_account_deletion — POST /cancel-deletion/
# ===========================================================================

CANCEL_DELETION_REQUIRED_FIELDS = {"message", "cancelled_count"}


class TestCancelAccountDeletionResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /cancel-deletion/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_all_documented_fields(self):
        app = _app("SnapCancelDelApp1")
        user = _user("snap_cancel_del_1@test.com", "Pass123!")

        with patch(
            "tenxyte.views.account_deletion_views.AccountDeletionService"
        ) as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                True,
                {"message": "Cancelled 1 deletion request(s).", "cancelled_count": 1},
                "",
            )
            resp = _post_authed(
                cancel_account_deletion, "/auth/cancel-deletion/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        for field in CANCEL_DELETION_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /cancel-deletion/ success response"
            )

    @pytest.mark.django_db
    def test_cancelled_count_is_non_negative_integer(self):
        app = _app("SnapCancelDelApp2")
        user = _user("snap_cancel_del_2@test.com", "Pass123!")

        with patch(
            "tenxyte.views.account_deletion_views.AccountDeletionService"
        ) as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                True,
                {"message": "Cancelled 1 deletion request(s).", "cancelled_count": 1},
                "",
            )
            resp = _post_authed(
                cancel_account_deletion, "/auth/cancel-deletion/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        assert isinstance(resp.data["cancelled_count"], int)
        assert resp.data["cancelled_count"] >= 0


# ===========================================================================
# 6c. export_user_data — POST /export-user-data/
# ===========================================================================

EXPORT_REQUIRED_FIELDS = {"user_info", "export_metadata"}

EXPORT_USER_INFO_FIELDS = {
    "id", "email", "first_name", "last_name",
    "is_email_verified", "is_phone_verified", "is_2fa_enabled",
    "created_at",
}

EXPORT_METADATA_FIELDS = {"exported_at", "export_reason", "user_id", "compliance"}


class TestExportUserDataResponseShapeSnapshot:
    """
    Fige la réponse de succès de POST /export-user-data/ (Requirements 8.1, 8.3).
    """

    @pytest.mark.django_db
    def test_success_response_has_top_level_documented_fields(self):
        app = _app("SnapExportApp1")
        user = _user("snap_export_1@test.com", "Pass123!")

        with patch.object(user.__class__, "get_all_permissions", return_value=[]):
            resp = _post_authed(
                export_user_data, "/auth/export-user-data/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        for field in EXPORT_REQUIRED_FIELDS:
            assert field in resp.data, (
                f"Required field '{field}' missing from /export-user-data/ success response"
            )

    @pytest.mark.django_db
    def test_user_info_has_documented_subfields(self):
        app = _app("SnapExportApp2")
        user = _user("snap_export_2@test.com", "Pass123!")

        with patch.object(user.__class__, "get_all_permissions", return_value=[]):
            resp = _post_authed(
                export_user_data, "/auth/export-user-data/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        user_info = resp.data["user_info"]
        for field in EXPORT_USER_INFO_FIELDS:
            assert field in user_info, (
                f"user_info field '{field}' missing from /export-user-data/ success response"
            )

    @pytest.mark.django_db
    def test_export_metadata_has_documented_subfields(self):
        app = _app("SnapExportApp3")
        user = _user("snap_export_3@test.com", "Pass123!")

        with patch.object(user.__class__, "get_all_permissions", return_value=[]):
            resp = _post_authed(
                export_user_data, "/auth/export-user-data/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        metadata = resp.data["export_metadata"]
        for field in EXPORT_METADATA_FIELDS:
            assert field in metadata, (
                f"export_metadata field '{field}' missing from /export-user-data/ success response"
            )

    @pytest.mark.django_db
    def test_compliance_list_is_non_empty(self):
        app = _app("SnapExportApp4")
        user = _user("snap_export_4@test.com", "Pass123!")

        with patch.object(user.__class__, "get_all_permissions", return_value=[]):
            resp = _post_authed(
                export_user_data, "/auth/export-user-data/", user, app,
                {"password": "Pass123!"},
            )

        assert resp.status_code == 200
        assert len(resp.data["export_metadata"]["compliance"]) > 0
