"""
Tenxyte Models - Authentication models.

Contains:
- UserManager: Custom user manager
- AbstractPermission: Hierarchical permissions
- AbstractRole: Role-based access control
- AbstractUser: Full-featured user model with RBAC + Organization support
- Permission, Role, User: Default concrete implementations (swappable)
"""
import bcrypt
import secrets
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .base import AutoFieldClass


# =============================================================================
# MANAGERS
# =============================================================================

class UserManager(BaseUserManager):
    """Manager personnalisé pour le modèle User."""

    def create_user(self, email=None, password=None, **extra_fields):
        """Crée et sauvegarde un utilisateur."""
        if not email:
            raise ValueError('L\'email est requis')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        """Crée et sauvegarde un superutilisateur."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# =============================================================================
# ABSTRACT MODELS - Extend these in your own app
# =============================================================================

class AbstractPermission(models.Model):
    """
    Abstract Permission model - Extend this to add custom fields.

    Supports hierarchical permissions via the `parent` field.
    Having a parent permission automatically grants all its children.

    Example:
        class CustomPermission(AbstractPermission):
            category = models.CharField(max_length=50)
            is_system = models.BooleanField(default=False)

            class Meta(AbstractPermission.Meta):
                db_table = 'custom_permissions'
    """
    id = AutoFieldClass(primary_key=True)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['code']

    def __str__(self):
        return self.code

    def get_all_children(self, include_self=True):
        """Retourne tous les descendants (récursif)."""
        result = [self] if include_self else []
        for child in self.children.all():
            result.extend(child.get_all_children(include_self=True))
        return result

    def get_ancestors(self, include_self=False):
        """Retourne tous les ancêtres (récursif)."""
        result = [self] if include_self else []
        if self.parent:
            result.append(self.parent)
            result.extend(self.parent.get_ancestors(include_self=False))
        return result


class AbstractRole(models.Model):
    """
    Abstract Role model - Extend this to add custom fields.

    Example:
        class CustomRole(AbstractRole):
            priority = models.IntegerField(default=0)
            color = models.CharField(max_length=7, default='#000000')

            class Meta(AbstractRole.Meta):
                db_table = 'custom_roles'
    """
    id = AutoFieldClass(primary_key=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        'tenxyte.Permission',
        related_name='roles',
        blank=True
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name

    def has_permission(self, permission_code: str) -> bool:
        return self.permissions.filter(code=permission_code).exists()

    @classmethod
    def get_default_role(cls):
        return cls.objects.filter(is_default=True).first()


class AbstractUser(models.Model):
    """
    Abstract User model - Extend this to add custom fields.

    Example:
        class CustomUser(AbstractUser):
            company = models.CharField(max_length=100, blank=True)
            avatar = models.ImageField(upload_to='avatars/', null=True)
            preferences = models.JSONField(default=dict)

            class Meta(AbstractUser.Meta):
                db_table = 'custom_users'

        # In settings.py:
        TENXYTE_USER_MODEL = 'myapp.CustomUser'
        AUTH_USER_MODEL = 'myapp.CustomUser'  # Also set this for Django
    """
    id = AutoFieldClass(primary_key=True)

    # Identifiants
    email = models.EmailField(max_length=191, unique=True, null=True, blank=True, db_index=True)
    phone_country_code = models.CharField(max_length=5, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    # Sécurité
    password = models.CharField(max_length=128)

    # Profil
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # OAuth
    google_id = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)

    # Rôles et permissions
    roles = models.ManyToManyField(
        'tenxyte.Role',
        related_name='users',
        blank=True
    )
    direct_permissions = models.ManyToManyField(
        'tenxyte.Permission',
        related_name='users_direct',
        blank=True
    )

    # Vérification
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # 2FA (TOTP)
    # SECURITY (R2): totp_secret is encrypted at rest using cryptography.fernet in the service layer.
    totp_secret = models.CharField(max_length=255, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)

    # État
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    is_banned = models.BooleanField(
        default=False,
        help_text="Permanent ban (manual admin action). Cannot be auto-lifted."
    )
    
    # Soft delete (RGPD)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    anonymization_token = models.CharField(max_length=100, null=True, blank=True, unique=True)
    
    # --- GDPR / RGPD Compliance (Art. 18) ---
    is_restricted = models.BooleanField(
        default=False, 
        help_text="Marque le compte comme restreint (Art. 18 RGPD). "
                  "Limite le traitement des données sans suppression."
    )

    # Django admin
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Session management
    max_sessions = models.PositiveIntegerField(
        default=1,
        help_text="Maximum concurrent sessions allowed (0 = unlimited)"
    )
    max_devices = models.PositiveIntegerField(
        default=1,
        help_text="Maximum unique devices allowed (0 = unlimited)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Manager
    objects = UserManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['phone_country_code', 'phone_number']),
        ]

    # Configuration Django Auth
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if self.email:
            from django.contrib.auth.models import BaseUserManager
            self.email = BaseUserManager.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    # Proprietes requises par Django/DRF pour l'authentification
    @property
    def is_authenticated(self):
        """Toujours True pour un utilisateur reel (pas AnonymousUser)."""
        return True

    @property
    def is_anonymous(self):
        """Toujours False pour un utilisateur reel."""
        return False

    def has_perm(self, perm, obj=None):
        """Pour compatibilité Django admin."""
        return self.is_superuser or self.has_permission(perm)

    def has_module_perms(self, app_label):
        """Pour compatibilité Django admin."""
        return self.is_superuser

    def set_password(self, raw_password: str):
        from ..conf import auth_settings
        import hashlib
        pre_hash = hashlib.sha256(raw_password.encode('utf-8')).hexdigest()
        self.password = bcrypt.hashpw(
            pre_hash.encode('utf-8'),
            bcrypt.gensalt(rounds=auth_settings.BCRYPT_ROUNDS)
        ).decode('utf-8')

    def check_password(self, raw_password: str) -> bool:
        import hashlib
        pre_hash = hashlib.sha256(raw_password.encode('utf-8')).hexdigest()
        return bcrypt.checkpw(
            pre_hash.encode('utf-8'),
            self.password.encode('utf-8')
        )

    def lock_account(self, duration_minutes: int = 30):
        self.is_locked = True
        self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save()

    def unlock_account(self):
        self.is_locked = False
        self.locked_until = None
        self.save()

    def is_account_locked(self) -> bool:
        if not self.is_locked:
            return False
        if self.locked_until and timezone.now() > self.locked_until:
            self.unlock_account()
            return False
        return True

    def is_account_banned(self) -> bool:
        """Check if the account is permanently banned."""
        return self.is_banned

    def is_account_deleted(self) -> bool:
        """Check if the account is soft deleted."""
        return self.is_deleted

    def soft_delete(self, generate_token=True):
        """
        Soft delete the user account (GDPR compliance).
        Anonymizes PII data while keeping audit trail.
        """
        from django.utils import timezone
        import secrets

        if self.is_deleted:
            return False  # Already deleted
        
        if generate_token:
            self.anonymization_token = secrets.token_urlsafe(32)
        
        # Anonymize personal data
        self.email = f"deleted_{self.id}@deleted.local"
        self.first_name = ""
        self.last_name = ""
        
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        
        self.save(update_fields=['is_deleted', 'deleted_at', 'is_active', 'anonymization_token', 'email', 'first_name', 'last_name'])
        
        # Revoke all Refresh Tokens
        try:
            from .operational import RefreshToken
            RefreshToken.objects.filter(user=self, is_revoked=False).update(is_revoked=True)
        except Exception:
            pass

        return True

    @property
    def full_phone(self) -> str:
        if self.phone_country_code and self.phone_number:
            return f"+{self.phone_country_code}{self.phone_number}"
        return ""

    def __str__(self):
        return self.email or self.full_phone or str(self.id)

    # =============================================
    # Organization Methods (Opt-in Feature)
    # =============================================
    
    def get_organizations(self):
        """
        Get all organizations this user is an active member of.
        
        Returns:
            QuerySet of Organizations
        """
        from ..conf import org_settings
        if not org_settings.ORGANIZATIONS_ENABLED:
            return []
        
        from .base import get_organization_model
        return get_organization_model().objects.filter(
            memberships__user=self,
            memberships__status='active'
        ).distinct()
    
    def get_org_membership(self, organization):
        """
        Get the membership in a specific organization.
        
        Args:
            organization: Organization instance
            
        Returns:
            OrganizationMembership instance or None
        """
        from ..conf import org_settings
        if not org_settings.ORGANIZATIONS_ENABLED:
            return None
        
        from .base import get_organization_membership_model
        OrganizationMembership = get_organization_membership_model()
        try:
            return OrganizationMembership.objects.get(
                user=self,
                organization=organization
            )
        except OrganizationMembership.DoesNotExist:
            return None
    
    def get_org_role(self, organization):
        """
        Get the role of this user in an organization.
        
        Args:
            organization: Organization instance
            
        Returns:
            OrganizationRole instance or None
        """
        membership = self.get_org_membership(organization)
        return membership.role if membership else None
    
    def has_org_role(self, organization, role_code, check_inheritance=True):
        """
        Check if user has a specific role in an organization.
        
        Args:
            organization: Organization instance
            role_code: Role code (e.g., 'admin', 'owner')
            check_inheritance: Check parent organizations if enabled
            
        Returns:
            Boolean
        """
        from ..conf import org_settings
        if not org_settings.ORGANIZATIONS_ENABLED:
            return False
        
        # Check direct membership
        membership = self.get_org_membership(organization)
        if membership and membership.role.code == role_code and membership.is_active_membership():
            return True
        
        # Check inheritance if enabled
        if check_inheritance and org_settings.ORG_ROLE_INHERITANCE:
            # Check if user has this role in any ancestor organization
            ancestors = organization.get_ancestors(include_self=False)
            from .base import get_organization_membership_model
            OrganizationMembership = get_organization_membership_model()
            
            return OrganizationMembership.objects.filter(
                user=self,
                organization__in=ancestors,
                role__code=role_code,
                status='active'
            ).exists()
        
        return False
    
    def has_org_permission(self, organization, permission_code, check_inheritance=True):
        """
        Check if user has a specific permission in an organization.
        
        Args:
            organization: Organization instance
            permission_code: Permission code (e.g., 'org.members.invite')
            check_inheritance: Check parent organizations if enabled
            
        Returns:
            Boolean
        """
        from ..conf import org_settings
        if not org_settings.ORGANIZATIONS_ENABLED:
            return False
        
        # Check direct membership
        membership = self.get_org_membership(organization)
        if membership and membership.has_permission(permission_code) and membership.is_active_membership():
            return True
        
        # Check inheritance if enabled
        if check_inheritance and org_settings.ORG_ROLE_INHERITANCE:
            ancestors = organization.get_ancestors(include_self=False)
            from .base import get_organization_membership_model
            OrganizationMembership = get_organization_membership_model()
            
            for ancestor_membership in OrganizationMembership.objects.filter(
                user=self,
                organization__in=ancestors,
                status='active'
            ):
                if ancestor_membership.has_permission(permission_code):
                    return True
        
        return False
    
    def is_org_member(self, organization):
        """
        Check if user is an active member of an organization.
        
        Args:
            organization: Organization instance
            
        Returns:
            Boolean
        """
        from ..conf import org_settings
        if not org_settings.ORGANIZATIONS_ENABLED:
            return False
        
        membership = self.get_org_membership(organization)
        return membership is not None and membership.is_active_membership()
    
    def is_org_owner(self, organization):
        """
        Check if user is the owner of an organization.
        
        Args:
            organization: Organization instance
            
        Returns:
            Boolean
        """
        return self.has_org_role(organization, 'owner', check_inheritance=False)
    
    def is_org_admin(self, organization):
        """
        Check if user is an admin of an organization.
        
        Args:
            organization: Organization instance
            
        Returns:
            Boolean
        """
        return self.has_org_role(organization, 'admin', check_inheritance=True)

    # =============================================
    # RBAC Methods (Global)
    # =============================================
    
    def has_role(self, role_code: str) -> bool:
        """Vérifie si l'utilisateur a un rôle spécifique"""
        return self.roles.filter(code=role_code).exists()

    def has_any_role(self, role_codes: list) -> bool:
        """Vérifie si l'utilisateur a au moins un des rôles"""
        return self.roles.filter(code__in=role_codes).exists()

    def has_all_roles(self, role_codes: list) -> bool:
        """Vérifie si l'utilisateur a tous les rôles"""
        return self.roles.filter(code__in=role_codes).count() == len(role_codes)

    def _get_effective_permission_codes(self) -> set:
        """Retourne l'ensemble des codes de permissions effectifs (rôles + directes + hiérarchie)."""
        from .base import get_permission_model
        Permission = get_permission_model()
        from django.db.models import Q

        # Permissions via rôles + permissions directes
        user_perms = Permission.objects.filter(
            Q(roles__users=self) | Q(users_direct=self)
        ).distinct()

        codes = set(user_perms.values_list('code', flat=True))

        # Ajouter les enfants des permissions parentes (hiérarchie)
        parent_perms = user_perms.filter(children__isnull=False).distinct()
        for perm in parent_perms:
            for child in perm.get_all_children(include_self=False):
                codes.add(child.code)

        return codes

    def has_permission(self, permission_code: str) -> bool:
        """Vérifie si l'utilisateur a une permission (via rôles, directe, ou hiérarchie)."""
        from .base import get_permission_model
        Permission = get_permission_model()
        from django.db.models import Q

        # Vérification directe (rôles + permissions directes)
        if Permission.objects.filter(
            Q(roles__users=self) | Q(users_direct=self),
            code=permission_code
        ).exists():
            return True

        # Vérification hiérarchique : un ancêtre de cette permission est-il attribué ?
        try:
            perm = Permission.objects.get(code=permission_code)
            ancestors = perm.get_ancestors()
            if ancestors:
                ancestor_codes = [a.code for a in ancestors]
                return Permission.objects.filter(
                    Q(roles__users=self) | Q(users_direct=self),
                    code__in=ancestor_codes
                ).exists()
        except Permission.DoesNotExist:
            pass

        return False

    def has_any_permission(self, permission_codes: list) -> bool:
        """Vérifie si l'utilisateur a au moins une des permissions."""
        return any(self.has_permission(code) for code in permission_codes)

    def has_all_permissions(self, permission_codes: list) -> bool:
        """Vérifie si l'utilisateur a toutes les permissions."""
        return all(self.has_permission(code) for code in permission_codes)

    def get_all_permissions(self) -> list:
        """Retourne la liste de toutes les permissions effectives de l'utilisateur."""
        return list(self._get_effective_permission_codes())

    def get_all_roles(self) -> list:
        """Retourne la liste de tous les rôles de l'utilisateur"""
        return list(self.roles.values_list('code', flat=True))

    def assign_role(self, role_code: str) -> bool:
        """Attribue un rôle à l'utilisateur"""
        from .base import get_role_model
        Role = get_role_model()
        try:
            role = Role.objects.get(code=role_code)
            self.roles.add(role)
            return True
        except Role.DoesNotExist:
            return False

    def remove_role(self, role_code: str) -> bool:
        """Retire un rôle à l'utilisateur"""
        from .base import get_role_model
        Role = get_role_model()
        try:
            role = Role.objects.get(code=role_code)
            self.roles.remove(role)
            return True
        except Role.DoesNotExist:
            return False

    def assign_default_role(self):
        """Attribue le rôle par défaut à l'utilisateur"""
        from .base import get_role_model
        Role = get_role_model()
        default_role = Role.get_default_role()
        if default_role:
            self.roles.add(default_role)


# =============================================================================
# CONCRETE MODELS - Default implementations (can be swapped)
# =============================================================================

class Permission(AbstractPermission):
    """
    Default Permission model. Can be replaced by setting TENXYTE_PERMISSION_MODEL.
    """
    class Meta(AbstractPermission.Meta):
        db_table = 'permissions'
        swappable = 'TENXYTE_PERMISSION_MODEL'


class Role(AbstractRole):
    """
    Default Role model. Can be replaced by setting TENXYTE_ROLE_MODEL.
    """
    class Meta(AbstractRole.Meta):
        db_table = 'roles'
        swappable = 'TENXYTE_ROLE_MODEL'


class User(AbstractUser):
    """
    Default User model. Can be replaced by setting TENXYTE_USER_MODEL.

    Note: You should also set AUTH_USER_MODEL in Django settings if you're
    extending this model.
    """
    class Meta(AbstractUser.Meta):
        db_table = 'users'
        swappable = 'TENXYTE_USER_MODEL'
