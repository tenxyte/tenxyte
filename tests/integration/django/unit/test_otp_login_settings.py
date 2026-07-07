"""
Tests for new OTP login settings defaults (AuthSettingsMixin) and
non-regression on preexisting auth_settings defaults.

Covers:
- OTP_LOGIN_ENABLED, OTP_LOGIN_AUTO_REGISTER, OTP_LOGIN_VALIDITY_MINUTES defaults
- No change to preexisting AuthSettingsMixin defaults (TOTP/OTP/password/lockout/
  refresh-token-cookie settings) now that the three new properties were added

Requirements: 5.1, 5.2, 5.3, 8.7
"""
from unittest.mock import MagicMock, patch

from django.test import override_settings

from tenxyte.conf import TenxyteSettings


def _get_no_mode(name: str):
    """
    Resolve a TenxyteSettings property against a mock Django settings object
    with no TENXYTE_* attributes and no DEBUG (so no secure-mode preset and no
    auto-dev preset kick in) — isolates the hardcoded default in conf/*.py.
    """
    s = TenxyteSettings()
    mock = MagicMock(spec=[])  # no attributes at all, including DEBUG
    with patch('tenxyte.conf.base.settings', mock):
        return getattr(s, name)


class TestOTPLoginSettingsDefaults:
    """Requirements 5.1, 5.2, 5.3: new settings default values."""

    def test_otp_login_enabled_defaults_to_false(self):
        assert _get_no_mode('OTP_LOGIN_ENABLED') is False

    def test_otp_login_auto_register_defaults_to_true(self):
        assert _get_no_mode('OTP_LOGIN_AUTO_REGISTER') is True

    def test_otp_login_validity_minutes_defaults_to_10(self):
        assert _get_no_mode('OTP_LOGIN_VALIDITY_MINUTES') == 10


class TestOTPLoginSettingsOverride:
    """
    Regression coverage: settings.py overrides via TENXYTE_OTP_LOGIN_* must
    actually take effect. This guards against the double-prefix bug where
    AuthSettingsMixin._get() was called with an already-prefixed name
    (e.g. "TENXYTE_OTP_LOGIN_ENABLED" instead of "OTP_LOGIN_ENABLED"),
    causing the lookup to silently always fall back to the hardcoded default.
    """

    def test_otp_login_enabled_override_takes_effect(self):
        s = TenxyteSettings()
        with override_settings(TENXYTE_OTP_LOGIN_ENABLED=True):
            assert s.OTP_LOGIN_ENABLED is True

    def test_otp_login_auto_register_override_takes_effect(self):
        s = TenxyteSettings()
        with override_settings(TENXYTE_OTP_LOGIN_AUTO_REGISTER=False):
            assert s.OTP_LOGIN_AUTO_REGISTER is False

    def test_otp_login_validity_minutes_override_takes_effect(self):
        s = TenxyteSettings()
        with override_settings(TENXYTE_OTP_LOGIN_VALIDITY_MINUTES=5):
            assert s.OTP_LOGIN_VALIDITY_MINUTES == 5


class TestAuthSettingsMixinNonRegression:
    """
    Requirement 8.7: adding OTP_LOGIN_* properties must not change any
    preexisting AuthSettingsMixin default value.
    """

    def test_totp_and_backup_codes_defaults_unchanged(self):
        assert _get_no_mode('TOTP_ISSUER') == 'MyApp'
        assert _get_no_mode('TOTP_VALID_WINDOW') == 1
        assert _get_no_mode('BACKUP_CODES_COUNT') == 10

    def test_preexisting_otp_defaults_unchanged(self):
        assert _get_no_mode('OTP_LENGTH') == 6
        assert _get_no_mode('OTP_EMAIL_VALIDITY') == 15
        assert _get_no_mode('OTP_PHONE_VALIDITY') == 10
        assert _get_no_mode('OTP_MAX_ATTEMPTS') == 5

    def test_password_policy_defaults_unchanged(self):
        assert _get_no_mode('PASSWORD_MIN_LENGTH') == 8
        assert _get_no_mode('PASSWORD_MIN_LENGTH_NO_MFA') == 0
        assert _get_no_mode('PASSWORD_MAX_LENGTH') == 128
        assert _get_no_mode('BCRYPT_ROUNDS') == 12
        assert _get_no_mode('PASSWORD_REQUIRE_UPPERCASE') is True
        assert _get_no_mode('PASSWORD_REQUIRE_LOWERCASE') is True
        assert _get_no_mode('PASSWORD_REQUIRE_DIGIT') is True
        assert _get_no_mode('PASSWORD_REQUIRE_SPECIAL') is True
        assert _get_no_mode('PASSWORD_HISTORY_ENABLED') is True
        assert _get_no_mode('PASSWORD_HISTORY_COUNT') == 5

    def test_social_and_agent_defaults_unchanged(self):
        assert _get_no_mode('SOCIAL_REQUIRE_VERIFIED_EMAIL') is True
        assert _get_no_mode('AGENT_ACTION_RETENTION_DAYS') == 7
        assert _get_no_mode('PURGE_IP_ON_DELETION') is False

    def test_lockout_defaults_unchanged(self):
        assert _get_no_mode('MAX_LOGIN_ATTEMPTS') == 5
        assert _get_no_mode('LOCKOUT_DURATION_MINUTES') == 30
        assert _get_no_mode('ACCOUNT_LOCKOUT_ENABLED') is True
        assert _get_no_mode('LOCKOUT_ESCALATION_ENABLED') is True
        assert _get_no_mode('LOCKOUT_MAX_DURATION_MINUTES') == 1440

    def test_refresh_token_cookie_defaults_unchanged(self):
        assert _get_no_mode('REFRESH_TOKEN_COOKIE_ENABLED') is False
        assert _get_no_mode('REFRESH_TOKEN_COOKIE_NAME') == 'tenxyte_refresh'
        assert _get_no_mode('REFRESH_TOKEN_COOKIE_SAMESITE') == 'Strict'
        assert _get_no_mode('REFRESH_TOKEN_COOKIE_PATH') == '/api/v1/auth/'
