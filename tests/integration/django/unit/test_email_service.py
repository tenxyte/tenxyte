"""
Tests for DjangoEmailService - targeting 100% coverage of
src/tenxyte/adapters/django/email_service.py
"""
import pytest
from unittest.mock import patch, MagicMock

from tenxyte.adapters.django.email_service import DjangoEmailService, get_email_service
from tenxyte.core.email_service import EmailAttachment


@pytest.fixture
def email_svc():
    return DjangoEmailService()


# ── _get_from_email ──────────────────────────────────────────────────────────

def test_get_from_email_explicit(email_svc):
    """Returns the explicitly provided from_email (line 55-56)."""
    assert email_svc._get_from_email("alice@example.com") == "alice@example.com"


def test_get_from_email_default_instance():
    """Returns _default_from_email when set on the instance (line 57-58)."""
    svc = DjangoEmailService(default_from_email="svc@example.com")
    assert svc._get_from_email() == "svc@example.com"


def test_get_from_email_django_setting(email_svc):
    """Falls back to Django DEFAULT_FROM_EMAIL setting (line 59)."""
    with patch("tenxyte.adapters.django.email_service.django_settings") as mock_settings:
        mock_settings.DEFAULT_FROM_EMAIL = "django@example.com"
        result = email_svc._get_from_email()
    assert result == "django@example.com"


# ── send ────────────────────────────────────────────────────────────────────

def test_send_plain_text(email_svc):
    """send() with plain-text body returns True (lines 88-114)."""
    with patch("tenxyte.adapters.django.email_service.EmailMultiAlternatives") as MockMsg:
        instance = MagicMock()
        MockMsg.return_value = instance
        result = email_svc.send(
            to_email="bob@example.com",
            subject="Hello",
            body="World",
        )
    assert result is True
    instance.send.assert_called_once()
    instance.attach_alternative.assert_not_called()


def test_send_with_html(email_svc):
    """send() with html_body attaches the HTML alternative (line 100-101)."""
    with patch("tenxyte.adapters.django.email_service.EmailMultiAlternatives") as MockMsg:
        instance = MagicMock()
        MockMsg.return_value = instance
        result = email_svc.send(
            to_email="bob@example.com",
            subject="Hello",
            body="World",
            html_body="<b>World</b>",
        )
    assert result is True
    instance.attach_alternative.assert_called_once_with("<b>World</b>", "text/html")


def test_send_with_cc_bcc(email_svc):
    """send() passes cc and bcc through to EmailMultiAlternatives (lines 95-96)."""
    with patch("tenxyte.adapters.django.email_service.EmailMultiAlternatives") as MockMsg:
        instance = MagicMock()
        MockMsg.return_value = instance
        result = email_svc.send(
            to_email="bob@example.com",
            subject="Hi",
            body="Body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )
    assert result is True
    _, kwargs = MockMsg.call_args
    assert kwargs["cc"] == ["cc@example.com"]
    assert kwargs["bcc"] == ["bcc@example.com"]


def test_send_with_attachments(email_svc):
    """send() attaches files when attachments provided (lines 104-110)."""
    attachment = EmailAttachment(
        filename="file.txt",
        content=b"hello",
        content_type="text/plain",
    )
    with patch("tenxyte.adapters.django.email_service.EmailMultiAlternatives") as MockMsg:
        instance = MagicMock()
        MockMsg.return_value = instance
        result = email_svc.send(
            to_email="bob@example.com",
            subject="Hi",
            body="Body",
            attachments=[attachment],
        )
    assert result is True
    instance.attach.assert_called_once_with("file.txt", b"hello", "text/plain")


def test_send_exception_returns_false(email_svc):
    """send() returns False and prints error when an exception occurs (lines 116-120)."""
    with patch("tenxyte.adapters.django.email_service.EmailMultiAlternatives") as MockMsg:
        MockMsg.side_effect = Exception("SMTP error")
        result = email_svc.send(
            to_email="bob@example.com",
            subject="Hi",
            body="Body",
        )
    assert result is False


# ── send_mass_email ──────────────────────────────────────────────────────────

def test_send_mass_email_success(email_svc):
    """send_mass_email() returns the count of sent emails (lines 137-148)."""
    recipients = [
        ("Subject1", "Body1", "a@example.com"),
        ("Subject2", "Body2", "b@example.com"),
    ]
    with patch("django.core.mail.send_mass_mail", return_value=2) as mock_smm:
        result = email_svc.send_mass_email(recipients)
    assert result == 2
    mock_smm.assert_called_once()


def test_send_mass_email_exception_returns_zero(email_svc):
    """send_mass_email() returns 0 on exception (lines 149-151)."""
    with patch("django.core.mail.send_mass_mail", side_effect=Exception("fail")):
        result = email_svc.send_mass_email([("S", "B", "x@example.com")])
    assert result == 0


def test_send_mass_email_with_from(email_svc):
    """send_mass_email() forwards custom from_email (line 139)."""
    with patch("django.core.mail.send_mass_mail", return_value=1) as mock_smm:
        email_svc.send_mass_email(
            [("S", "B", "x@example.com")],
            from_email="custom@example.com",
        )
    args, _ = mock_smm.call_args
    # First arg is the list of tuples; check the from_email field
    assert args[0][0][2] == "custom@example.com"


# ── get_email_service ────────────────────────────────────────────────────────

def test_get_email_service(email_svc):
    """get_email_service() returns a configured DjangoEmailService (lines 171-172)."""
    with patch("tenxyte.adapters.django.email_service.django_settings") as mock_settings:
        mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
        svc = get_email_service()
    assert isinstance(svc, DjangoEmailService)
    assert svc._default_from_email == "noreply@example.com"
