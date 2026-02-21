"""
GDPR admin serializers - AccountDeletionRequest management.
"""
from rest_framework import serializers
from ..models import AccountDeletionRequest


class DeletionRequestSerializer(serializers.ModelSerializer):
    """Serializer for admin deletion request listing/detail."""
    id = serializers.CharField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)
    processed_by_email = serializers.CharField(
        source='processed_by.email', read_only=True, default=None
    )
    is_grace_period_expired = serializers.SerializerMethodField()

    class Meta:
        model = AccountDeletionRequest
        fields = [
            'id', 'user', 'user_email', 'status',
            'requested_at', 'confirmed_at',
            'grace_period_ends_at', 'completed_at',
            'ip_address', 'reason',
            'admin_notes', 'processed_by', 'processed_by_email',
            'is_grace_period_expired',
        ]

    def get_is_grace_period_expired(self, obj):
        return obj.is_grace_period_expired()


class ProcessDeletionSerializer(serializers.Serializer):
    """Serializer for processing a deletion request."""
    admin_notes = serializers.CharField(
        max_length=1000, required=False, default='',
        help_text="Notes de l'admin sur le traitement"
    )
