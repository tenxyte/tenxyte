# Implementation Plan: Make the package agnostic (Core Re-architecture)

> [!IMPORTANT]
> **Major Constraint: Zero Breaking Changes**
> This entire refactoring must guarantee **100% backward compatibility** for current Tenxyte users working with Django.
> - **API Endpoints (DRF)**: URLs, request payloads, and JSON responses must remain strictly identical.
> - **Configuration**: Variables in `settings.py` (e.g., `TENXYTE_JWT_SECRET`, etc.) must continue to work without any modifications on the user's end.
> - **Models and DB**: No database migrations should be required for users upgrading the package.
> - **Features**: No regressions are tolerated on existing features (JWT, 2FA, RBAC, Passkeys).

## Phase 1: Preparation and Architecture (Week 1)
The goal of this phase is to prepare the groundwork for refactoring by ensuring the project structure supports the new agnostic approach.
*   **Create the new folder structure**: `src/tenxyte/core/`, `src/tenxyte/adapters/django/`, `src/tenxyte/adapters/fastapi/` and `src/tenxyte/ports/`.
*   **Configuration System**: Create an agnostic `Settings` class for the Core. **Crucial:** Create an adapter that automatically reads variables from `django.conf.settings` to feed the Core, ensuring no changes are needed for current users.
*   **Interface Definition (Ports)**: Create Abstract Base Classes (ABC) or Protocols for `UserRepository`, `OrganizationRepository`, `AuditLogRepository`, etc. (Issue 2).
*   **Dependency Management**: Restructure `pyproject.toml` with optional extras (Issue 8):
    - `[core]` - Minimal Core dependencies (PyJWT, bcrypt, pyotp, Pydantic)
    - `[django]` - Django/DRF stack + Core
    - `[fastapi]` - FastAPI stack + Core
    - `[postgres]`, `[mysql]`, `[mongodb]` - Database adapters (work with both Django and FastAPI)
    - `[twilio]`, `[sendgrid]`, `[webauthn]` - Feature-specific extras (work with all adapters)
    - `[all]` - All adapters and features combined
    - **Backward Compatibility**: Default install (`pip install tenxyte`) continues to include Django stack

## Phase 1.5: Cross-cutting Services Abstraction (Week 1-2)
This critical phase ensures all system services are abstracted before Core extraction.
*   **EmailService/NotificationService**: Create an `EmailService` port to abstract email sending (Magic Links, 2FA codes, notifications). Implement the Django adapter using `django.core.mail` (Issue 7.1).
*   **CacheService**: Create a `CacheService` port to abstract the caching system (token blacklist, rate limiting). Implement the Django adapter using `django.core.cache` (Issue 7.2).
*   **Validation System**: Integrate Pydantic in the Core for data validation, independent of DRF serializers (Issue 7.4).
*   **Middleware Abstraction**: Identify and plan the extraction of middlewares (`ApplicationAuthMiddleware`, audit, etc.) to the Core (Issue 7.3).

## Phase 2: Core Extraction (Weeks 2-3)
The main body of work. Move all business logic to the new `core/` folder without breaking anything.
*   **Authentication and JWT**: Move token generation, signing, and validation to `core/jwt/`. Include blacklist management via `CacheService`.
*   **Security (2FA, WebAuthn, Magic Links)**: Migrate validation logic to take simple Python parameters. Use `EmailService` for sending codes/links.
*   **Session Management**: Abstract session and refresh token management independently of the framework.
*   **Core Middlewares**: Extract business logic from middlewares (ApplicationAuth, audit logging) to the Core, using defined ports.
*   **Core Unit Tests**: Create pure tests (using `pytest` without Django plugins) for all functions in `core/`. Use mocks for ports (Issue 4).

## Phase 3: Django Adapter Creation (Weeks 3-4)
This is where we guarantee "Zero Breaking Changes". The current entry points (Views) will simply become facades that call the new Core.
*   **Django Repositories Implementation**: Create classes (e.g., `DjangoUserRepository`) that wrap the current Django ORM. Existing Django data models remain intact.
*   **Django Services Implementation**: Create `DjangoEmailService` (using `django.core.mail`), `DjangoCacheService` (using `django.core.cache`), etc.
*   **"Transparent" Views and Serializers Overhaul**: The external interface of the Views (endpoints, input/output serializers) does not change. Only their internal workings are modified to instantiate the Tenxyte Core. DRF serializers remain for HTTP input/output validation but use Pydantic internally.
*   **Django Middlewares**: Transform current middlewares into wrappers calling Core logic. Ensure `ApplicationAuthMiddleware` continues to be added automatically via `tenxyte.setup()`.
*   **Permissions and Decorators**: Create agnostic equivalents of Django decorators (`@permission_required`, etc.) that work with the RBAC Core.
*   **Test Validation**: Run the entirely of the current Django test suite. **No existing tests should be modified or deleted**; they must all pass to prove no regressions. (Issue 4).
*   **Graceful Deprecation**: If deep imports (e.g., `from tenxyte.views import LoginView`) are moved to `tenxyte.adapters.django.views`, keep backward compatibility pointers (aliases) in the old files with `DeprecationWarning`s for v2.0 (Issue 3.3).

## Phase 4: FastAPI Proof of Concept & Documentation (Week 5)
Prove that the package is truly agnostic.
*   **FastAPI Adapter**: Create a `tenxyte.adapters.fastapi` module with a few routes (Login, Register, Magic Link) to demonstrate flexibility. Implement FastAPI repositories (SQLAlchemy or other ORM) (Issue 5).
*   **FastAPI Services**: Implement `FastAPIEmailService`, `FastAPICacheService` (e.g., Redis) to show full portability.
*   **Documentation Update**: 
    - Update `README.md`: change "Complete Django authentication" to "Framework-Agnostic Python Authentication" (Issue 6.1).
    - Add an Architecture section explaining Core vs Adapters (Issue 6.2).
    - Write a detailed Migration Guide for existing Django users (Issue 6.3).
    - Document how to create custom adapters and extend the package (Issue 6.4).
    - Create a troubleshooting guide for common migration issues (Issue 6.5).
*   **OpenAPI/Swagger**: Ensure automatic OpenAPI schema generation still works for both Django (DRF) and FastAPI.
*   **Release Candidate**: Publish a version (e.g., `1.0.0-rc1`) on PyPI for final validation.

## Phase 5: Async Support and Background Tasks (Week 6)
Add async/await capabilities and background task processing for full FastAPI compatibility and modern Python standards.
*   **Core Async Support**: Refactor Core services to support async/await patterns where beneficial (e.g., email sending, cache operations) while maintaining backward compatibility with synchronous Django code.
*   **TaskService Port**: Create a `TaskService` port to abstract background job execution (Issue 9.2).
*   **Django Task Adapter**: Implement `DjangoTaskService` using Celery or RQ for background job processing (Issue 9.3).
*   **FastAPI Task Adapter**: Implement `FastAPITaskService` using asyncio background tasks or integration with task queues (Issue 9.4).
*   **Async-Compatible Testing**: Ensure all async code paths are tested with both sync and async test runners.
