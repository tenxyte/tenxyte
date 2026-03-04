# Quickstart — Tenxyte in 2 minutes

## 1. Install

```bash
pip install tenxyte
```

## 2. Configure `settings.py`

```python
# settings.py — add these 2 lines
import tenxyte
tenxyte.setup()  # auto-configures INSTALLED_APPS, AUTH_USER_MODEL, REST_FRAMEWORK, MIDDLEWARE
```

Then add the URLs:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

## 3. Bootstrap

```bash
python manage.py tenxyte_quickstart
```

This single command executes:
- `makemigrations` + `migrate`
- Seed roles and permissions (4 roles, 41 permissions)
- Create a default Application (credentials displayed)

## ✅ Ready!

In `DEBUG=True` mode (zero-config), the `development` preset is automatically activated:
- No need for `TENXYTE_JWT_SECRET_KEY` (auto-generated ephemeral key)
- No need for Application credentials (X-Access-Key disabled)
- Rate limiting, lockout, and basic security enabled

```bash
# Your first request — no special headers required in dev!
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

---

## Production

In production (`DEBUG=False`), configure explicitly:

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'your-dedicated-jwt-secret-key'  # REQUIRED
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # or 'robust'

# If Application auth is needed (recommended):
# TENXYTE_APPLICATION_AUTH_ENABLED = True  # already True by default outside dev preset
```

All individual settings remain overridable:

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'
TENXYTE_MAX_LOGIN_ATTEMPTS = 3       # overrides the preset
TENXYTE_BREACH_CHECK_ENABLED = True  # overrides the preset
```

→ [Settings Reference](settings.md) for the 150+ options.

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

- [Settings Reference](settings.md) — 150+ configuration options
- [API Endpoints](endpoints.md) — Full reference with curl examples
- [RBAC Guide](rbac.md) — Roles, permissions, decorators
- [Security Guide](security.md) — Rate limiting, 2FA, device fingerprinting
- [Organizations Guide](organizations.md) — B2B multi-tenant setup
