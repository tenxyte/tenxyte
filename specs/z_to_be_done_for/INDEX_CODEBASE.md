# 📇 INDEX COMPLET - TENXYTE CODEBASE

## Légende
- 📄 Fichier Python (.py)
- 📁 Répertoire
- 🧪 Test
- 📖 Documentation
- ⚙️ Configuration
- 🔐 Sécurité-critique

---

## 🔷 CORE - LOGIQUE PURE (Framework-agnostique)

### `src/tenxyte/core/` - Cœur fonctionnel

```
core/
├── __init__.py                    # Exports public
├── jwt.py                         # 🔐 JWT generation/validation, refresh tokens
├── totp_service.py                # 🔐 2FA TOTP, secret generation, QR codes
├── webauthn_service.py            # 🔐 WebAuthn/FIDO2, credential registration
├── magic_link_service.py          # 🔐 Magic link generation, validation
├── session_service.py             # User session tracking, device limits
├── email_service.py               # Email abstraction (interface)
├── cache_service.py               # Cache abstraction (Redis, Memcache)
├── task_service.py                # Async task abstraction (Celery, RQ)
├── settings.py                    # Settings loader, Pydantic config
├── schemas.py                     # Shared Pydantic schemas
└── env_provider.py                # Environment variable access
```

**Caractéristiques:**
- ✅ Zero framework dependencies
- ✅ Full type hints
- ✅ 90%+ test coverage
- ✅ Pure, testable functions

---

## 🔷 MODELS - MODÈLES DE DONNÉES

### `src/tenxyte/models/` - Définition des entités

```
models/
├── __init__.py                    # Model exports
├── base.py                        # 🔐 AbstractUser
│                                  #   - email, phone, password (bcrypt)
│                                  #   - TOTP secret (encrypted), 2FA
│                                  #   - WebAuthn credentials
│                                  #   - Social auth links
│                                  #   - Device tracking
│                                  #   - GDPR deletion fields
│
├── agent.py                       # 🔐 AgentToken, AgentPendingAction (AIRS)
│                                  #   - Token scoped permissions
│                                  #   - Circuit breaker limits
│                                  #   - Budget tracking
│                                  #   - Dead man's switch
│
├── organization.py                # Organization, OrganizationMember
│                                  #   - Hierarchical structure (parent_id)
│                                  #   - Org-scoped roles
│                                  #   - Membership invitations
│
├── role.py                        # Role, Permission
│                                  #   - Roles with permissions
│                                  #   - Default RBAC roles
│                                  #   - Org-scoped role inheritance
│
├── tenant.py                      # Tenant (multi-tenancy support)
├── social.py                      # SocialAuthConnection (OAuth links)
├── magic_link.py                  # MagicLinkToken, MagicLinkRequest
├── webauthn.py                    # WebAuthnCredential, WebAuthnChallenge
├── gdpr.py                        # GDPRDeletionRequest, data export
│
└── audit.py                       # AuditLog (activity tracking)
                                   #   - Tracks all auth events
                                   #   - Links to agent tokens via prompt_trace_id
                                   #   - Full queryable API
```

**Types de modèles:**
1. **Abstracts** - `AbstractUser`, `AbstractRole`, etc.
2. **Concrètes** - `User`, `Role`, etc. (auto-created if not overridden)
3. **Through tables** - `UserRole`, `RolePermission`, etc.

---

## 🔷 ADAPTATEURS - INTÉGRATIONS FRAMEWORK

### `src/tenxyte/adapters/django/` - Django Integration

```
adapters/django/
├── __init__.py
├── middleware.py                  # CORS, Auth, Tenant context, Security headers
├── authentication.py              # JWT auth backend for Django
├── cache_service.py               # Redis/Memcache adapter
├── email_service.py               # Django Mail / SendGrid adapter
├── task_service.py                # Celery / RQ adapter
├── totp_storage.py                # Store/retrieve TOTP secrets (encrypted)
├── webauthn_storage.py            # Store/retrieve WebAuthn challenges
├── settings_provider.py           # Read settings from Django
└── context_processors.py          # Template context
```

### `src/tenxyte/adapters/fastapi/` - FastAPI Integration

```
adapters/fastapi/
├── __init__.py
├── routers.py                     # FastAPI router setup (auth, RBAC, etc.)
├── models.py                      # Pydantic request/response models
├── repositories.py                # SQLAlchemy ORM models
├── task_service.py                # Async task runner (asyncio, celery)
├── middleware.py                  # (in progress)
└── decorators.py                  # (planned)
```

**État FastAPI:** ✅ Routers OK, ⚠️ Middleware/decorators en dev

---

## 🔷 VIEWS - API ENDPOINTS

### `src/tenxyte/views/` - Route handlers (Django REST Framework)

```
views/
├── __init__.py
│
├── auth_views.py                  # Basic auth
│   - POST /register/              # User registration
│   - POST /login/email/           # Email/password login
│   - POST /login/phone/           # Phone OTP login
│   - POST /refresh/               # Refresh JWT
│   - POST /logout/                # Logout (blacklist token)
│   - POST /logout/all/            # Logout all devices
│
├── otp_views.py                   # One-Time Password
│   - POST /otp/request/           # Request OTP (email/SMS)
│   - POST /otp/verify/email/      # Verify email OTP
│   - POST /otp/verify/phone/      # Verify phone OTP
│
├── magic_link_views.py            # Passwordless
│   - POST /magic-link/request/    # Send magic link
│   - POST /magic-link/verify/     # Verify & login
│
├── webauthn_views.py              # Passkeys / FIDO2
│   - POST /webauthn/register/begin/      # Start registration
│   - POST /webauthn/register/complete/   # Complete registration
│   - POST /webauthn/authenticate/begin/  # Start authentication
│   - POST /webauthn/authenticate/complete/  # Complete auth
│
├── security_views.py              # Password & 2FA
│   - POST /password/reset/request/  # Reset password
│   - POST /password/reset/confirm/  # Confirm password reset
│   - POST /password/change/         # Change password (authenticated)
│   - POST /2fa/setup/               # Setup TOTP 2FA
│   - POST /2fa/confirm/             # Confirm TOTP
│   - POST /2fa/disable/             # Disable 2FA
│   - GET  /2fa/backup-codes/        # Get backup codes
│
├── rbac_views.py                  # Role-Based Access Control
│   - GET  /roles/                 # List roles
│   - GET  /permissions/           # List permissions
│   - POST /users/{id}/roles/      # Assign role to user
│   - DELETE /users/{id}/roles/    # Remove role from user
│   - POST /users/{id}/permissions/ # Direct permission
│
├── organization_views.py          # B2B Multi-tenant
│   - CRUD /organizations/         # Org management
│   - GET  /organizations/{id}/members/  # Members
│   - POST /organizations/invitations/   # Invite members
│   - GET  /invitations/{token}/         # Accept invitation
│
├── agent_views.py                 # 🔐 AI Agent Tokens (AIRS)
│   - POST /ai/tokens/             # Create agent token
│   - GET  /ai/tokens/             # List user's tokens
│   - POST /ai/tokens/{id}/revoke/ # Revoke token
│   - POST /ai/tokens/{id}/suspend/ # Suspend token
│   - POST /ai/tokens/{id}/heartbeat/  # Send heartbeat
│   - POST /ai/tokens/{id}/report-usage/ # Report LLM usage
│   - GET  /ai/pending-actions/    # List pending confirmations
│   - POST /ai/pending-actions/{token}/confirm/ # Confirm action (HITL)
│
├── dashboard_views.py             # Stats & monitoring
│   - GET  /dashboard/stats/       # Auth stats
│   - GET  /audit-logs/            # Audit log API
│
├── gdpr_admin_views.py            # GDPR Data deletion
│   - POST /account/delete-request/ # Request deletion
│   - POST /account/delete-confirm/ # Confirm deletion
│   - GET  /account/deletion-status/ # Check status
│   - POST /account/data-export/    # Export user data
│
├── magic_link_views.py            # (duplicate check)
└── profile_views.py               # (if exists)
    - GET  /me/                    # Current user info
    - GET  /me/roles/              # User's roles
    - PATCH /me/                   # Update profile
```

**Total:** ~80+ endpoints

---

## 🔷 SÉRIALISEURS - VALIDATION DONNÉES

### `src/tenxyte/serializers/` - DRF Serializers

```
serializers/
├── __init__.py
├── auth_serializers.py            # Register, login, refresh
├── otp_serializers.py             # OTP request/verify
├── security_serializers.py        # Password, 2FA, passkeys
├── rbac_serializers.py            # Roles, permissions, assignments
├── organization_serializers.py    # Org management, invitations
├── gdpr_admin_serializers.py      # Data export, deletion
└── (agent_serializers.py)         # Agent token requests/responses
```

**Chaque serializer:**
- ✅ Full validation rules
- ✅ Custom validators
- ✅ Error messages clairs
- ✅ Type hints

---

## 🔷 SERVICES - LOGIQUE MÉTIER

### `src/tenxyte/services/` - Business logic

```
services/
├── __init__.py
├── agent_service.py               # 🔐 Agent token lifecycle
│                                  #   - Create with scoped perms
│                                  #   - Circuit breaker enforcement
│                                  #   - Budget accumulation
│                                  #   - Token suspension logic
│
├── social_auth_service.py         # OAuth flows
│                                  #   - Google, GitHub, Microsoft, Facebook
│                                  #   - Token exchange, user creation
│                                  #   - Linked account management
│
├── email_service.py               # Email notifications
│                                  #   - Registration confirmation
│                                  #   - Password reset
│                                  #   - Account deletion
│                                  #   - OTP emails
│
└── stats_service.py               # Analytics & metrics
                                   #   - User counts
                                   #   - Auth method distribution
                                   #   - Activity trends
```

---

## 🔷 PORTS - INTERFACES ABSTRAITES

### `src/tenxyte/ports/` - Hexagonal boundaries

```
ports/
├── __init__.py
├── repositories.py                # Abstract repository interfaces
│                                  #   - UserRepository
│                                  #   - RoleRepository
│                                  #   - TokenRepository
│                                  #   - etc.
│
├── email_port.py                  # Abstract email interface
├── cache_port.py                  # Abstract cache interface
├── task_port.py                   # Abstract task interface
└── storage_port.py                # Abstract file storage interface
```

**Rôle:** Define contracts; adapters implement them

---

## 🔷 CONFIGURATION - SETTINGS

### `src/tenxyte/conf/` - Configuration & Presets

```
conf/
├── __init__.py                    # Expose auth_settings
│
├── base.py                        # 🔐 115+ settings
│                                  #   JWT, TOTP, WebAuthn, OAuth
│                                  #   Email, SMS, Rate limiting
│                                  #   Account lockout, session limits
│                                  #   RBAC, Organizations, GDPR
│                                  #   AIRS (agent tokens)
│                                  #   Validated with Pydantic
│
├── presets.py                     # Shortcut Secure Mode
│                                  #   - 'development': lax
│                                  #   - 'medium': SaaS-grade
│                                  #   - 'robust': fintech-grade
│
├── jwt.py                         # JWT-specific settings
│                                  #   - Secret key management
│                                  #   - Token lifetimes
│                                  #   - Rotation policies
│
├── social.py                      # OAuth provider config
│                                  #   - Google, GitHub, Microsoft, Facebook
│                                  #   - Credentials, scopes
│
├── communication.py               # Email & SMS config
│                                  #   - Providers (Django Mail, SendGrid, Twilio)
│                                  #   - Templates
│
└── airs.py                        # Agent token defaults
                                   #   - Default budget
                                   #   - Circuit breaker limits
                                   #   - Heartbeat interval
```

---

## 🔷 MIDDLEWARE & AUTHENTIFICATION

### `src/tenxyte/middleware/` - Request processing

```
middleware/
├── __init__.py
├── auth.py                        # JWT auth extraction
├── cors.py                        # CORS headers
├── tenant.py                      # Multi-tenant context (X-Org-Slug)
└── security.py                    # Security headers (HSTS, CSP, etc.)
```

### `src/tenxyte/authentication.py` - Django auth backend

```
authentication.py
├── JWTAuthentication              # Backend for DRF
├── AgentTokenAuthentication       # Backend for agents (AIRS)
└── Application auth               # X-Access-Key validation
```

---

## 🔷 MANAGEMENT COMMANDS

### `src/tenxyte/management/commands/` - Django CLI

```
management/commands/
├── tenxyte_quickstart.py          # Setup wizard
│                                  #   - Migrate DB
│                                  #   - Create default roles
│                                  #   - Create test application
│                                  #   - Print credentials
│
├── tenxyte_seed.py                # Load fixture data
├── tenxyte_cleanup.py             # Cleanup expired tokens
└── tenxyte_purge_audit_logs.py    # Archive/delete old logs
```

---

## 🔷 MIGRATIONS - DATABASE

### `src/tenxyte/migrations/` - Schema versions

```
migrations/
├── 0001_core.py                   # Initial: User, Role, Permission
├── 0002_agenttoken_*.py           # Add AgentToken, PendingAction
├── 0003_auditlog_*.py             # Add AuditLog table
├── 0004_*.py                      # Add prompt_trace_id
├── 0005_hash_refresh_*.py         # Hash refresh tokens
├── 0006_encrypt_totp_*.py         # Encrypt TOTP secrets
├── 0007_*.py                      # OAuth, WebAuthn
├── 0008_merge_initial.py          # Squash initial migrations
├── 0009_*.py                      # WebAuthn challenges
├── 0010_permission_*.py           # Add permission.updated_at
├── 0011_add_profile_*.py          # Profile fields
└── 0012_*.py                      # App redirects, lockout
```

**État:** ✅ 12 migrations, production-ready

---

## 🔷 DECORATORS & UTILITIES

### `src/tenxyte/decorators.py` - Permission decorators

```python
@require_jwt                        # Require JWT token
@require_agent_token               # Require agent token (AIRS)
@require_permission('code')        # Require specific permission
@require_role('code')              # Require specific role
@require_org_context               # Require org context (X-Org-Slug)
@require_org_permission('code')    # Org-scoped permission
@require_agent_clearance           # Agent endpoint decorator
  └── human_in_the_loop_required   # Triggers HITL workflow
@rate_limit(10)                    # Per-user rate limiting
```

### `src/tenxyte/exceptions.py` - Custom exceptions

```python
AuthenticationFailed               # JWT invalid/missing
PermissionDenied                   # Insufficient permissions
TokenExpired                       # Token lifecycle issue
InvalidOTP                         # OTP validation failed
AccountLocked                      # Too many login attempts
AgentTokenSuspended                # Circuit breaker triggered
PendingActionRequired              # HITL confirmation needed
```

### `src/tenxyte/filters.py` - DRF filters

```python
UserFilter                         # Filter users by email, role, org
AuditLogFilter                     # Filter audit logs by date, action, user
```

---

## 🔷 TEMPLATES & STATIC

### `src/tenxyte/templates/` - Email templates

```
templates/emails/
├── registration_confirmation.html     # Email confirmation
├── password_reset.html                # Password reset link
├── otp_email.html                     # OTP code email
├── account_deletion_*.html            # Deletion workflow
├── magic_link.html                    # Magic link email
└── org_invitation.html                # Org member invitation
```

### `src/tenxyte/static/` - Frontend assets

```
static/tenxyte/
├── js/
│   ├── auth.js                    # Frontend auth helpers
│   ├── device-info.js             # Device fingerprinting
│   └── webauthn.js                # WebAuthn browser API wrapper
│
└── css/
    └── (minimal, usually frontend owns styling)
```

---

## 🔷 BACKENDS - EMAIL/SMS

### `src/tenxyte/backends/` - Provider adapters

```
backends/
├── __init__.py
└── email.py                       # Email backend dispatch
                                   #   - Django Mail (SMTP)
                                   #   - SendGrid
                                   #   - Console (development)
```

---

## 🔷 DOCUMENTATION GENERATION

### `src/tenxyte/docs/` - Schema export

```
docs/
├── __init__.py
└── schemas.py                     # OpenAPI schema generation
                                   #   - Auto-generated from DRF
                                   #   - Swagger UI, ReDoc
```

---

## 🔷 TASKS - ASYNC JOBS

### `src/tenxyte/tasks/` - Background jobs

```
tasks/
├── __init__.py
└── agent_tasks.py                 # Periodic agent checks
                                   #   - Circuit breaker evaluation
                                   #   - Heartbeat validation
                                   #   - Budget enforcement
                                   #   - Token suspension
```

---

## 🔷 TENANT CONTEXT

### `src/tenxyte/tenant_context.py` - Multi-tenancy helpers

```python
get_current_tenant()               # Extract from X-Org-Slug header
set_tenant_context()               # Set in thread-local/context var
with_tenant_context()              # Context manager
TenantContextMiddleware             # Auto-extract tenant
```

---

## 🔷 SIGNALS & APP CONFIG

### `src/tenxyte/signals.py` - Django signals

```python
post_save.connect(on_user_created)  # Create default roles
post_delete.connect(on_user_deleted) # Cleanup tokens
```

### `src/tenxyte/apps.py` - Django app config

```python
class TenxyteConfig(AppConfig):
    name = 'tenxyte'
    verbose_name = 'Tenxyte Authentication'
    # Connect signals, initialize adapters
```

---

## 🔷 ADMIN INTERFACE

### `src/tenxyte/admin.py` - Django admin customization

```python
UserAdmin                          # Custom user admin
RoleAdmin                          # Role editor
PermissionAdmin                    # Permission editor
OrganizationAdmin                  # Org tree view
AuditLogAdmin                      # Read-only audit log
```

---

# 🧪 TESTS - SUITE DE TESTS

## `tests/` - 187 test files

### Unit Tests (Pure Core)

```
tests/core/
├── test_jwt_service.py            # JWT generation, validation, rotation
├── test_totp_service.py           # TOTP generation, verification
├── test_webauthn_service.py       # WebAuthn registration, auth
├── test_magic_link_service.py     # Magic link generation, expiry
├── test_session_service.py        # Session tracking, device limits
├── test_password_hashing.py       # bcrypt hashing
├── test_breach_check.py           # HaveIBeenPwned integration
├── test_email_service.py          # Email abstraction
├── test_cache_service.py          # Cache abstraction
└── test_task_service.py           # Task abstraction
```

### Integration Tests (Django)

```
tests/integration/django/
├── settings.py                    # Test Django settings
├── urls.py                        # Test URL config
│
├── test_auth_views.py             # Register, login, logout
├── test_otp_views.py              # OTP flow testing
├── test_webauthn_views.py         # Passkey registration/auth
├── test_magic_link_views.py       # Magic link flow
├── test_security_views.py         # Password reset, 2FA
├── test_rbac_views.py             # RBAC endpoints
├── test_rbac_decorators.py        # Permission decorators
├── test_organization_views.py     # Org CRUD, invitations
├── test_org_hierarchy.py          # Org tree logic
├── test_agent_tokens.py           # Agent token lifecycle
├── test_airs_circuit_breaker.py   # Circuit breaker testing
├── test_airs_budget.py            # Budget tracking
├── test_airs_hitl.py              # Human-in-the-loop workflow
├── test_audit_logging.py          # Audit trail
├── test_gdpr_deletion.py          # Account deletion
├── test_social_auth.py            # OAuth flows
├── test_middleware.py             # Middleware stack
│
└── multidb/                       # Multi-database tests
    ├── settings_sqlite.py
    ├── settings_pgsql.py
    ├── settings_mysql.py
    └── settings_mongodb.py
```

### Integration Tests (FastAPI)

```
tests/integration/fastapi/
├── settings.py                    # Test FastAPI settings
├── test_routers.py                # FastAPI route testing
├── test_auth_flow.py              # End-to-end auth flow
└── (more to be added)
```

### Fixtures

```
tests/fixtures/
├── users.py                       # User factory, fixtures
├── organizations.py               # Org factory
├── roles.py                       # Role fixtures
├── permissions.py                 # Permission fixtures
└── agent_tokens.py                # Agent token fixtures
```

**Coverage:** ✅ 90%+ required (pytest.ini)

---

# 📚 DOCUMENTATION

## `docs/` - 59 files

### Guides de démarrage
```
docs/
├── quickstart.md                  # Django 2-minute setup
├── fastapi_quickstart.md          # FastAPI setup
└── MIGRATION_GUIDE.md             # From dj-rest-auth, simplejwt
```

### Guides de configuration
```
├── settings.md                    # 115+ settings reference
├── jwt.md                         # JWT configuration
├── security.md                    # Security features
├── rbac.md                        # Role-based access control
└── organizations.md               # Multi-tenant setup
```

### Guides features
```
├── endpoints.md                   # Complete API reference
├── applications.md                # API client management
├── airs.md                        # Agent tokens & HITL
├── architecture.md                # Hexagonal design
└── custom_adapters.md             # Custom framework adapters
```

### Guides techniques
```
├── async_guide.md                 # Async/await patterns
├── task_service.md                # Background job setup
├── TESTING.md                     # Testing strategies
├── CONTRIBUTING.md                # Contribution guide
└── troubleshooting.md             # Common issues
```

### Intégration JavaScript
```
├── integration/javascript/index.md
├── integration/javascript/core.md          # @tenxyte/core
├── integration/javascript/react.md         # @tenxyte/react
└── integration/javascript/vue.md           # @tenxyte/vue
```

### Config fichiers
```
├── mkdocs.yml                     # MkDocs config (English)
├── mkdocs-fr.yml                  # MkDocs config (Français)
└── .readthedocs.yaml              # ReadTheDocs config
```

---

# ⚙️ CONFIGURATION & BUILD

## Configuration files

```
pyproject.toml                     # Project metadata, dependencies, tool config
pyrightconfig.json                 # Type checking (Pyright)
.ruff_cache/                       # Ruff linter cache
.coveragerc                        # Coverage configuration
.gitignore                         # Git ignore rules
.gitleaks.toml                     # Secret detection config
.markdownlint.json                 # Markdown linting
.pip-audit-ignore                  # Dependency audit ignore
```

## Build & Distribution

```
dist/                              # Built distributions (wheel, tarball)
old_dists/                         # Previous releases (v0.0.8 - v0.9.0.6)
MANIFEST.in                        # Include files in distribution
setup.py (generated)               # (via hatchling)
```

## API & Schema Files

```
openapi_schema.json                # OpenAPI 3.0 schema (auto-generated)
openapi_schema.backup.json         # Backup copy
openapi_schema_optimized.json      # Optimized version
tenxyte_api_collection.postman_collection.json  # Postman collection
tenxyte_api_environment.postman_environment.json  # Postman env
schemas_dump.json                  # Schema dump for debugging
login_schema.json                  # Login endpoint schema
```

## Reports & Analysis

```
documentation_validation_report.json # Doc validation results
openapi_validation_report.json       # OpenAPI validation results
schema_optimization_report.json      # Schema optimization results
.coverage                           # Coverage data file
htmlcov/                            # HTML coverage report
```

## CI/CD

```
.github/workflows/                 # GitHub Actions
├── ci.yml                         # Run tests, lint
├── publish.yml                    # Publish to PyPI
└── docs.yml                       # Build & deploy docs
```

---

# 📋 RÉSUMÉ DES FICHIERS PAR TYPE

## Par nombre de fichiers

| Catégorie | Fichiers | Type |
|-----------|----------|------|
| Tests | 187 | 🧪 |
| Code source | 147 | 📄 |
| Documentation | 59 | 📖 |
| Distribution | 40+ | 📦 |
| Configuration | 15+ | ⚙️ |
| **Total** | **~450** | |

## Par importance

### 🔴 Critique (doit être testé)
- `src/tenxyte/core/*.py` - Logique core
- `src/tenxyte/models/*.py` - Schéma DB
- `src/tenxyte/services/*.py` - Logique métier
- `src/tenxyte/conf/base.py` - Validation settings
- `tests/` - Suite de tests

### 🟡 Important (maintenance)
- `src/tenxyte/views/*.py` - Endpoints API
- `src/tenxyte/adapters/` - Framework integration
- `src/tenxyte/serializers/` - Validation données
- `docs/` - Documentation
- `pyproject.toml` - Dépendances

### 🟢 Utile (reference)
- `src/tenxyte/backends/` - Providers
- `src/tenxyte/templates/` - Email templates
- `src/tenxyte/static/` - Assets
- `src/tenxyte/management/` - CLI commands
- Examples, scripts, graphics

---

# 🎯 POINTS DE NAVIGATION

## Pour déboguer/modifier une feature

**2FA (TOTP):**
1. `src/tenxyte/core/totp_service.py` - Logique pure
2. `src/tenxyte/models/base.py` - Field `totp_secret`
3. `src/tenxyte/views/security_views.py` - Endpoints `/2fa/*`
4. `tests/core/test_totp_service.py` - Unit tests
5. `tests/integration/django/test_security_views.py` - Integration tests

**Passkeys (WebAuthn):**
1. `src/tenxyte/core/webauthn_service.py` - Logique
2. `src/tenxyte/models/webauthn.py` - Models
3. `src/tenxyte/views/webauthn_views.py` - Routes
4. `tests/core/test_webauthn_service.py`
5. `tests/integration/django/test_webauthn_views.py`

**RBAC (Roles & Permissions):**
1. `src/tenxyte/models/base.py` - User, Role, Permission
2. `src/tenxyte/views/rbac_views.py` - RBAC endpoints
3. `src/tenxyte/decorators.py` - Permission decorators
4. `tests/integration/django/test_rbac_*.py`

**Agent Tokens (AIRS):**
1. `src/tenxyte/models/agent.py` - AgentToken, PendingAction
2. `src/tenxyte/services/agent_service.py` - Service logic
3. `src/tenxyte/views/agent_views.py` - AIRS endpoints
4. `src/tenxyte/tasks/agent_tasks.py` - Circuit breaker jobs
5. `tests/integration/django/test_airs_*.py`

**Organizations (B2B):**
1. `src/tenxyte/models/organization.py` - Org model
2. `src/tenxyte/views/organization_views.py` - Org endpoints
3. `src/tenxyte/tenant_context.py` - Multi-tenant context
4. `tests/integration/django/test_org_*.py`

**OAuth Social Login:**
1. `src/tenxyte/conf/social.py` - OAuth config
2. `src/tenxyte/services/social_auth_service.py` - OAuth logic
3. `tests/integration/django/test_social_auth.py`

---

# ✅ CHECKLIST DE NAVIGATION

Pour un nouveau développeur:

- [ ] Lire `README.md` (overview)
- [ ] Lire `docs/quickstart.md` (setup)
- [ ] Lire `docs/architecture.md` (design)
- [ ] Explorer `src/tenxyte/core/` (comprendre logique pure)
- [ ] Explorer `src/tenxyte/models/` (schéma DB)
- [ ] Exécuter `pytest tests/core/` (tests purs)
- [ ] Exécuter `pytest tests/integration/django/` (tests d'intégration)
- [ ] Lire `src/tenxyte/views/` (endpoints)
- [ ] Lire `src/tenxyte/decorators.py` (permission checking)
- [ ] Consulter `docs/endpoints.md` (API reference)

---

**Index généré:** 2026-08-27  
**État:** ✅ Complet  
**Fichiers indexés:** ~450
