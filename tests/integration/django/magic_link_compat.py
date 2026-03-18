"""
Compatibility wrapper for MagicLinkService in Django tests.

Provides Django ORM implementations of the required protocols and a
wrapper for MagicLinkService that can be instantiated without arguments.
"""

import hashlib
from typing import Any, Dict, Optional
from datetime import timedelta
from django.utils import timezone

from tenxyte.core.magic_link_service import (
    MagicLinkService as CoreMagicLinkService,
    MagicLinkRepository,
    UserLookup,
    MagicLinkToken as CoreMagicLinkToken,
)
from tenxyte.core.settings import Settings
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.models import MagicLinkToken as DjangoMagicLinkToken, User
from tenxyte.services.email_service import EmailService


class DjangoMagicLinkRepository(MagicLinkRepository):
    """Django ORM implementation of MagicLinkRepository."""

    def create(
        self,
        token_hash: str,
        user_id: str,
        email: str,
        application_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expiry_minutes: int = 15,
    ) -> CoreMagicLinkToken:
        """Create a new magic link token."""
        from tenxyte.models import Application
        
        user = User.objects.get(id=user_id)
        app = Application.objects.get(id=application_id) if application_id else None
        
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        django_token = DjangoMagicLinkToken.objects.create(
            token=token_hash,
            user=user,
            application=app,
            ip_address=ip_address or "",
            user_agent=(user_agent or "")[:255],
            expires_at=expires_at,
        )
        
        return CoreMagicLinkToken(
            id=str(django_token.id),
            token="",  # Raw token not stored
            user_id=str(user.id),
            email=user.email,
            application_id=str(app.id) if app else None,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=django_token.created_at,
            expires_at=django_token.expires_at,
            used_at=django_token.used_at,
            is_used=django_token.is_used,
        )

    def get_by_token(self, token: str) -> Optional[CoreMagicLinkToken]:
        """Get token by raw token value (validates hash internally)."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            django_token = DjangoMagicLinkToken.objects.get(
                token=token_hash,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            return CoreMagicLinkToken(
                id=str(django_token.id),
                token=token,
                user_id=str(django_token.user.id),
                email=django_token.user.email,
                application_id=str(django_token.application.id) if django_token.application else None,
                ip_address=django_token.ip_address,
                user_agent=django_token.user_agent,
                created_at=django_token.created_at,
                expires_at=django_token.expires_at,
                used_at=django_token.used_at,
                is_used=django_token.is_used,
            )
        except DjangoMagicLinkToken.DoesNotExist:
            return None

    def invalidate_user_tokens(self, user_id: str, application_id: Optional[str] = None) -> int:
        """Mark all unused tokens for user as used."""
        query = DjangoMagicLinkToken.objects.filter(user_id=user_id, is_used=False)
        if application_id:
            query = query.filter(application_id=application_id)
        count = query.count()
        query.update(is_used=True, used_at=timezone.now())
        return count

    def consume(self, token_id: str) -> bool:
        """Mark token as used."""
        try:
            django_token = DjangoMagicLinkToken.objects.get(id=token_id)
            django_token.is_used = True
            django_token.used_at = timezone.now()
            django_token.save()
            return True
        except DjangoMagicLinkToken.DoesNotExist:
            return False


class DjangoUserLookup(UserLookup):
    """Django ORM implementation of UserLookup."""

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email (case-insensitive)."""
        try:
            user = User.objects.get(email__iexact=email)
            return {
                "id": str(user.id),
                "email": user.email,
                "is_active": user.is_active,
                "is_locked": user.is_locked,
            }
        except User.DoesNotExist:
            return None

    def is_active(self, user_id: str) -> bool:
        """Check if user account is active."""
        try:
            user = User.objects.get(id=user_id)
            return user.is_active
        except User.DoesNotExist:
            return False

    def is_locked(self, user_id: str) -> bool:
        """Check if user account is locked."""
        try:
            user = User.objects.get(id=user_id)
            return user.is_locked
        except User.DoesNotExist:
            return False


class MagicLinkService(CoreMagicLinkService):
    """
    Django-compatible wrapper for MagicLinkService.
    
    Can be instantiated without arguments for test compatibility.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        repo: Optional[MagicLinkRepository] = None,
        user_lookup: Optional[UserLookup] = None,
        email_service: Optional[EmailService] = None,
    ):
        """Initialize with optional arguments, using Django defaults if not provided."""
        if settings is None:
            settings = Settings(provider=DjangoSettingsProvider())
        if repo is None:
            repo = DjangoMagicLinkRepository()
        if user_lookup is None:
            user_lookup = DjangoUserLookup()
        if email_service is None:
            email_service = EmailService()
        
        super().__init__(
            settings=settings,
            repo=repo,
            user_lookup=user_lookup,
            email_service=email_service,
        )

    def request_magic_link(self, email: str, application=None, **kwargs):
        """Override to accept application object and convert to application_id."""
        application_id = str(application.id) if application else None
        return super().request_magic_link(email=email, application_id=application_id, **kwargs)

    def verify_magic_link(self, token: str, application=None, **kwargs):
        """Override to accept application object and convert to application_id, and return tuple."""
        application_id = str(application.id) if application else None
        result = super().verify_magic_link(token=token, application_id=application_id, **kwargs)
        
        # Convert MagicLinkResult to tuple format expected by tests
        if result.success:
            # Generate JWT tokens for successful verification
            from tenxyte.models import User
            from tests.integration.django.test_helpers import create_jwt_token
            
            user = User.objects.get(id=result.user_id)
            app = application if application else None
            
            if app:
                token_pair = create_jwt_token(user, app)
                data = {
                    'access_token': token_pair['access_token'],
                    'refresh_token': token_pair['refresh_token'],
                    'user_id': result.user_id,
                    'email': result.email,
                }
            else:
                data = {
                    'user_id': result.user_id,
                    'email': result.email,
                }
            
            return True, data, ''
        else:
            return False, None, result.error
