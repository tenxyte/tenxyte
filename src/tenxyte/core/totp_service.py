"""
TOTP Service for Tenxyte Core.

Framework-agnostic TOTP (Time-based One-Time Password) implementation
for 2FA/MFA authentication. Compatible with Google Authenticator, Authy, etc.
"""

import base64
import logging
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import BytesIO
from typing import List, Optional, Protocol, Tuple, runtime_checkable

import pyotp
import qrcode
from cryptography.fernet import Fernet

from tenxyte.core.settings import Settings


logger = logging.getLogger(__name__)


@dataclass
class TOTPSetupResult:
    """Result of TOTP 2FA setup."""
    secret: str
    qr_code: str  # base64 data URI
    provisioning_uri: str
    backup_codes: List[str]  # Plain codes to show ONCE


@dataclass
class TOTPUserData:
    """Framework-agnostic user data for TOTP operations."""
    id: str
    email: str
    totp_secret: Optional[str] = None  # Encrypted or plaintext
    is_2fa_enabled: bool = False
    backup_codes: List[str] = field(default_factory=list)  # Hashed codes
    
    def has_backup_codes(self) -> bool:
        """Check if user has backup codes."""
        return len(self.backup_codes) > 0


@runtime_checkable
class TOTPStorage(Protocol):
    """Protocol for TOTP data storage operations."""
    
    def save_totp_secret(self, user_id: str, encrypted_secret: str) -> bool:
        """Save encrypted TOTP secret for user."""
        ...
    
    def save_backup_codes(self, user_id: str, hashed_codes: List[str]) -> bool:
        """Save hashed backup codes for user."""
        ...
    
    def enable_2fa(self, user_id: str) -> bool:
        """Enable 2FA for user."""
        ...
    
    def disable_2fa(self, user_id: str) -> bool:
        """Disable 2FA and clear secrets for user."""
        ...
    
    def load_user_data(self, user_id: str) -> Optional[TOTPUserData]:
        """Load user TOTP data."""
        ...


@runtime_checkable
class CodeReplayProtection(Protocol):
    """Protocol for code replay protection (cache)."""
    
    def is_code_used(self, user_id: str, code: str) -> bool:
        """Check if this code was recently used by this user."""
        ...
    
    def mark_code_used(self, user_id: str, code: str, ttl_seconds: int) -> bool:
        """Mark code as used for replay protection."""
        ...


class InMemoryCodeReplayProtection:
    """In-memory implementation of code replay protection."""
    
    def __init__(self):
        self._used_codes: dict = {}
    
    def is_code_used(self, user_id: str, code: str) -> bool:
        """Check if code was recently used."""
        key = f"{user_id}:{code}"
        return key in self._used_codes
    
    def mark_code_used(self, user_id: str, code: str, ttl_seconds: int) -> bool:
        """Mark code as used."""
        # Note: In production, this should use a real cache with TTL
        # This in-memory version doesn't auto-expire
        key = f"{user_id}:{code}"
        self._used_codes[key] = True
        return True


class TOTPService:
    """
    Framework-agnostic TOTP service for 2FA/MFA.
    
    Handles TOTP secret generation, QR codes, verification, and backup codes.
    Works with any storage backend through the TOTPStorage protocol.
    
    Example:
        from tenxyte.core import Settings, TOTPService
        from tenxyte.adapters.django import DjangoSettingsProvider
        
        settings = Settings(provider=DjangoSettingsProvider())
        totp_service = TOTPService(settings=settings)
        
        # Setup 2FA
        result = totp_service.setup_2fa(
            user_id="user123",
            email="user@example.com",
            storage=django_storage_adapter
        )
        print(result.qr_code)  # Show QR to user
        print(result.backup_codes)  # Show backup codes ONCE
    """
    
    # Default constants
    BACKUP_CODE_LENGTH = 8
    DEFAULT_BACKUP_CODES_COUNT = 10
    DEFAULT_VALID_WINDOW = 1  # 30s periods before/after to accept
    
    def __init__(
        self,
        settings: Settings,
        encryption_key: Optional[str] = None,
        replay_protection: Optional[CodeReplayProtection] = None
    ):
        """
        Initialize TOTP service.
        
        Args:
            settings: Tenxyte settings
            encryption_key: Fernet key for encrypting TOTP secrets (optional but recommended)
            replay_protection: Service for replay protection (defaults to in-memory)
        """
        self.settings = settings
        
        # Setup encryption for TOTP secrets
        if encryption_key:
            self.totp_key = Fernet(encryption_key.encode("utf-8"))
        else:
            # Try from environment or settings
            env_key = os.environ.get("TENXYTE_TOTP_ENCRYPTION_KEY")
            if env_key:
                self.totp_key = Fernet(env_key.encode("utf-8"))
            else:
                self.totp_key = None
                logger.warning(
                    "TENXYTE_TOTP_ENCRYPTION_KEY not set. "
                    "TOTP secrets will be stored in plaintext. This is insecure."
                )
        
        # Replay protection
        self.replay_protection = replay_protection or InMemoryCodeReplayProtection()
        
        # Settings
        self.issuer_name = settings.totp_issuer_name
        self.backup_codes_count = getattr(settings, 'backup_codes_count', self.DEFAULT_BACKUP_CODES_COUNT)
        self.valid_window = getattr(settings, 'totp_valid_window', self.DEFAULT_VALID_WINDOW)
    
    def _encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret if encryption is enabled."""
        if self.totp_key:
            return self.totp_key.encrypt(secret.encode("utf-8")).decode("utf-8")
        return secret
    
    def _decrypt_secret(self, encrypted_secret: str) -> Optional[str]:
        """Decrypt TOTP secret if encryption is enabled."""
        if not encrypted_secret:
            return None
        
        if self.totp_key:
            try:
                return self.totp_key.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
            except Exception as e:
                logger.error(f"[TOTP] Failed to decrypt TOTP secret: {e}")
                return None
        return encrypted_secret
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret (base32)."""
        return pyotp.random_base32()
    
    def get_totp(self, secret: str) -> pyotp.TOTP:
        """Create TOTP object from secret."""
        return pyotp.TOTP(secret)
    
    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """
        Generate URI for authenticator app setup.
        
        Format: otpauth://totp/Tenxyte:user@email.com?secret=XXX&issuer=Tenxyte
        """
        totp = self.get_totp(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.issuer_name)
    
    def generate_qr_code(self, secret: str, email: str) -> str:
        """
        Generate QR code as base64 data URI for scanning.
        
        Returns:
            PNG image encoded as base64 data URI
        """
        uri = self.get_provisioning_uri(secret, email)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
    
    def generate_backup_codes(self, count: Optional[int] = None) -> Tuple[List[str], List[str]]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of codes to generate (default: backup_codes_count setting)
            
        Returns:
            Tuple of (plain_codes, hashed_codes)
            - plain_codes: Show to user ONCE
            - hashed_codes: Store in database
        """
        import bcrypt
        
        count = count or self.backup_codes_count
        plain_codes = []
        hashed_codes = []
        
        for _ in range(count):
            # Generate random code (64 bits, formatted: "a1b2c3d4-e5f6g7h8")
            code = secrets.token_hex(self.BACKUP_CODE_LENGTH)
            formatted_code = f"{code[:8]}-{code[8:]}"
            plain_codes.append(formatted_code)
            
            # Hash with bcrypt
            hashed = bcrypt.hashpw(
                formatted_code.encode('utf-8'),
                bcrypt.gensalt(rounds=12)
            ).decode('utf-8')
            hashed_codes.append(hashed)
        
        return plain_codes, hashed_codes
    
    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verify and consume a backup code.
        
        Args:
            code: Code entered by user
            hashed_codes: List of stored hashed codes
            
        Returns:
            Tuple of (is_valid, remaining_codes)
            - is_valid: True if code matched and was removed
            - remaining_codes: Updated list of hashed codes
        """
        import bcrypt
        
        if not hashed_codes:
            return False, []
        
        # Normalize code
        normalized = code.lower().replace(" ", "").replace("-", "")
        if len(normalized) == 16:
            formatted = f"{normalized[:8]}-{normalized[8:]}"
        else:
            formatted = code.lower()
        
        # Find matching hash
        matched_hash = None
        remaining = list(hashed_codes)  # Copy
        
        for stored in hashed_codes:
            if bcrypt.checkpw(formatted.encode('utf-8'), stored.encode('utf-8')):
                matched_hash = stored
                remaining.remove(stored)
                break
        
        if matched_hash:
            return True, remaining
        
        return False, hashed_codes
    
    def verify_code(
        self,
        secret: str,
        code: str,
        user_id: Optional[str] = None,
        valid_window: Optional[int] = None
    ) -> bool:
        """
        Verify a TOTP code with replay protection.
        
        Args:
            secret: TOTP secret (plaintext)
            code: 6-digit code from authenticator app
            user_id: User ID for replay protection (optional)
            valid_window: Number of 30s periods to accept (default: valid_window setting)
            
        Returns:
            True if code is valid and not replayed
        """
        window = valid_window if valid_window is not None else self.valid_window
        
        if not secret or not code:
            return False
        
        # Anti-replay check
        if user_id:
            if self.replay_protection.is_code_used(user_id, code):
                logger.warning(f"[TOTP] Replay attack prevented for user {user_id}")
                return False
        
        try:
            totp = self.get_totp(secret)
            is_valid = totp.verify(code, valid_window=window)
            
            if is_valid and user_id:
                # Mark code as used for window duration + margin
                # valid_window=1 means checking 3 periods (90s), cache for 120s to be safe
                ttl = (window * 30 * 2) + 60
                self.replay_protection.mark_code_used(user_id, code, ttl)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"[TOTP] Verification error: {e}")
            return False
    
    def setup_2fa(
        self,
        user_id: str,
        email: str,
        storage: TOTPStorage
    ) -> TOTPSetupResult:
        """
        Initialize 2FA setup for a user.
        
        Args:
            user_id: User identifier
            email: User email for QR code
            storage: Storage adapter for saving secrets
            
        Returns:
            TOTPSetupResult with secret, QR code, and backup codes
        """
        # Generate new secret
        secret = self.generate_secret()
        
        # Encrypt and save secret
        encrypted = self._encrypt_secret(secret)
        storage.save_totp_secret(user_id, encrypted)
        
        # Generate QR code
        qr_code = self.generate_qr_code(secret, email)
        
        # Generate backup codes
        plain_codes, hashed_codes = self.generate_backup_codes()
        storage.save_backup_codes(user_id, hashed_codes)
        
        return TOTPSetupResult(
            secret=secret,
            qr_code=qr_code,
            provisioning_uri=self.get_provisioning_uri(secret, email),
            backup_codes=plain_codes,
        )
    
    def confirm_2fa_setup(
        self,
        user_id: str,
        code: str,
        storage: TOTPStorage
    ) -> Tuple[bool, str]:
        """
        Confirm 2FA activation by verifying first code.
        
        Args:
            user_id: User identifier
            code: TOTP code from authenticator app
            storage: Storage adapter
            
        Returns:
            Tuple of (success, error_message)
        """
        # Load user data
        user_data = storage.load_user_data(user_id)
        if not user_data or not user_data.totp_secret:
            return False, "2FA setup not initiated. Call setup first."
        
        if user_data.is_2fa_enabled:
            return False, "2FA is already enabled."
        
        # Decrypt secret and verify code
        secret = self._decrypt_secret(user_data.totp_secret)
        if not secret:
            return False, "Failed to decrypt TOTP secret."
        
        if not self.verify_code(secret, code, user_id=user_id):
            return False, "Invalid code. Please try again."
        
        # Enable 2FA
        storage.enable_2fa(user_id)
        logger.info(f"[TOTP] 2FA enabled for user {user_id}")
        
        return True, ""
    
    def verify_2fa(
        self,
        user_id: str,
        code: str,
        storage: TOTPStorage
    ) -> Tuple[bool, str]:
        """
        Verify 2FA code during login.
        
        Args:
            user_id: User identifier
            code: TOTP code or backup code
            storage: Storage adapter
            
        Returns:
            Tuple of (success, error_message)
        """
        # Load user data
        user_data = storage.load_user_data(user_id)
        if not user_data:
            return False, "User not found."
        
        if not user_data.is_2fa_enabled:
            return True, ""  # 2FA not enabled = OK
        
        if not code:
            return False, "2FA code required."
        
        # Try TOTP code first
        secret = self._decrypt_secret(user_data.totp_secret)
        if secret and self.verify_code(secret, code, user_id=user_id):
            return True, ""
        
        # Try backup code
        is_valid, remaining = self.verify_backup_code(code, user_data.backup_codes)
        if is_valid:
            # Update remaining codes
            storage.save_backup_codes(user_id, remaining)
            logger.info(f"[TOTP] Backup code used for user {user_id}. {len(remaining)} remaining.")
            return True, ""
        
        return False, "Invalid 2FA code."
    
    def disable_2fa(
        self,
        user_id: str,
        code: str,
        storage: TOTPStorage
    ) -> Tuple[bool, str]:
        """
        Disable 2FA after verification.
        
        Args:
            user_id: User identifier
            code: TOTP code or backup code for verification
            storage: Storage adapter
            
        Returns:
            Tuple of (success, error_message)
        """
        # Load user data
        user_data = storage.load_user_data(user_id)
        if not user_data:
            return False, "User not found."
        
        if not user_data.is_2fa_enabled:
            return False, "2FA is not enabled."
        
        # Verify code first
        secret = self._decrypt_secret(user_data.totp_secret)
        is_valid = False
        
        if secret:
            is_valid = self.verify_code(secret, code, user_id=user_id)
        
        if not is_valid and user_data.has_backup_codes():
            is_valid, _ = self.verify_backup_code(code, user_data.backup_codes)
        
        if not is_valid:
            return False, "Invalid code."
        
        # Disable 2FA
        storage.disable_2fa(user_id)
        logger.info(f"[TOTP] 2FA disabled for user {user_id}")
        
        return True, ""
    
    def regenerate_backup_codes(
        self,
        user_id: str,
        code: str,
        storage: TOTPStorage
    ) -> Tuple[bool, List[str], str]:
        """
        Regenerate backup codes after verification.
        
        Args:
            user_id: User identifier
            code: TOTP code for verification
            storage: Storage adapter
            
        Returns:
            Tuple of (success, new_codes, error_message)
        """
        # Load user data
        user_data = storage.load_user_data(user_id)
        if not user_data:
            return False, [], "User not found."
        
        if not user_data.is_2fa_enabled:
            return False, [], "2FA is not enabled."
        
        # Verify TOTP code
        secret = self._decrypt_secret(user_data.totp_secret)
        if not secret or not self.verify_code(secret, code, user_id=user_id):
            return False, [], "Invalid code."
        
        # Generate new codes
        plain_codes, hashed_codes = self.generate_backup_codes()
        storage.save_backup_codes(user_id, hashed_codes)
        
        logger.info(f"[TOTP] Backup codes regenerated for user {user_id}")
        return True, plain_codes, ""
