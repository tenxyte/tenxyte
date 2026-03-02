from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

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
    AccountDeletionRequest,
)
from .conf import org_settings

# Conditional Organizations import
if org_settings.ORGANIZATIONS_ENABLED:
    from .models import (
        get_organization_model,
        get_organization_role_model,
        get_organization_membership_model,
        OrganizationInvitation,
    )
    Organization = get_organization_model()
    OrganizationRole = get_organization_role_model()
    OrganizationMembership = get_organization_membership_model()

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()
Application = get_application_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin pour le modèle User de tenxyte."""
    
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_banned', 'is_2fa_enabled', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_banned', 'is_2fa_enabled', 'is_email_verified', 'is_phone_verified')
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
        (_('Verrouillage'), {'fields': ('is_locked', 'locked_until', 'is_banned')}),
        (_('Dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    actions = ['ban_users', 'unban_users']
    
    def ban_users(self, request, queryset):
        """Ban selected users permanently."""
        # Get user details for audit before updating
        users_details = [{'id': user.id, 'email': user.email} for user in queryset]
        
        count = queryset.update(is_banned=True)
        
        # Log audit for each banned user
        for user_detail in users_details:
            from .models import AuditLog
            AuditLog.objects.create(
                action='user_banned',
                user_id=user_detail['id'],
                ip_address=self._get_client_ip(request),
                details={
                    'banned_by': request.user.email if hasattr(request.user, 'email') else str(request.user),
                    'reason': 'Admin action',
                    'email': user_detail['email'],
                    'banned_at': timezone.now().isoformat()
                }
            )
        
        self.message_user(request, f'{count} utilisateur(s) banni(s) avec succès.', messages.SUCCESS)
    ban_users.short_description = 'Bannir les utilisateurs sélectionnés'
    
    def unban_users(self, request, queryset):
        """Unban selected users."""
        # Get user details for audit before updating
        users_details = [{'id': user.id, 'email': user.email} for user in queryset]
        
        count = queryset.update(is_banned=False)
        
        # Log audit for each unbanned user
        for user_detail in users_details:
            from .models import AuditLog
            AuditLog.objects.create(
                action='user_unbanned',
                user_id=user_detail['id'],
                ip_address=self._get_client_ip(request),
                details={
                    'unbanned_by': request.user.email if hasattr(request.user, 'email') else str(request.user),
                    'reason': 'Admin action',
                    'email': user_detail['email'],
                    'unbanned_at': timezone.now().isoformat()
                }
            )
        
        self.message_user(request, f'{count} utilisateur(s) débanni(s) avec succès.', messages.SUCCESS)
    unban_users.short_description = 'Débannir les utilisateurs sélectionnés'
    
    def get_actions(self, request):
        """Filter actions based on user selection."""
        actions = super().get_actions(request)
        if 'ban_users' in actions:
            # Only show ban action for non-banned users
            selected = request.POST.getlist('_selected_action')
            if selected:
                users = self.get_queryset(request).filter(pk__in=selected)
                if users.filter(is_banned=True).exists():
                    del actions['ban_users']
        if 'unban_users' in actions:
            # Only show unban action for banned users
            selected = request.POST.getlist('_selected_action')
            if selected:
                users = self.get_queryset(request).filter(pk__in=selected)
                if users.filter(is_banned=False).exists():
                    del actions['unban_users']
        return actions
    
    def _get_client_ip(self, request):
        """Get client IP address for audit logging."""
        from .conf import auth_settings
        trusted = auth_settings.TRUSTED_PROXIES

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR', '')

        if x_forwarded_for:
            if not trusted:
                return x_forwarded_for.split(',')[0].strip()

            import ipaddress
            try:
                remote_ip = ipaddress.ip_address(remote_addr)
                for trusted_entry in trusted:
                    try:
                        network = ipaddress.ip_network(trusted_entry, strict=False)
                        if remote_ip in network:
                            return x_forwarded_for.split(',')[0].strip()
                    except ValueError:
                        continue
            except ValueError:
                pass
                
            import logging
            logging.getLogger('tenxyte.security').warning(
                "X-Forwarded-For header rejected: REMOTE_ADDR %s is not in TRUSTED_PROXIES.", remote_addr
            )
        return remote_addr
    
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


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    """Admin pour les demandes de suppression de compte."""
    
    list_display = ('user_email', 'status', 'requested_at', 'grace_period_ends_at', 'days_remaining', 'processed_by')
    list_filter = ('status', 'requested_at', 'confirmed_at')
    search_fields = ('user__email', 'reason', 'ip_address')
    readonly_fields = ('confirmation_token', 'requested_at', 'confirmed_at', 'grace_period_ends_at', 'completed_at', 'ip_address', 'user_agent')
    raw_id_fields = ('user', 'processed_by')
    ordering = ('-requested_at',)
    
    actions = ['approve_requests', 'reject_requests', 'cancel_requests', 'execute_requests']
    
    fieldsets = (
        (None, {'fields': ('user', 'status', 'reason')}),
        (_('Timestamps'), {'fields': ('requested_at', 'confirmed_at', 'grace_period_ends_at', 'completed_at')}),
        (_('Request Details'), {'fields': ('confirmation_token', 'ip_address', 'user_agent')}),
        (_('Admin Actions'), {'fields': ('admin_notes', 'processed_by')}),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else "N/A"
    user_email.short_description = 'User Email'
    
    def days_remaining(self, obj):
        if obj.grace_period_ends_at:
            from django.utils import timezone
            remaining = obj.grace_period_ends_at - timezone.now()
            if remaining.days > 0:
                return f"{remaining.days} days"
            elif remaining.days == 0:
                return f"{remaining.seconds // 3600} hours"
            else:
                return "Expired"
        return "-"
    days_remaining.short_description = 'Days Remaining'
    
    def approve_requests(self, request, queryset):
        """Approuver les demandes sélectionnées."""
        from .services.account_deletion_service import AccountDeletionService
        
        service = AccountDeletionService()
        approved_count = 0
        
        for deletion_request in queryset.filter(status='confirmation_sent'):
            success, message = service.admin_process_request(
                request_id=deletion_request.id,
                action='approve',
                admin_user=request.user
            )
            if success:
                approved_count += 1
        
        if approved_count > 0:
            self.message_user(request, f'{approved_count} demande(s) approuvée(s).', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucune demande éligible à l\'approbation.', messages.WARNING)
    
    approve_requests.short_description = 'Approuver les demandes sélectionnées'
    
    def reject_requests(self, request, queryset):
        """Rejeter les demandes sélectionnées."""
        from .services.account_deletion_service import AccountDeletionService
        
        service = AccountDeletionService()
        rejected_count = 0
        
        for deletion_request in queryset.filter(status__in=['pending', 'confirmation_sent']):
            success, message = service.admin_process_request(
                request_id=deletion_request.id,
                action='reject',
                admin_user=request.user
            )
            if success:
                rejected_count += 1
        
        if rejected_count > 0:
            self.message_user(request, f'{rejected_count} demande(s) rejetée(s).', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucune demande éligible au rejet.', messages.WARNING)
    
    reject_requests.short_description = 'Rejeter les demandes sélectionnées'
    
    def cancel_requests(self, request, queryset):
        """Annuler les demandes sélectionnées."""
        from .services.account_deletion_service import AccountDeletionService
        
        service = AccountDeletionService()
        cancelled_count = 0
        
        for deletion_request in queryset.filter(status__in=['pending', 'confirmation_sent', 'confirmed']):
            success, message = service.admin_process_request(
                request_id=deletion_request.id,
                action='cancel',
                admin_user=request.user
            )
            if success:
                cancelled_count += 1
        
        if cancelled_count > 0:
            self.message_user(request, f'{cancelled_count} demande(s) annulée(s).', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucune demande éligible à l\'annulation.', messages.WARNING)
    
    cancel_requests.short_description = 'Annuler les demandes sélectionnées'
    
    def execute_requests(self, request, queryset):
        """Exécuter les suppressions sélectionnées."""
        from .services.account_deletion_service import AccountDeletionService
        
        service = AccountDeletionService()
        executed_count = 0
        
        for deletion_request in queryset.filter(status='confirmed'):
            success, message = service.admin_process_request(
                request_id=deletion_request.id,
                action='execute',
                admin_user=request.user
            )
            if success:
                executed_count += 1
        
        if executed_count > 0:
            self.message_user(request, f'{executed_count} suppression(s) exécutée(s).', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucune demande éligible à l\'exécution.', messages.WARNING)
    
    execute_requests.short_description = 'Exécuter les suppressions sélectionnées'
    
    def get_actions(self, request):
        """Filtrer les actions selon le contexte."""
        actions = super().get_actions(request)
        
        # Filtrer selon les objets sélectionnés
        if hasattr(request, '_selected_obj'):
            selected = request._selected_obj
            if not selected.filter(status='confirmation_sent').exists():
                actions.pop('approve_requests', None)
            if not selected.filter(status__in=['pending', 'confirmation_sent']).exists():
                actions.pop('reject_requests', None)
            if not selected.filter(status__in=['pending', 'confirmation_sent', 'confirmed']).exists():
                actions.pop('cancel_requests', None)
            if not selected.filter(status='confirmed').exists():
                actions.pop('execute_requests', None)
        
        return actions


# =============================================
# Organizations Admin (Conditional)
# =============================================

if org_settings.ORGANIZATIONS_ENABLED:
    
    @admin.register(Organization)
    class OrganizationAdmin(admin.ModelAdmin):
        """Admin for Organization model."""
        
        list_display = ('name', 'slug', 'parent', 'is_active', 'member_count', 'created_at', 'created_by')
        list_filter = ('is_active', 'created_at')
        search_fields = ('name', 'slug', 'description')
        readonly_fields = ('slug', 'created_at', 'updated_at', 'created_by')
        raw_id_fields = ('parent', 'created_by')
        ordering = ('-created_at',)
        
        fieldsets = (
            (None, {'fields': ('name', 'slug', 'description', 'parent')}),
            (_('Settings'), {'fields': ('is_active', 'max_members', 'metadata')}),
            (_('Dates'), {'fields': ('created_at', 'updated_at', 'created_by')}),
        )
        
        def member_count(self, obj):
            return obj.get_member_count()
        member_count.short_description = 'Members'
    
    
    @admin.register(OrganizationRole)
    class OrganizationRoleAdmin(admin.ModelAdmin):
        """Admin for OrganizationRole model."""
        
        list_display = ('name', 'code', 'is_system', 'is_default', 'created_at')
        list_filter = ('is_system', 'is_default')
        search_fields = ('name', 'code', 'description')
        readonly_fields = ('created_at', 'updated_at')
        ordering = ('name',)
        
        fieldsets = (
            (None, {'fields': ('code', 'name', 'description')}),
            (_('Properties'), {'fields': ('is_system', 'is_default', 'permissions')}),
            (_('Dates'), {'fields': ('created_at', 'updated_at')}),
        )
    
    
    @admin.register(OrganizationMembership)
    class OrganizationMembershipAdmin(admin.ModelAdmin):
        """Admin for OrganizationMembership model."""
        
        list_display = ('user_email', 'organization_name', 'role_name', 'status', 'created_at')
        list_filter = ('status', 'role', 'created_at')
        search_fields = ('user__email', 'organization__name')
        readonly_fields = ('created_at', 'updated_at', 'invited_by', 'invited_at')
        raw_id_fields = ('user', 'organization', 'role', 'invited_by')
        ordering = ('-created_at',)
        
        fieldsets = (
            (None, {'fields': ('user', 'organization', 'role', 'status')}),
            (_('Invitation'), {'fields': ('invited_by', 'invited_at')}),
            (_('Dates'), {'fields': ('created_at', 'updated_at')}),
        )
        
        def user_email(self, obj):
            return obj.user.email if obj.user else "N/A"
        user_email.short_description = 'User'
        
        def organization_name(self, obj):
            return obj.organization.name if obj.organization else "N/A"
        organization_name.short_description = 'Organization'
        
        def role_name(self, obj):
            return obj.role.name if obj.role else "N/A"
        role_name.short_description = 'Role'
    
    
    @admin.register(OrganizationInvitation)
    class OrganizationInvitationAdmin(admin.ModelAdmin):
        """Admin for OrganizationInvitation model."""
        
        list_display = ('email', 'organization_name', 'role_name', 'status', 'invited_by_email', 'created_at', 'expires_at')
        list_filter = ('status', 'created_at', 'expires_at')
        search_fields = ('email', 'organization__name', 'token')
        readonly_fields = ('token', 'created_at', 'expires_at', 'accepted_at', 'invited_by')
        raw_id_fields = ('organization', 'role', 'invited_by')
        ordering = ('-created_at',)
        
        fieldsets = (
            (None, {'fields': ('organization', 'email', 'role', 'status')}),
            (_('Token'), {'fields': ('token',)}),
            (_('Invitation'), {'fields': ('invited_by',)}),
            (_('Dates'), {'fields': ('created_at', 'expires_at', 'accepted_at')}),
        )
        
        def organization_name(self, obj):
            return obj.organization.name if obj.organization else "N/A"
        organization_name.short_description = 'Organization'
        
        def role_name(self, obj):
            return obj.role.name if obj.role else "N/A"
        role_name.short_description = 'Role'
        
        def invited_by_email(self, obj):
            return obj.invited_by.email if obj.invited_by else "N/A"
        invited_by_email.short_description = 'Invited By'
