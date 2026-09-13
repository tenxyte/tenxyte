"""
Tenxyte Models Package.

All models are re-exported here for backward compatibility.
Usage: from tenxyte.models import User, Role, Permission, Application, ...
"""

# Base utilities
# Agent models
from .agent import (
    AgentPendingAction,
    AgentToken,
)

# Application models (Abstract + Concrete)
from .application import (
    AbstractApplication,
    Application,
)

# Auth models (Abstract + Concrete)
from .auth import (
    AbstractPermission,
    AbstractRole,
    AbstractUser,
    Permission,
    Role,
    User,
    UserManager,
)
from .base import (
    AutoFieldClass,
    _get_auto_field_class,
    get_application_model,
    get_organization_membership_model,
    get_organization_model,
    get_organization_role_model,
    get_permission_model,
    get_role_model,
    get_user_model,
)

# GDPR models
from .gdpr import (
    AccountDeletionRequest,
)

# Magic Link models
from .magic_link import (
    MagicLinkToken,
)

# Operational models
from .operational import (
    LoginAttempt,
    OTPCode,
    RefreshToken,
)

# Organization models (Abstract + Concrete)
from .organization import (
    AbstractOrganization,
    AbstractOrganizationInvitation,
    AbstractOrganizationMembership,
    AbstractOrganizationRole,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationRole,
)

# Security models
from .security import (
    AuditLog,
    BlacklistedToken,
    PasswordHistory,
)

# Social Login models
from .social import (
    SocialConnection,
)

# Multi-Tenancy Base Model
from .tenant import BaseTenantModel

# WebAuthn / Passkeys models
from .webauthn import (
    WebAuthnChallenge,
    WebAuthnCredential,
)

__all__ = [  # noqa: RUF022
    # Base
    "_get_auto_field_class",
    "AutoFieldClass",
    "get_user_model",
    "get_role_model",
    "get_permission_model",
    "get_application_model",
    "get_organization_model",
    "get_organization_role_model",
    "get_organization_membership_model",
    # Auth
    "UserManager",
    "AbstractPermission",
    "AbstractRole",
    "AbstractUser",
    "Permission",
    "Role",
    "User",
    # Application
    "AbstractApplication",
    "Application",
    # Operational
    "OTPCode",
    "RefreshToken",
    "LoginAttempt",
    # Security
    "BlacklistedToken",
    "AuditLog",
    "PasswordHistory",
    # GDPR
    "AccountDeletionRequest",
    # Magic Link
    "MagicLinkToken",
    # Social Login
    "SocialConnection",
    # WebAuthn
    "WebAuthnCredential",
    "WebAuthnChallenge",
    # Organization
    "AbstractOrganization",
    "AbstractOrganizationRole",
    "AbstractOrganizationMembership",
    "AbstractOrganizationInvitation",
    "Organization",
    "OrganizationRole",
    "OrganizationMembership",
    "OrganizationInvitation",
    # Agent
    "AgentToken",
    "AgentPendingAction",
    # Tenant
    "BaseTenantModel",
]
