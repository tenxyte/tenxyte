# Tenxyte Architecture: Core & Adapters

Tenxyte is built on a **Framework-Agnostic Core** architecture, specifically designed using the Hexagonal Architecture (also known as Ports and Adapters) pattern. This ensures that the core authentication and security logic is decoupled from any specific web framework, database, or third-party service.

## The Core (`tenxyte.core`)
The Core contains all the business logic of the package. It does not know whether you are using Django or FastAPI, nor does it care if you are using PostgreSQL, MongoDB, Twilio, or SendGrid.

It strictly handles:
- Token generation, signing, and verification (JWT).
- Validation of RBAC rules, passwords, OTPs, and Passkeys.
- Definition of expected interfaces ("Ports") for databases, caches, email sending, etc.

By depending only on standard Python libraries (and minimal tools like Pydantic), the Core remains extremely stable and highly testable.

## The Ports (`tenxyte.ports`)
Ports are abstract base classes or protocols that define how the Core expects to interact with the outside world. Examples include:
- `UserRepository`: Interface for finding/creating users.
- `CacheService`: Interface for setting/getting cache values (used for rate-limiting, blacklisting, etc.).
- `EmailService`: Interface for dispatching emails (e.g. magic links).

## The Adapters (`tenxyte.adapters`)
Adapters are the implementations of the Ports tailored to specific technologies or frameworks.

### Web Framework Adapters
Tenxyte provides pre-built "Primary Adapters" (Driving Adapters) that wrap the core logic and expose HTTP endpoints:
- **Django Adapter** (`tenxyte.adapters.django`): Hooks into Django's views, signals, ORM, and `django.core.cache`. It preserves full backward compatibility for users of previous Tenxyte versions.
- **FastAPI Adapter** (`tenxyte.adapters.fastapi`): Hooks into FastAPI routers and dependency injection.

### Infrastructure Adapters
These "Secondary Adapters" (Driven Adapters) connect to external infrastructure:
- **Databases**: Supported via the specific ORM used by your web framework (e.g., Django ORM integrations).
- **Communication**: Implementations such as `DjangoEmailService` (using `django.core.mail`), `ConsoleEmailService` (for development), or custom adapters you write yourself.

## Benefits
1. **Framework Portability**: Switch from Django to FastAPI (or others in the future) while using the exact same authentication business logic.
2. **Zero Breaking Changes**: For existing Django users, the Django Adapter maintains exactly the same endpoints, models, and settings as before.
3. **Easy Extensibility**: You can easily swap out the cache service or email service by writing a single small adapter class that implements the respective port, without modifying any internal authentication code.
