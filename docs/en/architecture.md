# Tenxyte Architecture: Core & Adapters

Tenxyte is built on a **Framework-Agnostic Core** architecture, specifically designed using the Hexagonal Architecture (also known as Ports and Adapters) pattern. This ensures that the core authentication and security logic is decoupled from any specific web framework, database, or third-party service.

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     HTTP / WebSocket                        │
├─────────────────────────────────────────────────────────────┤
│  views/          │  middleware/       │  serializers/       │
│  (endpoints)     │  (AIRS, PII,       │  (DRF validation)   │
│                  │   tenant, auth)    │                     │
├─────────────────────────────────────────────────────────────┤
│  services/       │  decorators.py     │  conf/              │
│  (AgentToken,    │  (@require_perm,   │  (auth, jwt, airs,  │
│   business logic)│   @require_agent)  │   org settings)     │
├──────────────────┴───────────────────┴──────────────────────┤
│                     tenxyte.core                            │
│  jwt_service · totp_service · webauthn_service              │
│  magic_link_service · cache_service · email_service         │
│  session_service · schemas · settings                       │
├─────────────────────────────────────────────────────────────┤
│                     tenxyte.ports                           │
│  UserRepository · OrganizationRepository · RoleRepository   │
│  AuditLogRepository · EmailService · CacheService           │
├─────────────────────────────────────────────────────────────┤
│                     tenxyte.adapters                        │
│  adapters/django/  │  adapters/fastapi/                     │
│  (ORM, cache,      │  (routers, models,                     │
│   email, TOTP,     │   repositories)                        │
│   WebAuthn)        │                                        │
├─────────────────────────────────────────────────────────────┤
│  Django ORM / PostgreSQL │ django.core.cache │ SMTP / SES   │
└─────────────────────────────────────────────────────────────┘
```

---

## The Core (`tenxyte.core`)

The Core contains all the business logic of the package. It does not know whether you are using Django or FastAPI, nor does it care if you are using PostgreSQL, MongoDB, Twilio, or SendGrid.

It strictly handles:
- Token generation, signing, and verification (`JWTService`).
- TOTP-based 2FA setup, verification, and backup codes (`TOTPService`).
- WebAuthn/Passkey registration and authentication (`WebAuthnService`).
- Passwordless login via magic links (`MagicLinkService`).
- Cache abstractions and in-memory fallbacks (`CacheService`, `InMemoryCacheService`).
- Email dispatch abstractions (`EmailService`, `ConsoleEmailService`).
- Session lifecycle management (`SessionService`).
- Pydantic schemas for user, organization, and token data (`schemas`).

By depending only on standard Python libraries (and minimal tools like Pydantic), the Core remains extremely stable and highly testable.

---

## The Ports (`tenxyte.ports`)

Ports are abstract base classes or protocols that define how the Core expects to interact with the outside world.

### Repository Ports (ABC)

| Port | Responsibility |
|---|---|
| `UserRepository` | CRUD operations on users, MFA secrets, email verification |
| `OrganizationRepository` | Organization CRUD, member management, hierarchy traversal |
| `RoleRepository` | Role CRUD, user-role assignments, org-scoped roles |
| `AuditLogRepository` | Audit log creation, querying by user/org/resource, cleanup |

### Service Ports (Protocol)

| Port | Responsibility |
|---|---|
| `CacheService` | Get/set/delete cache values, token blacklist management |
| `EmailService` | Send emails, magic links, and 2FA codes |

---

## The Adapters (`tenxyte.adapters`)

Adapters are the implementations of the Ports tailored to specific technologies or frameworks.

### Web Framework Adapters

Tenxyte provides pre-built "Primary Adapters" (Driving Adapters) that wrap the core logic and expose HTTP endpoints:

| Adapter | Module | Components |
|---|---|---|
| **Django** | `tenxyte.adapters.django` | ORM repositories, `DjangoCacheService`, `DjangoEmailService`, TOTP/WebAuthn storage, settings provider, middleware |
| **FastAPI** | `tenxyte.adapters.fastapi` | SQLAlchemy models, repositories, routers, task service |

### Infrastructure Adapters

These "Secondary Adapters" (Driven Adapters) connect to external infrastructure:
- **Databases**: Supported via the specific ORM used by your web framework (e.g., Django ORM integrations).
- **Communication**: Implementations such as `DjangoEmailService` (using `django.core.mail`), `ConsoleEmailService` (for development), or custom adapters you write yourself.

---

## Supporting Layers

Beyond the hexagonal core, Tenxyte includes several supporting layers:

| Layer | Path | Purpose |
|---|---|---|
| **Configuration** | `tenxyte.conf` | Modular settings mixins (`auth`, `jwt`, `airs`, `org`) with `_get()` fallback to Django settings |
| **Services** | `tenxyte.services` | Higher-level business services (e.g., `AgentTokenService` for AIRS token lifecycle) |
| **Middleware** | `tenxyte.middleware` | Request processing: AIRS circuit breaker, PII redaction, tenant context, application auth |
| **Tasks** | `tenxyte.tasks` | Periodic maintenance: token cleanup, blacklist purge, expired deletion processing |
| **Serializers** | `tenxyte.serializers` | DRF serializer layer for request validation and response formatting |
| **Decorators** | `tenxyte.decorators` | Permission guards (`@require_permission`), agent clearance (`@require_agent_clearance`) |

---

## Benefits

1. **Framework Portability**: Switch from Django to FastAPI (or others in the future) while using the exact same authentication business logic.
2. **Zero Breaking Changes**: For existing Django users, the Django Adapter maintains exactly the same endpoints, models, and settings as before.
3. **Easy Extensibility**: You can easily swap out the cache service or email service by writing a single small adapter class that implements the respective port, without modifying any internal authentication code.
4. **Testability**: The Core can be tested in complete isolation from any web framework using in-memory implementations (`InMemoryCacheService`, `ConsoleEmailService`).
