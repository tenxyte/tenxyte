"""
Tenxyte Serializers Package.

All serializers are re-exported here for backward compatibility.
Usage: from tenxyte.serializers import UserSerializer, RoleSerializer, ...
"""

# Auth serializers
from .auth_serializers import (
    RegisterSerializer,
    LoginEmailSerializer,
    LoginPhoneSerializer,
    RefreshTokenSerializer,
    GoogleAuthSerializer,
    UserSerializer,
)

# OTP serializers
from .otp_serializers import (
    VerifyOTPSerializer,
    RequestOTPSerializer,
)

# Password serializers
from .password_serializers import (
    PasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
)

# RBAC serializers
from .rbac_serializers import (
    PermissionSerializer,
    RoleSerializer,
    RoleListSerializer,
    ManageRolePermissionsSerializer,
    AssignRoleSerializer,
    UserRolesSerializer,
)

# Application serializers
from .application_serializers import (
    ApplicationSerializer,
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
)

# 2FA serializers
from .twofa_serializers import (
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    TwoFactorStatusSerializer,
    LoginWith2FASerializer,
)

# User admin serializers
from .user_admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    BanUserSerializer,
    LockUserSerializer,
)

# Security serializers
from .security_serializers import (
    AuditLogSerializer,
    LoginAttemptSerializer,
    BlacklistedTokenSerializer,
    RefreshTokenAdminSerializer,
)

# GDPR admin serializers
from .gdpr_admin_serializers import (
    DeletionRequestSerializer,
    ProcessDeletionSerializer,
)

# Organization serializers
from .organization_serializers import (
    OrganizationRoleSerializer,
    UserBasicSerializer,
    OrganizationMembershipSerializer,
    OrganizationSerializer,
    OrganizationTreeSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer,
    InviteMemberSerializer,
    OrganizationInvitationSerializer,
)


__all__ = [
    # Auth
    'RegisterSerializer',
    'LoginEmailSerializer',
    'LoginPhoneSerializer',
    'RefreshTokenSerializer',
    'GoogleAuthSerializer',
    'UserSerializer',
    # OTP
    'VerifyOTPSerializer',
    'RequestOTPSerializer',
    # Password
    'PasswordSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'ChangePasswordSerializer',
    # RBAC
    'PermissionSerializer',
    'RoleSerializer',
    'RoleListSerializer',
    'ManageRolePermissionsSerializer',
    'AssignRoleSerializer',
    'UserRolesSerializer',
    # Application
    'ApplicationSerializer',
    'ApplicationCreateSerializer',
    'ApplicationUpdateSerializer',
    # 2FA
    'TwoFactorSetupSerializer',
    'TwoFactorVerifySerializer',
    'TwoFactorStatusSerializer',
    'LoginWith2FASerializer',
    # User Admin
    'AdminUserListSerializer',
    'AdminUserDetailSerializer',
    'AdminUserUpdateSerializer',
    'BanUserSerializer',
    'LockUserSerializer',
    # Security
    'AuditLogSerializer',
    'LoginAttemptSerializer',
    'BlacklistedTokenSerializer',
    'RefreshTokenAdminSerializer',
    # GDPR Admin
    'DeletionRequestSerializer',
    'ProcessDeletionSerializer',
    # Organization
    'OrganizationRoleSerializer',
    'UserBasicSerializer',
    'OrganizationMembershipSerializer',
    'OrganizationSerializer',
    'OrganizationTreeSerializer',
    'CreateOrganizationSerializer',
    'UpdateOrganizationSerializer',
    'AddMemberSerializer',
    'UpdateMemberRoleSerializer',
    'InviteMemberSerializer',
    'OrganizationInvitationSerializer',
]
