"""
Thin `python -m` entrypoint for the Django_Adapter's `tenxyte_quickstart` management command —
gives the Django adapter the same invocation shape as
`python -m tenxyte.adapters.fastapi.quickstart`, for anyone comparing/testing both adapters side
by side who would otherwise have to remember one adapter uses `python manage.py <command>` and the
other doesn't.

`python manage.py tenxyte_quickstart` remains the idiomatic, primary way to run this for a real
Django project — it already has a `manage.py`, and Django's own tooling (`--help`, autodiscovery,
`self.stdout.write` styling) is built around that convention. This is an *additional* entrypoint,
not a replacement — a thin wrapper that configures Django (`django.setup()`, via
`_settings_discovery.setup_django_or_exit`) and delegates to the exact same command via
`call_command`, not a second implementation to keep in sync.

`DJANGO_SETTINGS_MODULE` is auto-discovered — see `_settings_discovery.py`'s own docstring for the
lookup order — so no extra step is needed for the common case of running this from a real
project's root.

Usage:
    python -m tenxyte.adapters.django.quickstart

    # Only needed if _settings_discovery's lookup finds nothing:
    DJANGO_SETTINGS_MODULE=myproject.settings python -m tenxyte.adapters.django.quickstart
"""

from __future__ import annotations

import argparse

from tenxyte.adapters.django._settings_discovery import setup_django_or_exit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap Tenxyte's Django adapter (migrate + seed + default Application)"
    )
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding roles and permissions")
    parser.add_argument("--no-app", action="store_true", help="Skip creating the default Application")
    parser.add_argument("--app-name", default="Default App", help="Name for the default Application")
    args = parser.parse_args()

    setup_django_or_exit("tenxyte.adapters.django.quickstart")

    from django.core.management import call_command

    call_command(
        "tenxyte_quickstart",
        no_seed=args.no_seed,
        no_app=args.no_app,
        app_name=args.app_name,
    )


if __name__ == "__main__":
    main()
