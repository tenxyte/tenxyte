"""
Tests for `tenxyte.adapters.django.quickstart` — the thin `python -m` entrypoint for the
`tenxyte_quickstart` management command, giving the Django adapter the same invocation shape as
`python -m tenxyte.adapters.fastapi.quickstart`.
"""

import sys
from unittest.mock import patch

import pytest

import tenxyte.core.env_provider as env_provider_module
from tenxyte.adapters.django.quickstart import _discover_settings_module, main


@pytest.fixture(autouse=True)
def _reset_dotenv_loaded_flag():
    """`ensure_dotenv_loaded()`'s once-per-process cache would otherwise leak between tests that
    each expect their own tmp_path's `.env` (or lack thereof) to be re-scanned — same convention
    as tests/core/test_core_env_provider.py's own fixture."""
    env_provider_module._dotenv_loaded = False
    yield
    env_provider_module._dotenv_loaded = False


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


def test_main_exits_with_clear_error_when_settings_module_unset(monkeypatch, tmp_path):
    # Only the early discovery/os.environ check is under test here -- Django itself is already
    # configured in-process for this test session regardless, so popping the var doesn't disturb
    # other tests. chdir into an empty tmp_path so no manage.py/.env from elsewhere is found.
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.chdir(tmp_path)
    with patch.object(sys, "argv", ["quickstart"]), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


class TestDiscoverSettingsModule:
    def test_os_environ_wins_when_already_set(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "explicit.settings")
        assert _discover_settings_module() == "explicit.settings"

    def test_falls_back_to_dotenv_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        (tmp_path / ".env").write_text("DJANGO_SETTINGS_MODULE=dotenv.settings\n")
        monkeypatch.chdir(tmp_path)
        assert _discover_settings_module() == "dotenv.settings"

    def test_falls_back_to_manage_py_in_cwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        (tmp_path / "manage.py").write_text(
            "import os\n" "def main():\n" "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')\n"
        )
        monkeypatch.chdir(tmp_path)
        assert _discover_settings_module() == "myproject.settings"

    def test_os_environ_wins_over_manage_py(self, monkeypatch, tmp_path):
        (tmp_path / "manage.py").write_text(
            "import os\n"
            "def main():\n"
            "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'from_manage_py.settings')\n"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "explicit.settings")
        assert _discover_settings_module() == "explicit.settings"

    def test_returns_none_when_nothing_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        monkeypatch.chdir(tmp_path)
        assert _discover_settings_module() is None
