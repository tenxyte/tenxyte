"""
Tenxyte Models - GDPR compliance models.

Contains:
- AccountDeletionRequest: Account deletion workflow (RGPD/GDPR)
"""

import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .base import AutoFieldClass


class AccountDeletionRequest(models.Model):
    """
    Demande de suppression de compte (RGPD).

    Workflow:
    1. User requests deletion → status=PENDING
    2. Email confirmation sent → status=CONFIRMATION_SENT
    3. User confirms → status=CONFIRMED (grace period starts)
    4. Grace period expires → status=COMPLETED (account deleted)
    5. User cancels → status=CANCELLED
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmation_sent", "Confirmation Sent"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = AutoFieldClass(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Token de confirmation sécurisé
    confirmation_token = models.CharField(max_length=64, unique=True, help_text="Secure token for email confirmation")

    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    reason = models.TextField(blank=True, help_text="Optional reason for deletion request")

    # Admin notes
    admin_notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_deletions",
    )

    class Meta:
        db_table = "account_deletion_requests"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "grace_period_ends_at"]),
            models.Index(fields=["confirmation_token"]),
        ]

    def __str__(self):
        return f"Deletion request for {self.user.email} - {self.status}"

    @classmethod
    def create_request(cls, user, ip_address=None, user_agent="", reason=""):
        """Create a new deletion request with secure token."""
        # Cancel any existing pending requests
        cls.objects.filter(user=user, status__in=["pending", "confirmation_sent", "confirmed"]).update(
            status="cancelled"
        )

        return cls.objects.create(
            user=user,
            confirmation_token=secrets.token_urlsafe(48),
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason,
        )

    def send_confirmation_email(self):
        """Send confirmation email to user."""
        from tenxyte.adapters.django.email_service import DjangoEmailService

        self.status = "confirmation_sent"
        self.save()

        try:
            email_service = DjangoEmailService()
            email_service.send_account_deletion_confirmation(self)
            return True
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Error sending deletion confirmation email: {e}", exc_info=True)
            from .security import AuditLog

            AuditLog.objects.create(
                action="deletion_confirmation_email_failed",
                user=self.user,
                ip_address="system",
                details={"request_id": self.id, "error": "Internal server error"},
            )
            return False

    def confirm_request(self, grace_period_days=30):
        """Confirm the deletion request and start grace period."""
        self.status = "confirmed"
        self.confirmed_at = timezone.now()
        self.grace_period_ends_at = timezone.now() + timedelta(days=grace_period_days)
        self.save()

        return True

    def execute_deletion(self, processed_by=None):
        """Execute the actual account deletion."""
        if self.status != "confirmed":
            return False

        # Soft delete the user account
        success = self.user.soft_delete()

        if success:
            self.status = "completed"
            self.completed_at = timezone.now()
            self.processed_by = processed_by
            self.save()

            # Envoyer email de notification de completion
            try:
                from tenxyte.adapters.django.email_service import DjangoEmailService

                email_service = DjangoEmailService()
                email_service.send_account_deletion_completed(self)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error sending deletion completion email: {e}", exc_info=True)
                from .security import AuditLog

                AuditLog.objects.create(
                    action="deletion_completion_email_failed",
                    user=self.user,
                    ip_address="system",
                    details={"request_id": self.id, "error": "Internal server error"},
                )

            return True

        return False

    def cancel_request(self):
        """Cancel the deletion request."""
        self.status = "cancelled"
        self.save()
        return True

    def is_grace_period_expired(self):
        """Check if the grace period has expired."""
        if not self.grace_period_ends_at:
            return False
        return timezone.now() > self.grace_period_ends_at

    @classmethod
    def get_expired_requests(cls):
        """Get all confirmed requests past their grace period."""
        return cls.objects.filter(status="confirmed", grace_period_ends_at__lt=timezone.now())
