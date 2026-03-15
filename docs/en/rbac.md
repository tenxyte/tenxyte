# RBAC Guide — Roles, Permissions & Decorators

Tenxyte provides a flexible Role-Based Access Control (RBAC) system with:
- **Permissions** — atomic capabilities (e.g. `posts.publish`, `users.ban`)
- **Roles** — named groups of permissions with optional hierarchy
- **Decorators** — protect views with a single line of code

## Table of Contents

- [Concepts](#concepts)
  - [Permissions](#permissions)
  - [Permission Hierarchy](#permission-hierarchy)
  - [Roles](#roles)
  - [Permission Resolution Order](#permission-resolution-order)
- [User RBAC Methods](#user-rbac-methods)
- [Decorators](#decorators)
  - [`@require_permission`](#require_permission)
  - [`@require_any_permission`](#require_any_permission)
  - [`@require_all_permissions`](#require_all_permissions)
  - [`@require_role`](#require_role)
  - [`@require_any_role`](#require_any_role)
  - [`@require_all_roles`](#require_all_roles)
  - [`@require_jwt`](#require_jwt)
  - [`@require_verified_email`](#require_verified_email)
  - [`@require_verified_phone`](#require_verified_phone)
- [Combining Decorators](#combining-decorators)
- [API Endpoints for RBAC Management](#api-endpoints-for-rbac-management)
  - [Permissions](#permissions-1)
  - [Roles](#roles-1)
  - [User Roles & Permissions](#user-roles--permissions)
- [Organization-Scoped RBAC](#organization-scoped-rbac)
- [Default Roles](#default-roles)
- [Built-in Permission Codes](#built-in-permission-codes)
- [Seeding & Customization](#seeding--customization)
  - [`tenxyte_seed` Command](#tenxyte_seed-command)
  - [Swappable Models](#swappable-models)

---

## Concepts

### Permissions

A permission is a string code like `users.view`, `posts.publish`, `billing.manage`.

```python
from tenxyte.models import Permission

# Create
perm = Permission.objects.create(code="posts.publish", name="Publish Posts")

# Assign directly to a user
user.direct_permissions.add(perm)

# Check
user.has_permission("posts.publish")  # True
```

### Permission Hierarchy

Permissions support parent/child relationships. Having a parent permission automatically grants all its children.

```python
from tenxyte.models import Permission

# Create a parent permission
content = Permission.objects.create(code="content", name="All Content")

# Create children — having "content" grants both automatically
Permission.objects.create(code="content.edit", name="Edit Content", parent=content)
Permission.objects.create(code="content.publish", name="Publish Content", parent=content)

# A user with the parent has all children
user.direct_permissions.add(content)
user.has_permission("content.edit")     # True (inherited from parent)
user.has_permission("content.publish")  # True (inherited from parent)
```

### Roles

A role groups multiple permissions. Each role has a unique `code` identifier.

```python
from tenxyte.models import Role

# Create a role (code is required and must be unique)
editor = Role.objects.create(code="editor", name="Editor", description="Can edit content")
editor.permissions.add(Permission.objects.get(code="posts.edit"))

# Create another role
publisher = Role.objects.create(code="publisher", name="Publisher", description="Can publish content")
publisher.permissions.add(Permission.objects.get(code="posts.publish"))

# Assign to user
user.roles.add(editor)

# Check
user.has_permission("posts.edit")    # True (from editor role)
user.has_permission("posts.publish") # False (only publisher has it)
```

### Permission Resolution Order

When checking `user.has_permission("x")`, Tenxyte checks:
1. User's **direct permissions** and permissions from user's **roles** (checked together in a single query)
2. **Permission hierarchy** — if the permission has ancestors (via `parent`), checks if any ancestor permission is assigned to the user

---

## User RBAC Methods

The `User` model provides these built-in methods for RBAC:

### Permission Methods

```python
# Single permission check (includes roles, direct, and hierarchy)
user.has_permission("posts.publish")             # bool

# Multiple permission checks
user.has_any_permission(["posts.edit", "posts.publish"])   # True if at least one
user.has_all_permissions(["posts.edit", "posts.publish"])  # True if all

# List all effective permissions (roles + direct + hierarchy)
user.get_all_permissions()  # ['posts.edit', 'posts.publish', ...]
```

### Role Methods

```python
# Check roles
user.has_role("admin")                           # bool
user.has_any_role(["admin", "editor"])            # True if at least one
user.has_all_roles(["admin", "editor"])           # True if all

# Assign / remove roles
user.assign_role("editor")    # True if assigned, False if role not found
user.remove_role("editor")    # True if removed, False if role not found

# List all role codes
user.get_all_roles()          # ['editor', 'viewer']

# Assign the default role (is_default=True)
user.assign_default_role()
```

---

## Decorators

### `@require_permission`

Protect a view method — returns `403` if the user lacks the permission.

```python
from tenxyte.decorators import require_permission

class PostPublishView(APIView):
    @require_permission('posts.publish')
    def post(self, request):
        ...
```

### `@require_any_permission`

Allow access if the user has **at least one** of the listed permissions.

```python
from tenxyte.decorators import require_any_permission

class ContentView(APIView):
    @require_any_permission(['posts.edit', 'posts.publish'])
    def get(self, request):
        ...
```

### `@require_all_permissions`

Allow access only if the user has **all** listed permissions.

```python
from tenxyte.decorators import require_all_permissions

class AdminView(APIView):
    @require_all_permissions(['users.view', 'users.manage'])
    def get(self, request):
        ...
```

### `@require_role`

Allow access only if the user has a specific role (by **code**, not name).

```python
from tenxyte.decorators import require_role

class EditorView(APIView):
    @require_role('editor')
    def post(self, request):
        ...
```

### `@require_any_role`

Allow access if the user has **at least one** of the listed roles.

```python
from tenxyte.decorators import require_any_role

class StaffView(APIView):
    @require_any_role(['admin', 'editor'])
    def get(self, request):
        ...
```

### `@require_all_roles`

Allow access only if the user has **all** listed roles.

```python
from tenxyte.decorators import require_all_roles

class SuperStaffView(APIView):
    @require_all_roles(['admin', 'editor'])
    def get(self, request):
        ...
```

### `@require_jwt`

Require a valid JWT access token. Returns `401` if missing or invalid.

```python
from tenxyte.decorators import require_jwt

class ProtectedView(APIView):
    @require_jwt
    def get(self, request):
        # request.user is set
        ...
```

### `@require_verified_email`

Require the user's email to be verified.

```python
from tenxyte.decorators import require_verified_email

class SensitiveView(APIView):
    @require_verified_email
    def post(self, request):
        ...
```

### `@require_verified_phone`

Require the user's phone number to be verified. Includes JWT validation.

```python
from tenxyte.decorators import require_verified_phone

class PhoneRequiredView(APIView):
    @require_verified_phone
    def post(self, request):
        ...
```

---

## Combining Decorators

Decorators can be stacked — they are applied bottom-up:

```python
class AdminOnlyView(APIView):
    @require_permission('admin.access')
    @require_verified_email
    def get(self, request):
        ...
```

> **Note:** `@require_permission`, `@require_any_permission`, `@require_all_permissions`, `@require_role`, and `@require_verified_email` all include JWT validation internally — no need to add `@require_jwt` explicitly when using them.

---

## API Endpoints for RBAC Management

### Permissions

```bash
# List all permissions
GET /api/v1/auth/permissions/

# Create a permission
POST /api/v1/auth/permissions/
{ "code": "posts.publish", "name": "Publish Posts" }

# Get / Update / Delete
GET    /api/v1/auth/permissions/<id>/
PUT    /api/v1/auth/permissions/<id>/
DELETE /api/v1/auth/permissions/<id>/
```

### Roles

```bash
# List all roles
GET /api/v1/auth/roles/

# Create a role
POST /api/v1/auth/roles/
{ "code": "editor", "name": "Editor", "description": "..." }

# Get / Update / Delete
GET    /api/v1/auth/roles/<id>/
PUT    /api/v1/auth/roles/<id>/
DELETE /api/v1/auth/roles/<id>/

# Manage role permissions
GET  /api/v1/auth/roles/<id>/permissions/
POST /api/v1/auth/roles/<id>/permissions/
{ "permission_codes": ["posts.publish", "posts.edit"] }
```

### User Roles & Permissions

```bash
# Assign/remove roles
GET    /api/v1/auth/users/<id>/roles/
POST   /api/v1/auth/users/<id>/roles/
DELETE /api/v1/auth/users/<id>/roles/

# Assign/remove direct permissions
GET    /api/v1/auth/users/<id>/permissions/
POST   /api/v1/auth/users/<id>/permissions/
DELETE /api/v1/auth/users/<id>/permissions/
```

---

## Assigning Admin Roles & Superusers

There are two primary ways to grant administrative privileges in Tenxyte:

### 1. Django Superuser (`is_superuser=True`)
A superuser bypasses all RBAC permission checks automatically. They also have access to the Django Admin interface (`/admin/`).
You typically create your first superuser via the command line:

```bash
python manage.py createsuperuser
```

*Note: Superusers do not need to be explicitly assigned the `admin` or `super_admin` RBAC roles.*

### 2. RBAC Admin Roles (`super_admin` or `admin`)
These are standard users assigned a role that contains high-level permissions. They don't have access to the Django Admin panel (unless `is_staff=True`), but they have administrative capabilities over the API.

To assign an Admin role to an existing user via the API:

```bash
POST /api/v1/auth/users/<user_id>/roles/
Authorization: Bearer <superuser_token>

{
  "role_codes": ["super_admin"]
}
```

Or via the Django python shell:
```python
user = User.objects.get(email="manager@example.com")
user.assign_role("admin")
```

---

## Organization-Scoped RBAC

When `TENXYTE_ORGANIZATIONS_ENABLED = True`, roles can be scoped to an organization:

```python
# A user can be "Admin" in Org A but "Viewer" in Org B
membership = OrganizationMembership.objects.get(user=user, organization=org_a)
membership.role  # OrganizationRole scoped to org_a
```

Use `@require_org_permission` to check org-scoped permissions:

```python
from tenxyte.decorators import require_org_permission

class OrgAdminView(APIView):
    @require_org_permission('org.manage')
    def post(self, request):
        # request.organization is set by the middleware
        ...
```

See [organizations.md](organizations.md) for the full Organizations guide.

---

## Default Roles

Tenxyte seeds 4 default roles via `tenxyte_seed`:

| Code | Name | Default | Permissions |
|---|---|---|---|
| `viewer` | Viewer | ✅ | `content.view` |
| `editor` | Editor | — | `content.view`, `content.create`, `content.edit` |
| `admin` | Administrator | — | Content + Users + Roles view + Permissions view |
| `super_admin` | Super Administrator | — | **All permissions** |

> **Note:** The `viewer` role is the default role (`is_default=True`) — it is automatically assigned to new users when calling `user.assign_default_role()`.

---

## Built-in Permission Codes

Tenxyte seeds 41 permissions via `tenxyte_seed`. Parent permissions (bold) grant all their children via hierarchy.

### Users

| Code | Description |
|---|---|
| **`users`** | All user permissions (parent) |
| `users.view` | View user list and details |
| `users.create` | Create new users |
| `users.edit` | Edit user information |
| `users.delete` | Delete users |
| `users.ban` | Ban/unban users |
| `users.lock` | Lock/unlock user accounts |
| **`users.roles`** | All user role permissions (parent) |
| `users.roles.view` | View user roles |
| `users.roles.assign` | Assign roles to users |
| `users.roles.remove` | Remove roles from users |
| **`users.permissions`** | All user direct permission management (parent) |
| `users.permissions.view` | View user direct permissions |
| `users.permissions.assign` | Assign direct permissions to users |
| `users.permissions.remove` | Remove direct permissions from users |

### Roles & Permissions

| Code | Description |
|---|---|
| **`roles`** | All role permissions (parent) |
| `roles.view` | View role list and details |
| `roles.create` | Create new roles |
| `roles.update` | Update role information |
| `roles.delete` | Delete roles |
| `roles.manage_permissions` | Assign/remove permissions from roles |
| **`permissions`** | All permission permissions (parent) |
| `permissions.view` | View permission list |
| `permissions.create` | Create new permissions |
| `permissions.update` | Update permission information |
| `permissions.delete` | Delete permissions |

### Applications

| Code | Description |
|---|---|
| **`applications`** | All application permissions (parent) |
| `applications.view` | View application list and details |
| `applications.create` | Create new applications |
| `applications.update` | Update application information |
| `applications.delete` | Delete applications |
| `applications.regenerate` | Regenerate application credentials |

### Content (generic)

| Code | Description |
|---|---|
| **`content`** | All content permissions (parent) |
| `content.view` | View content |
| `content.create` | Create content |
| `content.edit` | Edit content |
| `content.delete` | Delete content |
| `content.publish` | Publish content |

### System & Security

| Code | Description |
|---|---|
| **`system`** | All system permissions (parent) |
| `system.admin` | Full system administration access |
| `system.settings` | Manage system settings |
| `system.logs` | View system logs |
| `system.audit` | View audit trail |
| `dashboard.view` | Access dashboard statistics |
| `security.view` | View audit logs, login attempts, tokens |
| `gdpr.admin` | View deletion requests |
| `gdpr.process` | Process deletion requests |

---

## Seeding & Customization

### `tenxyte_seed` Command

Seed the default permissions and roles into the database:

```bash
# Seed all defaults
python manage.py tenxyte_seed

# Options
python manage.py tenxyte_seed --no-permissions   # Skip permissions
python manage.py tenxyte_seed --no-roles          # Skip roles
python manage.py tenxyte_seed --force              # Delete and recreate all
```

This command is idempotent — running it multiple times will not create duplicates.

### Swappable Models

All RBAC models can be replaced with custom implementations:

```python
# settings.py
TENXYTE_PERMISSION_MODEL = 'myapp.CustomPermission'  # extends AbstractPermission
TENXYTE_ROLE_MODEL = 'myapp.CustomRole'              # extends AbstractRole
TENXYTE_USER_MODEL = 'myapp.CustomUser'              # extends AbstractUser
```

Example custom permission model:

```python
from tenxyte.models import AbstractPermission

class CustomPermission(AbstractPermission):
    category = models.CharField(max_length=50)
    is_system = models.BooleanField(default=False)

    class Meta(AbstractPermission.Meta):
        db_table = 'custom_permissions'
```
