from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    get_user_model,
    get_role_model,
    get_permission_model,
    get_application_model,
    RefreshToken,
    LoginAttempt,
    OTPCode,
    AuditLog,
    PasswordHistory,
    BlacklistedToken,
)

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()
Application = get_application_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin pour le modèle User de tenxyte."""
    
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_2fa_enabled', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_2fa_enabled', 'is_email_verified', 'is_phone_verified')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    filter_horizontal = ('roles', 'direct_permissions')
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'phone_country_code', 'phone_number')}),
        (_('OAuth'), {'fields': ('google_id',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'roles', 'direct_permissions')}),
        (_('Vérification'), {'fields': ('is_email_verified', 'is_phone_verified')}),
        (_('2FA'), {'fields': ('is_2fa_enabled', 'totp_secret', 'backup_codes')}),
        (_('Sessions'), {'fields': ('max_sessions', 'max_devices')}),
        (_('Verrouillage'), {'fields': ('is_locked', 'locked_until')}),
        (_('Dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin pour le modèle Role."""
    
    list_display = ('code', 'name', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('permissions',)
    ordering = ('code',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin pour le modèle Permission."""
    
    list_display = ('code', 'name', 'parent', 'created_at')
    list_filter = ('parent',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    raw_id_fields = ('parent',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Admin pour le modèle Application."""
    
    list_display = ('name', 'access_key', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'access_key')
    readonly_fields = ('access_key', 'access_secret', 'created_at', 'updated_at')
    ordering = ('name',)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    """Admin pour les refresh tokens."""
    
    list_display = ('token_short', 'user', 'is_revoked', 'expires_at', 'created_at')
    list_filter = ('is_revoked',)
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'last_used_at')
    raw_id_fields = ('user', 'application')
    ordering = ('-created_at',)
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..." if obj.token else "-"
    token_short.short_description = 'Token'


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin pour les tentatives de connexion."""
    
    list_display = ('identifier', 'ip_address', 'success', 'failure_reason', 'created_at')
    list_filter = ('success',)
    search_fields = ('identifier', 'ip_address')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """Admin pour les codes OTP."""
    
    list_display = ('user', 'otp_type', 'is_used', 'expires_at', 'created_at')
    list_filter = ('otp_type', 'is_used')
    search_fields = ('user__email',)
    readonly_fields = ('code', 'created_at')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin pour les logs d'audit."""
    
    list_display = ('action', 'user', 'ip_address', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__email', 'action', 'ip_address')
    readonly_fields = ('action', 'user', 'application', 'ip_address', 'details', 'created_at')
    raw_id_fields = ('user', 'application')
    ordering = ('-created_at',)


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    """Admin pour l'historique des mots de passe."""
    
    list_display = ('user', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('user', 'password_hash', 'created_at')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)


@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    """Admin pour les tokens blacklistés."""
    
    list_display = ('token_jti_short', 'user', 'reason', 'blacklisted_at', 'expires_at')
    list_filter = ('reason',)
    search_fields = ('token_jti', 'user__email', 'reason')
    readonly_fields = ('token_jti', 'blacklisted_at')
    raw_id_fields = ('user',)
    ordering = ('-blacklisted_at',)
    
    def token_jti_short(self, obj):
        return f"{obj.token_jti[:20]}..." if obj.token_jti else "-"
    token_jti_short.short_description = 'Token JTI'
