"""
Security serializers - AuditLog, LoginAttempt, BlacklistedToken, RefreshToken.

All read-only serializers for admin security monitoring.
"""
from rest_framework import serializers
from ..models import AuditLog, BlacklistedToken, RefreshToken, LoginAttempt


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries."""
    id = serializers.CharField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)
    application_name = serializers.CharField(source='application.name', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'action',
            'ip_address', 'user_agent',
            'application', 'application_name',
            'details', 'created_at',
        ]


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer for login attempt records."""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'identifier', 'ip_address', 'application',
            'success', 'failure_reason', 'created_at',
        ]


class BlacklistedTokenSerializer(serializers.ModelSerializer):
    """Serializer for blacklisted JWT tokens."""
    id = serializers.CharField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = BlacklistedToken
        fields = [
            'id', 'token_jti', 'user', 'user_email',
            'blacklisted_at', 'expires_at', 'reason', 'is_expired',
        ]

    def get_is_expired(self, obj):
        from django.utils import timezone
        return obj.expires_at < timezone.now()


class RefreshTokenAdminSerializer(serializers.ModelSerializer):
    """Serializer for refresh tokens (admin view, token value hidden)."""
    id = serializers.CharField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)
    application_name = serializers.CharField(source='application.name', read_only=True, default=None)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = RefreshToken
        fields = [
            'id', 'user', 'user_email',
            'application', 'application_name',
            'device_info', 'ip_address',
            'is_revoked', 'is_expired',
            'expires_at', 'created_at', 'last_used_at',
        ]

    def get_is_expired(self, obj):
        from django.utils import timezone
        return obj.expires_at < timezone.now()
