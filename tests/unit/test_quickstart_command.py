"""
Tests for tenxyte_quickstart management command.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
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
