"""
Login OTP serializers - Connexion passwordless par OTP téléphonique,
création de mot de passe initial, et réauthentification par OTP.
"""

from rest_framework import serializers
from ..validators import validate_password, normalize_phone_country_code
from ..device_info import validate_device_info as _validate_device_info


class LoginOTPRequestSerializer(serializers.Serializer):
    phone_country_code = serializers.CharField(max_length=5)
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_country_code(self, value):
        """Normalise l'indicatif (sans '+') pour matcher le stockage en base."""
        return normalize_phone_country_code(value)


class LoginOTPVerifySerializer(serializers.Serializer):
    phone_country_code = serializers.CharField(max_length=5)
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    totp_code = serializers.CharField(
        max_length=10, required=False, allow_blank=True, help_text="Code 2FA (requis si 2FA activé)"
    )
    device_info = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="Device info au format v1 (ex: v=1|os=windows;osv=11|device=desktop)",
    )

    def validate_phone_country_code(self, value):
        """Normalise l'indicatif (sans '+') pour matcher le stockage en base."""
        return normalize_phone_country_code(value)

    def validate_device_info(self, value):
        if value:
            is_valid, errors = _validate_device_info(value)
            if not is_valid:
                raise serializers.ValidationError(errors)
        return value


class SetInitialPasswordSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        """Valide la complexite du nouveau mot de passe."""
        is_valid, errors = validate_password(value)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value


class ReauthSerializer(serializers.Serializer):
    """Preuve de réauthentification pour une Sensitive_Password_Action : mot
    de passe courant OU OTP_Reauth_Challenge (otp_code). Champs optionnels
    ajoutés en plus des champs métier existants de chaque action ; aucun champ
    existant n'est retiré ni renommé."""

    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    otp_code = serializers.CharField(required=False, allow_blank=True, max_length=6, min_length=6)
