"""
WebAuthn Service Compatibility Layer for Django Tests.

This module provides Django-specific repositories and a wrapper for WebAuthnService
to maintain compatibility with existing tests.
"""

from typing import List, Optional
from datetime import datetime, timedelta, timezone

from tenxyte.core.webauthn_service import (
    WebAuthnService as CoreWebAuthnService,
    WebAuthnCredential as CoreCredential,
    WebAuthnChallenge as CoreChallenge,
)
from tenxyte.core.settings import Settings
from tenxyte.adapters.django import get_django_settings
from tenxyte.models.webauthn import WebAuthnCredential, WebAuthnChallenge


class DjangoWebAuthnCredentialRepository:
    """Django ORM implementation of WebAuthnCredentialRepository."""
    
    def get_by_credential_id(self, credential_id: str) -> Optional[CoreCredential]:
        """Get credential by its ID."""
        try:
            cred = WebAuthnCredential.objects.get(credential_id=credential_id)
            return CoreCredential(
                id=str(cred.id),
                credential_id=cred.credential_id,
                public_key=cred.public_key,
                user_id=str(cred.user_id),
                sign_count=cred.sign_count,
                device_name=cred.device_name or "Passkey",
                aaguid=cred.aaguid or "",
                transports=cred.transports or [],
                created_at=cred.created_at,
                last_used_at=cred.last_used_at,
                is_active=True,
            )
        except WebAuthnCredential.DoesNotExist:
            return None
    
    def list_by_user(self, user_id: str) -> List[CoreCredential]:
        """List all credentials for a user."""
        creds = WebAuthnCredential.objects.filter(user_id=user_id)
        return [
            CoreCredential(
                id=str(c.id),
                credential_id=c.credential_id,
                public_key=c.public_key,
                user_id=str(c.user_id),
                sign_count=c.sign_count,
                device_name=c.device_name or "Passkey",
                aaguid=c.aaguid or "",
                transports=c.transports or [],
                created_at=c.created_at,
                last_used_at=c.last_used_at,
                is_active=True,
            )
            for c in creds
        ]
    
    def create(self, credential: CoreCredential) -> CoreCredential:
        """Create a new credential."""
        cred = WebAuthnCredential.objects.create(
            credential_id=credential.credential_id,
            public_key=credential.public_key,
            user_id=credential.user_id,
            sign_count=credential.sign_count,
            device_name=credential.device_name,
            aaguid=credential.aaguid,
            transports=credential.transports,
        )
        credential.id = str(cred.id)
        credential.created_at = cred.created_at
        return credential
    
    def update_sign_count(self, credential_id: str, new_count: int) -> bool:
        """Update sign count for a credential."""
        try:
            cred = WebAuthnCredential.objects.get(credential_id=credential_id)
            cred.update_sign_count(new_count)
            return True
        except WebAuthnCredential.DoesNotExist:
            return False
    
    def delete(self, credential_id: str, user_id: str) -> bool:
        """Delete a credential (must belong to user)."""
        deleted, _ = WebAuthnCredential.objects.filter(
            credential_id=credential_id,
            user_id=user_id
        ).delete()
        return deleted > 0


class DjangoWebAuthnChallengeRepository:
    """Django ORM implementation of WebAuthnChallengeRepository."""
    
    def create(
        self,
        challenge: str,
        operation: str,
        user_id: Optional[str] = None,
        expiry_seconds: int = 300
    ) -> CoreChallenge:
        """Create a new challenge."""
        from tenxyte.models import User
        
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        instance, raw_challenge = WebAuthnChallenge.generate(
            operation=operation,
            user=user
        )
        
        return CoreChallenge(
            id=str(instance.id),
            challenge=raw_challenge,
            operation=instance.operation,
            user_id=str(instance.user_id) if instance.user_id else None,
            created_at=instance.created_at,
            expires_at=instance.expires_at,
            consumed=instance.is_used,
        )
    
    def get_by_id(self, challenge_id: str) -> Optional[CoreChallenge]:
        """Get challenge by ID."""
        try:
            ch = WebAuthnChallenge.objects.get(id=challenge_id)
            return CoreChallenge(
                id=str(ch.id),
                challenge=ch.challenge,
                operation=ch.operation,
                user_id=str(ch.user_id) if ch.user_id else None,
                created_at=ch.created_at,
                expires_at=ch.expires_at,
                consumed=ch.is_used,
            )
        except WebAuthnChallenge.DoesNotExist:
            return None
    
    def consume(self, challenge_id: str) -> bool:
        """Mark challenge as consumed."""
        try:
            ch = WebAuthnChallenge.objects.get(id=challenge_id)
            ch.consume()
            return True
        except WebAuthnChallenge.DoesNotExist:
            return False


class WebAuthnService:
    """
    Compatibility wrapper for WebAuthnService that works with Django models.
    
    This wrapper automatically provides the required repositories and settings
    so tests don't need to be modified.
    """
    
    def __init__(self):
        """Initialize with Django-specific repositories."""
        self.credential_repo = DjangoWebAuthnCredentialRepository()
        self.challenge_repo = DjangoWebAuthnChallengeRepository()
    
    def _get_service(self):
        """Get a fresh service instance with current settings."""
        # Force re-read of settings to pick up override_settings changes
        import tenxyte.core.settings as settings_module
        from tenxyte.adapters.django import DjangoSettingsProvider
        
        # Force reset of global singleton to pick up Django's override_settings
        settings_module._settings = None
        settings = settings_module.init(provider=DjangoSettingsProvider())
        
        return CoreWebAuthnService(
            settings=settings,
            credential_repo=self.credential_repo,
            challenge_repo=self.challenge_repo,
        )
    
    def begin_registration(self, user):
        """
        Begin WebAuthn registration for a user.
        
        Args:
            user: Django User object
            
        Returns:
            Tuple of (success, data, error)
        """
        return self._get_service().begin_registration(
            user_id=str(user.id),
            email=user.email,
            display_name=getattr(user, 'get_full_name', lambda: user.email)(),
        )
    
    def complete_registration(self, user, challenge_id, credential_data, device_name=""):
        """
        Complete WebAuthn registration.
        
        Args:
            user: Django User object
            challenge_id: Challenge ID
            credential_data: Credential data from client
            device_name: Optional device name
            
        Returns:
            Tuple of (success, credential, error)
        """
        result = self._get_service().complete_registration(
            user_id=str(user.id),
            challenge_id=challenge_id,
            credential_data=credential_data,
            device_name=device_name,
        )
        # Convert RegistrationResult to tuple for legacy API
        return (result.success, result.credential, result.error)
    
    def begin_authentication(self, user=None):
        """
        Begin WebAuthn authentication.
        
        Args:
            user: Optional Django User object for user-specific auth
            
        Returns:
            Tuple of (success, data, error)
        """
        user_id = str(user.id) if user else None
        return self._get_service().begin_authentication(user_id=user_id)
    
    def complete_authentication(self, credential_data, challenge_id, **kwargs):
        """
        Complete WebAuthn authentication.
        
        Args:
            credential_data: Credential data from client
            challenge_id: Challenge ID
            **kwargs: Additional arguments (application, ip_address, etc.) - ignored for now
            
        Returns:
            Tuple of (success, user_data, error)
        """
        # First check if user is active/unlocked before attempting authentication
        from tenxyte.models import User
        from django.utils import timezone
        
        # Get challenge to find user
        challenge = self.challenge_repo.get_by_id(challenge_id)
        if challenge and challenge.user_id:
            try:
                user = User.objects.get(id=challenge.user_id)
                
                # Check if user is active
                if not user.is_active:
                    return (False, None, "Account is disabled")
                
                # Check if user is locked
                if hasattr(user, 'is_locked') and user.is_locked:
                    if hasattr(user, 'locked_until') and user.locked_until:
                        if timezone.now() < user.locked_until:
                            return (False, None, "Account is locked")
            except User.DoesNotExist:
                pass
        
        result = self._get_service().complete_authentication(
            challenge_id=challenge_id,
            credential_data=credential_data,
        )
        # Convert AuthenticationResult to tuple for legacy API
        # For now, return user_id in data dict if successful
        if result.success and result.user_id:
            data = {'user_id': result.user_id, 'access_token': 'mock_token'}
            return (True, data, "")
        return (result.success, None, result.error)
    
    def list_credentials(self, user):
        """
        List all credentials for a user.
        
        Args:
            user: Django User object
            
        Returns:
            List of credentials
        """
        return self._get_service().list_credentials(user_id=str(user.id))
    
    def delete_credential(self, user, credential_id):
        """
        Delete a credential.
        
        Args:
            user: Django User object
            credential_id: Credential database ID or credential_id string
            
        Returns:
            Tuple of (success, error)
        """
        # If credential_id is a database ID (int), get the actual credential_id
        if isinstance(credential_id, int):
            try:
                cred = WebAuthnCredential.objects.get(id=credential_id, user_id=user.id)
                credential_id = cred.credential_id
            except WebAuthnCredential.DoesNotExist:
                return (False, "Credential not found")
        
        return self._get_service().delete_credential(
            user_id=str(user.id),
            credential_id=credential_id,
        )
    
    def _get_origin(self):
        """Get origin URL for WebAuthn - delegates to core service."""
        return self._get_service()._get_origin()
