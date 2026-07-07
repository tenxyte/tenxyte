from typing import Tuple

from .otp_service import OTPService


class ReauthService:
    """
    Point unique de la logique de la porte de réauthentification, réutilisé
    par les Sensitive_Password_Action (changement de mot de passe, désactivation
    2FA, suppression de compte, export de données, etc.).
    """

    def __init__(self, otp_service: OTPService = None):
        self.otp_service = otp_service or OTPService()

    def verify(self, user, password: str = "", otp_code: str = "") -> Tuple[bool, str, str]:
        """
        Retourne (success, error_code, error_message).
        - password non vide et correct -> succès (comportement actuel inchangé).
        - otp_code non vide et valide (Login_OTP_Code frais) -> succès.
        - aucune preuve valide -> échec REAUTH_REQUIRED.
        """
        if password:
            if user.check_password(password):
                return True, "", ""
            return False, "INVALID_PASSWORD", "Current password is incorrect"
        if otp_code:
            ok, err = self.otp_service.verify_login_otp(user, otp_code)
            if ok:
                return True, "", ""
            return False, "OTP_INVALID", err
        return False, "REAUTH_REQUIRED", "Current password or a valid OTP code is required"
