import pytest
from tenxyte.core import settings
from tenxyte.core.settings import Settings, SecureModePreset, SettingsProvider

class DummyProviderForExceptions:
    def __init__(self, raise_attr=False, raise_key=False):
        self.raise_attr = raise_attr
        self.raise_key = raise_key

    def get(self, name, default=None):
        if self.raise_attr:
            raise AttributeError("attr")
        if self.raise_key:
            raise KeyError("key")
        return default

class DummyProvider:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, name, default=None):
        return self.mapping.get(name, default)

def test_settings_provider_protocol():
    # Cover line 18 (...)
    class ProtocolInst:
        pass
    try:
        SettingsProvider.get(ProtocolInst(), "foo")
    except Exception:
        pass

def test_exceptions_in_provider_get():
    s_attr = Settings(provider=DummyProviderForExceptions(raise_attr=True))
    assert s_attr.base_url == "http://127.0.0.1:8000"  # covers line 122 and 141-142 and 148-149

    s_key = Settings(provider=DummyProviderForExceptions(raise_key=True))
    assert s_key.base_url == "http://127.0.0.1:8000"

def test_secure_mode_preset():
    # Covers lines 128-130
    s = Settings(provider=DummyProvider({"TENXYTE_SHORTCUT_SECURE_MODE": "enterprise"}))
    assert s.jwt_algorithm == "RS256"
    assert s.password_min_length == 16
    assert s.mfa_required is True

def test_properties_defaults():
    s = Settings()
    assert s.base_url == "http://127.0.0.1:8000"
    assert s.api_version == 1
    assert s.api_prefix == "/api/v1"
    assert s.jwt_public_key is None
    assert s.max_login_attempts == 5
    assert s.breach_check_enabled is True
    assert s.mfa_required is False
    assert s.application_auth_enabled is True
    assert s.exempt_paths == ["/admin/", "/api/v1/health/", "/api/v1/docs/"]
    assert s.exact_exempt_paths == ["/api/v1/"]
    assert s.org_role_inheritance is True
    assert s.org_max_depth == 5
    assert s.org_max_members == 0
    assert s.audit_log_enabled is True
    assert s.audit_log_retention_days == 90
    assert s.simple_throttle_rules == {}

def test_api_prefix_not_starting_with_slash():
    s = Settings(provider=DummyProvider({"TENXYTE_API_PREFIX": "my/prefix"}))
    assert s.api_prefix == "/my/prefix"

def test_get_settings_exception():
    # Covers 358-363, 369-370
    old = settings._settings
    try:
        settings._settings = None
        with pytest.raises(RuntimeError):
            settings.get_settings()
        
        # Now init
        instance = settings.init(DummyProvider({}))
        assert instance is not None
        assert settings.get_settings() is instance
    finally:
        settings._settings = old
