import pytest
from django.utils import timezone
from tenxyte.serializers.user_admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    BanUserSerializer,
    LockUserSerializer,
)
from tenxyte.models import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAdminUserListSerializer:
    def test_serialization(self):
        user = User.objects.create(email="list@example.com", first_name="A", last_name="B")
        serializer = AdminUserListSerializer(user)
        data = serializer.data
        
        assert data['email'] == "list@example.com"
        assert data['first_name'] == "A"
        assert 'roles' in data
        assert isinstance(data['roles'], list)


@pytest.mark.django_db
class TestAdminUserDetailSerializer:
    def test_serialization(self):
        user = User.objects.create(email="detail@example.com")
        serializer = AdminUserDetailSerializer(user)
        data = serializer.data
        
        assert data['email'] == "detail@example.com"
        assert 'roles' in data
        assert 'permissions' in data
        assert isinstance(data['roles'], list)
        assert isinstance(data['permissions'], list)


class TestAdminUserUpdateSerializer:
    def test_valid_update(self):
        data = {
            'first_name': 'New',
            'last_name': 'Name',
            'is_active': False,
            'is_staff': True,
            'is_superuser': False,
            'max_sessions': 10,
            'max_devices': 5
        }
        serializer = AdminUserUpdateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_max_devices(self):
        data = {'max_devices': -1}
        serializer = AdminUserUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'max_devices' in serializer.errors


class TestBanUserSerializer:
    def test_valid_ban(self):
        data = {'reason': 'Spam'}
        serializer = BanUserSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['reason'] == 'Spam'

    def test_empty_reason(self):
        data = {}
        serializer = BanUserSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['reason'] == ''


class TestLockUserSerializer:
    def test_valid_lock(self):
        data = {
            'duration_minutes': 60,
            'reason': 'Too many attempts'
        }
        serializer = LockUserSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['duration_minutes'] == 60
        assert serializer.validated_data['reason'] == 'Too many attempts'

    def test_default_values(self):
        data = {}
        serializer = LockUserSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['duration_minutes'] == 30
        assert serializer.validated_data['reason'] == ''

    def test_invalid_duration(self):
        data = {'duration_minutes': 0}
        serializer = LockUserSerializer(data=data)
        assert not serializer.is_valid()
        assert 'duration_minutes' in serializer.errors
