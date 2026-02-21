"""
Tests for TENXYTE_SHORTCUT_SECURE_MODE preset system.

Coverage targets:
- conf.py: TenxyteSettings._get() priority logic
- All three presets: starter, medium, robust
- Priority: settings.py > preset > default
- Invalid mode warning
"""
import warnings
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.conf import settings as django_settings

from tenxyte.conf import auth_settings, TenxyteSettings, SECURE_MODE_PRESETS, VALID_SECURE_MODES


def _settings_with_mode(mode: str, **extra):
    """
    Build a mock settings object that only has TENXYTE_SHORTCUT_SECURE_MODE
    and any extra explicit settings — simulating a clean project settings.py
    that only sets the mode (no individual TENXYTE_* overrides).
    """
    mock = MagicMock(spec=[])
    mock.TENXYTE_SHORTCUT_SECURE_MODE = mode
    for key, val in extra.items():
        setattr(mock, key, val)
    return mock


def _get_with_mode(name: str, mode: str, **extra):
    """Call TenxyteSettings._get() against a clean mock settings with the given mode."""
    s = TenxyteSettings()
    mock = _settings_with_mode(mode, **extra)
    with patch('tenxyte.conf.settings', mock):
        return getattr(s, name)


def _get_no_mode(name: str):
    """Call TenxyteSettings._get() against a clean mock settings with no mode set."""
    s = TenxyteSettings()
    mock = MagicMock(spec=[])  # no attributes at all
    with patch('tenxyte.conf.settings', mock):
        return getattr(s, name)


# ===========================================================================
# Preset dictionary integrity
# ===========================================================================

class TestPresetDefinitions:

    def test_all_three_modes_defined(self):
        assert 'starter' in SECURE_MODE_PRESETS
        assert 'medium' in SECURE_MODE_PRESETS
        assert 'robust' in SECURE_MODE_PRESETS

    def test_valid_secure_modes_matches_presets(self):
        assert VALID_SECURE_MODES == set(SECURE_MODE_PRESETS.keys())

    def test_starter_has_required_keys(self):
        preset = SECURE_MODE_PRESETS['starter']
        required = [
            'JWT_ACCESS_TOKEN_LIFETIME', 'JWT_REFRESH_TOKEN_LIFETIME',
            'REFRESH_TOKEN_ROTATION', 'ACCOUNT_LOCKOUT_ENABLED',
            'BREACH_CHECK_ENABLED', 'AUDIT_LOGGING_ENABLED',
        ]
        for key in required:
            assert key in preset, f"'starter' preset missing key: {key}"

    def test_medium_has_required_keys(self):
        preset = SECURE_MODE_PRESETS['medium']
        required = [
            'JWT_ACCESS_TOKEN_LIFETIME', 'BREACH_CHECK_ENABLED',
            'PASSWORD_HISTORY_ENABLED', 'AUDIT_LOGGING_ENABLED',
        ]
        for key in required:
            assert key in preset, f"'medium' preset missing key: {key}"

    def test_robust_has_required_keys(self):
        preset = SECURE_MODE_PRESETS['robust']
        required = [
            'JWT_ACCESS_TOKEN_LIFETIME', 'BREACH_CHECK_ENABLED',
            'WEBAUTHN_ENABLED', 'PASSWORD_HISTORY_COUNT',
        ]
        for key in required:
            assert key in preset, f"'robust' preset missing key: {key}"

    def test_starter_jwt_lifetime_longer_than_robust(self):
        assert SECURE_MODE_PRESETS['starter']['JWT_ACCESS_TOKEN_LIFETIME'] > \
               SECURE_MODE_PRESETS['robust']['JWT_ACCESS_TOKEN_LIFETIME']

    def test_robust_max_login_attempts_strictest(self):
        assert SECURE_MODE_PRESETS['robust']['MAX_LOGIN_ATTEMPTS'] < \
               SECURE_MODE_PRESETS['medium']['MAX_LOGIN_ATTEMPTS'] < \
               SECURE_MODE_PRESETS['starter']['MAX_LOGIN_ATTEMPTS']

    def test_robust_password_history_count_highest(self):
        assert SECURE_MODE_PRESETS['robust']['PASSWORD_HISTORY_COUNT'] > \
               SECURE_MODE_PRESETS['medium']['PASSWORD_HISTORY_COUNT']

    def test_starter_cors_allow_all_true(self):
        assert SECURE_MODE_PRESETS['starter']['CORS_ALLOW_ALL_ORIGINS'] is True

    def test_medium_robust_cors_allow_all_false(self):
        assert SECURE_MODE_PRESETS['medium']['CORS_ALLOW_ALL_ORIGINS'] is False
        assert SECURE_MODE_PRESETS['robust']['CORS_ALLOW_ALL_ORIGINS'] is False

    def test_robust_webauthn_enabled(self):
        assert SECURE_MODE_PRESETS['robust']['WEBAUTHN_ENABLED'] is True

    def test_starter_webauthn_disabled(self):
        assert SECURE_MODE_PRESETS['starter']['WEBAUTHN_ENABLED'] is False

    def test_robust_breach_check_enabled(self):
        assert SECURE_MODE_PRESETS['robust']['BREACH_CHECK_ENABLED'] is True

    def test_starter_breach_check_disabled(self):
        assert SECURE_MODE_PRESETS['starter']['BREACH_CHECK_ENABLED'] is False


# ===========================================================================
# Priority: no mode → defaults
# ===========================================================================

class TestNoPriorityMode:

    def test_no_mode_uses_default_jwt_lifetime(self):
        assert _get_no_mode('JWT_ACCESS_TOKEN_LIFETIME') == 3600

    def test_no_mode_uses_default_refresh_rotation(self):
        assert _get_no_mode('REFRESH_TOKEN_ROTATION') is True

    def test_no_mode_breach_check_disabled_by_default(self):
        assert _get_no_mode('BREACH_CHECK_ENABLED') is False

    def test_no_mode_webauthn_disabled_by_default(self):
        assert _get_no_mode('WEBAUTHN_ENABLED') is False

    def test_no_mode_password_history_enabled_by_default(self):
        assert _get_no_mode('PASSWORD_HISTORY_ENABLED') is True


# ===========================================================================
# Priority: starter preset
# ===========================================================================

class TestStarterPreset:

    def test_starter_jwt_access_lifetime(self):
        assert _get_with_mode('JWT_ACCESS_TOKEN_LIFETIME', 'starter') == 3600

    def test_starter_refresh_rotation_false(self):
        assert _get_with_mode('REFRESH_TOKEN_ROTATION', 'starter') is False

    def test_starter_breach_check_disabled(self):
        assert _get_with_mode('BREACH_CHECK_ENABLED', 'starter') is False

    def test_starter_password_history_disabled(self):
        assert _get_with_mode('PASSWORD_HISTORY_ENABLED', 'starter') is False

    def test_starter_audit_logging_disabled(self):
        assert _get_with_mode('AUDIT_LOGGING_ENABLED', 'starter') is False

    def test_starter_cors_allow_all(self):
        assert _get_with_mode('CORS_ALLOW_ALL_ORIGINS', 'starter') is True

    def test_starter_security_headers_disabled(self):
        assert _get_with_mode('SECURITY_HEADERS_ENABLED', 'starter') is False

    def test_starter_device_limit_disabled(self):
        assert _get_with_mode('TENXYTE_DEVICE_LIMIT_ENABLED', 'starter') is False

    def test_starter_session_limit_disabled(self):
        assert _get_with_mode('TENXYTE_SESSION_LIMIT_ENABLED', 'starter') is False

    def test_starter_max_login_attempts_relaxed(self):
        assert _get_with_mode('MAX_LOGIN_ATTEMPTS', 'starter') == 10


# ===========================================================================
# Priority: medium preset
# ===========================================================================

class TestMediumPreset:

    def test_medium_jwt_access_lifetime_15min(self):
        assert _get_with_mode('JWT_ACCESS_TOKEN_LIFETIME', 'medium') == 900

    def test_medium_refresh_rotation_true(self):
        assert _get_with_mode('REFRESH_TOKEN_ROTATION', 'medium') is True

    def test_medium_breach_check_enabled(self):
        assert _get_with_mode('BREACH_CHECK_ENABLED', 'medium') is True

    def test_medium_breach_check_reject(self):
        assert _get_with_mode('BREACH_CHECK_REJECT', 'medium') is True

    def test_medium_password_history_enabled(self):
        assert _get_with_mode('PASSWORD_HISTORY_ENABLED', 'medium') is True

    def test_medium_password_history_count(self):
        assert _get_with_mode('PASSWORD_HISTORY_COUNT', 'medium') == 5

    def test_medium_magic_link_enabled(self):
        assert _get_with_mode('MAGIC_LINK_ENABLED', 'medium') is True

    def test_medium_webauthn_disabled(self):
        assert _get_with_mode('WEBAUTHN_ENABLED', 'medium') is False

    def test_medium_audit_logging_enabled(self):
        assert _get_with_mode('AUDIT_LOGGING_ENABLED', 'medium') is True

    def test_medium_cors_allow_all_false(self):
        assert _get_with_mode('CORS_ALLOW_ALL_ORIGINS', 'medium') is False

    def test_medium_security_headers_enabled(self):
        assert _get_with_mode('SECURITY_HEADERS_ENABLED', 'medium') is True

    def test_medium_device_limit_enabled(self):
        assert _get_with_mode('TENXYTE_DEVICE_LIMIT_ENABLED', 'medium') is True

    def test_medium_max_devices(self):
        assert _get_with_mode('TENXYTE_DEFAULT_MAX_DEVICES', 'medium') == 5

    def test_medium_max_login_attempts(self):
        assert _get_with_mode('MAX_LOGIN_ATTEMPTS', 'medium') == 5


# ===========================================================================
# Priority: robust preset
# ===========================================================================

class TestRobustPreset:

    def test_robust_jwt_access_lifetime_5min(self):
        assert _get_with_mode('JWT_ACCESS_TOKEN_LIFETIME', 'robust') == 300

    def test_robust_jwt_refresh_lifetime_1day(self):
        assert _get_with_mode('JWT_REFRESH_TOKEN_LIFETIME', 'robust') == 86400

    def test_robust_refresh_rotation_true(self):
        assert _get_with_mode('REFRESH_TOKEN_ROTATION', 'robust') is True

    def test_robust_breach_check_enabled(self):
        assert _get_with_mode('BREACH_CHECK_ENABLED', 'robust') is True

    def test_robust_webauthn_enabled(self):
        assert _get_with_mode('WEBAUTHN_ENABLED', 'robust') is True

    def test_robust_magic_link_disabled(self):
        assert _get_with_mode('MAGIC_LINK_ENABLED', 'robust') is False

    def test_robust_password_history_count_12(self):
        assert _get_with_mode('PASSWORD_HISTORY_COUNT', 'robust') == 12

    def test_robust_max_login_attempts_3(self):
        assert _get_with_mode('MAX_LOGIN_ATTEMPTS', 'robust') == 3

    def test_robust_lockout_duration_60min(self):
        assert _get_with_mode('LOCKOUT_DURATION_MINUTES', 'robust') == 60

    def test_robust_device_limit_enabled(self):
        assert _get_with_mode('TENXYTE_DEVICE_LIMIT_ENABLED', 'robust') is True

    def test_robust_max_devices_2(self):
        assert _get_with_mode('TENXYTE_DEFAULT_MAX_DEVICES', 'robust') == 2

    def test_robust_device_limit_action_deny(self):
        assert _get_with_mode('TENXYTE_DEVICE_LIMIT_ACTION', 'robust') == 'deny'

    def test_robust_session_limit_enabled(self):
        assert _get_with_mode('TENXYTE_SESSION_LIMIT_ENABLED', 'robust') is True

    def test_robust_max_sessions_1(self):
        assert _get_with_mode('TENXYTE_DEFAULT_MAX_SESSIONS', 'robust') == 1

    def test_robust_cors_allow_all_false(self):
        assert _get_with_mode('CORS_ALLOW_ALL_ORIGINS', 'robust') is False

    def test_robust_security_headers_enabled(self):
        assert _get_with_mode('SECURITY_HEADERS_ENABLED', 'robust') is True

    def test_robust_audit_logging_enabled(self):
        assert _get_with_mode('AUDIT_LOGGING_ENABLED', 'robust') is True


# ===========================================================================
# Priority: settings.py overrides preset
# ===========================================================================

class TestSettingsPyOverridesPreset:

    def test_explicit_setting_overrides_preset(self):
        # robust preset says 300s, explicit override says 1800s
        val = _get_with_mode('JWT_ACCESS_TOKEN_LIFETIME', 'robust',
                             TENXYTE_JWT_ACCESS_TOKEN_LIFETIME=1800)
        assert val == 1800

    def test_explicit_breach_check_overrides_starter(self):
        # starter preset says False, explicit override says True
        val = _get_with_mode('BREACH_CHECK_ENABLED', 'starter',
                             TENXYTE_BREACH_CHECK_ENABLED=True)
        assert val is True

    def test_explicit_magic_link_overrides_medium(self):
        # medium preset says True, explicit override says False
        val = _get_with_mode('MAGIC_LINK_ENABLED', 'medium',
                             TENXYTE_MAGIC_LINK_ENABLED=False)
        assert val is False

    def test_explicit_max_attempts_overrides_robust(self):
        # robust preset says 3, explicit override says 10
        val = _get_with_mode('MAX_LOGIN_ATTEMPTS', 'robust',
                             TENXYTE_MAX_LOGIN_ATTEMPTS=10)
        assert val == 10

    def test_multiple_overrides_on_starter(self):
        s = TenxyteSettings()
        mock = _settings_with_mode('starter',
                                   TENXYTE_PASSWORD_HISTORY_ENABLED=True,
                                   TENXYTE_PASSWORD_HISTORY_COUNT=8)
        with patch('tenxyte.conf.settings', mock):
            assert s.PASSWORD_HISTORY_ENABLED is True
            assert s.PASSWORD_HISTORY_COUNT == 8

    def test_explicit_webauthn_disabled_overrides_robust(self):
        # robust preset says True, explicit override says False
        val = _get_with_mode('WEBAUTHN_ENABLED', 'robust',
                             TENXYTE_WEBAUTHN_ENABLED=False)
        assert val is False


# ===========================================================================
# Invalid mode — warning
# ===========================================================================

class TestInvalidMode:

    def test_invalid_mode_emits_warning(self):
        s = TenxyteSettings()
        mock = _settings_with_mode('ultra')
        with patch('tenxyte.conf.settings', mock):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                _ = s.JWT_ACCESS_TOKEN_LIFETIME
                assert len(w) == 1
                assert issubclass(w[0].category, UserWarning)
                assert 'ultra' in str(w[0].message)
                assert 'invalid' in str(w[0].message).lower()

    def test_invalid_mode_falls_back_to_default(self):
        s = TenxyteSettings()
        mock = _settings_with_mode('ultra')
        with patch('tenxyte.conf.settings', mock):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                assert s.JWT_ACCESS_TOKEN_LIFETIME == 3600

    def test_empty_string_mode_emits_warning(self):
        s = TenxyteSettings()
        mock = _settings_with_mode('')
        with patch('tenxyte.conf.settings', mock):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                _ = s.BREACH_CHECK_ENABLED
                assert len(w) == 1
                assert issubclass(w[0].category, UserWarning)
