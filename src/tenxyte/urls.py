from django.urls import path
from .views import (
    RegisterView, LoginEmailView, LoginPhoneView, GoogleAuthView,
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
    ApplicationListView, ApplicationDetailView, ApplicationRegenerateView
)
from .views.account_deletion_views import (
    request_account_deletion, confirm_account_deletion, 
    cancel_account_deletion, account_deletion_status, export_user_data
)

app_name = 'authentication'

urlpatterns = [
    # Registration
    path('register/', RegisterView.as_view(), name='register'),

    # Login
    path('login/email/', LoginEmailView.as_view(), name='login_email'),
    path('login/phone/', LoginPhoneView.as_view(), name='login_phone'),
    path('google/', GoogleAuthView.as_view(), name='google_auth'),

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
]
