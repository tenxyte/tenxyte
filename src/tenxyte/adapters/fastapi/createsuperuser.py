"""
`python -m` entrypoint to create a superuser for the FastAPI Reference_Stack — the counterpart of
Django's `python manage.py createsuperuser` / `python -m tenxyte.adapters.django.createsuperuser`.

There was no prior Tenxyte tooling for this on the FastAPI side: `register/` never sets
`is_superuser`/`is_staff` (a public registration endpoint shouldn't be able to), and nothing else
in the Reference_Stack creates one — this is new, not a port of existing Django logic (unlike
Django's own `createsuperuser`, which ships with `django.contrib.auth` and needed no new code).

Prompts interactively for email/password by default, mirroring Django's own `createsuperuser` UX
(hidden password input via `getpass`, typed twice to confirm) — or accepts them non-interactively
via `--email`/`--password`/`--noinput` for scripting/CI, same flag names Django's command uses.

Usage:
    python -m tenxyte.adapters.fastapi.createsuperuser
    python -m tenxyte.adapters.fastapi.createsuperuser --email admin@example.com --password "..." --noinput
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from uuid import uuid4

import bcrypt

from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.settings import get_default_settings
from tenxyte.ports.repositories import User


def _prompt_email() -> str:
    while True:
        email = input("Email address: ").strip()
        if email:
            return email
        print("Error: this field cannot be blank.", file=sys.stderr)


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        if not password:
            print("Error: blank passwords aren't allowed.", file=sys.stderr)
            continue
        confirm = getpass.getpass("Password (again): ")
        if password != confirm:
            print("Error: your passwords didn't match.", file=sys.stderr)
            continue
        return password


async def create_superuser(database_url: str, email: str, password: str) -> None:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        # Same bcrypt hard limit `routers/auth.py`'s `register` enforces — caught here as a clean
        # error instead of letting bcrypt raise deep inside hashpw().
        raise ValueError("Password must be at most 72 bytes when UTF-8 encoded")

    settings = get_default_settings()
    engine = db_module.create_engine(database_url)
    try:
        await db_module.create_all_tables(engine)
        session_factory = db_module.create_session_factory(engine)
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            existing = await repo.get_by_email(email)
            if existing is not None:
                raise ValueError(f'A user with email "{email}" already exists.')

            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")
            await repo.create(
                User(
                    id=str(uuid4()),
                    email=email,
                    password_hash=hashed,
                    is_active=True,
                    is_superuser=True,
                    is_staff=True,
                )
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a superuser for Tenxyte's FastAPI Reference_Stack")
    parser.add_argument("--database-url", default=None, help=f"Default: {db_module.DEFAULT_DATABASE_URL}")
    parser.add_argument("--email", default=None, help="Email address (prompted if omitted)")
    parser.add_argument(
        "--password",
        default=None,
        help="Password (prompted if omitted -- prefer the interactive prompt outside of scripting/CI)",
    )
    parser.add_argument(
        "--noinput",
        "--no-input",
        dest="noinput",
        action="store_true",
        help="Never prompt; --email and --password are then required",
    )
    args = parser.parse_args()

    if args.noinput:
        if not args.email or not args.password:
            print("--noinput requires both --email and --password.", file=sys.stderr)
            sys.exit(1)
        email, password = args.email, args.password
    else:
        email = args.email or _prompt_email()
        password = args.password or _prompt_password()

    try:
        asyncio.run(create_superuser(args.database_url or db_module.DEFAULT_DATABASE_URL, email, password))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f'Superuser "{email}" created successfully.')


if __name__ == "__main__":
    main()
