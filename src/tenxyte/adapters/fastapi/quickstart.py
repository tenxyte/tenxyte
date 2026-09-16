"""
FastAPI_Adapter equivalent of the Django_Adapter's `python manage.py tenxyte_quickstart`
(`src/tenxyte/management/commands/tenxyte_quickstart.py`) — bootstraps a Reference_Stack
deployment in one command: create the schema, seed the default roles/permissions, create a
default Application.

Usage:
    python -m tenxyte.adapters.fastapi.quickstart

There was previously no FastAPI counterpart to this at all: the Reference_Stack shipped
`RoleDB`/`PermissionDB` tables (Wave D, task 10.1) with nothing to populate them, and
`create_application()` (`application_auth.py`) existed only as a function callers had to script
themselves.

`DEFAULT_PERMISSIONS`/`DEFAULT_ROLES` live in `tenxyte.core.rbac_defaults` — a single,
framework-agnostic source both adapters import, so RBAC data can't silently drift apart between
them (a first version of this script kept its own literal copy of that data instead; extracted
after the fact).

`seed_rbac()` deliberately mirrors `tenxyte_seed.py`'s **re-sync** semantics, not a one-shot
"create if missing" — this is a considered choice, not the more obvious option: an earlier version
of this function skipped every already-existing row entirely (`continue` as soon as a permission/
role's `code` was found), which is simpler but silently breaks the upgrade path. If Tenxyte ships
a new permission in a later version and a project re-runs its quickstart/seed expecting to pick it
up, "skip if exists" never grants it to `super_admin` on an existing install, while Django's own
`tenxyte_seed.py` always did (re-running it re-syncs every `DEFAULT_ROLES` role's permission set,
and resolves `"__all__"` against every permission that exists *at seed time*, not a fixed list).
Kept identical here for the same reason Django accepts it: overwriting a manually renamed built-in
role's name/description is a documented trade-off (see `docs/en/rbac.md`), not an accident — this
script still has no `--force` equivalent, since Django's own `--force` (delete-and-recreate) is a
strictly more destructive operation this quickstart never needs to offer.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.application_auth import create_application
from tenxyte.adapters.fastapi.models_sa import ApplicationDB, PermissionDB
from tenxyte.adapters.fastapi.rbac_service import (
    create_permission_async,
    create_role_async,
    get_permission_by_code_async,
    get_role_by_code_async,
    update_permission_async,
    update_role_async,
)
from tenxyte.core.rbac_defaults import DEFAULT_PERMISSIONS, DEFAULT_ROLES


class RbacSeedResult(NamedTuple):
    permissions_created: int
    permissions_updated: int
    roles_created: int
    roles_updated: int


async def seed_rbac(session: AsyncSession) -> RbacSeedResult:
    """Create-or-resync every `DEFAULT_PERMISSIONS`/`DEFAULT_ROLES` row — see the module docstring
    for why this always re-syncs an existing role's permission set rather than skipping it."""
    permissions_created = 0
    permissions_updated = 0

    # Pass 1: create or field-sync every permission (name/description) without touching `parent`
    # yet — a child's parent permission may not exist yet on its own first pass otherwise, same
    # two-pass split as tenxyte_seed.py's own `_create_permissions`.
    for perm_data in DEFAULT_PERMISSIONS:
        existing = await get_permission_by_code_async(session, perm_data["code"])
        if existing is None:
            await create_permission_async(
                session, code=perm_data["code"], name=perm_data["name"], description=perm_data["description"]
            )
            permissions_created += 1
        elif existing.name != perm_data["name"] or existing.description != perm_data["description"]:
            await update_permission_async(
                session, existing, name=perm_data["name"], description=perm_data["description"]
            )
            permissions_updated += 1

    # Pass 2: wire/re-sync parent relationships (hierarchy).
    for perm_data in DEFAULT_PERMISSIONS:
        parent_code = perm_data.get("parent")
        if not parent_code:
            continue
        perm = await get_permission_by_code_async(session, perm_data["code"])
        parent = await get_permission_by_code_async(session, parent_code)
        if perm is not None and parent is not None and perm.parent_id != parent.id:
            await update_permission_async(session, perm, parent_code=parent_code)

    # Every permission that exists right now — not just this module's own DEFAULT_PERMISSIONS
    # codes — so a project's own custom permissions are included in "__all__" too, matching
    # tenxyte_seed.py's `Permission.objects.all()`.
    all_permissions = (await session.execute(select(PermissionDB))).scalars().all()
    all_permission_codes = [p.code for p in all_permissions]

    roles_created = 0
    roles_updated = 0
    for role_data in DEFAULT_ROLES:
        perm_codes = role_data["permissions"]
        resolved_codes = all_permission_codes if "__all__" in perm_codes else perm_codes

        existing_role = await get_role_by_code_async(session, role_data["code"])
        if existing_role is None:
            await create_role_async(
                session,
                code=role_data["code"],
                name=role_data["name"],
                description=role_data["description"],
                is_default=role_data["is_default"],
                permission_codes=resolved_codes,
            )
            roles_created += 1
            continue

        needs_field_update = (
            existing_role.name != role_data["name"]
            or existing_role.description != role_data["description"]
            or existing_role.is_default != role_data["is_default"]
        )
        if needs_field_update:
            roles_updated += 1

        # Always re-sync permissions regardless of whether name/description/is_default changed —
        # see the module docstring for why this deliberately mirrors tenxyte_seed.py instead of
        # skipping existing rows.
        await update_role_async(
            session,
            existing_role,
            name=role_data["name"] if needs_field_update else None,
            description=role_data["description"] if needs_field_update else None,
            is_default=role_data["is_default"] if needs_field_update else None,
            permission_codes=resolved_codes,
        )

    return RbacSeedResult(permissions_created, permissions_updated, roles_created, roles_updated)


async def create_default_application(session: AsyncSession, app_name: str) -> tuple[ApplicationDB, str] | None:
    """Idempotent: returns `None` (nothing created) if an Application with this name already
    exists, matching `tenxyte_quickstart.py`'s `Application.objects.filter(name=...).exists()`
    check."""
    existing = (await session.execute(select(ApplicationDB).where(ApplicationDB.name == app_name))).scalar_one_or_none()
    if existing is not None:
        return None
    return await create_application(session, name=app_name)


async def bootstrap(
    database_url: str | None = None,
    *,
    seed: bool = True,
    create_app: bool = True,
    app_name: str = "Default App",
) -> None:
    resolved_url = database_url or db_module.DEFAULT_DATABASE_URL

    print("Tenxyte Quickstart (FastAPI)")
    print()

    print("Step 1/3: Creating schema...")
    engine = db_module.create_engine(resolved_url)
    try:
        await db_module.create_all_tables(engine)
        print("  Schema ready")

        session_factory = db_module.create_session_factory(engine)
        async with session_factory() as session:
            if seed:
                print("Step 2/3: Seeding roles & permissions...")
                result = await seed_rbac(session)
                print(f"  Permissions: {result.permissions_created} created, " f"{result.permissions_updated} updated")
                print(f"  Roles: {result.roles_created} created, {result.roles_updated} updated")
            else:
                print("Step 2/3: Skipped (--no-seed)")

            if create_app:
                print("Step 3/3: Creating default Application...")
                result = await create_default_application(session, app_name)
                if result is None:
                    print(f'  Application "{app_name}" already exists (skipped)')
                else:
                    application, raw_secret = result
                    print()
                    print("  ======================================================")
                    print("  SAVE THESE CREDENTIALS -- shown only once!")
                    print("  ------------------------------------------------------")
                    print(f"  Access Key:    {application.access_key}")
                    print(f"  Access Secret: {raw_secret}")
                    print("  ------------------------------------------------------")
                    print("  The secret is bcrypt-hashed in the database and cannot")
                    print("  be retrieved later. Use POST /api/v1/applications/{id}/")
                    print("  regenerate/ to generate new credentials if needed.")
                    print("  ======================================================")
            else:
                print("Step 3/3: Skipped (--no-app)")
    finally:
        await engine.dispose()

    print()
    print("Tenxyte is ready!")
    print()
    print("  Start your server:  uvicorn main:app --reload")
    print("  Register a user:    POST /api/v1/register/")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Tenxyte's FastAPI Reference_Stack")
    parser.add_argument("--database-url", default=None, help=f"Default: {db_module.DEFAULT_DATABASE_URL}")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding roles and permissions")
    parser.add_argument("--no-app", action="store_true", help="Skip creating the default Application")
    parser.add_argument("--app-name", default="Default App", help="Name for the default Application")
    args = parser.parse_args()

    asyncio.run(
        bootstrap(
            args.database_url,
            seed=not args.no_seed,
            create_app=not args.no_app,
            app_name=args.app_name,
        )
    )


if __name__ == "__main__":
    main()
