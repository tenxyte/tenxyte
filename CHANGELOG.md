# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Added
- `tenxyte_cleanup` management command for purging expired tokens, OTPs, and logs
- `signals.py` with `post_delete` cleanup for user-related data
- `pytest-cov` configuration for code coverage measurement

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
