"""
Tests unitaires pour le réglage FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED.

Vérifie :
- La valeur par défaut est False
- Aucune valeur par défaut d'un setting préexistant n'a changé

Feature: force_password_change_on_first_login
Validates: Requirements 6.1, 6.3, 7.2
"""
import pytest
from django.test import override_settings
from tenxyte.conf import auth_settings


class TestForcePasswordChangeSettingDefault:
    """Vérifie la valeur par défaut du nouveau réglage."""

    def test_force_password_change_enabled_defaults_to_false(self):
        """FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED doit valoir False par défaut."""
        assert auth_settings.FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED is False

    def test_setting_is_accessible_on_auth_settings(self):
        """Le réglage doit être accessible via auth_settings."""
        value = auth_settings.FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED
        assert isinstance(value, bool)

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_setting_override_takes_effect(self):
        """override_settings doit être pris en compte."""
        assert auth_settings.FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED is True


class TestExistingSettingsNonRegression:
    """Vérifie qu'aucun réglage préexistant n'a changé de valeur par défaut."""

    def test_otp_login_enabled_still_false(self):
        assert auth_settings.OTP_LOGIN_ENABLED is False

    def test_otp_login_auto_register_still_true(self):
        assert auth_settings.OTP_LOGIN_AUTO_REGISTER is True

    def test_otp_login_validity_minutes_still_10(self):
        assert auth_settings.OTP_LOGIN_VALIDITY_MINUTES == 10

    def test_bcrypt_rounds_still_12(self):
        assert auth_settings.BCRYPT_ROUNDS == 12

    def test_password_min_length_still_8(self):
        assert auth_settings.PASSWORD_MIN_LENGTH == 8

    def test_max_login_attempts_still_5(self):
        assert auth_settings.MAX_LOGIN_ATTEMPTS == 5

    def test_account_lockout_enabled_still_true(self):
        assert auth_settings.ACCOUNT_LOCKOUT_ENABLED is True

    def test_refresh_token_cookie_enabled_still_false(self):
        assert auth_settings.REFRESH_TOKEN_COOKIE_ENABLED is False
