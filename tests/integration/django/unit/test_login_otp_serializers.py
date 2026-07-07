from tenxyte.serializers.login_otp_serializers import (
    LoginOTPRequestSerializer,
    LoginOTPVerifySerializer,
    SetInitialPasswordSerializer,
    ReauthSerializer,
)


class TestLoginOTPRequestSerializer:
    def test_phone_country_code_normalized_without_plus(self):
        data = {'phone_country_code': '229', 'phone_number': '612345678'}
        serializer = LoginOTPRequestSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['phone_country_code'] == '229'

    def test_phone_country_code_normalized_with_plus(self):
        data = {'phone_country_code': '+229', 'phone_number': '612345678'}
        serializer = LoginOTPRequestSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['phone_country_code'] == '229'

    def test_missing_phone_number_rejected(self):
        data = {'phone_country_code': '+229'}
        serializer = LoginOTPRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone_number' in serializer.errors


class TestLoginOTPVerifySerializer:
    def test_valid_data(self):
        data = {
            'phone_country_code': '+229',
            'phone_number': '612345678',
            'otp_code': '123456',
        }
        serializer = LoginOTPVerifySerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['phone_country_code'] == '229'

    def test_phone_country_code_normalized_without_plus(self):
        data = {
            'phone_country_code': '229',
            'phone_number': '612345678',
            'otp_code': '123456',
        }
        serializer = LoginOTPVerifySerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['phone_country_code'] == '229'

    def test_missing_phone_number_rejected(self):
        data = {
            'phone_country_code': '+229',
            'otp_code': '123456',
        }
        serializer = LoginOTPVerifySerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone_number' in serializer.errors

    def test_otp_code_too_short_rejected(self):
        data = {
            'phone_country_code': '+229',
            'phone_number': '612345678',
            'otp_code': '12345',
        }
        serializer = LoginOTPVerifySerializer(data=data)
        assert not serializer.is_valid()
        assert 'otp_code' in serializer.errors

    def test_otp_code_too_long_rejected(self):
        data = {
            'phone_country_code': '+229',
            'phone_number': '612345678',
            'otp_code': '1234567',
        }
        serializer = LoginOTPVerifySerializer(data=data)
        assert not serializer.is_valid()
        assert 'otp_code' in serializer.errors


class TestSetInitialPasswordSerializer:
    def test_valid_data(self):
        data = {'otp_code': '123456', 'new_password': 'SecurePassword123!'}
        serializer = SetInitialPasswordSerializer(data=data)
        assert serializer.is_valid()

    def test_non_compliant_password_rejected(self):
        data = {'otp_code': '123456', 'new_password': 'weak'}
        serializer = SetInitialPasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors

    def test_otp_code_wrong_length_rejected(self):
        data = {'otp_code': '12345', 'new_password': 'SecurePassword123!'}
        serializer = SetInitialPasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'otp_code' in serializer.errors


class TestReauthSerializer:
    def test_password_only_accepted(self):
        data = {'password': 'SomePassword123!'}
        serializer = ReauthSerializer(data=data)
        assert serializer.is_valid()

    def test_otp_code_only_accepted(self):
        data = {'otp_code': '123456'}
        serializer = ReauthSerializer(data=data)
        assert serializer.is_valid()

    def test_neither_field_accepted(self):
        data = {}
        serializer = ReauthSerializer(data=data)
        assert serializer.is_valid()

    def test_both_fields_accepted(self):
        data = {'password': 'SomePassword123!', 'otp_code': '123456'}
        serializer = ReauthSerializer(data=data)
        assert serializer.is_valid()
