"""
Tests for auto-dev preset activation, JWT auto-generation, and preset override behavior.
"""
import pytest
import warnings
from unittest.mock import patch, PropertyMock
from django.core.exceptions import ImproperlyConfigured


class TestAutoDevPreset:
    """Tests for automatic development preset activation in DEBUG mode."""

    def test_auto_dev_preset_activates_in_debug(self):
        """DEBUG=True without explicit preset → development preset values."""
        from tenxyte.conf.base import BaseSettingsMixin
        from types import SimpleNamespace

        class TestSettings(BaseSettingsMixin):
            pass

        obj = TestSettings()
        # Use SimpleNamespace to properly simulate missing attributes
        mock_settings = SimpleNamespace(DEBUG=True)
        with patch('tenxyte.conf.base.settings', mock_settings), \
             patch('tenxyte.conf.presets.settings', mock_settings):
            # Development preset has PASSWORD_HISTORY_ENABLED=False
            result = obj._get('PASSWORD_HISTORY_ENABLED', True)
            assert result is False  # Development preset value, not default True

    def test_auto_dev_preset_does_not_activate_in_production(self):
        """DEBUG=False without explicit preset → defaults (no auto-dev)."""
        from tenxyte.conf.base import BaseSettingsMixin
        from types import SimpleNamespace

        class TestSettings(BaseSettingsMixin):
            pass

        obj = TestSettings()
        mock_settings = SimpleNamespace(DEBUG=False)
        with patch('tenxyte.conf.base.settings', mock_settings), \
             patch('tenxyte.conf.presets.settings', mock_settings):
            # Should use default value True, not development preset value False
            result = obj._get('PASSWORD_HISTORY_ENABLED', True)
            assert result is True

    def test_explicit_preset_overrides_auto_dev(self):
        """Explicit TENXYTE_SHORTCUT_SECURE_MODE='medium' overrides auto-dev even in DEBUG."""
        from tenxyte.conf.base import BaseSettingsMixin
        from types import SimpleNamespace

        class TestSettings(BaseSettingsMixin):
            pass

        obj = TestSettings()
        mock_settings = SimpleNamespace(DEBUG=True, TENXYTE_SHORTCUT_SECURE_MODE='medium')
        with patch('tenxyte.conf.base.settings', mock_settings), \
             patch('tenxyte.conf.presets.settings', mock_settings):
            # Medium preset has PASSWORD_HISTORY_ENABLED=True
            result = obj._get('PASSWORD_HISTORY_ENABLED', False)
            assert result is True

    def test_explicit_setting_overrides_auto_dev(self):
        """Explicit TENXYTE_* setting takes priority over auto-dev preset."""
        from tenxyte.conf.base import BaseSettingsMixin
        from types import SimpleNamespace

        class TestSettings(BaseSettingsMixin):
            pass

        obj = TestSettings()
        mock_settings = SimpleNamespace(DEBUG=True, TENXYTE_PASSWORD_HISTORY_ENABLED=True)
        with patch('tenxyte.conf.base.settings', mock_settings), \
             patch('tenxyte.conf.presets.settings', mock_settings):
            result = obj._get('PASSWORD_HISTORY_ENABLED', False)
            assert result is True  # Explicit setting wins

    def test_application_auth_enabled_in_dev_preset(self):
        """Development preset does NOT disable APPLICATION_AUTH_ENABLED — app auth is active even in dev."""
        from tenxyte.conf.presets import SECURE_MODE_PRESETS

        # APPLICATION_AUTH_ENABLED is not in the development preset,
        # so the default (True) applies — app auth is always active.
        assert 'APPLICATION_AUTH_ENABLED' not in SECURE_MODE_PRESETS['development']

    def test_application_auth_not_disabled_in_medium(self):
        """Medium preset does not include APPLICATION_AUTH_ENABLED=False."""
        from tenxyte.conf.presets import SECURE_MODE_PRESETS

        # Medium preset doesn't have APPLICATION_AUTH_ENABLED key
        # so default (True) would apply
        assert SECURE_MODE_PRESETS['medium'].get('APPLICATION_AUTH_ENABLED', True) is True

    def test_application_auth_not_disabled_in_robust(self):
        """Robust preset does not include APPLICATION_AUTH_ENABLED=False."""
        from tenxyte.conf.presets import SECURE_MODE_PRESETS

        assert SECURE_MODE_PRESETS['robust'].get('APPLICATION_AUTH_ENABLED', True) is True

    def test_development_preset_values(self):
        """Verify development preset has expected relaxed values."""
        from tenxyte.conf.presets import SECURE_MODE_PRESETS

        dev = SECURE_MODE_PRESETS['development']
        assert dev['JWT_ACCESS_TOKEN_LIFETIME'] == 3600
        assert dev['JWT_REFRESH_TOKEN_LIFETIME'] == 86400 * 30
        assert dev['REFRESH_TOKEN_ROTATION'] is False
        assert dev['BREACH_CHECK_ENABLED'] is False
        assert dev['AUDIT_LOGGING_ENABLED'] is False
        assert dev['DEVICE_LIMIT_ENABLED'] is False
        assert dev['SESSION_LIMIT_ENABLED'] is False
        assert dev['SECURITY_HEADERS_ENABLED'] is False

    def test_valid_preset_names(self):
        """All expected preset names are valid."""
        from tenxyte.conf.presets import VALID_SECURE_MODES

        assert 'development' in VALID_SECURE_MODES
        assert 'medium' in VALID_SECURE_MODES
        assert 'robust' in VALID_SECURE_MODES

    def test_invalid_preset_warning(self):
        """Invalid preset name emits a warning and falls back to default."""
        from tenxyte.conf.base import BaseSettingsMixin
        from types import SimpleNamespace

        class TestSettings(BaseSettingsMixin):
            pass

        obj = TestSettings()
        mock_settings = SimpleNamespace(
            DEBUG=False,
            TENXYTE_SHORTCUT_SECURE_MODE='nonexistent'
        )
        with patch('tenxyte.conf.base.settings', mock_settings), \
             patch('tenxyte.conf.presets.settings', mock_settings):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                result = obj._get('PASSWORD_HISTORY_ENABLED', True)
                assert result is True  # Falls back to default
                assert len(w) == 1
                assert 'nonexistent' in str(w[0].message)


class TestJWTSecretKeyAutoGen:
    """Tests for ephemeral JWT secret key auto-generation in DEBUG mode."""

    def test_jwt_secret_auto_generated_in_debug(self):
        """DEBUG=True without TENXYTE_JWT_SECRET_KEY → auto-generated key with warning."""
        from tenxyte.conf.jwt import JwtSettingsMixin
        from types import SimpleNamespace

        class TestJwt(JwtSettingsMixin):
            pass

        obj = TestJwt()
        mock_settings = SimpleNamespace(DEBUG=True)
        with patch('tenxyte.conf.jwt.settings', mock_settings):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                key = obj.JWT_SECRET_KEY
                assert key is not None
                assert len(key) == 128  # hex(64) = 128 chars
                assert len(w) == 1
                assert 'ephemeral' in str(w[0].message).lower()

    def test_jwt_secret_persists_across_calls(self):
        """Same ephemeral key returned on subsequent accesses."""
        from tenxyte.conf.jwt import JwtSettingsMixin
        from types import SimpleNamespace

        class TestJwt(JwtSettingsMixin):
            pass

        obj = TestJwt()
        mock_settings = SimpleNamespace(DEBUG=True)
        with patch('tenxyte.conf.jwt.settings', mock_settings):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter('always')
                key1 = obj.JWT_SECRET_KEY
                key2 = obj.JWT_SECRET_KEY
                assert key1 == key2

    def test_jwt_secret_required_in_production(self):
        """DEBUG=False without TENXYTE_JWT_SECRET_KEY → ImproperlyConfigured."""
        from tenxyte.conf.jwt import JwtSettingsMixin
        from types import SimpleNamespace

        class TestJwt(JwtSettingsMixin):
            pass

        obj = TestJwt()
        mock_settings = SimpleNamespace(DEBUG=False)
        with patch('tenxyte.conf.jwt.settings', mock_settings):
            with pytest.raises(ImproperlyConfigured):
                _ = obj.JWT_SECRET_KEY

    def test_jwt_explicit_key_used_when_set(self):
        """Explicit TENXYTE_JWT_SECRET_KEY is used regardless of DEBUG."""
        from tenxyte.conf.jwt import JwtSettingsMixin
        from types import SimpleNamespace

        class TestJwt(JwtSettingsMixin):
            pass

        obj = TestJwt()
        mock_settings = SimpleNamespace(DEBUG=True, TENXYTE_JWT_SECRET_KEY='my-explicit-key')
        with patch('tenxyte.conf.jwt.settings', mock_settings):
            key = obj.JWT_SECRET_KEY
            assert key == 'my-explicit-key'

    def test_jwt_auto_gen_warning_only_once(self):
        """Warning is only emitted once per instance, not on every access."""
        from tenxyte.conf.jwt import JwtSettingsMixin
        from types import SimpleNamespace

        class TestJwt(JwtSettingsMixin):
            pass

        obj = TestJwt()
        mock_settings = SimpleNamespace(DEBUG=True)
        with patch('tenxyte.conf.jwt.settings', mock_settings):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                _ = obj.JWT_SECRET_KEY
                _ = obj.JWT_SECRET_KEY
                _ = obj.JWT_SECRET_KEY
                # Warning emitted only once (on first access)
                assert len(w) == 1
