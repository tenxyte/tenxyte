# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Passwordless Phone Login (OTP)** — Users can now log in with only a phone number and a one-time SMS code, with no password required.
  - `POST /login/otp/request/` — Request a login OTP. If `TENXYTE_OTP_LOGIN_AUTO_REGISTER=True` (default) and the phone number has no account, a *Passwordless Account* is created automatically.
  - `POST /login/otp/verify/` — Verify the OTP and receive JWT tokens. Applies all the same security checks as `/login/phone/` (account status, 2FA gate, device/session limits). Response shape is identical to `/login/phone/`.
  - `POST /password/set-initial/` — Passwordless accounts can voluntarily set a first password via a fresh OTP as proof of phone ownership. After success, both OTP and password-based login remain available.
  - New `has_usable_password` field on the `User` model (default `True`). Set to `False` for auto-registered passwordless accounts; reset to `True` by `Set_Initial_Password_Operation`.
  - Three new settings: `TENXYTE_OTP_LOGIN_ENABLED` (default `False`), `TENXYTE_OTP_LOGIN_AUTO_REGISTER` (default `True`), `TENXYTE_OTP_LOGIN_VALIDITY_MINUTES` (default `10`).
  - Dedicated throttle classes `LoginOTPRequestThrottle` (5/min) and `LoginOTPRequestDailyThrottle` (20/day), independent of `/register/`.
  - New serializers: `LoginOTPRequestSerializer`, `LoginOTPVerifySerializer`, `SetInitialPasswordSerializer`, `ReauthSerializer`.
  - `ReauthService` — centralised re-authentication service for sensitive actions. All sensitive endpoints (`/password/change/`, `/2fa/disable/`, account deletion, data export) now accept a valid login OTP (`otp_code`) as an alternative to the current password.
  - Migration `0017_login_otp_type_and_passwordless_account`: additive — adds `User.has_usable_password` field and `"login"` choice to `OTPCode.otp_type`. No existing field or constraint is removed.

### Changed
- **`/password/change/`** — Passwordless accounts (`has_usable_password=False`) are now rejected with `400 PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD` and directed to the new `/password/set-initial/` endpoint.
- **`/2fa/disable/`, account deletion endpoints, data export endpoint** — Now accept `otp_code` as an alternative to `current_password` for re-authentication, enabling passwordless users to perform sensitive actions without a password.

## [0.9.6.4.1]

### Fixed
- **Phone-Only Registration** — Resolved bug preventing user registration with phone number only. The `UserManager.create_user()` now accepts either email OR phone (with country code), aligning with `RegisterSerializer` validation. Added unique constraint on phone numbers for non-deleted users to prevent duplicates. Migration `0015_add_unique_phone_constraint` includes the database constraint.

### Changed
- **UserManager.create_user()** — Modified to accept `None` for email if valid phone number is provided (`phone_country_code` + `phone_number`). Error message updated to: "L'email ou le numéro de téléphone est requis".
- **User Model Constraints** — Added `UniqueConstraint` on `(phone_country_code, phone_number)` with condition `phone_number__isnull=False & is_deleted=False`.

## [0.9.6] - 2025-01-XX

### Fixed
- **Super Admin 2FA Bootstrap** — Resolved circular dependency preventing super admins from logging in without 2FA. Introduced restricted-scope JWT tokens (`scope: "2fa_setup_only"`) with 15-minute expiration that permit access exclusively to `/2fa/setup/` and `/2fa/confirm/` endpoints. After successful 2FA activation, the system automatically issues a full-scope token and invalidates the bootstrap token, enabling seamless first-time admin authentication flow.

### Security
- **Token Scope Enforcement** — Added `allowed_scopes` parameter to `@require_jwt` decorator, enforcing strict scope validation. Restricted tokens attempting to access unauthorized endpoints now receive `403 INSUFFICIENT_SCOPE` error.

## [0.9.4] - 2026-03-26

### Security
- **JWT Hardening** — Implemented key rotation via `JWT_PREVIOUS_SECRET_KEY` and dynamic `iss`/`aud` claims.
- **HttpOnly Cookies** — Added secure HttpOnly cookie transport for refresh tokens (`REFRESH_TOKEN_COOKIE_ENABLED`).
- **OAuth Hardening** — Implemented PKCE (`code_verifier`), strict `redirect_uri` application whitelist, and configurable social scopes.
- **Lockout Policy** — Added exponential lockout scaling (base × 2^(n-1)) to mitigate brute-force attacks (`LOCKOUT_ESCALATION_ENABLED`).
- **NIST Password Policy** — Enforced 15-character minimum for accounts without MFA (`PASSWORD_MIN_LENGTH_NO_MFA`).

### Added
- **Task Service Documentation** — Complete guide for `TaskService` port and adapters (`docs/task_service.md`)
- **FastAPI Quickstart** — Step-by-step guide for FastAPI integration (`docs/fastapi_quickstart.md`)
- **Async Guide** — Comprehensive async/await patterns and best practices (`docs/async_guide.md`)
- **TaskService Custom Adapter Example** — Added to `docs/custom_adapters.md` for custom task queue implementations
- Documentation updates mirroring all security improvements in `endpoints.md`, `schemas.md`, `settings.md`, and `security.md` (EN/FR).
- **JS/TS SDK Documentation** — Added integration guide and API reference for the official JavaScript/TypeScript client.

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
