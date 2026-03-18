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
from datetime import timedelta

from tenxyte.models import User, Application, RefreshToken, AuditLog
from tests.integration.django.auth_service_compat import AuthService


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_app():
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        count = svc.logout_all_devices(user, ip_address="1.2.3.4", application=app)

        assert count == 2
        from tenxyte.models import RefreshToken
        still_active = RefreshToken.objects.filter(user=user, is_revoked=False).count()
        assert still_active == 0

    @pytest.mark.django_db
    def test_returns_zero_when_no_active_tokens(self):
        _make_app()
        user = _make_user("logout_none@test.com")

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        count = svc.logout_all_devices(user)
        assert count == 0

    @pytest.mark.django_db
    def test_creates_audit_log_entry(self):
        app = _make_app()
        user = _make_user("logout_audit@test.com")
        _make_refresh_token(user, app)

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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
        app = _make_app()
        user = _make_user("sess_revoke@test.com")
        user.max_sessions = 1
        user.save()
        old_rt = _make_refresh_token(user, app, "device_old")

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        with override_settings(TENXYTE_SESSION_LIMIT_ENABLED=False):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")

        assert result is None

    @pytest.mark.django_db
    def test_expired_zombies_purged_before_counting(self):
        from django.test import override_settings
        app = _make_app()
        user = _make_user("sess_zombie@test.com")
        user.max_sessions = 1
        user.save()
        # Créer un token expiré (zombie)
        _make_refresh_token(user, app, expired=True)

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
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

        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        before = AuditLog.objects.count()
        with override_settings(TENXYTE_AUDIT_LOGGING_ENABLED=False):
            svc._audit_log("test_action", user, "1.2.3.4", app)
        assert AuditLog.objects.count() == before

class TestAuthServiceAdditionalEdgeCases:
    def test_lockout_duration_minutes_property(self):
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        from tenxyte.conf import auth_settings
        svc = AuthService()
        assert svc.lockout_duration_minutes == auth_settings.LOCKOUT_DURATION_MINUTES

    @pytest.mark.django_db
    def test_validate_application_invalid_secret(self):
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        app = _make_app()
        svc = AuthService()
        ok, res, msg = svc.validate_application(app.access_key, "wrongsecret")
        assert ok is False
        assert "Invalid access_secret" in msg

    @pytest.mark.django_db
    def test_validate_application_invalid_key(self):
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        ok, res, msg = svc.validate_application("wrongkey", "wrongsecret")
        assert ok is False
        assert "Invalid access_key" in msg

    @pytest.mark.django_db
    def test_enforce_session_limit_zero_is_unlimited(self):
        app = _make_app()
        user = _make_user("sess_unlimited@test.com")
        user.max_sessions = 0
        user.save()
        from django.test import override_settings
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        with override_settings(TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny'):
            result = svc._enforce_session_limit(user, app, "1.2.3.4")
            assert result is None

    @pytest.mark.django_db
    def test_enforce_device_limit_zero_is_unlimited(self):
        app = _make_app()
        user = _make_user("dev_unlimited@test.com")
        user.max_devices = 0
        user.save()
        from django.test import override_settings
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        with override_settings(TENXYTE_DEVICE_LIMIT_ACTION='deny'):
            result = svc._enforce_device_limit(user, app, "1.2.3.4", device_info="foo")
            assert result is None

    @pytest.mark.django_db
    def test_enforce_device_limit_unknown_device_zombie_check(self):
        app = _make_app()
        user = _make_user("dev_unknown_zom@test.com")
        user.max_devices = 1
        user.save()
        _make_refresh_token(user, app, device_info="", expired=True) # Unknown device zombie
        from django.test import override_settings
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        with override_settings(TENXYTE_DEVICE_LIMIT_ACTION='deny'):
            result = svc._enforce_device_limit(user, app, "1.2.3.4", device_info="newdev")
            assert result is None

    @pytest.mark.django_db
    def test_enforce_device_limit_revoke_oldest(self):
        from django.utils import timezone
        import datetime
        app = _make_app()
        user = _make_user("dev_revoke_oldest@test.com")
        user.max_devices = 1
        user.save()
        
        dev_str = "v=1|os=android|device=mobile"
        
        rt1 = _make_refresh_token(user, app, device_info=dev_str) # First old
        rt1.created_at = timezone.now() - datetime.timedelta(days=2)
        rt1.save()
        
        rt2 = _make_refresh_token(user, app, device_info=dev_str) # Second old, same device
        rt2.created_at = timezone.now() - datetime.timedelta(days=1)
        rt2.save()
        
        _make_refresh_token(user, app, device_info="") # Unknown device
        # Created now, so it's the newest.
        
        from django.test import override_settings
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        
        with override_settings(TENXYTE_DEVICE_LIMIT_ACTION='revoke_oldest'):
            # The oldest is rt1.
            # The method should revoke all tokens for dev_str.
            result = svc._enforce_device_limit(user, app, "1.2.3.4", device_info="v=1|os=ios|device=mobile")
            assert result is None
            
            from tenxyte.models import RefreshToken
            assert RefreshToken.objects.filter(user=user, device_info=dev_str, is_revoked=False).count() == 0
            
            # Now unknown device token is the oldest because old tokens are revoked.
            result2 = svc._enforce_device_limit(user, app, "1.2.3.4", device_info="v=1|os=windows|device=desktop")
            assert result2 is None
            
            assert RefreshToken.objects.filter(user=user, device_info="", is_revoked=False).count() == 0

    @pytest.mark.django_db
    def test_check_new_device_alert_email_fail(self):
        app = _make_app()
        user = _make_user("new_dev_email_fail@test.com")
        # AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
        svc = AuthService()
        with patch("tenxyte.services.email_service.EmailService") as MockService:
            MockService.return_value.send_security_alert_email.side_effect = Exception("Email Failed")
            # Should catch exception and not crash
            svc._check_new_device_alert(user, "device1", "1.2.3.4", app)
