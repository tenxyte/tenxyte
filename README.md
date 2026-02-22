# Tenxyte Auth

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-5.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-1069%20passing-brightgreen.svg)]()

Complete Django authentication package — JWT, RBAC, 2FA (TOTP), Magic Links, Passkeys (WebAuthn), Social Login, Breach Check, Organizations B2B, and multi-application support.

## Documentation

### 🚀 **Enhanced DRF Spectacular Documentation**
- [**Interactive API Docs**](http://localhost:8000/api/docs/) — Swagger UI with live testing
- [**ReDoc Documentation**](http://localhost:8000/api/redoc/) — Beautiful API reference
- [**Static Documentation Site**](docs_site/index.html) — Complete documentation website
- [**Postman Collection**](tenxyte_api_collection.postman_collection.json) — Ready-to-use API collection
- [**Migration Guide**](docs/MIGRATION_GUIDE.md) — Upgrade from old documentation

### 📚 **Developer Guides**
- [**Quickstart**](docs/quickstart.md) — Up and running in 5 minutes
- [**Settings Reference**](docs/settings.md) — All 150+ configuration options
- [**API Endpoints**](docs/endpoints.md) — Full endpoint reference with curl examples
- [**RBAC Guide**](docs/rbac.md) — Roles, permissions, 8 decorators
- [**Security Guide**](docs/security.md) — Rate limiting, 2FA, device fingerprinting, JWT hardening
- [**Organizations Guide**](docs/organizations.md) — B2B multi-tenant setup
- [**Database Setup**](DATABASE_SETUP.md) — PostgreSQL, MySQL, MongoDB, SQLite

### 🔧 **Documentation Tools**
- [**OpenAPI Validation**](scripts/validate_openapi_spec.py) — Validate API specification
- [**Schema Optimization**](scripts/optimize_schemas.py) — Optimize performance
- [**Documentation Testing**](tests/test_documentation_examples.py) — Test examples and schemas

## Features

✨ **Core Authentication**
- JWT with access + refresh tokens, rotation, blacklisting
- Email and phone number login
- Social Login — Google, GitHub, Microsoft, Facebook
- Magic Links (passwordless email login)
- Passkeys / WebAuthn (FIDO2)
- Multi-application support (`X-Access-Key` / `X-Access-Secret`)

🔐 **Security**
- Two-Factor Authentication (TOTP) — Google Authenticator, Authy
- OTP verification via email and SMS
- Breach password check (HaveIBeenPwned, k-anonymity)
- Account lockout after failed attempts
- Session & device limits
- Rate limiting, CORS, security headers
- Audit logging

👥 **Role-Based Access Control (RBAC)**
- Flexible roles and permissions, hierarchical
- Per-user and per-role direct permissions
- 8 decorators + DRF permission classes

🏢 **Organizations (B2B)**
- Multi-tenant with hierarchical org tree
- Per-org roles and memberships

📱 **Multi-Channel Communication**
- SMS: Twilio, NGH Corp, Console
- Email: Django (recommended), SendGrid, Console

⚙️ **Shortcut Secure Mode**
- One-line security preset: `TENXYTE_SHORTCUT_SECURE_MODE = 'medium'`
- Modes: `starter` / `medium` / `robust` — all individually overridable

## Installation

```bash
pip install tenxyte

# Optional extras
pip install tenxyte[twilio]    # Twilio SMS
pip install tenxyte[sendgrid]  # SendGrid email
pip install tenxyte[mongodb]   # MongoDB support
pip install tenxyte[postgres]  # PostgreSQL
pip install tenxyte[mysql]     # MySQL/MariaDB
pip install tenxyte[all]       # Everything
```

## 🆕 **Documentation Enhancements**

### **Enhanced DRF Spectacular Documentation**
- ✅ **100% API Coverage** — All 50+ endpoints documented with examples
- ✅ **Multi-tenant Support** — X-Org-Slug header documentation for B2B
- ✅ **Realistic Examples** — Working request/response examples for all scenarios
- ✅ **Error Handling** — Comprehensive error codes and troubleshooting guides
- ✅ **Security Features** — 2FA, rate limiting, device management documentation

### **Developer Tools**
- 📮 **Postman Collection** — Ready-to-use with authentication and tests
- 🌐 **Static Documentation Site** — Responsive website with search
- 🔧 **Validation Scripts** — Automated OpenAPI validation and optimization
- 🧪 **Test Suite** — Comprehensive testing of documentation examples
- 📊 **Performance Monitoring** — Schema optimization and size analysis

### **Interactive Documentation**
```bash
# Start Django development server
python manage.py runserver

# Access interactive documentation
http://localhost:8000/api/docs/     # Swagger UI
http://localhost:8000/api/redoc/    # ReDoc
```

### **Documentation Quality Metrics**
- 📈 **Quality Score**: 95/100 (automated validation)
- 🎯 **Coverage**: 100% of endpoints documented
- ⚡ **Performance**: Optimized schemas with 40% size reduction
- 🔍 **Examples**: 15+ reusable examples across all scenarios
- 🏢 **Multi-tenant**: Complete B2B documentation

## Database Support

- ✅ **SQLite** — development
- ✅ **PostgreSQL** — recommended for production
- ✅ **MySQL/MariaDB**
- ✅ **MongoDB** — via `django-mongodb-backend`

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for full per-database setup.

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

# Disable built-in migrations (integer PKs incompatible with ObjectId)
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

To use Django Admin with MongoDB, replace the default admin/auth/contenttypes entries with custom configs that set `ObjectIdAutoField`.

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
    # Replace the three Django defaults with your MongoDB-aware versions:
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

> Replace `config` with the name of your main Django app. After this, run `python manage.py makemigrations && python manage.py migrate` — Django Admin will work correctly with MongoDB.

## Quick Start

> Full walkthrough: [docs/quickstart.md](docs/quickstart.md). For MongoDB, see the [MongoDB section](#mongodb--required-configuration) above first.

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'tenxyte',
]

AUTH_USER_MODEL = 'tenxyte.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}
```

### 2. Configure URLs

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

### 3. Middleware

```python
MIDDLEWARE = [
    ...
    'tenxyte.middleware.ApplicationAuthMiddleware',
    'tenxyte.middleware.SecurityHeadersMiddleware',  # optional
]
```

### 4. Migrate + seed

Tenxyte does not ship a pre-built migration — generate and apply from your project:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py tenxyte_seed   # creates 4 roles + 41 permissions
```

### 5. Create an Application

```python
from tenxyte.models import Application

app, secret = Application.create_application(name="My App")
print(app.access_key, secret)  # secret shown only once — save it
```

### 6. Security preset (optional)

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # 'starter' | 'medium' | 'robust'
```

→ See [Settings Reference — Shortcut Secure Mode](docs/settings.md#shortcut-secure-mode)

## Usage Examples

All requests require two-layer auth headers:

```http
X-Access-Key: <your_app_access_key>
X-Access-Secret: <your_app_access_secret>
Authorization: Bearer <jwt_access_token>   # authenticated endpoints only
```

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/email/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'
```

Full examples with responses: [docs/endpoints.md](docs/endpoints.md)

## API Endpoints (overview)

| Category | Key endpoints |
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

Full reference with curl examples: [docs/endpoints.md](docs/endpoints.md)

---

## Extending Models

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

---

## Configuration Reference

All 150+ settings documented in [docs/settings.md](docs/settings.md).

Key toggles for development:

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # disable X-Access-Key check
TENXYTE_RATE_LIMITING_ENABLED = False
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = False          # testing only
```

---

## Development

```bash
git clone https://github.com/tenxyte/tenxyte.git
pip install -e ".[dev]"
pytest                               # 893 tests, 100% pass rate
pytest --cov=tenxyte --cov-report=html
```

**Multi-DB tests** (requires running server per backend):

```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mysql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

---

## Troubleshooting

**`MongoDB does not support AutoField/BigAutoField`**
→ Set `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` and add `MIGRATION_MODULES = {'contenttypes': None, 'auth': None}`. For Django Admin, use the custom app configs described in the [MongoDB Admin section](#mongodb--django-admin-support) above.

**`Model instances without primary key value are unhashable`**
→ Same fix as above (`MIGRATION_MODULES`). If it persists, disconnect `post_migrate` signals for `create_permissions` and `create_contenttypes`.

**`ModuleNotFoundError: No module named 'rest_framework'`**
→ `pip install djangorestframework`

**401 Unauthorized / JWT not working**
→ Ensure all three headers are present: `X-Access-Key`, `X-Access-Secret`, `Authorization: Bearer <token>`.

**`No module named 'corsheaders'`**
→ Tenxyte includes built-in CORS middleware (`tenxyte.middleware.CORSMiddleware`). Remove `corsheaders` from your config.

---

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## License

MIT — see [LICENSE](LICENSE).

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
