from tenxyte.serializers.twofa_serializers import (
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    TwoFactorStatusSerializer,
    LoginWith2FASerializer,
)


class TestTwoFactorSetupSerializer:
    def test_valid_setup(self):
        data = {
            'secret': 'dummy_secret',
            'qr_code': 'data:image/png;base64,dummy',
            'provisioning_uri': 'otpauth://totp/dummy',
            'backup_codes': ['123', '456']
        }
        serializer = TwoFactorSetupSerializer(data=data)
        assert serializer.is_valid()


class TestTwoFactorVerifySerializer:
    def test_valid_verify(self):
        data = {'code': '123456'}
        serializer = TwoFactorVerifySerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_code_too_short(self):
        data = {'code': '12345'}
        serializer = TwoFactorVerifySerializer(data=data)
        assert not serializer.is_valid()
        assert 'code' in serializer.errors


class TestTwoFactorStatusSerializer:
    def test_valid_status(self):
        data = {'is_enabled': True, 'backup_codes_remaining': 10}
        serializer = TwoFactorStatusSerializer(data=data)
        assert serializer.is_valid()


class TestLoginWith2FASerializer:
    def test_valid_login_with_email(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'totp_code': '123456'
        }
        serializer = LoginWith2FASerializer(data=data)
        assert serializer.is_valid()

    def test_valid_login_with_phone(self):
        data = {
            'phone_country_code': '+33',
            'phone_number': '612345678',
            'password': 'SecurePassword123!',
            'totp_code': '123456'
        }
        serializer = LoginWith2FASerializer(data=data)
        assert serializer.is_valid()
