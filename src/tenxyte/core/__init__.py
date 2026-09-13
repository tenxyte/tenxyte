"""Tenxyte Core - Framework agnostic authentication core."""

__version__ = "0.9.2.5"

from .auth_service import (
    AuthenticationService,
    AuthResult,
    PasswordUserLookup,
)
from .cache_service import (
    CacheService,
    InMemoryCacheService,
)
from .email_service import (
    ConsoleEmailService,
    EmailAttachment,
    EmailService,
)
from .env_provider import (
    EnvSettingsProvider,
    get_env_settings,
)
from .jwt_service import (
    DecodedToken,
    InMemoryTokenBlacklistService,
    JWTService,
    TokenBlacklistService,
    TokenPair,
)
from .magic_link_service import (
    MagicLinkRepository,
    MagicLinkResult,
    MagicLinkService,
    MagicLinkToken,
    UserLookup,
)
from .schemas import (
    LoginRequest,
    OrganizationBase,
    OrganizationCreate,
    OrganizationResponse,
    TokenResponse,
    UserBase,
    UserCreate,
    UserInDB,
    UserResponse,
    UserUpdate,
)
from .settings import (
    SECURE_MODE_PRESETS,
    SecureModePreset,
    Settings,
    SettingsProvider,
    get_settings,
    init,
)
from .task_service import TaskService
from .totp_service import (
    CodeReplayProtection,
    TOTPService,
    TOTPSetupResult,
    TOTPStorage,
    TOTPUserData,
)
from .webauthn_service import (
    AuthenticationResult,
    RegistrationResult,
    WebAuthnChallenge,
    WebAuthnChallengeRepository,
    WebAuthnCredential,
    WebAuthnCredentialRepository,
    WebAuthnService,
)

__all__ = [  # noqa: RUF022
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
    "TaskService",
    # Services - Authentication
    "AuthenticationService",
    "AuthResult",
    "PasswordUserLookup",
]
