"""
Tests for the tenxyte_purge_audit_logs management command (R19).
"""
import pytest
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from tenxyte.models import AuditLog


@pytest.mark.django_db
class TestPurgeAuditLogsCommand:

    def _create_audit_log(self, days_ago: int):
        """Helper to create an AuditLog with a backdated created_at."""
        log = AuditLog.objects.create(
            action='login',
            ip_address='127.0.0.1',
        )
        # Bypass auto_now_add by using update()
        created_at = timezone.now() - timedelta(days=days_ago)
        AuditLog.objects.filter(pk=log.pk).update(created_at=created_at)
        log.refresh_from_db()
        return log

    def test_purges_old_logs_using_configured_retention(self):
        """Logs older than the configured retention period should be deleted."""
        old_log = self._create_audit_log(days_ago=100)
        recent_log = self._create_audit_log(days_ago=10)

        out = StringIO()
        with patch('tenxyte.management.commands.tenxyte_purge_audit_logs.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOG_RETENTION_DAYS = 90
            call_command('tenxyte_purge_audit_logs', stdout=out)

        assert not AuditLog.objects.filter(pk=old_log.pk).exists(), "Old log should be deleted"
        assert AuditLog.objects.filter(pk=recent_log.pk).exists(), "Recent log should be kept"
        assert 'Purged 1' in out.getvalue()

    def test_dry_run_does_not_delete(self):
        """Dry run should report count but not delete anything."""
        old_log = self._create_audit_log(days_ago=100)

        out = StringIO()
        with patch('tenxyte.management.commands.tenxyte_purge_audit_logs.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOG_RETENTION_DAYS = 90
            call_command('tenxyte_purge_audit_logs', dry_run=True, stdout=out)

        assert AuditLog.objects.filter(pk=old_log.pk).exists(), "Dry run should not delete"
        assert 'DRY RUN' in out.getvalue()
        assert '1 audit log' in out.getvalue()

    def test_days_override(self):
        """--days flag should override the configured retention period."""
        log_30d = self._create_audit_log(days_ago=30)
        log_5d = self._create_audit_log(days_ago=5)

        out = StringIO()
        call_command('tenxyte_purge_audit_logs', days=20, stdout=out)

        assert not AuditLog.objects.filter(pk=log_30d.pk).exists(), "Log older than 20d should be purged"
        assert AuditLog.objects.filter(pk=log_5d.pk).exists(), "Log newer than 20d should remain"

    def test_zero_days_skips_purge(self):
        """--days=0 should print a skip notice and not delete anything."""
        old_log = self._create_audit_log(days_ago=500)

        out = StringIO()
        call_command('tenxyte_purge_audit_logs', days=0, stdout=out)

        assert AuditLog.objects.filter(pk=old_log.pk).exists(), "Log should not be deleted when days=0"
        assert 'skipped' in out.getvalue().lower()

    def test_negative_days_raises_error(self):
        """Negative --days value should raise a CommandError."""
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            call_command('tenxyte_purge_audit_logs', days=-1)

    def test_no_logs_to_purge(self):
        """Command should handle gracefully when no logs match."""
        recent_log = self._create_audit_log(days_ago=5)

        out = StringIO()
        call_command('tenxyte_purge_audit_logs', days=90, stdout=out)

        assert AuditLog.objects.filter(pk=recent_log.pk).exists()
        assert 'Purged 0' in out.getvalue()
