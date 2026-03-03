"""
Auth serializers - Registration, Login, Token, Google Auth, User profile.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import get_user_model
from ..validators import validate_password
from ..device_info import validate_device_info as _validate_device_info

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    phone_country_code = serializers.CharField(max_length=5, required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=100, required=False, default='')
    last_name = serializers.CharField(max_length=100, required=False, default='')
    login = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Si True, l'utilisateur est connecté immédiatement après l'inscription (tokens JWT retournés)"
    )
    device_info = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default='',
        help_text="Device info au format v1 (ex: v=1|os=windows;osv=11|device=desktop)"
    )

    def validate_device_info(self, value):
        if value:
            is_valid, errors = _validate_device_info(value)
            if not is_valid:
                raise serializers.ValidationError(errors)
        return value

    def validate_password(self, value):
        """Valide la complexite du mot de passe."""
        # On recupere l'email du contexte initial si disponible
        email = self.initial_data.get('email')
        is_valid, errors = validate_password(value, email=email)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, data):
        if not data.get('email') and not (data.get('phone_country_code') and data.get('phone_number')):
            raise serializers.ValidationError('Email or phone number is required')
        return data


class LoginEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        help_text="Code 2FA (requis si 2FA activé)"
    )
    device_info = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default='',
        help_text="Device info au format v1 (ex: v=1|os=windows;osv=11|device=desktop)"
    )

    def validate_device_info(self, value):
        if value:
            is_valid, errors = _validate_device_info(value)
            if not is_valid:
                raise serializers.ValidationError(errors)
        return value


class LoginPhoneSerializer(serializers.Serializer):
    phone_country_code = serializers.CharField(max_length=5)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        help_text="Code 2FA (requis si 2FA activé)"
    )
    device_info = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default='',
        help_text="Device info au format v1 (ex: v=1|os=windows;osv=11|device=desktop)"
    )

    def validate_device_info(self, value):
        if value:
            is_valid, errors = _validate_device_info(value)
            if not is_valid:
                raise serializers.ValidationError(errors)
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()



class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_country_code', 'phone_number',
            'first_name', 'last_name', 'is_email_verified', 'is_phone_verified',
            'is_2fa_enabled', 'roles', 'permissions', 'created_at', 'last_login'
        ]
        # VULN-005: Ensure sensitive fields are strictly read-only even if injected
        read_only_fields = [
            'id', 'is_email_verified', 'is_phone_verified', 'is_2fa_enabled', 
            'created_at', 'last_login', 'is_staff', 'is_superuser', 
            'is_banned', 'is_active', 'is_locked', 'is_deleted'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        return obj.get_all_roles()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        return obj.get_all_permissions()
