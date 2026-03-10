# Milestone: Make the package agnostic (Core Re-architecture)

- [x] **Issue 1: Extract Business Logic (Core) outside of Django**
  - [x] Sub-issue 1.1: Extract JWT token generation and validation into a pure Python module.
  - [x] Sub-issue 1.2: Extract validation and generation logic (TOTP, WebAuthn/Passkeys, Magic Links) so it depends only on simple variables (dictionaries, dataclasses).
  - [x] Sub-issue 1.3: Create a configuration system (`Settings` class) specific to the Core package.
  - [x] Sub-issue 1.4: **[Backward Compatibility]** Create an adapter that automatically reads `django.conf.settings` to feed the Core without any changes required on the user side.

- [x] **Issue 2: Create Abstraction Interfaces (Ports/Repositories) for the Database**
  - [x] Sub-issue 2.1: Define user management interfaces (`UserRepository`, `AbstractUser`).
  - [x] Sub-issue 2.2: Define interfaces for RBAC (Role-Based Access Control) and B2B organizations (`OrganizationRepository`, `RoleRepository`).
  - [x] Sub-issue 2.3: Define an interface for generating and writing Audit Logs without depending on the Django model.

- [x] **Issue 3: Isolate Django Implementation in an "Adapter" Module (Zero Breaking Changes)**
  - [x] Sub-issue 3.1: Transform current Views and Serializers into facades that call the Core, **without modifying Endpoints, Payloads, or JSON Responses**.
  - [x] Sub-issue 3.2: Implement the Repositories defined in Issue 2 by wrapping the current Django ORM (**no changes to models or DB**).
  - [x] Sub-issue 3.3: **[Backward Compatibility]** If views are moved, keep import pointers in old files (e.g., `tenxyte/views.py`) with a `DeprecationWarning` for v2.0.

- [x] **Issue 4: Re-architect Testing Suite (Sanctification)**
  - [x] Sub-issue 4.1: Set up pure unit tests for `tenxyte.core` (without `pytest-django`).
  - [ ] Sub-issue 4.2: Move current tests to a `tests/integration/django/` subfolder.
  - [ ] Sub-issue 4.3: **[Backward Compatibility]** Run the entire current Django test suite **without modifying behavior or assertions** to guarantee absolute zero regression.

- [ ] **Issue 5: [Proof of Concept] Develop a second adapter (FastAPI)**
  - [ ] Sub-issue 5.1: Create an abstract data model (e.g., Pydantic or SQLAlchemy) to represent users within the FastAPI context.
  - [ ] Sub-issue 5.2: Implement the Repositories for the FastAPI adapter.
  - [ ] Sub-issue 5.3: Expose 1 or 2 routes (e.g., Login, Magic Link) via FastAPI + Tenxyte Core.

- [ ] **Issue 6: Update Documentation (Readme & Docs)**
  - [ ] Sub-issue 6.1: Update `README.md` (change "Complete Django authentication" to "Framework-Agnostic Python Authentication").
  - [ ] Sub-issue 6.2: Add an Architecture section to the documentation explaining Core vs Adapters.
  - [ ] Sub-issue 6.3: Write a detailed Migration Guide for current Django projects to transition smoothly from v0.9 to v1.0.
  - [ ] Sub-issue 6.4: Document how to create custom adapters and extend the package.
  - [ ] Sub-issue 6.5: Create a troubleshooting guide for common migration issues.

- [x] **Issue 7: Abstract Cross-cutting Services (Critical)**
  - [x] Sub-issue 7.1: Create an `EmailService` port to abstract email sending and implement the Django adapter (`DjangoEmailService` using `django.core.mail`).
  - [x] Sub-issue 7.2: Create a `CacheService` port to abstract the cache system and implement the Django adapter (`DjangoCacheService` using `django.core.cache`).
  - [x] Sub-issue 7.3: Extract business logic from middlewares (`ApplicationAuthMiddleware`, audit logging) to the Core using defined ports. Django middlewares become wrappers.
  - [x] Sub-issue 7.4: Create an agnostic validation system (Pydantic) for the Core, independent of DRF serializers.
  - [x] Sub-issue 7.5: Abstract session and refresh token management independently of the framework.

- [ ] **Issue 8: Dependency Management and Modular Packaging**
  - [x] Sub-issue 8.1: Restructure `pyproject.toml` with hierarchical optional extras:
    - `[core]` - Minimal Core dependencies (PyJWT, bcrypt, pyotp, qrcode, Pydantic, requests, Pillow)
    - `[django]` - Django/DRF stack (django>=5.0, djangorestframework, django-cors-headers, drf-spectacular, django-cryptography) + Core
    - `[fastapi]` - FastAPI stack (fastapi>=0.100, uvicorn, python-multipart) + Core
  - [x] Sub-issue 8.2: Database adapter extras (work with both Django and FastAPI):
    - `[postgres]` - psycopg2-binary>=2.9
    - `[mysql]` - mysqlclient>=2.2  
    - `[mongodb]` - django-mongodb-backend>=5.0 (Django-specific)
  - [x] Sub-issue 8.3: Feature-specific extras (work with all adapters):
    - `[twilio]` - twilio>=9.0 (SMS support)
    - `[sendgrid]` - sendgrid>=6.10 (Email via SendGrid)
    - `[webauthn]` - webauthn>=2.0.0 (Passkeys/FIDO2)
  - [x] Sub-issue 8.4: Meta extras:
    - `[all]` - Includes django + all database adapters + all features
    - `[dev]` - pytest, pytest-django, pytest-cov, pytest-asyncio, black, ruff, mypy
  - [x] Sub-issue 8.5: **Backward Compatibility**: Ensure `pip install tenxyte` (no extras) defaults to `[django]` behavior for existing users
  - [x] Sub-issue 8.6: Separate requirements files: `requirements-core.txt`, `requirements-django.txt`, `requirements-fastapi.txt`
  - [x] Sub-issue 8.7: Update `MANIFEST.in` to correctly include new modules and sub-packages
  - [x] Sub-issue 8.8: Validate all extra combinations work: `pip install tenxyte[django,postgres,webauthn]`, `pip install tenxyte[fastapi,postgres]`, etc.

- [ ] **Issue 9: Async Support and Background Task Abstraction**
  - [ ] Sub-issue 9.1: Add async/await support to Core services for FastAPI compatibility.
  - [ ] Sub-issue 9.2: Create `TaskService` port for background job abstraction.
  - [ ] Sub-issue 9.3: Implement Django adapter (Celery/RQ integration).
  - [ ] Sub-issue 9.4: Implement FastAPI adapter (asyncio background tasks).
