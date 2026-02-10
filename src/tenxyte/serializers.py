from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import get_user_model, get_role_model, get_permission_model, get_application_model
from .validators import validate_password, get_password_strength

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()
Application = get_application_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    phone_country_code = serializers.CharField(max_length=5, required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=100, required=False, default='')
    last_name = serializers.CharField(max_length=100, required=False, default='')

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


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False)
    access_token = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    redirect_uri = serializers.CharField(required=False)

    def validate(self, data):
        if not data.get('id_token') and not data.get('access_token') and not data.get('code'):
            raise serializers.ValidationError('id_token, access_token or code is required')
        if data.get('code') and not data.get('redirect_uri'):
            raise serializers.ValidationError('redirect_uri is required when using code')
        return data


class VerifyOTPSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class RequestOTPSerializer(serializers.Serializer):
    otp_type = serializers.ChoiceField(choices=['email', 'phone'])


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_country_code = serializers.CharField(max_length=5, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        if not data.get('email') and not (data.get('phone_country_code') and data.get('phone_number')):
            raise serializers.ValidationError('Email or phone number is required')
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
        read_only_fields = ['id', 'is_email_verified', 'is_phone_verified', 'is_2fa_enabled', 'created_at', 'last_login']

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        return obj.get_all_roles()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        return obj.get_all_permissions()


# ============== RBAC Serializers ==============

class PermissionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class RoleSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'permissions', 'permission_codes', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        permission_codes = validated_data.pop('permission_codes', [])
        role = Role.objects.create(**validated_data)
        if permission_codes:
            permissions = Permission.objects.filter(code__in=permission_codes)
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permission_codes = validated_data.pop('permission_codes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permission_codes is not None:
            permissions = Permission.objects.filter(code__in=permission_codes)
            instance.permissions.set(permissions)
        return instance


class RoleListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes"""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'is_default']


class AssignRoleSerializer(serializers.Serializer):
    role_code = serializers.CharField()


class UserRolesSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    role_codes = serializers.ListField(child=serializers.CharField())


# ============== Application Serializers ==============

class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les applications (sans le secret)"""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'access_key', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'access_key', 'created_at', 'updated_at']


class ApplicationCreateSerializer(serializers.Serializer):
    """Serializer pour créer une application"""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, default='', allow_blank=True)


class ApplicationUpdateSerializer(serializers.Serializer):
    """Serializer pour mettre à jour une application"""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


# ============== 2FA Serializers ==============

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
