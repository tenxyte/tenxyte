"""
Magic Link Service for Tenxyte Core.

Framework-agnostic passwordless authentication via email magic links.
"""

import logging
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from tenxyte.core.settings import Settings
from tenxyte.core.email_service import EmailService


logger = logging.getLogger(__name__)


@dataclass
class MagicLinkToken:
    """Magic link token data structure."""
    id: str
    token: str  # Raw token (only available at creation time)
    user_id: str
    email: str
    application_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    is_used: bool = False
    
    def is_valid(self) -> bool:
        """Check if token is valid (not used, not expired)."""
        if self.is_used:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class MagicLinkResult:
    """Result of magic link verification."""
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    error: str = ""


@runtime_checkable
class MagicLinkRepository(Protocol):
    """Protocol for magic link token storage."""
    
    def create(
        self,
        token_hash: str,
        user_id: str,
        email: str,
        application_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expiry_minutes: int = 15
    ) -> MagicLinkToken:
        """Create a new magic link token. Returns token with raw token set."""
        ...  # pragma: no cover
    
    def get_by_token(self, token: str) -> Optional[MagicLinkToken]:
        """Get token by raw token value (validates hash internally)."""
        ...  # pragma: no cover
    
    def invalidate_user_tokens(
        self,
        user_id: str,
        application_id: Optional[str] = None
    ) -> int:
        """Mark all unused tokens for user as used. Returns count."""
        ...  # pragma: no cover
    
    def consume(self, token_id: str) -> bool:
        """Mark token as used."""
        ...  # pragma: no cover


@runtime_checkable
class UserLookup(Protocol):
    """Protocol for user lookup operations."""
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email (case-insensitive). Returns None if not found."""
        ...  # pragma: no cover
    
    def is_active(self, user_id: str) -> bool:
        """Check if user account is active."""
        ...  # pragma: no cover
    
    def is_locked(self, user_id: str) -> bool:
        """Check if user account is locked."""
        ...  # pragma: no cover


class MagicLinkService:
    """
    Framework-agnostic Magic Link service for passwordless authentication.
    
    Handles magic link generation, email sending, and validation.
    Works with any storage backend through the MagicLinkRepository protocol.
    
    Example:
        from tenxyte.core import Settings, MagicLinkService
        from tenxyte.adapters.django import DjangoSettingsProvider
        
        settings = Settings(provider=DjangoSettingsProvider())
        magic = MagicLinkService(
            settings=settings,
            repo=DjangoMagicLinkRepository(),
            user_lookup=DjangoUserLookup(),
            email_service=DjangoEmailService()
        )
        
        # Request magic link
        success, error = magic.request_magic_link(
            email="user@example.com",
            application_id="app123"
        )
    """
    
    def __init__(
        self,
        settings: Settings,
        repo: MagicLinkRepository,
        user_lookup: UserLookup,
        email_service: EmailService
    ):
        """
        Initialize magic link service.
        
        Args:
            settings: Tenxyte settings
            repo: Repository for token storage
            user_lookup: Service for user lookups
            email_service: Service for sending emails
        """
        self.settings = settings
        self.repo = repo
        self.user_lookup = user_lookup
        self.email_service = email_service
        
        # Configuration
        self.enabled = getattr(settings, 'magic_link_enabled', True)
        self.expiry_minutes = getattr(settings, 'magic_link_expiry_minutes', 15)
        self.app_name = getattr(settings, 'app_name', 'Tenxyte')
    
    def _generate_token(self) -> str:
        """Generate a cryptographically secure token."""
        # 32 bytes = 64 hex chars or use URL-safe base64
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage (prevent token recovery if DB leaked)."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
    
    def request_magic_link(
        self,
        email: str,
        application_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: str = "",
        validation_url: Optional[str] = None,
        first_name: str = ""
    ) -> Tuple[bool, str]:
        """
        Generate a magic link and send via email.
        
        Args:
            email: User email address
            application_id: Optional application ID
            ip_address: Client IP for security logging
            device_info: Device info for security logging
            validation_url: Base URL for magic link (e.g., https://app.com/auth/magic)
            first_name: User's first name for email personalization
            
        Returns:
            Tuple of (success, error_message)
            Note: Returns success=True even if email not found (security)
        """
        if not self.enabled:
            return False, "Magic link authentication is not enabled"
        
        # Lookup user
        user = self.user_lookup.get_by_email(email)
        
        if not user:
            # Don't reveal if email exists (security)
            logger.info(f"Magic link requested for unknown email: {email}")
            return True, ""
        
        # Handle both dict and object user types
        if isinstance(user, dict):
            user_id = user.get('id')
            user_email = user.get('email', email)
            user_first_name = first_name or user.get('first_name', '')
        else:
            # User is an object (e.g., Django User model)
            user_id = getattr(user, 'id', None)
            user_email = getattr(user, 'email', email)
            user_first_name = first_name or getattr(user, 'first_name', '')
        
        # Check if user is active
        if not self.user_lookup.is_active(user_id):
            logger.info(f"Magic link requested for inactive user: {email}")
            return True, ""
        
        # Invalidate old tokens for this user
        self.repo.invalidate_user_tokens(user_id, application_id)
        
        # Generate token
        raw_token = self._generate_token()
        
        # Create token in repository
        token_instance = self.repo.create(
            token_hash=self._hash_token(raw_token),
            user_id=user_id,
            email=user_email,
            application_id=application_id,
            ip_address=ip_address,
            user_agent=device_info,
            expiry_minutes=self.expiry_minutes
        )
        
        # Build magic link URL
        magic_url = f"{validation_url}?token={raw_token}" if validation_url else None
        
        # Send email
        try:
            self.email_service.send_magic_link(
                to_email=user_email,
                magic_link_url=magic_url or f"https://example.com/verify?token={raw_token}",
                expires_in_minutes=self.expiry_minutes
            )
        except Exception as e:
            logger.error(f"Failed to send magic link email to {user_email}: {e}")
            return False, "Failed to send magic link email"
        
        logger.info(f"Magic link sent to {user_email}")
        return True, ""
    
    def verify_magic_link(
        self,
        token: str,
        application_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: str = "",
        require_same_device: bool = True
    ) -> MagicLinkResult:
        """
        Validate a magic link and return user info if valid.
        
        Args:
            token: Raw token from URL
            application_id: Expected application ID
            ip_address: Client IP for validation
            device_info: Device info for validation
            require_same_device: If True, validates IP/user_agent match
            
        Returns:
            MagicLinkResult with user_id or error
        """
        if not self.enabled:
            return MagicLinkResult(success=False, error="Magic link authentication is not enabled")
        
        # Get token from repository
        token_instance = self.repo.get_by_token(token)
        
        if not token_instance:
            return MagicLinkResult(
                success=False,
                error="Invalid or expired magic link."
            )
        
        # Check validity
        if not token_instance.is_valid():
            return MagicLinkResult(
                success=False,
                error="Magic link has expired or already been used."
            )
        
        # Check application match (if specified)
        if application_id and token_instance.application_id:
            if token_instance.application_id != application_id:
                return MagicLinkResult(
                    success=False,
                    error="Magic link is not valid for this application."
                )
        
        # Same-device check (security)
        if require_same_device:
            # Allow IP changes within same /24 subnet for mobile networks
            ip_match = self._ip_matches(token_instance.ip_address, ip_address)
            
            if not ip_match:
                logger.warning(
                    f"Magic link IP mismatch for user {token_instance.user_id}: "
                    f"expected {token_instance.ip_address}, got {ip_address}"
                )
                return MagicLinkResult(
                    success=False,
                    error="Magic link must be opened on the same device that requested it."
                )
        
        # Check user status
        if not self.user_lookup.is_active(token_instance.user_id):
            return MagicLinkResult(success=False, error="Account is disabled")
        
        if self.user_lookup.is_locked(token_instance.user_id):
            return MagicLinkResult(success=False, error="Account is locked")
        
        # Consume token (single-use)
        self.repo.consume(token_instance.id)
        
        logger.info(f"Magic link verified for user {token_instance.user_id}")
        
        return MagicLinkResult(
            success=True,
            user_id=token_instance.user_id,
            email=token_instance.email
        )
    
    def _ip_matches(self, stored_ip: Optional[str], current_ip: Optional[str]) -> bool:
        """
        Check if IPs match (with subnet tolerance for mobile networks).
        
        Allows /24 subnet match for mobile network roaming.
        """
        if not stored_ip or not current_ip:
            return True  # If we don't have IPs, skip check
        
        if stored_ip == current_ip:
            return True
        
        # Check /24 subnet match
        try:
            stored_parts = stored_ip.split('.')
            current_parts = current_ip.split('.')
            
            if len(stored_parts) == 4 and len(current_parts) == 4:
                # IPv4 /24 subnet match (first 3 octets)
                return stored_parts[:3] == current_parts[:3]
        except Exception:  # pragma: no cover
            pass
        
        return False
