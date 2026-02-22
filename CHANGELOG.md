# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0.0] - 2026-02-21

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
