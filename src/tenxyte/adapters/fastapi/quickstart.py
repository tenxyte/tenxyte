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
themselves. `DEFAULT_PERMISSIONS`/`DEFAULT_ROLES` below are a literal copy of the Django
`tenxyte_seed.py` command's data — kept in sync deliberately, not independently redefined, so a
project comparing RBAC data across both adapters sees identical codes/hierarchy/role assignments.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.application_auth import create_application
from tenxyte.adapters.fastapi.models_sa import ApplicationDB
from tenxyte.adapters.fastapi.rbac_service import (
    create_permission_async,
    create_role_async,
    get_permission_by_code_async,
    get_role_by_code_async,
)

# =============================================================================
# DEFAULT PERMISSIONS — kept identical to management/commands/tenxyte_seed.py
# =============================================================================

DEFAULT_PERMISSIONS = [
    # -- Parent groups (hierarchical: having a parent grants all its children) --
    {"code": "users", "name": "Users", "description": "All user permissions"},
    {"code": "users.roles", "name": "User Roles", "description": "All user role permissions", "parent": "users"},
    {
        "code": "users.permissions",
        "name": "User Permissions",
        "description": "All user direct permission management",
        "parent": "users",
    },
    {"code": "roles", "name": "Roles", "description": "All role permissions"},
    {"code": "permissions", "name": "Permissions", "description": "All permission permissions"},
    {"code": "applications", "name": "Applications", "description": "All application permissions"},
    {"code": "content", "name": "Content", "description": "All content permissions"},
    {"code": "system", "name": "System", "description": "All system permissions"},
    # User permissions
    {"code": "users.view", "name": "View Users", "description": "Can view user list and details", "parent": "users"},
    {"code": "users.create", "name": "Create Users", "description": "Can create new users", "parent": "users"},
    {"code": "users.update", "name": "Update Users", "description": "Can update user information", "parent": "users"},
    {"code": "users.delete", "name": "Delete Users", "description": "Can delete users", "parent": "users"},
    {"code": "users.ban", "name": "Ban Users", "description": "Can ban/unban users", "parent": "users"},
    {"code": "users.lock", "name": "Lock Users", "description": "Can lock/unlock user accounts", "parent": "users"},
    {
        "code": "users.roles.view",
        "name": "View User Roles",
        "description": "Can view user roles",
        "parent": "users.roles",
    },
    {
        "code": "users.roles.assign",
        "name": "Assign User Roles",
        "description": "Can assign roles to users",
        "parent": "users.roles",
    },
    {
        "code": "users.roles.remove",
        "name": "Remove User Roles",
        "description": "Can remove roles from users",
        "parent": "users.roles",
    },
    {
        "code": "users.permissions.view",
        "name": "View User Permissions",
        "description": "Can view user direct permissions",
        "parent": "users.permissions",
    },
    {
        "code": "users.permissions.assign",
        "name": "Assign User Permissions",
        "description": "Can assign direct permissions to users",
        "parent": "users.permissions",
    },
    {
        "code": "users.permissions.remove",
        "name": "Remove User Permissions",
        "description": "Can remove direct permissions from users",
        "parent": "users.permissions",
    },
    # Role permissions
    {"code": "roles.view", "name": "View Roles", "description": "Can view role list and details", "parent": "roles"},
    {"code": "roles.create", "name": "Create Roles", "description": "Can create new roles", "parent": "roles"},
    {"code": "roles.update", "name": "Update Roles", "description": "Can update role information", "parent": "roles"},
    {"code": "roles.delete", "name": "Delete Roles", "description": "Can delete roles", "parent": "roles"},
    {
        "code": "roles.manage_permissions",
        "name": "Manage Role Permissions",
        "description": "Can assign/remove permissions from roles",
        "parent": "roles",
    },
    # Permission permissions
    {
        "code": "permissions.view",
        "name": "View Permissions",
        "description": "Can view permission list",
        "parent": "permissions",
    },
    {
        "code": "permissions.create",
        "name": "Create Permissions",
        "description": "Can create new permissions",
        "parent": "permissions",
    },
    {
        "code": "permissions.update",
        "name": "Update Permissions",
        "description": "Can update permission information",
        "parent": "permissions",
    },
    {
        "code": "permissions.delete",
        "name": "Delete Permissions",
        "description": "Can delete permissions",
        "parent": "permissions",
    },
    # Application permissions
    {
        "code": "applications.view",
        "name": "View Applications",
        "description": "Can view application list and details",
        "parent": "applications",
    },
    {
        "code": "applications.create",
        "name": "Create Applications",
        "description": "Can create new applications",
        "parent": "applications",
    },
    {
        "code": "applications.update",
        "name": "Update Applications",
        "description": "Can update application information",
        "parent": "applications",
    },
    {
        "code": "applications.delete",
        "name": "Delete Applications",
        "description": "Can delete applications",
        "parent": "applications",
    },
    {
        "code": "applications.regenerate",
        "name": "Regenerate Credentials",
        "description": "Can regenerate application credentials",
        "parent": "applications",
    },
    # Content permissions (generic)
    {"code": "content.view", "name": "View Content", "description": "Can view content", "parent": "content"},
    {"code": "content.create", "name": "Create Content", "description": "Can create content", "parent": "content"},
    {"code": "content.edit", "name": "Edit Content", "description": "Can edit content", "parent": "content"},
    {"code": "content.delete", "name": "Delete Content", "description": "Can delete content", "parent": "content"},
    {"code": "content.publish", "name": "Publish Content", "description": "Can publish content", "parent": "content"},
    # System permissions
    {
        "code": "system.admin",
        "name": "System Administration",
        "description": "Full system administration access",
        "parent": "system",
    },
    {
        "code": "system.settings",
        "name": "Manage Settings",
        "description": "Can manage system settings",
        "parent": "system",
    },
    {"code": "system.logs", "name": "View Logs", "description": "Can view system logs", "parent": "system"},
    {"code": "system.audit", "name": "View Audit Trail", "description": "Can view audit trail", "parent": "system"},
    # Dashboard & Security permissions
    {"code": "dashboard.view", "name": "View Dashboard", "description": "Can access dashboard statistics"},
    {"code": "security.view", "name": "View Security", "description": "Can view audit logs, login attempts, tokens"},
    {"code": "gdpr.admin", "name": "GDPR Admin", "description": "Can view deletion requests"},
    {"code": "gdpr.process", "name": "GDPR Process", "description": "Can process deletion requests"},
]

# =============================================================================
# DEFAULT ROLES WITH THEIR PERMISSIONS — kept identical to tenxyte_seed.py
# =============================================================================

DEFAULT_ROLES = [
    {
        "code": "viewer",
        "name": "Viewer",
        "description": "Read-only access to content",
        "is_default": True,
        "permissions": ["content.view"],
    },
    {
        "code": "editor",
        "name": "Editor",
        "description": "Can create and edit content",
        "is_default": False,
        "permissions": ["content.view", "content.create", "content.edit"],
    },
    {
        "code": "admin",
        "name": "Administrator",
        "description": "Administrative access to users and content",
        "is_default": False,
        "permissions": [
            "content.view",
            "content.create",
            "content.edit",
            "content.delete",
            "content.publish",
            "users.view",
            "users.create",
            "users.update",
            "users.roles.view",
            "users.roles.assign",
            "users.roles.remove",
            "roles.view",
            "permissions.view",
        ],
    },
    {
        "code": "super_admin",
        "name": "Super Administrator",
        "description": "Full access to all system features",
        "is_default": False,
        "permissions": ["__all__"],
    },
]


async def seed_rbac(session: AsyncSession) -> tuple[int, int]:
    """Idempotent: existing permissions/roles (matched by `code`) are left untouched, matching
    `tenxyte_seed.py`'s non-`--force` behavior — this script has no `--force` equivalent since
    overwriting manual RBAC customization isn't something a quickstart should ever do silently.

    Returns `(permissions_created, roles_created)`.
    """
    permissions_created = 0
    for perm_data in DEFAULT_PERMISSIONS:
        if await get_permission_by_code_async(session, perm_data["code"]) is not None:
            continue
        _, error = await create_permission_async(
            session,
            code=perm_data["code"],
            name=perm_data["name"],
            description=perm_data["description"],
            parent_code=perm_data.get("parent"),
        )
        if error is None:
            permissions_created += 1

    all_permission_codes = [p["code"] for p in DEFAULT_PERMISSIONS]

    roles_created = 0
    for role_data in DEFAULT_ROLES:
        if await get_role_by_code_async(session, role_data["code"]) is not None:
            continue
        perm_codes = role_data["permissions"]
        resolved_codes = all_permission_codes if "__all__" in perm_codes else perm_codes
        await create_role_async(
            session,
            code=role_data["code"],
            name=role_data["name"],
            description=role_data["description"],
            is_default=role_data["is_default"],
            permission_codes=resolved_codes,
        )
        roles_created += 1

    return permissions_created, roles_created


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
                permissions_created, roles_created = await seed_rbac(session)
                print(f"  {permissions_created} permissions created, {roles_created} roles created")
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
