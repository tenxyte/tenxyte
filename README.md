[Lire cette documentation en Français](README.fr.md)

![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Framework-Agnostic Python Authentication in minutes — JWT, RBAC, 2FA, Magic Links, Passkeys, Social Login, Breach Check, Organizations (B2B), multi-application support.

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-6.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml)

---

## Table of Contents

- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quickstart (Dev vs Prod)](#quickstart--development)
- [Request & Response Examples](#request--response-examples)
- [Endpoints & Documentation](#endpoints--documentation)
- [Documentation Structure](#-documentation-structure)
- [Architecture: Core & Adapters](#architecture-core--adapters)
- [Supported Databases](#supported-databases)
- [Periodic Maintenance](#periodic-maintenance)
- [Customization & Extension](#customization--extension)
- [Development & Testing](#development--testing)
- [Troubleshooting](#frequently-asked-questions--troubleshooting)
- [Contributing](#contributing)
- [License & Support](#license)

---

## Key Features

✨ **Core Authentication**
- JWT with access + refresh tokens, rotation, blacklisting
- Login via email / phone, Magic Links (passwordless), Passkeys (WebAuthn/FIDO2)
- Social Login — Google, GitHub, Microsoft, Facebook
- Multi-application support (`X-Access-Key` / `X-Access-Secret`)

🔐 **Security**
- 2FA (TOTP) — Google Authenticator, Authy
- OTP via email and SMS, password breach check (HaveIBeenPwned, k-anonymity)
- Account lockout, session & device limits, rate limiting, CORS, security headers
- Audit logging

👥 **RBAC**
- Hierarchical roles, direct permissions (per-user and per-role)
- 8 decorators + DRF permission classes

🏢 **Organizations (B2B)**
- Multi-tenant with hierarchical tree, per-org roles & memberships

📱 **Communication**
- SMS: Twilio, NGH Corp, Console
- Email: Django (recommended), SendGrid, Console

⚙️ **Shortcut Secure Mode**
- One-line security preset: `TENXYTE_SHORTCUT_SECURE_MODE = 'medium'`
- Modes: `development` / `medium` / `robust` — all individually overridable

---

## Prerequisites

- Python 3.10+ (3.11+ recommended)
- `pip` and a virtual environment
- **Django 6.0+** (for the Django adapter) or **FastAPI 0.135+** (for the FastAPI adapter)
- Database (PostgreSQL recommended for production)

## Installation

```bash
pip install tenxyte              # Includes Django adapter (backward compatible)
pip install tenxyte[core]        # Core only — no framework, bring your own
pip install tenxyte[fastapi]     # FastAPI adapter + Core

# Optional Extras (work with any adapter)
pip install tenxyte[twilio]      # SMS via Twilio
pip install tenxyte[sendgrid]    # Email via SendGrid
pip install tenxyte[mongodb]     # MongoDB support
pip install tenxyte[postgres]    # PostgreSQL
pip install tenxyte[mysql]       # MySQL/MariaDB
pip install tenxyte[webauthn]    # Passkeys / FIDO2
pip install tenxyte[all]         # Everything included
```

## Quickstart — Development

### 1. Install

```bash
pip install tenxyte
```

### 2. Configure (`settings.py` + `urls.py`)

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
Passing `globals()` tells Tenxyte to directly modify the local dictionary of variables in your `settings.py`. **This is the recommended and safest approach**, as it strictly ensures that your `INSTALLED_APPS`, `MIDDLEWARE`, and `REST_FRAMEWORK` dictionaries are cleanly appended to without risking module resolution issues. Always place it at the **very bottom** of your `settings.py`.

```python
# urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

### 3. Bootstrap

```bash
python manage.py tenxyte_quickstart
# → makemigrations + migrate + seed roles/permissions + create Application
python manage.py runserver
```

> ⚠️ In `DEBUG=True`, Tenxyte activates a "zero-configuration" behavior: ephemeral JWT, `X-Access-Key` disabled, relaxed limits.

```bash
# First request — no special headers needed in dev!
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

### Quickstart — Production

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'your-dedicated-long-random-secret'   # REQUIRED
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'                        # 'medium' | 'robust'
TENXYTE_APPLICATION_AUTH_ENABLED = True
```

- Configure a resilient DB backend (PostgreSQL recommended)
- Configure an email provider (e.g., SendGrid)
- Enable TLS/HTTPS in front

---

## Request & Response Examples

> In production, routes require `X-Access-Key` and `X-Access-Secret` headers. In `DEBUG=True` (dev mode), they are not required.

### Register

**Request:**

```http
POST /api/v1/auth/register/
Content-Type: application/json
X-Access-Key: <app_key>
X-Access-Secret: <app_secret>

{
  "email": "user@example.com",
  "password": "SecureP@ss1!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201 Created):**

```json
{
  "message": "Registration successful",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "phone_country_code": null,
    "phone_number": null,
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "roles": [],
    "permissions": [],
    "created_at": "2026-03-03T22:00:00Z",
    "last_login": null
  },
  "verification_required": {
    "email": true,
    "phone": false
  }
}
```

> 💡 To log the user in immediately after registration, include `"login": true` in the request — JWT tokens will then be included in the response (`access_token`, `refresh_token`, `token_type`, `expires_in`).

### Login (email)

**Request:**

```http
POST /api/v1/auth/login/email/
Content-Type: application/json
X-Access-Key: <app_key>
X-Access-Secret: <app_secret>

{
  "email": "user@example.com",
  "password": "SecureP@ss1!"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "desktop/windows",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "phone": "",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false
  }
}
```

> If 2FA is enabled on the account, add `"totp_code": "123456"` to the request.

### curl — Quick Summary

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'

# Authenticated request
curl http://localhost:8000/api/v1/auth/me/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Authorization: Bearer <access_token>"
```

For more complete examples with responses, see: [docs/en/endpoints.md](docs/en/endpoints.md)

---

## Endpoints & Documentation

### Interactive Documentation

To enable the interactive documentation endpoints (Swagger UI, ReDoc, and OpenAPI Schema), make sure they are included in your routing, normally done in your main `urls.py`:

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns = [
    # ... your other urls
    path(f'{api_prefix}/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{api_prefix}/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{api_prefix}/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

Once configured, start your server:

```bash
python manage.py runserver

# Swagger UI: http://localhost:8000/api/v1/docs/
# ReDoc:      http://localhost:8000/api/v1/docs/redoc/
# Schema:     http://localhost:8000/api/v1/docs/schema/
```

- [**Static Site**](docs_site/index.html) — Full documentation
- [**Postman Collection**](tenxyte_api_collection.postman_collection.json) — Ready-to-use collection
- [**Endpoint Reference**](docs/en/endpoints.md) — All endpoints with curl examples

### Endpoint Overview

| Category | Key Endpoints |
|---|---|
| **Auth** | `register`, `login/email`, `login/phone`, `refresh`, `logout`, `logout/all` |
| **Social** | `social/google`, `social/github`, `social/microsoft`, `social/facebook` |
| **Magic Link** | `magic-link/request`, `magic-link/verify` |
| **Passkeys** | `webauthn/register/begin+complete`, `webauthn/authenticate/begin+complete` |
| **OTP** | `otp/request`, `otp/verify/email`, `otp/verify/phone` |
| **Password** | `password/reset/request`, `password/reset/confirm`, `password/change` |
| **2FA** | `2fa/setup`, `2fa/confirm`, `2fa/disable`, `2fa/backup-codes` |
| **Profile** | `me/`, `me/roles/` |
| **RBAC** | `roles/`, `permissions/`, `users/{id}/roles/`, `users/{id}/permissions/` |
| **Applications** | `applications/` (CRUD + regenerate) |

---

## 📚 Documentation Structure

### 📖 **Developer Guides**
- [**Quickstart**](docs/en/quickstart.md) - Get started in 2 minutes with Django
- [**FastAPI Quickstart**](docs/en/fastapi_quickstart.md) - Get started with FastAPI
- [**Settings Reference**](docs/en/settings.md) - All 95+ configuration options
- [**API Endpoints**](docs/en/endpoints.md) - Full endpoint reference with examples
- [**Admin Accounts**](docs/en/admin.md) - Manage Superusers and RBAC Admins
- [**Applications Guide**](docs/en/applications.md) - Manage API clients and credentials
- [**RBAC Guide**](docs/en/rbac.md) - Roles, permissions, and decorators
- [**Security Guide**](docs/en/security.md) - Security features and best practices
- [**Organizations Guide**](docs/en/organizations.md) - B2B multi-tenant setup
- [**AIRS Guide**](docs/en/airs.md) - AI Responsibility & Security
- [**Migration Guide**](docs/en/MIGRATION_GUIDE.md) - Migration from dj-rest-auth, simplejwt

### 🔧 **Technical Documentation**
- [**Architecture Guide**](docs/en/architecture.md) - Core & Adapters (Hexagonal) architecture
- [**Async Guide**](docs/en/async_guide.md) - Async/await patterns and best practices
- [**Task Service**](docs/en/task_service.md) - Background job processing
- [**Custom Adapters Guide**](docs/en/custom_adapters.md) - Creating custom adapters
- [**Schemas Reference**](docs/en/schemas.md) - Reusable schema components
- [**Testing Guide**](docs/en/TESTING.md) - Testing strategies and examples
- [**Periodic Tasks**](docs/en/periodic_tasks.md) - Scheduled maintenance and cleanup tasks
- [**Troubleshooting**](docs/en/troubleshooting.md) - Common issues and solutions
- [**Contributing**](docs/en/CONTRIBUTING.md) - How to contribute to Tenxyte

---

## 📊 Documentation Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| API Coverage | 100% | ✅ Complete |
| Quality Score | 100/100 | ✅ Perfect |
| Schema Size Reduction | 3% | ✅ Optimized |
| Examples Count | 280+ | ✅ Comprehensive |
| Error Code Coverage | 100% | ✅ Complete |
| Multi-tenant Documentation | 100% | ✅ Complete |

---

## 🛠️ Documentation Scripts

### Validation Tools
```bash
# Validate OpenAPI specification
python scripts/validate_openapi_spec.py

# Check documentation coverage
python scripts/validate_documentation.py

# Optimize schema performance
python scripts/optimize_schemas.py
```

### Generation Tools
```bash
# Generate Postman collection
python scripts/generate_postman_collection.py

# Generate static documentation site
python scripts/generate_docs_site.py
```

See [Scripts Documentation](https://github.com/tenxyte/tenxyte/blob/main/scripts/README.md) for complete usage guide.

---

## Architecture: Core & Adapters

Tenxyte is built around a **Framework-Agnostic Core** utilizing a Ports and Adapters (Hexagonal) architecture. 

- **Core**: Contains pure Python authentication, JWT, and RBAC logic (zero framework dependencies).
- **Ports**: Defines abstract interfaces for external operations (e.g., Repositories, EmailServices, CacheServices).
- **Adapters**: Concrete implementations tailored to frameworks (Django, FastAPI) or libraries.

This design guarantees that existing Django deployments run with **zero breaking changes**, while natively opening support for modern async frameworks like FastAPI.

Read more in our detailed **[Architecture Guide](docs/en/architecture.md)**.

---

## Supported Databases

- ✅ **SQLite** — development
- ✅ **PostgreSQL** — recommended for production
- ✅ **MySQL/MariaDB**
- ✅ **MongoDB** — via `django-mongodb-backend`

### MongoDB — Required Configuration

```bash
pip install tenxyte[mongodb]
```

```python
# settings.py
AUTH_USER_MODEL = 'tenxyte.User'
DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'NAME': 'tenxyte_db',
        'HOST': 'localhost',
        'PORT': 27017,
    }
}

# Disable native migrations (integer PKs incompatible with ObjectId)
MIGRATION_MODULES = {
    'contenttypes': None,
    'auth': None,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'tenxyte.middleware.CORSMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ❌ Remove: 'django.contrib.auth.middleware.AuthenticationMiddleware'
    'django.contrib.messages.middleware.MessageMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]
```

#### MongoDB — Django Admin Support

To use Django Admin with MongoDB, replace default admin/auth/contenttypes entries with custom configs that set `ObjectIdAutoField`.

**Step 1 — `apps.py` of your main app:**

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

**Step 2 — `INSTALLED_APPS`:**

```python
INSTALLED_APPS = [
    # Replace the three Django defaults with your MongoDB versions:
    'config.apps.MongoAdminConfig',       # replaces 'django.contrib.admin'
    'config.apps.MongoAuthConfig',        # replaces 'django.contrib.auth'
    'config.apps.MongoContentTypesConfig', # replaces 'django.contrib.contenttypes'

    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'tenxyte',
]
```

> Replace `config` with the name of your main Django app. Then, run `python manage.py makemigrations && python manage.py migrate` — Django Admin will work correctly with MongoDB.

---

## Periodic Maintenance

Tenxyte requires a few periodic tasks to maintain performance and security. Configure **Celery Beat** or a standard *cron* job:

1. **Token Cleanup** (Daily at 3 AM)
   Remove blacklisted JWT tokens and expired refresh/agent tokens:
   ```python
   from tenxyte.models import BlacklistedToken, RefreshToken, AgentToken
   BlacklistedToken.cleanup_expired()
   # Add similar logic for Refresh/Agent tokens based on expires_at
   ```

2. **OTP & WebAuthn Purge** (Every 15 minutes)
   Clear expired OTP codes and unused WebAuthn challenges:
   ```python
   from tenxyte.models import OTPCode, WebAuthnChallenge
   OTPCode.cleanup_expired()
   WebAuthnChallenge.cleanup_expired()
   ```

3. **Audit Log Rotation** (Monthly)
   To comply with GDPR, archive or delete old logs:
   ```python
   from django.utils import timezone
   from datetime import timedelta
   from tenxyte.models import AuditLog
   
   cutoff = timezone.now() - timedelta(days=90)
   AuditLog.objects.filter(timestamp__lt=cutoff).delete()
   ```

---

## Customization & Extension

Tenxyte exposes abstract base classes: `AbstractUser`, `AbstractRole`, `AbstractPermission`, `AbstractApplication`.

```python
# myapp/models.py
from tenxyte.models import AbstractUser

class CustomUser(AbstractUser):
    company = models.CharField(max_length=100, blank=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'
```

```python
# settings.py
TENXYTE_USER_MODEL = 'myapp.CustomUser'
AUTH_USER_MODEL = 'myapp.CustomUser'
```

Same pattern for `TENXYTE_ROLE_MODEL`, `TENXYTE_PERMISSION_MODEL`, `TENXYTE_APPLICATION_MODEL`. Always inherit the parent `Meta` and set a custom `db_table`.

### Creating Custom Framework Adapters

Because Tenxyte is framework-agnostic, you can write your own Database adapters, Cache adapters, or Email adapters using the core `Ports`. See the **[Custom Adapters Guide](docs/en/custom_adapters.md)** for detailed instructions on extending the core.

---

## Configuration Reference

All 115+ settings documented in [docs/en/settings.md](docs/en/settings.md).

Useful toggles for development:

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # disables X-Access-Key check
TENXYTE_RATE_LIMITING_ENABLED = False
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = False          # testing only
```

---

## Development & Testing

```bash
git clone https://github.com/tenxyte/tenxyte.git
pip install -e ".[dev]"
pytest                               # 1553 tests, 100% pass rate
pytest --cov=tenxyte --cov-report=html
```

**Multi-DB Tests** (requires a running server per backend):

```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mysql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

---

## Frequently Asked Questions & Troubleshooting

**`MongoDB does not support AutoField/BigAutoField`**
→ Configure `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` and add `MIGRATION_MODULES = {'contenttypes': None, 'auth': None}`. For Django Admin, use the custom app configs described in the [MongoDB Admin section](#mongodb--django-admin-support).

**`Model instances without primary key value are unhashable`**
→ Same fix (`MIGRATION_MODULES`). If it persists, disconnect `post_migrate` signals for `create_permissions` and `create_contenttypes`.

**`ModuleNotFoundError: No module named 'rest_framework'`**
→ `pip install djangorestframework`

**401 Unauthorized / JWT not working**
→ Ensure all three headers are present: `X-Access-Key`, `X-Access-Secret`, `Authorization: Bearer <token>`.

**`No module named 'corsheaders'`**
→ Tenxyte includes built-in CORS middleware (`tenxyte.middleware.CORSMiddleware`). Remove `corsheaders` from your config.

---

## 🎯 Documentation Standards

### Quality Requirements
- ✅ **100% Coverage** - All endpoints documented
- ✅ **Working Examples** - All examples tested and functional
- ✅ **Error Documentation** - Comprehensive error handling
- ✅ **Multi-tenant Support** - Complete B2B documentation
- ✅ **Security Features** - Privacy and security documented

### Maintenance Standards
- 🔄 **Regular Updates** - Keep documentation synchronized
- 🧪 **Automated Testing** - Continuous validation
- 📊 **Quality Monitoring** - Track metrics and improvements
- 🔧 **Tool Updates** - Maintain validation and generation tools
- 📚 **User Feedback** - Incorporate developer feedback

---

## Contributing

Contributions are welcome! A few simple rules:

1. Open an issue before a major feature request.
2. Fork → branch `feature/xxx` → PR with tests and changelog.
3. Respect commit conventions and add unit tests.

See [docs/en/CONTRIBUTING.md](docs/en/CONTRIBUTING.md) for more details.

## License

MIT — see [LICENSE](LICENSE).

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
