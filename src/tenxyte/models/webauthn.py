"""
Tenxyte Models - WebAuthn / Passkeys credentials.

Contains:
- WebAuthnCredential: FIDO2 credential linked to a user
- WebAuthnChallenge: Temporary challenge for registration/authentication
"""
import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .base import AutoFieldClass


class WebAuthnCredential(models.Model):
    """
    Credential FIDO2/WebAuthn (Passkey) lié à un utilisateur.

    Stocke la clé publique et les métadonnées nécessaires à la vérification.
    Un utilisateur peut avoir plusieurs passkeys (un par appareil).
    """
    id = AutoFieldClass(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='webauthn_credentials'
    )
    credential_id = models.TextField(unique=True, db_index=True)
    public_key = models.TextField()
    sign_count = models.PositiveBigIntegerField(default=0)
    device_name = models.CharField(max_length=100, blank=True, default='')
    aaguid = models.CharField(max_length=36, blank=True, default='')
    transports = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webauthn_credentials'

    def __str__(self):
        return f"{self.user} — {self.device_name or self.credential_id[:16]}"

    def update_sign_count(self, new_count: int):
        self.sign_count = new_count
        self.last_used_at = timezone.now()
        self.save(update_fields=['sign_count', 'last_used_at'])


class WebAuthnChallenge(models.Model):
    """
    Challenge temporaire pour les opérations WebAuthn (registration/authentication).
    Expire après TENXYTE_WEBAUTHN_CHALLENGE_EXPIRY_SECONDS (défaut: 300s).
    """
    OPERATION_REGISTER = 'register'
    OPERATION_AUTHENTICATE = 'authenticate'

    OPERATION_CHOICES = [
        (OPERATION_REGISTER, 'Register'),
        (OPERATION_AUTHENTICATE, 'Authenticate'),
    ]

    id = AutoFieldClass(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='webauthn_challenges',
        null=True,
        blank=True
    )
    challenge = models.CharField(max_length=191, unique=True, db_index=True)
    operation = models.CharField(max_length=16, choices=OPERATION_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webauthn_challenges'

    @classmethod
    def generate(cls, operation: str, user=None, expiry_seconds: int = 300):
        challenge = secrets.token_urlsafe(32)
        return cls.objects.create(
            user=user,
            challenge=challenge,
            operation=operation,
            expires_at=timezone.now() + timedelta(seconds=expiry_seconds)
        ), challenge

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at

    def consume(self):
        self.is_used = True
        self.save(update_fields=['is_used'])
