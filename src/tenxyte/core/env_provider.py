"""
Environment Variable Settings Provider for Tenxyte Core.

This module provides a SettingsProvider that reads from environment variables.
Useful for containerized deployments, 12-factor apps, or when you want to
configure Tenxyte without a framework-specific settings file.
"""

import os
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tenxyte.core.settings import Settings

from tenxyte.core.settings import SettingsProvider


class EnvSettingsProvider(SettingsProvider):
    """
    Settings provider that reads from environment variables.

    Automatically prefixes setting names with 'TENXYTE_' when looking up
    environment variables. Supports type conversion for common types.

    Example:
        # Set environment variables
        export TENXYTE_JWT_SECRET="my-secret-key"
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
        - Support for .env files via python-dotenv (optional)
        - Fallback to unprefixed names for common variables (DEBUG, etc.)
    """

    # Type hints for known settings to enable automatic conversion
    BOOLEAN_SETTINGS = {
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

    INTEGER_SETTINGS = {
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

    LIST_SETTINGS = {
        "TENXYTE_CORS_ALLOWED_ORIGINS",
        "TENXYTE_CORS_ALLOWED_METHODS",
        "TENXYTE_CORS_ALLOWED_HEADERS",
        "TENXYTE_CORS_EXPOSE_HEADERS",
        "TENXYTE_EXEMPT_PATHS",
        "TENXYTE_EXACT_EXEMPT_PATHS",
    }

    def __init__(self, prefix: str = "TENXYTE_", dotenv_path: Optional[str] = None, dotenv_encoding: str = "utf-8"):
        """
        Initialize the environment settings provider.

        Args:
            prefix: Prefix for environment variable names (default: TENXYTE_)
            dotenv_path: Path to .env file to load (optional)
            dotenv_encoding: Encoding for .env file (default: utf-8)
        """
        self.prefix = prefix

        # Load .env file if python-dotenv is available and path provided
        if dotenv_path:
            try:
                from dotenv import load_dotenv

                load_dotenv(dotenv_path=dotenv_path, encoding=dotenv_encoding)
            except ImportError:
                raise ImportError(
                    "python-dotenv is required to load .env files. " "Install with: pip install python-dotenv"
                )

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value from environment variables.

        Args:
            name: Setting name (e.g., 'TENXYTE_JWT_SECRET' or 'JWT_SECRET')
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

    def _convert_type(self, name: str, value: str) -> Any:
        """Convert string value to appropriate type based on setting name."""
        if name in self.BOOLEAN_SETTINGS:
            return self._parse_bool(value)

        if name in self.INTEGER_SETTINGS:
            try:
                return int(value)
            except ValueError:
                return value

        if name in self.LIST_SETTINGS:
            return self._parse_list(value)

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
def get_env_settings(dotenv_path: Optional[str] = None) -> "Settings":
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
