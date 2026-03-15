# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Task Service Documentation** — Complete guide for `TaskService` port and adapters (`docs/task_service.md`)
- **FastAPI Quickstart** — Step-by-step guide for FastAPI integration (`docs/fastapi_quickstart.md`)
- **Async Guide** — Comprehensive async/await patterns and best practices (`docs/async_guide.md`)
- **TaskService Custom Adapter Example** — Added to `docs/custom_adapters.md` for custom task queue implementations

### Fixed
- **Test Fixes for 100% Coverage** — Fixed failing async service tests:
  - `test_async_jwt_service.py`: `test_refresh_tokens_async_rotate_exception` now properly tests exception handling
  - `test_async_magic_link_service.py`: Removed duplicate test methods, fixed `test_ip_subnet_match` exception path
  - `test_async_totp_service.py`: Fixed `test_disable_2fa_async` to use actual encrypted secret, fixed `test_totp_storage_stubs` protocol testing
  - `test_task_service_extra.py`: Fixed incomplete `test_celery_task_service_enqueue_generic_wrap` test

## [0.9.3] - 2026-03-14

### Added
- **Framework-Agnostic Core** — Refactored business logic into a standalone `tenxyte.core` module, independent of Django.
- **Framework Adapters** — Introduced `tenxyte.adapters.django` containing Django-specific implementations (cache, email, middleware, settings provider).
- **Dependency Injection Ports** — Added `tenxyte.ports` defining abstract interfaces (repositories, providers) to allow custom ORM and framework integrations (e.g., FastAPI, Flask).
- **100% Test Coverage** — Achieved full coverage on core services and middleware components.
- Complete decoupling of essential services (`jwt_service`, `totp_service`, `magic_link_service`, `webauthn_service`, `email_service`, `cache_service`) from Django's specific dependencies.

### Changed
- Base middleware refactored into `tenxyte.core.middleware` with abstract core logic, while Django-specific execution moved to `tenxyte.adapters.django.middleware`.
- Shifted settings and environment variable management from direct Django imports to explicit `SettingsProvider` and `EnvProvider` interfaces.

### Fixed
- Various test suite fixes, including proper model mocking and exception simulation, using framework-agnostic injection strategies.

## [0.9.1.7] - 2026-02-21

### Added
- **Magic Links** — passwordless login via email (`TENXYTE_MAGIC_LINK_ENABLED`)
- **Social Login** — OAuth2 for Google, GitHub, Microsoft, Facebook (`TENXYTE_SOCIAL_PROVIDERS`)
- **Passkeys / WebAuthn (FIDO2)** — passwordless authentication via platform authenticators (`TENXYTE_WEBAUTHN_ENABLED`)
- **Breach Password Check** — HaveIBeenPwned k-anonymity API integration (`TENXYTE_BREACH_CHECK_ENABLED`)
- **Shortcut Secure Mode** — one-line security preset: `TENXYTE_SHORTCUT_SECURE_MODE = 'starter' | 'medium' | 'robust'`
- `tenxyte_cleanup` management command for purging expired tokens, OTPs, and logs
- `signals.py` with `post_delete` cleanup for user-related data
- `pytest-cov` configuration for code coverage measurement (893 tests, ≥80% coverage)

### Changed
- Unified configuration: merged `config.py` into `conf.py` with canonical `TENXYTE_JWT_*` naming
- Replaced `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`
- Replaced `print()` with `logger` in `google_auth_service.py`
- Replaced hardcoded `User` imports with `get_user_model()` for swappable model support
- Removed deprecated `default_app_config` from `__init__.py`

### Fixed
- Fixed `tenxyte_auth` imports to `tenxyte` in tests
- Fixed `Application` fixture to use `create_application()` (properly hashes secrets)
- OTP codes now stored as SHA-256 hashes instead of plaintext

## [0.0.8] - 2025-01-01

### Added
- Initial public release on PyPI
- JWT authentication with access and refresh tokens
- Token blacklisting and refresh token rotation
- Role-Based Access Control (RBAC) with hierarchical roles and permissions
- Two-Factor Authentication (TOTP) compatible with Google Authenticator
- Backup codes for 2FA recovery
- OTP verification via email and SMS
- Google OAuth integration
- Multi-application support with X-Access-Key / X-Access-Secret headers
- Rate limiting and progressive throttling
- Account lockout after failed login attempts
- Password validation and strength checking
- Password history to prevent reuse
- Session and device limit enforcement
- Audit logging for security-sensitive actions
- Extensible abstract models (User, Role, Permission, Application)
- SMS backends: Twilio, Console
- Email backends: Django, SendGrid, Console, Template
- Management command `tenxyte_seed` for default roles and permissions
- Support for SQLite, PostgreSQL, MySQL, and MongoDB
