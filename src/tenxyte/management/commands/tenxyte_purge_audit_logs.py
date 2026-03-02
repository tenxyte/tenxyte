"""
Tenxyte - Dedicated audit log purge command (R19).

Purges AuditLog entries older than TENXYTE_AUDIT_LOG_RETENTION_DAYS days.
The retention period defaults to 90 days and is configurable via settings.

Usage:
    python manage.py tenxyte_purge_audit_logs
    python manage.py tenxyte_purge_audit_logs --days 30
    python manage.py tenxyte_purge_audit_logs --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tenxyte.conf import auth_settings
from tenxyte.models import AuditLog


class Command(BaseCommand):
    help = (
        'Purge AuditLog entries older than the configured retention period '
        '(TENXYTE_AUDIT_LOG_RETENTION_DAYS, default: 90 days). '
        'Pass --days=0 to disable purging (no-op).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help=(
                'Override the retention period in days. '
                'Defaults to TENXYTE_AUDIT_LOG_RETENTION_DAYS (currently '
                f'{auth_settings.AUDIT_LOG_RETENTION_DAYS} days). '
                'Pass 0 to skip purging.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report how many rows would be deleted without actually deleting them.',
        )

    def handle(self, *args, **options):
        retention_days = options['days']
        if retention_days is None:
            retention_days = auth_settings.AUDIT_LOG_RETENTION_DAYS

        if retention_days < 0:
            raise CommandError('--days must be 0 or a positive integer.')

        if retention_days == 0:
            self.stdout.write(
                self.style.WARNING(
                    'Audit log purge skipped: retention_days=0 '
                    '(set TENXYTE_AUDIT_LOG_RETENTION_DAYS > 0 to enable).'
                )
            )
            return

        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=retention_days)
        qs = AuditLog.objects.filter(created_at__lt=cutoff)
        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN — {count} audit log(s) older than {retention_days} days '
                    f'(before {cutoff.date()}) would be deleted.'
                )
            )
        else:
            qs.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Purged {count} audit log(s) older than {retention_days} days '
                    f'(before {cutoff.date()}).'
                )
            )
