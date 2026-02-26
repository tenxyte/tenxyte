# Quickstart — Tenxyte Auth in 5 Minutes

## 1. Install

```bash
pip install tenxyte
```

## 2. Add to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    ...
    'tenxyte',
]
```

## 3. Add Middleware

```python
MIDDLEWARE = [
    ...
    'tenxyte.middleware.ApplicationAuthMiddleware',  # Validates X-Access-Key / X-Access-Secret
    'tenxyte.middleware.SecurityHeadersMiddleware',  # Optional: security headers
]
```

## 4. Add URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('api/auth/', include('tenxyte.urls', namespace='authentication')),
]
```

## 5. Run Migrations

Tenxyte does not ship a pre-built initial migration. Generate and apply migrations from your project:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 6. Create Your First Application

```python
from tenxyte.models import Application

app, secret = Application.create_application(name="My Web App")
print(f"Access Key:    {app.access_key}")
print(f"Access Secret: {secret}")  # Save this — shown only once
```

## 7. Make Your First Request

All API requests require the application credentials in headers:

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## 8. Authenticate Subsequent Requests

```bash
curl -X GET http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Access-Key: <your-access-key>" \
  -H "X-Access-Secret: <your-access-secret>"
```

## 9. Minimal `settings.py` Configuration

```python
# Required
SECRET_KEY = 'your-django-secret-key'

# Optional — override Tenxyte defaults
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600       # 1 hour
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 604800    # 7 days
TENXYTE_REFRESH_TOKEN_ROTATION = True
TENXYTE_MAX_LOGIN_ATTEMPTS = 5
TENXYTE_LOCKOUT_DURATION_MINUTES = 30
```

Or use a **Shortcut Secure Mode** to configure everything at once:

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # 'starter' | 'medium' | 'robust'
```

See [Settings Reference → Shortcut Secure Mode](settings.md#shortcut-secure-mode) for the full preset table.

---

## MongoDB — Django Admin Support

When using MongoDB (`django-mongodb-backend`), Django Admin requires custom app configs to set the correct auto field type. Without this, admin migrations will fail.

### Step 1 — Create custom app configs

In your main app's `apps.py`:

```python
from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig


class MongoAdminConfig(AdminConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
```

### Step 2 — Register them in `INSTALLED_APPS`

Replace the default Django admin/auth/contenttypes entries with your custom configs:

```python
INSTALLED_APPS = [
    # Replace these three defaults:
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',

    # With your MongoDB-aware versions:
    'config.apps.MongoAdminConfig',
    'config.apps.MongoAuthConfig',
    'config.apps.MongoContentTypesConfig',

    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tenxyte',
]
```

> Replace `config` with the name of your main Django app (the one containing `apps.py`).

After this, run migrations and Django Admin will work correctly with MongoDB:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Next Steps

- [Settings Reference](settings.md) — All 150+ configuration options
- [API Endpoints](endpoints.md) — Full endpoint reference with examples
- [RBAC Guide](rbac.md) — Roles, permissions, decorators
- [Security Guide](security.md) — Rate limiting, 2FA, device fingerprinting
- [Organizations Guide](organizations.md) — B2B multi-tenant setup
