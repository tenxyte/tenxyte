"""
Environment Variable Settings Provider for Tenxyte Core.

This module provides a SettingsProvider that reads from environment variables.
Useful for containerized deployments, 12-factor apps, or when you want to
configure Tenxyte without a framework-specific settings file.

**Unified settings priority (both adapters)**: `Adapter_Custom > OS env > .env > preset >
default`. `Adapter_Custom` is whatever the adapter's own primary source is — a Django project's
`settings.py` (`conf/base.py`'s `BaseSettingsMixin`, `adapters/django/settings_provider.py`'s
`DjangoSettingsProvider`) or an explicit `SettingsProvider` subclass overriding `.get()` on the
FastAPI side. `OS env > .env` is this module's own job: real environment variables always win
over a `.env` file (`python-dotenv`'s `override=False`), so a `.env` committed to a repo or left
in a Docker image can never silently shadow a real deployment secret. `ensure_dotenv_loaded()`
and `get_env_or_dotenv()` are the shared primitives both Django-side resolution paths import to
get the same `OS env > .env` tier `EnvSettingsProvider` itself already had — see each call site's
own docstring for exactly where that tier sits in its chain.
"""

import os
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from tenxyte.core.settings import Settings

from tenxyte.core.settings import SettingsProvider

_dotenv_loaded = False


def ensure_dotenv_loaded(dotenv_path: str | None = None, encoding: str = "utf-8") -> None:
    """Loads a `.env` file into `os.environ` — real OS environment variables already set are
    never overwritten (`python-dotenv`'s own `override=False`), so this is always safe to call
    before reading `os.environ` directly.

    **`usecwd=True` for the default (auto-discovered) case** — verified directly, not assumed:
    `python-dotenv`'s own `find_dotenv()` defaults to `usecwd=False`, which walks up from the
    *calling file's* location (`frame.f_code.co_filename`), not the process's current working
    directory. Left at that default, a real deployment would search upward from wherever
    `tenxyte` itself is installed (e.g. inside `site-packages/`), never from the project the app
    actually runs in — the wrong search entirely for a library. `usecwd=True` searches from
    `os.getcwd()` instead, matching where a real app is actually launched from (`uvicorn
    main:app` run from the project root, a container's `WORKDIR`, etc.).

    Idempotent for the default (auto-discovered) case: repeating that filesystem walk on every
    settings lookup would be wasteful, so it only actually runs once per process for
    `dotenv_path=None`. An explicit `dotenv_path` always loads (a caller asking for a *specific*
    file has opted out of the auto-discovery default and presumably wants it honored every time,
    e.g. tests pointing at a fixture file)."""
    global _dotenv_loaded
    if dotenv_path is None and _dotenv_loaded:
        return
    from dotenv import find_dotenv, load_dotenv

    # load_dotenv() itself has no usecwd kwarg — find_dotenv(usecwd=True) resolves the real path
    # first (empty string if none found, which load_dotenv() treats as "nothing to load", the
    # same no-op as an explicit missing path).
    resolved_path = dotenv_path if dotenv_path is not None else find_dotenv(usecwd=True)
    load_dotenv(dotenv_path=resolved_path, encoding=encoding, override=False)
    if dotenv_path is None:
        _dotenv_loaded = True


def get_env_or_dotenv(name: str, default: Any = None) -> Any:
    """The shared `OS env > .env` tier — `name` must already carry the `TENXYTE_` prefix (or
    whatever prefix the caller uses; this function doesn't add one). Returns `default` (never
    raises) if the variable isn't set anywhere. Used directly by `EnvSettingsProvider.get()`
    below, and by both Django-side resolution paths (`conf/base.py`,
    `adapters/django/settings_provider.py`) as their own new middle tier, so a bare OS
    environment variable or `.env` entry works identically regardless of which adapter reads it."""
    ensure_dotenv_loaded()
    if name not in os.environ:
        return default
    return EnvSettingsProvider._convert_type(name, os.environ[name])


class EnvSettingsProvider(SettingsProvider):
    """
    Settings provider that reads from environment variables.

    Automatically prefixes setting names with 'TENXYTE_' when looking up
    environment variables. Supports type conversion for common types.

    Example:
        # Set environment variables
        export TENXYTE_JWT_SECRET_KEY="my-secret-key"
        export TENXYTE_JWT_ACCESS_TOKEN_LIFETIME="3600"
        export TENXYTE_MFA_REQUIRED="true"

        # Use in code
        from tenxyte.core.settings import Settings
        from tenxyte.core.env_provider import EnvSettingsProvider

        settings = Settings(provider=EnvSettingsProvider())
        print(settings.jwt_secret)  # "my-secret-key"
        print(settings.jwt_access_token_lifetime)  # 3600 (int)

    Features:
        - Automatic TENXYTE_ prefix
        - Type conversion (int, bool, float, list)
        - `.env` file support via python-dotenv (a Core dependency, always available) — auto-
          discovered from the current working directory by default; real OS environment
          variables always take priority over a `.env` value (see module docstring)
        - Fallback to unprefixed names for common variables (DEBUG, etc.)
    """

    # Type hints for known settings to enable automatic conversion
    BOOLEAN_SETTINGS: ClassVar[dict] = {
        "TENXYTE_MFA_REQUIRED",
        "TENXYTE_APPLICATION_AUTH_ENABLED",
        "TENXYTE_BREACH_CHECK_ENABLED",
        "TENXYTE_PASSWORD_REQUIRE_UPPERCASE",
        "TENXYTE_PASSWORD_REQUIRE_LOWERCASE",
        "TENXYTE_PASSWORD_REQUIRE_DIGIT",
        "TENXYTE_PASSWORD_REQUIRE_SPECIAL",
        "TENXYTE_AUDIT_LOG_ENABLED",
        "TENXYTE_DEVICE_FINGERPRINTING_ENABLED",
        "TENXYTE_ORG_ROLE_INHERITANCE",
        "TENXYTE_SECURITY_HEADERS_ENABLED",
        "TENXYTE_CORS_ENABLED",
        "TENXYTE_CORS_ALLOW_CREDENTIALS",
        "TENXYTE_CORS_ALLOW_ALL_ORIGINS",
        "DEBUG",
    }

    INTEGER_SETTINGS: ClassVar[dict] = {
        "TENXYTE_JWT_ACCESS_TOKEN_LIFETIME",
        "TENXYTE_JWT_REFRESH_TOKEN_LIFETIME",
        "TENXYTE_PASSWORD_MIN_LENGTH",
        "TENXYTE_MAX_LOGIN_ATTEMPTS",
        "TENXYTE_LOCKOUT_DURATION",
        "TENXYTE_API_VERSION",
        "TENXYTE_ORG_MAX_DEPTH",
        "TENXYTE_ORG_MAX_MEMBERS",
        "TENXYTE_MAX_DEVICES_PER_USER",
        "TENXYTE_AUDIT_LOG_RETENTION_DAYS",
        "TENXYTE_CORS_MAX_AGE",
    }

    LIST_SETTINGS: ClassVar[dict] = {
        "TENXYTE_CORS_ALLOWED_ORIGINS",
        "TENXYTE_CORS_ALLOWED_METHODS",
        "TENXYTE_CORS_ALLOWED_HEADERS",
        "TENXYTE_CORS_EXPOSE_HEADERS",
        "TENXYTE_EXEMPT_PATHS",
        "TENXYTE_EXACT_EXEMPT_PATHS",
    }

    def __init__(self, prefix: str = "TENXYTE_", dotenv_path: str | None = None, dotenv_encoding: str = "utf-8"):
        """
        Initialize the environment settings provider.

        `.env` loading is automatic and unconditional (`ensure_dotenv_loaded`, module-level) —
        `python-dotenv` is a Core dependency, not an optional extra, so there's no "not installed"
        case to guard against any more. `dotenv_path`/`dotenv_encoding` stay for the case a caller
        wants a *specific* file instead of the default auto-discovered `.env` (e.g. tests).

        Args:
            prefix: Prefix for environment variable names (default: TENXYTE_)
            dotenv_path: Path to .env file to load (optional — default auto-discovers `.env`)
            dotenv_encoding: Encoding for .env file (default: utf-8)
        """
        self.prefix = prefix
        ensure_dotenv_loaded(dotenv_path=dotenv_path, encoding=dotenv_encoding)

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value from environment variables.

        Args:
            name: Setting name (e.g., 'TENXYTE_JWT_SECRET_KEY' or 'JWT_SECRET_KEY')
            default: Default value if not found

        Returns:
            The setting value with appropriate type conversion, or default
        """
        # Handle unprefixed names (like DEBUG)
        if not name.startswith(self.prefix):
            # Try with prefix first
            value = os.environ.get(f"{self.prefix}{name}")
            if value is not None:
                return self._convert_type(f"{self.prefix}{name}", value)

            # Try unprefixed for common variables
            value = os.environ.get(name)
            if value is not None:
                return self._convert_type(name, value)
        else:
            # Name already has prefix
            value = os.environ.get(name)
            if value is not None:
                return self._convert_type(name, value)

        return default

    @staticmethod
    def _convert_type(name: str, value: str) -> Any:
        """Convert string value to appropriate type based on setting name. `@staticmethod` (not
        just convention — no instance state involved) so `get_env_or_dotenv()` can call it
        without constructing a throwaway `EnvSettingsProvider`."""
        if name in EnvSettingsProvider.BOOLEAN_SETTINGS:
            return EnvSettingsProvider._parse_bool(value)

        if name in EnvSettingsProvider.INTEGER_SETTINGS:
            try:
                return int(value)
            except ValueError:
                return value

        if name in EnvSettingsProvider.LIST_SETTINGS:
            return EnvSettingsProvider._parse_list(value)

        return value

    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse a boolean string value."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")

    @staticmethod
    def _parse_list(value: str) -> list:
        """Parse a comma-separated list value."""
        if not value:
            return []
        return [item.strip() for item in value.split(",")]

    @classmethod
    def from_env(cls, **kwargs) -> "EnvSettingsProvider":
        """
        Convenience factory method to create provider from current environment.

        Args:
            **kwargs: Additional arguments to pass to constructor

        Returns:
            Configured EnvSettingsProvider instance

        Example:
            from tenxyte.core.env_provider import EnvSettingsProvider
            from tenxyte.core.settings import Settings

            provider = EnvSettingsProvider.from_env()
            settings = Settings(provider=provider)
        """
        return cls(**kwargs)


# Convenience function for quick initialization
def get_env_settings(dotenv_path: str | None = None) -> "Settings":
    """
    Get Tenxyte settings configured from environment variables.

    Args:
        dotenv_path: Optional path to .env file

    Returns:
        Settings instance configured with environment variables

    Example:
        from tenxyte.core.env_provider import get_env_settings

        settings = get_env_settings(dotenv_path='.env')
        print(settings.jwt_secret)
    """
    from tenxyte.core.settings import Settings

    provider = EnvSettingsProvider(dotenv_path=dotenv_path)
    return Settings(provider=provider)
