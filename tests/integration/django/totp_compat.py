"""
Wrapper de compatibilité pour TOTPService avec l'ancienne API Django.

Ce wrapper permet aux tests existants de continuer à fonctionner en adaptant
l'API du core TOTPService pour accepter des objets User Django.
"""
from typing import Optional
from tenxyte.core.totp_service import TOTPService as CoreTOTPService
from tenxyte.adapters.django import get_django_settings


class TOTPService:
    """Wrapper de compatibilité pour TOTPService avec objets User Django."""
    
    def __init__(self):
        """Initialiser le service TOTP avec les settings Django."""
        settings = get_django_settings()
        self._service = CoreTOTPService(settings=settings)
    
    def generate_secret(self) -> str:
        """Générer un secret TOTP."""
        return self._service.generate_secret()
    
    def get_totp(self, secret: str):
        """Obtenir un objet TOTP."""
        return self._service.get_totp(secret)
    
    def verify_code(self, user, code: str, valid_window: Optional[int] = None) -> bool:
        """
        Vérifier un code TOTP pour un utilisateur Django.
        
        Args:
            user: Objet User Django avec attribut totp_secret
            code: Code TOTP à vérifier
            valid_window: Fenêtre de validation optionnelle
            
        Returns:
            True si le code est valide
        """
        if not hasattr(user, 'totp_secret') or not user.totp_secret:
            return False
        
        user_id = str(user.id) if hasattr(user, 'id') else None
        return self._service.verify_code(
            secret=user.totp_secret,
            code=code,
            user_id=user_id,
            valid_window=valid_window
        )
    
    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Générer l'URI de provisioning."""
        return self._service.get_provisioning_uri(secret, email)
    
    def generate_qr_code(self, secret: str, email: str) -> str:
        """Générer un QR code."""
        return self._service.generate_qr_code(secret, email)
    
    def generate_backup_codes(self, count: Optional[int] = None):
        """Générer des codes de secours."""
        return self._service.generate_backup_codes(count=count)
    
    def verify_backup_code(self, user, code: str) -> bool:
        """
        Vérifier un code de secours pour un utilisateur Django.
        
        Args:
            user: Objet User Django avec attribut backup_codes
            code: Code de secours à vérifier
            
        Returns:
            True si le code est valide
        """
        if not hasattr(user, 'backup_codes'):
            return False
        
        # Convertir backup_codes en liste si c'est une chaîne JSON
        backup_codes = user.backup_codes
        if isinstance(backup_codes, str):
            import json
            try:
                backup_codes = json.loads(backup_codes)
            except (json.JSONDecodeError, TypeError):
                backup_codes = []
        
        if not backup_codes:
            return False
        
        # Vérifier le code - retourne (is_valid, remaining_codes)
        is_valid, remaining_codes = self._service.verify_backup_code(code, backup_codes)
        
        # Si valide, mettre à jour les codes restants
        if is_valid and hasattr(user, 'save'):
            user.backup_codes = remaining_codes if isinstance(user.backup_codes, list) else json.dumps(remaining_codes)
            user.save(update_fields=['backup_codes'])
        
        return is_valid
    
    @property
    def BACKUP_CODES_COUNT(self):
        """Nombre de codes de secours par défaut."""
        return self._service.DEFAULT_BACKUP_CODES_COUNT
    
    @property
    def totp_key(self):
        """Clé de chiffrement TOTP."""
        return self._service.totp_key
    
    def _get_decrypted_secret(self, user):
        """Déchiffrer le secret TOTP d'un utilisateur."""
        if not hasattr(user, 'totp_secret') or not user.totp_secret:
            return None
        return self._service._decrypt_secret(user.totp_secret)
    
    def setup_2fa(self, user):
        """
        Setup 2FA pour un utilisateur Django.
        
        Returns:
            dict avec 'secret', 'qr_code', 'backup_codes'
        """
        secret = self.generate_secret()
        
        # Chiffrer et sauvegarder le secret
        encrypted = self._service._encrypt_secret(secret)
        user.totp_secret = encrypted
        
        # Générer QR code
        qr_code = self.generate_qr_code(secret, user.email)
        
        # Générer backup codes
        plain_codes, hashed_codes = self.generate_backup_codes()
        user.backup_codes = hashed_codes
        
        user.save(update_fields=['totp_secret', 'backup_codes'])
        
        return {
            'secret': secret,
            'qr_code': qr_code,
            'backup_codes': plain_codes
        }
    
    def confirm_2fa(self, user, code: str):
        """
        Confirmer l'activation 2FA en vérifiant le premier code.
        
        Returns:
            Tuple (success: bool, message: str)
        """
        if not hasattr(user, 'totp_secret') or not user.totp_secret:
            return False, "No TOTP secret configured"
        
        if hasattr(user, 'is_2fa_enabled') and user.is_2fa_enabled:
            return False, "2FA already enabled"
        
        if not self.verify_code(user, code):
            return False, "Invalid code"
        
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])
        
        return True, ""
    
    def disable_2fa(self, user, code: str):
        """
        Désactiver 2FA après vérification du code.
        
        Returns:
            Tuple (success: bool, message: str)
        """
        if not hasattr(user, 'is_2fa_enabled') or not user.is_2fa_enabled:
            return False, "2FA not enabled"
        
        # Vérifier avec code TOTP ou backup code
        valid_totp = self.verify_code(user, code)
        valid_backup = self.verify_backup_code(user, code) if not valid_totp else False
        
        if not valid_totp and not valid_backup:
            return False, "Invalid code"
        
        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = []
        user.save(update_fields=['is_2fa_enabled', 'totp_secret', 'backup_codes'])
        
        return True, ""
    
    def verify_2fa(self, user, code: str):
        """
        Vérifier un code 2FA (TOTP ou backup).
        
        Returns:
            Tuple (success: bool, message: str)
        """
        if not hasattr(user, 'is_2fa_enabled') or not user.is_2fa_enabled:
            return True, ""  # 2FA not enabled, pass through
        
        if not code:
            return False, "Code required"
        
        # Essayer TOTP d'abord
        if self.verify_code(user, code):
            return True, ""
        
        # Essayer backup code
        if self.verify_backup_code(user, code):
            return True, ""
        
        return False, "Invalid code"
    
    def regenerate_backup_codes(self, user, code: str):
        """
        Régénérer les codes de secours après vérification.
        
        Returns:
            Tuple (success: bool, codes: List[str], message: str)
        """
        if not hasattr(user, 'is_2fa_enabled') or not user.is_2fa_enabled:
            return False, [], "2FA not enabled"
        
        if not self.verify_code(user, code):
            return False, [], "Invalid code"
        
        plain_codes, hashed_codes = self.generate_backup_codes()
        user.backup_codes = hashed_codes
        user.save(update_fields=['backup_codes'])
        
        return True, plain_codes, ""
