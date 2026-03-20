from tenxyte.serializers.password_serializers import (
    PasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
)


class TestPasswordSerializer:
    def test_valid_password(self):
        data = {'password': 'SecurePassword123!'}
        serializer = PasswordSerializer(data=data)
        assert serializer.is_valid()

    def test_empty_password(self):
        data = {'password': ''}
        serializer = PasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors


class TestPasswordResetRequestSerializer:
    def test_valid_request_email(self):
        data = {'email': 'test@example.com'}
        serializer = PasswordResetRequestSerializer(data=data)
        assert serializer.is_valid()

    def test_valid_request_phone(self):
        data = {
            'phone_country_code': '+33',
            'phone_number': '612345678'
        }
        serializer = PasswordResetRequestSerializer(data=data)
        assert serializer.is_valid()

    def test_missing_email_and_phone(self):
        data = {}
        serializer = PasswordResetRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors


class TestPasswordResetConfirmSerializer:
    def test_valid_reset(self):
        data = {
            'code': '123456',
            'new_password': 'SecurePassword123!'
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_code_too_short(self):
        data = {
            'code': '12345',
            'new_password': 'SecurePassword123!'
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        assert not serializer.is_valid()
        assert 'code' in serializer.errors

    def test_invalid_password_complexity(self):
        data = {
            'code': '123456',
            'new_password': 'weak'
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors


class TestChangePasswordSerializer:
    def test_valid_change(self):
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'SecurePassword123!'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_password_complexity(self):
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'weak'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors
