"""
Django WebAuthn Storage for Tenxyte Core.

Implements the WebAuthnCredentialRepository and WebAuthnChallengeRepository
protocols using Django's ORM.
"""

from typing import Optional, List
from datetime import datetime, timedelta

from tenxyte.core.webauthn_service import WebAuthnCredential, WebAuthnChallenge


class DjangoWebAuthnCredential:
    """Django model wrapper for WebAuthn credential."""
    
    def __init__(self, django_credential):
        self._credential = django_credential
    
    @property
    def id(self) -> str:
        return str(self._credential.id)
    
    @property
    def user_id(self) -> str:
        return str(self._credential.user_id)
    
    @property
    def credential_id(self) -> str:
        return self._credential.credential_id
    
    @property
    def public_key(self) -> bytes:
        return self._credential.public_key
    
    @property
    def sign_count(self) -> int:
        return getattr(self._credential, 'sign_count', 0)
    
    @property
    def is_active(self) -> bool:
        return getattr(self._credential, 'is_active', True)
    
    @property
    def device_name(self) -> str:
        return getattr(self._credential, 'device_name', 'Passkey')
    
    @property
    def created_at(self):
        return getattr(self._credential, 'created_at', None)
    
    @property
    def last_used_at(self):
        return getattr(self._credential, 'last_used_at', None)
    
    @property
    def transports(self):
        return getattr(self._credential, 'transports', [])


class DjangoWebAuthnStorage:
    """
    WebAuthn storage implementation for Django.
    
    Manages WebAuthn credentials and challenges using Django ORM.
    
    Example:
        from tenxyte.adapters.django.webauthn_storage import DjangoWebAuthnStorage
        
        storage = DjangoWebAuthnStorage()
        credential = storage.get_credential(credential_id)
        storage.store_credential(user_id, credential_data)
    """
    
    def __init__(self):
        """Initialize WebAuthn storage."""
        pass
    
    def get_credential(self, credential_id: str) -> Optional[dict]:
        """
        Get a WebAuthn credential by its ID.
        
        Args:
            credential_id: WebAuthn credential ID
            
        Returns:
            Credential data dict or None
        """
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            cred = WebAuthnCredentialModel.objects.get(
                credential_id=credential_id,
                is_active=True
            )
            return {
                'id': str(cred.id),
                'user_id': str(cred.user_id),
                'credential_id': cred.credential_id,
                'public_key': cred.public_key,
                'sign_count': getattr(cred, 'sign_count', 0),
            }
        except Exception:
            return None
    
    def get_credentials_for_user(self, user_id: str) -> List[dict]:
        """
        Get all WebAuthn credentials for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of credential data dicts
        """
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            creds = WebAuthnCredentialModel.objects.filter(
                user_id=user_id,
                is_active=True
            )
            return [
                {
                    'id': str(c.id),
                    'user_id': str(c.user_id),
                    'credential_id': c.credential_id,
                    'public_key': c.public_key,
                    'sign_count': getattr(c, 'sign_count', 0),
                }
                for c in creds
            ]
        except Exception:
            return []
    
    def store_credential(self, user_id: str, credential_data: dict) -> bool:
        """
        Store a new WebAuthn credential.
        
        Args:
            user_id: User ID
            credential_data: Credential data including credential_id, public_key
            
        Returns:
            True if stored successfully
        """
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            WebAuthnCredentialModel.objects.create(
                user_id=user_id,
                credential_id=credential_data['credential_id'],
                public_key=credential_data['public_key'],
                sign_count=credential_data.get('sign_count', 0),
            )
            return True
        except Exception:
            return False
    
    def update_sign_count(self, credential_id: str, new_count: int) -> bool:
        """
        Update the signature counter for a credential.
        
        Args:
            credential_id: Credential ID
            new_count: New signature count
            
        Returns:
            True if updated successfully
        """
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            cred = WebAuthnCredentialModel.objects.get(credential_id=credential_id)
            cred.sign_count = new_count
            cred.save(update_fields=['sign_count'])
            return True
        except Exception:
            return False
    
    def delete_credential(self, credential_id: str) -> bool:
        """
        Delete (deactivate) a WebAuthn credential.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            True if deleted successfully
        """
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            cred = WebAuthnCredentialModel.objects.get(credential_id=credential_id)
            cred.is_active = False
            cred.save(update_fields=['is_active'])
            return True
        except Exception:
            return False
    
    def get_challenge(self, challenge_id: str) -> Optional[dict]:
        """
        Get a WebAuthn challenge by ID.
        
        Args:
            challenge_id: Challenge ID
            
        Returns:
            Challenge data dict or None
        """
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            challenge = WebAuthnChallengeModel.objects.get(
                id=challenge_id,
                expires_at__gt=datetime.utcnow()
            )
            return {
                'id': str(challenge.id),
                'challenge': challenge.challenge,
                'user_id': str(challenge.user_id) if challenge.user_id else None,
                'purpose': getattr(challenge, 'purpose', 'authentication'),
                'expires_at': challenge.expires_at,
            }
        except Exception:
            return None
    
    def store_challenge(self, challenge_data: dict) -> str:
        """
        Store a new WebAuthn challenge.
        
        Args:
            challenge_data: Challenge data including challenge bytes
            
        Returns:
            Challenge ID
        """
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            expires_at = challenge_data.get('expires_at')
            if isinstance(expires_at, int):
                expires_at = datetime.utcnow() + timedelta(seconds=expires_at)
            
            challenge = WebAuthnChallengeModel.objects.create(
                challenge=challenge_data['challenge'],
                user_id=challenge_data.get('user_id'),
                purpose=challenge_data.get('purpose', 'authentication'),
                expires_at=expires_at or (datetime.utcnow() + timedelta(minutes=5)),
            )
            return str(challenge.id)
        except Exception:
            return ""
    
    def delete_challenge(self, challenge_id: str) -> bool:
        """
        Delete a WebAuthn challenge.
        
        Args:
            challenge_id: Challenge ID
            
        Returns:
            True if deleted successfully
        """
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            WebAuthnChallengeModel.objects.filter(id=challenge_id).delete()
            return True
        except Exception:
            return False
    
    def cleanup_expired_challenges(self) -> int:
        """
        Delete all expired challenges.
        
        Returns:
            Number of challenges deleted
        """
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            count, _ = WebAuthnChallengeModel.objects.filter(
                expires_at__lt=datetime.utcnow()
            ).delete()
            return count
        except Exception:
            return 0
    
    # =========================================================================
    # Core WebAuthn Protocol Methods
    # =========================================================================
    
    def get_by_credential_id(self, credential_id: str) -> Optional[WebAuthnCredential]:
        """Get credential by its ID - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            cred = WebAuthnCredentialModel.objects.get(
                credential_id=credential_id,
                is_active=True
            )
            return WebAuthnCredential(
                id=str(cred.id),
                credential_id=cred.credential_id,
                public_key=cred.public_key.decode() if isinstance(cred.public_key, bytes) else cred.public_key,
                user_id=str(cred.user_id),
                sign_count=getattr(cred, 'sign_count', 0),
                device_name=getattr(cred, 'device_name', 'Passkey'),
                aaguid=getattr(cred, 'aaguid', ''),
                transports=getattr(cred, 'transports', [])
            )
        except Exception:
            return None
    
    def list_by_user(self, user_id: str) -> List[WebAuthnCredential]:
        """List all credentials for a user - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            creds = WebAuthnCredentialModel.objects.filter(
                user_id=user_id,
                is_active=True
            )
            return [
                WebAuthnCredential(
                    id=str(c.id),
                    credential_id=c.credential_id,
                    public_key=c.public_key.decode() if isinstance(c.public_key, bytes) else c.public_key,
                    user_id=str(c.user_id),
                    sign_count=getattr(c, 'sign_count', 0),
                    device_name=getattr(c, 'device_name', 'Passkey'),
                    aaguid=getattr(c, 'aaguid', ''),
                    transports=getattr(c, 'transports', [])
                )
                for c in creds
            ]
        except Exception:
            return []
    
    def create(self, *args, **kwargs):
        """
        Create credential or challenge - Core WebAuthnService compatibility.
        
        Args:
            If first arg is WebAuthnCredential: create credential
            Otherwise: create challenge with (challenge, operation, user_id, expiry_seconds)
        """
        from tenxyte.core.webauthn_service import WebAuthnCredential, WebAuthnChallenge
        
        # Check if first argument is a WebAuthnCredential
        if args and isinstance(args[0], WebAuthnCredential):
            return self._create_credential(args[0])
        
        # Otherwise, treat as challenge creation
        challenge = kwargs.get('challenge') or (args[0] if args else None)
        operation = kwargs.get('operation') or (args[1] if len(args) > 1 else 'authenticate')
        user_id = kwargs.get('user_id') or (args[2] if len(args) > 2 else None)
        expiry_seconds = kwargs.get('expiry_seconds') or (args[3] if len(args) > 3 else 300)
        
        return self._create_challenge(challenge, operation, user_id, expiry_seconds)
    
    def _create_credential(self, credential: WebAuthnCredential) -> WebAuthnCredential:
        """Create a new credential - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            django_cred = WebAuthnCredentialModel.objects.create(
                user_id=credential.user_id,
                credential_id=credential.credential_id,
                public_key=credential.public_key.encode() if isinstance(credential.public_key, str) else credential.public_key,
                sign_count=credential.sign_count,
                device_name=credential.device_name,
                aaguid=getattr(credential, 'aaguid', ''),
                transports=getattr(credential, 'transports', [])
            )
            # Return updated credential with generated ID
            return WebAuthnCredential(
                id=str(django_cred.id),
                credential_id=django_cred.credential_id,
                public_key=credential.public_key,
                user_id=credential.user_id,
                sign_count=credential.sign_count,
                device_name=credential.device_name,
                aaguid=getattr(credential, 'aaguid', ''),
                transports=getattr(credential, 'transports', [])
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create credential: {e}")
    
    def _create_challenge(
        self,
        challenge: str,
        operation: str,
        user_id: Optional[str] = None,
        expiry_seconds: int = 300
    ) -> WebAuthnChallenge:
        """Create a new challenge - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            expires_at = datetime.utcnow() + timedelta(seconds=expiry_seconds)
            
            django_challenge = WebAuthnChallengeModel.objects.create(
                challenge=challenge,
                user_id=user_id,
                operation=operation,
                expires_at=expires_at,
            )
            
            return WebAuthnChallenge(
                id=str(django_challenge.id),
                challenge=django_challenge.challenge,
                user_id=str(django_challenge.user_id) if django_challenge.user_id else None,
                operation=django_challenge.operation,
                expires_at=django_challenge.expires_at,
                consumed=False
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create challenge: {e}")
    
    def delete(self, credential_id: str, user_id: str) -> bool:
        """Delete a credential (must belong to user) - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnCredential as WebAuthnCredentialModel
            
            cred = WebAuthnCredentialModel.objects.get(
                id=credential_id,
                user_id=user_id
            )
            cred.is_active = False
            cred.save(update_fields=['is_active'])
            return True
        except Exception:
            return False
    
    def get_by_id(self, challenge_id: str) -> Optional[WebAuthnChallenge]:
        """Get challenge by ID - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            challenge = WebAuthnChallengeModel.objects.get(
                id=challenge_id,
                expires_at__gt=datetime.utcnow()
            )
            
            return WebAuthnChallenge(
                id=str(challenge.id),
                challenge=challenge.challenge,
                user_id=str(challenge.user_id) if challenge.user_id else None,
                operation=challenge.operation,
                expires_at=challenge.expires_at,
                consumed=challenge.is_used
            )
        except Exception:
            return None
    
    def consume(self, challenge_id: str) -> bool:
        """Mark challenge as consumed - Core WebAuthnService compatibility."""
        try:
            from tenxyte.models import WebAuthnChallenge as WebAuthnChallengeModel
            
            challenge = WebAuthnChallengeModel.objects.get(id=challenge_id)
            challenge.is_used = True
            challenge.save(update_fields=['is_used'])
            return True
        except Exception:
            return False
