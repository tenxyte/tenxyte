"""
Tenxyte Models - Social Login connections.

Contains:
- SocialConnection: Links a user to a social OAuth provider account
"""
from django.db import models
from django.conf import settings

from .base import AutoFieldClass


class SocialConnection(models.Model):
    """
    Lie un utilisateur à un compte OAuth d'un provider social.

    Un utilisateur peut avoir plusieurs connexions sociales (Google, GitHub, etc.)
    mais une seule par provider.
    """
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('github', 'GitHub'),
        ('microsoft', 'Microsoft'),
        ('facebook', 'Facebook'),
        ('apple', 'Apple'),
    ]

    id = AutoFieldClass(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, 'AUTH_USER_MODEL') else 'tenxyte.User',
        on_delete=models.CASCADE,
        related_name='social_connections'
    )
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, db_index=True)
    provider_user_id = models.CharField(max_length=191, db_index=True)
    email = models.CharField(max_length=191, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_connections'
        unique_together = [('provider', 'provider_user_id')]

    def __str__(self):
        return f"{self.user} — {self.provider}:{self.provider_user_id}"

    @classmethod
    def get_or_create_for_user(
        cls,
        user,
        provider: str,
        provider_user_id: str,
        email: str = '',
        first_name: str = '',
        last_name: str = '',
        avatar_url: str = '',
        access_token: str = '',
        refresh_token: str = '',
    ):
        """
        Crée ou met à jour une connexion sociale pour un utilisateur.

        Returns:
            (SocialConnection instance, created: bool)
        """
        connection, created = cls.objects.update_or_create(
            provider=provider,
            provider_user_id=provider_user_id,
            defaults={
                'user': user,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'avatar_url': avatar_url,
                'access_token': access_token,
                'refresh_token': refresh_token,
            }
        )
        return connection, created
