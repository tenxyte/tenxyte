"""
Tenxyte - Seed command for default roles and permissions.

Usage:
    python manage.py tenxyte_seed

Options:
    --no-permissions    Skip creating permissions
    --no-roles          Skip creating roles
    --force             Recreate all (delete existing and recreate)

Note: idempotent means no duplicate rows, not "read-only after the first run". Every run
(with or without --force) re-syncs the permission set of each DEFAULT_ROLES role (viewer,
editor, admin, super_admin) to match this module's current definitions, overwriting any
manual customization made to those built-in role codes. See docs/en/rbac.md for details.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from tenxyte.core.rbac_defaults import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from tenxyte.models import get_permission_model, get_role_model


class Command(BaseCommand):
    help = "Seed default roles and permissions for Tenxyte"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-permissions",
            action="store_true",
            help="Skip creating permissions",
        )
        parser.add_argument(
            "--no-roles",
            action="store_true",
            help="Skip creating roles",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing and recreate all",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Permission = get_permission_model()
        Role = get_role_model()

        no_permissions = options["no_permissions"]
        no_roles = options["no_roles"]
        force = options["force"]

        self.stdout.write(self.style.NOTICE("Tenxyte - Seeding default data..."))
        self.stdout.write("")

        # Create permissions
        if not no_permissions:
            self._create_permissions(Permission, force)

        # Create roles
        if not no_roles:
            self._create_roles(Role, Permission, force)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seeding completed successfully!"))

    def _create_permissions(self, Permission, force):
        self.stdout.write(self.style.NOTICE("Creating permissions..."))

        created_count = 0
        updated_count = 0

        # First pass: create/update all permissions (without parent)
        for perm_data in DEFAULT_PERMISSIONS:
            if force:
                perm, created = Permission.objects.update_or_create(
                    code=perm_data["code"],
                    defaults={
                        "name": perm_data["name"],
                        "description": perm_data["description"],
                    },
                )
            else:
                perm, created = Permission.objects.get_or_create(
                    code=perm_data["code"],
                    defaults={
                        "name": perm_data["name"],
                        "description": perm_data["description"],
                    },
                )

            if created:
                created_count += 1
                self.stdout.write(f"  + Created: {perm.code}")
            elif force:
                updated_count += 1
                self.stdout.write(f"  ~ Updated: {perm.code}")
            else:
                updated = False
                if perm.name != perm_data["name"]:
                    perm.name = perm_data["name"]
                    updated = True
                if perm.description != perm_data["description"]:
                    perm.description = perm_data["description"]
                    updated = True
                if updated:
                    perm.save()
                    updated_count += 1
                    self.stdout.write(f"  ~ Updated: {perm.code}")

        # Second pass: assign parent relationships (hierarchy)
        parent_count = 0
        for perm_data in DEFAULT_PERMISSIONS:
            parent_code = perm_data.get("parent")
            if parent_code:
                try:
                    perm = Permission.objects.get(code=perm_data["code"])
                    parent = Permission.objects.get(code=parent_code)
                    if perm.parent_id != parent.pk:
                        perm.parent = parent
                        perm.save()
                        parent_count += 1
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  ! Could not set parent "{parent_code}" for "{perm_data["code"]}"')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Permissions: {created_count} created, {updated_count} updated, " f"{parent_count} parent links set"
            )
        )

    def _safe_set_permissions(self, role, permissions):
        """Set permissions on a role, with MongoDB-compatible fallback."""
        try:
            role.permissions.set(permissions)
        except TypeError:
            # MongoDB: set() fails due to deletion collector issue
            # Fallback: clear through table directly, then re-add
            try:
                through = role.permissions.through
                source = role.permissions.source_field_name
                db = role._state.db or "default"
                through.objects.using(db).filter(
                    **{
                        source: role.pk,
                    }
                )._raw_delete(db)
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f"  ! Could not clear permissions through-table for role: {e}"))
            role.permissions.add(*permissions)

    def _create_roles(self, Role, Permission, force):
        self.stdout.write(self.style.NOTICE("Creating roles..."))

        created_count = 0
        updated_count = 0

        # Get all permissions for super_admin
        all_permissions = list(Permission.objects.all())

        for role_data in DEFAULT_ROLES:
            if force:
                role, created = Role.objects.update_or_create(
                    code=role_data["code"],
                    defaults={
                        "name": role_data["name"],
                        "description": role_data["description"],
                        "is_default": role_data["is_default"],
                    },
                )
            else:
                role, created = Role.objects.get_or_create(
                    code=role_data["code"],
                    defaults={
                        "name": role_data["name"],
                        "description": role_data["description"],
                        "is_default": role_data["is_default"],
                    },
                )

            if created:
                created_count += 1
                self.stdout.write(f"  + Created: {role.code}")
            elif force:
                updated_count += 1
                self.stdout.write(f"  ~ Updated: {role.code}")
            else:
                # Update existing only if changed
                updated = False
                if role.name != role_data["name"]:
                    role.name = role_data["name"]
                    updated = True
                if role.description != role_data["description"]:
                    role.description = role_data["description"]
                    updated = True
                if role.is_default != role_data["is_default"]:
                    role.is_default = role_data["is_default"]
                    updated = True
                if updated:
                    role.save()
                    updated_count += 1
                    self.stdout.write(f"  ~ Updated: {role.code}")

            # Assign permissions
            perm_codes = role_data["permissions"]
            if "__all__" in perm_codes:
                # Super admin gets all permissions
                self._safe_set_permissions(role, all_permissions)
                self.stdout.write(f"    -> Assigned ALL permissions ({len(all_permissions)})")
            else:
                permissions = list(Permission.objects.filter(code__in=perm_codes))
                self._safe_set_permissions(role, permissions)
                self.stdout.write(f"    -> Assigned {len(permissions)} permissions")

        self.stdout.write(self.style.SUCCESS(f"  Roles: {created_count} created, {updated_count} updated"))
