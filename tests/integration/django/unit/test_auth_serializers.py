import pytest
from rest_framework.exceptions import ValidationError

from tenxyte.serializers.auth_serializers import (
    RegisterSerializer,
    LoginEmailSerializer,
    LoginPhoneSerializer,
    RefreshTokenSerializer,
    UserSerializer,
)
from tenxyte.models import get_user_model

User = get_user_model()


class TestRegisterSerializer:
    def test_valid_email_registration(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User',
            'device_info': 'v=1|os=windows;osv=11|device=desktop'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['email'] == 'test@example.com'
        assert serializer.validated_data['first_name'] == 'Test'

    def test_valid_phone_registration(self):
        data = {
            'phone_country_code': '+33',
            'phone_number': '612345678',
            'password': 'SecurePassword123!'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['phone_country_code'] == '+33'
        assert serializer.validated_data['phone_number'] == '612345678'
        
    def test_missing_email_and_phone(self):
        data = {
            'password': 'SecurePassword123!'
        }
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_invalid_device_info(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'device_info': 'invalid_format'
        }
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'device_info' in serializer.errors

    def test_invalid_password_complexity(self):
        data = {
            'email': 'test@example.com',
            'password': 'weak'
        }
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors


class TestLoginEmailSerializer:
    def test_valid_login(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'device_info': 'v=1|os=windows;osv=11|device=desktop'
        }
        serializer = LoginEmailSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['email'] == 'test@example.com'

    def test_invalid_device_info(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'device_info': 'invalid_format'
        }
        serializer = LoginEmailSerializer(data=data)
        assert not serializer.is_valid()
        assert 'device_info' in serializer.errors


class TestLoginPhoneSerializer:
    def test_valid_login(self):
        data = {
            'phone_country_code': '+33',
            'phone_number': '612345678',
            'password': 'SecurePassword123!',
            'device_info': 'v=1|os=windows;osv=11|device=desktop'
        }
        serializer = LoginPhoneSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_device_info(self):
        data = {
            'phone_country_code': '+33',
            'phone_number': '612345678',
            'password': 'SecurePassword123!',
            'device_info': 'invalid_format'
        }
        serializer = LoginPhoneSerializer(data=data)
        assert not serializer.is_valid()
        assert 'device_info' in serializer.errors


class TestRefreshTokenSerializer:
    def test_valid_refresh_token(self):
        data = {
            'refresh_token': 'dummy_token'
        }
        serializer = RefreshTokenSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestUserSerializer:
    def test_user_serialization(self):
        user = User.objects.create(
            email='user@example.com',
            first_name='John',
            last_name='Doe',
            is_email_verified=True
        )
        
        serializer = UserSerializer(user)
        data = serializer.data
        
        assert data['email'] == 'user@example.com'
        assert data['first_name'] == 'John'
        assert data['is_email_verified'] is True
        assert 'roles' in data
        assert 'permissions' in data
        assert 'password' not in data

    def test_roles_and_permissions(self):
        user = User.objects.create(email='admin@example.com')
        # We assume empty roles and permissions initially
        serializer = UserSerializer(user)
        data = serializer.data
        assert isinstance(data['roles'], list)
        assert isinstance(data['permissions'], list)
