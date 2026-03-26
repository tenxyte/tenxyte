# Admin Accounts Management

Admin accounts are required to manage users, configure Role-Based Access Control (RBAC), view audit logs, and access the built-in Django Administration panel. Tenxyte provides two distinct levels of administrative accounts.

---

## Table of Contents

- [Overview](#overview)
- [1. Django Superuser](#1-django-superuser)
  - [Creation](#creation)
  - [Capabilities](#capabilities)
- [2. RBAC Admin Roles](#2-rbac-admin-roles)
  - [Creation](#creation-1)
  - [Capabilities](#capabilities-1)
- [Comparison](#comparison)

---

## Overview

In Tenxyte, you can have a full **Superuser** (which bypasses all permission checks) or an **RBAC Admin** (a standard user assigned the `admin` or `super_admin` role). Depending on your security requirements, you might only grant Superuser status to backend developers, while support staff gets the `admin` role.

---

## 1. Django Superuser

A Django Superuser is essentially a "root" account for your application. This user has `is_superuser=True` and `is_staff=True` in the database.

### Creation

Superusers are typically created via the command line. This is almost always the very first account you create when setting up Tenxyte for the first time.

```bash
python manage.py createsuperuser
```

Prompt example:
```
Email address: admin@example.com
Password: 
Password (again): 
Superuser created successfully.
```

### Capabilities

- **Bypasses RBAC:** `user.has_permission("any.permission")` always returns `True`.
- **Admin Panel Access:** Can log into `http://localhost:8000/admin/` to view raw database tables.
- **API Access:** Has implied access to every single API endpoint automatically.

*Note: You do not need to assign any RBAC roles to a Superuser.*

---

## 2. RBAC Admin Roles

An RBAC Admin is a regular user who has been assigned a powerful role (e.g., `admin` or `super_admin`). They do not have `is_superuser=True`.

### Creation

To create an RBAC Admin, the user must first register an account normally. Then, an existing Superuser or Admin can elevate them via the API:

```bash
POST /api/v1/auth/users/<user_id>/roles/
Authorization: Bearer <superuser_token>

{
  "role_code": "super_admin"
}
```

Alternatively, you can elevate a user programmatically via the Django shell:

```python
# python manage.py shell
from tenxyte.models import get_user_model
User = get_user_model()

user = User.objects.get(email="manager@example.com")
user.assign_role("super_admin")
```

### Capabilities

- **Strict RBAC:** They only have the permissions explicitly granted to their role.
- **No Django Admin Access:** By default, they cannot access `/admin/` unless you also manually set `is_staff=True` on their account.
- **Safer for Teams:** Ideal for customer support, HR, or product managers who need widespread API access without raw database access.
- **2FA Enforcement:** Admin and super_admin users are required to enable 2FA before logging in. If 2FA is not configured, the login returns `403 ADMIN_2FA_SETUP_REQUIRED`.

See the [RBAC Guide](rbac.md) for details on built-in roles and permissions.

### Admin API Endpoints

Admins with the appropriate permissions can access the following API groups (documented in [Endpoints Reference](endpoints.md)):

| Category | Endpoints | Required Permission |
|---|---|---|
| **User Management** | `GET/PUT /admin/users/`, ban, unban, lock, unlock | `users.view`, `users.ban`, `users.lock` |
| **Audit Logs** | `GET /admin/audit-logs/` | `audit.view` |
| **Login Attempts** | `GET /admin/login-attempts/` | `audit.view` |
| **Token Management** | `GET /admin/refresh-tokens/`, revoke, blacklist cleanup | `tokens.view`, `tokens.revoke` |
| **GDPR** | `GET /admin/deletion-requests/`, process | `gdpr.view`, `gdpr.process` |
| **Dashboard** | `GET /dashboard/stats/`, auth, security, gdpr, orgs | `dashboard.view` |

---

## Comparison

| Feature | Django Superuser | RBAC `super_admin` | RBAC `admin` |
|---|---|---|---|
| **Bypass Permissions** | ✅ Yes | ❌ No (Relies on assigned perms) | ❌ No |
| **Django Admin (`/admin/`) access** | ✅ Yes | ❌ No (requires `is_staff`) | ❌ No |
| **Manage Users & Roles (API)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **2FA Required at Login** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Creation Method** | CLI (`createsuperuser`) | API or Shell | API or Shell |
| **Best For** | Developers, Sysadmins | Team Leads | Support Staff |

