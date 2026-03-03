"""
Service TOTP pour l'authentification 2FA.

Utilise pyotp pour générer et vérifier les codes TOTP compatibles
avec Google Authenticator, Authy, etc.
"""

import base64
import hashlib
import secrets
import logging
import os
from io import BytesIO
from typing import Tuple, List, Optional

import pyotp
import qrcode
from cryptography.fernet import Fernet

from ..models import get_user_model
from ..conf import auth_settings

User = get_user_model()

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Service de gestion 2FA avec TOTP (Time-based One-Time Password).
    Compatible avec Google Authenticator, Authy, Microsoft Authenticator, etc.
    """
    def __init__(self):
        encryption_key = os.environ.get("TENXYTE_TOTP_ENCRYPTION_KEY")
        if encryption_key:
            self.totp_key = Fernet(encryption_key.encode('utf-8'))
        else:
            self.totp_key = None
            logger.warning("TENXYTE_TOTP_ENCRYPTION_KEY not set. TOTP secrets will be stored in plaintext. This is insecure.")

    def _get_decrypted_secret(self, user) -> str:
        if not user.totp_secret:
            return None
        if self.totp_key:
            try:
                return self.totp_key.decrypt(user.totp_secret.encode('utf-8')).decode('utf-8')
            except Exception as e:
                logger.error(f"[TOTP] Failed to decrypt TOTP secret for user {user.id}: {e}")
                return None
        return user.totp_secret

    @property
    def ISSUER_NAME(self):
        return auth_settings.TOTP_ISSUER

    @property
    def BACKUP_CODES_COUNT(self):
        return auth_settings.BACKUP_CODES_COUNT

    BACKUP_CODE_LENGTH = 8  # Constante technique, pas configurable

    def generate_secret(self) -> str:
        """
        Génère un nouveau secret TOTP (base32).
        """
        return pyotp.random_base32()

    def get_totp(self, secret: str) -> pyotp.TOTP:
        """
        Crée un objet TOTP à partir du secret.
        """
        return pyotp.TOTP(secret)

    def verify_code(self, user: User, code: str, valid_window: int = 1) -> bool:
        """
        Vérifie un code TOTP avec protection anti-replay.

        Args:
            user: L'utilisateur
            code: Le code à 6 chiffres entré par l'utilisateur
            valid_window: Nombre de périodes de 30s acceptées avant/après (défaut: 1)

        Returns:
            True si le code est valide ET n'a pas été rejoué dans sa fenêtre de validité.
        """
        secret = self._get_decrypted_secret(user)
        if not secret or not code:
            return False

        try:
            from django.core.cache import cache
            
            # Anti-replay check
            cache_key = f"totp_used_{user.id}_{code}"
            if cache.get(cache_key):
                logger.warning(f"[TOTP] Replay attack prevented for user {user.id}")
                return False

            totp = self.get_totp(secret)
            is_valid = totp.verify(code, valid_window=valid_window)
            
            if is_valid:
                # Mark code as used for the duration of the window (+ extra margin)
                # valid_window=1 means checking current, previous, and next 30s period.
                # So the code could be valid for up to 90 seconds. We cache for 120s to be safe.
                cache.set(cache_key, True, timeout=(valid_window * 30 * 2) + 60)
                
            return is_valid
        except Exception as e:
            logger.error(f"[TOTP] Verification error: {e}")
            return False

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """
        Génère l'URI pour configurer l'app authenticator.
        Format: otpauth://totp/Tenxyte:user@email.com?secret=XXX&issuer=Tenxyte
        """
        totp = self.get_totp(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.ISSUER_NAME)

    def generate_qr_code(self, secret: str, email: str) -> str:
        """
        Génère un QR code en base64 pour scanner avec l'app authenticator.

        Returns:
            Image PNG encodée en base64 (data URI)
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
        img.save(buffer, format='PNG')
        buffer.seek(0)

        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"

    def generate_backup_codes(self) -> Tuple[List[str], List[str]]:
        """
        Génère des codes de secours pour récupération.

        Returns:
            Tuple (codes_en_clair, codes_hashés)
            - codes_en_clair: à afficher à l'utilisateur UNE SEULE FOIS
            - codes_hashés: à stocker en base de données
        """
        plain_codes = []
        hashed_codes = []

        for _ in range(self.BACKUP_CODES_COUNT):
            # Générer un code aléatoire (64 bits, ex: "a1b2c3d4-e5f6g7h8")
            code = secrets.token_hex(self.BACKUP_CODE_LENGTH)
            formatted_code = f"{code[:8]}-{code[8:]}"
            plain_codes.append(formatted_code)

            # Hasher le code pour stockage
            hashed = hashlib.sha256(formatted_code.encode()).hexdigest()
            hashed_codes.append(hashed)

        return plain_codes, hashed_codes

    def verify_backup_code(self, user: User, code: str) -> bool:
        """
        Vérifie et consomme un code de secours.

        Returns:
            True si le code est valide (et le supprime de la liste)
        """
        if not user.backup_codes:
            return False

        # Normaliser le code (enlever espaces, tirets optionnels)
        normalized = code.lower().replace(' ', '').replace('-', '')
        if len(normalized) == 16:
            # Reformater pour le hash
            formatted = f"{normalized[:8]}-{normalized[8:]}"
        else:
            formatted = code.lower()

        code_hash = hashlib.sha256(formatted.encode()).hexdigest()

        # time-constant défensif
        import hmac
        # Find if any stored hash matches the provided hash
        matched_hash = None
        for stored in user.backup_codes:
            if hmac.compare_digest(code_hash, stored):
                matched_hash = stored
                break

        if matched_hash:
            # Supprimer le code utilisé
            user.backup_codes.remove(matched_hash)
            user.save(update_fields=['backup_codes'])
            logger.info(f"[TOTP] Backup code used for user {user.id}. {len(user.backup_codes)} remaining.")
            return True

        return False

    def setup_2fa(self, user: User) -> dict:
        """
        Initialise la configuration 2FA pour un utilisateur.

        Returns:
            Dict avec secret, qr_code, et backup_codes
        """
        # Générer un nouveau secret
        secret = self.generate_secret()

        # Stocker temporairement (pas encore activé)
        if self.totp_key:
            user.totp_secret = self.totp_key.encrypt(secret.encode('utf-8')).decode('utf-8')
        else:
            user.totp_secret = secret
        user.save(update_fields=['totp_secret'])

        # Générer le QR code
        email = user.email or f"user_{user.id}"
        qr_code = self.generate_qr_code(secret, email)

        # Générer les codes de secours
        plain_codes, hashed_codes = self.generate_backup_codes()

        # Stocker les codes hashés
        user.backup_codes = hashed_codes
        user.save(update_fields=['backup_codes'])

        return {
            'secret': secret,
            'qr_code': qr_code,
            'provisioning_uri': self.get_provisioning_uri(secret, email),
            'backup_codes': plain_codes,
        }

    def confirm_2fa(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Confirme l'activation du 2FA en vérifiant le premier code.

        Args:
            user: L'utilisateur
            code: Le code TOTP entré depuis l'app authenticator

        Returns:
            Tuple (success, error_message)
        """
        if not user.totp_secret:
            return False, "2FA setup not initiated. Call setup first."

        if user.is_2fa_enabled:
            return False, "2FA is already enabled."

        if not self.verify_code(user, code):
            return False, "Invalid code. Please try again."

        # Activer le 2FA
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])

        logger.info(f"[TOTP] 2FA enabled for user {user.id}")
        return True, ""

    def disable_2fa(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Désactive le 2FA après vérification du code.

        Args:
            user: L'utilisateur
            code: Le code TOTP ou un code de secours

        Returns:
            Tuple (success, error_message)
        """
        if not user.is_2fa_enabled:
            return False, "2FA is not enabled."

        # Vérifier le code TOTP ou un code de secours
        is_valid = self.verify_code(user, code)
        if not is_valid:
            is_valid = self.verify_backup_code(user, code)

        if not is_valid:
            return False, "Invalid code."

        # Désactiver le 2FA
        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = []
        user.save(update_fields=['is_2fa_enabled', 'totp_secret', 'backup_codes'])

        logger.info(f"[TOTP] 2FA disabled for user {user.id}")
        return True, ""

    def verify_2fa(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Vérifie un code 2FA (TOTP ou backup) lors du login.

        Args:
            user: L'utilisateur
            code: Le code TOTP ou un code de secours

        Returns:
            Tuple (success, error_message)
        """
        if not user.is_2fa_enabled:
            return True, ""  # 2FA non activé = OK

        if not code:
            return False, "2FA code required."

        # Essayer le code TOTP d'abord
        if self.verify_code(user, code):
            return True, ""

        # Sinon essayer un code de secours
        if self.verify_backup_code(user, code):
            return True, ""

        return False, "Invalid 2FA code."

    def regenerate_backup_codes(self, user: User, code: str) -> Tuple[bool, List[str], str]:
        """
        Régénère les codes de secours après vérification.

        Returns:
            Tuple (success, new_codes, error_message)
        """
        if not user.is_2fa_enabled:
            return False, [], "2FA is not enabled."

        # Vérifier le code TOTP
        if not self.verify_code(user, code):
            return False, [], "Invalid code."

        # Générer de nouveaux codes
        plain_codes, hashed_codes = self.generate_backup_codes()
        user.backup_codes = hashed_codes
        user.save(update_fields=['backup_codes'])

        logger.info(f"[TOTP] Backup codes regenerated for user {user.id}")
        return True, plain_codes, ""


# Instance singleton
totp_service = TOTPService()
