"""
Tenxyte - Quickstart command for fast project bootstrap.

Usage:
    python manage.py tenxyte_quickstart

Runs makemigrations, migrate, seed, and creates a default Application — all in one command.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = "Bootstrap Tenxyte: migrate + seed + create default Application (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-seed",
            action="store_true",
            help="Skip seeding roles and permissions",
        )
        parser.add_argument(
            "--no-app",
            action="store_true",
            help="Skip creating the default Application",
        )
        parser.add_argument(
            "--app-name",
            type=str,
            default="Default App",
            help='Name for the default Application (default: "Default App")',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🚀 Tenxyte Quickstart"))
        self.stdout.write("")

        # Step 1: makemigrations
        self.stdout.write(self.style.NOTICE("Step 1/4: Creating migrations..."))
        try:
            call_command("makemigrations", verbosity=0)
            self.stdout.write(self.style.SUCCESS("  ✓ Migrations created"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ makemigrations: {e}"))

        # Step 2: migrate
        self.stdout.write(self.style.NOTICE("Step 2/4: Applying migrations..."))
        try:
            # SQLite cannot run schema changes while FK constraint checks are
            # enabled inside transaction.atomic().  Disable them first.
            if connection.vendor == "sqlite":
                with connection.constraint_checks_disabled():
                    call_command("migrate", verbosity=0)
            else:
                call_command("migrate", verbosity=0)
            self.stdout.write(self.style.SUCCESS("  ✓ Database migrated"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  ✗ migrate failed: {e}"))
            return

        # Step 3: seed
        if not options["no_seed"]:
            self.stdout.write(self.style.NOTICE("Step 3/4: Seeding roles & permissions..."))
            try:
                call_command("tenxyte_seed", verbosity=0)
                self.stdout.write(self.style.SUCCESS("  ✓ Roles & permissions seeded"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ⚠ seed: {e}"))
        else:
            self.stdout.write(self.style.NOTICE("Step 3/4: Skipped (--no-seed)"))

        # Step 4: create default Application
        if not options["no_app"]:
            self.stdout.write(self.style.NOTICE("Step 4/4: Creating default Application..."))
            self._create_default_app(options["app_name"])
        else:
            self.stdout.write(self.style.NOTICE("Step 4/4: Skipped (--no-app)"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ Tenxyte is ready!"))
        self.stdout.write("")
        self.stdout.write("  Start your server:  python manage.py runserver")
        self.stdout.write("  Register a user:    POST /api/v1/auth/register/")
        self.stdout.write("")

    def _create_default_app(self, app_name):
        """Create a default Application if none exists (idempotent)."""
        from tenxyte.models import Application

        if Application.objects.filter(name=app_name).exists():
            self.stdout.write(self.style.SUCCESS(f'  ✓ Application "{app_name}" already exists (skipped)'))
            return

        try:
            app, raw_secret = Application.create_application(
                name=app_name,
                description="Auto-created by tenxyte_quickstart",
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Application created: "{app_name}"'))
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("  ╔══════════════════════════════════════════════════════╗"))
            self.stdout.write(self.style.WARNING("  ║  SAVE THESE CREDENTIALS — shown only once!          ║"))
            self.stdout.write(self.style.WARNING("  ╠══════════════════════════════════════════════════════╣"))
            self.stdout.write(f"  ║  Access Key:    {app.access_key}")
            self.stdout.write(f"  ║  Access Secret: {raw_secret}")
            self.stdout.write(self.style.WARNING("  ╠══════════════════════════════════════════════════════╣"))
            self.stdout.write(self.style.WARNING("  ║  The secret is bcrypt-hashed in the database and    ║"))
            self.stdout.write(self.style.WARNING("  ║  CANNOT be retrieved later. Use the API endpoint    ║"))
            self.stdout.write(self.style.WARNING("  ║  POST /api/v1/auth/applications/{id}/regenerate/    ║"))
            self.stdout.write(self.style.WARNING("  ║  to generate new credentials if needed.             ║"))
            self.stdout.write(self.style.WARNING("  ╚══════════════════════════════════════════════════════╝"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  ✗ Failed to create application: {e}"))
