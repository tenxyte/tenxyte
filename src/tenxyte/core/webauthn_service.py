"""
WebAuthn / Passkeys Service for Tenxyte Core (FIDO2).

Framework-agnostic WebAuthn implementation for passwordless authentication.
Requires: pip install py_webauthn

Supports:
- Registration: begin (challenge) + complete (verify + store credential)
- Authentication: begin (challenge) + complete (verify + return user data)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from tenxyte.core.settings import Settings


logger = logging.getLogger(__name__)


def _get_webauthn():
    """Lazy import of py_webauthn to avoid hard dependency."""
    try:
        import webauthn
        return webauthn
    except ImportError:
        raise ImportError(
            "py_webauthn is required for WebAuthn/Passkeys support. "
            "Install it with: pip install py_webauthn"
        )


@dataclass
class WebAuthnCredential:
    """WebAuthn credential data structure."""
    id: str
    credential_id: str
    public_key: str
    user_id: str
    sign_count: int = 0
    device_name: str = "Passkey"
    aaguid: str = ""
    transports: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class WebAuthnChallenge:
    """WebAuthn challenge data structure."""
    id: str
    challenge: str
    operation: str  # 'register' or 'authenticate'
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    consumed: bool = False
    
    def is_valid(self) -> bool:
        """Check if challenge is valid (not expired, not consumed)."""
        if self.consumed:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class RegistrationResult:
    """Result of WebAuthn registration."""
    success: bool
    credential: Optional[WebAuthnCredential] = None
    error: str = ""


@dataclass
class AuthenticationResult:
    """Result of WebAuthn authentication."""
    success: bool
    user_id: Optional[str] = None
    credential: Optional[WebAuthnCredential] = None
    error: str = ""


@runtime_checkable
class WebAuthnCredentialRepository(Protocol):
    """Protocol for WebAuthn credential storage."""
    
    def get_by_credential_id(self, credential_id: str) -> Optional[WebAuthnCredential]:
        """Get credential by its ID."""
        ...
    
    def list_by_user(self, user_id: str) -> List[WebAuthnCredential]:
        """List all credentials for a user."""
        ...
    
    def create(self, credential: WebAuthnCredential) -> WebAuthnCredential:
        """Create a new credential."""
        ...
    
    def update_sign_count(self, credential_id: str, new_count: int) -> bool:
        """Update sign count for a credential."""
        ...
    
    def delete(self, credential_id: str, user_id: str) -> bool:
        """Delete a credential (must belong to user)."""
        ...


@runtime_checkable
class WebAuthnChallengeRepository(Protocol):
    """Protocol for WebAuthn challenge storage."""
    
    def create(
        self,
        challenge: str,
        operation: str,
        user_id: Optional[str] = None,
        expiry_seconds: int = 300
    ) -> WebAuthnChallenge:
        """Create a new challenge."""
        ...
    
    def get_by_id(self, challenge_id: str) -> Optional[WebAuthnChallenge]:
        """Get challenge by ID."""
        ...
    
    def consume(self, challenge_id: str) -> bool:
        """Mark challenge as consumed."""
        ...


class WebAuthnService:
    """
    Framework-agnostic WebAuthn/Passkeys service.
    
    Handles FIDO2 registration and authentication flows without
    dependencies on any specific framework.
    
    Example:
        from tenxyte.core import Settings, WebAuthnService
        from tenxyte.adapters.django import DjangoSettingsProvider
        
        settings = Settings(provider=DjangoSettingsProvider())
        webauthn = WebAuthnService(
            settings=settings,
            credential_repo=DjangoWebAuthnCredentialRepository(),
            challenge_repo=DjangoWebAuthnChallengeRepository()
        )
        
        # Begin registration
        success, options, error = webauthn.begin_registration(
            user_id="user123",
            email="user@example.com",
            display_name="John Doe"
        )
    """
    
    def __init__(
        self,
        settings: Settings,
        credential_repo: WebAuthnCredentialRepository,
        challenge_repo: WebAuthnChallengeRepository
    ):
        """
        Initialize WebAuthn service.
        
        Args:
            settings: Tenxyte settings
            credential_repo: Repository for credential storage
            challenge_repo: Repository for challenge storage
        """
        self.settings = settings
        self.credential_repo = credential_repo
        self.challenge_repo = challenge_repo
        
        # RP configuration
        self.rp_id = getattr(settings, 'webauthn_rp_id', 'localhost')
        self.rp_name = getattr(settings, 'webauthn_rp_name', 'Tenxyte')
        self.enabled = getattr(settings, 'webauthn_enabled', True)
    
    def _get_origin(self) -> str:
        """Get origin URL for WebAuthn."""
        if self.rp_id == "localhost":
            return "http://localhost"
        return f"https://{self.rp_id}"
    
    # =========================================================================
    # Registration
    # =========================================================================
    
    def begin_registration(
        self,
        user_id: str,
        email: str,
        display_name: str = ""
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Generate WebAuthn registration options for user.
        
        Args:
            user_id: User identifier
            email: User email (used as username)
            display_name: Display name for authenticator
            
        Returns:
            Tuple of (success, options_dict, error)
        """
        if not self.enabled:
            return False, None, "WebAuthn is not enabled"
        
        webauthn = _get_webauthn()
        
        # Get existing credentials to exclude
        existing = self.credential_repo.list_by_user(user_id)
        existing_ids = [c.credential_id for c in existing]
        
        # Generate challenge
        import secrets
        raw_challenge = secrets.token_urlsafe(32)
        
        challenge = self.challenge_repo.create(
            challenge=raw_challenge,
            operation='register',
            user_id=user_id,
            expiry_seconds=300
        )
        
        try:
            options = webauthn.generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=user_id.encode(),
                user_name=email,
                user_display_name=display_name or email,
                challenge=raw_challenge.encode(),
                exclude_credentials=[
                    webauthn.PublicKeyCredentialDescriptor(id=cid.encode())
                    for cid in existing_ids
                ],
            )
            
            return (
                True,
                {
                    "challenge_id": challenge.id,
                    "options": webauthn.options_to_json(options),
                },
                "",
            )
        except Exception as e:
            logger.error(f"WebAuthn begin_registration error: {e}", exc_info=True)
            return False, None, "An unexpected error occurred during WebAuthn registration."
    
    def complete_registration(
        self,
        user_id: str,
        credential_data: Dict[str, Any],
        challenge_id: str,
        device_name: str = ""
    ) -> RegistrationResult:
        """
        Verify and register a new WebAuthn credential.
        
        Args:
            user_id: User identifier
            credential_data: Credential data from client
            challenge_id: Challenge ID from begin_registration
            device_name: Name for this device
            
        Returns:
            RegistrationResult with credential or error
        """
        if not self.enabled:
            return RegistrationResult(success=False, error="WebAuthn is not enabled")
        
        # Get and validate challenge
        challenge = self.challenge_repo.get_by_id(challenge_id)
        if not challenge:
            return RegistrationResult(success=False, error="Invalid or expired challenge")
        
        if not challenge.is_valid():
            return RegistrationResult(success=False, error="Challenge has expired or already been used")
        
        if challenge.user_id != user_id:
            return RegistrationResult(success=False, error="Challenge does not match user")
        
        webauthn = _get_webauthn()
        
        try:
            verification = webauthn.verify_registration_response(
                credential=credential_data,
                expected_challenge=challenge.challenge.encode(),
                expected_rp_id=self.rp_id,
                expected_origin=self._get_origin(),
            )
        except Exception as e:
            logger.warning(f"WebAuthn registration verification failed: {e}")
            return RegistrationResult(success=False, error=f"Registration verification failed: {e}")
        
        # Mark challenge as consumed
        self.challenge_repo.consume(challenge_id)
        
        # Store credential
        credential = WebAuthnCredential(
            id="",  # Will be set by repository
            credential_id=(
                verification.credential_id.decode()
                if isinstance(verification.credential_id, bytes)
                else str(verification.credential_id)
            ),
            public_key=(
                verification.credential_public_key.decode()
                if isinstance(verification.credential_public_key, bytes)
                else str(verification.credential_public_key)
            ),
            user_id=user_id,
            sign_count=verification.sign_count,
            device_name=device_name or "Passkey",
            aaguid=str(verification.aaguid) if hasattr(verification, "aaguid") else "",
        )
        
        stored = self.credential_repo.create(credential)
        
        return RegistrationResult(success=True, credential=stored)
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def begin_authentication(
        self,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Generate WebAuthn authentication options.
        
        Args:
            user_id: If provided, lists credentials for this user.
                     If None, allows any credential (usernameless/discoverable).
            
        Returns:
            Tuple of (success, options_dict, error)
        """
        if not self.enabled:
            return False, None, "WebAuthn is not enabled"
        
        webauthn = _get_webauthn()
        
        # Generate challenge
        import secrets
        raw_challenge = secrets.token_urlsafe(32)
        
        challenge = self.challenge_repo.create(
            challenge=raw_challenge,
            operation='authenticate',
            user_id=user_id,
            expiry_seconds=300
        )
        
        # Get allowed credentials
        allow_credentials = []
        if user_id:
            credentials = self.credential_repo.list_by_user(user_id)
            allow_credentials = [
                webauthn.PublicKeyCredentialDescriptor(id=c.credential_id.encode())
                for c in credentials
            ]
        
        try:
            options = webauthn.generate_authentication_options(
                rp_id=self.rp_id,
                challenge=raw_challenge.encode(),
                allow_credentials=allow_credentials,
            )
            
            return (
                True,
                {
                    "challenge_id": challenge.id,
                    "options": webauthn.options_to_json(options),
                },
                "",
            )
        except Exception as e:
            logger.error(f"WebAuthn begin_authentication error: {e}", exc_info=True)
            return False, None, "An unexpected error occurred during WebAuthn authentication."
    
    def complete_authentication(
        self,
        credential_data: Dict[str, Any],
        challenge_id: str
    ) -> AuthenticationResult:
        """
        Verify WebAuthn assertion and return user data.
        
        Args:
            credential_data: Credential assertion from client
            challenge_id: Challenge ID from begin_authentication
            
        Returns:
            AuthenticationResult with user_id or error
        """
        if not self.enabled:
            return AuthenticationResult(success=False, error="WebAuthn is not enabled")
        
        # Get and validate challenge
        challenge = self.challenge_repo.get_by_id(challenge_id)
        if not challenge:
            return AuthenticationResult(success=False, error="Invalid or expired challenge")
        
        if not challenge.is_valid():
            return AuthenticationResult(success=False, error="Challenge has expired or already been used")
        
        # Find credential by ID
        raw_credential_id = credential_data.get("id", "")
        stored_credential = self.credential_repo.get_by_credential_id(raw_credential_id)
        
        if not stored_credential:
            return AuthenticationResult(success=False, error="Unknown credential")
        
        webauthn = _get_webauthn()
        
        try:
            verification = webauthn.verify_authentication_response(
                credential=credential_data,
                expected_challenge=challenge.challenge.encode(),
                expected_rp_id=self.rp_id,
                expected_origin=self._get_origin(),
                credential_public_key=(
                    stored_credential.public_key.encode()
                    if isinstance(stored_credential.public_key, str)
                    else stored_credential.public_key
                ),
                credential_current_sign_count=stored_credential.sign_count,
            )
        except Exception as e:
            logger.warning(f"WebAuthn authentication verification failed: {e}")
            return AuthenticationResult(success=False, error=f"Authentication verification failed: {e}")
        
        # Mark challenge as consumed and update sign count
        self.challenge_repo.consume(challenge_id)
        self.credential_repo.update_sign_count(
            stored_credential.id,
            verification.new_sign_count
        )
        
        return AuthenticationResult(
            success=True,
            user_id=stored_credential.user_id,
            credential=stored_credential
        )
    
    # =========================================================================
    # Credential Management
    # =========================================================================
    
    def list_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        """List passkeys for a user."""
        credentials = self.credential_repo.list_by_user(user_id)
        return [
            {
                "id": c.id,
                "device_name": c.device_name,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
                "transports": c.transports,
            }
            for c in credentials
        ]
    
    def delete_credential(self, user_id: str, credential_id: str) -> Tuple[bool, str]:
        """Delete a user's passkey."""
        success = self.credential_repo.delete(credential_id, user_id)
        if success:
            return True, ""
        return False, "Credential not found"
