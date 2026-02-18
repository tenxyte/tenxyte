"""
Tenxyte Models - Extensible User, Role, and Permission models.

These models can be extended by creating your own models that inherit from the
Abstract classes (AbstractUser, AbstractRole, AbstractPermission) and configuring
the settings to use your custom models.

Example:
    # In your app's models.py
    from tenxyte.models import AbstractUser

    class CustomUser(AbstractUser):
        # Add your custom fields
        company = models.CharField(max_length=100, blank=True)
        department = models.CharField(max_length=100, blank=True)

        class Meta(AbstractUser.Meta):
            db_table = 'custom_users'

    # In settings.py
    TENXYTE_USER_MODEL = 'myapp.CustomUser'
"""
import hashlib
import secrets
import bcrypt
import base64
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

# Détection du backend pour MongoDB
# On vérifie le moteur DB configuré, pas juste la disponibilité du package,
# pour éviter d'utiliser ObjectIdAutoField sur SQLite/PG/MySQL quand
# django-mongodb-backend est installé.
def _get_auto_field_class():
    try:
        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    except Exception:
        db_engine = ''
    if 'mongodb' in db_engine:
        try:
            from django_mongodb_backend.fields import ObjectIdAutoField
            return ObjectIdAutoField
        except ImportError:
            pass
    return models.BigAutoField

AutoFieldClass = _get_auto_field_class()


# =============================================================================
# HELPERS - Get swappable models
# =============================================================================

def get_user_model():
    """
    Returns the User model that is active in this project.
    Similar to django.contrib.auth.get_user_model().
    """
    from django.apps import apps
    model_path = getattr(settings, 'TENXYTE_USER_MODEL', 'tenxyte.User')
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        return User


def get_role_model():
    """
    Returns the Role model that is active in this project.
    """
    from django.apps import apps
    model_path = getattr(settings, 'TENXYTE_ROLE_MODEL', 'tenxyte.Role')
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        return Role


def get_permission_model():
    """
    Returns the Permission model that is active in this project.
    """
    from django.apps import apps
    model_path = getattr(settings, 'TENXYTE_PERMISSION_MODEL', 'tenxyte.Permission')
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        return Permission


def get_application_model():
    """
    Returns the Application model that is active in this project.
    """
    from django.apps import apps
    model_path = getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.Application')
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        return Application


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
    totp_secret = models.CharField(max_length=32, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)

    # État
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)

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
        self.password = bcrypt.hashpw(
            raw_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(
            raw_password.encode('utf-8'),
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

    @property
    def full_phone(self) -> str:
        if self.phone_country_code and self.phone_number:
            return f"+{self.phone_country_code}{self.phone_number}"
        return ""

    def __str__(self):
        return self.email or self.full_phone or str(self.id)

    # Méthodes RBAC
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
        Role = get_role_model()
        try:
            role = Role.objects.get(code=role_code)
            self.roles.add(role)
            return True
        except Role.DoesNotExist:
            return False

    def remove_role(self, role_code: str) -> bool:
        """Retire un rôle à l'utilisateur"""
        Role = get_role_model()
        try:
            role = Role.objects.get(code=role_code)
            self.roles.remove(role)
            return True
        except Role.DoesNotExist:
            return False

    def assign_default_role(self):
        """Attribue le rôle par défaut à l'utilisateur"""
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


# =============================================================================
# ABSTRACT APPLICATION MODEL
# =============================================================================

class AbstractApplication(models.Model):
    """
    Abstract Application model - Extend this to add custom fields.

    Example:
        class CustomApplication(AbstractApplication):
            owner = models.ForeignKey('myapp.User', on_delete=models.CASCADE)
            api_rate_limit = models.IntegerField(default=1000)

            class Meta(AbstractApplication.Meta):
                db_table = 'custom_applications'

        # In settings.py:
        TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
    """
    id = AutoFieldClass(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    access_key = models.CharField(max_length=64, unique=True, db_index=True)
    access_secret = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name

    @staticmethod
    def _hash_secret(raw_secret: str) -> str:
        """Hash le secret et encode en base64 pour éviter les problèmes avec MongoDB"""
        hashed = bcrypt.hashpw(raw_secret.encode('utf-8'), bcrypt.gensalt())
        return base64.b64encode(hashed).decode('utf-8')

    @staticmethod
    def _verify_hashed_secret(raw_secret: str, stored_secret: str) -> bool:
        """Vérifie le secret contre le hash stocké en base64"""
        try:
            hashed = base64.b64decode(stored_secret.encode('utf-8'))
            return bcrypt.checkpw(raw_secret.encode('utf-8'), hashed)
        except Exception:
            return False

    def verify_secret(self, raw_secret: str) -> bool:
        if not self.access_secret or not raw_secret:
            return False
        return self._verify_hashed_secret(raw_secret, self.access_secret)

    def regenerate_credentials(self):
        """
        Régénère access_key et access_secret
        Retourne le secret brut UNE SEULE FOIS
        """
        raw_secret = secrets.token_hex(32)
        hashed_secret = self._hash_secret(raw_secret)

        self.access_key = secrets.token_hex(32)
        self.access_secret = hashed_secret
        self.save()

        return {
            'access_key': self.access_key,
            'access_secret': raw_secret
        }

    @classmethod
    def create_application(cls, name: str, description: str = ''):
        """
        Crée une nouvelle application et retourne l'instance + le secret brut
        """
        raw_secret = secrets.token_hex(32)
        hashed_secret = cls._hash_secret(raw_secret)
        app = cls(
            name=name,
            description=description,
            access_key=secrets.token_hex(32),
            access_secret=hashed_secret
        )
        app.save()
        return app, raw_secret


class Application(AbstractApplication):
    """
    Default Application model. Can be replaced by setting TENXYTE_APPLICATION_MODEL.
    """
    class Meta(AbstractApplication.Meta):
        db_table = 'applications'
        swappable = 'TENXYTE_APPLICATION_MODEL'


class OTPCode(models.Model):
    """
    Codes OTP pour vérification email/téléphone.
    """
    id = AutoFieldClass(primary_key=True)

    TYPE_CHOICES = [
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
        ('login_2fa', 'Login 2FA'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='otp_codes'
    )
    code = models.CharField(max_length=64)
    otp_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)

    class Meta:
        db_table = 'otp_codes'

    @staticmethod
    def _hash_code(code: str) -> str:
        """Hash an OTP code with SHA-256."""
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def generate(cls, user, otp_type: str, validity_minutes: int = 10):
        raw_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        otp = cls.objects.create(
            user=user,
            code=cls._hash_code(raw_code),
            otp_type=otp_type,
            expires_at=timezone.now() + timedelta(minutes=validity_minutes)
        )
        return otp, raw_code

    def is_valid(self) -> bool:
        return (
            not self.is_used
            and timezone.now() < self.expires_at
            and self.attempts < self.max_attempts
        )

    def verify(self, code: str) -> bool:
        if not self.is_valid():
            return False

        self.attempts += 1
        self.save(update_fields=['attempts'])

        if self.code == self._hash_code(code):
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True
        return False


class RefreshToken(models.Model):
    """
    Refresh tokens pour JWT.
    """
    id = AutoFieldClass(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    application = models.ForeignKey(
        getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.Application'),
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    token = models.CharField(max_length=191, unique=True, db_index=True)
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refresh_tokens'

    @classmethod
    def generate(cls, user, application, device_info: str = '', ip_address: str = None, validity_days: int = 30):
        token = secrets.token_urlsafe(64)
        return cls.objects.create(
            user=user,
            application=application,
            token=token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(days=validity_days)
        )

    def is_valid(self) -> bool:
        return (
            not self.is_revoked
            and timezone.now() < self.expires_at
            and self.user.is_active
            and not self.user.is_account_locked()
        )

    def revoke(self):
        self.is_revoked = True
        self.save()


class LoginAttempt(models.Model):
    """
    Suivi des tentatives de connexion pour rate limiting.
    """
    id = AutoFieldClass(primary_key=True)
    identifier = models.CharField(max_length=191, db_index=True)
    ip_address = models.GenericIPAddressField()
    application = models.ForeignKey(
        getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.Application'),
        on_delete=models.CASCADE,
        null=True
    )
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_attempts'

    @classmethod
    def record(cls, identifier: str, ip_address: str, application=None, success: bool = False, failure_reason: str = ''):
        return cls.objects.create(
            identifier=identifier,
            ip_address=ip_address,
            application=application,
            success=success,
            failure_reason=failure_reason
        )

    @classmethod
    def get_recent_failures(cls, identifier: str, minutes: int = 15) -> int:
        since = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            identifier=identifier,
            success=False,
            created_at__gte=since
        ).count()

    @classmethod
    def is_rate_limited(cls, identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        return cls.get_recent_failures(identifier, window_minutes) >= max_attempts


# =============================================================================
# SECURITY MODELS - Blacklist, Audit, Password History
# =============================================================================

class BlacklistedToken(models.Model):
    """
    JWT Access Token Blacklist for immediate token revocation.
    Tokens are blacklisted until their natural expiration.
    """
    id = AutoFieldClass(primary_key=True)
    token_jti = models.CharField(max_length=191, unique=True, db_index=True)  # JWT ID
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='blacklisted_tokens',
        null=True,
        blank=True
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # When the token would have expired anyway
    reason = models.CharField(max_length=100, blank=True)  # logout, password_change, security, etc.

    class Meta:
        db_table = 'blacklisted_tokens'

    def __str__(self):
        return f"Blacklisted: {self.token_jti[:20]}..."

    @classmethod
    def blacklist_token(cls, token_jti: str, expires_at, user=None, reason: str = ''):
        """Add a token to the blacklist."""
        return cls.objects.get_or_create(
            token_jti=token_jti,
            defaults={
                'user': user,
                'expires_at': expires_at,
                'reason': reason
            }
        )

    @classmethod
    def is_blacklisted(cls, token_jti: str) -> bool:
        """Check if a token is blacklisted."""
        return cls.objects.filter(token_jti=token_jti).exists()

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove expired blacklisted tokens (they're no longer valid anyway)."""
        result = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return result[0]


class AuditLog(models.Model):
    """
    Audit trail for security-sensitive actions.
    """
    id = AutoFieldClass(primary_key=True)

    ACTION_CHOICES = [
        # Authentication
        ('login', 'Login'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('logout_all', 'Logout All Devices'),
        ('token_refresh', 'Token Refresh'),

        # Password
        ('password_change', 'Password Changed'),
        ('password_reset_request', 'Password Reset Requested'),
        ('password_reset_complete', 'Password Reset Completed'),

        # 2FA
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('2fa_backup_used', '2FA Backup Code Used'),

        # Account
        ('account_created', 'Account Created'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('email_verified', 'Email Verified'),
        ('phone_verified', 'Phone Verified'),

        # Roles & Permissions
        ('role_assigned', 'Role Assigned'),
        ('role_removed', 'Role Removed'),
        ('permission_changed', 'Permission Changed'),

        # Application
        ('app_created', 'Application Created'),
        ('app_credentials_regenerated', 'Application Credentials Regenerated'),

        # Account lifecycle
        ('account_deleted', 'Account Deleted'),

        # Security
        ('suspicious_activity', 'Suspicious Activity Detected'),
        ('session_limit_exceeded', 'Session Limit Exceeded'),
        ('device_limit_exceeded', 'Device Limit Exceeded'),
        ('new_device_detected', 'New Device Detected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    application = models.ForeignKey(
        getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.Application'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    details = models.JSONField(default=dict, blank=True)  # Additional context
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"

    @classmethod
    def log(cls, action: str, user=None, ip_address: str = None, user_agent: str = '',
            application=None, details: dict = None):
        """Create an audit log entry."""
        return cls.objects.create(
            user=user,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            application=application,
            details=details or {}
        )

    @classmethod
    def get_user_activity(cls, user, limit: int = 100):
        """Get recent activity for a user."""
        return cls.objects.filter(user=user)[:limit]

    @classmethod
    def get_suspicious_activity(cls, hours: int = 24):
        """Get suspicious activity in the last N hours."""
        since = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(
            action__in=['login_failed', 'suspicious_activity', 'session_limit_exceeded', 'device_limit_exceeded'],
            created_at__gte=since
        )


class PasswordHistory(models.Model):
    """
    Password history to prevent reuse of old passwords.
    """
    id = AutoFieldClass(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='password_history'
    )
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_history'
        ordering = ['-created_at']

    @classmethod
    def add_password(cls, user, password_hash: str, max_history: int = 5):
        """
        Add a password to history and cleanup old entries.

        Args:
            user: The user
            password_hash: The bcrypt hashed password
            max_history: Maximum passwords to keep in history
        """
        # Add new password
        cls.objects.create(user=user, password_hash=password_hash)

        # Cleanup old entries (keep only max_history)
        old_passwords = cls.objects.filter(user=user).order_by('-created_at')[max_history:]
        if old_passwords:
            cls.objects.filter(id__in=[p.id for p in old_passwords]).delete()

    @classmethod
    def is_password_used(cls, user, raw_password: str, check_count: int = 5) -> bool:
        """
        Check if a password was recently used.

        Args:
            user: The user
            raw_password: The raw password to check
            check_count: How many previous passwords to check

        Returns:
            True if the password was recently used
        """
        recent_passwords = cls.objects.filter(user=user).order_by('-created_at')[:check_count]

        for history in recent_passwords:
            try:
                if bcrypt.checkpw(raw_password.encode('utf-8'), history.password_hash.encode('utf-8')):
                    return True
            except Exception:
                continue

        return False
