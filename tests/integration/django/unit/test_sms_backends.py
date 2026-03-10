import json
import pytest
import sys
from unittest.mock import patch, MagicMock
from django.test import override_settings

try:
    import twilio
    import twilio.rest
    import twilio.base.exceptions
except ImportError:
    class MockTwilioRestException(Exception):
        def __init__(self, status, uri, msg=""):
            super().__init__(msg)
            self.status = status
            self.uri = uri
            self.msg = msg
            self.code = 12345

    mock_exceptions = MagicMock()
    mock_exceptions.TwilioRestException = MockTwilioRestException

    twilio_mock = MagicMock()
    twilio_rest_mock = MagicMock()
    twilio_base_mock = MagicMock()
    
    twilio_mock.rest = twilio_rest_mock
    twilio_mock.base = twilio_base_mock
    twilio_base_mock.exceptions = mock_exceptions

    sys.modules['twilio'] = twilio_mock
    sys.modules['twilio.rest'] = twilio_rest_mock
    sys.modules['twilio.base'] = twilio_base_mock
    sys.modules['twilio.base.exceptions'] = mock_exceptions

from tenxyte.backends.sms import (
    ConsoleBackend,
    TwilioBackend,
    NGHBackend,
    get_sms_backend,
)

class TestConsoleBackend:
    def test_send_sms_logs_message(self, caplog):
        backend = ConsoleBackend()
        result = backend.send_sms("+33600000000", "Mon code OTP est 123456")
        
        assert result is True
        assert "[SMS Console] To: +33600000000" in caplog.text
        assert "[SMS Console] Message: Mon code OTP est 123456" in caplog.text


class TestTwilioBackend:
    @override_settings(
        TWILIO_ACCOUNT_SID="dummy_sid",
        TWILIO_AUTH_TOKEN="dummy_token",
        TWILIO_PHONE_NUMBER="+123456789"
    )
    @patch("twilio.rest.Client")
    def test_send_sms_success(self, MockClient):
        mock_client_instance = MockClient.return_value
        mock_message = MagicMock()
        mock_message.sid = "SMfake123"
        mock_client_instance.messages.create.return_value = mock_message

        backend = TwilioBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        
        assert result is True
        mock_client_instance.messages.create.assert_called_once_with(
            body="Mon OTP",
            from_="+123456789",
            to="+33612345678"
        )

    @override_settings(
        TWILIO_ACCOUNT_SID="",
        TWILIO_AUTH_TOKEN="dummy_token",
        TWILIO_PHONE_NUMBER="+123456789"
    )
    def test_missing_credentials_returns_false(self):
        backend = TwilioBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        assert result is False

    @override_settings(
        TWILIO_ACCOUNT_SID="dummy_sid",
        TWILIO_AUTH_TOKEN="dummy_token",
        TWILIO_PHONE_NUMBER="+123456789"
    )
    @patch("twilio.rest.Client")
    def test_exception_returns_false(self, MockClient):
        mock_client_instance = MockClient.return_value
        mock_client_instance.messages.create.side_effect = Exception("Twilio down")
        
        backend = TwilioBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        assert result is False

    @override_settings(
        TWILIO_ACCOUNT_SID="dummy_sid",
        TWILIO_AUTH_TOKEN="dummy_token",
        TWILIO_PHONE_NUMBER="+123456789"
    )
    @patch("twilio.rest.Client")
    def test_twilio_rest_exception_returns_false(self, MockClient):
        mock_client_instance = MockClient.return_value
        from twilio.base.exceptions import TwilioRestException
        mock_client_instance.messages.create.side_effect = TwilioRestException(
            status=400, uri="/api/v1/whatever", msg="Invalid number"
        )
        
        backend = TwilioBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        assert result is False


class TestNGHBackend:
    @override_settings(
        NGH_API_KEY="dummy_key",
        NGH_API_SECRET="dummy_secret",
        NGH_SENDER_ID="TEST"
    )
    @patch("http.client.HTTPSConnection")
    def test_send_sms_success(self, MockConnection):
        mock_conn_instance = MockConnection.return_value
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": 200,
            "messageid": "12345",
            "credits": "98"
        }).encode("utf-8")
        mock_conn_instance.getresponse.return_value = mock_response

        backend = NGHBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        
        assert result is True
        mock_conn_instance.request.assert_called_once()
        
    @override_settings(NGH_API_KEY="")
    def test_missing_credentials_returns_false(self):
        backend = NGHBackend()
        assert backend.send_sms("+33", "msg") is False

    @override_settings(
        NGH_API_KEY="dummy_key",
        NGH_API_SECRET="dummy_secret",
        NGH_SENDER_ID="TEST"
    )
    @patch("http.client.HTTPSConnection")
    def test_api_returns_error_status(self, MockConnection):
        mock_conn_instance = MockConnection.return_value
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": 401,
            "status_desc": "Unauthorized"
        }).encode("utf-8")
        mock_conn_instance.getresponse.return_value = mock_response

        backend = NGHBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        assert result is False

    @override_settings(
        NGH_API_KEY="dummy_key",
        NGH_API_SECRET="dummy_secret",
        NGH_SENDER_ID="TEST"
    )
    @patch("http.client.HTTPSConnection")
    def test_unexpected_exception_returns_false(self, MockConnection):
        mock_conn_instance = MockConnection.return_value
        mock_conn_instance.request.side_effect = Exception("Network Error")

        backend = NGHBackend()
        result = backend.send_sms("+33612345678", "Mon OTP")
        assert result is False


class TestGetSMSBackend:
    @override_settings(TENXYTE_SMS_BACKEND="tenxyte.backends.sms.ConsoleBackend")
    def test_get_sms_backend_returns_configured_instance(self):
        backend = get_sms_backend()
        assert isinstance(backend, ConsoleBackend)
