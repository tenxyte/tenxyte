"""
Tests for core env_provider - targeting 100% coverage of
src/tenxyte/core/env_provider.py

Real `.env` files (no mocked imports) for every dotenv-related test — `python-dotenv` is a real,
always-installed Core dependency now (spec: unified settings priority, `Adapter_Custom > OS env >
.env > preset > default`), so there's no "not installed" fallback branch left to simulate, and
mocking `builtins.__import__` to fake dotenv's presence/absence would test a mock, not the real
priority chain the feature is actually for.
"""

import os
from unittest.mock import patch

import pytest

import tenxyte.core.env_provider as env_provider_module
from tenxyte.core.env_provider import EnvSettingsProvider, ensure_dotenv_loaded, get_env_or_dotenv, get_env_settings


@pytest.fixture(autouse=True)
def _reset_dotenv_loaded_flag():
    """`ensure_dotenv_loaded()`'s once-per-process cache would otherwise leak between tests —
    each test that cares about a specific `.env` file passes `dotenv_path` explicitly (which
    always reloads, see the function's own docstring), but resetting the flag keeps the
    default-discovery tests isolated from whichever test ran first."""
    env_provider_module._dotenv_loaded = False
    yield
    env_provider_module._dotenv_loaded = False


# ═══════════════════════════════════════════════════════════════════════════════
# __init__  (lines 99-110)
# ═══════════════════════════════════════════════════════════════════════════════


def test_init_no_dotenv():
    """Line 99: basic init without dotenv."""
    provider = EnvSettingsProvider()
    assert provider.prefix == "TENXYTE_"


def test_init_with_real_dotenv_file_loads_values(tmp_path):
    """An explicit `dotenv_path` pointing at a real `.env` file on disk actually populates
    `os.environ` — no mocking, a real file read by real python-dotenv."""
    dotenv_file = tmp_path / "test.env"
    dotenv_file.write_text("TENXYTE_FROM_DOTENV_FILE=hello-from-file\n", encoding="utf-8")

    os.environ.pop("TENXYTE_FROM_DOTENV_FILE", None)
    try:
        EnvSettingsProvider(dotenv_path=str(dotenv_file))
        assert os.environ["TENXYTE_FROM_DOTENV_FILE"] == "hello-from-file"
    finally:
        os.environ.pop("TENXYTE_FROM_DOTENV_FILE", None)


def test_init_with_missing_dotenv_path_does_not_raise(tmp_path):
    """A `dotenv_path` pointing at a file that doesn't exist is not an error — python-dotenv
    itself treats a missing file as "nothing to load", not a failure, and there's no reason for
    this adapter to be stricter than the library it wraps."""
    EnvSettingsProvider(dotenv_path=str(tmp_path / "does-not-exist.env"))


# ═══════════════════════════════════════════════════════════════════════════════
# Unified priority chain: Adapter_Custom > OS env > .env > preset > default
# ═══════════════════════════════════════════════════════════════════════════════


def test_real_os_env_wins_over_dotenv_file(tmp_path):
    """The core guarantee of the new tier: a real OS environment variable is never shadowed by a
    `.env` file, even when the `.env` file also defines the same key."""
    dotenv_file = tmp_path / "test.env"
    dotenv_file.write_text("TENXYTE_PRIORITY_CHECK=from-dotenv\n", encoding="utf-8")

    with patch.dict(os.environ, {"TENXYTE_PRIORITY_CHECK": "from-real-os-env"}):
        EnvSettingsProvider(dotenv_path=str(dotenv_file))
        assert os.environ["TENXYTE_PRIORITY_CHECK"] == "from-real-os-env"


def test_dotenv_file_fills_gap_when_os_env_unset(tmp_path):
    """When the real OS environment doesn't have the variable at all, the `.env` value is used —
    the actual reason this feature exists."""
    dotenv_file = tmp_path / "test.env"
    dotenv_file.write_text("TENXYTE_ONLY_IN_DOTENV=from-dotenv-only\n", encoding="utf-8")

    os.environ.pop("TENXYTE_ONLY_IN_DOTENV", None)
    try:
        provider = EnvSettingsProvider(dotenv_path=str(dotenv_file))
        assert provider.get("TENXYTE_ONLY_IN_DOTENV") == "from-dotenv-only"
    finally:
        os.environ.pop("TENXYTE_ONLY_IN_DOTENV", None)


def test_get_env_or_dotenv_returns_default_when_unset():
    assert get_env_or_dotenv("TENXYTE_DOES_NOT_EXIST_ANYWHERE", "fallback") == "fallback"


def test_get_env_or_dotenv_applies_type_conversion():
    with patch.dict(os.environ, {"TENXYTE_MFA_REQUIRED": "true"}):
        assert get_env_or_dotenv("TENXYTE_MFA_REQUIRED") is True


def test_ensure_dotenv_loaded_default_case_only_loads_once(tmp_path, monkeypatch):
    """Auto-discovery (`dotenv_path=None`) shouldn't re-walk the filesystem on every call —
    verified by pointing python-dotenv's own default search at a real file via a changed cwd and
    confirming a second call doesn't re-apply (the flag short-circuits it)."""
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("TENXYTE_ONCE_CHECK=first-load\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    os.environ.pop("TENXYTE_ONCE_CHECK", None)
    try:
        ensure_dotenv_loaded()
        assert os.environ["TENXYTE_ONCE_CHECK"] == "first-load"

        # Change the file — a second default call must NOT re-read it (already "loaded").
        dotenv_file.write_text("TENXYTE_ONCE_CHECK=second-load\n", encoding="utf-8")
        ensure_dotenv_loaded()
        assert os.environ["TENXYTE_ONCE_CHECK"] == "first-load"
    finally:
        os.environ.pop("TENXYTE_ONCE_CHECK", None)


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
