# Migration Guide

This guide helps you migrate from common Django authentication libraries to Tenxyte.


## Table of Contents

- [Migrating from `djangorestframework-simplejwt`](#migrating-from-djangorestframework-simplejwt)
  - [Settings Mapping](#settings-mapping)
  - [Authentication Class](#authentication-class)
  - [URL Migration](#url-migration)
  - [Token Format Compatibility](#token-format-compatibility)
  - [User Model Migration](#user-model-migration)
- [Migrating from `dj-rest-auth`](#migrating-from-dj-rest-auth)
  - [Endpoint Mapping](#endpoint-mapping)
  - [Response Format Changes](#response-format-changes)
- [Migrating from a Custom Auth Implementation](#migrating-from-a-custom-auth-implementation)
  - [Step 1 — Preserve existing users](#step-1--preserve-existing-users)
  - [Step 2 — Migrate roles and permissions](#step-2--migrate-roles-and-permissions)
  - [Step 3 — Update frontend headers](#step-3--update-frontend-headers)
- [Breaking Changes Checklist](#breaking-changes-checklist)
- [Need Help?](#need-help)

---


## Migrating from `djangorestframework-simplejwt`

### Settings Mapping

| simplejwt | Tenxyte | Notes |
|---|---|---|
| `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']` | `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | In seconds (not `timedelta`) |
| `SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']` | `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | In seconds |
| `SIMPLE_JWT['ROTATE_REFRESH_TOKENS']` | `TENXYTE_REFRESH_TOKEN_ROTATION` | Boolean |
| `SIMPLE_JWT['BLACKLIST_AFTER_ROTATION']` | `TENXYTE_TOKEN_BLACKLIST_ENABLED` | Boolean |
| `SIMPLE_JWT['SIGNING_KEY']` | `TENXYTE_JWT_SECRET_KEY` | String |
| `SIMPLE_JWT['AUTH_HEADER_TYPES']` | Always `Bearer` | Fixed in Tenxyte |
| `SIMPLE_JWT['USER_ID_FIELD']` | Always `id` (Integer/String) | Fixed in Tenxyte |

### Authentication Class

```python
# Before (simplejwt)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# After (Tenxyte)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}
```

### URL Migration

```python
# Before (simplejwt)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]

# After (Tenxyte)
urlpatterns = [
    path('api/auth/', include('tenxyte.urls')),
    # Login:   POST /api/auth/login/email/
    # Refresh: POST /api/auth/refresh/
]

> **Note**: If you have configured `TENXYTE_API_PREFIX = '/api/v1'` in `settings.py`, the endpoints will be prefixed accordingly.
```

### Token Format Compatibility

Tenxyte tokens are **not compatible** with simplejwt tokens. All existing tokens will become invalid after migration. Plan for:

1. A maintenance window or a grace period where both systems run in parallel
2. Client-side re-authentication after the migration window

### User Model Migration

If your custom user model only included fields that Tenxyte already handles (e.g., `phone`, `first_name`, `last_name`), you can switch to the default Tenxyte model:

```python
# Before
from django.contrib.auth.models import AbstractUser

class MyUser(AbstractUser):
    phone = models.CharField(...)

# After — Tenxyte's User already includes phone, 2FA, etc.
# Set in settings.py:
AUTH_USER_MODEL = 'tenxyte.User'
```

If your custom user model included **project-specific fields** (e.g., `company`, `avatar`), you must extend Tenxyte's `AbstractUser`:

```python
# After — Extend Tenxyte's AbstractUser
from tenxyte.models import AbstractUser

class MyUser(AbstractUser):
    company = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'

# Set in settings.py:
TENXYTE_USER_MODEL = 'myapp.MyUser'
AUTH_USER_MODEL = 'myapp.MyUser'  # Also set this for Django
```

After updating your models and settings, run:
```bash
python manage.py makemigrations --empty myapp --name migrate_to_tenxyte_user
python manage.py migrate
```

---

## Migrating from `dj-rest-auth`

### Endpoint Mapping

| dj-rest-auth endpoint | Tenxyte equivalent (with `TENXYTE_API_PREFIX=/api/v1`) |
|---|---|
| `POST /auth/login/` | `POST /api/v1/auth/login/email/` |
| `POST /auth/logout/` | `POST /api/v1/auth/logout/` |
| `POST /auth/registration/` | `POST /api/v1/auth/register/` |
| `POST /auth/password/change/` | `POST /api/v1/auth/password/change/` |
| `POST /auth/password/reset/` | `POST /api/v1/auth/password/reset/request/` |
| `POST /auth/password/reset/confirm/` | `POST /api/v1/auth/password/reset/confirm/` |
| `GET /auth/user/` | `GET /api/v1/auth/me/` |
| `PUT /auth/user/` | `PUT /api/v1/auth/me/` |

### Response Format Changes

dj-rest-auth returns tokens inside a `key` field (Knox) or `access`/`refresh` (JWT adapter). Tenxyte always returns a detailed payload:

```json
{
  "access_token": "<access token>",
  "refresh_token": "<refresh token>",
  "access_token_expires_at": "...",
  "access_token_jti": "...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user": { ... },
  "requires_2fa": false,
  "session_id": "...",
  "device_id": "..."
}
```

Update your frontend token handling accordingly (focusing on `access_token` and `refresh_token` keys).

---

## Migrating from a Custom Auth Implementation

### Step 1 — Preserve existing users

Tenxyte's `User` model uses standard primary keys (usually Integers) and stores passwords using bcrypt with SHA-256 pre-hashing. Existing bcrypt-hashed passwords from Django's default PBKDF2 hasher **will not** work directly.

Option A — Force password reset for all users:
```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.all().update(password='!')  # invalidates all passwords
"
```
Then trigger a mass password-reset email from your admin panel.

Option B — Implement a one-time migration hasher that accepts PBKDF2 on first login and re-hashes with bcrypt transparently (recommended for zero-downtime migrations).

### Step 2 — Migrate roles and permissions

If you had custom groups/permissions, map them to Tenxyte RBAC roles using the `assign_role()` method on the user model:

```python
# management command or shell script
from tenxyte.models import get_user_model, get_role_model

User = get_user_model()
Role = get_role_model()

# Ensure the role exists
Role.objects.get_or_create(code='admin', defaults={'name': 'Admin'})

# Assign role to a user
for user in User.objects.all():
    user.assign_role('admin')  # uses role code, not name
```

See [RBAC Guide](rbac.md) for the full role/permission model.

### Step 3 — Update frontend headers

Tenxyte uses `Authorization: Bearer <token>` for JWT. If you used session cookies or custom headers, update your frontend HTTP client.

```http
Authorization: Bearer <access_token>
```

---

## Breaking Changes Checklist

- [ ] `AUTH_USER_MODEL` changed to `tenxyte.User`
- [ ] All existing JWT tokens are invalidated
- [ ] Password hashes may need to be reset if migrating from PBKDF2
- [ ] Endpoint URLs have changed (see mapping tables above)
- [ ] Response format for login changed (no `key` field, use `access_token`/`refresh_token` keys)
- [ ] Custom groups/permissions must be migrated to Tenxyte RBAC roles

---

## Need Help?

- [Settings Reference](settings.md) — all configuration options
- [RBAC Guide](rbac.md) — roles and permissions
- [Security Guide](security.md) — security hardening after migration
- [Troubleshooting](troubleshooting.md) — common post-migration errors
