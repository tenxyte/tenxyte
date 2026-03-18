"""
Django Settings Provider for Tenxyte Core.

This module provides a SettingsProvider that reads from Django's settings.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tenxyte.core.settings import Settings

from tenxyte.core.settings import SettingsProvider


class DjangoSettingsProvider(SettingsProvider):
    """
    Settings provider that reads from Django's settings.

    This provider automatically imports Django settings and makes them
    available to the Tenxyte Core in a framework-agnostic way.

    Example:
        from tenxyte.core.settings import init, Settings
        from tenxyte.adapters.django import DjangoSettingsProvider

        # Initialize with Django provider
        settings = init(provider=DjangoSettingsProvider())

        # Now settings automatically reads from django.conf.settings
        print(settings.jwt_secret_key)  # Reads TENXYTE_JWT_SECRET_KEY from Django
    """

    def __init__(self):
        """Initialize the Django settings provider."""
        self._django_settings = None

    def _get_django_settings(self):
        """Lazy import Django settings to avoid circular imports."""
        if self._django_settings is None:
            from django.conf import settings as django_settings

            self._django_settings = django_settings
        return self._django_settings

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value from Django settings.

        Args:
            name: Full setting name (e.g., 'TENXYTE_JWT_SECRET_KEY')
            default: Default value if setting not found

        Returns:
            The setting value or default
        """
        settings = self._get_django_settings()

        if hasattr(settings, name):
            return getattr(settings, name)

        return default

    @property
    def debug(self) -> bool:
        """Check if Django is in DEBUG mode."""
        return self._get_django_settings().DEBUG


# Convenience function for Django integration
def get_django_settings() -> "Settings":
    """
    Get or initialize Tenxyte settings with Django provider.

    This is a convenience function that handles the initialization
    automatically for Django projects.

    Returns:
        Settings instance configured with Django provider

    Example:
        from tenxyte.adapters.django import get_django_settings

        settings = get_django_settings()
        print(settings.jwt_access_token_lifetime)
    """
    from tenxyte.core.settings import _settings, init

    if _settings is None:
        provider = DjangoSettingsProvider()
        return init(provider=provider)

    return _settings
