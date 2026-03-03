"""
Tenxyte Models - Magic Link tokens.

Contains:
- MagicLinkToken: Single-use tokens for passwordless authentication
"""
import hashlib
import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .base import AutoFieldClass


class MagicLinkToken(models.Model):
    """
    Token à usage unique pour l'authentification sans mot de passe (Magic Link).

    Flow:
    1. User requests a magic link → token generated, email sent
    2. User clicks the link → token verified, JWT returned
    3. Token is marked as used (single-use)
    """
    id = AutoFieldClass(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='magic_link_tokens'
    )
    application = models.ForeignKey(
        getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.Application'),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='magic_link_tokens'
    )
    token = models.CharField(max_length=191, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'magic_link_tokens'

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def generate(cls, user, application=None, ip_address: str = None, user_agent: str = None, expiry_minutes: int = 15):
        """
        Génère un nouveau magic link token.

        Returns:
            (MagicLinkToken instance, raw_token string)
        """
        raw_token = secrets.token_urlsafe(48)
        
        # Truncate user_agent if it's too long
        if user_agent and len(user_agent) > 255:
            user_agent = user_agent[:255]
            
        instance = cls.objects.create(
            user=user,
            application=application,
            token=cls._hash_token(raw_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
        )
        return instance, raw_token

    @classmethod
    def get_valid(cls, raw_token: str, ip_address: str = None, user_agent: str = None):
        """
        Récupère un token valide (non utilisé, non expiré) depuis le token brut.
        F-12 Security Check: Valide l'IP et le User-Agent si configuré dans TENXYTE_MAGIC_LINK_REQUIRE_SAME_CLIENT.

        Returns:
            MagicLinkToken instance or None
        """
        hashed = cls._hash_token(raw_token)
        try:
            token = cls.objects.select_related('user', 'application').get(token=hashed)
        except cls.DoesNotExist:
            return None

        if token.is_used or timezone.now() >= token.expires_at:
            return None
            
        from ..conf import auth_settings
        # F-12 Mitigation: Prevent stolen link reuse by attackers
        if getattr(auth_settings, 'MAGIC_LINK_REQUIRE_SAME_CLIENT', True):
            if token.ip_address and ip_address and token.ip_address != ip_address:
                import logging
                logging.getLogger('tenxyte.security').warning(
                    f"[Security F-12] Magic link IP mismatch. Expected {token.ip_address}, got {ip_address}")
                return None
                
            if token.user_agent and user_agent:
                truncated_ua = user_agent[:255]
                if token.user_agent != truncated_ua:
                    import logging
                    logging.getLogger('tenxyte.security').warning(
                        f"[Security F-12] Magic link User-Agent mismatch.")
                    return None

        return token

    def consume(self):
        """Marque le token comme utilisé (single-use)."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at
