"""
User Admin serializers - Admin user management (list, detail, update, ban, lock).
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import get_user_model

User = get_user_model()


class AdminUserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for admin user listing."""
    id = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'is_active', 'is_locked', 'is_banned', 'is_deleted',
            'is_email_verified', 'is_phone_verified', 'is_2fa_enabled',
            'roles', 'created_at', 'last_login',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        return list(obj.roles.values_list('code', flat=True))


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Full serializer for admin user detail view."""
    id = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_country_code', 'phone_number',
            'first_name', 'last_name',
            'is_active', 'is_locked', 'locked_until', 'is_banned',
            'is_deleted', 'deleted_at',
            'is_email_verified', 'is_phone_verified',
            'is_2fa_enabled',
            'is_staff', 'is_superuser',
            'max_sessions', 'max_devices',
            'roles', 'permissions',
            'created_at', 'updated_at', 'last_login',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        return list(obj.roles.values_list('code', flat=True))

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        return obj.get_all_permissions()


class AdminUserUpdateSerializer(serializers.Serializer):
    """Serializer for admin user updates (partial)."""
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    is_active = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)
    is_superuser = serializers.BooleanField(required=False)
    max_sessions = serializers.IntegerField(required=False, min_value=0)
    max_devices = serializers.IntegerField(required=False, min_value=0)


class BanUserSerializer(serializers.Serializer):
    """Serializer for banning a user."""
    reason = serializers.CharField(
        max_length=500, required=False, default='',
        help_text="Reason for the ban (stored in audit log)"
    )


class LockUserSerializer(serializers.Serializer):
    """Serializer for locking a user account."""
    duration_minutes = serializers.IntegerField(
        required=False, default=30, min_value=1, max_value=43200,
        help_text="Lock duration in minutes (default: 30, max: 30 days)"
    )
    reason = serializers.CharField(
        max_length=500, required=False, default='',
        help_text="Reason for the lock (stored in audit log)"
    )
