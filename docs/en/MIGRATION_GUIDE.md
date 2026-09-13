# Migration Guide

This guide helps you migrate from common Django authentication libraries to Tenxyte.


## Table of Contents

- [Migrating from Tenxyte v0.9.x to v1.0.0 (Packaging Inversion)](#migrating-from-tenxyte-v09x-to-v100-packaging-inversion)
- [Migrating from Tenxyte v0.9.x to v0.9.3 (Core Re-architecture)](#migrating-from-tenxyte-v09x-to-v093-core-re-architecture)
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

## Migrating from Tenxyte v0.9.x to v1.0.0 (Packaging Inversion)

**This is the only behavior change 1.0.0 introduces for existing users — everything else is
additive.** See the [Stability Contract](stability.md) for the full policy this release
establishes going forward.

### What changed

Before 1.0.0, `pip install tenxyte` installed the full Django stack (Django, DRF,
django-cors-headers, drf-spectacular, google-auth) by default. Since 1.0.0, `pip install tenxyte`
installs **only the framework-agnostic Core** (JWT, TOTP, WebAuthn services, schemas — no Django).

| | Before (≤ 0.9.x) | Since 1.0.0 |
|---|---|---|
| `pip install tenxyte` | Full Django stack | Core only |
| `pip install tenxyte[django]` | Full Django stack (redundant with default) | Full Django stack |
| `pip install tenxyte[core]` | Core only | Core only (deprecated no-op alias of the new default — see below) |

### What you need to do

**If you use Tenxyte with Django** (the vast majority of existing users), change your install
command and nothing else:

```diff
- pip install tenxyte
+ pip install tenxyte[django]
```

```diff
# requirements.txt / pyproject.toml
- tenxyte>=0.9
+ tenxyte[django]>=1.0
```

That is the entire migration. Runtime behavior with `tenxyte[django]` installed is **byte-identical**
to the previous default install: same endpoints, same settings, same migrations, same response
shapes. No code change is required in your views, settings, or models beyond the install command.

**If you use Tenxyte with FastAPI** (or a custom framework), no change is needed — you were
already using `pip install tenxyte[core]` or `tenxyte[fastapi]`, and the plain `tenxyte` default
now matches what `[core]` used to install.

**If you use `pip install tenxyte[core]` today**, it keeps working — `[core]` is retained in
1.0.0 as a deprecated no-op alias (it installs no additional dependencies of its own, since Core is
already the default). We recommend dropping the `[core]` extra entirely in favor of the bare
`tenxyte` dependency; `[core]` will be removed in a future MAJOR release after a full deprecation
cycle per the [Stability Contract](stability.md).

### The Import_Guard: what happens if Django is missing

If your code (or a dependency) does `import tenxyte` without Django installed, the import itself
**always succeeds** — `tenxyte.__version__` and every `tenxyte.core.*` symbol are usable
immediately. Only accessing a Django-only symbol without Django installed raises an explicit
error:

```python
import tenxyte
tenxyte.setup({})
# tenxyte.TenxyteMissingDependencyError:
#   'tenxyte.setup' requires the Django stack. Install it with: pip install tenxyte[django]
```

This replaces what used to be a confusing `ModuleNotFoundError` surfacing from deep inside
`tenxyte.models` with an explicit instruction. `TenxyteMissingDependencyError` is a subclass of
`ImportError`, so existing `except ImportError:` handling keeps working unchanged.

### Verifying your upgrade

```bash
pip install "tenxyte[django]>=1.0"
python manage.py check          # should pass with no changes
python manage.py migrate        # no new migrations expected
pytest                          # your existing test suite should be green
```

If anything behaves differently after upgrading to `tenxyte[django]>=1.0` beyond the install
command itself, that is a bug — please [open an issue](https://github.com/tenxyte/tenxyte/issues).

---

## Migrating from Tenxyte v0.9.x to v0.9.3 (Core Re-architecture)

Tenxyte v0.9.3 introduces a major underlying architecture change: business logic has been extracted into a framework-agnostic `tenxyte.core`. However, for existing Django projects, this update is designed to have **zero breaking changes**.

### What you need to know

1. **No changes to `settings.py`**: All your existing `TENXYTE_*` settings will continue to work exactly as before. The new Django Adapter reads `django.conf.settings` and feeds them automatically to the Core.
2. **No changes to Models or Database**: The Tenxyte database schema remains strictly identical. You do **not** need to run `makemigrations` or `migrate` when upgrading.
3. **No changes to API Endpoints**: All URLs, JSON request payloads, and JSON responses remain exactly the same.
4. **No changes to Tokens**: Existing JWTs, Refresh Tokens, and Passkeys will continue to function without any interruption.

### How to Upgrade

Simply upgrade the package via pip:

```bash
pip install tenxyte==0.9.3
```

*(If you are using specific extras like Twilio or SendGrid, you might want to switch to the new hierarchical extras syntax, though the default `pip install tenxyte` continues to install the full Django stack.)*

```bash
pip install "tenxyte[django,twilio]"
```

### Deprecation Warnings

While your code will continue to work, some deep internal imports have been structurally moved. For instance, if you were directly importing Services instead of using the REST endpoints, you may see `DeprecationWarning`s.

```python
# Old import (still works in v0.9.3 but raises a DeprecationWarning)
from tenxyte.services.auth_service import AuthService

# Recommended: use tenxyte.core services with adapters instead
from tenxyte.core.jwt_service import JWTService
```

These aliased imports will be kept until v1.0.0, giving you plenty of time to update any customized overrides.

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

> **Note**: The exact URL depends on where you mount `tenxyte.urls` in your `urls.py`. If you configured `path('api/v1/auth/', include('tenxyte.urls'))`, the endpoints will be prefixed with `/api/v1/auth/`.
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

| dj-rest-auth endpoint | Tenxyte equivalent (assuming `path('api/v1/auth/', ...)` in your `urls.py`) |
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
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 604800,
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
