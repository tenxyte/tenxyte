"""
Tests Phase 4 - AuthService edge cases:
- logout_all_devices
- _enforce_session_limit (deny / revoke_oldest)
- _enforce_device_limit (deny)
- _check_new_device_alert
- _audit_log
"""
import pytest
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_app():
    from tenxyte.models import Application
    app, _ = Application.create_application(name="AuthSvcTestApp")
    return app


def _make_user(email, password="TestPass1!"):
    from tenxyte.models import User
    user = User.objects.create(email=email, is_active=True)
    user.set_password(password)
    user.save()
    return user


def _make_refresh_token(user, app, device_info="", expired=False):
    from tenxyte.models import RefreshToken
    rt = RefreshToken.generate(
        user=user,
        application=app,
        ip_address="1.2.3.4",
        device_info=device_info
    )
    if expired:
        rt.expires_at = timezone.now() - timedelta(hours=1)
        rt.save()
    return rt


# ─── logout_all_devices ───────────────────────────────────────────────────────

class TestLogoutAllDevices:

    @pytest.mark.django_db
    def test_revokes_all_active_tokens(self):
        app = _make_app()
        user = _make_user("logout_all@test.com")
        _make_refresh_token(user, app, "device1")
        _make_refresh_token(user, app, "device2")

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        count = svc.logout_all_devices(user, ip_address="1.2.3.4", application=app)

        assert count == 2
        from tenxyte.models import RefreshToken
        still_active = RefreshToken.objects.filter(user=user, is_revoked=False).count()
        assert still_active == 0

    @pytest.mark.django_db
    def test_returns_zero_when_no_active_tokens(self):
        app = _make_app()
        user = _make_user("logout_none@test.com")

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        count = svc.logout_all_devices(user)
        assert count == 0

    @pytest.mark.django_db
    def test_creates_audit_log_entry(self):
        app = _make_app()
        user = _make_user("logout_audit@test.com")
        _make_refresh_token(user, app)

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        from tenxyte.models import AuditLog
        before = AuditLog.objects.count()
        svc.logout_all_devices(user, ip_address="1.2.3.4", application=app)
        assert AuditLog.objects.count() > before


# ─── _enforce_session_limit ───────────────────────────────────────────────────

class TestEnforceSessionLimit:

    @pytest.mark.django_db
    def test_deny_when_limit_reached(self):
        from django.test import override_settings
        app = _make_app()
        user = _make_user("sess_deny@test.com")
        user.max_sessions = 1
        user.save()
        _make_refresh_token(user, app)  # 1 active session → limit atteinte

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny'):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")

        assert result is not None
        ok, _, msg = result
        assert ok is False
        assert "Session limit" in msg

    @pytest.mark.django_db
    def test_revoke_oldest_when_limit_reached(self):
        from django.test import override_settings
        from tenxyte.models import RefreshToken
        app = _make_app()
        user = _make_user("sess_revoke@test.com")
        user.max_sessions = 1
        user.save()
        old_rt = _make_refresh_token(user, app, "device_old")

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='revoke_oldest'):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")

        # Ne retourne pas d'erreur, mais révoque l'ancienne session
        assert result is None
        old_rt.refresh_from_db()
        assert old_rt.is_revoked is True

    @pytest.mark.django_db
    def test_returns_none_when_disabled(self):
        from django.test import override_settings
        app = _make_app()
        user = _make_user("sess_disabled@test.com")

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_SESSION_LIMIT_ENABLED=False):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")

        assert result is None

    @pytest.mark.django_db
    def test_expired_zombies_purged_before_counting(self):
        from django.test import override_settings
        from tenxyte.models import RefreshToken
        app = _make_app()
        user = _make_user("sess_zombie@test.com")
        user.max_sessions = 1
        user.save()
        # Créer un token expiré (zombie)
        _make_refresh_token(user, app, expired=True)

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny'):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")

        # Après purge des zombies, la limite n'est plus atteinte
        assert result is None


# ─── _enforce_device_limit ────────────────────────────────────────────────────

class TestEnforceDeviceLimit:

    @pytest.mark.django_db
    def test_deny_when_device_limit_reached(self):
        from django.test import override_settings
        app = _make_app()
        user = _make_user("dev_deny@test.com")
        user.max_devices = 1
        user.save()
        _make_refresh_token(user, app, device_info='v=1|os=android|device=mobile')

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_DEVICE_LIMIT_ACTION='deny'):
            result = svc._enforce_device_limit(
                user, app, "1.2.3.4", device_info='v=1|os=ios|device=mobile'
            )

        assert result is not None
        ok, _, msg = result
        assert ok is False
        assert "Device limit" in msg

    @pytest.mark.django_db
    def test_returns_none_when_disabled(self):
        from django.test import override_settings
        app = _make_app()
        user = _make_user("dev_disabled@test.com")

        from tenxyte.services.auth_service import AuthService
        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        with override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=False):
            result = svc._enforce_device_limit(user, app, "1.2.3.4")

        assert result is None


# ─── _check_new_device_alert ─────────────────────────────────────────────────

class TestCheckNewDeviceAlert:

    @pytest.mark.django_db
    def test_no_alert_for_known_device(self):
        app = _make_app()
        user = _make_user("known_device@test.com")
        # Créer un token avec ce device
        device = 'v=1|os=android|device=mobile'
        _make_refresh_token(user, app, device_info=device)

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        from tenxyte.models import AuditLog
        before = AuditLog.objects.filter(action='new_device_detected').count()
        svc._check_new_device_alert(user, device, "1.2.3.4", app)
        after = AuditLog.objects.filter(action='new_device_detected').count()
        assert after == before  # Pas d'alerte car device connu

    @pytest.mark.django_db
    def test_alert_for_new_device(self):
        app = _make_app()
        user = _make_user("new_device@test.com")

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        from tenxyte.models import AuditLog
        before = AuditLog.objects.filter(action='new_device_detected').count()
        svc._check_new_device_alert(
            user, 'v=1|os=ios|device=mobile', "1.2.3.4", app
        )
        after = AuditLog.objects.filter(action='new_device_detected').count()
        assert after > before


# ─── _audit_log ──────────────────────────────────────────────────────────────

class TestAuditLog:

    @pytest.mark.django_db
    def test_creates_audit_entry_when_enabled(self):
        from django.test import override_settings
        from tenxyte.models import AuditLog
        app = _make_app()
        user = _make_user("auditlog_on@test.com")

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        before = AuditLog.objects.count()
        with override_settings(TENXYTE_AUDIT_LOGGING_ENABLED=True):
            svc._audit_log("test_action", user, "1.2.3.4", app, {"detail": "ok"})
        assert AuditLog.objects.count() > before

    @pytest.mark.django_db
    def test_no_entry_when_disabled(self):
        from django.test import override_settings
        from tenxyte.models import AuditLog
        app = _make_app()
        user = _make_user("auditlog_off@test.com")

        from tenxyte.services.auth_service import AuthService
        svc = AuthService()
        before = AuditLog.objects.count()
        with override_settings(TENXYTE_AUDIT_LOGGING_ENABLED=False):
            svc._audit_log("test_action", user, "1.2.3.4", app)
        assert AuditLog.objects.count() == before
