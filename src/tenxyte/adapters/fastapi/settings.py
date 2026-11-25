"""
FastAPI settings resolution (spec z_aud_3, Requirement 3.5).

`core/env_provider.py`'s `EnvSettingsProvider` already resolves every `TENXYTE_*` environment
variable framework-agnostically (same names and type conversion Django's settings surface uses)
— there is no FastAPI-specific settings format to build. This module is a thin, documented entry
point rather than a new pydantic-settings implementation, so the FastAPI adapter shares exactly
the same settings resolution as any other framework-agnostic Core consumer.
"""

from __future__ import annotations

from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings


def get_default_settings() -> Settings:
    """
    The FastAPI_Adapter's default `Settings`, resolved from `TENXYTE_*` environment variables.

    Programmatic overrides: construct your own `Settings(provider=...)` with any
    `SettingsProvider` implementation (see `core/settings.py`) and pass it to
    `create_tenxyte_app`/`create_tenxyte_router` instead of relying on this default.
    """
    return Settings(provider=EnvSettingsProvider())
