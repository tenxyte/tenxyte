"""
Tenxyte Models - Security models.

Contains:
- BlacklistedToken: JWT token blacklist for immediate revocation
- AuditLog: Security-sensitive action audit trail
- PasswordHistory: Password reuse prevention
"""

import bcrypt
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

from .base import AutoFieldClass


class BlacklistedToken(models.Model):
    """
    JWT Access Token Blacklist for immediate token revocation.
    Tokens are blacklisted until their natural expiration.
    """

    id = AutoFieldClass(primary_key=True)
    token_jti = models.CharField(max_length=191, unique=True, db_index=True)  # JWT ID
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        on_delete=models.CASCADE,
        related_name="blacklisted_tokens",
        null=True,
        blank=True,
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # When the token would have expired anyway
    reason = models.CharField(max_length=100, blank=True)  # logout, password_change, security, etc.

    class Meta:
        db_table = "blacklisted_tokens"

    def __str__(self):
        return f"Blacklisted: {self.token_jti[:20]}..."

    @classmethod
    def blacklist_token(cls, token_jti: str, expires_at, user=None, reason: str = ""):
        """Add a token to the blacklist."""
        from django.core.cache import cache

        timeout = int((expires_at - timezone.now()).total_seconds())
        if timeout > 0:
            cache.set(f"bl_token_{token_jti}", True, timeout=timeout)

        return cls.objects.get_or_create(
            token_jti=token_jti, defaults={"user": user, "expires_at": expires_at, "reason": reason}
        )

    @classmethod
    def is_blacklisted(cls, token_jti: str) -> bool:
        """Check if a token is blacklisted."""
        from django.core.cache import cache

        if cache.get(f"bl_token_{token_jti}"):
            return True

        token = cls.objects.filter(token_jti=token_jti).first()
        if token:
            timeout = int((token.expires_at - timezone.now()).total_seconds())
            if timeout > 0:
                cache.set(f"bl_token_{token_jti}", True, timeout=timeout)
            return True

        return False

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove expired blacklisted tokens (they're no longer valid anyway)."""
        result = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return result[0]


class AuditLog(models.Model):
    """
    Audit trail for security-sensitive actions.
    """

    id = AutoFieldClass(primary_key=True)

    ACTION_CHOICES = [
        # Authentication
        ("login", "Login"),
        ("login_failed", "Login Failed"),
        ("logout", "Logout"),
        ("logout_all", "Logout All Devices"),
        ("token_refresh", "Token Refresh"),
        # Password
        ("password_change", "Password Changed"),
        ("password_reset_request", "Password Reset Requested"),
        ("password_reset_complete", "Password Reset Completed"),
        # 2FA
        ("2fa_enabled", "2FA Enabled"),
        ("2fa_disabled", "2FA Disabled"),
        ("2fa_backup_used", "2FA Backup Code Used"),
        # Account
        ("account_created", "Account Created"),
        ("account_locked", "Account Locked"),
        ("account_unlocked", "Account Unlocked"),
        ("email_verified", "Email Verified"),
        ("phone_verified", "Phone Verified"),
        # Roles & Permissions
        ("role_assigned", "Role Assigned"),
        ("role_removed", "Role Removed"),
        ("permission_changed", "Permission Changed"),
        # Application
        ("app_created", "Application Created"),
        ("app_credentials_regenerated", "Application Credentials Regenerated"),
        # Account lifecycle
        ("account_deleted", "Account Deleted"),
        # Security
        ("suspicious_activity", "Suspicious Activity Detected"),
        ("session_limit_exceeded", "Session Limit Exceeded"),
        ("device_limit_exceeded", "Device Limit Exceeded"),
        ("new_device_detected", "New Device Detected"),
        # Agent actions (AIRS)
        ("agent_action", "Agent Action Executed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    # --- AIRS Context ---
    agent_token = models.ForeignKey(
        "tenxyte.AgentToken", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    on_behalf_of = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs_agent",
    )
    prompt_trace_id = models.CharField(max_length=128, null=True, blank=True)
    # --------------------
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    application = models.ForeignKey(
        getattr(settings, "TENXYTE_APPLICATION_MODEL", "tenxyte.Application"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    details = models.JSONField(default=dict, blank=True)  # Additional context
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"

    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        ip_address: str = None,
        user_agent: str = "",
        application=None,
        details: dict = None,
        agent_token=None,
        on_behalf_of=None,
        prompt_trace_id: str = None,
    ):
        """Create an audit log entry."""
        import logging
        import json

        logger = logging.getLogger("tenxyte.security.audit")

        # Determine log level based on action severity
        log_level = (
            logging.WARNING
            if any(word in action for word in ["failed", "exceeded", "suspicious", "locked"])
            else logging.INFO
        )

        # F-15 Security check: Ensure details payload doesn't exceed 10KB
        safe_details = details or {}
        try:
            details_str = json.dumps(safe_details)
            if len(details_str.encode("utf-8")) > 10240:  # 10KB limit
                logger.warning(f"[Security F-15] AuditLog details truncated for action {action} (exceeded 10KB)")
                safe_details = {
                    "error": "Payload too large to store",
                    "truncated": True,
                    "original_keys": list(safe_details.keys()),
                }
        except TypeError:
            safe_details = {"error": "Non-serializable payload", "truncated": True}

        log_data = {
            "timestamp": timezone.now().isoformat(),
            "level": "SECURITY",
            "event": action.upper(),
            "ip": ip_address,
            "userAgent": user_agent[:500] if user_agent else "",
            "user_id": str(user.id) if user else None,
            "details": safe_details,
        }

        logger.log(log_level, json.dumps(log_data))

        return cls.objects.create(
            user=user,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else "",
            application=application,
            details=safe_details,
            agent_token=agent_token,
            on_behalf_of=on_behalf_of,
            prompt_trace_id=prompt_trace_id,
        )

    @classmethod
    def get_user_activity(cls, user, limit: int = 100):
        """Get recent activity for a user."""
        return cls.objects.filter(user=user)[:limit]

    @classmethod
    def get_suspicious_activity(cls, hours: int = 24):
        """Get suspicious activity in the last N hours."""
        since = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(
            action__in=["login_failed", "suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"],
            created_at__gte=since,
        )


class PasswordHistory(models.Model):
    """
    Password history to prevent reuse of old passwords.
    """

    id = AutoFieldClass(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL if hasattr(settings, "AUTH_USER_MODEL") else "tenxyte.User",
        on_delete=models.CASCADE,
        related_name="password_history",
    )
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_history"
        ordering = ["-created_at"]

    @classmethod
    def add_password(cls, user, password_hash: str, max_history: int = 5):
        """
        Add a password to history and cleanup old entries.

        Args:
            user: The user
            password_hash: The bcrypt hashed password
            max_history: Maximum passwords to keep in history
        """
        # Add new password
        cls.objects.create(user=user, password_hash=password_hash)

        # Cleanup old entries (keep only max_history)
        old_passwords = cls.objects.filter(user=user).order_by("-created_at")[max_history:]
        if old_passwords:
            cls.objects.filter(id__in=[p.id for p in old_passwords]).delete()

    @classmethod
    def is_password_used(cls, user, raw_password: str, check_count: int = 5) -> bool:
        """
        Check if a password was recently used.

        Args:
            user: The user
            raw_password: The raw password to check
            check_count: How many previous passwords to check

        Returns:
            True if the password was recently used
        """
        recent_passwords = cls.objects.filter(user=user).order_by("-created_at")[:check_count]

        for history in recent_passwords:
            try:
                import hashlib

                pre_hash = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()  # lgtm[py/weak-sensitive-data-hashing] codeql[py/weak-sensitive-data-hashing]
                if bcrypt.checkpw(pre_hash.encode("utf-8"), history.password_hash.encode("utf-8")):

                    return True
            except Exception:
                continue

        return False


# =============================================================================
# SIGNALS
# =============================================================================


@receiver(post_save, sender=AuditLog)
def trigger_audit_log_webhook(sender, instance, created, **kwargs):
    """
    Trigger a webhook when a new AuditLog is created for real-time alerting.
    Configuration: TENXYTE_AUDIT_WEBHOOK_URL in settings.
    """
    if created:
        from ..conf import auth_settings

        webhook_url = getattr(auth_settings, "AUDIT_WEBHOOK_URL", None)
        if webhook_url:
            import threading

            def send_webhook():
                try:
                    import requests

                    payload = {
                        "action": instance.action,
                        "user_id": instance.user_id,
                        "ip_address": instance.ip_address,
                        "created_at": instance.created_at.isoformat(),
                        "details": instance.details,
                    }
                    requests.post(webhook_url, json=payload, timeout=5)
                except Exception as e:
                    import logging

                    logging.getLogger("tenxyte.security.audit").error(f"Failed to send audit webhook: {e}")

            threading.Thread(target=send_webhook, daemon=True).start()
