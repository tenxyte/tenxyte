from tenxyte.serializers.otp_serializers import VerifyOTPSerializer, RequestOTPSerializer


class TestVerifyOTPSerializer:
    def test_valid_otp(self):
        data = {'code': '123456'}
        serializer = VerifyOTPSerializer(data=data)
        assert serializer.is_valid()
        
    def test_invalid_otp_too_short(self):
        data = {'code': '12345'}
        serializer = VerifyOTPSerializer(data=data)
        assert not serializer.is_valid()
        assert 'code' in serializer.errors

    def test_invalid_otp_too_long(self):
        data = {'code': '1234567'}
        serializer = VerifyOTPSerializer(data=data)
        assert not serializer.is_valid()
        assert 'code' in serializer.errors


class TestRequestOTPSerializer:
    def test_valid_request_email(self):
        data = {'otp_type': 'email'}
        serializer = RequestOTPSerializer(data=data)
        assert serializer.is_valid()

    def test_valid_request_phone(self):
        data = {'otp_type': 'phone'}
        serializer = RequestOTPSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_request_type(self):
        data = {'otp_type': 'invalid'}
        serializer = RequestOTPSerializer(data=data)
        assert not serializer.is_valid()
        assert 'otp_type' in serializer.errors
