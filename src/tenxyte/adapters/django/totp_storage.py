"""
Django TOTP Storage for Tenxyte Core.

Implements the TOTPStorage protocol using Django's ORM.
Stores encrypted TOTP secrets and handles replay protection.
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TOTPUserData:
    """Data class for TOTP user data returned by load_user_data."""
    totp_secret: Optional[str]
    is_2fa_enabled: bool
    backup_codes: List[str]
    
    def has_backup_codes(self) -> bool:
        return bool(self.backup_codes)


class DjangoTOTPStorage:
    """
    TOTP storage implementation for Django.
    
    Stores TOTP secrets in the User model and manages replay protection
    using Django's cache framework.
    
    Example:
        from tenxyte.adapters.django.totp_storage import DjangoTOTPStorage
        
        storage = DjangoTOTPStorage()
        secret = storage.get_secret(user_id)
        storage.store_secret(user_id, encrypted_secret)
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize TOTP storage.
        
        Args:
            encryption_key: Key for encrypting TOTP secrets (optional)
        """
        self.encryption_key = encryption_key
    
    def get_secret(self, user_id: str) -> Optional[str]:
        """
        Get the encrypted TOTP secret for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Encrypted TOTP secret or None
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            return getattr(user, 'totp_secret', None)
        except UserModel.DoesNotExist:
            return None
    
    def store_secret(self, user_id: str, encrypted_secret: str) -> bool:
        """
        Store the encrypted TOTP secret for a user.
        
        Args:
            user_id: User ID
            encrypted_secret: Encrypted TOTP secret
            
        Returns:
            True if stored successfully
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            user.totp_secret = encrypted_secret
            user.save(update_fields=['totp_secret'])
            return True
        except UserModel.DoesNotExist:
            return False
    
    def delete_secret(self, user_id: str) -> bool:
        """
        Delete the TOTP secret for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            user.totp_secret = None
            user.is_2fa_enabled = False
            user.save(update_fields=['totp_secret', 'is_2fa_enabled'])
            return True
        except UserModel.DoesNotExist:
            return False
    
    def is_code_used(self, user_id: str, code: str) -> bool:
        """
        Check if a TOTP code has been used recently (replay protection).
        
        Uses Django cache to track recently used codes.
        
        Args:
            user_id: User ID
            code: TOTP code to check
            
        Returns:
            True if code was recently used
        """
        from django.core.cache import cache
        
        cache_key = f"totp_used_{user_id}_{code}"
        return cache.get(cache_key) is not None
    
    def mark_code_used(self, user_id: str, code: str, ttl_seconds: int = 60) -> bool:
        """
        Mark a TOTP code as used to prevent replay attacks.
        
        Args:
            user_id: User ID
            code: TOTP code that was used
            ttl_seconds: Time to keep code in cache (default 60s)
            
        Returns:
            True if marked successfully
        """
        from django.core.cache import cache
        
        cache_key = f"totp_used_{user_id}_{code}"
        cache.set(cache_key, True, timeout=ttl_seconds)
        return True
    
    def get_backup_codes(self, user_id: str) -> list:
        """
        Get hashed backup codes for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of hashed backup codes
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            codes = getattr(user, 'backup_codes', None)
            return codes or []
        except UserModel.DoesNotExist:
            return []
    
    def store_backup_codes(self, user_id: str, hashed_codes: list) -> bool:
        """
        Store hashed backup codes for a user.
        
        Args:
            user_id: User ID
            hashed_codes: List of hashed backup codes
            
        Returns:
            True if stored successfully
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            user.backup_codes = hashed_codes
            user.save(update_fields=['backup_codes'])
            return True
        except UserModel.DoesNotExist:
            return False
    
    def use_backup_code(self, user_id: str, code_hash: str) -> bool:
        """
        Mark a backup code as used by removing it.
        
        Args:
            user_id: User ID
            code_hash: Hash of the backup code used
            
        Returns:
            True if code was found and removed
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            codes = getattr(user, 'backup_codes', []) or []
            
            if code_hash in codes:
                codes.remove(code_hash)
                user.backup_codes = codes
                user.save(update_fields=['backup_codes'])
                return True
            return False
        except UserModel.DoesNotExist:
            return False
    
    # Core TOTPService compatible methods
    
    def save_totp_secret(self, user_id: str, encrypted_secret: str) -> bool:
        """Alias for store_secret - Core TOTPService compatibility."""
        return self.store_secret(user_id, encrypted_secret)
    
    def load_user_data(self, user_id: str) -> Optional[TOTPUserData]:
        """
        Load TOTP user data for Core TOTPService.
        
        Returns:
            TOTPUserData with totp_secret, is_2fa_enabled, backup_codes
        """
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            return TOTPUserData(
                totp_secret=getattr(user, 'totp_secret', None),
                is_2fa_enabled=getattr(user, 'is_2fa_enabled', False),
                backup_codes=getattr(user, 'backup_codes', []) or []
            )
        except UserModel.DoesNotExist:
            return None
    
    def save_backup_codes(self, user_id: str, hashed_codes: List[str]) -> bool:
        """Alias for store_backup_codes - Core TOTPService compatibility."""
        return self.store_backup_codes(user_id, hashed_codes)
    
    def enable_2fa(self, user_id: str) -> bool:
        """Enable 2FA for user - Core TOTPService compatibility."""
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            user.is_2fa_enabled = True
            user.save(update_fields=['is_2fa_enabled'])
            return True
        except UserModel.DoesNotExist:
            return False
    
    def disable_2fa(self, user_id: str) -> bool:
        """Disable 2FA for user - Core TOTPService compatibility."""
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(id=user_id)
            user.is_2fa_enabled = False
            user.totp_secret = None
            user.backup_codes = []
            user.save(update_fields=['is_2fa_enabled', 'totp_secret', 'backup_codes'])
            return True
        except UserModel.DoesNotExist:
            return False
