![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Framework-Agnostic Python Authentication in minutes — JWT, RBAC, 2FA, Magic Links, Passkeys, Social Login, Breach Check, Organizations (B2B), multi-application support.

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-4.2%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml)

---

## Quickstart — 2 minutes to your first API call

### 1. Install

```bash
pip install tenxyte
```

> **Requirements:** Python 3.10+, Django 6.0+ or FastAPI 0.135+

### 2. Configure

```python
# settings.py — add at the very bottom
import tenxyte
tenxyte.setup(globals())   # auto-injects INSTALLED_APPS, AUTH_USER_MODEL, REST_FRAMEWORK, MIDDLEWARE
```

```python
# urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

### 3. Run

```bash
python manage.py tenxyte_quickstart   # migrate + seed roles + create Application
python manage.py runserver
```

### 4. First API call

```bash
# Register — use the credentials displayed by tenxyte_quickstart
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" -H "X-Access-Secret: <your-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <your-access-key>" -H "X-Access-Secret: <your-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'

# Authenticated request
curl http://localhost:8000/api/v1/auth/me/ \
  -H "X-Access-Key: <your-access-key>" -H "X-Access-Secret: <your-access-secret>" \
  -H "Authorization: Bearer <access_token>"
```

> ⚠️ In `DEBUG=True`, Tenxyte auto-generates an **ephemeral JWT secret key** (invalidated on restart) and applies relaxed security limits. `X-Access-Key` / `X-Access-Secret` headers are **still required** unless you explicitly set `TENXYTE_APPLICATION_AUTH_ENABLED = False`.

> 💡 Include `"login": true` in the register request to receive JWT tokens in the response immediately.

That's it — you have a fully featured auth backend running.

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

## Installation Options

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

---

## Production Setup

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

## Endpoints Overview

> Routes require `X-Access-Key` and `X-Access-Secret` headers by default. To disable this check in development, set `TENXYTE_APPLICATION_AUTH_ENABLED = False` (forbidden in production).

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

For complete examples with full request/response bodies, see [endpoints.md](endpoints.md).

### Interactive Documentation

Add these routes to your `urls.py` for Swagger UI and ReDoc:

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns += [
    path(f'{api_prefix}/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{api_prefix}/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{api_prefix}/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

- [**Postman Collection**](../../tenxyte_api_collection.postman_collection.json) — Ready-to-use collection

---

## 📚 Documentation

### 📖 **Developer Guides**
- [**Quickstart**](quickstart.md) - Get started in 2 minutes with Django
- [**FastAPI Quickstart**](fastapi_quickstart.md) - Get started with FastAPI
- [**Settings Reference**](settings.md) - All 95+ configuration options
- [**API Endpoints**](endpoints.md) - Full endpoint reference with examples
- [**Admin Accounts**](admin.md) - Manage Superusers and RBAC Admins
- [**Applications Guide**](applications.md) - Manage API clients and credentials
- [**RBAC Guide**](rbac.md) - Roles, permissions, and decorators
- [**Security Guide**](security.md) - Security features and best practices
- [**Organizations Guide**](organizations.md) - B2B multi-tenant setup
- [**AIRS Guide**](airs.md) - AI Responsibility & Security
- [**Migration Guide**](MIGRATION_GUIDE.md) - Migration from dj-rest-auth, simplejwt

### 🔧 **Technical Documentation**
- [**Architecture Guide**](architecture.md) - Core & Adapters (Hexagonal) architecture
- [**Async Guide**](async_guide.md) - Async/await patterns and best practices
- [**Task Service**](task_service.md) - Background job processing
- [**Custom Adapters Guide**](custom_adapters.md) - Creating custom adapters
- [**Schemas Reference**](schemas.md) - Reusable schema components
- [**Testing Guide**](TESTING.md) - Testing strategies and examples
- [**Periodic Tasks**](periodic_tasks.md) - Scheduled maintenance and cleanup tasks
- [**Troubleshooting**](troubleshooting.md) - Common issues and solutions
- [**Contributing**](CONTRIBUTING.md) - How to contribute to Tenxyte

---

## Architecture: Core & Adapters

Tenxyte is built around a **Framework-Agnostic Core** utilizing a Ports and Adapters (Hexagonal) architecture. 

- **Core**: Contains pure Python authentication, JWT, and RBAC logic (zero framework dependencies).
- **Ports**: Defines abstract interfaces for external operations (e.g., Repositories, EmailServices, CacheServices).
- **Adapters**: Concrete implementations tailored to frameworks (Django, FastAPI) or libraries.

This design guarantees that existing Django deployments run with **zero breaking changes**, while natively opening support for modern async frameworks like FastAPI.

Read more in our detailed **[Architecture Guide](architecture.md)**.

---

## Supported Databases

- ✅ **SQLite** — development
- ✅ **PostgreSQL** — recommended for production
- ✅ **MySQL/MariaDB**
- ✅ **MongoDB** — via `django-mongodb-backend` (see [quickstart.md](quickstart.md#mongodb) for configuration)

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

Because Tenxyte is framework-agnostic, you can write your own Database adapters, Cache adapters, or Email adapters using the core `Ports`. See the **[Custom Adapters Guide](custom_adapters.md)** for detailed instructions on extending the core.

---

## Configuration Reference

All 115+ settings documented in [settings.md](settings.md).

Useful toggles for development:

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # disables X-Access-Key check
TENXYTE_RATE_LIMITING_ENABLED = False
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = False          # testing only
```

---

## Periodic Maintenance

Tenxyte requires periodic tasks (token cleanup, OTP purge, audit log rotation) to maintain performance and security. See the [Periodic Tasks Guide](periodic_tasks.md) for full configuration with Celery Beat or cron.

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
→ Configure `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` and add `MIGRATION_MODULES = {'contenttypes': None, 'auth': None}`. See [quickstart.md](quickstart.md#mongodb).

**`Model instances without primary key value are unhashable`**
→ Same fix (`MIGRATION_MODULES`). If it persists, disconnect `post_migrate` signals for `create_permissions` and `create_contenttypes`.

**`ModuleNotFoundError: No module named 'rest_framework'`**
→ `pip install djangorestframework`

**401 Unauthorized / JWT not working**
→ Ensure all three headers are present: `X-Access-Key`, `X-Access-Secret`, `Authorization: Bearer <token>`.

**`No module named 'corsheaders'`**
→ Tenxyte includes built-in CORS middleware (`tenxyte.middleware.CORSMiddleware`). Remove `corsheaders` from your config.

For more solutions, see [troubleshooting.md](troubleshooting.md).

---

## Contributing

Contributions are welcome! A few simple rules:

1. Open an issue before a major feature request.
2. Fork → branch `feature/xxx` → PR with tests and changelog.
3. Respect commit conventions and add unit tests.

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

MIT — see [LICENSE](../../LICENSE).

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

See [CHANGELOG.md](../../CHANGELOG.md) for release history.
