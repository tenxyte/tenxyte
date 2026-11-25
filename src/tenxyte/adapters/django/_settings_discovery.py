"""
Shared `DJANGO_SETTINGS_MODULE` auto-discovery for this adapter's `python -m` entrypoints
(`quickstart.py`, `createsuperuser.py`) — extracted so both stay in sync, not two independent
copies of the same lookup.

Discovery order:
1. Already set in the OS environment — an explicit value always wins, never overridden.
2. A `.env` file's `DJANGO_SETTINGS_MODULE` (via `python-dotenv`, the same `.env` file the rest of
   Tenxyte's settings-priority chain already reads — see `core/env_provider.py`).
3. `manage.py` in the current directory — the file every real Django project already has, parsed
   (never executed) for its own `os.environ.setdefault('DJANGO_SETTINGS_MODULE', ...)` call.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_MANAGE_PY_SETTINGS_RE = re.compile(
    r"""os\.environ\.setdefault\(\s*['"]DJANGO_SETTINGS_MODULE['"]\s*,\s*['"]([\w.]+)['"]\s*\)"""
)


def discover_settings_module() -> str | None:
    from tenxyte.core.env_provider import ensure_dotenv_loaded

    # Populates os.environ from a `.env` file for any key not already set (override=False) — a
    # DJANGO_SETTINGS_MODULE entry there becomes visible via os.environ.get() right after this.
    ensure_dotenv_loaded()
    existing = os.environ.get("DJANGO_SETTINGS_MODULE")
    if existing:
        return existing

    manage_py = Path.cwd() / "manage.py"
    if manage_py.is_file():
        match = _MANAGE_PY_SETTINGS_RE.search(manage_py.read_text(encoding="utf-8", errors="ignore"))
        if match:
            return match.group(1)

    return None


def setup_django_or_exit(entrypoint_module: str) -> None:
    """Resolves `DJANGO_SETTINGS_MODULE` (see `discover_settings_module`) and calls
    `django.setup()`, or prints a clear error and `sys.exit(1)`s if nothing was found.
    `entrypoint_module` is the module path shown in the error message's example command."""
    settings_module = discover_settings_module()
    if not settings_module:
        print(
            "Could not determine DJANGO_SETTINGS_MODULE -- no OS environment variable, no .env "
            "entry, and no manage.py found in the current directory. Set it explicitly, e.g.:\n\n"
            f"  DJANGO_SETTINGS_MODULE=myproject.settings python -m {entrypoint_module}\n",
            file=sys.stderr,
        )
        sys.exit(1)
    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    import django

    django.setup()
