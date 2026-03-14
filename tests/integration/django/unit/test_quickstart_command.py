"""
Tests for tenxyte_quickstart management command.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db(transaction=True)
class TestQuickstartCommand:
    """Tests for the tenxyte_quickstart management command."""

    def test_quickstart_runs_without_error(self):
        """The command executes without raising exceptions."""
        out = StringIO()
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'ready' in output.lower()

    def test_quickstart_creates_application(self):
        """The command creates a default Application."""
        from tenxyte.models import Application

        out = StringIO()
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        assert Application.objects.filter(name='Default App').exists()

    def test_quickstart_idempotent(self):
        """Running the command twice does not create duplicate Applications."""
        from tenxyte.models import Application

        out = StringIO()
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        assert Application.objects.filter(name='Default App').count() == 1

    def test_quickstart_seeds_roles(self):
        """The command seeds default roles and permissions."""
        from tenxyte.models import Role, Permission

        out = StringIO()
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        assert Role.objects.filter(code='admin').exists()
        assert Permission.objects.count() > 0

    def test_quickstart_no_seed_flag(self):
        """--no-seed skips seeding."""
        from tenxyte.models import Role

        out = StringIO()
        # Clear any existing roles first
        Role.objects.all().delete()
        call_command('tenxyte_quickstart', '--no-seed', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'Skipped (--no-seed)' in output

    def test_quickstart_no_app_flag(self):
        """--no-app skips Application creation."""
        from tenxyte.models import Application

        out = StringIO()
        Application.objects.all().delete()
        call_command('tenxyte_quickstart', '--no-app', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'Skipped (--no-app)' in output

    def test_quickstart_custom_app_name(self):
        """--app-name sets a custom Application name."""
        from tenxyte.models import Application

        out = StringIO()
        call_command('tenxyte_quickstart', '--app-name', 'My Custom App', stdout=out, verbosity=0)
        assert Application.objects.filter(name='My Custom App').exists()

    def test_quickstart_shows_credentials(self):
        """The command displays the Application credentials."""
        out = StringIO()
        call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'Access Key' in output
        assert 'Access Secret' in output

    def test_quickstart_makemigrations_failure(self):
        """makemigrations failure is caught and reported as a warning."""
        out = StringIO()
        with patch(
            'tenxyte.management.commands.tenxyte_quickstart.call_command',
            side_effect=_fail_on('makemigrations'),
        ):
            call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'makemigrations: boom' in output

    def test_quickstart_migrate_failure(self):
        """migrate failure is caught, reported, and aborts the command."""
        out = StringIO()
        err = StringIO()
        with patch(
            'tenxyte.management.commands.tenxyte_quickstart.call_command',
            side_effect=_fail_on('migrate'),
        ):
            call_command('tenxyte_quickstart', stdout=out, stderr=err, verbosity=0)
        assert 'migrate failed: boom' in err.getvalue()
        # Command should have aborted — no "ready" message
        assert 'ready' not in out.getvalue().lower()

    def test_quickstart_migrate_non_sqlite(self):
        """migrate takes the non-SQLite branch when vendor is not sqlite."""
        out = StringIO()
        # Patch the vendor attribute as seen by the command module.
        with patch(
            'tenxyte.management.commands.tenxyte_quickstart.connection',
        ) as mock_conn:
            mock_conn.vendor = 'postgresql'
            # migrate is called through the module-level call_command which we
            # also need to let through to the real implementation so that it
            # executes the non-SQLite branch *and* actually runs.
            from django.core.management import call_command as real_call
            with patch(
                'tenxyte.management.commands.tenxyte_quickstart.call_command',
                side_effect=real_call,
            ):
                call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'ready' in output.lower()

    def test_quickstart_seed_failure(self):
        """seed failure is caught and reported as a warning."""
        out = StringIO()
        with patch(
            'tenxyte.management.commands.tenxyte_quickstart.call_command',
            side_effect=_fail_on('tenxyte_seed'),
        ):
            call_command('tenxyte_quickstart', stdout=out, verbosity=0)
        output = out.getvalue()
        assert 'seed: boom' in output

    def test_quickstart_create_application_failure(self):
        """Application creation failure is caught and reported."""
        out = StringIO()
        err = StringIO()
        with patch(
            'tenxyte.models.Application.create_application',
            side_effect=RuntimeError('db error'),
        ):
            call_command('tenxyte_quickstart', stdout=out, stderr=err, verbosity=0)
        assert 'Failed to create application: db error' in err.getvalue()


def _fail_on(target_cmd):
    """Return a side_effect callable that raises only for *target_cmd*."""
    from django.core.management import call_command as real_call_command

    def _side_effect(name, *args, **kwargs):
        if name == target_cmd:
            raise RuntimeError('boom')
        return real_call_command(name, *args, **kwargs)

    return _side_effect

