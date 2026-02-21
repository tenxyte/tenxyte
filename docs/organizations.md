# Organizations Guide — B2B Multi-Tenant Setup

Tenxyte supports hierarchical organizations with org-scoped RBAC, member management, and invitations.

> **Opt-in feature** — disabled by default for backward compatibility.

---

## Enable Organizations

```python
# settings.py
TENXYTE_ORGANIZATIONS_ENABLED = True
```

Then run migrations:
```bash
python manage.py migrate
```

---

## Configuration

```python
TENXYTE_ORGANIZATIONS_ENABLED = True
TENXYTE_ORG_ROLE_INHERITANCE = True   # Roles propagate down the hierarchy
TENXYTE_ORG_MAX_DEPTH = 5             # Max hierarchy depth
TENXYTE_ORG_MAX_MEMBERS = 0           # 0 = unlimited
```

---

## Concepts

### Organization

A named entity that groups users. Organizations can be nested (parent → children).

```
Acme Corp (root)
├── Engineering
│   ├── Backend Team
│   └── Frontend Team
└── Sales
    └── EMEA
```

### OrganizationRole

A role scoped to an organization (e.g. `admin`, `member`, `viewer`). Different from global RBAC roles.

### OrganizationMembership

Links a user to an organization with a specific role.

---

## API Usage

### Create an Organization

```bash
POST /api/auth/organizations/
Authorization: Bearer <token>

{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Our main organization"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "parent": null,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### Create a Sub-Organization

```bash
POST /api/auth/organizations/
{
  "name": "Engineering",
  "slug": "acme-engineering",
  "parent_id": 1
}
```

### List My Organizations

```bash
GET /api/auth/organizations/list/
```

### Get Organization Details

```bash
GET /api/auth/organizations/detail/?org_id=1
```

### Get Organization Tree

```bash
GET /api/auth/organizations/tree/?org_id=1
```

**Response:**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "children": [
    {
      "id": 2,
      "name": "Engineering",
      "children": [
        { "id": 3, "name": "Backend Team", "children": [] },
        { "id": 4, "name": "Frontend Team", "children": [] }
      ]
    }
  ]
}
```

### Update an Organization

```bash
PUT /api/auth/organizations/update/?org_id=1
{
  "name": "Acme Corporation",
  "description": "Updated description"
}
```

### Delete an Organization

```bash
DELETE /api/auth/organizations/delete/?org_id=1
```

---

## Member Management

### List Members

```bash
GET /api/auth/organizations/members/?org_id=1
```

**Response:**
```json
[
  {
    "user_id": 42,
    "email": "alice@acme.com",
    "role": "admin",
    "joined_at": "2026-01-01T00:00:00Z"
  }
]
```

### Add a Member

```bash
POST /api/auth/organizations/members/add/
{
  "org_id": 1,
  "user_id": 42,
  "role": "member"
}
```

### Update a Member's Role

```bash
PUT /api/auth/organizations/members/42/?org_id=1
{
  "role": "admin"
}
```

### Remove a Member

```bash
DELETE /api/auth/organizations/members/42/remove/?org_id=1
```

### Invite a Member by Email

```bash
POST /api/auth/organizations/invitations/
{
  "org_id": 1,
  "email": "newmember@example.com",
  "role": "member"
}
```

An invitation email is sent. The user can accept by registering or logging in.

---

## Organization Roles

List available org-scoped roles:

```bash
GET /api/auth/org-roles/
```

Create org roles programmatically:

```python
from tenxyte.models import OrganizationRole

role = OrganizationRole.objects.create(
    name="admin",
    organization=org,
    permissions=["org.manage", "org.members.manage"]
)
```

---

## Role Inheritance

When `TENXYTE_ORG_ROLE_INHERITANCE = True`, roles assigned at a parent organization propagate to all child organizations.

Example:
- Alice is `admin` in `Acme Corp`
- She automatically has `admin` rights in `Engineering`, `Backend Team`, etc.

To check effective permissions in a specific org:

```python
membership = OrganizationMembership.objects.get(user=alice, organization=backend_team)
# membership.role may be inherited from parent
```

---

## Python API

```python
from tenxyte.services import OrganizationService

service = OrganizationService()

# Create
success, org, error = service.create_organization(
    name="Acme Corp",
    slug="acme-corp",
    owner=user,
    application=app
)

# Add member
success, membership, error = service.add_member(
    organization=org,
    user=new_user,
    role_name="member",
    added_by=admin_user
)

# Get tree
tree = service.get_organization_tree(org)

# Check membership
is_member = service.is_member(user, org)
```

---

## Org-Scoped RBAC in Views

Use `@require_org_permission` to protect views with org-scoped permissions:

```python
from tenxyte.decorators import require_org_permission

class OrgSettingsView(APIView):
    @require_org_permission('org.manage')
    def post(self, request):
        # request.organization is set by middleware
        org = request.organization
        ...
```

The middleware resolves the organization from the request (e.g. via `X-Org-ID` header or query param).

---

## Data Model

```
Organization
├── id
├── name
├── slug (unique)
├── description
├── parent (FK → Organization, nullable)
├── is_active
├── application (FK → Application)
├── created_at
└── updated_at

OrganizationRole
├── id
├── name
├── organization (FK → Organization)
├── permissions (M2M → Permission)
└── created_at

OrganizationMembership
├── id
├── user (FK → User)
├── organization (FK → Organization)
├── role (FK → OrganizationRole)
├── invited_by (FK → User, nullable)
├── joined_at
└── is_active
```

---

## Settings Reference

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_ORGANIZATIONS_ENABLED` | `False` | Enable the feature |
| `TENXYTE_ORG_ROLE_INHERITANCE` | `True` | Propagate roles down hierarchy |
| `TENXYTE_ORG_MAX_DEPTH` | `5` | Max nesting depth |
| `TENXYTE_ORG_MAX_MEMBERS` | `0` | Max members per org (0 = unlimited) |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Swappable model |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Swappable model |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL` | `'tenxyte.OrganizationMembership'` | Swappable model |
