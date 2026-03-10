import logging
import pytest
import sys
from unittest.mock import patch, MagicMock
from django.test import override_settings

# Mock optionnels pour éviter ImportError avec @patch
sys.modules['sendgrid'] = MagicMock()
sys.modules['sendgrid.helpers'] = MagicMock()
sys.modules['sendgrid.helpers.mail'] = MagicMock()

from tenxyte.backends.email import (
    ConsoleBackend,
    DjangoBackend,
    TemplateEmailBackend,
    SendGridBackend,
    get_email_backend,
)

@pytest.fixture
def base_context():
    return {"name": "Test User"}


class TestConsoleBackend:
    def test_send_email_logs_message(self, caplog):
        backend = ConsoleBackend()
        with caplog.at_level(logging.INFO):
            result = backend.send_email(
                "test@example.com", "Sujet", "Message", "<html>HTML</html>"
            )
        assert result is True
        assert "[Email Console] To: test@example.com" in caplog.text
        assert "[Email Console] Subject: Sujet" in caplog.text


class TestDjangoBackend:
    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_email_success(self, mock_send):
        backend = DjangoBackend()
        result = backend.send_email("test@example.com", "Sujet", "Message brut")
        
        assert result is True
        mock_send.assert_called_once_with(fail_silently=False)

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_email_with_html_and_context(self, mock_send):
        backend = DjangoBackend()
        # "Hello {{ name }}" devrait devenir "Hello Test User" si template valide
        result = backend.send_email(
            "test@example.com",
            "Sujet",
            "Hello {{ name }}",
            html_message="<b>Hello {{ name }}</b>",
            context={"name": "Test User"}
        )
        assert result is True
        mock_send.assert_called_once()

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_send_email_exception_returns_false(self, mock_send):
        mock_send.side_effect = Exception("SMTP Error")
        backend = DjangoBackend()
        result = backend.send_email("test@example.com", "Sujet", "Message")
        assert result is False


class TestTemplateEmailBackend:
    @patch("django.template.loader.render_to_string")
    @patch.object(DjangoBackend, "send_email")
    def test_send_template_email_success(self, mock_send_email, mock_render):
        mock_render.return_value = "<html>Bonjour</html>"
        mock_send_email.return_value = True

        backend = TemplateEmailBackend()
        result = backend.send_template_email(
            "test@example.com", "Sujet template", "dummy.html", {"var": 1}
        )
        
        assert result is True
        mock_render.assert_called_once_with("dummy.html", {"var": 1})
        mock_send_email.assert_called_once_with(
            to_email="test@example.com",
            subject="Sujet template",
            message="Bonjour",  # strip_tags de <html>Bonjour</html>
            html_message="<html>Bonjour</html>"
        )
        
    @patch("django.template.loader.render_to_string")
    def test_send_template_email_exception_returns_false(self, mock_render):
        mock_render.side_effect = Exception("Template introuvable")
        backend = TemplateEmailBackend()
        result = backend.send_template_email("test@example.com", "S", "d.html")
        assert result is False


class TestSendGridBackend:
    @override_settings(SENDGRID_API_KEY="dummy_key", SENDGRID_FROM_EMAIL="from@example.com")
    @patch("sendgrid.SendGridAPIClient")
    def test_send_email_success(self, MockSendGridClient):
        # Mocker la reponse
        mock_client_instance = MockSendGridClient.return_value
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client_instance.send.return_value = mock_response

        backend = SendGridBackend()
        result = backend.send_email("test@ex.com", "Sujet", "Texte", "HTML")
        assert result is True
        mock_client_instance.send.assert_called_once()

    @override_settings(SENDGRID_API_KEY="", SENDGRID_FROM_EMAIL="from@example.com")
    def test_send_email_missing_api_key_returns_false(self):
        backend = SendGridBackend()
        result = backend.send_email("test@ex.com", "Sujet", "Texte")
        assert result is False

    @override_settings(SENDGRID_API_KEY="dummy_key", SENDGRID_FROM_EMAIL="from@example.com")
    @patch("sendgrid.SendGridAPIClient")
    def test_send_email_exception_returns_false(self, MockSendGridClient):
        mock_client_instance = MockSendGridClient.return_value
        mock_client_instance.send.side_effect = Exception("SendGrid Error")
        
        backend = SendGridBackend()
        result = backend.send_email("test@ex.com", "Sujet", "Texte")
        assert result is False


class TestGetEmailBackend:
    @override_settings(TENXYTE_EMAIL_BACKEND="tenxyte.backends.email.ConsoleBackend")
    def test_get_email_backend_returns_configured_instance(self):
        backend = get_email_backend()
        assert isinstance(backend, ConsoleBackend)
