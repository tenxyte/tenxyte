# Tenxyte Auth

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-5.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Complete Django authentication package with JWT, RBAC, 2FA (TOTP), OTP verification, and multi-application support.

## Features

✨ **Core Authentication**
- JWT authentication with access and refresh tokens
- Email and phone number authentication
- Google OAuth integration
- Multi-application support (multiple client apps)

🔐 **Security**
- Two-Factor Authentication (TOTP) compatible with Google Authenticator, Authy, etc.
- OTP verification via email and SMS
- Password strength validation
- Account lockout after failed attempts
- Rate limiting on sensitive endpoints
- CORS and security headers configuration

👥 **Role-Based Access Control (RBAC)**
- Flexible role and permission system
- Hierarchical permissions
- Per-user and per-role permissions

📱 **Multi-Channel Communication**
- SMS via Twilio (optional)
- Email via SendGrid or Django (optional)
- Console backend for development

## Installation

### Basic Installation

```bash
pip install tenxyte
```

### With Optional Dependencies

```bash
# SMS Support
pip install tenxyte[twilio]

# Email Support
pip install tenxyte[sendgrid]

# Database Drivers
pip install tenxyte[mongodb]    # MongoDB support
pip install tenxyte[postgres]   # PostgreSQL support
pip install tenxyte[mysql]      # MySQL/MariaDB support

# Everything included
pip install tenxyte[all]
```

## Database Support

Tenxyte Auth is compatible with **all Django-supported databases**:

- ✅ **SQLite** - Perfect for development
- ✅ **PostgreSQL** - Recommended for production
- ✅ **MySQL/MariaDB** - Widely supported
- ✅ **MongoDB** - NoSQL with django-mongodb-backend

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed setup instructions for each database.

### Quick Database Configuration

#### SQLite (Default)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

#### PostgreSQL
```bash
pip install psycopg2-binary
```
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tenxyte_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### MongoDB

> ⚠️ **IMPORTANT: MongoDB Configuration Differences**
>
> MongoDB has specific requirements that differ from traditional SQL databases. **You MUST remove certain Django apps** that are incompatible with MongoDB.

```bash
pip install tenxyte[mongodb]
# This installs: django-mongodb-backend
```

**Critical Configuration Steps:**

```python
# settings.py

# 1. INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    # ❌ REMOVE: 'django.contrib.admin'  (incompatible with ObjectIdAutoField)

    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',
    'drf_spectacular',

    # Tenxyte Auth
    'tenxyte',
]

# 2. Custom User Model (REQUIRED)
AUTH_USER_MODEL = 'tenxyte.User'

# 3. MongoDB-specific AutoField
DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'

# 4. Disable migrations for built-in apps (incompatible with ObjectId PKs)
MIGRATION_MODULES = {
    'contenttypes': None,
    'auth': None,
}

# 5. Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'NAME': 'tenxyte_db',
        'HOST': 'localhost',
        'PORT': 27017,
        # Optional: authentication
        # 'USER': 'mongo_user',
        # 'PASSWORD': 'mongo_password',
    }
}

# 6. MIDDLEWARE - Remove AuthenticationMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ❌ REMOVE: 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]

# 7. REST Framework authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}
```

**Why these changes?**
- MongoDB uses `ObjectIdAutoField` instead of `AutoField` or `BigAutoField`
- Django's `admin` app is incompatible with ObjectId primary keys
- `contenttypes` and `auth` migrations are disabled since their models use integer PKs
- Tenxyte automatically detects the MongoDB engine and uses the correct field types for its own models

## Quick Start

> 📌 **Using MongoDB?** The configuration is different! Jump to the [MongoDB Configuration](#mongodb) section first.

> 💡 **Tip:** For SQL databases (PostgreSQL, MySQL, SQLite), follow the standard setup below. For MongoDB, you must remove certain Django apps - see the dedicated section.

### 1. Add to INSTALLED_APPS

```python
# settings.py

INSTALLED_APPS = [
    # Django apps (for SQL databases: PostgreSQL, MySQL, SQLite)
    # Note: If using MongoDB, see MongoDB Configuration section above
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',
    'drf_spectacular',  # Optional, for API docs

    # Tenxyte Auth
    'tenxyte',

    # Your apps
    ...
]
```

### 2. Configure URLs

```python
# urls.py

from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Tenxyte endpoints
    path('api/auth/', include('tenxyte.urls')),

    # Your URLs
    ...
]
```

### 3. Configure Settings (Optional)

```python
# settings.py

# JWT Settings
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 86400 * 7  # 7 days

# 2FA Settings
TENXYTE_TOTP_ISSUER = "MyApp"

# SMS Backend (default: console for development)
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.TwilioBackend'
TENXYTE_SMS_ENABLED = True
TENXYTE_SMS_DEBUG = False

# Twilio credentials (if using Twilio backend)
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "+1234567890"

# Email Backend
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.SendGridBackend'

# SendGrid credentials (if using SendGrid backend)
SENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SENDGRID_FROM_EMAIL = "noreply@example.com"
```

### 4. Additional Configuration (Important)

```python
# settings.py

# Custom User Model (REQUIRED if using tenxyte)
AUTH_USER_MODEL = 'tenxyte.User'

# REST Framework Authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
    'tenxyte.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS Configuration (if using a frontend)
CORS_ALLOW_ALL_ORIGINS = True  # For development only!
# In production:
# CORS_ALLOWED_ORIGINS = ['https://yourdomain.com']
```

### 5. Run Migrations

```bash
python manage.py migrate
```

> ⚠️ **Common Errors and Solutions:**
>
> **Error: `MongoDB does not support AutoField/BigAutoField`**
> - Solution: See the [MongoDB Configuration](#mongodb) section above
> - You must set `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'`
> - Remove incompatible apps: `admin`, `auth`, `contenttypes`
>
> **Error: `No module named 'django_mongodb_backend'`**
> - Solution: Install MongoDB backend: `pip install tenxyte[mongodb]`
>
> **Error: `User model not found`**
> - Solution: Add `AUTH_USER_MODEL = 'tenxyte.User'` to settings.py

### 6. Seed Default Roles & Permissions (Optional but Recommended)

```bash
python manage.py tenxyte_seed
```

This creates:
- **4 Default Roles**: `viewer`, `editor`, `admin`, `super_admin`
- **28 Default Permissions**: For users, roles, permissions, applications, content, and system

| Role | Description | Permissions |
|------|-------------|-------------|
| `viewer` | Read-only access (default for new users) | `content.view` |
| `editor` | Can create and edit content | `content.view`, `content.create`, `content.edit` |
| `admin` | Administrative access | Content + Users + View roles/permissions |
| `super_admin` | Full system access | ALL permissions |

**Options:**
```bash
# Force recreate (delete and recreate)
python manage.py tenxyte_seed --force

# Only create permissions (skip roles)
python manage.py tenxyte_seed --no-roles

# Only create roles (skip permissions)
python manage.py tenxyte_seed --no-permissions
```

### 7. Create an Application

```python
# Create an application for your client (frontend, mobile app, etc.)
python manage.py shell

from tenxyte.models import Application

# Use the factory method to generate credentials
app, raw_secret = Application.create_application(
    name="My Frontend App",
    description="React frontend application"
)

# Save these credentials securely - the secret is shown only once!
print(f"Access Key: {app.access_key}")
print(f"Access Secret: {raw_secret}")  # Store this securely!
```

> ⚠️ **IMPORTANT:** Always use `Application.create_application()` instead of `objects.create()`
> - The factory method generates and hashes credentials automatically
> - The raw secret is returned only once - save it securely
> - Never use `objects.create()` as it won't generate credentials

## Usage Examples

### Authentication Headers

All API requests require two-layer authentication:

```http
X-Access-Key: <your_application_access_key>
X-Access-Secret: <your_application_access_secret>
Authorization: Bearer <jwt_access_token>
```

### Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "X-Access-Key: your_access_key" \
  -H "X-Access-Secret: your_access_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecureP@ssw0rd!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login/email/ \
  -H "X-Access-Key: your_access_key" \
  -H "X-Access-Secret: your_access_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecureP@ssw0rd!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "123",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_2fa_enabled": false
  }
}
```

### Enable 2FA

**1. Setup 2FA (get QR code)**
```bash
curl -X POST http://localhost:8000/api/auth/2fa/setup/ \
  -H "X-Access-Key: your_access_key" \
  -H "X-Access-Secret: your_access_secret" \
  -H "Authorization: Bearer your_access_token"
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "provisioning_uri": "otpauth://totp/MyApp:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=MyApp",
  "backup_codes": [
    "a1b2-c3d4",
    "e5f6-g7h8",
    ...
  ],
  "warning": "Save the backup codes securely. They will not be shown again."
}
```

**2. Scan QR code with Google Authenticator**

**3. Confirm with the first TOTP code**
```bash
curl -X POST http://localhost:8000/api/auth/2fa/confirm/ \
  -H "X-Access-Key: your_access_key" \
  -H "X-Access-Secret: your_access_secret" \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

**4. Login with 2FA**
```bash
curl -X POST http://localhost:8000/api/auth/login/email/ \
  -H "X-Access-Key: your_access_key" \
  -H "X-Access-Secret: your_access_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecureP@ssw0rd!",
    "totp_code": "123456"
  }'
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/email/` - Login with email
- `POST /api/auth/login/phone/` - Login with phone
- `POST /api/auth/google/` - Google OAuth login
- `POST /api/auth/refresh/` - Refresh access token
- `POST /api/auth/logout/` - Logout (revoke refresh token)
- `POST /api/auth/logout/all/` - Logout from all devices

### OTP Verification
- `POST /api/auth/otp/request/` - Request OTP code
- `POST /api/auth/otp/verify/email/` - Verify email OTP
- `POST /api/auth/otp/verify/phone/` - Verify phone OTP

### Password Management
- `POST /api/auth/password/reset/request/` - Request password reset
- `POST /api/auth/password/reset/confirm/` - Confirm password reset with OTP
- `POST /api/auth/password/change/` - Change password (authenticated)
- `POST /api/auth/password/strength/` - Check password strength
- `GET /api/auth/password/requirements/` - Get password requirements

### Two-Factor Authentication (2FA)
- `GET /api/auth/2fa/status/` - Get 2FA status
- `POST /api/auth/2fa/setup/` - Setup 2FA (get QR code)
- `POST /api/auth/2fa/confirm/` - Confirm and enable 2FA
- `POST /api/auth/2fa/disable/` - Disable 2FA
- `POST /api/auth/2fa/backup-codes/` - Regenerate backup codes

### User Profile
- `GET /api/auth/me/` - Get current user profile
- `PATCH /api/auth/me/` - Update current user profile
- `GET /api/auth/me/roles/` - Get user roles and permissions

### RBAC (Role-Based Access Control)
- `GET /api/auth/permissions/` - List all permissions
- `GET /api/auth/permissions/{id}/` - Get permission details
- `GET /api/auth/roles/` - List all roles
- `POST /api/auth/roles/` - Create role (admin only)
- `GET /api/auth/roles/{id}/` - Get role details
- `PUT /api/auth/roles/{id}/` - Update role (admin only)
- `DELETE /api/auth/roles/{id}/` - Delete role (admin only)
- `GET /api/auth/users/{id}/roles/` - Get user roles
- `POST /api/auth/users/{id}/roles/` - Assign role to user (admin only)
- `DELETE /api/auth/users/{id}/roles/` - Remove role from user (admin only)

### Applications
- `GET /api/auth/applications/` - List applications (admin only)
- `POST /api/auth/applications/` - Create application (admin only)
- `GET /api/auth/applications/{id}/` - Get application details
- `PUT /api/auth/applications/{id}/` - Update application
- `DELETE /api/auth/applications/{id}/` - Delete application
- `POST /api/auth/applications/{id}/regenerate/` - Regenerate credentials

## Extending Models

Tenxyte provides **abstract base classes** that you can extend to add custom fields to User, Role, Permission, and Application models.

### Extending User Model

```python
# myapp/models.py
from django.db import models
from tenxyte.models import AbstractUser

class CustomUser(AbstractUser):
    """Custom user with additional fields."""
    company = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'
```

```python
# settings.py
TENXYTE_USER_MODEL = 'myapp.CustomUser'
AUTH_USER_MODEL = 'myapp.CustomUser'  # Also set Django's setting
```

### Extending Role Model

```python
# myapp/models.py
from django.db import models
from tenxyte.models import AbstractRole

class CustomRole(AbstractRole):
    """Custom role with additional fields."""
    priority = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#000000')
    icon = models.CharField(max_length=50, blank=True)
    max_users = models.IntegerField(null=True, blank=True)

    class Meta(AbstractRole.Meta):
        db_table = 'custom_roles'
```

```python
# settings.py
TENXYTE_ROLE_MODEL = 'myapp.CustomRole'
```

### Extending Permission Model

```python
# myapp/models.py
from django.db import models
from tenxyte.models import AbstractPermission

class CustomPermission(AbstractPermission):
    """Custom permission with additional fields."""
    category = models.CharField(max_length=50, blank=True)
    is_system = models.BooleanField(default=False)
    requires_2fa = models.BooleanField(default=False)

    class Meta(AbstractPermission.Meta):
        db_table = 'custom_permissions'
```

```python
# settings.py
TENXYTE_PERMISSION_MODEL = 'myapp.CustomPermission'
```

### Extending Application Model

```python
# myapp/models.py
from django.db import models
from tenxyte.models import AbstractApplication

class CustomApplication(AbstractApplication):
    """Custom application with additional fields."""
    owner = models.ForeignKey('myapp.CustomUser', on_delete=models.CASCADE, null=True)
    api_rate_limit = models.IntegerField(default=1000)
    allowed_origins = models.JSONField(default=list, blank=True)
    webhook_url = models.URLField(blank=True)

    class Meta(AbstractApplication.Meta):
        db_table = 'custom_applications'
```

```python
# settings.py
TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
```

### Using Helper Functions

```python
from tenxyte.models import get_user_model, get_role_model, get_permission_model, get_application_model

# Get the active model (custom or default)
User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()
Application = get_application_model()

# Use them like normal Django models
user = User.objects.create_user(email='test@example.com', password='secret')
app, secret = Application.create_application(name='My App')
```

### Important Notes

1. **Set both settings**: When extending User, set both `TENXYTE_USER_MODEL` and `AUTH_USER_MODEL`
2. **Run migrations**: After creating custom models, run `python manage.py makemigrations` and `python manage.py migrate`
3. **Inherit Meta**: Always inherit from the parent's Meta class: `class Meta(AbstractUser.Meta):`
4. **Don't forget db_table**: Set a custom `db_table` to avoid conflicts

## Configuration Reference

All available settings are listed below.

### Essential Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | `3600` | Access token lifetime (seconds) |
| `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | `604800` | Refresh token lifetime (seconds) |
| `TENXYTE_TOTP_ISSUER` | `"MyApp"` | TOTP issuer name |
| `TENXYTE_SMS_BACKEND` | `'...ConsoleBackend'` | SMS backend class path |
| `TENXYTE_EMAIL_BACKEND` | `'...ConsoleBackend'` | Email backend class path |

### Security Layers (Can be Disabled for Development)

All security layers are **enabled by default**. Disable them only for development/testing.

```python
# settings.py - Development configuration example

# Disable Application authentication (X-Access-Key, X-Access-Secret)
TENXYTE_APPLICATION_AUTH_ENABLED = False

# Disable rate limiting
TENXYTE_RATE_LIMITING_ENABLED = False

# Disable JWT authentication (DANGEROUS - testing only!)
TENXYTE_JWT_AUTH_ENABLED = False

# Disable account lockout
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
```

| Setting | Default | Description |
|---------|---------|-------------|
| `TENXYTE_APPLICATION_AUTH_ENABLED` | `True` | Enable Application authentication |
| `TENXYTE_RATE_LIMITING_ENABLED` | `True` | Enable rate limiting |
| `TENXYTE_JWT_AUTH_ENABLED` | `True` | Enable JWT authentication |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED` | `True` | Enable account lockout |

### Rate Limiting Settings

```python
# settings.py

# Maximum login attempts before lockout
TENXYTE_MAX_LOGIN_ATTEMPTS = 5

# Account lockout duration (minutes)
TENXYTE_LOCKOUT_DURATION_MINUTES = 30

# Time window for counting login attempts (minutes)
TENXYTE_RATE_LIMIT_WINDOW_MINUTES = 15
```

### Exempt Paths (Application Auth)

```python
# settings.py

# Paths exempt from application authentication (prefix match)
TENXYTE_EXEMPT_PATHS = [
    '/admin/',
    '/api/v1/health/',
    '/api/v1/docs/',
    '/api/v1/public/',
]

# Exact paths exempt from application authentication
TENXYTE_EXACT_EXEMPT_PATHS = [
    '/api/v1/',
    '/',
]
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/tenxyte/tenxyte.git
cd tenxyte

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=tenxyte --cov-report=html
```

### Running Tests

```bash
# Run all tests (unit + integration + security + multi-DB SQLite)
pytest

# Run with coverage report
pytest --cov=tenxyte --cov-report=html
```

### Multi-Database Tests

The test suite includes 50 dedicated multi-DB tests that verify all Tenxyte models and auth flows work identically across every supported backend:

```bash
# SQLite (default, in-memory)
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite" --create-db

# PostgreSQL (requires psycopg2-binary + running server)
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql" --create-db

# MySQL (requires mysqlclient + running server)
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mysql" --create-db

# MongoDB (requires django-mongodb-backend + running server)
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb" --create-db
```

Database connection settings are configured via environment variables:

| Variable | Default | Backend |
|----------|---------|---------|
| `TENXYTE_PG_HOST` / `_PORT` / `_NAME` / `_USER` / `_PASSWORD` | `localhost:5432/tenxyte_test` | PostgreSQL |
| `TENXYTE_MYSQL_HOST` / `_PORT` / `_NAME` / `_USER` / `_PASSWORD` | `127.0.0.1:3306/tenxyte_test` | MySQL |
| `TENXYTE_MONGO_HOST` / `_PORT` / `_NAME` | `localhost:27017/tenxyte_test` | MongoDB |

### Test Coverage

| Metric | Value |
|--------|-------|
| Total tests | **192** |
| Pass rate | **100%** |
| Code coverage | **68.51%** (minimum threshold: 60%) |
| Multi-DB tests per backend | **50** |
| Verified backends | SQLite, PostgreSQL, MySQL, MongoDB |

## Troubleshooting

### MongoDB Issues

**Problem 1:** `MongoDB does not support AutoField` or `BigAutoField`

```
SystemCheckError: System check identified some issues:
ERRORS:
tenxyte.User.id: (mongodb.E001) MongoDB does not support BigAutoField.
```

**Solution:**
1. Set the correct default auto field:
   ```python
   DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
   ```

2. Disable migrations for built-in apps (their models use integer PKs):
   ```python
   MIGRATION_MODULES = {
       'contenttypes': None,
       'auth': None,
   }
   ```

3. Remove `django.contrib.admin` from `INSTALLED_APPS` (incompatible with ObjectId PKs).

**Problem 2:** `Model instances without primary key value are unhashable`

```
TypeError: Model instances without primary key value are unhashable
```

**Solution:**
This occurs during `migrate` because Django's `create_permissions` and `create_contenttypes` signals
try to hash ContentType objects with `pk=None`. Add `MIGRATION_MODULES` to disable built-in app
migrations (see Problem 1). If the error persists, disconnect the problematic signals before migrations:
```python
from django.db.models.signals import post_migrate
post_migrate.disconnect(dispatch_uid='django.contrib.auth.management.create_permissions')
post_migrate.disconnect(dispatch_uid='django.contrib.contenttypes.management.create_contenttypes')
```

### PostgreSQL/MySQL Issues

**Problem:** User model conflicts

**Solution:** Just set the custom user model:
```python
AUTH_USER_MODEL = 'tenxyte.User'
```

For SQL databases, you can keep the standard Django apps:
```python
INSTALLED_APPS = [
    'django.contrib.admin',         # ✅ OK for SQL databases
    'django.contrib.auth',          # ✅ OK for SQL databases
    'django.contrib.contenttypes',  # ✅ OK for SQL databases
    # ... rest
    'tenxyte',
]
```

### Common Installation Issues

**Problem:** `ModuleNotFoundError: No module named 'rest_framework'`

**Solution:**
```bash
pip install djangorestframework
```

**Problem:** `ModuleNotFoundError: No module named 'corsheaders'`

**Solution:**
```bash
pip install django-cors-headers
```

**Problem:** JWT tokens not working / 401 Unauthorized

**Solution:** Ensure you're sending the correct headers:
```http
X-Access-Key: <your_app_access_key>
X-Access-Secret: <your_app_access_secret>
Authorization: Bearer <jwt_token>
```

## Database-Specific Notes

### SQLite
- ✅ Works out of the box
- ⚠️ Not recommended for production
- ✅ Perfect for development and testing

### PostgreSQL
- ✅ Recommended for production
- ✅ All Django apps compatible
- ⚠️ Requires `psycopg2-binary` package

### MySQL/MariaDB
- ✅ Widely supported
- ✅ All Django apps compatible
- ⚠️ Requires `mysqlclient` package

### MongoDB
- ✅ NoSQL flexibility
- ⚠️ Requires `django-mongodb-backend` package
- ⚠️ Requires `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'`
- ⚠️ Requires `MIGRATION_MODULES` to disable `contenttypes` and `auth` migrations
- ⚠️ Remove `django.contrib.admin` (incompatible with ObjectId PKs)
- ⚠️ M2M `remove()` not supported on auto-generated through tables (use `set()` or `add()`/`clear()` patterns)
- See [MongoDB Configuration](#mongodb) for full setup

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Credits

Developed and maintained by the Tenxyte Team.
