"""
Tests for `tenxyte.adapters.django._settings_discovery` — the shared `DJANGO_SETTINGS_MODULE`
auto-discovery behind both `python -m tenxyte.adapters.django.quickstart` and
`python -m tenxyte.adapters.django.createsuperuser`.
"""

import pytest

import tenxyte.core.env_provider as env_provider_module
from tenxyte.adapters.django._settings_discovery import discover_settings_module, setup_django_or_exit


@pytest.fixture(autouse=True)
def _reset_dotenv_loaded_flag():
    """`ensure_dotenv_loaded()`'s once-per-process cache would otherwise leak between tests that
    each expect their own tmp_path's `.env` (or lack thereof) to be re-scanned — same convention
    as tests/core/test_core_env_provider.py's own fixture."""
    env_provider_module._dotenv_loaded = False
    yield
    env_provider_module._dotenv_loaded = False


class TestDiscoverSettingsModule:
    def test_os_environ_wins_when_already_set(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "explicit.settings")
        assert discover_settings_module() == "explicit.settings"

    def test_falls_back_to_dotenv_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        (tmp_path / ".env").write_text("DJANGO_SETTINGS_MODULE=dotenv.settings\n")
        monkeypatch.chdir(tmp_path)
        assert discover_settings_module() == "dotenv.settings"

    def test_falls_back_to_manage_py_in_cwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        (tmp_path / "manage.py").write_text(
            "import os\n" "def main():\n" "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')\n"
        )
        monkeypatch.chdir(tmp_path)
        assert discover_settings_module() == "myproject.settings"

    def test_os_environ_wins_over_manage_py(self, monkeypatch, tmp_path):
        (tmp_path / "manage.py").write_text(
            "import os\n"
            "def main():\n"
            "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'from_manage_py.settings')\n"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "explicit.settings")
        assert discover_settings_module() == "explicit.settings"

    def test_returns_none_when_nothing_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        monkeypatch.chdir(tmp_path)
        assert discover_settings_module() is None


class TestSetupDjangoOrExit:
    def test_exits_with_clear_error_when_nothing_found(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            setup_django_or_exit("tenxyte.adapters.django.some_entrypoint")
        assert exc_info.value.code == 1
        assert "tenxyte.adapters.django.some_entrypoint" in capsys.readouterr().err

    def test_succeeds_and_configures_os_environ_when_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.integration.django.settings")
        # Doesn't raise -- django.setup() succeeds against the real test settings module.
        setup_django_or_exit("tenxyte.adapters.django.some_entrypoint")
