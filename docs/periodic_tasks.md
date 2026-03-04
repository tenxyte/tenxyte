# Periodic Tasks Guide

Tenxyte accumulates time-sensitive records (tokens, OTPs, audit logs) that must be cleaned up regularly to maintain database health and comply with data retention policies.

This guide describes all recommended periodic tasks and how to automate them with **Celery Beat**, **APScheduler**, or **cron**.

---

## Daily Tasks

### 1. Cleanup Expired & Revoked Refresh Tokens

Revoked or expired `RefreshToken` records accumulate in the database. Remove them daily.

**Celery task:**
```python
# myapp/tasks.py
from celery import shared_task

@shared_task
def cleanup_refresh_tokens():
    from tenxyte.models import RefreshToken
    from django.utils import timezone

    count = RefreshToken.objects.filter(is_revoked=True).delete()[0]
    count += RefreshToken.objects.filter(
        expires_at__lt=timezone.now(), is_revoked=False
    ).update(is_revoked=True)
    return f"Cleaned {count} expired/revoked refresh tokens"
```

**Cron alternative:**
```cron
0 3 * * * /path/to/venv/bin/python manage.py cleanup_tokens
```

---

### 2. Cleanup Expired OTP Codes

Unused `OTPCode` entries linger after expiry.

```python
@shared_task
def cleanup_expired_otps():
    from tenxyte.models import OTPCode
    from django.utils import timezone

    count, _ = OTPCode.objects.filter(expires_at__lt=timezone.now()).delete()
    return f"Deleted {count} expired OTP codes"
```

---

### 3. Audit Log Retention

Define a maximum retention window to comply with GDPR / SOC 2 (which may impose both minimum *and* maximum retention periods).

```python
@shared_task
def cleanup_audit_logs():
    from tenxyte.models import AuditLog
    from django.utils.timezone import now
    from datetime import timedelta

    RETENTION_DAYS = 90  # adjust to your policy
    count, _ = AuditLog.objects.filter(
        created_at__lt=now() - timedelta(days=RETENTION_DAYS)
    ).delete()
    return f"Deleted {count} audit log entries older than {RETENTION_DAYS} days"
```

> **Note:** Some regulations require a *minimum* retention period (e.g. keep logs for at least 1 year). Ensure your retention window satisfies both the minimum and maximum requirements.

---

## Weekly Tasks

### 4. Cleanup Expired AgentTokens (AIRS)

Remove expired AIRS agent tokens.

```python
@shared_task
def cleanup_agent_tokens():
    from tenxyte.models.agent import AgentToken
    from django.utils import timezone

    count, _ = AgentToken.objects.filter(expires_at__lt=timezone.now()).delete()
    return f"Deleted {count} expired agent tokens"
```

---

### 5. Cleanup Expired Magic Links & Verification Tokens

Depending on your models (`UnverifiedEmail`, `PhoneVerification`, etc.):

```python
@shared_task
def cleanup_verification_tokens():
    from tenxyte.models import UnverifiedEmail
    from django.utils import timezone

    count, _ = UnverifiedEmail.objects.filter(expires_at__lt=timezone.now()).delete()
    return f"Deleted {count} expired verification tokens"
```

---

### 6. Archive Old Login Attempts

`LoginAttempt` records do not need indefinite retention (they are used only for lockout logic).

```python
@shared_task
def cleanup_login_attempts():
    from tenxyte.models import LoginAttempt
    from django.utils.timezone import now
    from datetime import timedelta

    count, _ = LoginAttempt.objects.filter(
        attempted_at__lt=now() - timedelta(days=30)
    ).delete()
    return f"Deleted {count} old login attempts"
```

---

## Monthly / Security Tasks

### 7. Encryption Key Rotation (`FIELD_ENCRYPTION_KEY`)

If you use `FIELD_ENCRYPTION_KEY` for TOTP secret encryption, plan periodic key rotation:

1. Decrypt all encrypted fields with the old key
2. Re-encrypt with the new key
3. Update `FIELD_ENCRYPTION_KEY` in `settings.py`

See the [django-cryptography key rotation docs](https://django-cryptography.readthedocs.io/en/latest/key-rotation.html) for the migration script.

---

### 8. Audit Long-Lived AgentTokens

Identify AIRS tokens with a lifetime > 24 h that have not been used recently:

```python
from tenxyte.models.agent import AgentToken
from django.utils import timezone
from datetime import timedelta

stale = AgentToken.objects.filter(
    expires_at__gt=timezone.now() + timedelta(hours=24),
    last_used_at__lt=timezone.now() - timedelta(days=7)
)
# Review or revoke stale tokens
stale.update(is_revoked=True)
```

---

### 9. Dependency Vulnerability Scan

Run in CI or manually:

```bash
pip-audit
safety check
bandit -r src/tenxyte/
```

---

## Celery Beat Configuration

Add all tasks to your Celery Beat schedule:

```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Daily at 3:00 AM
    'tenxyte-cleanup-refresh-tokens': {
        'task': 'myapp.tasks.cleanup_refresh_tokens',
        'schedule': crontab(hour=3, minute=0),
    },
    'tenxyte-cleanup-otps': {
        'task': 'myapp.tasks.cleanup_expired_otps',
        'schedule': crontab(hour=3, minute=10),
    },
    'tenxyte-cleanup-audit-logs': {
        'task': 'myapp.tasks.cleanup_audit_logs',
        'schedule': crontab(hour=3, minute=20),
    },
    # Weekly on Monday at 4:00 AM
    'tenxyte-cleanup-agent-tokens': {
        'task': 'myapp.tasks.cleanup_agent_tokens',
        'schedule': crontab(hour=4, minute=0, day_of_week='monday'),
    },
    'tenxyte-cleanup-login-attempts': {
        'task': 'myapp.tasks.cleanup_login_attempts',
        'schedule': crontab(hour=4, minute=10, day_of_week='monday'),
    },
}
```

---

## Summary Table

| Task | Frequency | Impact |
|---|---|---|
| Cleanup refresh tokens | Daily | DB size |
| Cleanup expired OTPs | Daily | DB size |
| Audit log retention | Daily | Compliance |
| Cleanup agent tokens | Weekly | DB size |
| Cleanup login attempts | Weekly | DB size |
| Cleanup verification tokens | Weekly | DB size |
| Key rotation | Monthly | Security |
| Audit long-lived agent tokens | Monthly | Security |
| Dependency scan | Monthly or in CI | Security |
