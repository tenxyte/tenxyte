"""
Tenxyte Serializers Package.

All serializers are re-exported here for backward compatibility.
Usage: from tenxyte.serializers import UserSerializer, RoleSerializer, ...
"""

# Auth serializers
# Application serializers
from .application_serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationUpdateSerializer,
)
from .auth_serializers import (
    LoginEmailSerializer,
    LoginPhoneSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    UserSerializer,
)

# GDPR admin serializers
from .gdpr_admin_serializers import (
    DeletionRequestSerializer,
    ProcessDeletionSerializer,
)

# Login OTP serializers
from .login_otp_serializers import (
    LoginOTPRequestSerializer,
    LoginOTPVerifySerializer,
    ReauthSerializer,
    SetInitialPasswordSerializer,
)

# Organization serializers
from .organization_serializers import (
    AddMemberSerializer,
    CreateOrganizationSerializer,
    InviteMemberSerializer,
    OrganizationInvitationSerializer,
    OrganizationMembershipSerializer,
    OrganizationRoleSerializer,
    OrganizationSerializer,
    OrganizationTreeSerializer,
    UpdateMemberRoleSerializer,
    UpdateOrganizationSerializer,
    UserBasicSerializer,
)

# OTP serializers
from .otp_serializers import (
    RequestOTPSerializer,
    VerifyOTPSerializer,
)

# Password serializers
from .password_serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordSerializer,
)

# RBAC serializers
from .rbac_serializers import (
    AssignRoleSerializer,
    ManageRolePermissionsSerializer,
    PermissionSerializer,
    RoleListSerializer,
    RoleSerializer,
    UserRolesSerializer,
)

# Security serializers
from .security_serializers import (
    AuditLogSerializer,
    BlacklistedTokenSerializer,
    LoginAttemptSerializer,
    RefreshTokenAdminSerializer,
)

# 2FA serializers
from .twofa_serializers import (
    LoginWith2FASerializer,
    TwoFactorSetupSerializer,
    TwoFactorStatusSerializer,
    TwoFactorVerifySerializer,
)

# User admin serializers
from .user_admin_serializers import (
    AdminUserDetailSerializer,
    AdminUserListSerializer,
    AdminUserUpdateSerializer,
    BanUserSerializer,
    LockUserSerializer,
)

__all__ = [  # noqa: RUF022
    # Auth
    "RegisterSerializer",
    "LoginEmailSerializer",
    "LoginPhoneSerializer",
    "RefreshTokenSerializer",
    "UserSerializer",
    # OTP
    "VerifyOTPSerializer",
    "RequestOTPSerializer",
    # Password
    "PasswordSerializer",
    "PasswordResetRequestSerializer",
    "PasswordResetConfirmSerializer",
    "ChangePasswordSerializer",
    # Login OTP
    "LoginOTPRequestSerializer",
    "LoginOTPVerifySerializer",
    "SetInitialPasswordSerializer",
    "ReauthSerializer",
    # RBAC
    "PermissionSerializer",
    "RoleSerializer",
    "RoleListSerializer",
    "ManageRolePermissionsSerializer",
    "AssignRoleSerializer",
    "UserRolesSerializer",
    # Application
    "ApplicationSerializer",
    "ApplicationCreateSerializer",
    "ApplicationUpdateSerializer",
    # 2FA
    "TwoFactorSetupSerializer",
    "TwoFactorVerifySerializer",
    "TwoFactorStatusSerializer",
    "LoginWith2FASerializer",
    # User Admin
    "AdminUserListSerializer",
    "AdminUserDetailSerializer",
    "AdminUserUpdateSerializer",
    "BanUserSerializer",
    "LockUserSerializer",
    # Security
    "AuditLogSerializer",
    "LoginAttemptSerializer",
    "BlacklistedTokenSerializer",
    "RefreshTokenAdminSerializer",
    # GDPR Admin
    "DeletionRequestSerializer",
    "ProcessDeletionSerializer",
    # Organization
    "OrganizationRoleSerializer",
    "UserBasicSerializer",
    "OrganizationMembershipSerializer",
    "OrganizationSerializer",
    "OrganizationTreeSerializer",
    "CreateOrganizationSerializer",
    "UpdateOrganizationSerializer",
    "AddMemberSerializer",
    "UpdateMemberRoleSerializer",
    "InviteMemberSerializer",
    "OrganizationInvitationSerializer",
]
