"""
Agnostic Settings for Tenxyte Core.

This module provides a framework-agnostic settings class that can be used
with any framework (Django, FastAPI, etc.) through appropriate adapters.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass


@runtime_checkable
class SettingsProvider(Protocol):
    """Protocol for settings providers."""

    def get(self, name: str, default: Any = None) -> Any:
        """Get a setting value by name."""
        ...


@dataclass
class SecureModePreset:
    """Preset configuration for a security mode."""

    name: str
    jwt_access_token_lifetime: int = 3600
    jwt_refresh_token_lifetime: int = 86400
    jwt_algorithm: str = "HS256"
    password_min_length: int = 8
    password_require_special: bool = False
    mfa_required: bool = False
    max_login_attempts: int = 5
    lockout_duration: int = 300


# Predefined security mode presets
SECURE_MODE_PRESETS = {
    "development": SecureModePreset(
        name="development",
        jwt_access_token_lifetime=3600,
        jwt_refresh_token_lifetime=86400,
        jwt_algorithm="HS256",
        password_min_length=6,
        password_require_special=False,
        mfa_required=False,
        max_login_attempts=10,
        lockout_duration=60,
    ),
    "production": SecureModePreset(
        name="production",
        jwt_access_token_lifetime=900,
        jwt_refresh_token_lifetime=43200,
        jwt_algorithm="RS256",
        password_min_length=12,
        password_require_special=True,
        mfa_required=False,
        max_login_attempts=5,
        lockout_duration=1800,
    ),
    "enterprise": SecureModePreset(
        name="enterprise",
        jwt_access_token_lifetime=600,
        jwt_refresh_token_lifetime=21600,
        jwt_algorithm="RS256",
        password_min_length=16,
        password_require_special=True,
        mfa_required=True,
        max_login_attempts=3,
        lockout_duration=3600,
    ),
}


class Settings:
    """
    Framework-agnostic settings for Tenxyte Core.

    This class can be initialized with a SettingsProvider that reads from
    any configuration source (Django settings, FastAPI config, environment
    variables, etc.).

    Example:
        # With Django adapter
        from tenxyte.adapters.django import DjangoSettingsProvider
        settings = Settings(provider=DjangoSettingsProvider())

        # With environment variables
        from tenxyte.core.env_provider import EnvSettingsProvider
        settings = Settings(provider=EnvSettingsProvider())
    """

    def __init__(self, provider: Optional[SettingsProvider] = None):
        """
        Initialize settings with an optional provider.

        Args:
            provider: A SettingsProvider implementation that reads configuration
                     from the underlying framework or environment.
        """
        self._provider = provider
        self._cache: Dict[str, Any] = {}

    def _get(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value with priority:
        1. Provider value (if provider is set)
        2. Preset value (if secure mode is active)
        3. Default value

        Args:
            name: Setting name WITHOUT the TENXYTE_ prefix
            default: Default value if not found

        Returns:
            The setting value
        """
        # 1. Check provider first
        if self._provider is not None:
            try:
                provider_value = self._provider.get(f"TENXYTE_{name}")
                if provider_value is not None:
                    return provider_value
            except (AttributeError, KeyError):
                pass

        # 2. Check preset if active
        mode = self._get_secure_mode()
        if mode and mode in SECURE_MODE_PRESETS:
            preset = SECURE_MODE_PRESETS[mode]
            if hasattr(preset, name.lower()):
                return getattr(preset, name.lower())

        # 3. Return default
        return default

    def _get_secure_mode(self) -> Optional[str]:
        """Get the active secure mode from provider or default."""
        if self._provider is not None:
            try:
                mode = self._provider.get("TENXYTE_SHORTCUT_SECURE_MODE")
                if mode:
                    return mode
            except (AttributeError, KeyError):
                pass

        # Default to development if DEBUG is True
        try:
            if self._provider and self._provider.get("DEBUG", False):
                return "development"
        except (AttributeError, KeyError):
            pass

        return None

    # ============================================================
    # Base Settings
    # ============================================================

    @property
    def base_url(self) -> str:
        """Base URL of the API."""
        return self._get("BASE_URL", "http://127.0.0.1:8000")

    @property
    def api_version(self) -> int:
        """API version (e.g., 1)."""
        return self._get("API_VERSION", 1)

    @property
    def api_prefix(self) -> str:
        """API prefix (e.g., /api/v1)."""
        prefix = self._get("API_PREFIX", f"/api/v{self.api_version}")
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        return prefix.rstrip("/")

    # ============================================================
    # JWT Settings
    # ============================================================

    @property
    def jwt_secret(self) -> str:
        """Secret key for JWT signing (HS256) or private key (RS256)."""
        return self._get("JWT_SECRET", "")

    @property
    def jwt_public_key(self) -> Optional[str]:
        """Public key for JWT verification (RS256 only)."""
        return self._get("JWT_PUBLIC_KEY", None)

    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm (HS256 or RS256)."""
        return self._get("JWT_ALGORITHM", "HS256")

    @property
    def jwt_access_token_lifetime(self) -> int:
        """Access token lifetime in seconds."""
        return self._get("JWT_ACCESS_TOKEN_LIFETIME", 3600)

    @property
    def jwt_refresh_token_lifetime(self) -> int:
        """Refresh token lifetime in seconds."""
        return self._get("JWT_REFRESH_TOKEN_LIFETIME", 86400)

    @property
    def jwt_issuer(self) -> str:
        """JWT issuer claim."""
        return self._get("JWT_ISSUER", "tenxyte")

    @property
    def jwt_audience(self) -> Optional[str]:
        """JWT audience claim."""
        return self._get("JWT_AUDIENCE", None)

    # ============================================================
    # Security Settings
    # ============================================================

    @property
    def password_min_length(self) -> int:
        """Minimum password length."""
        return self._get("PASSWORD_MIN_LENGTH", 8)

    @property
    def password_require_uppercase(self) -> bool:
        """Require uppercase letters in password."""
        return self._get("PASSWORD_REQUIRE_UPPERCASE", True)

    @property
    def password_require_lowercase(self) -> bool:
        """Require lowercase letters in password."""
        return self._get("PASSWORD_REQUIRE_LOWERCASE", True)

    @property
    def password_require_digit(self) -> bool:
        """Require digits in password."""
        return self._get("PASSWORD_REQUIRE_DIGIT", True)

    @property
    def password_require_special(self) -> bool:
        """Require special characters in password."""
        return self._get("PASSWORD_REQUIRE_SPECIAL", False)

    @property
    def max_login_attempts(self) -> int:
        """Maximum failed login attempts before lockout."""
        return self._get("MAX_LOGIN_ATTEMPTS", 5)

    @property
    def lockout_duration(self) -> int:
        """Account lockout duration in seconds."""
        return self._get("LOCKOUT_DURATION", 300)

    @property
    def breach_check_enabled(self) -> bool:
        """Enable HaveIBeenPwned breach check."""
        return self._get("BREACH_CHECK_ENABLED", True)

    # ============================================================
    # 2FA Settings
    # ============================================================

    @property
    def mfa_required(self) -> bool:
        """Require MFA for all users."""
        return self._get("MFA_REQUIRED", False)

    @property
    def totp_issuer_name(self) -> str:
        """TOTP issuer name displayed in authenticator apps."""
        return self._get("TOTP_ISSUER_NAME", "Tenxyte")

    # ============================================================
    # Application Auth Settings
    # ============================================================

    @property
    def application_auth_enabled(self) -> bool:
        """Enable application-level authentication."""
        return self._get("APPLICATION_AUTH_ENABLED", True)

    @property
    def exempt_paths(self) -> List[str]:
        """Paths exempt from application authentication (prefix match)."""
        return self._get("EXEMPT_PATHS", ["/admin/", f"{self.api_prefix}/health/", f"{self.api_prefix}/docs/"])

    @property
    def exact_exempt_paths(self) -> List[str]:
        """Paths exempt from application authentication (exact match)."""
        return self._get("EXACT_EXEMPT_PATHS", [f"{self.api_prefix}/"])

    # ============================================================
    # Organization Settings
    # ============================================================

    @property
    def org_role_inheritance(self) -> bool:
        """Enable role inheritance in organization hierarchy."""
        return self._get("ORG_ROLE_INHERITANCE", True)

    @property
    def org_max_depth(self) -> int:
        """Maximum depth of organization hierarchy."""
        return self._get("ORG_MAX_DEPTH", 5)

    @property
    def org_max_members(self) -> int:
        """Default maximum members per organization (0 = unlimited)."""
        return self._get("ORG_MAX_MEMBERS", 0)

    # ============================================================
    # Audit Settings
    # ============================================================

    @property
    def audit_log_enabled(self) -> bool:
        """Enable audit logging."""
        return self._get("AUDIT_LOG_ENABLED", True)

    @property
    def audit_log_retention_days(self) -> int:
        """Audit log retention period in days."""
        return self._get("AUDIT_LOG_RETENTION_DAYS", 90)

    # ============================================================
    # Device & Session Settings
    # ============================================================

    @property
    def max_devices_per_user(self) -> int:
        """Maximum devices per user (0 = unlimited)."""
        return self._get("MAX_DEVICES_PER_USER", 0)

    @property
    def device_fingerprinting_enabled(self) -> bool:
        """Enable device fingerprinting."""
        return self._get("DEVICE_FINGERPRINTING_ENABLED", True)

    # ============================================================
    # Throttling Settings
    # ============================================================

    @property
    def simple_throttle_rules(self) -> Dict[str, str]:
        """Simple throttle rules by URL prefix."""
        return self._get("SIMPLE_THROTTLE_RULES", {})


# Global settings instance (will be initialized by framework adapters)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    if _settings is None:
        raise RuntimeError(
            "Settings not initialized. Call settings.init() first " "or use a framework adapter (e.g., DjangoAdapter)."
        )
    return _settings


def init(provider: Optional[SettingsProvider] = None) -> Settings:
    """Initialize global settings with a provider."""
    global _settings
    _settings = Settings(provider=provider)
    return _settings
