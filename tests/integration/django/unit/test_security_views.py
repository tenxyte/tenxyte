"""
Tests security_views.py - Admin security views (audit logs, login attempts, tokens).

Coverage cible : views/security_views.py (41% → ~80%)
"""

import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, Permission, AuditLog, BlacklistedToken, RefreshToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="SecApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, *perm_codes):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    for code in perm_codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        u.direct_permissions.add(perm)
    return u


def _jwt_token(user, app):
    from tenxyte.services.jwt_service import JWTService
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]


def _authed_request(method, path, user, app, data=None, params=None):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    if params:
        path = path + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = getattr(factory, method)(
        path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs
    )
    req.user = user
    req.application = app
    return req


def _make_audit_log(user, action="login"):
    return AuditLog.objects.create(
        user=user, action=action, ip_address="1.2.3.4", details={}
    )


def _make_refresh_token(user, app):
    from django.utils import timezone
    from datetime import timedelta
    return RefreshToken.objects.create(
        user=user,
        application=app,
        token="rt_" + user.email.replace("@", "_").replace(".", "_"),
        expires_at=timezone.now() + timedelta(days=7),
        is_revoked=False,
    )


# ===========================================================================
# AuditLogListView
# ===========================================================================

class TestAuditLogListView:

    @pytest.mark.django_db
    def test_list_returns_200_with_permission(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditListApp")
        admin = _user("audit_list@test.com", "audit.view")

        req = _authed_request("get", "/admin/audit-logs/", admin, app)
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_returns_403_without_permission(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditListNoPermApp")
        user = _user("audit_list_noperm@test.com")

        req = _authed_request("get", "/admin/audit-logs/", user, app)
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_returns_401_unauthenticated(self):
        from tenxyte.views.security_views import AuditLogListView
        factory = APIRequestFactory()
        req = factory.get("/admin/audit-logs/")
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 401

    @pytest.mark.django_db
    def test_list_filter_by_action(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditFilterApp")
        admin = _user("audit_filter@test.com", "audit.view")
        target = _user("audit_filter_target@test.com")
        _make_audit_log(target, "login")

        req = _authed_request(
            "get", "/admin/audit-logs/", admin, app,
            params={"action": "login"}
        )
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_user_id(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditUserFilterApp")
        admin = _user("audit_uid@test.com", "audit.view")
        target = _user("audit_uid_target@test.com")
        _make_audit_log(target)

        req = _authed_request(
            "get", "/admin/audit-logs/", admin, app,
            params={"user_id": str(target.id)}
        )
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_date_range(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditDateApp")
        admin = _user("audit_date@test.com", "audit.view")

        req = _authed_request(
            "get", "/admin/audit-logs/", admin, app,
            params={"date_from": "2020-01-01T00:00:00Z", "date_to": "2030-12-31T23:59:59Z"}
        )
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_ip(self):
        from tenxyte.views.security_views import AuditLogListView
        app = _app("AuditIPApp")
        admin = _user("audit_ip@test.com", "audit.view")

        req = _authed_request(
            "get", "/admin/audit-logs/", admin, app,
            params={"ip_address": "1.2.3.4"}
        )
        view = AuditLogListView.as_view()
        response = view(req)

        assert response.status_code == 200


# ===========================================================================
# AuditLogDetailView
# ===========================================================================

class TestAuditLogDetailView:

    @pytest.mark.django_db
    def test_detail_returns_200(self):
        from tenxyte.views.security_views import AuditLogDetailView
        app = _app("AuditDetailApp")
        admin = _user("audit_detail@test.com", "audit.view")
        target = _user("audit_detail_target@test.com")
        log = _make_audit_log(target)

        req = _authed_request("get", f"/admin/audit-logs/{log.id}/", admin, app)
        view = AuditLogDetailView.as_view()
        response = view(req, log_id=log.id)

        assert response.status_code == 200
        assert "action" in response.data

    @pytest.mark.django_db
    def test_detail_returns_404_for_nonexistent(self):
        from tenxyte.views.security_views import AuditLogDetailView
        app = _app("AuditDetailNFApp")
        admin = _user("audit_detail_nf@test.com", "audit.view")

        req = _authed_request("get", "/admin/audit-logs/99999/", admin, app)
        view = AuditLogDetailView.as_view()
        response = view(req, log_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_detail_returns_403_without_permission(self):
        from tenxyte.views.security_views import AuditLogDetailView
        app = _app("AuditDetailNoPermApp")
        user = _user("audit_detail_noperm@test.com")
        target = _user("audit_detail_noperm_target@test.com")
        log = _make_audit_log(target)

        req = _authed_request("get", f"/admin/audit-logs/{log.id}/", user, app)
        view = AuditLogDetailView.as_view()
        response = view(req, log_id=log.id)

        assert response.status_code == 403


# ===========================================================================
# LoginAttemptListView
# ===========================================================================

class TestLoginAttemptListView:

    @pytest.mark.django_db
    def test_list_returns_200_with_permission(self):
        from tenxyte.views.security_views import LoginAttemptListView
        app = _app("LoginAttemptApp")
        admin = _user("login_attempt@test.com", "security.view")

        req = _authed_request("get", "/admin/login-attempts/", admin, app)
        view = LoginAttemptListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_returns_403_without_permission(self):
        from tenxyte.views.security_views import LoginAttemptListView
        app = _app("LoginAttemptNoPermApp")
        user = _user("login_attempt_noperm@test.com")

        req = _authed_request("get", "/admin/login-attempts/", user, app)
        view = LoginAttemptListView.as_view()
        response = view(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_filter_by_identifier(self):
        from tenxyte.views.security_views import LoginAttemptListView
        app = _app("LoginAttemptFilterApp")
        admin = _user("login_attempt_filter@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/login-attempts/", admin, app,
            params={"identifier": "test@test.com"}
        )
        view = LoginAttemptListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_success(self):
        from tenxyte.views.security_views import LoginAttemptListView
        app = _app("LoginAttemptSuccessApp")
        admin = _user("login_attempt_success@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/login-attempts/", admin, app,
            params={"success": "true"}
        )
        view = LoginAttemptListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_login_attempts_no_pagination(self):
        from tenxyte.views.security_views import LoginAttemptListView
        app = _app("LoginAttemptNoPage")
        admin = _user("login_attempt_nopg@test.com", "security.view")

        req = _authed_request("get", "/admin/login-attempts/", admin, app)
        view = LoginAttemptListView.as_view()
        with patch('tenxyte.views.security_views.TenxytePagination.paginate_queryset', return_value=None):
            response = view(req)
        assert response.status_code == 200
        assert isinstance(response.data, list)


# ===========================================================================
# BlacklistedTokenListView
# ===========================================================================

class TestBlacklistedTokenListView:

    @pytest.mark.django_db
    def test_list_returns_200_with_permission(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistApp")
        admin = _user("blacklist@test.com", "security.view")

        req = _authed_request("get", "/admin/blacklisted-tokens/", admin, app)
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_returns_403_without_permission(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistNoPermApp")
        user = _user("blacklist_noperm@test.com")

        req = _authed_request("get", "/admin/blacklisted-tokens/", user, app)
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_filter_by_user_id(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistUserApp")
        admin = _user("blacklist_uid@test.com", "security.view")
        target = _user("blacklist_uid_target@test.com")

        req = _authed_request(
            "get", "/admin/blacklisted-tokens/", admin, app,
            params={"user_id": str(target.id)}
        )
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_reason(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistReasonApp")
        admin = _user("blacklist_reason@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/blacklisted-tokens/", admin, app,
            params={"reason": "logout"}
        )
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_expired_true(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistExpiredApp")
        admin = _user("blacklist_expired@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/blacklisted-tokens/", admin, app,
            params={"expired": "true"}
        )
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_expired_false(self):
        from tenxyte.views.security_views import BlacklistedTokenListView
        app = _app("BlacklistNotExpiredApp")
        admin = _user("blacklist_notexpired@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/blacklisted-tokens/", admin, app,
            params={"expired": "false"}
        )
        view = BlacklistedTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200


# ===========================================================================
# BlacklistedTokenCleanupView
# ===========================================================================

class TestBlacklistedTokenCleanupView:

    @pytest.mark.django_db
    def test_cleanup_returns_200(self):
        from tenxyte.views.security_views import BlacklistedTokenCleanupView
        app = _app("BlacklistCleanupApp")
        admin = _user("blacklist_cleanup@test.com", "security.view")

        req = _authed_request("post", "/admin/blacklisted-tokens/cleanup/", admin, app)
        view = BlacklistedTokenCleanupView.as_view()
        response = view(req)

        assert response.status_code == 200
        assert "deleted_count" in response.data

    @pytest.mark.django_db
    def test_cleanup_returns_403_without_permission(self):
        from tenxyte.views.security_views import BlacklistedTokenCleanupView
        app = _app("BlacklistCleanupNoPermApp")
        user = _user("blacklist_cleanup_noperm@test.com")

        req = _authed_request("post", "/admin/blacklisted-tokens/cleanup/", user, app)
        view = BlacklistedTokenCleanupView.as_view()
        response = view(req)

        assert response.status_code == 403


# ===========================================================================
# RefreshTokenListView
# ===========================================================================

class TestRefreshTokenListView:

    @pytest.mark.django_db
    def test_list_returns_200_with_permission(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshListApp")
        admin = _user("refresh_list@test.com", "security.view")

        req = _authed_request("get", "/admin/refresh-tokens/", admin, app)
        view = RefreshTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_returns_403_without_permission(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshListNoPermApp")
        user = _user("refresh_list_noperm@test.com")

        req = _authed_request("get", "/admin/refresh-tokens/", user, app)
        view = RefreshTokenListView.as_view()
        response = view(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_filter_by_user_id(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshUserApp")
        admin = _user("refresh_uid@test.com", "security.view")
        target = _user("refresh_uid_target@test.com")
        _make_refresh_token(target, app)

        req = _authed_request(
            "get", "/admin/refresh-tokens/", admin, app,
            params={"user_id": str(target.id)}
        )
        view = RefreshTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_is_revoked(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshRevokedApp")
        admin = _user("refresh_revoked@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/refresh-tokens/", admin, app,
            params={"is_revoked": "false"}
        )
        view = RefreshTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_expired(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshExpiredApp")
        admin = _user("refresh_expired@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/refresh-tokens/", admin, app,
            params={"expired": "false"}
        )
        view = RefreshTokenListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_app_and_expired_true_and_no_pagination(self):
        from tenxyte.views.security_views import RefreshTokenListView
        app = _app("RefreshExpiredApp2")
        admin = _user("refresh_expired2@test.com", "security.view")

        req = _authed_request(
            "get", "/admin/refresh-tokens/", admin, app,
            params={"application_id": str(app.id), "expired": "true"}
        )
        view = RefreshTokenListView.as_view()
        response = view(req)
        assert response.status_code == 200

        req2 = _authed_request("get", "/admin/refresh-tokens/", admin, app)
        with patch('tenxyte.pagination.TenxytePagination.paginate_queryset', return_value=None):
            response2 = view(req2)
        assert response2.status_code == 200
        assert isinstance(response2.data, list)


# ===========================================================================
# RefreshTokenRevokeView
# ===========================================================================

class TestRefreshTokenRevokeView:

    @pytest.mark.django_db
    def test_revoke_success_returns_200(self):
        from tenxyte.views.security_views import RefreshTokenRevokeView
        app = _app("RevokeApp")
        admin = _user("revoke@test.com", "security.view")
        target = _user("revoke_target@test.com")
        rt = _make_refresh_token(target, app)

        req = _authed_request(
            "post", f"/admin/refresh-tokens/{rt.id}/revoke/", admin, app
        )
        view = RefreshTokenRevokeView.as_view()
        response = view(req, token_id=rt.id)

        assert response.status_code == 200
        assert "message" in response.data

    @pytest.mark.django_db
    def test_revoke_already_revoked_returns_400(self):
        from tenxyte.views.security_views import RefreshTokenRevokeView
        app = _app("RevokeAlreadyApp")
        admin = _user("revoke_already@test.com", "security.view")
        target = _user("revoke_already_target@test.com")
        rt = _make_refresh_token(target, app)
        rt.revoke()

        req = _authed_request(
            "post", f"/admin/refresh-tokens/{rt.id}/revoke/", admin, app
        )
        view = RefreshTokenRevokeView.as_view()
        response = view(req, token_id=rt.id)

        assert response.status_code == 400
        assert "ALREADY_REVOKED" in response.data.get("code", "")

    @pytest.mark.django_db
    def test_revoke_nonexistent_returns_404(self):
        from tenxyte.views.security_views import RefreshTokenRevokeView
        app = _app("RevokeNFApp")
        admin = _user("revoke_nf@test.com", "security.view")

        req = _authed_request(
            "post", "/admin/refresh-tokens/99999/revoke/", admin, app
        )
        view = RefreshTokenRevokeView.as_view()
        response = view(req, token_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_revoke_returns_403_without_permission(self):
        from tenxyte.views.security_views import RefreshTokenRevokeView
        app = _app("RevokeNoPermApp")
        user = _user("revoke_noperm@test.com")
        target = _user("revoke_noperm_target@test.com")
        rt = _make_refresh_token(target, app)

        req = _authed_request(
            "post", f"/admin/refresh-tokens/{rt.id}/revoke/", user, app
        )
        view = RefreshTokenRevokeView.as_view()
        response = view(req, token_id=rt.id)

        assert response.status_code == 403

# ===========================================================================
# User Security Views (list_sessions, revoke_session, etc)
# ===========================================================================

class TestUserSecurityViews:
    def setup_method(self, method):
        import sys
        from unittest.mock import MagicMock
        self.mock_security_service_module = MagicMock()
        self.mock_security_service_class = MagicMock()
        self.mock_security_service_module.SecurityService = self.mock_security_service_class
        sys.modules['tenxyte.services.security_service'] = self.mock_security_service_module

    def teardown_method(self, method):
        import sys
        sys.modules.pop('tenxyte.services.security_service', None)

    @pytest.mark.django_db
    def test_list_sessions(self):
        from tenxyte.views.security_views import list_sessions
        app = _app("SessListApp")
        user = _user("sess_list@test.com")
        req = _authed_request("get", "/me/sessions/", user, app)
        self.mock_security_service_class.return_value.get_user_sessions.return_value = []
        response = list_sessions(req)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_revoke_session(self):
        from tenxyte.views.security_views import revoke_session
        app = _app("SessRevokeApp")
        user = _user("sess_revoke@test.com")

        req1 = _authed_request("delete", "/me/sessions/123/", user, app)
        self.mock_security_service_class.return_value.revoke_session.return_value = (True, "")
        response = revoke_session(req1, session_id="123")
        assert response.status_code == 200

        req2 = _authed_request("delete", "/me/sessions/123/", user, app)
        self.mock_security_service_class.return_value.revoke_session.return_value = (False, "SESSION_NOT_FOUND")
        response = revoke_session(req2, session_id="123")
        assert response.status_code == 404

        req3 = _authed_request("delete", "/me/sessions/123/", user, app)
        self.mock_security_service_class.return_value.revoke_session.return_value = (False, "CANNOT_REVOKE_CURRENT")
        response = revoke_session(req3, session_id="123")
        assert response.status_code == 400

        req4 = _authed_request("delete", "/me/sessions/123/", user, app)
        self.mock_security_service_class.return_value.revoke_session.return_value = (False, "OTHER")
        response = revoke_session(req4, session_id="123")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_revoke_all_sessions(self):
        from tenxyte.views.security_views import revoke_all_sessions
        app = _app("SessRevokeAllApp")
        user = _user("sess_revoke_all@test.com")

        req1 = _authed_request("delete", "/me/sessions/", user, app, data={})
        response = revoke_all_sessions(req1)
        assert response.status_code == 400

        req2 = _authed_request("delete", "/me/sessions/", user, app, data={"confirmation": "REVOKE ALL"})
        self.mock_security_service_class.return_value.revoke_all_sessions.return_value = 5
        response = revoke_all_sessions(req2)
        assert response.status_code == 200
        assert response.data["revoked_count"] == 5

    @pytest.mark.django_db
    def test_list_devices(self):
        from tenxyte.views.security_views import list_devices
        app = _app("DevListApp")
        user = _user("dev_list@test.com")
        req = _authed_request("get", "/me/devices/", user, app)
        self.mock_security_service_class.return_value.get_user_devices.return_value = []
        response = list_devices(req)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_revoke_device(self):
        from tenxyte.views.security_views import revoke_device
        app = _app("DevRevokeApp")
        user = _user("dev_revoke@test.com")

        req1 = _authed_request("delete", "/me/devices/1/", user, app)
        self.mock_security_service_class.return_value.revoke_device.return_value = (True, {"sessions_revoked": 2}, "")
        response = revoke_device(req1, device_id=1)
        assert response.status_code == 200

        req2 = _authed_request("delete", "/me/devices/1/", user, app)
        self.mock_security_service_class.return_value.revoke_device.return_value = (False, {}, "DEVICE_NOT_FOUND")
        response = revoke_device(req2, device_id=1)
        assert response.status_code == 404

        req3 = _authed_request("delete", "/me/devices/1/", user, app)
        self.mock_security_service_class.return_value.revoke_device.return_value = (False, {}, "OTHER")
        response = revoke_device(req3, device_id=1)
        assert response.status_code == 400
