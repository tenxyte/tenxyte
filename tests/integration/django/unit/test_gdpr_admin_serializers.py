import pytest
from tenxyte.serializers.gdpr_admin_serializers import (
    DeletionRequestSerializer,
    ProcessDeletionSerializer,
)
from tenxyte.models import AccountDeletionRequest, get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestDeletionRequestSerializer:
    def test_serialization(self):
        user = User.objects.create(email="delete_me@example.com")
        req = AccountDeletionRequest.objects.create(user=user, reason="privacy")
        
        serializer = DeletionRequestSerializer(req)
        data = serializer.data
        
        assert data['user'] == user.id
        assert data['user_email'] == "delete_me@example.com"
        assert data['reason'] == "privacy"
        assert data['status'] == "pending"
        assert 'is_grace_period_expired' in data


class TestProcessDeletionSerializer:
    def test_valid_processing(self):
        data = {'admin_notes': 'Processed according to procedure'}
        serializer = ProcessDeletionSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['admin_notes'] == 'Processed according to procedure'

    def test_empty_notes(self):
        data = {}
        serializer = ProcessDeletionSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['admin_notes'] == ''
