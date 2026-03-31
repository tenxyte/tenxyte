![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Framework-Agnostic Python Authentication in minutes — JWT, RBAC, 2FA, Magic Links, Passkeys, Social Login, Breach Check, Organizations (B2B), multi-application support.

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-4.2%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml)
![Downloads](https://img.shields.io/pypi/dm/tenxyte)
[![Total](https://static.pepy.tech/personalized-badge/tenxyte?period=total&units=INTERNATIONAL_SYSTEM&left_color=black&right_color=green&left_text=downloads)](https://pepy.tech/projects/tenxyte)

---

## Quickstart — 2 minutes to your first API call

### 1. Install

```bash
pip install tenxyte
```

> **Requirements:** Python 3.10+, Django 4.2+ or FastAPI 0.135+

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

## AIRS — AI Responsibility & Security (AI-Ready Start)

Tenxyte doesn’t just authenticate humans — it makes your backend **safe to connect to AI agents**.

**Core principle**: an AI agent never acts on its own authority. It borrows a user’s permissions via a scoped, time-limited `AgentToken`, and every action becomes auditable, controllable, and suspendable.

### A real, end-to-end “AI Ready” flow

#### 1) A user delegates a limited token to an agent

```http
POST /ai/tokens/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "agent_id": "finance-agent-v2",
  "expires_in": 3600,
  "permissions": ["read:reports", "write:invoices"],
  "organization": "acme-corp",
  "budget_limit_usd": 5.00,
  "circuit_breaker": {
    "max_requests_per_minute": 30,
    "max_requests_total": 500
  },
  "dead_mans_switch": {
    "heartbeat_required_every": 300
  }
}
```

**Response (201):**

```json
{
  "id": 42,
  "token": "eKj3...raw_token...Xz9",
  "agent_id": "finance-agent-v2",
  "status": "ACTIVE",
  "expires_at": "2024-01-20T16:00:00Z"
}
```

> ⚠️ The raw `token` is returned **only once** at creation — only its SHA-256 hash is persisted. Store it securely.

The agent then calls your APIs with:

```http
Authorization: AgentBearer <raw_token>
```

#### 2) Every agent request is double-checked (Agent scope + Human RBAC)

Tenxyte enforces **Double RBAC Validation**:

- **Agent scope check**: is the permission in the token’s `granted_permissions`?
- **Human check**: does the delegating user still have it?

If either fails, the request is rejected (`403 Forbidden`).

#### 3) Dangerous actions can require Human-in-the-Loop (HITL)

Endpoints decorated with `@require_agent_clearance(human_in_the_loop_required=True)` do not execute immediately when called by an agent. Tenxyte creates an `AgentPendingAction` and returns **`202 Accepted`**:

```json
{
  "status": "pending_confirmation",
  "message": "This action requires human approval.",
  "confirmation_token": "hitl_a1b2c3d4e5f6...",
  "expires_at": "2024-01-20T16:10:00Z"
}
```

The human confirms via:

```http
POST /ai/pending-actions/<confirmation_token>/confirm/
Authorization: Bearer <user_jwt>
```

The agent then retries the original call with the confirmed token:

```http
X-Action-Confirmation: hitl_a1b2c3d4e5f6...
```

#### 4) Runaway agents get stopped automatically (Circuit Breaker + Dead Man’s Switch)

If the agent exceeds RPM/total limits, hits anomaly thresholds, misses the heartbeat, or exhausts its budget, the token is automatically **SUSPENDED**.

```http
POST /ai/tokens/{id}/heartbeat/
Authorization: AgentBearer <raw_token>
```

#### 5) Budget tracking turns LLM spend into an enforcement mechanism

Your code reports cost; Tenxyte accumulates it and suspends the token when the limit is reached.

```http
POST /ai/tokens/{id}/report-usage/
Authorization: AgentBearer <raw_token>
Content-Type: application/json

{
  "cost_usd": 0.042,
  "prompt_tokens": 1250,
  "completion_tokens": 450
}
```

#### 6) Forensic audit: trace “which prompt caused which action”

Attach `X-Prompt-Trace-ID` to agent requests and Tenxyte links it to pending actions and the audit trail.

```http
X-Prompt-Trace-ID: trace_7f3a2b9c-...
```

> Want the full reference (PII redaction, settings, suspension reasons, etc.)? See the **[AIRS Guide](airs.md)**.

---

## Organizations — B2B Multi-Tenant, Out of the Box

Building SaaS for companies? Tenxyte ships a full multi-tenant hierarchy with per-org RBAC, member management, and invitation flows — no extra infrastructure needed.

### Enable in one line

```python
TENXYTE_ORGANIZATIONS_ENABLED = True
```

### Model any org structure

```
Acme Corp (root)
├── Engineering
│   ├── Backend Team
│   └── Frontend Team
└── Sales
    └── EMEA
```

```http
POST /api/v1/auth/organizations/
Authorization: Bearer <token>
Content-Type: application/json

{ "name": "Engineering", "slug": "acme-engineering", "parent_id": 1 }
```

### Invite members by email

```http
POST /api/v1/auth/organizations/invitations/
Authorization: Bearer <token>
X-Org-Slug: acme-corp
Content-Type: application/json

{ "email": "newmember@example.com", "role_code": "member", "expires_in_days": 7 }
```

An invitation email is sent. The user accepts by registering or logging in.

### Org-scoped permissions in views

```python
from tenxyte.decorators import require_jwt, require_org_context, require_org_permission

class OrgSettingsView(APIView):
    @require_jwt
    @require_org_context
    @require_org_permission('org.manage')
    def post(self, request):
        org = request.organization   # resolved from X-Org-Slug header
        ...
```

### Role inheritance

When `TENXYTE_ORG_ROLE_INHERITANCE = True` (default), roles propagate down the hierarchy: an `admin` in `Acme Corp` is automatically `admin` in `Engineering`, `Backend Team`, etc.

> Full reference: **[Organizations Guide](organizations.md)**

---

## Shortcut Secure Mode — Production-Ready Security in One Line

Instead of tuning 115+ settings, pick a preset that matches your threat model:

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'   # 'development' | 'medium' | 'robust'
```

| Setting | `development` | `medium` | `robust` |
|---|---|---|---|
| **Target** | Prototypes, local dev | Public SaaS, B2C | Fintech, healthcare, GDPR |
| Access token lifetime | 1h | 15min | **5min** |
| Refresh token rotation | ✗ | ✓ | ✓ |
| Max login attempts | 10 | 5 | **3** |
| Lockout duration | 15min | 30min | **60min** |
| Password history | ✗ | 5 | **12** |
| Breach check (HIBP) | ✗ | ✓ + block | ✓ + block |
| Audit logging | ✗ | ✓ | ✓ |
| Device limits | ✗ | 5 | **2 (deny)** |
| Security headers | ✗ | ✓ | ✓ |
| Passkeys (WebAuthn) | ✗ | ✗ | **✓** |

Every setting remains individually overridable — the preset is a starting point, not a cage:

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'robust'
TENXYTE_WEBAUTHN_ENABLED = False         # opt-out of passkeys
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 600  # 10min instead of 5min
```

> Full reference: **[Settings Guide](settings.md)**

---

## Passkeys (WebAuthn / FIDO2) — Passwordless, Phishing-Proof

Tenxyte ships a complete WebAuthn/FIDO2 stack. Users register once with Face ID, Touch ID, or a hardware key — then authenticate with no password, ever.

### Enable

```python
TENXYTE_WEBAUTHN_ENABLED = True          # auto-enabled with 'robust' preset
TENXYTE_WEBAUTHN_RP_ID = 'yourapp.com'
TENXYTE_WEBAUTHN_RP_NAME = 'Your App'
```

> Requires: `pip install tenxyte[webauthn]`

### 1) Register a passkey

```http
# Step 1 — Get browser challenge
POST /api/v1/auth/webauthn/register/begin/
Authorization: Bearer <user_jwt>

# Step 2 — Submit browser credential
POST /api/v1/auth/webauthn/register/complete/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "challenge_id": 123,
  "credential": { ...WebAuthn browser response... },
  "device_name": "MacBook Touch ID"
}
```

**Response (201):**

```json
{
  "message": "Passkey registered successfully",
  "credential": {
    "id": "cred_abc123",
    "device_name": "MacBook Touch ID",
    "created_at": "2024-01-20T15:00:00Z"
  }
}
```

### 2) Authenticate — no password

```http
# Step 1 — Get browser challenge
POST /api/v1/auth/webauthn/authenticate/begin/
Content-Type: application/json

{ "email": "user@example.com" }

# Step 2 — Submit browser credential
POST /api/v1/auth/webauthn/authenticate/complete/
Content-Type: application/json

{
  "challenge_id": 456,
  "credential": { ...WebAuthn browser response... }
}
```

**Response (200):**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": { "id": 42, "email": "user@example.com" },
  "message": "Authentication successful"
}
```

Supports **resident keys** — the passkey itself identifies the user, no email needed.

> Full reference: **[API Endpoints](endpoints.md)**

---

## Why Choose Tenxyte?

Tenxyte is the only auth package built for **both human users and AI agents**, while staying fully self-hosted, open-source, and framework-agnostic — with full Django support today, FastAPI (partial), and Java, Node.js, and PHP on the roadmap.

### Feature Comparison

| Feature | **Tenxyte** | django-allauth | Clerk | Auth0 |
|---|:---:|:---:|:---:|:---:|
| **Type** | Django package | Django package | SaaS | SaaS |
| **Open source** | ✅ MIT | ✅ MIT | ❌ | ❌ |
| **Self-hosted / data ownership** | ✅ | ✅ | ❌ | ❌ ¹ |
| **Framework support** | ✅ Django (full) · FastAPI (partial) · Java, Node.js, PHP coming | Django only | SDK (JS-first) | SDK (20+ languages) |
| **JWT (access + refresh)** | ✅ | ❌ ² | ✅ | ✅ |
| **Social login** | ✅ 4 providers | ✅ 50+ providers | ✅ 20+ providers | ✅ 30+ providers |
| **Magic links** | ✅ | ✅ | ✅ | ✅ |
| **Passkeys / WebAuthn** | ✅ | ✅ | ✅ | ✅ |
| **2FA / TOTP + backup codes** | ✅ | ✅ | ✅ | ✅ |
| **RBAC (roles + perms + Python decorators)** | ✅ full | ❌ | ⚠️ org-scoped | ⚠️ add-on |
| **Organizations / multi-tenant** | ✅ hierarchical | ❌ | ✅ flat | ✅ |
| **Breach check (HaveIBeenPwned)** | ✅ built-in | ❌ | ❌ | ✅ |
| **Progressive account lockout** | ✅ | ⚠️ basic | ✅ | ✅ |
| **Audit logging (queryable API)** | ✅ | ❌ | ⚠️ dashboard | ⚠️ log streams |
| **Shortcut Secure Mode presets** | ✅ | ❌ | ❌ | ❌ |
| **AI agent tokens (AIRS)** | ✅ | ❌ | ❌ | ⚠️ experimental ³ |
| **Human-in-the-Loop (HITL)** | ✅ | ❌ | ❌ | ❌ |
| **LLM budget tracking** | ✅ | ❌ | ❌ | ❌ |
| **Circuit breaker + Dead Man's Switch** | ✅ | ❌ | ❌ | ❌ |
| **Forensic trace (X-Prompt-Trace-ID)** | ✅ | ❌ | ❌ | ❌ |
| **Free / pricing** | ✅ unlimited | ✅ unlimited | ⚠️ 10k MAU | ⚠️ 7.5k MAU |

> ✅ = native support · ⚠️ = partial / limited · ❌ = not available

¹ Auth0 offers a "Private Cloud" deploy option at enterprise pricing.  
² django-allauth uses Django sessions; JWT requires a separate package (e.g. `djangorestframework-simplejwt`).  
³ Auth0 announced OAuth-based AI agent flows in 2025 (`auth0.com/ai`), but with no budget tracking, HITL, or circuit breakers.

### When to choose Tenxyte

- **You need AI-ready infrastructure** — scoped agent tokens, HITL, budget enforcement, and circuit breakers are built-in, not bolted on.
- **You own your data** — users, tokens, audit logs, and org structures live in your own database.
- **You're building serious SaaS** — hierarchical multi-tenant orgs, double-RBAC validation, and forensic audit trails out of the box.
- **You want one config line for production security** — `TENXYTE_SHORTCUT_SECURE_MODE = 'robust'` replaces a security audit checklist.
- **You need multi-framework coverage** — full Django integration today, FastAPI (partial) already supported, with Java (Spring Boot), Node.js (Express, Nest.js), and PHP (Laravel, Symfony) on the roadmap.

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
- 9 decorators + DRF permission classes

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
- [**Settings Reference**](settings.md) - All 115+ configuration options
- [**API Endpoints**](endpoints.md) - Full endpoint reference with examples
- [**Admin Accounts**](admin.md) - Manage Superusers and RBAC Admins
- [**Applications Guide**](applications.md) - Manage API clients and credentials
- [**RBAC Guide**](rbac.md) - Roles, permissions, and decorators
- [**Security Guide**](security.md) - Security features and best practices
- [**Organizations Guide**](organizations.md) - B2B multi-tenant setup
- [**AIRS Guide**](airs.md) - AI Responsibility & Security
- [**Migration Guide**](MIGRATION_GUIDE.md) - Migration from dj-rest-auth, simplejwt

### 📦 **SDK Integration (JavaScript / TypeScript)**
- [**JavaScript SDK Overview**](integration/javascript/index.md) - Packages, installation, configuration, error handling
- [**@tenxyte/core Guide**](integration/javascript/core.md) - Framework-agnostic SDK — all 10 modules, cookie mode, PKCE, events
- [**@tenxyte/react Guide**](integration/javascript/react.md) - React hooks, TenxyteProvider, SPA examples
- [**@tenxyte/vue Guide**](integration/javascript/vue.md) - Vue 3 composables, plugin setup, SPA examples

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
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_sqlite"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_pgsql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mysql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mongodb"
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
