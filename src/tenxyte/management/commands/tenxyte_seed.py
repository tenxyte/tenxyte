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
    # User permissions
    {'code': 'users.view', 'name': 'View Users', 'description': 'Can view user list and details'},
    {'code': 'users.create', 'name': 'Create Users', 'description': 'Can create new users'},
    {'code': 'users.edit', 'name': 'Edit Users', 'description': 'Can edit user information'},
    {'code': 'users.delete', 'name': 'Delete Users', 'description': 'Can delete users'},
    {'code': 'users.manage_roles', 'name': 'Manage User Roles', 'description': 'Can assign/remove roles from users'},

    # Role permissions
    {'code': 'roles.view', 'name': 'View Roles', 'description': 'Can view role list and details'},
    {'code': 'roles.create', 'name': 'Create Roles', 'description': 'Can create new roles'},
    {'code': 'roles.edit', 'name': 'Edit Roles', 'description': 'Can edit role information'},
    {'code': 'roles.delete', 'name': 'Delete Roles', 'description': 'Can delete roles'},
    {'code': 'roles.manage_permissions', 'name': 'Manage Role Permissions', 'description': 'Can assign/remove permissions from roles'},

    # Permission permissions
    {'code': 'permissions.view', 'name': 'View Permissions', 'description': 'Can view permission list'},
    {'code': 'permissions.create', 'name': 'Create Permissions', 'description': 'Can create new permissions'},
    {'code': 'permissions.edit', 'name': 'Edit Permissions', 'description': 'Can edit permission information'},
    {'code': 'permissions.delete', 'name': 'Delete Permissions', 'description': 'Can delete permissions'},

    # Application permissions
    {'code': 'applications.view', 'name': 'View Applications', 'description': 'Can view application list and details'},
    {'code': 'applications.create', 'name': 'Create Applications', 'description': 'Can create new applications'},
    {'code': 'applications.edit', 'name': 'Edit Applications', 'description': 'Can edit application information'},
    {'code': 'applications.delete', 'name': 'Delete Applications', 'description': 'Can delete applications'},
    {'code': 'applications.regenerate', 'name': 'Regenerate Credentials', 'description': 'Can regenerate application credentials'},

    # Content permissions (generic)
    {'code': 'content.view', 'name': 'View Content', 'description': 'Can view content'},
    {'code': 'content.create', 'name': 'Create Content', 'description': 'Can create content'},
    {'code': 'content.edit', 'name': 'Edit Content', 'description': 'Can edit content'},
    {'code': 'content.delete', 'name': 'Delete Content', 'description': 'Can delete content'},
    {'code': 'content.publish', 'name': 'Publish Content', 'description': 'Can publish content'},

    # System permissions
    {'code': 'system.admin', 'name': 'System Administration', 'description': 'Full system administration access'},
    {'code': 'system.settings', 'name': 'Manage Settings', 'description': 'Can manage system settings'},
    {'code': 'system.logs', 'name': 'View Logs', 'description': 'Can view system logs'},
    {'code': 'system.audit', 'name': 'View Audit Trail', 'description': 'Can view audit trail'},
]


# =============================================================================
# DEFAULT ROLES WITH THEIR PERMISSIONS
# =============================================================================

DEFAULT_ROLES = [
    {
        'code': 'viewer',
        'name': 'Viewer',
        'description': 'Read-only access to content',
        'is_default': True,  # Default role for new users
        'permissions': [
            'content.view',
        ]
    },
    {
        'code': 'editor',
        'name': 'Editor',
        'description': 'Can create and edit content',
        'is_default': False,
        'permissions': [
            'content.view',
            'content.create',
            'content.edit',
        ]
    },
    {
        'code': 'admin',
        'name': 'Administrator',
        'description': 'Administrative access to users and content',
        'is_default': False,
        'permissions': [
            # Content
            'content.view',
            'content.create',
            'content.edit',
            'content.delete',
            'content.publish',
            # Users
            'users.view',
            'users.create',
            'users.edit',
            'users.manage_roles',
            # Roles
            'roles.view',
            # Permissions
            'permissions.view',
        ]
    },
    {
        'code': 'super_admin',
        'name': 'Super Administrator',
        'description': 'Full access to all system features',
        'is_default': False,
        'permissions': [
            # All permissions - will be set to ALL available permissions
            '__all__',
        ]
    },
]


class Command(BaseCommand):
    help = 'Seed default roles and permissions for Tenxyte'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-permissions',
            action='store_true',
            help='Skip creating permissions',
        )
        parser.add_argument(
            '--no-roles',
            action='store_true',
            help='Skip creating roles',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing and recreate all',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Permission = get_permission_model()
        Role = get_role_model()

        no_permissions = options['no_permissions']
        no_roles = options['no_roles']
        force = options['force']

        self.stdout.write(self.style.NOTICE('Tenxyte - Seeding default data...'))
        self.stdout.write('')

        # Create permissions
        if not no_permissions:
            self._create_permissions(Permission, force)

        # Create roles
        if not no_roles:
            self._create_roles(Role, Permission, force)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seeding completed successfully!'))

    def _create_permissions(self, Permission, force):
        self.stdout.write(self.style.NOTICE('Creating permissions...'))

        if force:
            count = Permission.objects.filter(
                code__in=[p['code'] for p in DEFAULT_PERMISSIONS]
            ).delete()[0]
            if count:
                self.stdout.write(f'  Deleted {count} existing permissions')

        created_count = 0
        updated_count = 0

        for perm_data in DEFAULT_PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                code=perm_data['code'],
                defaults={
                    'name': perm_data['name'],
                    'description': perm_data['description'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  + Created: {perm.code}')
            else:
                # Update existing
                updated = False
                if perm.name != perm_data['name']:
                    perm.name = perm_data['name']
                    updated = True
                if perm.description != perm_data['description']:
                    perm.description = perm_data['description']
                    updated = True
                if updated:
                    perm.save()
                    updated_count += 1
                    self.stdout.write(f'  ~ Updated: {perm.code}')

        self.stdout.write(
            self.style.SUCCESS(f'  Permissions: {created_count} created, {updated_count} updated')
        )

    def _create_roles(self, Role, Permission, force):
        self.stdout.write(self.style.NOTICE('Creating roles...'))

        if force:
            count = Role.objects.filter(
                code__in=[r['code'] for r in DEFAULT_ROLES]
            ).delete()[0]
            if count:
                self.stdout.write(f'  Deleted {count} existing roles')

        created_count = 0
        updated_count = 0

        # Get all permissions for super_admin
        all_permissions = list(Permission.objects.all())

        for role_data in DEFAULT_ROLES:
            role, created = Role.objects.get_or_create(
                code=role_data['code'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'is_default': role_data['is_default'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  + Created: {role.code}')
            else:
                # Update existing
                updated = False
                if role.name != role_data['name']:
                    role.name = role_data['name']
                    updated = True
                if role.description != role_data['description']:
                    role.description = role_data['description']
                    updated = True
                if role.is_default != role_data['is_default']:
                    role.is_default = role_data['is_default']
                    updated = True
                if updated:
                    role.save()
                    updated_count += 1
                    self.stdout.write(f'  ~ Updated: {role.code}')

            # Assign permissions
            perm_codes = role_data['permissions']
            if '__all__' in perm_codes:
                # Super admin gets all permissions
                role.permissions.set(all_permissions)
                self.stdout.write(f'    -> Assigned ALL permissions ({len(all_permissions)})')
            else:
                permissions = Permission.objects.filter(code__in=perm_codes)
                role.permissions.set(permissions)
                self.stdout.write(f'    -> Assigned {permissions.count()} permissions')

        self.stdout.write(
            self.style.SUCCESS(f'  Roles: {created_count} created, {updated_count} updated')
        )
