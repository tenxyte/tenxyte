import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models

logger = logging.getLogger("tenxyte.security")


class Command(BaseCommand):
    help = "Nettoie les tokens expirés (JWT Blacklist, Magic Links, OTPs) pour libérer de l'espace et prévenir la réutilisation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Ne supprime rien, affiche juste ce qui serait supprimé"
        )
        parser.add_argument(
            "--login-attempts-days", type=int, default=90, help="Jours avant suppression des LoginAttempt (0 = garder)"
        )
        parser.add_argument(
            "--audit-log-days", type=int, default=365, help="Jours avant suppression des AuditLog (0 = garder)"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        login_days = options["login_attempts_days"]
        audit_days = options["audit_log_days"]

        if dry_run:
            self.stdout.write("DRY RUN - no data will be deleted (simulation only).")

        self.stdout.write("Demarrage du nettoyage des tokens expirés...")

        # 1. Clean Blacklisted JWT Tokens
        try:
            from tenxyte.models.security import BlacklistedToken

            qs = BlacklistedToken.objects.filter(expires_at__lt=timezone.now())
            bl_count = qs.count()
            if not dry_run:
                BlacklistedToken.cleanup_expired()
            self.stdout.write(self.style.SUCCESS(f"Blacklisted tokens (expired): {bl_count} deleted."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning blacklisted tokens: {str(e)}"))

        # 2. Clean Expired Magic Links (F-13)
        try:
            from tenxyte.models.magic_link import MagicLinkToken

            qs = MagicLinkToken.objects.filter(expires_at__lt=timezone.now())
            ml_count = qs.count()
            if not dry_run:
                qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {ml_count} expired Magic Link tokens."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning Magic Link tokens: {str(e)}"))

        # 3. Clean Expired OTP Codes
        try:
            from tenxyte.models.operational import OTPCode

            qs = OTPCode.objects.filter(expires_at__lt=timezone.now())
            otp_count = qs.count()
            if not dry_run:
                qs.delete()
            self.stdout.write(self.style.SUCCESS(f"OTP codes (expired or used): {otp_count} deleted."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning OTP codes: {str(e)}"))

        # 4. Clean Expired/Revoked Refresh Tokens
        try:
            from tenxyte.models.operational import RefreshToken

            qs = RefreshToken.objects.filter(models.Q(expires_at__lt=timezone.now()) | models.Q(is_revoked=True))
            rt_count = qs.count()
            if not dry_run:
                qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Refresh tokens (revoked or expired): {rt_count} deleted."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning Refresh tokens: {str(e)}"))

        # 5. Clean Old Login Attempts
        if login_days > 0:
            try:
                from tenxyte.models.operational import LoginAttempt

                cutoff = timezone.now() - timezone.timedelta(days=login_days)
                qs = LoginAttempt.objects.filter(created_at__lt=cutoff)
                la_count = qs.count()
                if not dry_run:
                    qs.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Login attempts (older than {login_days} days): {la_count} deleted.")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cleaning Login attempts: {str(e)}"))
        else:
            self.stdout.write("Login attempts: skipped")

        # 6. Clean Old Audit Logs
        if audit_days > 0:
            try:
                from tenxyte.models.security import AuditLog

                cutoff = timezone.now() - timezone.timedelta(days=audit_days)
                qs = AuditLog.objects.filter(created_at__lt=cutoff)
                al_count = qs.count()
                if not dry_run:
                    qs.delete()
                self.stdout.write(self.style.SUCCESS(f"Audit logs (older than {audit_days} days): {al_count} deleted."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cleaning Audit logs: {str(e)}"))
        else:
            self.stdout.write("Audit logs: skipped (--audit-log-days=0)")

        self.stdout.write(self.style.SUCCESS("Nettoyage termine avec succes."))
