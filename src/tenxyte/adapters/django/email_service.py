"""
Django Email Service Adapter for Tenxyte Core.

This module provides an EmailService implementation using Django's email backend.
"""

from typing import List, Optional

from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings

from tenxyte.core.email_service import EmailService, EmailAttachment


class DjangoEmailService(EmailService):
    """
    Email service implementation using Django's email framework.

    This adapter uses Django's email backends (SMTP, console, file, etc.)
    configured via Django settings.

    Example:
        # In settings.py
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.gmail.com'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = 'your-email@gmail.com'
        EMAIL_HOST_PASSWORD = 'your-password'
        DEFAULT_FROM_EMAIL = 'noreply@example.com'

        # Usage
        from tenxyte.adapters.django import DjangoEmailService

        email_service = DjangoEmailService()
        email_service.send(
            to_email='user@example.com',
            subject='Hello',
            body='Welcome!',
        )
    """

    def __init__(self, default_from_email: Optional[str] = None):
        """
        Initialize the Django email service.

        Args:
            default_from_email: Default sender email. Uses Django's
                DEFAULT_FROM_EMAIL setting if not provided.
        """
        self._default_from_email = default_from_email

    def _get_from_email(self, from_email: Optional[str] = None) -> str:
        """Get the sender email address."""
        if from_email:
            return from_email
        if self._default_from_email:
            return self._default_from_email
        return getattr(django_settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> bool:
        """
        Send an email using Django's email framework.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_email: Sender email (uses default if not provided)
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            attachments: List of attachments

        Returns:
            True if email was sent successfully
        """
        try:
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=self._get_from_email(from_email),
                to=[to_email],
                cc=cc or [],
                bcc=bcc or [],
            )

            # Add HTML alternative if provided
            if html_body:
                msg.attach_alternative(html_body, "text/html")

            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    msg.attach(
                        attachment.filename,
                        attachment.content,
                        attachment.content_type,
                    )

            # Send the email
            msg.send()
            return True

        except Exception as e:
            # Log the error but don't expose details to caller
            # In production, you should use proper logging
            print(f"Failed to send email: {e}")
            return False

    def send_mass_email(
        self,
        recipients: List[tuple],
        from_email: Optional[str] = None,
    ) -> int:
        """
        Send mass emails efficiently using Django's send_mass_mail.

        Args:
            recipients: List of (subject, message, to_email) tuples
            from_email: Default sender email

        Returns:
            Number of emails sent
        """
        from django.core.mail import send_mass_mail

        sender = self._get_from_email(from_email)

        # Format for send_mass_mail: (subject, message, from_email, recipient_list)
        messages = [(subject, message, sender, [to_email]) for subject, message, to_email in recipients]

        try:
            return send_mass_mail(messages, fail_silently=False)
        except Exception as e:
            print(f"Failed to send mass emails: {e}")
            return 0


# Convenience function for getting configured email service
def get_email_service() -> DjangoEmailService:
    """
    Get a DjangoEmailService instance with settings from Django config.

    Returns:
        Configured DjangoEmailService instance

    Example:
        from tenxyte.adapters.django.email_service import get_email_service

        email_service = get_email_service()
        email_service.send_magic_link(
            to_email='user@example.com',
            magic_link_url='https://example.com/magic/abc123',
        )
    """
    default_from = getattr(django_settings, "DEFAULT_FROM_EMAIL", None)
    return DjangoEmailService(default_from_email=default_from)
