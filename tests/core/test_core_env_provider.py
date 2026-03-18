"""
Tests for core env_provider - targeting 100% coverage of
src/tenxyte/core/env_provider.py
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from tenxyte.core.env_provider import EnvSettingsProvider, get_env_settings


# ═══════════════════════════════════════════════════════════════════════════════
# __init__  (lines 99-110)
# ═══════════════════════════════════════════════════════════════════════════════

def test_init_no_dotenv():
    """Line 99: basic init without dotenv."""
    provider = EnvSettingsProvider()
    assert provider.prefix == "TENXYTE_"


def test_init_with_dotenv_available():
    """Lines 102-105: dotenv_path provided and python-dotenv available."""
    with patch("tenxyte.core.env_provider.EnvSettingsProvider.__init__", wraps=EnvSettingsProvider.__init__) as _:
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            # We need to actually run the init, so let's patch the import inside
            pass

    # More direct approach: patch the import inside __init__
    mock_dotenv = MagicMock()
    with patch("builtins.__import__", side_effect=lambda name, *a, **kw: mock_dotenv if name == "dotenv" else __import__(name, *a, **kw)):
        EnvSettingsProvider(dotenv_path="/tmp/test.env")
    mock_dotenv.load_dotenv.assert_called_once()


def test_init_with_dotenv_missing():
    """Lines 106-110: dotenv_path provided but python-dotenv not installed."""
    with patch("builtins.__import__", side_effect=ImportError("No module")):
        with pytest.raises(ImportError, match="python-dotenv"):
            EnvSettingsProvider(dotenv_path="/tmp/test.env")


# ═══════════════════════════════════════════════════════════════════════════════
# get()  (lines 124-140)
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_prefixed_name():
    """Lines 134-138: name already has prefix."""
    provider = EnvSettingsProvider()
    with patch.dict(os.environ, {"TENXYTE_JWT_SECRET_KEY": "mysecret"}):
        assert provider.get("TENXYTE_JWT_SECRET_KEY") == "mysecret"


def test_get_unprefixed_with_prefix_found():
    """Lines 124-128: unprefixed name → found with prefix."""
    provider = EnvSettingsProvider()
    with patch.dict(os.environ, {"TENXYTE_JWT_SECRET_KEY": "val"}, clear=False):
        assert provider.get("JWT_SECRET_KEY") == "val"


def test_get_unprefixed_fallback():
    """Lines 130-133: unprefixed name → tried with prefix (not found), found unprefixed."""
    provider = EnvSettingsProvider()
    env = {"DEBUG": "true"}
    with patch.dict(os.environ, env, clear=False):
        # Remove any TENXYTE_DEBUG if present
        os.environ.pop("TENXYTE_DEBUG", None)
        result = provider.get("DEBUG")
    assert result is True  # converted to bool


def test_get_not_found():
    """Line 140: not found anywhere → default."""
    provider = EnvSettingsProvider()
    with patch.dict(os.environ, {}, clear=True):
        assert provider.get("NONEXISTENT", "fallback") == "fallback"


def test_get_prefixed_not_found():
    """Lines 136-138, 140: prefixed name not in env → default."""
    provider = EnvSettingsProvider()
    with patch.dict(os.environ, {}, clear=True):
        assert provider.get("TENXYTE_MISSING", "default") == "default"


# ═══════════════════════════════════════════════════════════════════════════════
# _convert_type  (lines 144-156)
# ═══════════════════════════════════════════════════════════════════════════════

def test_convert_bool():
    """Lines 144-145."""
    provider = EnvSettingsProvider()
    assert provider._convert_type("TENXYTE_MFA_REQUIRED", "true") is True
    assert provider._convert_type("TENXYTE_MFA_REQUIRED", "false") is False


def test_convert_int():
    """Lines 147-149."""
    provider = EnvSettingsProvider()
    assert provider._convert_type("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME", "3600") == 3600


def test_convert_int_invalid():
    """Lines 150-151: invalid int → return raw string."""
    provider = EnvSettingsProvider()
    assert provider._convert_type("TENXYTE_JWT_ACCESS_TOKEN_LIFETIME", "abc") == "abc"


def test_convert_list():
    """Lines 153-154."""
    provider = EnvSettingsProvider()
    result = provider._convert_type("TENXYTE_CORS_ALLOWED_ORIGINS", "http://a.com, http://b.com")
    assert result == ["http://a.com", "http://b.com"]


def test_convert_plain_string():
    """Line 156: no known type → return as-is."""
    provider = EnvSettingsProvider()
    assert provider._convert_type("TENXYTE_UNKNOWN", "val") == "val"


# ═══════════════════════════════════════════════════════════════════════════════
# _parse_bool / _parse_list  (lines 161, 166-168)
# ═══════════════════════════════════════════════════════════════════════════════

def test_parse_bool_truthy():
    """Line 161."""
    for v in ("true", "1", "yes", "on", "enabled", "TRUE", "Yes"):
        assert EnvSettingsProvider._parse_bool(v) is True


def test_parse_bool_falsy():
    assert EnvSettingsProvider._parse_bool("false") is False
    assert EnvSettingsProvider._parse_bool("0") is False


def test_parse_list_empty():
    """Line 166-167."""
    assert EnvSettingsProvider._parse_list("") == []


def test_parse_list_values():
    """Line 168."""
    assert EnvSettingsProvider._parse_list("a, b, c") == ["a", "b", "c"]


# ═══════════════════════════════════════════════════════════════════════════════
# from_env  (line 188)
# ═══════════════════════════════════════════════════════════════════════════════

def test_from_env():
    """Line 188."""
    provider = EnvSettingsProvider.from_env()
    assert isinstance(provider, EnvSettingsProvider)


# ═══════════════════════════════════════════════════════════════════════════════
# get_env_settings  (lines 208-211)
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_env_settings():
    """Lines 208-211."""
    settings = get_env_settings()
    assert settings is not None
