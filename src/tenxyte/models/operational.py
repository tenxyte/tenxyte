"""
Tenxyte Models - Operational models.

Contains:
- OTPCode: One-time password codes for verification
- RefreshToken: JWT refresh tokens
- LoginAttempt: Login attempt tracking for rate limiting
"""
import hashlib
import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .base import AutoFieldClass


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

    SECURITY: Le token est stocké sous forme de hash SHA-256 en base de données.
    La valeur brute est uniquement disponible au moment de la génération via generate().
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
    token = models.CharField(
        max_length=191,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of the raw refresh token. Never store the raw value."
    )
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refresh_tokens'

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """Hash a raw refresh token with SHA-256 for secure storage."""
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @classmethod
    def generate(cls, user, application, device_info: str = '', ip_address: str = None, validity_days: int = 30):
        """
        Génère un nouveau refresh token.

        Returns:
            Tuple (RefreshToken instance, raw_token: str)
            Le raw_token doit être retourné au client — il n'est pas conservé en DB.
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = cls._hash_token(raw_token)
        instance = cls.objects.create(
            user=user,
            application=application,
            token=token_hash,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(days=validity_days)
        )
        # Attacher le token brut à l'instance pour usage immédiat (non persistant)
        instance._raw_token = raw_token
        return instance

    @classmethod
    def get_by_raw_token(cls, raw_token: str):
        """
        Retrouve un RefreshToken depuis sa valeur brute.

        Args:
            raw_token: La valeur brute fournie par le client

        Returns:
            RefreshToken instance

        Raises:
            RefreshToken.DoesNotExist si le hash ne correspond à aucun token
        """
        token_hash = cls._hash_token(raw_token)
        return cls.objects.get(token=token_hash)

    @property
    def raw_token(self) -> str:
        """Retourne le token brut si disponible (seulement juste après generate())."""
        return getattr(self, '_raw_token', None)

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
