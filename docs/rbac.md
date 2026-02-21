# RBAC Guide — Roles, Permissions & Decorators

Tenxyte provides a flexible Role-Based Access Control (RBAC) system with:
- **Permissions** — atomic capabilities (e.g. `posts.publish`, `users.ban`)
- **Roles** — named groups of permissions with optional hierarchy
- **Decorators** — protect views with a single line of code

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

### Roles

A role groups multiple permissions. Roles can inherit from a parent role.

```python
from tenxyte.models import Role

# Create a base role
editor = Role.objects.create(name="Editor", description="Can edit content")
editor.permissions.add(Permission.objects.get(code="posts.edit"))

# Create a child role (inherits editor permissions)
senior_editor = Role.objects.create(name="Senior Editor", parent=editor)
senior_editor.permissions.add(Permission.objects.get(code="posts.publish"))

# Assign to user
user.roles.add(editor)

# Check (includes inherited permissions)
user.has_permission("posts.edit")    # True (from editor role)
user.has_permission("posts.publish") # False (only senior_editor has it)
```

### Permission Resolution Order

When checking `user.has_permission("x")`, Tenxyte checks in this order:
1. User's **direct permissions**
2. Permissions from user's **direct roles**
3. Permissions from **parent roles** (recursive, up the hierarchy)

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
    @require_any_permission('posts.edit', 'posts.publish')
    def get(self, request):
        ...
```

### `@require_all_permissions`

Allow access only if the user has **all** listed permissions.

```python
from tenxyte.decorators import require_all_permissions

class AdminView(APIView):
    @require_all_permissions('users.view', 'users.manage')
    def get(self, request):
        ...
```

### `@require_role`

Allow access only if the user has a specific role (by name).

```python
from tenxyte.decorators import require_role

class EditorView(APIView):
    @require_role('Editor')
    def post(self, request):
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

### `@require_2fa`

Require 2FA to be enabled for the user.

```python
from tenxyte.decorators import require_2fa

class HighSecurityView(APIView):
    @require_2fa
    def post(self, request):
        ...
```

---

## Combining Decorators

Decorators can be stacked — they are applied bottom-up:

```python
class AdminOnlyView(APIView):
    @require_jwt
    @require_permission('admin.access')
    @require_verified_email
    def get(self, request):
        ...
```

---

## API Endpoints for RBAC Management

### Permissions

```bash
# List all permissions
GET /api/auth/permissions/

# Create a permission
POST /api/auth/permissions/
{ "code": "posts.publish", "name": "Publish Posts" }

# Get / Update / Delete
GET    /api/auth/permissions/<id>/
PUT    /api/auth/permissions/<id>/
DELETE /api/auth/permissions/<id>/
```

### Roles

```bash
# List all roles
GET /api/auth/roles/

# Create a role
POST /api/auth/roles/
{ "name": "Editor", "description": "...", "parent": null }

# Get / Update / Delete
GET    /api/auth/roles/<id>/
PUT    /api/auth/roles/<id>/
DELETE /api/auth/roles/<id>/

# Manage role permissions
GET  /api/auth/roles/<id>/permissions/
POST /api/auth/roles/<id>/permissions/
{ "permission_id": 5 }
```

### User Roles & Permissions

```bash
# Assign/remove roles
GET    /api/auth/users/<id>/roles/
POST   /api/auth/users/<id>/roles/
DELETE /api/auth/users/<id>/roles/

# Assign/remove direct permissions
GET    /api/auth/users/<id>/permissions/
POST   /api/auth/users/<id>/permissions/
DELETE /api/auth/users/<id>/permissions/
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

## Built-in Permission Codes

Tenxyte uses these permission codes internally for its own admin endpoints:

| Code | Description |
|---|---|
| `dashboard.view` | Access dashboard statistics |
| `users.view` | View user list and profiles |
| `users.manage` | Create/update users |
| `users.ban` | Ban/unban users |
| `users.lock` | Lock/unlock user accounts |
| `permissions.view` | View permissions |
| `permissions.manage` | Create/update/delete permissions |
| `roles.view` | View roles |
| `roles.manage` | Create/update/delete roles |
| `applications.view` | View applications |
| `applications.manage` | Create/update/delete applications |
| `audit.view` | View audit logs and login attempts |
| `audit.manage` | Cleanup tokens, manage audit data |
| `gdpr.view` | View deletion requests |
| `gdpr.manage` | Process deletion requests |
