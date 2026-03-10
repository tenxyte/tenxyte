"""
Tests auth_service.py — méthodes non couvertes.

Coverage cible : services/auth_service.py (51% → 85%)
Couvre : logout, logout_all_devices, refresh_access_token (rotation ON/OFF),
         register_user, change_password, _enforce_session_limit,
         _enforce_device_limit, _check_new_device_alert, generate_tokens_for_user.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import override_settings
from datetime import timedelta

from tenxyte.models import User, Application, RefreshToken, AuditLog
from tenxyte.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="AuthSvcApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, password="Pass123!"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _refresh_token(user, app, expired=False, revoked=False):
    # R1: RefreshToken.generate() returns instance with _raw_token attached
    # (token field in DB is SHA-256 hash; _raw_token is needed to call services)
    rt = RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4")
    if expired:
        rt.expires_at = timezone.now() - timedelta(days=1)
        rt.save()
    if revoked:
        rt.is_revoked = True
        rt.save()
    return rt


# ===========================================================================
# logout
# ===========================================================================

class TestLogout:

    @pytest.mark.django_db
    def test_logout_revokes_refresh_token(self):
        app = _app("LogoutApp1")
        user = _user("logout1@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        # R1: rt.token is the SHA-256 hash; must use _raw_token for service calls
        result = service.logout(rt._raw_token)

        assert result is True
        rt.refresh_from_db()
        assert rt.is_revoked is True

    @pytest.mark.django_db
    def test_logout_invalid_token_returns_false(self):
        service = AuthService()
        result = service.logout("nonexistent-token-xyz")
        assert result is False

    @pytest.mark.django_db
    def test_logout_blacklists_access_token_when_provided(self):
        app = _app("LogoutApp2")
        user = _user("logout2@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        # R1: must use _raw_token since service looks up by raw value
        with patch.object(service.jwt_service, 'blacklist_token') as mock_bl:
            service.logout(rt._raw_token, access_token="fake.access.token")

        mock_bl.assert_called_once_with("fake.access.token", user, 'logout')

    @pytest.mark.django_db
    def test_logout_no_blacklist_when_no_access_token(self):
        app = _app("LogoutApp3")
        user = _user("logout3@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        # R1: must use _raw_token since service looks up by raw value
        with patch.object(service.jwt_service, 'blacklist_token') as mock_bl:
            service.logout(rt._raw_token, access_token=None)

        mock_bl.assert_not_called()


# ===========================================================================
# logout_all_devices
# ===========================================================================

class TestLogoutAllDevices:

    @pytest.mark.django_db
    def test_revokes_all_active_tokens(self):
        app = _app("LogoutAllApp1")
        user = _user("logoutall1@test.com")
        rt1 = _refresh_token(user, app)
        rt2 = _refresh_token(user, app)
        rt3 = _refresh_token(user, app)

        service = AuthService()
        count = service.logout_all_devices(user)

        assert count == 3
        for rt in [rt1, rt2, rt3]:
            rt.refresh_from_db()
            assert rt.is_revoked is True

    @pytest.mark.django_db
    def test_does_not_count_already_revoked(self):
        app = _app("LogoutAllApp2")
        user = _user("logoutall2@test.com")
        _refresh_token(user, app, revoked=True)
        rt2 = _refresh_token(user, app)

        service = AuthService()
        count = service.logout_all_devices(user)

        assert count == 1

    @pytest.mark.django_db
    def test_blacklists_access_token_when_provided(self):
        app = _app("LogoutAllApp3")
        user = _user("logoutall3@test.com")
        _refresh_token(user, app)

        service = AuthService()
        with patch.object(service.jwt_service, 'blacklist_token') as mock_bl:
            service.logout_all_devices(user, access_token="my.access.token")

        mock_bl.assert_called_once_with("my.access.token", user, 'logout_all')

    @pytest.mark.django_db
    def test_returns_zero_when_no_active_tokens(self):
        app = _app("LogoutAllApp4")
        user = _user("logoutall4@test.com")

        service = AuthService()
        count = service.logout_all_devices(user)

        assert count == 0


# ===========================================================================
# refresh_access_token
# ===========================================================================

class TestRefreshAccessToken:

    @pytest.mark.django_db
    @override_settings(TENXYTE_REFRESH_TOKEN_ROTATION=False)
    def test_refresh_returns_new_access_token(self):
        app = _app("RefreshApp1")
        user = _user("refresh1@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        # R1: must use _raw_token since service looks up by raw value
        success, data, error = service.refresh_access_token(rt._raw_token, app)

        assert success is True
        assert 'access_token' in data
        assert error == ''

    @pytest.mark.django_db
    def test_refresh_invalid_token_returns_error(self):
        app = _app("RefreshApp2")
        service = AuthService()
        success, data, error = service.refresh_access_token("bad-token", app)

        assert success is False
        assert data is None
        assert 'Invalid' in error

    @pytest.mark.django_db
    def test_refresh_expired_token_returns_error(self):
        app = _app("RefreshApp3")
        user = _user("refresh3@test.com")
        rt = _refresh_token(user, app, expired=True)

        service = AuthService()
        # R1: must use _raw_token since service looks up by raw value
        success, data, error = service.refresh_access_token(rt._raw_token, app)

        assert success is False
        assert 'expired' in error.lower() or 'revoked' in error.lower()

    @pytest.mark.django_db
    def test_refresh_revoked_token_returns_error(self):
        app = _app("RefreshApp4")
        user = _user("refresh4@test.com")
        rt = _refresh_token(user, app, revoked=True)

        service = AuthService()
        success, data, error = service.refresh_access_token(rt.token, app)

        assert success is False

    @pytest.mark.django_db
    @override_settings(TENXYTE_REFRESH_TOKEN_ROTATION=True)
    def test_refresh_with_rotation_creates_new_token(self):
        app = _app("RefreshApp5")
        user = _user("refresh5@test.com")
        rt = _refresh_token(user, app)
        old_token_str = rt.token

        service = AuthService()
        # R1: capture raw before calling refresh (rotation will revoke old token)
        raw_token_str = rt._raw_token
        success, data, error = service.refresh_access_token(raw_token_str, app)

        assert success is True
        # Old token should be revoked
        rt.refresh_from_db()
        assert rt.is_revoked is True
        # New refresh token should differ from the original raw token
        assert data['refresh_token'] != raw_token_str

    @pytest.mark.django_db
    def test_refresh_wrong_application_returns_error(self):
        app1 = _app("RefreshApp6a")
        app2 = _app("RefreshApp6b")
        user = _user("refresh6@test.com")
        rt = _refresh_token(user, app1)

        service = AuthService()
        # R1: must use _raw_token since service looks up by raw value
        success, data, error = service.refresh_access_token(rt._raw_token, app2)

        assert success is False


# ===========================================================================
# register_user
# ===========================================================================

class TestRegisterUser:

    @pytest.mark.django_db
    def test_register_with_email_succeeds(self):
        app = _app("RegisterApp1")
        service = AuthService()
        success, user, error = service.register_user(
            email="newuser@test.com",
            password="Pass123!",
            ip_address="1.2.3.4",
            application=app
        )

        assert success is True
        assert user is not None
        assert user.email == "newuser@test.com"
        assert error == ''

    @pytest.mark.django_db
    def test_register_duplicate_email_fails(self):
        app = _app("RegisterApp2")
        _user("dup@test.com")
        service = AuthService()
        success, user, error = service.register_user(
            email="dup@test.com",
            password="Pass123!",
            application=app
        )

        assert success is False
        assert 'already registered' in error

    @pytest.mark.django_db
    def test_register_without_email_or_phone_fails(self):
        app = _app("RegisterApp3")
        service = AuthService()
        success, user, error = service.register_user(
            password="Pass123!",
            application=app
        )

        assert success is False
        assert 'required' in error.lower()

    @pytest.mark.django_db
    def test_register_without_password_fails(self):
        app = _app("RegisterApp4")
        service = AuthService()
        success, user, error = service.register_user(
            email="nopwd@test.com",
            application=app
        )

        assert success is False
        assert 'Password' in error

    @pytest.mark.django_db
    def test_register_with_phone_succeeds(self):
        app = _app("RegisterApp5")
        service = AuthService()
        success, user, error = service.register_user(
            phone_country_code="33",
            phone_number="612345678",
            password="Pass123!",
            ip_address="1.2.3.4",
            application=app
        )

        assert success is True
        assert user.phone_number == "612345678"

    @pytest.mark.django_db
    def test_register_duplicate_phone_fails(self):
        app = _app("RegisterApp6")
        existing = User.objects.create(
            phone_country_code="33",
            phone_number="699999999",
            is_active=True
        )
        existing.set_password("Pass123!")
        existing.save()

        service = AuthService()
        success, user, error = service.register_user(
            phone_country_code="33",
            phone_number="699999999",
            password="Pass123!",
            application=app
        )

        assert success is False
        assert 'already registered' in error


# ===========================================================================
# change_password
# ===========================================================================

class TestChangePassword:

    @pytest.mark.django_db
    def test_change_password_success(self):
        app = _app("ChangePwdApp1")
        user = _user("changepwd1@test.com", "OldPass123!")
        service = AuthService()

        success, error = service.change_password(
            user=user,
            old_password="OldPass123!",
            new_password="NewPass456!",
            application=app
        )

        assert success is True
        assert error == ''
        user.refresh_from_db()
        assert user.check_password("NewPass456!")

    @pytest.mark.django_db
    def test_change_password_wrong_old_password(self):
        user = _user("changepwd2@test.com", "OldPass123!")
        service = AuthService()

        success, error = service.change_password(
            user=user,
            old_password="WrongPass!",
            new_password="NewPass456!"
        )

        assert success is False
        assert 'Invalid' in error

    @pytest.mark.django_db
    @override_settings(TENXYTE_PASSWORD_HISTORY_ENABLED=True, TENXYTE_PASSWORD_HISTORY_COUNT=5)
    def test_change_password_history_check(self):
        from tenxyte.models import PasswordHistory
        app = _app("ChangePwdApp3")
        user = _user("changepwd3@test.com", "OldPass123!")
        service = AuthService()

        # First change: OldPass123! → NewPass456! (adds OldPass123! to history)
        service.change_password(user, "OldPass123!", "NewPass456!", application=app)
        # Second change: NewPass456! → AnotherPass789! (adds NewPass456! to history)
        service.change_password(user, "NewPass456!", "AnotherPass789!", application=app)

        # Try to reuse NewPass456! — should fail (it's in history)
        success, error = service.change_password(
            user=user,
            old_password="AnotherPass789!",
            new_password="NewPass456!",
            application=app
        )

        assert success is False
        assert 'used recently' in error


# ===========================================================================
# _enforce_session_limit
# ===========================================================================

class TestEnforceSessionLimit:

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=False)
    def test_no_limit_when_disabled(self):
        app = _app("SessionLimitApp1")
        user = _user("sessionlimit1@test.com")
        service = AuthService()

        result = service._enforce_session_limit(user, app, "1.2.3.4")

        assert result is None

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_SESSIONS=0)
    def test_no_limit_when_max_is_zero(self):
        app = _app("SessionLimitApp2")
        user = _user("sessionlimit2@test.com")
        service = AuthService()

        result = service._enforce_session_limit(user, app, "1.2.3.4")

        assert result is None

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_SESSIONS=2,
                       TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny')
    def test_deny_action_when_limit_exceeded(self):
        app = _app("SessionLimitApp3")
        user = _user("sessionlimit3@test.com")
        # Create 2 active sessions
        _refresh_token(user, app)
        _refresh_token(user, app)

        service = AuthService()
        result = service._enforce_session_limit(user, app, "1.2.3.4")

        assert result is not None
        success, data, error = result
        assert success is False
        assert 'Session limit' in error

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_SESSIONS=2,
                       TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='revoke_oldest')
    def test_revoke_oldest_action_when_limit_exceeded(self):
        app = _app("SessionLimitApp4")
        user = _user("sessionlimit4@test.com")
        rt1 = _refresh_token(user, app)
        rt2 = _refresh_token(user, app)

        service = AuthService()
        result = service._enforce_session_limit(user, app, "1.2.3.4")

        # Should return None (allowed) but revoke the oldest
        assert result is None
        rt1.refresh_from_db()
        assert rt1.is_revoked is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_SESSIONS=2,
                       TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny')
    def test_zombie_purge_allows_new_session(self):
        app = _app("SessionLimitApp5")
        user = _user("sessionlimit5@test.com")
        # Create 2 expired (zombie) tokens
        _refresh_token(user, app, expired=True)
        _refresh_token(user, app, expired=True)

        service = AuthService()
        result = service._enforce_session_limit(user, app, "1.2.3.4")

        # Zombies purged → active_sessions = 0 < 2 → allowed
        assert result is None


# ===========================================================================
# _enforce_device_limit
# ===========================================================================

class TestEnforceDeviceLimit:

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=False)
    def test_no_limit_when_disabled(self):
        app = _app("DeviceLimitApp1")
        user = _user("devicelimit1@test.com")
        service = AuthService()

        result = service._enforce_device_limit(user, app, "1.2.3.4", "device_a")

        assert result is None

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_DEVICES=0)
    def test_no_limit_when_max_is_zero(self):
        app = _app("DeviceLimitApp2")
        user = _user("devicelimit2@test.com")
        service = AuthService()

        result = service._enforce_device_limit(user, app, "1.2.3.4", "device_a")

        assert result is None

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_DEVICES=1)
    def test_known_device_always_allowed(self):
        app = _app("DeviceLimitApp3")
        user = _user("devicelimit3@test.com")
        device = 'v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122'
        # Create token with same device
        RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4", device_info=device)

        service = AuthService()
        result = service._enforce_device_limit(user, app, "1.2.3.4", device)

        assert result is None

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_DEVICES=1,
                       TENXYTE_DEVICE_LIMIT_ACTION='deny')
    def test_deny_action_when_device_limit_exceeded(self):
        app = _app("DeviceLimitApp4")
        user = _user("devicelimit4@test.com")
        device_a = 'v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122'
        RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4", device_info=device_a)

        service = AuthService()
        # device_b has different os+device — not matching device_a, so active_devices=1 >= max=1 → deny
        device_b = 'v=1|os=ios;osv=17|device=mobile|arch=arm64|runtime=safari;rtv=17'
        result = service._enforce_device_limit(user, app, "5.6.7.8", device_b)

        assert result is not None
        success, data, error = result
        assert success is False
        assert 'Device limit' in error


# ===========================================================================
# _check_new_device_alert
# ===========================================================================

class TestCheckNewDeviceAlert:

    @pytest.mark.django_db
    def test_no_alert_for_empty_device_info(self):
        app = _app("NewDeviceApp1")
        user = _user("newdevice1@test.com")
        service = AuthService()

        # Should not raise
        service._check_new_device_alert(user, '', "1.2.3.4", app)

    @pytest.mark.django_db
    def test_alert_sent_for_new_device(self):
        app = _app("NewDeviceApp2")
        user = _user("newdevice2@test.com")
        service = AuthService()
        device = '{"browser": "Chrome", "os": "Windows", "device_type": "desktop"}'

        with patch('tenxyte.services.email_service.EmailService.send_security_alert_email', return_value=True) as mock_email:
            service._check_new_device_alert(user, device, "1.2.3.4", app)

        mock_email.assert_called_once()

    @pytest.mark.django_db
    def test_no_alert_for_known_device(self):
        app = _app("NewDeviceApp3")
        user = _user("newdevice3@test.com")
        device = '{"browser": "Chrome", "os": "Windows", "device_type": "desktop"}'
        # Register the device first
        RefreshToken.generate(user=user, application=app, ip_address="1.2.3.4", device_info=device)

        service = AuthService()
        with patch('tenxyte.services.email_service.EmailService.send_security_alert_email') as mock_email:
            service._check_new_device_alert(user, device, "1.2.3.4", app)

        mock_email.assert_not_called()

    @pytest.mark.django_db
    def test_no_email_when_user_has_no_email(self):
        app = _app("NewDeviceApp4")
        user = User.objects.create(
            phone_country_code="33",
            phone_number="611111111",
            is_active=True
        )
        user.set_password("Pass123!")
        user.save()

        device = '{"browser": "Safari", "os": "iOS", "device_type": "mobile"}'
        service = AuthService()

        with patch('tenxyte.services.email_service.EmailService.send_security_alert_email') as mock_email:
            service._check_new_device_alert(user, device, "1.2.3.4", app)

        mock_email.assert_not_called()


# ===========================================================================
# generate_tokens_for_user
# ===========================================================================

class TestGenerateTokensForUser:

    @pytest.mark.django_db
    def test_returns_token_pair(self):
        app = _app("GenTokensApp1")
        user = _user("gentokens1@test.com")
        service = AuthService()

        result = service.generate_tokens_for_user(
            user=user,
            application=app,
            ip_address="1.2.3.4"
        )

        assert 'access_token' in result
        assert 'refresh_token' in result
        assert 'token_type' in result
        assert 'expires_in' in result

    @pytest.mark.django_db
    def test_updates_last_login(self):
        app = _app("GenTokensApp2")
        user = _user("gentokens2@test.com")
        user.last_login = None
        user.save()

        service = AuthService()
        service.generate_tokens_for_user(user=user, application=app, ip_address="1.2.3.4")

        user.refresh_from_db()
        assert user.last_login is not None

    @pytest.mark.django_db
    def test_creates_refresh_token_in_db(self):
        app = _app("GenTokensApp3")
        user = _user("gentokens3@test.com")
        service = AuthService()

        before_count = RefreshToken.objects.filter(user=user).count()
        service.generate_tokens_for_user(user=user, application=app, ip_address="1.2.3.4")
        after_count = RefreshToken.objects.filter(user=user).count()

        assert after_count == before_count + 1

# ===========================================================================
# dummy hash / timing attack mitigation (VULN-001)
# ===========================================================================

class TestDummyHashTimingAttackMitigation:

    @pytest.mark.django_db
    def test_get_dummy_hash_generates_and_caches(self):
        AuthService._DUMMY_HASH = None
        hash1 = AuthService._get_dummy_hash()
        assert hash1 is not None
        assert hash1.startswith('$2')  # bcrypt prefix
        
        # Second call should return the exact same cached string
        hash2 = AuthService._get_dummy_hash()
        assert hash1 == hash2

    @pytest.mark.django_db
    def test_authenticate_by_email_uses_dummy_hash_when_user_not_found(self):
        app = _app("DummyApp1")
        service = AuthService()
        
        with patch('tenxyte.models.User.check_password') as mock_checkpw:
            success, data, error = service.authenticate_by_email("nonexistent@test.com", "Pass123!", app, "1.2.3.4")
        
        assert success is False
        assert error == 'Invalid credentials'
        mock_checkpw.assert_called_once_with("Pass123!")

    @pytest.mark.django_db
    def test_authenticate_by_phone_uses_dummy_hash_when_user_not_found(self):
        app = _app("DummyApp2")
        service = AuthService()
        
        with patch('tenxyte.models.User.check_password') as mock_checkpw:
            success, data, error = service.authenticate_by_phone("33", "600000000", "Pass123!", app, "1.2.3.4")
        
        assert success is False
        assert error == 'Invalid credentials'
        mock_checkpw.assert_called_once_with("Pass123!")
