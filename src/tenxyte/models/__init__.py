"""
Tenxyte Models Package.

All models are re-exported here for backward compatibility.
Usage: from tenxyte.models import User, Role, Permission, Application, ...
"""

# Base utilities
from .base import (
    _get_auto_field_class,
    AutoFieldClass,
    get_user_model,
    get_role_model,
    get_permission_model,
    get_application_model,
    get_organization_model,
    get_organization_role_model,
    get_organization_membership_model,
)

# Auth models (Abstract + Concrete)
from .auth import (
    UserManager,
    AbstractPermission,
    AbstractRole,
    AbstractUser,
    Permission,
    Role,
    User,
)

# Application models (Abstract + Concrete)
from .application import (
    AbstractApplication,
    Application,
)

# Operational models
from .operational import (
    OTPCode,
    RefreshToken,
    LoginAttempt,
)

# Security models
from .security import (
    BlacklistedToken,
    AuditLog,
    PasswordHistory,
)

# GDPR models
from .gdpr import (
    AccountDeletionRequest,
)

# Magic Link models
from .magic_link import (
    MagicLinkToken,
)

# Social Login models
from .social import (
    SocialConnection,
)

# WebAuthn / Passkeys models
from .webauthn import (
    WebAuthnCredential,
    WebAuthnChallenge,
)

# Organization models (Abstract + Concrete)
from .organization import (
    AbstractOrganization,
    AbstractOrganizationRole,
    AbstractOrganizationMembership,
    AbstractOrganizationInvitation,
    Organization,
    OrganizationRole,
    OrganizationMembership,
    OrganizationInvitation,
)

__all__ = [
    # Base
    '_get_auto_field_class',
    'AutoFieldClass',
    'get_user_model',
    'get_role_model',
    'get_permission_model',
    'get_application_model',
    'get_organization_model',
    'get_organization_role_model',
    'get_organization_membership_model',
    # Auth
    'UserManager',
    'AbstractPermission',
    'AbstractRole',
    'AbstractUser',
    'Permission',
    'Role',
    'User',
    # Application
    'AbstractApplication',
    'Application',
    # Operational
    'OTPCode',
    'RefreshToken',
    'LoginAttempt',
    # Security
    'BlacklistedToken',
    'AuditLog',
    'PasswordHistory',
    # GDPR
    'AccountDeletionRequest',
    # Magic Link
    'MagicLinkToken',
    # Social Login
    'SocialConnection',
    # WebAuthn
    'WebAuthnCredential',
    'WebAuthnChallenge',
    # Organization
    'AbstractOrganization',
    'AbstractOrganizationRole',
    'AbstractOrganizationMembership',
    'AbstractOrganizationInvitation',
    'Organization',
    'OrganizationRole',
    'OrganizationMembership',
    'OrganizationInvitation',
]
