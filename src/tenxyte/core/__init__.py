"""Tenxyte Core - Framework agnostic authentication core."""

__version__ = "0.9.2.5"

from .settings import (
    Settings,
    SettingsProvider,
    SecureModePreset,
    SECURE_MODE_PRESETS,
    init,
    get_settings,
)
from .email_service import (
    EmailService,
    EmailAttachment,
    ConsoleEmailService,
)
from .cache_service import (
    CacheService,
    InMemoryCacheService,
)
from .schemas import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    LoginRequest,
    TokenResponse,
    OrganizationBase,
    OrganizationCreate,
    OrganizationResponse,
)

__all__ = [
    # Settings
    "Settings",
    "SettingsProvider",
    "SecureModePreset",
    "SECURE_MODE_PRESETS",
    "init",
    "get_settings",
    # Email
    "EmailService",
    "EmailAttachment",
    "ConsoleEmailService",
    # Cache
    "CacheService",
    "InMemoryCacheService",
    # Schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "LoginRequest",
    "TokenResponse",
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationResponse",
]
