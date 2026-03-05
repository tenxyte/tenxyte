# Periodic Tasks Guide

Tenxyte accumulates time-sensitive records (tokens, OTPs, audit logs) that must be cleaned up regularly to maintain database health and comply with data retention policies. It also includes active monitoring tasks for agent connections.

This guide describes all recommended periodic tasks and how to automate them with **Cron** or **Celery Beat**.

---

## Table of Contents

- [1. Database Cleanup (`tenxyte_cleanup`)](#1-database-cleanup-tenxyte_cleanup)
  - [What it cleans](#what-it-cleans)
  - [Usage & Options](#usage--options)
  - [Automation Examples (Cron & Celery)](#automation-examples)
- [2. Agent Heartbeats Monitoring](#2-agent-heartbeats-monitoring)
  - [Celery Configuration](#celery-configuration)
- [3. Monthly / Security Tasks](#3-monthly--security-tasks)
  - [Encryption Key Rotation](#encryption-key-rotation-tenxyte_totp_encryption_key)
  - [Dependency Vulnerability Scan](#dependency-vulnerability-scan)
- [Summary Table](#summary-table)

---

## 1. Database Cleanup (`tenxyte_cleanup`)

Instead of writing custom management commands or tasks, Tenxyte provides a built-in command to handle all database cleanup in one pass.

### What it cleans

When executed, `tenxyte_cleanup` deletes:
1. **Blacklisted Tokens**: Expired tokens from the JWT blacklist
2. **Magic Links**: Expired passwordless login links
3. **OTP Codes**: Expired or used 2FA verification codes
4. **Refresh Tokens**: Expired or explicitly revoked JWT refresh tokens
5. **Login Attempts**: Old login attempts (used for rate-limiting and lockout)
6. **Audit Logs**: Old security audit events (depending on policy)

### Usage & Options

```bash
python manage.py tenxyte_cleanup
```

By default, it keeps Login Attempts for **90 days** and Audit Logs for **365 days**. You can override these retentions:

| Option | Default | Description |
|---|---|---|
| `--login-attempts-days` | 90 | Days before deleting LoginAttempt (0 = keep forever) |
| `--audit-log-days` | 365 | Days before deleting AuditLog (0 = keep forever) |
| `--dry-run` | - | Simulates the cleanup without deleting anything |

> **Compliance Note:** GDPR / SOC 2 may impose a strict maximum retention window for Audit Logs (e.g., 90 days), but also a minimum. Choose a value that complies with both.

### Automation Examples

You should run this command **daily** (e.g., at 3:00 AM) to keep the database size under control.

**Cron alternative:**
```cron
# Run daily at 03:00 AM
0 3 * * * /path/to/venv/bin/python manage.py tenxyte_cleanup
```

**Celery Beat alternative:**
```python
# myapp/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def run_tenxyte_cleanup():
    call_command('tenxyte_cleanup')
```

---

## 2. Agent Heartbeats Monitoring

If you use the **AIRS module** with `AgentTokens` that require regular heartbeats (`heartbeat_required_every`), you must run the monitoring task continuously.

Without this task, an agent might disconnect forcefully without sending a suspension signal, and the token would remain indefinitely Active.

### Celery Configuration

Tenxyte provides the `@shared_task` directly. You must schedule it to run **every minute** via Celery Beat:

```python
# settings.py or celery.py schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Run every minute to suspend agents missing heartbeats
    'check-agent-heartbeats': {
        'task': 'tenxyte.tasks.agent_tasks.check_agent_heartbeats',
        'schedule': crontab(minute='*'),
    },
    
    # Run daily DB cleanup
    'daily-db-cleanup': {
        'task': 'myapp.tasks.run_tenxyte_cleanup',
        'schedule': crontab(hour=3, minute=0),
    },
}
```

When this task runs, it finds all `AgentToken` objects with missing heartbeats and automatically changes their status to `SUSPENDED` with the reason `HEARTBEAT_MISSING`. It also logs a security warning.

---

## 3. Monthly / Security Tasks

### Encryption Key Rotation (`TENXYTE_TOTP_ENCRYPTION_KEY`)

If you use `TENXYTE_TOTP_ENCRYPTION_KEY` for TOTP secret encryption, plan periodic key rotation.
Because Tenxyte uses standard `cryptography.fernet.Fernet` for TOTP secrets, you will need a custom script to:

1. Decrypt all `totp_secret` fields in the `User` model with the old key.
2. Re-encrypt them with the new key.
3. Update `TENXYTE_TOTP_ENCRYPTION_KEY` in your environment variables.

### Dependency Vulnerability Scan

Run in CI or manually every month:

```bash
pip-audit
safety check
bandit -r src/tenxyte/
```

---

## Summary Table

| Task | Execution | Frequency | Impact |
|---|---|---|---|
| Check Agent Heartbeats | `tenxyte.tasks.agent_tasks.check_agent_heartbeats` | Every minute | Suspending disconnected bots |
| Database Cleanup | `python manage.py tenxyte_cleanup` | Daily | Data privacy & DB size |
| Key rotation | Custom script | Monthly / Yearly | Security |
| Dependency scan | `pip-audit` | Monthly or CI | Security |
