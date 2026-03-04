"""
Tenxyte — Periodic Maintenance and Security Tasks
========================================================

This document describes the tasks that must be executed periodically
to maintain the health and security of your Tenxyte installation.

Possible integration with Celery Beat, APScheduler, or cron.

R15 Audit: Document and automate periodic cleanup tasks.
"""

# ============================================================================
# DAILY TASKS
# ============================================================================

# 1. Cleanup of expired refresh tokens
# ----------------------------------------
# Revoked or expired RefreshTokens accumulate in the database.
# This Django management command deletes obsolete entries.
#
# Celery Beat (recommended):
#   from celery import shared_task
#   @shared_task
#   def cleanup_refresh_tokens():
#       from tenxyte.models import RefreshToken
#       from django.utils import timezone
#       count = RefreshToken.objects.filter(
#           is_revoked=True
#       ).delete()[0]
#       count += RefreshToken.objects.filter(
#           expires_at__lt=timezone.now(), is_revoked=False
#       ).update(is_revoked=True)
#       return f"Cleaned {count} expired/revoked refresh tokens"
#
# Alternative Cron:
#   0 3 * * * python manage.py cleanup_tokens

# 2. Cleanup of old audit logs (retention)
# -------------------------------------------------
# Define a retention policy to avoid unlimited growth.
# Regulations (GDPR, SOC 2) may impose both minimum AND maximum retention.
#
# Example: keeping 90 days of audit logs
#   from tenxyte.models import AuditLog
#   from django.utils.timezone import now
#   from datetime import timedelta
#   AuditLog.objects.filter(created_at__lt=now() - timedelta(days=90)).delete()

# 3. Cleanup of expired OTPs
# -----------------------------
# Unused OTPCodes accumulate.
#   from tenxyte.models import OTPCode
#   from django.utils import timezone
#   OTPCode.objects.filter(expires_at__lt=timezone.now()).delete()


# ============================================================================
# WEEKLY TASKS
# ============================================================================

# 4. Cleanup of expired or revoked AgentTokens (AIRS)
# --------------------------------------------------------
#   from tenxyte.models.agent import AgentToken
#   from django.utils import timezone
#   AgentToken.objects.filter(
#       expires_at__lt=timezone.now()  # expired
#   ).delete()

# 5. Cleanup of expired MagicLink / verification tokens
# ------------------------------------------------------------
# Depending on your models: UnverifiedEmail, PhoneVerification, etc.

# 6. Archiving of old LoginAttempts
# ----------------------------------------
# LoginAttempts don't need to be kept indefinitely.
#   from tenxyte.models import LoginAttempt
#   from django.utils.timezone import now
#   from datetime import timedelta
#   LoginAttempt.objects.filter(attempted_at__lt=now() - timedelta(days=30)).delete()


# ============================================================================
# MONTHLY / SECURITY TASKS
# ============================================================================

# 7. FIELD_ENCRYPTION_KEY Rotation
# -----------------------------------------
# If you use django-cryptography for totp_secret encryption (R2),
# plan periodic key rotation. Procedure:
# 1. Decrypt all fields with the old key
# 2. Encrypt with the new key
# 3. Update FIELD_ENCRYPTION_KEY in settings.py
# See: https://django-cryptography.readthedocs.io/en/latest/key-rotation.html

# 8. Audit of long-lived AgentTokens
# -----------------------------------------------------
# Identify AIRS tokens with life > 24h that haven't been used:
#   from tenxyte.models.agent import AgentToken
#   from django.utils import timezone
#   from datetime import timedelta
#   stale = AgentToken.objects.filter(
#       expires_at__gt=timezone.now() + timedelta(hours=24),
#       last_used_at__lt=timezone.now() - timedelta(days=7)
#   )

# 9. Vulnerable dependency check
# --------------------------------------------
# Run manually or in CI (R3, R7 audit):
#   pip-audit
#   safety check
#   bandit -r src/tenxyte/


# ============================================================================
# CELERY BEAT CONFIGURATION (example)
# ============================================================================

# CELERY_BEAT_SCHEDULE = {
#     'tenxyte-cleanup-daily': {
#         'task': 'myapp.tasks.tenxyte_daily_cleanup',
#         'schedule': crontab(hour=3, minute=0),  # 3 AM
#     },
#     'tenxyte-cleanup-weekly': {
#         'task': 'myapp.tasks.tenxyte_weekly_cleanup',
#         'schedule': crontab(hour=4, minute=0, day_of_week='monday'),
#     },
# }
