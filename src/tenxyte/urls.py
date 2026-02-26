from django.urls import path
from .views import (
    RegisterView, LoginEmailView, LoginPhoneView,
    RefreshTokenView, LogoutView, LogoutAllView,
    RequestOTPView, VerifyEmailOTPView, VerifyPhoneOTPView,
    PasswordResetRequestView, PasswordResetConfirmView, ChangePasswordView,
    PasswordStrengthView, PasswordRequirementsView,
    MeView, MyRolesView,
    TwoFactorStatusView, TwoFactorSetupView, TwoFactorConfirmView,
    TwoFactorDisableView, TwoFactorBackupCodesView,
    PermissionListView, PermissionDetailView,
    RoleListView, RoleDetailView, RolePermissionsView,
    UserRolesView, UserDirectPermissionsView,
    ApplicationListView, ApplicationDetailView, ApplicationRegenerateView,
    UserListView, UserDetailView,
    UserBanView, UserUnbanView, UserLockView, UserUnlockView,
    AuditLogListView, AuditLogDetailView,
    LoginAttemptListView,
    BlacklistedTokenListView, BlacklistedTokenCleanupView,
    RefreshTokenListView, RefreshTokenRevokeView,
)
from .views.account_deletion_views import (
    request_account_deletion, confirm_account_deletion, 
    cancel_account_deletion, account_deletion_status, export_user_data
)
from .views.gdpr_admin_views import (
    DeletionRequestListView, DeletionRequestDetailView,
    ProcessDeletionView, ProcessExpiredDeletionsView,
)
from .views.dashboard_views import (
    DashboardGlobalView, DashboardAuthView, DashboardSecurityView,
    DashboardGDPRView, DashboardOrganizationsView,
)
from .views.magic_link_views import MagicLinkRequestView, MagicLinkVerifyView
from .views.social_auth_views import SocialAuthView
from .views.webauthn_views import (
    WebAuthnRegisterBeginView, WebAuthnRegisterCompleteView,
    WebAuthnAuthenticateBeginView, WebAuthnAuthenticateCompleteView,
    WebAuthnCredentialListView, WebAuthnCredentialDeleteView,
)

app_name = 'authentication'

urlpatterns = [
    # Registration
    path('register/', RegisterView.as_view(), name='register'),

    # Login
    path('login/email/', LoginEmailView.as_view(), name='login_email'),
    path('login/phone/', LoginPhoneView.as_view(), name='login_phone'),

    # Social Login Multi-Provider
    path('social/<str:provider>/', SocialAuthView.as_view(), name='social_auth'),

    # Token management
    path('refresh/', RefreshTokenView.as_view(), name='refresh_token'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout/all/', LogoutAllView.as_view(), name='logout_all'),

    # OTP verification
    path('otp/request/', RequestOTPView.as_view(), name='request_otp'),
    path('otp/verify/email/', VerifyEmailOTPView.as_view(), name='verify_email_otp'),
    path('otp/verify/phone/', VerifyPhoneOTPView.as_view(), name='verify_phone_otp'),

    # Password management
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/', ChangePasswordView.as_view(), name='password_change'),
    path('password/strength/', PasswordStrengthView.as_view(), name='password_strength'),
    path('password/requirements/', PasswordRequirementsView.as_view(), name='password_requirements'),

    # User profile
    path('me/', MeView.as_view(), name='me'),
    path('me/roles/', MyRolesView.as_view(), name='my_roles'),

    # 2FA (Two-Factor Authentication)
    path('2fa/status/', TwoFactorStatusView.as_view(), name='2fa_status'),
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='2fa_setup'),
    path('2fa/confirm/', TwoFactorConfirmView.as_view(), name='2fa_confirm'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='2fa_disable'),
    path('2fa/backup-codes/', TwoFactorBackupCodesView.as_view(), name='2fa_backup_codes'),

    # RBAC - Permissions
    path('permissions/', PermissionListView.as_view(), name='permission_list'),
    path('permissions/<str:permission_id>/', PermissionDetailView.as_view(), name='permission_detail'),

    # RBAC - Roles
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('roles/<str:role_id>/', RoleDetailView.as_view(), name='role_detail'),
    path('roles/<str:role_id>/permissions/', RolePermissionsView.as_view(), name='role_permissions'),

    # RBAC - User Roles & Permissions
    path('users/<str:user_id>/roles/', UserRolesView.as_view(), name='user_roles'),
    path('users/<str:user_id>/permissions/', UserDirectPermissionsView.as_view(), name='user_direct_permissions'),

    # Applications
    path('applications/', ApplicationListView.as_view(), name='application_list'),
    path('applications/<str:app_id>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<str:app_id>/regenerate/', ApplicationRegenerateView.as_view(), name='application_regenerate'),

    # Account Deletion (RGPD)
    path('request-account-deletion/', request_account_deletion, name='request_account_deletion'),
    path('confirm-account-deletion/', confirm_account_deletion, name='confirm_account_deletion'),
    path('cancel-account-deletion/', cancel_account_deletion, name='cancel_account_deletion'),
    path('account-deletion-status/', account_deletion_status, name='account_deletion_status'),
    path('export-user-data/', export_user_data, name='export_user_data'),

    # Admin - User Management
    path('admin/users/', UserListView.as_view(), name='admin_user_list'),
    path('admin/users/<str:user_id>/', UserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<str:user_id>/ban/', UserBanView.as_view(), name='admin_user_ban'),
    path('admin/users/<str:user_id>/unban/', UserUnbanView.as_view(), name='admin_user_unban'),
    path('admin/users/<str:user_id>/lock/', UserLockView.as_view(), name='admin_user_lock'),
    path('admin/users/<str:user_id>/unlock/', UserUnlockView.as_view(), name='admin_user_unlock'),

    # Admin - Security
    path('admin/audit-logs/', AuditLogListView.as_view(), name='admin_audit_log_list'),
    path('admin/audit-logs/<str:log_id>/', AuditLogDetailView.as_view(), name='admin_audit_log_detail'),
    path('admin/login-attempts/', LoginAttemptListView.as_view(), name='admin_login_attempt_list'),
    path('admin/blacklisted-tokens/', BlacklistedTokenListView.as_view(), name='admin_blacklisted_token_list'),
    path('admin/blacklisted-tokens/cleanup/', BlacklistedTokenCleanupView.as_view(), name='admin_blacklisted_token_cleanup'),
    path('admin/refresh-tokens/', RefreshTokenListView.as_view(), name='admin_refresh_token_list'),
    path('admin/refresh-tokens/<str:token_id>/revoke/', RefreshTokenRevokeView.as_view(), name='admin_refresh_token_revoke'),

    # Admin - GDPR
    path('admin/deletion-requests/', DeletionRequestListView.as_view(), name='admin_deletion_request_list'),
    path('admin/deletion-requests/process-expired/', ProcessExpiredDeletionsView.as_view(), name='admin_process_expired_deletions'),
    path('admin/deletion-requests/<str:request_id>/', DeletionRequestDetailView.as_view(), name='admin_deletion_request_detail'),
    path('admin/deletion-requests/<str:request_id>/process/', ProcessDeletionView.as_view(), name='admin_process_deletion'),

    # Magic Link (Passwordless)
    path('magic-link/request/', MagicLinkRequestView.as_view(), name='magic_link_request'),
    path('magic-link/verify/', MagicLinkVerifyView.as_view(), name='magic_link_verify'),

    # WebAuthn / Passkeys (FIDO2)
    path('webauthn/register/begin/', WebAuthnRegisterBeginView.as_view(), name='webauthn_register_begin'),
    path('webauthn/register/complete/', WebAuthnRegisterCompleteView.as_view(), name='webauthn_register_complete'),
    path('webauthn/authenticate/begin/', WebAuthnAuthenticateBeginView.as_view(), name='webauthn_authenticate_begin'),
    path('webauthn/authenticate/complete/', WebAuthnAuthenticateCompleteView.as_view(), name='webauthn_authenticate_complete'),
    path('webauthn/credentials/', WebAuthnCredentialListView.as_view(), name='webauthn_credential_list'),
    path('webauthn/credentials/<int:credential_id>/', WebAuthnCredentialDeleteView.as_view(), name='webauthn_credential_delete'),

    # Dashboard
    path('dashboard/stats/', DashboardGlobalView.as_view(), name='dashboard_global'),
    path('dashboard/auth/', DashboardAuthView.as_view(), name='dashboard_auth'),
    path('dashboard/security/', DashboardSecurityView.as_view(), name='dashboard_security'),
    path('dashboard/gdpr/', DashboardGDPRView.as_view(), name='dashboard_gdpr'),
    path('dashboard/organizations/', DashboardOrganizationsView.as_view(), name='dashboard_organizations'),
]

# =============================================
# Organizations (Conditional - Opt-in Feature)
# =============================================

from .conf import org_settings

if org_settings.ORGANIZATIONS_ENABLED:
    from .views.organization_views import (
        create_organization,
        list_organizations,
        get_organization,
        update_organization,
        delete_organization,
        get_organization_tree,
        list_members,
        add_member,
        update_member_role,
        remove_member,
        invite_member,
        list_org_roles,
    )
    
    # Add organization URLs to urlpatterns
    urlpatterns += [
        # Organizations CRUD
        path('organizations/', create_organization, name='create_organization'),
        path('organizations/list/', list_organizations, name='list_organizations'),
        path('organizations/detail/', get_organization, name='get_organization'),
        path('organizations/update/', update_organization, name='update_organization'),
        path('organizations/delete/', delete_organization, name='delete_organization'),
        
        # Hierarchy
        path('organizations/tree/', get_organization_tree, name='get_organization_tree'),
        
        # Members
        path('organizations/members/', list_members, name='list_members'),
        path('organizations/members/add/', add_member, name='add_member'),
        path('organizations/members/<int:user_id>/', update_member_role, name='update_member_role'),
        path('organizations/members/<int:user_id>/remove/', remove_member, name='remove_member'),
        
        # Invitations
        path('organizations/invitations/', invite_member, name='invite_member'),
        
        # Organization Roles
        path('org-roles/', list_org_roles, name='list_org_roles'),
    ]
