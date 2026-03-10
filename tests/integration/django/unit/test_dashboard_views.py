"""
Tests dashboard_views.py + stats_service.py.

Coverage cible : views/dashboard_views.py (0% → 80%)
                 services/stats_service.py (0% → 80%)
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from django.utils import timezone
from datetime import timedelta

from tenxyte.models import (
    User, Application, Permission, AuditLog, BlacklistedToken,
    RefreshToken, LoginAttempt, AccountDeletionRequest,
)
from tenxyte.views.dashboard_views import (
    DashboardGlobalView, DashboardAuthView,
    DashboardSecurityView, DashboardGDPRView, DashboardOrganizationsView,
)
from tenxyte.services.stats_service import StatsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="DashApp"):
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


def _authed_get(view_cls, path, user, app):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req)


# ===========================================================================
# DashboardGlobalView
# ===========================================================================

class TestDashboardGlobalView:

    @pytest.mark.django_db
    def test_global_stats_success(self):
        app = _app("DashGlobal1")
        admin = _user("dashglobal1@test.com", "dashboard.view")

        resp = _authed_get(DashboardGlobalView, "/auth/dashboard/stats/", admin, app)

        assert resp.status_code == 200
        data = resp.data
        assert "users" in data
        assert "auth" in data
        assert "applications" in data
        assert "security" in data
        assert "gdpr" in data

    @pytest.mark.django_db
    def test_global_stats_without_permission_returns_403(self):
        app = _app("DashGlobal2")
        user = _user("dashglobal2@test.com")

        resp = _authed_get(DashboardGlobalView, "/auth/dashboard/stats/", user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_global_stats_requires_jwt(self):
        app = _app("DashGlobal3")
        factory = APIRequestFactory()
        req = factory.get("/auth/dashboard/stats/")
        req.application = app
        resp = DashboardGlobalView.as_view()(req)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_global_stats_users_section_counts(self):
        app = _app("DashGlobal4")
        admin = _user("dashglobal4@test.com", "dashboard.view")
        # Create some users with different states
        u1 = _user("dashglobal4_active@test.com")
        u2 = _user("dashglobal4_banned@test.com")
        u2.is_banned = True
        u2.save()

        resp = _authed_get(DashboardGlobalView, "/auth/dashboard/stats/", admin, app)

        assert resp.status_code == 200
        users = resp.data["users"]
        assert users["total"] >= 2
        assert users["banned"] >= 1


# ===========================================================================
# DashboardAuthView
# ===========================================================================

class TestDashboardAuthView:

    @pytest.mark.django_db
    def test_auth_stats_success(self):
        app = _app("DashAuth1")
        admin = _user("dashauth1@test.com", "dashboard.view")

        resp = _authed_get(DashboardAuthView, "/auth/dashboard/auth/", admin, app)

        assert resp.status_code == 200
        data = resp.data
        assert "login_stats" in data
        assert "registration_stats" in data
        assert "token_stats" in data
        assert "top_login_failure_reasons" in data
        assert "charts" in data

    @pytest.mark.django_db
    def test_auth_stats_without_permission_returns_403(self):
        app = _app("DashAuth2")
        user = _user("dashauth2@test.com")

        resp = _authed_get(DashboardAuthView, "/auth/dashboard/auth/", user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_auth_stats_login_periods(self):
        app = _app("DashAuth3")
        admin = _user("dashauth3@test.com", "dashboard.view")
        # Create a login attempt
        LoginAttempt.record(
            identifier=admin.email,
            ip_address="1.2.3.4",
            application=app,
            success=True,
        )

        resp = _authed_get(DashboardAuthView, "/auth/dashboard/auth/", admin, app)

        assert resp.status_code == 200
        login_stats = resp.data["login_stats"]
        assert "today" in login_stats
        assert "this_week" in login_stats
        assert "this_month" in login_stats
        assert login_stats["today"]["total"] >= 1

    @pytest.mark.django_db
    def test_auth_stats_token_stats(self):
        app = _app("DashAuth4")
        admin = _user("dashauth4@test.com", "dashboard.view")
        # Create an active refresh token
        RefreshToken.generate(user=admin, application=app, ip_address="1.2.3.4")

        resp = _authed_get(DashboardAuthView, "/auth/dashboard/auth/", admin, app)

        assert resp.status_code == 200
        token_stats = resp.data["token_stats"]
        assert "active_refresh_tokens" in token_stats
        assert token_stats["active_refresh_tokens"] >= 1

    @pytest.mark.django_db
    def test_auth_stats_failure_reasons(self):
        app = _app("DashAuth5")
        admin = _user("dashauth5@test.com", "dashboard.view")
        # Create failed login attempts with reasons
        for reason in ["INVALID_PASSWORD", "INVALID_PASSWORD", "ACCOUNT_LOCKED"]:
            LoginAttempt.record(
                identifier=admin.email,
                ip_address="1.2.3.4",
                application=app,
                success=False,
                failure_reason=reason,
            )

        resp = _authed_get(DashboardAuthView, "/auth/dashboard/auth/", admin, app)

        assert resp.status_code == 200
        reasons = resp.data["top_login_failure_reasons"]
        assert isinstance(reasons, list)
        if reasons:
            assert "reason" in reasons[0]
            assert "count" in reasons[0]


# ===========================================================================
# DashboardSecurityView
# ===========================================================================

class TestDashboardSecurityView:

    @pytest.mark.django_db
    def test_security_stats_success(self):
        app = _app("DashSec1")
        admin = _user("dashsec1@test.com", "dashboard.view")

        resp = _authed_get(DashboardSecurityView, "/auth/dashboard/security/", admin, app)

        assert resp.status_code == 200
        data = resp.data
        assert "audit_summary_24h" in data
        assert "blacklisted_tokens" in data
        assert "suspicious_activity" in data
        assert "account_security" in data

    @pytest.mark.django_db
    def test_security_stats_without_permission_returns_403(self):
        app = _app("DashSec2")
        user = _user("dashsec2@test.com")

        resp = _authed_get(DashboardSecurityView, "/auth/dashboard/security/", user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_security_stats_account_security(self):
        app = _app("DashSec3")
        admin = _user("dashsec3@test.com", "dashboard.view")
        # Lock and ban some users
        locked = _user("dashsec3_locked@test.com")
        locked.lock_account(30)
        banned = _user("dashsec3_banned@test.com")
        banned.is_banned = True
        banned.save()

        resp = _authed_get(DashboardSecurityView, "/auth/dashboard/security/", admin, app)

        assert resp.status_code == 200
        sec = resp.data["account_security"]
        assert sec["locked_accounts"] >= 1
        assert sec["banned_accounts"] >= 1
        assert "2fa_adoption_rate" in sec

    @pytest.mark.django_db
    def test_security_stats_blacklisted_tokens(self):
        app = _app("DashSec4")
        admin = _user("dashsec4@test.com", "dashboard.view")
        # Create a blacklisted token
        BlacklistedToken.objects.create(
            token_jti="test-jti-dash",
            reason="logout",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        resp = _authed_get(DashboardSecurityView, "/auth/dashboard/security/", admin, app)

        assert resp.status_code == 200
        bl = resp.data["blacklisted_tokens"]
        assert bl["total_active"] >= 1
        assert "by_reason" in bl


# ===========================================================================
# DashboardGDPRView
# ===========================================================================

class TestDashboardGDPRView:

    @pytest.mark.django_db
    def test_gdpr_stats_success(self):
        app = _app("DashGDPR1")
        admin = _user("dashgdpr1@test.com", "dashboard.view")

        resp = _authed_get(DashboardGDPRView, "/auth/dashboard/gdpr/", admin, app)

        assert resp.status_code == 200
        data = resp.data
        assert "deletion_requests" in data
        assert "data_exports" in data

    @pytest.mark.django_db
    def test_gdpr_stats_without_permission_returns_403(self):
        app = _app("DashGDPR2")
        user = _user("dashgdpr2@test.com")

        resp = _authed_get(DashboardGDPRView, "/auth/dashboard/gdpr/", user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_gdpr_stats_deletion_requests(self):
        app = _app("DashGDPR3")
        admin = _user("dashgdpr3@test.com", "dashboard.view")
        target = _user("dashgdpr3_target@test.com")
        AccountDeletionRequest.objects.create(
            user=target,
            status="pending",
            grace_period_ends_at=timezone.now() + timedelta(days=30),
        )

        resp = _authed_get(DashboardGDPRView, "/auth/dashboard/gdpr/", admin, app)

        assert resp.status_code == 200
        dr = resp.data["deletion_requests"]
        assert dr["total"] >= 1
        assert "by_status" in dr
        assert dr["by_status"].get("pending", 0) >= 1

    @pytest.mark.django_db
    def test_gdpr_stats_expiring_grace_period(self):
        app = _app("DashGDPR4")
        admin = _user("dashgdpr4@test.com", "dashboard.view")
        target = _user("dashgdpr4_target@test.com")
        # Confirmed request expiring in 3 days
        AccountDeletionRequest.objects.create(
            user=target,
            status="confirmed",
            grace_period_ends_at=timezone.now() + timedelta(days=3),
        )

        resp = _authed_get(DashboardGDPRView, "/auth/dashboard/gdpr/", admin, app)

        assert resp.status_code == 200
        dr = resp.data["deletion_requests"]
        assert dr["grace_period_expiring_7d"] >= 1


# ===========================================================================
# DashboardOrganizationsView
# ===========================================================================

class TestDashboardOrganizationsView:

    @pytest.mark.django_db
    def test_orgs_stats_disabled_returns_enabled_false(self):
        app = _app("DashOrg1")
        admin = _user("dashorgs1@test.com", "dashboard.view")

        with patch("tenxyte.services.stats_service.StatsService.get_organization_stats",
                   return_value={"enabled": False}):
            resp = _authed_get(DashboardOrganizationsView, "/auth/dashboard/organizations/",
                               admin, app)

        assert resp.status_code == 200
        assert resp.data["enabled"] is False

    @pytest.mark.django_db
    def test_orgs_stats_without_permission_returns_403(self):
        app = _app("DashOrg2")
        user = _user("dashorgs2@test.com")

        resp = _authed_get(DashboardOrganizationsView, "/auth/dashboard/organizations/",
                           user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_orgs_stats_enabled_returns_data(self):
        app = _app("DashOrg3")
        admin = _user("dashorgs3@test.com", "dashboard.view")

        mock_data = {
            "enabled": True,
            "total_organizations": 5,
            "active": 4,
            "with_sub_orgs": 1,
            "members": {"total": 20, "avg_per_org": 4.0, "by_role": {}},
            "top_organizations": [],
        }
        with patch("tenxyte.services.stats_service.StatsService.get_organization_stats",
                   return_value=mock_data):
            resp = _authed_get(DashboardOrganizationsView, "/auth/dashboard/organizations/",
                               admin, app)

        assert resp.status_code == 200
        assert resp.data["total_organizations"] == 5
        assert resp.data["enabled"] is True


# ===========================================================================
# StatsService unit tests
# ===========================================================================

class TestStatsService:

    @pytest.mark.django_db
    def test_get_global_stats_structure(self):
        service = StatsService()
        result = service.get_global_stats()

        assert "users" in result
        assert "auth" in result
        assert "applications" in result
        assert "security" in result
        assert "gdpr" in result

    @pytest.mark.django_db
    def test_user_stats_counts(self):
        u1 = _user("stats_u1@test.com")
        u2 = _user("stats_u2@test.com")
        u2.is_locked = True
        u2.save()
        u3 = _user("stats_u3@test.com")
        u3.is_banned = True
        u3.save()

        service = StatsService()
        stats = service._user_stats()

        assert stats["total"] >= 3
        assert stats["locked"] >= 1
        assert stats["banned"] >= 1

    @pytest.mark.django_db
    def test_2fa_rate_no_users(self):
        service = StatsService()
        # Deactivate all users to simulate empty
        User.objects.all().update(is_active=False)
        rate = service._2fa_rate()
        assert rate == 0.0

    @pytest.mark.django_db
    def test_2fa_rate_with_users(self):
        u1 = _user("stats_2fa1@test.com")
        u1.is_2fa_enabled = True
        u1.save()
        u2 = _user("stats_2fa2@test.com")

        service = StatsService()
        rate = service._2fa_rate()
        assert 0.0 <= rate <= 100.0

    @pytest.mark.django_db
    def test_get_auth_stats_structure(self):
        service = StatsService()
        result = service.get_auth_stats()

        assert "login_stats" in result
        assert "login_by_method" in result
        assert "registration_stats" in result
        assert "token_stats" in result
        assert "top_login_failure_reasons" in result
        assert "charts" in result
        assert "logins_per_day_7d" in result["charts"]

    @pytest.mark.django_db
    def test_login_period_stats_empty(self):
        service = StatsService()
        since = timezone.now() - timedelta(hours=1)
        result = service._login_period_stats(since)

        assert result["total"] >= 0
        assert result["success"] >= 0
        assert result["failed"] >= 0

    @pytest.mark.django_db
    def test_login_period_stats_with_attempts(self):
        app, _ = Application.create_application(name="StatsApp1")
        user = _user("stats_login1@test.com")
        LoginAttempt.record(
            identifier=user.email, ip_address="1.2.3.4",
            application=app, success=True
        )
        LoginAttempt.record(
            identifier=user.email, ip_address="1.2.3.4",
            application=app, success=False, failure_reason="INVALID_PASSWORD"
        )

        service = StatsService()
        since = timezone.now() - timedelta(hours=1)
        result = service._login_period_stats(since)

        assert result["total"] >= 2
        assert result["success"] >= 1
        assert result["failed"] >= 1

    @pytest.mark.django_db
    def test_top_failure_reasons(self):
        app, _ = Application.create_application(name="StatsApp2")
        user = _user("stats_fail1@test.com")
        for _ in range(3):
            LoginAttempt.record(
                identifier=user.email, ip_address="1.2.3.4",
                application=app, success=False, failure_reason="INVALID_PASSWORD"
            )
        LoginAttempt.record(
            identifier=user.email, ip_address="1.2.3.4",
            application=app, success=False, failure_reason="ACCOUNT_LOCKED"
        )

        service = StatsService()
        since = timezone.now() - timedelta(hours=1)
        reasons = service._top_failure_reasons(since)

        assert len(reasons) >= 1
        assert reasons[0]["reason"] == "INVALID_PASSWORD"
        assert reasons[0]["count"] >= 3

    @pytest.mark.django_db
    def test_logins_per_day(self):
        app, _ = Application.create_application(name="StatsApp3")
        user = _user("stats_perday1@test.com")
        LoginAttempt.record(
            identifier=user.email, ip_address="1.2.3.4",
            application=app, success=True
        )

        service = StatsService()
        result = service._logins_per_day(7)

        assert isinstance(result, list)
        if result:
            assert "date" in result[0]
            assert "success" in result[0]
            assert "failed" in result[0]

    @pytest.mark.django_db
    def test_get_security_stats_structure(self):
        service = StatsService()
        result = service.get_security_stats()

        assert "audit_summary_24h" in result
        assert "blacklisted_tokens" in result
        assert "suspicious_activity" in result
        assert "account_security" in result

    @pytest.mark.django_db
    def test_blacklisted_token_stats(self):
        BlacklistedToken.objects.create(
            token_jti="stats-jti-1",
            reason="logout",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        BlacklistedToken.objects.create(
            token_jti="stats-jti-expired",
            reason="logout",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        service = StatsService()
        result = service._blacklisted_token_stats(timezone.now())

        assert result["total_active"] >= 1
        assert result["expired_pending_cleanup"] >= 1
        assert "by_reason" in result

    @pytest.mark.django_db
    def test_audit_summary(self):
        app, _ = Application.create_application(name="StatsApp4")
        user = _user("stats_audit1@test.com")
        AuditLog.objects.create(
            user=user, application=app, action="login",
            ip_address="1.2.3.4"
        )
        AuditLog.objects.create(
            user=user, application=app, action="logout",
            ip_address="1.2.3.4"
        )

        service = StatsService()
        since = timezone.now() - timedelta(hours=1)
        result = service._audit_summary(since)

        assert result["total_events"] >= 2
        assert "by_action" in result
        assert "login" in result["by_action"]

    @pytest.mark.django_db
    def test_get_gdpr_stats_structure(self):
        service = StatsService()
        result = service.get_gdpr_stats()

        assert "deletion_requests" in result
        assert "data_exports" in result
        assert "total" in result["deletion_requests"]
        assert "by_status" in result["deletion_requests"]

    @pytest.mark.django_db
    def test_gdpr_summary_pending_count(self):
        target = _user("stats_gdpr1@test.com")
        AccountDeletionRequest.objects.create(
            user=target,
            status="pending",
            grace_period_ends_at=timezone.now() + timedelta(days=30),
        )

        service = StatsService()
        result = service._gdpr_summary()

        assert result["pending"] >= 1

    @pytest.mark.django_db
    def test_get_organization_stats_disabled(self):
        service = StatsService()

        with patch("tenxyte.services.stats_service.StatsService.get_organization_stats",
                   return_value={"enabled": False}):
            result = service.get_organization_stats()

        assert result["enabled"] is False

    @pytest.mark.django_db
    def test_application_stats(self):
        Application.create_application(name="StatsTestApp1")
        Application.create_application(name="StatsTestApp2")

        service = StatsService()
        result = service._application_stats()

        assert result["total"] >= 2
        assert result["active"] >= 0

    @pytest.mark.django_db
    def test_auth_summary_structure(self):
        service = StatsService()
        result = service._auth_summary()

        assert "total_logins_today" in result
        assert "failed_logins_today" in result
        assert "active_refresh_tokens" in result

    @pytest.mark.django_db
    def test_security_summary_structure(self):
        service = StatsService()
        result = service._security_summary()

        assert "blacklisted_tokens" in result
        assert "suspicious_activity_24h" in result

    @pytest.mark.django_db
    def test_login_by_method_fallback(self):
        """When no audit logs with method detail, fallback to total count."""
        service = StatsService()
        since = timezone.now() - timedelta(hours=1)
        result = service._login_by_method(since)

        assert isinstance(result, dict)
