"""
Tenxyte - Cleanup command for expired tokens, OTPs, and old logs.

Usage:
    python manage.py tenxyte_cleanup

Options:
    --login-attempts-days   Days to keep login attempts (default: 90)
    --audit-log-days        Days to keep audit logs (default: 365, 0 = keep all)
    --dry-run               Show what would be deleted without actually deleting
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from tenxyte.models import (
    BlacklistedToken, OTPCode, RefreshToken, LoginAttempt, AuditLog
)


class Command(BaseCommand):
    help = 'Clean up expired tokens, OTPs, login attempts, and old audit logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--login-attempts-days',
            type=int,
            default=90,
            help='Delete login attempts older than N days (default: 90)',
        )
        parser.add_argument(
            '--audit-log-days',
            type=int,
            default=365,
            help='Delete audit logs older than N days (default: 365, 0 = keep all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        login_days = options['login_attempts_days']
        audit_days = options['audit_log_days']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no data will be deleted\n'))

        self.stdout.write(self.style.NOTICE('Tenxyte - Cleaning up expired data...\n'))

        total_deleted = 0

        # 1. Blacklisted tokens (expired)
        total_deleted += self._cleanup_model(
            'Blacklisted tokens (expired)',
            BlacklistedToken.objects.filter(expires_at__lt=now),
            dry_run,
        )

        # 2. OTP codes (expired or used)
        total_deleted += self._cleanup_model(
            'OTP codes (expired or used)',
            OTPCode.objects.filter(expires_at__lt=now),
            dry_run,
        )

        # 3. Refresh tokens (revoked or expired)
        total_deleted += self._cleanup_model(
            'Refresh tokens (revoked or expired)',
            RefreshToken.objects.filter(
                is_revoked=True
            ) | RefreshToken.objects.filter(
                expires_at__lt=now
            ),
            dry_run,
        )

        # 4. Login attempts (older than N days)
        cutoff = now - timedelta(days=login_days)
        total_deleted += self._cleanup_model(
            f'Login attempts (older than {login_days} days)',
            LoginAttempt.objects.filter(created_at__lt=cutoff),
            dry_run,
        )

        # 5. Audit logs (older than N days, if configured)
        if audit_days > 0:
            cutoff = now - timedelta(days=audit_days)
            total_deleted += self._cleanup_model(
                f'Audit logs (older than {audit_days} days)',
                AuditLog.objects.filter(created_at__lt=cutoff),
                dry_run,
            )
        else:
            self.stdout.write('  Audit logs: skipped (--audit-log-days=0)')

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: {total_deleted} records would be deleted'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Cleanup completed: {total_deleted} records deleted'
            ))

    def _cleanup_model(self, label, queryset, dry_run):
        count = queryset.count()
        if not dry_run:
            queryset.delete()
        status = 'would delete' if dry_run else 'deleted'
        self.stdout.write(f'  {label}: {count} {status}')
        return count
