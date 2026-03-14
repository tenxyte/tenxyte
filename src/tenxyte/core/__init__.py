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
from .env_provider import (
    EnvSettingsProvider,
    get_env_settings,
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
from .jwt_service import (
    JWTService,
    TokenPair,
    DecodedToken,
    TokenBlacklistService,
    InMemoryTokenBlacklistService,
)
from .totp_service import (
    TOTPService,
    TOTPSetupResult,
    TOTPUserData,
    TOTPStorage,
    CodeReplayProtection,
)
from .webauthn_service import (
    WebAuthnService,
    WebAuthnCredential,
    WebAuthnChallenge,
    RegistrationResult,
    AuthenticationResult,
    WebAuthnCredentialRepository,
    WebAuthnChallengeRepository,
)
from .magic_link_service import (
    MagicLinkService,
    MagicLinkToken,
    MagicLinkResult,
    MagicLinkRepository,
    UserLookup,
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
    # Environment Provider
    "EnvSettingsProvider",
    "get_env_settings",
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
    # Services - JWT
    "JWTService",
    "TokenPair",
    "DecodedToken",
    "TokenBlacklistService",
    "InMemoryTokenBlacklistService",
    # Services - TOTP
    "TOTPService",
    "TOTPSetupResult",
    "TOTPUserData",
    "TOTPStorage",
    "CodeReplayProtection",
    # Services - WebAuthn
    "WebAuthnService",
    "WebAuthnCredential",
    "WebAuthnChallenge",
    "RegistrationResult",
    "AuthenticationResult",
    "WebAuthnCredentialRepository",
    "WebAuthnChallengeRepository",
    # Services - Magic Link
    "MagicLinkService",
    "MagicLinkToken",
    "MagicLinkResult",
    "MagicLinkRepository",
    "UserLookup",
]
