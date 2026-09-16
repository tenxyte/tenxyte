"""
Tests for `tenxyte.adapters.django.createsuperuser` — the thin `python -m` entrypoint for
Django's own built-in `createsuperuser` management command, giving the Django adapter the same
invocation shape as `python -m tenxyte.adapters.fastapi.createsuperuser`.
"""

import sys
from unittest.mock import patch

import pytest

from tenxyte.adapters.django.createsuperuser import main


@pytest.mark.django_db(transaction=True)
class TestCreatesuperuserEntrypoint:
    def test_main_delegates_to_djangos_own_command(self):
        """`main()` really runs createsuperuser end to end (no mocking of call_command) --
        Django's own createsuperuser, not any Tenxyte reimplementation of it."""
        from tenxyte.models import User

        with patch.object(sys, "argv", ["createsuperuser", "--email", "admin@example.com", "--noinput"]):
            main()

        user = User.objects.get(email="admin@example.com")
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_main_forwards_arbitrary_flags_unchanged(self):
        """Every argument is passed straight through -- no Tenxyte-specific argument parsing to
        keep in sync with Django's own createsuperuser flags."""
        from tenxyte.models import User

        with patch.object(sys, "argv", ["createsuperuser", "--email", "other@example.com", "--noinput"]):
            main()
        assert User.objects.filter(email="other@example.com").exists()


def test_main_exits_with_clear_error_when_settings_module_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.chdir(tmp_path)
    with (
        patch.object(sys, "argv", ["createsuperuser", "--noinput"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
