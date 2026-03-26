"""
Tenxyte - Seed command for default roles and permissions.

Usage:
    python manage.py tenxyte_seed

Options:
    --no-permissions    Skip creating permissions
    --no-roles          Skip creating roles
    --force             Recreate all (delete existing and recreate)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from tenxyte.models import get_role_model, get_permission_model

# =============================================================================
# DEFAULT PERMISSIONS
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
    {"code": "users.edit", "name": "Edit Users", "description": "Can edit user information", "parent": "users"},
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
# DEFAULT ROLES WITH THEIR PERMISSIONS
# =============================================================================

DEFAULT_ROLES = [
    {
        "code": "viewer",
        "name": "Viewer",
        "description": "Read-only access to content",
        "is_default": True,  # Default role for new users
        "permissions": [
            "content.view",
        ],
    },
    {
        "code": "editor",
        "name": "Editor",
        "description": "Can create and edit content",
        "is_default": False,
        "permissions": [
            "content.view",
            "content.create",
            "content.edit",
        ],
    },
    {
        "code": "admin",
        "name": "Administrator",
        "description": "Administrative access to users and content",
        "is_default": False,
        "permissions": [
            # Content
            "content.view",
            "content.create",
            "content.edit",
            "content.delete",
            "content.publish",
            # Users
            "users.view",
            "users.create",
            "users.edit",
            "users.roles.view",
            "users.roles.assign",
            "users.roles.remove",
            # Roles
            "roles.view",
            # Permissions
            "permissions.view",
        ],
    },
    {
        "code": "super_admin",
        "name": "Super Administrator",
        "description": "Full access to all system features",
        "is_default": False,
        "permissions": [
            # All permissions - will be set to ALL available permissions
            "__all__",
        ],
    },
]


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
            except Exception:
                pass
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
