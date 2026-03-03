import pytest
from io import StringIO
from datetime import timedelta
from django.utils import timezone
from django.core.management import call_command
from tenxyte.models import (
    BlacklistedToken, OTPCode, RefreshToken, LoginAttempt, AuditLog, User, Application
)

@pytest.fixture
def cleanup_data(db):
    now = timezone.now()
    user = User.objects.create(email="cleanup@test.com", is_active=True)
    app, _ = Application.objects.get_or_create(name="Cleanup App")

    # 1. BlacklistedToken
    BlacklistedToken.objects.create(token_jti="expired_token", expires_at=now - timedelta(days=1))
    BlacklistedToken.objects.create(token_jti="valid_token", expires_at=now + timedelta(days=1))

    # 2. OTPCode
    OTPCode.objects.create(user=user, code="111111", expires_at=now - timedelta(days=1))
    OTPCode.objects.create(user=user, code="222222", expires_at=now + timedelta(days=1))

    # 3. RefreshToken
    RefreshToken.objects.create(user=user, application=app, token="expired_rt", expires_at=now - timedelta(days=1), is_revoked=False)
    RefreshToken.objects.create(user=user, application=app, token="revoked_rt", expires_at=now + timedelta(days=1), is_revoked=True)
    RefreshToken.objects.create(user=user, application=app, token="valid_rt", expires_at=now + timedelta(days=1), is_revoked=False)

    # 4. LoginAttempt (older than 90 days)
    old_attempt = LoginAttempt.objects.create(identifier="old", ip_address="1.1.1.1", application=app, success=False)
    old_attempt.created_at = now - timedelta(days=100)
    old_attempt.save()

    recent_attempt = LoginAttempt.objects.create(identifier="recent", ip_address="1.1.1.1", application=app, success=False)

    # 5. AuditLog (older than 365 days)
    old_log = AuditLog.objects.create(user=user, action="login", ip_address="1.1.1.1", details={})
    old_log.created_at = now - timedelta(days=400)
    old_log.save()

    recent_log = AuditLog.objects.create(user=user, action="login", ip_address="1.1.1.1", details={})

    return user, app

@pytest.mark.django_db
def test_tenxyte_cleanup_normal(cleanup_data):
    out = StringIO()
    call_command('tenxyte_cleanup', stdout=out)
    output = out.getvalue()
    
    assert 'Nettoyage termine avec succes.' in output
    assert BlacklistedToken.objects.count() == 1
    assert OTPCode.objects.count() == 1
    assert RefreshToken.objects.count() == 1  # only valid_rt remains
    assert LoginAttempt.objects.count() == 1  # only recent attempt
    assert AuditLog.objects.count() == 1

@pytest.mark.django_db
def test_tenxyte_cleanup_dry_run(cleanup_data):
    out = StringIO()
    call_command('tenxyte_cleanup', '--dry-run', stdout=out)
    output = out.getvalue()
    
    assert 'DRY RUN - no data will be deleted' in output
    assert 'simulation only' in output
    
    assert BlacklistedToken.objects.count() == 2
    assert OTPCode.objects.count() == 2
    assert RefreshToken.objects.count() == 3
    assert LoginAttempt.objects.count() == 2
    assert AuditLog.objects.count() == 2

@pytest.mark.django_db
def test_tenxyte_cleanup_custom_days_and_skip_audit(cleanup_data):
    out = StringIO()
    # Skip audit logs by passing --audit-log-days 0
    # Make login attempt cutoff 5 days instead of 90
    call_command('tenxyte_cleanup', '--audit-log-days', '0', '--login-attempts-days', '5', stdout=out)
    output = out.getvalue()
    
    assert 'Audit logs: skipped' in output
    assert AuditLog.objects.count() == 2  # Not deleted!
