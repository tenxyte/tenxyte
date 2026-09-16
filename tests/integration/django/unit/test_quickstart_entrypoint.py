"""
Tests for `tenxyte.adapters.django.quickstart` — the thin `python -m` entrypoint for the
`tenxyte_quickstart` management command, giving the Django adapter the same invocation shape as
`python -m tenxyte.adapters.fastapi.quickstart`.
"""

import sys
from unittest.mock import patch

import pytest

from tenxyte.adapters.django.quickstart import main


@pytest.mark.django_db(transaction=True)
class TestQuickstartEntrypoint:
    def test_main_delegates_to_the_real_management_command(self):
        """`main()` really runs `tenxyte_quickstart` end to end (no mocking of call_command) --
        the same real seeding/Application-creation the command's own tests already verify."""
        from tenxyte.models import Application, Role

        with patch.object(sys, "argv", ["quickstart"]):
            main()

        assert Application.objects.filter(name="Default App").exists()
        assert Role.objects.filter(code="admin").exists()

    def test_main_forwards_no_seed_flag(self):
        from tenxyte.models import Role

        Role.objects.all().delete()
        with patch.object(sys, "argv", ["quickstart", "--no-seed"]):
            main()
        assert not Role.objects.exists()

    def test_main_forwards_no_app_flag(self):
        from tenxyte.models import Application

        Application.objects.all().delete()
        with patch.object(sys, "argv", ["quickstart", "--no-app"]):
            main()
        assert not Application.objects.exists()

    def test_main_forwards_custom_app_name(self):
        from tenxyte.models import Application

        with patch.object(sys, "argv", ["quickstart", "--app-name", "My Custom App"]):
            main()
        assert Application.objects.filter(name="My Custom App").exists()

    def test_main_is_idempotent(self):
        from tenxyte.models import Application

        with patch.object(sys, "argv", ["quickstart"]):
            main()
            main()
        assert Application.objects.filter(name="Default App").count() == 1


def test_main_exits_with_clear_error_when_settings_module_unset(monkeypatch):
    # Only the early os.environ check is under test here -- Django itself is already configured
    # in-process for this test session regardless, so popping the var doesn't disturb other tests.
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    with patch.object(sys, "argv", ["quickstart"]), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
