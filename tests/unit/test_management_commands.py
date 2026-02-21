"""
Tests Phase 5 - Cleanup Command
Couverture de src/tenxyte/management/commands/tenxyte_cleanup.py
"""
import pytest
from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from tenxyte.models import (
    Application, User, BlacklistedToken, OTPCode, RefreshToken, LoginAttempt, AuditLog
)

@pytest.fixture
def cleanup_data():
    """Prépare des données de test expirées et valides."""
    app, _ = Application.create_application(name="CleanupApp")
    user = User.objects.create(email="cleanup@test.com")
    now = timezone.now()
    past = now - timedelta(days=200)

    # 1. BlacklistedToken
    BlacklistedToken.objects.create(token_jti="expired_blk", expires_at=past)
    BlacklistedToken.objects.create(token_jti="valid_blk", expires_at=now + timedelta(days=1))

    # 2. OTPCode
    OTPCode.objects.create(user=user, code="0001", expires_at=past, otp_type="login_2fa")
    OTPCode.objects.create(user=user, code="0002", expires_at=now + timedelta(minutes=10), otp_type="login_2fa")

    # 3. RefreshToken
    RefreshToken.objects.create(user=user, application=app, token="expired_rt", expires_at=past)
    RefreshToken.objects.create(user=user, application=app, token="revoked_rt", expires_at=now + timedelta(days=1), is_revoked=True)
    RefreshToken.objects.create(user=user, application=app, token="valid_rt", expires_at=now + timedelta(days=1), is_revoked=False)

    # 4. LoginAttempt (creer en bypassant auto_now_add via update)
    la_old = LoginAttempt.objects.create(identifier="old@test.com", ip_address="1.1.1.1", application=app)
    LoginAttempt.objects.filter(id=la_old.id).update(created_at=past)
    LoginAttempt.objects.create(identifier="new@test.com", ip_address="1.1.1.1", application=app)

    # 5. AuditLog
    al_old = AuditLog.objects.create(action="old_action")
    AuditLog.objects.filter(id=al_old.id).update(created_at=past)
    AuditLog.objects.create(action="new_action")


@pytest.mark.django_db
class TestCleanupCommand:

    def test_cleanup_dry_run(self, cleanup_data):
        out = StringIO()
        # Ne doit rien supprimer
        call_command('tenxyte_cleanup', '--dry-run', stdout=out)

        assert "DRY RUN - no data will be deleted" in out.getvalue()
        
        # Vérifier que rien n'a été supprimé
        assert BlacklistedToken.objects.count() == 2
        assert OTPCode.objects.count() == 2
        assert RefreshToken.objects.count() == 3
        assert LoginAttempt.objects.count() == 2
        assert AuditLog.objects.count() == 2

    def test_cleanup_normal_execution(self, cleanup_data):
        out = StringIO()
        call_command('tenxyte_cleanup', '--login-attempts-days=90', '--audit-log-days=90', stdout=out)

        # Vérifier les suppressions
        assert BlacklistedToken.objects.count() == 1  # 1 expiré supprimé
        assert OTPCode.objects.count() == 1  # 1 expiré supprimé
        assert RefreshToken.objects.count() == 1  # 1 expiré + 1 révoqué supprimés, reste 1 valide
        assert LoginAttempt.objects.count() == 1  # 1 vieux supprimé
        assert AuditLog.objects.count() == 1  # 1 vieux supprimé

        output = out.getvalue()
        assert "Blacklisted tokens (expired): 1 deleted" in output
        assert "OTP codes (expired or used): 1 deleted" in output
        assert "Refresh tokens (revoked or expired): 2 deleted" in output
        assert "Login attempts (older than 90 days): 1 deleted" in output
        assert "Audit logs (older than 90 days): 1 deleted" in output

    def test_cleanup_skip_audit_logs(self, cleanup_data):
        out = StringIO()
        # --audit-log-days=0 indique de tout garder
        call_command('tenxyte_cleanup', '--audit-log-days=0', stdout=out)

        assert "Audit logs: skipped (--audit-log-days=0)" in out.getvalue()
        assert AuditLog.objects.count() == 2  # Rien n'est supprimé pour AuditLog
