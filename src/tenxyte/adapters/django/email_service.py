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

    def _generate_text_alternative(self, html_content: str) -> str:
        """
        Generate a plain text alternative from HTML content.

        Args:
            html_content: HTML content

        Returns:
            Plain text version
        """
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Decode HTML entities
        import html

        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def send_magic_link(
        self,
        to_email: str,
        magic_link_url: str,
        expires_in_minutes: int = 15,
    ) -> bool:
        """
        Send a magic link email.

        Args:
            to_email: Recipient email
            magic_link_url: The magic link URL
            expires_in_minutes: Link expiration time in minutes

        Returns:
            True if email was sent successfully
        """
        subject = "Your Magic Link"
        body = f"Click the link below to sign in:\n\n{magic_link_url}\n\nThis link expires in {expires_in_minutes} minutes."
        html_body = f"<p>Click the link below to sign in:</p><p><a href='{magic_link_url}'>Sign In</a></p><p>This link expires in {expires_in_minutes} minutes.</p>"

        return self.send(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
        )

    def _send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send an email using a Django template.

        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Path to the Django template
            context: Template context dictionary
            from_email: Sender email (uses default if not provided)

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            from django.template.loader import render_to_string
            from django.core.mail import EmailMultiAlternatives

            # Render the template
            html_content = render_to_string(template_name, context)

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=html_content,  # Fallback plain text
                from_email=self._get_from_email(from_email),
                to=[to_email],
            )
            email.attach_alternative(html_content, "text/html")

            # Send
            email.send()
            return True

        except Exception:
            # Log error but don't raise - return False to indicate failure
            return False

    def send_account_deletion_confirmation(self, deletion_request) -> bool:
        """Send email confirming account deletion request."""
        try:
            from django.contrib.sites.shortcuts import get_current_site
            from django.http import HttpRequest

            request = HttpRequest()
            site = get_current_site(request)

            cancel_url = f"https://{site.domain}/account/deletion/cancel/{deletion_request.id}/"

            context = {
                "user": deletion_request.user,
                "cancel_url": cancel_url,
            }

            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject="Account Deletion Request Confirmation",
                template_name="emails/account_deletion_confirmation.html",
                context=context,
            )
        except Exception:
            return False

    def send_account_deletion_confirmed(self, deletion_request) -> bool:
        """Send email when account deletion is confirmed."""
        try:
            from django.contrib.sites.shortcuts import get_current_site
            from django.http import HttpRequest
            from django.utils import timezone

            request = HttpRequest()
            site = get_current_site(request)

            cancel_url = f"https://{site.domain}/account/deletion/cancel/{deletion_request.id}/"

            # Calculate days remaining
            days_remaining = 0
            if deletion_request.grace_period_ends_at:
                delta = deletion_request.grace_period_ends_at - timezone.now()
                days_remaining = max(0, delta.days)

            context = {
                "user": deletion_request.user,
                "cancel_url": cancel_url,
                "days_remaining": days_remaining,
            }

            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject="Account Deletion Confirmed",
                template_name="emails/account_deletion_confirmed.html",
                context=context,
            )
        except Exception:
            return False

    def send_account_deletion_completed(self, deletion_request) -> bool:
        """Send email when account deletion is completed."""
        try:
            context = {
                "user": deletion_request.user,
                "user_email": deletion_request.user.email,
                "requested_at": deletion_request.requested_at,
                "reason": getattr(deletion_request, "reason", ""),
            }

            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject="Account Deletion Completed",
                template_name="emails/account_deletion_completed.html",
                context=context,
            )
        except Exception:
            return False

    def send_deletion_request_rejected(self, deletion_request) -> bool:
        """Send email when deletion request is rejected."""
        try:
            from django.contrib.sites.shortcuts import get_current_site
            from django.http import HttpRequest

            request = HttpRequest()
            site = get_current_site(request)

            login_url = f"https://{site.domain}/login/"

            context = {
                "user": deletion_request.user,
                "login_url": login_url,
                "admin_notes": getattr(deletion_request, "admin_notes", ""),
                "reason": getattr(deletion_request, "rejection_reason", "No reason provided"),
            }

            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject="Account Deletion Request Rejected",
                template_name="emails/account_deletion_rejected.html",
                context=context,
            )
        except Exception:
            return False

    def send_security_alert_email(self, user, device_info: str, ip_address: str) -> bool:
        """Send security alert email for new device login."""
        try:
            from django.utils import timezone

            context = {
                "user": user,
                "device_info": device_info,
                "ip_address": ip_address,
                "login_time": timezone.now(),
            }

            return self._send_template_email(
                to_email=user.email,
                subject="New Device Login Alert",
                template_name="emails/security_alert.html",
                context=context,
            )
        except Exception:
            return False


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
