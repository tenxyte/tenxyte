"""
Thin `python -m` entrypoint for the Django_Adapter's `tenxyte_quickstart` management command —
gives the Django adapter the same invocation shape as
`python -m tenxyte.adapters.fastapi.quickstart`, for anyone comparing/testing both adapters side
by side who would otherwise have to remember one adapter uses `python manage.py <command>` and the
other doesn't.

`python manage.py tenxyte_quickstart` remains the idiomatic, primary way to run this for a real
Django project — it already has a `manage.py`, and Django's own tooling (`--help`, autodiscovery,
`self.stdout.write` styling) is built around that convention. This is an *additional* entrypoint,
not a replacement — a thin wrapper that configures Django (`django.setup()`) and delegates to the
exact same command via `call_command`, not a second implementation to keep in sync.

`DJANGO_SETTINGS_MODULE` is auto-discovered, in priority order, so no extra step is needed for the
common case of running this from a real project's root:
1. Already set in the OS environment — an explicit value always wins, never overridden.
2. A `.env` file's `DJANGO_SETTINGS_MODULE` (via `python-dotenv`, the same `.env` file the rest of
   Tenxyte's settings-priority chain already reads — see `core/env_provider.py`).
3. `manage.py` in the current directory — the file every real Django project already has, parsed
   (never executed) for its own `os.environ.setdefault('DJANGO_SETTINGS_MODULE', ...)` call.

Usage:
    python -m tenxyte.adapters.django.quickstart

    # Only needed if none of the discovery steps above find it:
    DJANGO_SETTINGS_MODULE=myproject.settings python -m tenxyte.adapters.django.quickstart
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_MANAGE_PY_SETTINGS_RE = re.compile(
    r"""os\.environ\.setdefault\(\s*['"]DJANGO_SETTINGS_MODULE['"]\s*,\s*['"]([\w.]+)['"]\s*\)"""
)


def _discover_settings_module() -> str | None:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap Tenxyte's Django adapter (migrate + seed + default Application)"
    )
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding roles and permissions")
    parser.add_argument("--no-app", action="store_true", help="Skip creating the default Application")
    parser.add_argument("--app-name", default="Default App", help="Name for the default Application")
    args = parser.parse_args()

    settings_module = _discover_settings_module()
    if not settings_module:
        print(
            "Could not determine DJANGO_SETTINGS_MODULE -- no OS environment variable, no .env "
            "entry, and no manage.py found in the current directory. Set it explicitly, e.g.:\n\n"
            "  DJANGO_SETTINGS_MODULE=myproject.settings "
            "python -m tenxyte.adapters.django.quickstart\n",
            file=sys.stderr,
        )
        sys.exit(1)
    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    import django

    django.setup()

    from django.core.management import call_command

    call_command(
        "tenxyte_quickstart",
        no_seed=args.no_seed,
        no_app=args.no_app,
        app_name=args.app_name,
    )


if __name__ == "__main__":
    main()
