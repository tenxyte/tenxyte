"""
Tests for DjangoSettingsProvider - targeting 100% coverage of
src/tenxyte/adapters/django/settings_provider.py
"""
from unittest.mock import patch, MagicMock

from tenxyte.adapters.django.settings_provider import (
    DjangoSettingsProvider,
    get_django_settings,
)


class TestDjangoSettingsProvider:

    def test_debug_property(self):
        """Line 62: debug property reads Django DEBUG."""
        provider = DjangoSettingsProvider()
        result = provider.debug
        assert isinstance(result, bool)

    def test_get_existing_setting(self):
        """Lines 52-55: setting exists → returns value."""
        provider = DjangoSettingsProvider()
        # INSTALLED_APPS always exists in Django settings
        result = provider.get("INSTALLED_APPS")
        assert isinstance(result, (list, tuple))

    def test_get_missing_setting(self):
        """Lines 52, 57: setting missing → returns default."""
        provider = DjangoSettingsProvider()
        result = provider.get("NONEXISTENT_SETTING_XYZ", "fallback")
        assert result == "fallback"


class TestGetDjangoSettings:

    def test_get_django_settings_when_none(self):
        """Lines 82-86: _settings is None → calls init()."""
        mock_settings_obj = MagicMock()
        with patch("tenxyte.core.settings._settings", None), \
             patch("tenxyte.core.settings.init", return_value=mock_settings_obj) as mock_init:
            result = get_django_settings()
        mock_init.assert_called_once()
        assert result is mock_settings_obj

    def test_get_django_settings_already_initialized(self):
        """Lines 84, 88: _settings already set → returns it."""
        sentinel = MagicMock()
        with patch("tenxyte.core.settings._settings", sentinel):
            result = get_django_settings()
        assert result is sentinel
