"""
Tests for the unified settings priority chain's new middle tier (both Django-side resolution
paths — `conf/base.py`'s `BaseSettingsMixin._get()` and
`adapters/django/settings_provider.py`'s `DjangoSettingsProvider.get()`): `settings.py
(Adapter_Custom) > OS env > .env > preset > default`. See `core/env_provider.py`'s module
docstring for the full picture shared with the FastAPI side.

Real OS environment variables and real temp `.env` files throughout — no mocked environment
reads, only `django.conf.settings` itself is mocked (the same established pattern
`test_secure_mode.py` already uses for testing `_get()`'s resolution logic in isolation from a
real Django settings module).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import tenxyte.core.env_provider as env_provider_module
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.conf import TenxyteSettings


@pytest.fixture(autouse=True)
def _reset_dotenv_loaded_flag():
    env_provider_module._dotenv_loaded = False
    yield
    env_provider_module._dotenv_loaded = False


def _empty_settings_mock():
    """A Django settings.py that defines nothing — same convention as test_secure_mode.py's own
    `_get_no_mode` helper."""
    return MagicMock(spec=[])


class TestBaseSettingsMixinEnvTier:
    def test_real_os_env_used_when_settings_py_silent(self):
        """Also proves type conversion applies on this new tier — `1234` comes back as a real
        `int`, not the raw string every OS env var starts as (`get_env_or_dotenv` reuses
        `EnvSettingsProvider._convert_type`, the exact same conversion the FastAPI side uses)."""
        s = TenxyteSettings()
        mock = _empty_settings_mock()
        with (
            patch("tenxyte.conf.base.settings", mock),
            patch.dict(os.environ, {"TENXYTE_JWT_ACCESS_TOKEN_LIFETIME": "1234"}),
        ):
            assert s.JWT_ACCESS_TOKEN_LIFETIME == 1234

    def test_settings_py_still_wins_over_os_env(self):
        """Adapter_Custom stays absolute priority — this tier is new, but it must never regress
        Django's existing settings.py > * guarantee."""
        s = TenxyteSettings()
        mock = _empty_settings_mock()
        mock.TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 7200
        with (
            patch("tenxyte.conf.base.settings", mock),
            patch.dict(os.environ, {"TENXYTE_JWT_ACCESS_TOKEN_LIFETIME": "1234"}),
        ):
            assert s.JWT_ACCESS_TOKEN_LIFETIME == 7200

    def test_dotenv_file_used_when_neither_settings_py_nor_os_env_set(self, tmp_path, monkeypatch):
        dotenv_file = tmp_path / ".env"
        dotenv_file.write_text("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME=5555\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        s = TenxyteSettings()
        mock = _empty_settings_mock()
        os.environ.pop("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME", None)
        try:
            with patch("tenxyte.conf.base.settings", mock):
                assert s.JWT_ACCESS_TOKEN_LIFETIME == 5555
        finally:
            os.environ.pop("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME", None)

    def test_falls_through_to_preset_when_nothing_set_anywhere(self):
        """Nothing in settings.py, no OS env, no .env — must still reach the preset/default
        tiers exactly as before this change (Property: no regression to the pre-existing chain)."""
        s = TenxyteSettings()
        mock = _empty_settings_mock()
        mock.TENXYTE_SHORTCUT_SECURE_MODE = "development"
        os.environ.pop("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME", None)
        with patch("tenxyte.conf.base.settings", mock):
            assert s.JWT_ACCESS_TOKEN_LIFETIME == 3600  # development preset's own value


class TestDjangoSettingsProviderEnvTier:
    def test_real_os_env_used_when_django_settings_silent(self):
        provider = DjangoSettingsProvider()
        with patch.dict(os.environ, {"TENXYTE_SOME_CUSTOM_KEY": "from-os-env"}):
            assert provider.get("TENXYTE_SOME_CUSTOM_KEY", "fallback") == "from-os-env"

    def test_default_returned_when_nothing_set_anywhere(self):
        provider = DjangoSettingsProvider()
        os.environ.pop("TENXYTE_TRULY_NOWHERE", None)
        assert provider.get("TENXYTE_TRULY_NOWHERE", "fallback") == "fallback"
