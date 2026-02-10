"""
Tests unitaires pour les backends SMS et Email.
"""
import pytest
from unittest.mock import Mock, patch

from tenxyte.backends.sms import (
    ConsoleBackend as SMSConsoleBackend,
    get_sms_backend
)
from tenxyte.backends.email import (
    ConsoleBackend as EmailConsoleBackend,
    DjangoBackend,
    get_email_backend
)


class TestSMSBackends:
    """Tests pour les backends SMS."""

    def test_console_backend_send_sms(self):
        """Test d'envoi SMS via console."""
        backend = SMSConsoleBackend()
        result = backend.send_sms("+33612345678", "Code de vérification: 123456")

        assert result is True

    def test_get_sms_backend_default(self):
        """Test de récupération du backend par défaut."""
        backend = get_sms_backend()

        assert backend is not None
        assert isinstance(backend, SMSConsoleBackend)

    def test_get_sms_backend_from_settings(self, settings):
        """Test de récupération du backend configuré."""
        settings.TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.ConsoleBackend'
        backend = get_sms_backend()

        assert backend is not None
        assert isinstance(backend, SMSConsoleBackend)

    def test_console_backend_handles_errors(self):
        """Test de gestion des erreurs."""
        backend = SMSConsoleBackend()

        # Devrait retourner True même avec des données invalides (console)
        result = backend.send_sms("", "")
        assert result is True


class TestEmailBackends:
    """Tests pour les backends Email."""

    def test_console_backend_send_email(self):
        """Test d'envoi email via console."""
        backend = EmailConsoleBackend()
        result = backend.send_email(
            to_email="test@example.com",
            subject="Test",
            message="Message de test"
        )

        assert result is True

    def test_get_email_backend_default(self):
        """Test de récupération du backend email par défaut."""
        backend = get_email_backend()

        assert backend is not None
        assert isinstance(backend, (EmailConsoleBackend, DjangoBackend))

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_django_backend_send_email(self, mock_email_cls):
        """Test d'envoi email via Django."""
        mock_email = mock_email_cls.return_value
        mock_email.send.return_value = 1

        backend = DjangoBackend()
        result = backend.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            message="Test Message"
        )

        assert result is True
        mock_email.send.assert_called_once()

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_django_backend_handles_errors(self, mock_email_cls):
        """Test de gestion des erreurs Django backend."""
        mock_email = mock_email_cls.return_value
        mock_email.send.side_effect = Exception("SMTP error")

        backend = DjangoBackend()
        result = backend.send_email(
            to_email="test@example.com",
            subject="Test",
            message="Test"
        )

        assert result is False

    def test_console_backend_with_empty_fields(self):
        """Test d'envoi email console avec champs vides."""
        backend = EmailConsoleBackend()
        result = backend.send_email(
            to_email="test@example.com",
            subject="",
            message=""
        )

        # Console backend devrait quand même accepter
        assert result is True
