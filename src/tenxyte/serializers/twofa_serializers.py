"""
Two-Factor Authentication serializers - 2FA setup, verify, status.
"""
from rest_framework import serializers


class TwoFactorSetupSerializer(serializers.Serializer):
    """Response serializer pour le setup 2FA"""
    secret = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True, help_text="QR code en base64 (data URI)")
    provisioning_uri = serializers.CharField(read_only=True)
    backup_codes = serializers.ListField(child=serializers.CharField(), read_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer pour vérifier un code 2FA"""
    code = serializers.CharField(
        min_length=6,
        max_length=10,
        help_text="Code TOTP à 6 chiffres ou code de secours"
    )


class TwoFactorStatusSerializer(serializers.Serializer):
    """Response serializer pour le statut 2FA"""
    is_enabled = serializers.BooleanField()
    backup_codes_remaining = serializers.IntegerField()


class LoginWith2FASerializer(serializers.Serializer):
    """Serializer pour login avec 2FA"""
    email = serializers.EmailField(required=False)
    phone_country_code = serializers.CharField(max_length=5, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(
        max_length=10,
        required=False,
        help_text="Code 2FA (requis si 2FA activé)"
    )
