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

Usage:
    DJANGO_SETTINGS_MODULE=myproject.settings python -m tenxyte.adapters.django.quickstart
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap Tenxyte's Django adapter (migrate + seed + default Application)"
    )
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding roles and permissions")
    parser.add_argument("--no-app", action="store_true", help="Skip creating the default Application")
    parser.add_argument("--app-name", default="Default App", help="Name for the default Application")
    args = parser.parse_args()

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        print(
            "DJANGO_SETTINGS_MODULE is not set -- point it at your project's settings module "
            "first, e.g.:\n\n"
            "  DJANGO_SETTINGS_MODULE=myproject.settings "
            "python -m tenxyte.adapters.django.quickstart\n",
            file=sys.stderr,
        )
        sys.exit(1)

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
