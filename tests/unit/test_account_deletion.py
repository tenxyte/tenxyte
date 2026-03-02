"""
Tests AccountDeletionService + account_deletion_views.

Coverage cible :
- services/account_deletion_service.py (17% → ~70%)
- views/account_deletion_views.py (39% → ~80%)
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, AccountDeletionRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="DelApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, password="Pass123!", app=None):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _jwt_token(user, app):
    from tenxyte.services.jwt_service import JWTService
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]


def _authed_request(method, path, user, app, data=None):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    req = getattr(factory, method)(
        path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs
    )
    req.user = user
    req.application = app
    return req


# ===========================================================================
# AccountDeletionService
# ===========================================================================

class TestRequestDeletion:

    @pytest.mark.django_db
    def test_request_deletion_success(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_req@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            success, data, error = service.request_deletion(
                user=user,
                password="Pass123!",
                ip_address="1.2.3.4",
                reason="Testing"
            )

        assert success is True
        assert data is not None
        assert "request_id" in data
        assert error == ""

    @pytest.mark.django_db
    def test_request_deletion_wrong_password(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_badpw@test.com")
        service = AccountDeletionService()

        success, data, error = service.request_deletion(
            user=user,
            password="WrongPassword!",
            ip_address="1.2.3.4"
        )

        assert success is False
        assert error == "Invalid password"

    @pytest.mark.django_db
    def test_request_deletion_2fa_required(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_2fa@test.com")
        user.is_2fa_enabled = True
        user.save()
        service = AccountDeletionService()

        success, data, error = service.request_deletion(
            user=user,
            password="Pass123!",
            ip_address="1.2.3.4",
            otp_code=""
        )

        assert success is False
        assert "two-factor" in error.lower()

    @pytest.mark.django_db
    def test_request_deletion_2fa_invalid_code(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_2fa_bad@test.com")
        user.is_2fa_enabled = True
        user.save()
        service = AccountDeletionService()

        # OTPService is imported locally inside request_deletion, patch at the source module
        with patch("tenxyte.services.otp_service.OTPService", create=True) as MockOTP:
            MockOTP.return_value.verify_otp.return_value = False
            success, data, error = service.request_deletion(
                user=user,
                password="Pass123!",
                ip_address="1.2.3.4",
                otp_code="000000"
            )

        assert success is False
        assert "invalid" in error.lower()


class TestConfirmDeletion:

    @pytest.mark.django_db
    def test_confirm_deletion_success(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_confirm@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        # confirm_deletion requires status='confirmation_sent'
        deletion_req = AccountDeletionRequest.objects.get(id=data["request_id"])
        deletion_req.status = "confirmation_sent"
        deletion_req.save()
        token = deletion_req.confirmation_token

        with patch.object(service.email_service, 'send_account_deletion_confirmed', return_value=None):
            success, result, error = service.confirm_deletion(token=token)

        assert success is True
        assert "grace_period_ends_at" in result

    @pytest.mark.django_db
    def test_confirm_deletion_invalid_token(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        service = AccountDeletionService()

        success, data, error = service.confirm_deletion(token="invalid-token-xyz")

        assert success is False
        assert "invalid" in error.lower()

    @pytest.mark.django_db
    def test_confirm_deletion_email_failure(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_confirm_email_fail@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        deletion_req = AccountDeletionRequest.objects.get(id=data["request_id"])
        deletion_req.status = "confirmation_sent"
        deletion_req.save()
        token = deletion_req.confirmation_token

        with patch.object(service.email_service, 'send_account_deletion_confirmed', side_effect=Exception("Email Error")):
            success, result, error = service.confirm_deletion(token=token)

        assert success is True
        assert "grace_period_ends_at" in result
        
        from tenxyte.models import AuditLog
        log = AuditLog.objects.get(action='deletion_confirmation_email_failed', user=user)
        assert log.details['error'] == "Email Error"

    @pytest.mark.django_db
    def test_confirm_deletion_general_error(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest.objects, 'get', side_effect=Exception("DB Error")):
            success, data, error = service.confirm_deletion(token="some-token")

        assert success is False
        assert error == "An unexpected error occurred while confirming the deletion request."
        from tenxyte.models import AuditLog
        log = AuditLog.objects.filter(action='deletion_confirmation_error').first()
        assert log is not None
        assert log.details['error'] == "Internal server error"


class TestCancelDeletion:

    @pytest.mark.django_db
    def test_cancel_deletion_success(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_cancel@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            service.request_deletion(user=user, password="Pass123!")

        success, data, error = service.cancel_deletion(
            user=user, password="Pass123!"
        )

        assert success is True
        assert data["cancelled_count"] >= 1

    @pytest.mark.django_db
    def test_cancel_deletion_wrong_password(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_cancel_bad@test.com")
        service = AccountDeletionService()

        success, data, error = service.cancel_deletion(
            user=user, password="WrongPass!"
        )

        assert success is False
        assert error == "Invalid password"

    @pytest.mark.django_db
    def test_cancel_deletion_no_active_request(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_cancel_none@test.com")
        service = AccountDeletionService()

        success, data, error = service.cancel_deletion(
            user=user, password="Pass123!"
        )

        assert success is False
        assert "no active" in error.lower()


class TestGetUserRequests:

    @pytest.mark.django_db
    def test_get_user_requests_empty(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_hist_empty@test.com")
        service = AccountDeletionService()

        result = service.get_user_requests(user)

        assert result["total_requests"] == 0
        assert result["active_request"] is None
        assert result["history"] == []

    @pytest.mark.django_db
    def test_get_user_requests_with_active(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_hist_active@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            service.request_deletion(user=user, password="Pass123!")

        result = service.get_user_requests(user)

        assert result["total_requests"] == 1
        assert result["active_request"] is not None
        assert result["active_request"]["status"] in ["pending", "confirmation_sent"]


class TestAdminProcessRequest:

    @pytest.mark.django_db
    def test_admin_approve_confirmation_sent(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_admin_approve@test.com")
        admin = _user("del_admin@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = "confirmation_sent"
        req.save()

        success, msg = service.admin_process_request(req.id, "approve", admin)
        assert success is True
        assert "approved" in msg.lower()

    @pytest.mark.django_db
    def test_admin_reject_pending(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_admin_reject@test.com")
        admin = _user("del_admin_rej@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])

        success, msg = service.admin_process_request(req.id, "reject", admin, "Not valid")
        assert success is True
        assert "rejected" in msg.lower()

    @pytest.mark.django_db
    def test_admin_cancel_active(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_admin_cancel@test.com")
        admin = _user("del_admin_can@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])

        success, msg = service.admin_process_request(req.id, "cancel", admin)
        assert success is True
        assert "cancelled" in msg.lower()

    @pytest.mark.django_db
    def test_admin_invalid_action(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_admin_inv@test.com")
        admin = _user("del_admin_inv2@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])

        success, msg = service.admin_process_request(req.id, "invalid_action", admin)
        assert success is False
        assert "invalid" in msg.lower()

    @pytest.mark.django_db
    def test_admin_nonexistent_request(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        admin = _user("del_admin_nf@test.com")
        service = AccountDeletionService()

        success, msg = service.admin_process_request(99999, "approve", admin)
        assert success is False
        assert "not found" in msg.lower()

    @pytest.mark.django_db
    def test_admin_approve_not_confirmation_sent(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_app_not_conf@test.com")
        admin = _user("del_admin_app2@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        # status is currently 'pending'
        
        success, msg = service.admin_process_request(req.id, "approve", admin)
        assert success is False
        assert "Can only approve requests with confirmation_sent status" in msg

    @pytest.mark.django_db
    def test_admin_reject_not_valid_status(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_rej_not_val@test.com")
        admin = _user("del_admin_rej2@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = 'cancelled'
        req.save()
        
        success, msg = service.admin_process_request(req.id, "reject", admin)
        assert success is False
        assert "Can only reject pending or confirmation_sent requests" in msg

    @pytest.mark.django_db
    def test_admin_cancel_not_active(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_can_not_act@test.com")
        admin = _user("del_admin_can2@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = 'completed'
        req.save()
        
        success, msg = service.admin_process_request(req.id, "cancel", admin)
        assert success is False
        assert "Can only cancel active requests" in msg

    @pytest.mark.django_db
    def test_admin_execute_not_confirmed(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_exec_not_conf@test.com")
        admin = _user("del_admin_exec1@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        # status is pending
        
        success, msg = service.admin_process_request(req.id, "execute", admin)
        assert success is False
        assert "Can only execute confirmed requests" in msg

    @pytest.mark.django_db
    def test_admin_execute_success(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_exec_succ@test.com")
        admin = _user("del_admin_exec2@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = 'confirmed'
        req.save()
        
        with patch.object(req, 'execute_deletion', return_value=True):
            with patch('tenxyte.services.account_deletion_service.AccountDeletionRequest.objects.get', return_value=req):
                success, msg = service.admin_process_request(req.id, "execute", admin)
                assert success is True
                assert "executed successfully" in msg
                from tenxyte.models import AuditLog
                assert AuditLog.objects.filter(action='deletion_request_executed_admin').exists()

    @pytest.mark.django_db
    def test_admin_execute_fail(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_exec_fail@test.com")
        admin = _user("del_admin_exec3@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = 'confirmed'
        req.save()
        
        with patch.object(req, 'execute_deletion', return_value=False):
            with patch('tenxyte.services.account_deletion_service.AccountDeletionRequest.objects.get', return_value=req):
                success, msg = service.admin_process_request(req.id, "execute", admin)
                assert success is False
                assert "Failed to execute" in msg


class TestGetDeletionStatistics:

    @pytest.mark.django_db
    def test_statistics_empty(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        service = AccountDeletionService()

        stats = service.get_deletion_statistics()

        assert stats["total_requests"] == 0
        assert stats["completion_rate"] == 0
        assert "requests_by_status" in stats

    @pytest.mark.django_db
    def test_statistics_with_requests(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("del_stats@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            service.request_deletion(user=user, password="Pass123!")

        stats = service.get_deletion_statistics()

        assert stats["total_requests"] >= 1
        assert stats["recent_requests_30_days"] >= 1


class TestProcessExpiredRequests:

    @pytest.mark.django_db
    def test_process_expired_no_requests(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        service = AccountDeletionService()

        count = service.process_expired_requests()
        assert count == 0

    @pytest.mark.django_db
    def test_process_expired_requests_success(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("proc_exp_succ@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            _, data, _ = service.request_deletion(user=user, password="Pass123!")

        req = AccountDeletionRequest.objects.get(id=data["request_id"])
        req.status = 'confirmed'
        from django.utils import timezone
        import datetime
        req.grace_period_ends_at = timezone.now() - datetime.timedelta(days=1)
        req.save()

        with patch.object(AccountDeletionRequest, 'execute_deletion', return_value=True):
            count = service.process_expired_requests()
            assert count == 1
            from tenxyte.models import AuditLog
            assert AuditLog.objects.filter(action='deletion_request_processed').exists()

class TestGetPendingRequests:
    @pytest.mark.django_db
    def test_get_pending_requests(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        user = _user("get_pend_req@test.com")
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            service.request_deletion(user=user, password="Pass123!")

        result = service.get_pending_requests()
        assert result['pending_count'] == 1
        assert len(result['requests']) == 1
        assert result['requests'][0]['status'] == 'pending'


# ===========================================================================
# account_deletion_views
# ===========================================================================

class TestRequestAccountDeletionView:

    @pytest.mark.django_db
    def test_request_deletion_view_success(self):
        from tenxyte.views.account_deletion_views import request_account_deletion
        app = _app("DelViewApp")
        user = _user("view_del@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                True, {"request_id": 1, "grace_period_days": 30}, ""
            )
            req = _authed_request("post", "/request-deletion/", user, app, data={"password": "Pass123!"})
            response = request_account_deletion(req)

        assert response.status_code == 201

    @pytest.mark.django_db
    def test_request_deletion_view_invalid_password(self):
        from tenxyte.views.account_deletion_views import request_account_deletion
        app = _app("DelViewBadApp")
        user = _user("view_del_bad@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.request_deletion.return_value = (
                False, None, "Invalid password"
            )
            req = _authed_request("post", "/request-deletion/", user, app, data={"password": "wrong"})
            response = request_account_deletion(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_request_deletion_view_missing_password(self):
        from tenxyte.views.account_deletion_views import request_account_deletion
        app = _app("DelViewNoPassApp")
        user = _user("view_del_nopw@test.com")

        req = _authed_request("post", "/request-deletion/", user, app, data={})
        response = request_account_deletion(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_request_deletion_view_unauthenticated(self):
        from tenxyte.views.account_deletion_views import request_account_deletion
        factory = APIRequestFactory()
        req = factory.post("/request-deletion/", data={"password": "Pass123!"}, format="json")
        response = request_account_deletion(req)

        assert response.status_code in (401, 403)


class TestConfirmAccountDeletionView:

    @pytest.mark.django_db
    def test_confirm_deletion_view_success(self):
        from tenxyte.views.account_deletion_views import confirm_account_deletion
        factory = APIRequestFactory()

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.confirm_deletion.return_value = (
                True, {"grace_period_ends_at": "2025-01-01T00:00:00", "days_remaining": 30}, ""
            )
            req = factory.post("/confirm-deletion/", data={"token": "valid-token"}, format="json")
            response = confirm_account_deletion(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_confirm_deletion_view_missing_token(self):
        from tenxyte.views.account_deletion_views import confirm_account_deletion
        factory = APIRequestFactory()
        req = factory.post("/confirm-deletion/", data={}, format="json")
        response = confirm_account_deletion(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_confirm_deletion_view_invalid_token(self):
        from tenxyte.views.account_deletion_views import confirm_account_deletion
        factory = APIRequestFactory()

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.confirm_deletion.return_value = (
                False, None, "Invalid or expired confirmation token"
            )
            req = factory.post("/confirm-deletion/", data={"token": "bad-token"}, format="json")
            response = confirm_account_deletion(req)

        assert response.status_code == 400


class TestCancelAccountDeletionView:

    @pytest.mark.django_db
    def test_cancel_deletion_view_success(self):
        from tenxyte.views.account_deletion_views import cancel_account_deletion
        app = _app("CancelDelApp")
        user = _user("view_cancel@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                True, {"cancelled_count": 1, "message": "Cancelled 1 deletion request(s)."}, ""
            )
            req = _authed_request("post", "/cancel-deletion/", user, app, data={"password": "Pass123!"})
            response = cancel_account_deletion(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_cancel_deletion_view_no_active_request(self):
        from tenxyte.views.account_deletion_views import cancel_account_deletion
        app = _app("CancelDelNoneApp")
        user = _user("view_cancel_none@test.com")

        with patch("tenxyte.views.account_deletion_views.AccountDeletionService") as MockSvc:
            MockSvc.return_value.cancel_deletion.return_value = (
                False, None, "No active deletion requests found"
            )
            req = _authed_request("post", "/cancel-deletion/", user, app, data={"password": "Pass123!"})
            response = cancel_account_deletion(req)

        assert response.status_code == 400


class TestAccountDeletionStatusView:

    @pytest.mark.django_db
    def test_status_view_returns_200(self):
        from tenxyte.views.account_deletion_views import account_deletion_status
        app = _app("DelStatusApp")
        user = _user("view_status@test.com")

        req = _authed_request("get", "/account-deletion-status/", user, app)
        response = account_deletion_status(req)

        assert response.status_code == 200
        assert "total_requests" in response.data
        assert "history" in response.data

    @pytest.mark.django_db
    def test_status_view_unauthenticated(self):
        from tenxyte.views.account_deletion_views import account_deletion_status
        factory = APIRequestFactory()
        req = factory.get("/account-deletion-status/")
        response = account_deletion_status(req)

        assert response.status_code in (401, 403)


class TestExportUserDataView:

    @pytest.mark.django_db
    def test_export_data_success(self):
        from tenxyte.views.account_deletion_views import export_user_data
        from tenxyte.models import AuditLog
        app = _app("ExportApp")
        user = _user("view_export@test.com")

        req = _authed_request("post", "/export-user-data/", user, app, data={"password": "Pass123!"})
        req.user = user

        with patch.object(user.__class__, 'get_all_permissions', return_value=[]):
            response = export_user_data(req)

        assert response.status_code == 200
        assert "user_info" in response.data
        assert "export_metadata" in response.data

    @pytest.mark.django_db
    def test_export_data_wrong_password(self):
        from tenxyte.views.account_deletion_views import export_user_data
        app = _app("ExportBadApp")
        user = _user("view_export_bad@test.com")

        req = _authed_request("post", "/export-user-data/", user, app, data={"password": "WrongPass!"})
        response = export_user_data(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_export_data_missing_password(self):
        from tenxyte.views.account_deletion_views import export_user_data
        app = _app("ExportNoPassApp")
        user = _user("view_export_nopw@test.com")

        req = _authed_request("post", "/export-user-data/", user, app, data={})
        response = export_user_data(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_export_data_unauthenticated(self):
        from tenxyte.views.account_deletion_views import export_user_data
        factory = APIRequestFactory()
        req = factory.post("/export-user-data/", data={"password": "Pass123!"}, format="json")
        response = export_user_data(req)

        assert response.status_code in (401, 403)
