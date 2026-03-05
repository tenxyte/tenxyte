import logging
from typing import Tuple
from ..models import get_user_model, OTPCode

User = get_user_model()

logger = logging.getLogger(__name__)


class OTPService:
    """
    Service de gestion des codes OTP
    """

    def generate_email_verification_otp(self, user: User) -> Tuple[OTPCode, str]:
        """
        Génère un code OTP pour vérification email.

        Returns:
            Tuple of (OTPCode instance, raw_code)
        """
        # Invalider les anciens codes
        OTPCode.objects.filter(user=user, otp_type="email_verification", is_used=False).update(is_used=True)

        return OTPCode.generate(user, "email_verification", validity_minutes=15)

    def generate_phone_verification_otp(self, user: User) -> Tuple[OTPCode, str]:
        """
        Génère un code OTP pour vérification téléphone.

        SECURITY WARNING (F-11): L'authentification par SMS (OTP via SMS)
        est vulnérable aux attaques de SIM Swapping (détournement de ligne).
        Il est fortement déconseillé d'utiliser le SMS comme unique facteur
        de récupération ou comme 2FA principal dans un contexte hautement
        sécurisé (preset 'robust'). Préférez TOTP ou WebAuthn.

        Returns:
            Tuple of (OTPCode instance, raw_code)
        """
        # Invalider les anciens codes
        OTPCode.objects.filter(user=user, otp_type="phone_verification", is_used=False).update(is_used=True)

        return OTPCode.generate(user, "phone_verification", validity_minutes=10)

    def generate_password_reset_otp(self, user: User) -> Tuple[OTPCode, str]:
        """
        Génère un code OTP pour réinitialisation mot de passe.

        Returns:
            Tuple of (OTPCode instance, raw_code)
        """
        # Invalider les anciens codes
        OTPCode.objects.filter(user=user, otp_type="password_reset", is_used=False).update(is_used=True)

        return OTPCode.generate(user, "password_reset", validity_minutes=15)

    def verify_email_otp(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Vérifie un code OTP pour email
        """
        try:
            otp = OTPCode.objects.filter(user=user, otp_type="email_verification", is_used=False).latest("created_at")
        except OTPCode.DoesNotExist:
            return False, "No verification code found"

        if not otp.is_valid():
            return False, "Code expired or too many attempts. Please request a new code."

        if otp.verify(code):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            return True, ""

        otp.refresh_from_db()
        if otp.attempts >= otp.max_attempts:
            return False, "Too many attempts. Please request a new code."

        return False, f"Invalid code. {otp.max_attempts - otp.attempts} attempt(s) remaining."

    def verify_phone_otp(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Vérifie un code OTP pour téléphone
        """
        try:
            otp = OTPCode.objects.filter(user=user, otp_type="phone_verification", is_used=False).latest("created_at")
        except OTPCode.DoesNotExist:
            return False, "No verification code found"

        if not otp.is_valid():
            return False, "Code expired or too many attempts. Please request a new code."

        if otp.verify(code):
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])
            return True, ""

        otp.refresh_from_db()
        if otp.attempts >= otp.max_attempts:
            return False, "Too many attempts. Please request a new code."

        return False, f"Invalid code. {otp.max_attempts - otp.attempts} attempt(s) remaining."

    def verify_password_reset_otp(self, user: User, code: str) -> Tuple[bool, str]:
        """
        Vérifie un code OTP pour réinitialisation mot de passe
        """
        try:
            otp = OTPCode.objects.filter(user=user, otp_type="password_reset", is_used=False).latest("created_at")
        except OTPCode.DoesNotExist:
            return False, "No reset code found"

        if not otp.is_valid():
            return False, "Code expired or too many attempts. Please request a new code."

        if otp.verify(code):
            return True, ""

        otp.refresh_from_db()
        if otp.attempts >= otp.max_attempts:
            return False, "Too many attempts. Please request a new code."

        return False, f"Invalid code. {otp.max_attempts - otp.attempts} attempt(s) remaining."

    def send_email_otp(
        self, user: User, raw_code: str, otp_type: str = "email_verification", app_name: str = "Tenxyte"
    ) -> bool:
        """
        Envoie le code OTP par email via le service email.

        Args:
            user: L'utilisateur
            raw_code: Le code OTP en clair à envoyer
            otp_type: Le type d'OTP
            app_name: Nom de l'application (pour personnaliser l'email)

        Returns:
            True si l'envoi a réussi
        """
        if not user.email:
            logger.error(f"[OTP] User {user.id} has no email")
            return False

        from .email_service import EmailService

        try:
            email_service = EmailService()
            return email_service.send_otp_email(
                to_email=user.email, code=raw_code, otp_type=otp_type, validity_minutes=15, app_name=app_name
            )
        except Exception as e:
            logger.error(f"[OTP] Email service error: {e}")
            return False

    def send_phone_otp(self, user: User, raw_code: str) -> bool:
        """
        Envoie le code OTP par SMS via le backend configuré.

        SECURITY WARNING (F-11): L'authentification par SMS (OTP via SMS)
        est vulnérable aux attaques de SIM Swapping (détournement de ligne).
        Il est fortement déconseillé d'utiliser le SMS comme unique facteur
        de récupération ou comme 2FA principal dans un contexte hautement
        sécurisé (preset 'robust'). Préférez TOTP ou WebAuthn.

        Args:
            user: L'utilisateur
            raw_code: Le code OTP en clair à envoyer
        """
        phone_number = user.full_phone
        if not phone_number:
            logger.error(f"[OTP] User {user.id} has no phone number")
            return False

        from ..backends.sms import get_sms_backend
        from ..conf import auth_settings

        message = f"Votre code de vérification: {raw_code}. Valide pendant 10 minutes."

        if not auth_settings.SMS_ENABLED:
            if auth_settings.SMS_DEBUG:
                logger.info(f"[OTP][SMS_DEBUG] To: {phone_number} | Message: {message}")
                return True
            logger.warning("[OTP] SMS_ENABLED=False and SMS_DEBUG=False — SMS not sent.")
            return False

        try:
            backend = get_sms_backend()
            return backend.send_sms(phone_number, message)
        except Exception as e:
            logger.error(f"[OTP] SMS backend error: {e}")
            return False
