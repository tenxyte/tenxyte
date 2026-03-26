# Quickstart — Tenxyte in 2 minutes

## Table of Contents

- [Install](#1-install)
- [Configure](#2-configure-settingspy)
- [Bootstrap](#3-bootstrap)
- [Ready!](#-ready)
- [Login & Use JWT](#4-login--use-your-jwt)
- [Production](#production)
- [Manual Configuration](#manual-configuration-alternative)
- [MongoDB](#mongodb)
- [Next Steps](#next-steps)

---

## 1. Install

```bash
pip install tenxyte
```

## 2. Configure `settings.py`

```python
# settings.py — Add this at the END of the file (after INSTALLED_APPS, MIDDLEWARE, etc.)
import tenxyte
tenxyte.setup(globals())

# `tenxyte.setup(globals())` automatically injects the minimal required configuration:
# - Sets AUTH_USER_MODEL = 'tenxyte.User'
# - Adds 'rest_framework' and 'tenxyte' to INSTALLED_APPS
# - Configures DEFAULT_AUTHENTICATION_CLASSES and DEFAULT_SCHEMA_CLASS for REST_FRAMEWORK
# - Adds 'tenxyte.middleware.ApplicationAuthMiddleware' to MIDDLEWARE
# Note: It will NEVER overwrite settings you have already explicitly defined.
```

### Understanding `tenxyte.setup()` VS `tenxyte.setup(globals())`
By default, calling `tenxyte.setup()` will try to find the Django settings module and modify its properties. However, inside your `settings.py` file, standard variables you just defined (like `INSTALLED_APPS` or `MIDDLEWARE`) might not be fully loaded into the module registry yet. 

Passing `globals()` tells Tenxyte to directly modify the local dictionary of variables in your `settings.py`. **This is the recommended and safest approach**, as it strictly ensures that your `INSTALLED_APPS`, `MIDDLEWARE`, and `REST_FRAMEWORK` dictionaries are cleanly appended to without risking module resolution issues. Always place it at the **very bottom** of your `settings.py`.

Then add the URLs:

```python
# urls.py
from django.urls import path, include
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'{api_prefix}/auth/', include('tenxyte.urls')),
]
```

## 3. Bootstrap

```bash
python manage.py tenxyte_quickstart
```

This single command executes:
- `makemigrations` + `migrate`
- Seed roles and permissions (4 roles, 47 permissions)
- Create a default Application (credentials displayed)

**Options:**

| Flag | Description |
|---|---|
| `--no-seed` | Skip seeding roles and permissions |
| `--no-app` | Skip creating the default Application |
| `--app-name "My App"` | Custom name for the default Application |

## 4. Create an Admin Account

Some features and views (like the Django Admin Panel or RBAC configuration) require an administrator account. You can create your initial Superuser using the standard Django command:

```bash
python manage.py createsuperuser
```

Follow the prompts to set your email and password. This account is created with `is_staff=True` and `is_superuser=True`, granting you full access to all endpoints, including the built-in `http://localhost:8000/admin/` interface.

## ✅ Ready!

In `DEBUG=True` mode (zero-config), the `development` preset is automatically activated:
- No need for `TENXYTE_JWT_SECRET_KEY` (auto-generated ephemeral key)
- Application credentials (`X-Access-Key` / `X-Access-Secret`) are **required** — use the credentials displayed by `tenxyte_quickstart`
- Rate limiting, lockout, and basic security enabled

> **Note:** The Access Secret is bcrypt-hashed and shown **only once** during bootstrap.
> If lost, regenerate credentials via `POST /api/v1/auth/applications/{id}/regenerate/`.

```bash
# Register your first user — use the credentials from tenxyte_quickstart
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

## 4. Login & Use Your JWT

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "a1b2c3d4e5...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_2fa_enabled": false
  }
}
```

```bash
# Use the access token for authenticated requests
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>"
```

---

## Production

In production (`DEBUG=False`), configure explicitly:

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'your-dedicated-jwt-secret-key'  # REQUIRED
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # or 'robust'
```

All individual settings remain overridable:

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'
TENXYTE_MAX_LOGIN_ATTEMPTS = 3       # overrides the preset
TENXYTE_BREACH_CHECK_ENABLED = True  # overrides the preset
```

→ [Settings Reference](settings.md) for the 115+ options.

---

## Manual Configuration (Alternative)

If you prefer not to use `tenxyte.setup()`:

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'tenxyte',
]

AUTH_USER_MODEL = 'tenxyte.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}

MIDDLEWARE = [
    ...,
    'tenxyte.middleware.ApplicationAuthMiddleware',
]
```

Then run:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py tenxyte_seed
```

---

## MongoDB

For MongoDB, see the [MongoDB configuration](#mongodb--required-configuration) section in the README.

---

## Next Steps

- [Settings Reference](settings.md) — 115+ configuration options
- [API Endpoints](endpoints.md) — Full reference with curl examples
- [RBAC Guide](rbac.md) — Roles, permissions, decorators
- [Security Guide](security.md) — Rate limiting, 2FA, device fingerprinting
- [Organizations Guide](organizations.md) — B2B multi-tenant setup
