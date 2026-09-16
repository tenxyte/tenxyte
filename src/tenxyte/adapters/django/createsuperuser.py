"""
Thin `python -m` entrypoint for Django's own built-in `createsuperuser` management command —
gives the Django adapter the same invocation shape as
`python -m tenxyte.adapters.fastapi.createsuperuser`.

`python manage.py createsuperuser` remains the idiomatic, primary way to run this for a real
Django project. `createsuperuser` itself is not Tenxyte code at all (it ships with
`django.contrib.auth`) — Tenxyte's `User.USERNAME_FIELD = "email"` / `REQUIRED_FIELDS = []`
(`models/auth.py`) already make it work with no customization needed, so this wrapper adds nothing
beyond the same `DJANGO_SETTINGS_MODULE` auto-discovery `quickstart.py` uses
(`_settings_discovery.py`) and forwards every argument straight through unchanged.

Usage:
    python -m tenxyte.adapters.django.createsuperuser
    python -m tenxyte.adapters.django.createsuperuser --email admin@example.com --noinput

See `python manage.py createsuperuser --help` for the full flag list (`--email`, `--noinput`,
`--database`, ...) — all forwarded as-is.
"""

from __future__ import annotations

import sys

from tenxyte.adapters.django._settings_discovery import setup_django_or_exit


def main() -> None:
    setup_django_or_exit("tenxyte.adapters.django.createsuperuser")

    from django.core.management import call_command

    call_command("createsuperuser", *sys.argv[1:])


if __name__ == "__main__":
    main()
