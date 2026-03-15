"""
Email service implementations for Tenxyte Core.

This module provides base email service implementations that can be used
with any adapter (Django, FastAPI, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EmailTemplate(str, Enum):
    """Built-in email templates."""

    MAGIC_LINK = "magic_link"
    TWO_FACTOR_CODE = "two_factor_code"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    SECURITY_ALERT = "security_alert"


@dataclass
class EmailAttachment:
    """Email attachment data."""

    filename: str
    content: bytes
    content_type: str


class EmailService(ABC):
    """
    Abstract base class for email services.

    Implementations must provide concrete methods for sending emails
    regardless of the underlying email backend (SMTP, SendGrid, AWS SES, etc.).
    """

    @abstractmethod
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
        Send a basic email.

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
        pass

    def send_magic_link(
        self,
        to_email: str,
        magic_link_url: str,
        expires_in_minutes: int = 15,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send a magic link email for passwordless authentication.

        Args:
            to_email: Recipient email address
            magic_link_url: Full URL of the magic link
            expires_in_minutes: How long the link is valid
            from_email: Sender email

        Returns:
            True if email was sent successfully
        """
        subject = "Your magic sign-in link"
        body = f"""
Hello,

Click the link below to sign in. This link will expire in {expires_in_minutes} minutes.

{magic_link_url}

If you didn't request this link, you can safely ignore this email.
"""
        html_body = f"""
<!DOCTYPE html>
<html>
<body>
    <p>Hello,</p>
    <p>Click the button below to sign in. This link will expire in {expires_in_minutes} minutes.</p>
    <p><a href="{magic_link_url}" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">Sign In</a></p>
    <p>Or copy this link: {magic_link_url}</p>
    <p>If you didn't request this link, you can safely ignore this email.</p>
</body>
</html>
"""
        return self.send(to_email, subject, body, html_body, from_email)

    def send_two_factor_code(
        self,
        to_email: str,
        code: str,
        method: str = "email",
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send a 2FA verification code.

        Args:
            to_email: Recipient email address
            code: The verification code
            method: 2FA method (email, sms backup, etc.)
            from_email: Sender email

        Returns:
            True if email was sent successfully
        """
        subject = "Your verification code"
        body = f"""
Hello,

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please secure your account immediately.
"""
        html_body = f"""
<!DOCTYPE html>
<html>
<body>
    <p>Hello,</p>
    <p>Your verification code is:</p>
    <h1 style="font-size: 32px; letter-spacing: 4px;">{code}</h1>
    <p>This code will expire in 10 minutes.</p>
    <p>If you didn't request this code, please secure your account immediately.</p>
</body>
</html>
"""
        return self.send(to_email, subject, body, html_body, from_email)

    def send_password_reset(
        self,
        to_email: str,
        reset_url: str,
        expires_in_hours: int = 24,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send a password reset email.

        Args:
            to_email: Recipient email address
            reset_url: Full URL for password reset
            expires_in_hours: How long the link is valid
            from_email: Sender email

        Returns:
            True if email was sent successfully
        """
        subject = "Password reset request"
        body = f"""
Hello,

We received a request to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in {expires_in_hours} hours.

If you didn't request a password reset, you can safely ignore this email.
"""
        html_body = f"""
<!DOCTYPE html>
<html>
<body>
    <p>Hello,</p>
    <p>We received a request to reset your password. Click the button below to set a new password:</p>
    <p><a href="{reset_url}" style="padding: 12px 24px; background: #dc3545; color: white; text-decoration: none; border-radius: 4px;">Reset Password</a></p>
    <p>This link will expire in {expires_in_hours} hours.</p>
    <p>If you didn't request a password reset, you can safely ignore this email.</p>
</body>
</html>
"""
        return self.send(to_email, subject, body, html_body, from_email)

    def send_welcome(
        self,
        to_email: str,
        first_name: Optional[str] = None,
        login_url: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send a welcome email to new users.

        Args:
            to_email: Recipient email address
            first_name: User's first name for personalization
            login_url: Optional login URL to include
            from_email: Sender email

        Returns:
            True if email was sent successfully
        """
        greeting = f"Hello {first_name}," if first_name else "Hello,"
        subject = "Welcome!"

        login_section = f"\nYou can sign in at: {login_url}\n" if login_url else ""

        body = f"""
{greeting}

Welcome! Your account has been created successfully.
{login_section}

If you have any questions, please don't hesitate to contact us.
"""

        login_html = (
            f'<p><a href="{login_url}" style="padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Sign In</a></p>'
            if login_url
            else ""
        )

        html_body = f"""
<!DOCTYPE html>
<html>
<body>
    <p>{greeting}</p>
    <p>Welcome! Your account has been created successfully.</p>
    {login_html}
    <p>If you have any questions, please don't hesitate to contact us.</p>
</body>
</html>
"""
        return self.send(to_email, subject, body, html_body, from_email)

    def send_security_alert(
        self,
        to_email: str,
        alert_type: str,
        details: Dict[str, Any],
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send a security alert email.

        Args:
            to_email: Recipient email address
            alert_type: Type of security event (login, password_change, etc.)
            details: Dictionary with event details
            from_email: Sender email

        Returns:
            True if email was sent successfully
        """
        subject = f"Security alert: {alert_type}"

        details_text = "\n".join([f"{k}: {v}" for k, v in details.items()])

        body = f"""
Hello,

We detected a security event on your account:

Event: {alert_type}
{details_text}

If this was you, you can ignore this email. If you don't recognize this activity, please secure your account immediately.
"""

        details_html = "\n".join([f"<tr><td><strong>{k}:</strong></td><td>{v}</td></tr>" for k, v in details.items()])

        html_body = f"""
<!DOCTYPE html>
<html>
<body>
    <p>Hello,</p>
    <p>We detected a security event on your account:</p>
    <table>
        <tr><td><strong>Event:</strong></td><td>{alert_type}</td></tr>
        {details_html}
    </table>
    <p>If this was you, you can ignore this email. If you don't recognize this activity, please secure your account immediately.</p>
</body>
</html>
"""
        return self.send(to_email, subject, body, html_body, from_email)


class ConsoleEmailService(EmailService):
    """
    Email service that prints emails to console.

    Useful for development and testing.
    """

    def __init__(self, prefix: str = "[EMAIL]"):
        self.prefix = prefix

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
        """Print email to console instead of sending."""
        print(f"\n{'='*60}")
        print(f"{self.prefix} TO: {to_email}")
        print(f"{self.prefix} FROM: {from_email or 'default'}")
        print(f"{self.prefix} SUBJECT: {subject}")
        if cc:
            print(f"{self.prefix} CC: {', '.join(cc)}")
        if bcc:
            print(f"{self.prefix} BCC: {', '.join(bcc)}")
        if attachments:
            print(f"{self.prefix} ATTACHMENTS: {[a.filename for a in attachments]}")
        print(f"{'='*60}")
        print(body)
        if html_body:
            print(f"\n{self.prefix} HTML VERSION:")
            print(html_body)
        print(f"{'='*60}\n")
        return True
