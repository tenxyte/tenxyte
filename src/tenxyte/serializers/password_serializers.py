"""
Password serializers - Password validation, reset, change.
"""

from rest_framework import serializers
from ..validators import validate_password


class PasswordSerializer(serializers.Serializer):
    """Simple password validation serializer."""

    password = serializers.CharField(write_only=True, min_length=1)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_country_code = serializers.CharField(max_length=5, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        if not data.get("email") and not (data.get("phone_country_code") and data.get("phone_number")):
            raise serializers.ValidationError("Email or phone number is required")
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        """Valide la complexite du nouveau mot de passe."""
        is_valid, errors = validate_password(value)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        """Valide la complexite du nouveau mot de passe."""
        is_valid, errors = validate_password(value)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value
