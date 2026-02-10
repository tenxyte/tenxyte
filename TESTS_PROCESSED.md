# 🧪 Tests & Validation Checklist (Based on Analysis)

This document tracks the validation of `vannios-auth` (tenxyte) features, architecture, and documentation requirements derived from `ANALYSE_BY_OPUS_1.md`.

## 🏗️ 1. Architecture & Design

### Service Layer Isolation
- [ ] **Verify Service/View Separation**: Ensure `views.py` only handles Request/Response and calls `services/`.
- [ ] **Service Independence**: Verify `services/` contains purely business logic and is not coupled to Django Views.

### Pluggable Backends (Strategy Pattern)
- [ ] **Beckend Interface**: Verify `backends/` structure (`twilio_backend.py`, `sendgrid_backend.py`, `console_backend.py`).
- [ ] **Extensibility**: Create a dummy backend (e.g., `logging_backend.py`) and configure it to ensure it works without modifying core code.
- [ ] **Configuration**: Test switching backends via settings.

### Configuration & Defaults
- [ ] **Secure Defaults**: Verify `conf.py` has secure defaults (e.g., `TENXYTE_JWT_ALGORITHM = 'HS256'`).
- [ ] **Override Test**: parameters in `settings.py` and verify they are picked up.

### Multi-Database Support
- [x] **Schema Adaptation**: Verify models work with SQLite. ✅ 50/50 tests passed (in-memory SQLite)
- [x] **PostgreSQL**: Verify models work with PostgreSQL. ✅ 50/50 tests passed (PostgreSQL 16.11)
- [x] **MySQL/MariaDB**: Verify models work with MySQL. ✅ 50/50 tests passed (MySQL 8.4.8)
- [x] **MongoDB**: Verify compatibility. ✅ 50/50 tests passed (MongoDB 8.2.2, django-mongodb-backend 6.0.2). M2M `remove()` skipped (known limitation: through tables lack integer PKs).

---

## 🔐 2. Authentication Flow & Security

### Login & 2FA
- [ ] **Standard Login**: Test `auth_service.authenticate` with valid credentials.
- [ ] **2FA Trigger**: Test login when 2FA is required -> should return "2FA required" response/state.
- [ ] **OTP Generation**: Verify `otp_service` generates valid codes using the active backend.
- [ ] **OTP Verification**: Verify `totp_service.verify` validates the code correctly.

### Token Management (Crucial)
- [ ] **JWT Generation**: Verify Access Token contains correct claims (user_id, exp, etc.).
- [ ] **Refresh Token Rotation**:
    - [ ] **Initial Flow**: Login -> Receive Access Token + Refresh Token (RT1).
    - [ ] **Refresh Flow**: Use RT1 to get Access Token 2 + Refresh Token 2 (RT2).
    - [ ] **Invalidation**: Verify RT1 is now invalid/blacklisted.
    - [ ] **Reuse Detection**: Try to reuse RT1 -> Should trigger security alert/lock account?
- [ ] **Token Blacklisting**:
    - [ ] **Storage**: Configure blacklist storage (Redis vs DB).
    - [ ] **Logout**: Verify Logout functionality adds tokens to blacklist.
    - [ ] **Expiration**: Verify blacklisted tokens are cleaned up or handled efficiently.

### Audit & Data Protection
- [ ] **Sensitive Data**: trigger a password change and check `AuditLog`.
    - [ ] **Check Result**: Ensure the *actual password* is NOT logged.
- [ ] **PII**: Check if other sensitive fields (phone, email) are handled according to privacy settings.

---

## ⚙️ 3. Extensibility & Maintenance

### Middleware vs Authentication
- [ ] **Responsibility Check**:
    - [ ] **Middleware**: Verify it sets global context (App ID, Request context).
    - [ ] **Authentication**: Verify it strictly handles Credential Validation (JWT signature).
- [ ] **Redundancy**: detailed review to ensure they don't duplicate logic.

### Signals & Logging
- [x] **Event Logging**: Locate where events (Login, PasswordChange) are logged.
    - [x] **Option A (Services)**: Is it explicit? ✅ Events logged explicitly in `AuthService` and other services.
    - [x] **Option B (Signals)**: Is `signals.py` present and connected? ✅ `signals.py` now exists with `post_save`/`post_delete` handlers.
- [ ] **Decoupling**: Ensure logic is not hardcoded inside services if it should be an event.

### Migrations & Swappable Models
- [ ] **Custom User Model**: Create a new Django app with a custom User model.
    - [ ] **Configuration**: Point `vannios-auth` to use this model.
    - [ ] **Migrations**: Run `makemigrations` and `migrate`. Verify no conflicts.
- [ ] **Swappable Role/Permission**: Test swapping these models if supported.

---

## 📚 4. Documentation & DevEx (The "Hiring Material" Gap)

### Documentation Artifacts
- [ ] **README.md**:
    - [ ] Architecture Overview Diagram.
    - [ ] Core Concepts explanation.
    - [ ] Critical Flows (Login/2FA, Refresh Rotation).
- [ ] **docs/ARCHITECTURE.md**: Design decisions.
- [ ] **docs/SECURITY.md**: Threats, mitigations, OWASP mapping.
- [ ] **docs/INTEGRATION_GUIDE.md**: Step-by-step integration.
- [ ] **docs/TROUBLESHOOTING.md**: Common issues.

### Example Application
- [ ] **Create `examples/`**:
    - [ ] **Simple App**: `task_management_api` (Models, Views, Settings).
    - [ ] **Run Guide**: `README.md` inside example with install/run steps.

### Test Visibility
- [x] **Test Structure**:
    - [x] `tests/unit/` (Services) ✅ 6 test files: models, jwt, otp, totp, validators, backends
    - [x] `tests/integration/` (Flows) ✅ test_views.py — full auth flow integration tests
    - [x] `tests/security/` (Brute-force, Tampering) ✅ 30 tests: JWT tampering, brute-force, injection, cross-app, unauthenticated access
    - [x] `tests/multidb/` ✅ 50 tests × 4 backends (SQLite, PostgreSQL, MySQL, MongoDB)
- [x] **Coverage**: 68.51% (seuil minimum 60% atteint). Objectif 80% reste à atteindre.

---

## 📊 5. Performance & Benchmarks
- [ ] **Login Latency**: Measure time for `authenticate`.
- [ ] **2FA Latency**: Measure time for OTP generation/sending.
- [ ] **Throughput**: Load test (100/1000 req/s) if possible for Token Validation.
- [ ] **bcrypt Cost**: Measure password hashing time. Ensure bcrypt rounds are tuned (default 12 is ~250ms).
- [ ] **Token Decode**: Benchmark `JWTService.decode_token()` with and without blacklist check (DB query overhead).
- [ ] **Rate Limiter**: Stress test `ProgressiveLoginThrottle` under concurrent requests.

---

## 🐛 6. Bugs & Issues Found (From Code Analysis)

### Critical

- [x] **`conftest.py` imports from `tenxyte_auth`**: `tests/conftest.py` lines 10, 117 import from `tenxyte_auth.models` and `tenxyte_auth.services`, but the package is named `tenxyte`. Tests will fail with `ModuleNotFoundError`.
    - **Fix**: Replace all `tenxyte_auth` imports with `tenxyte` in `conftest.py`. ✅ Also fixed in `test_views.py` and `test_otp.py`.
- [x] **`Application` fixture bypasses `create_application()`**: `conftest.py` line 30 uses `Application.objects.create()` which does NOT hash the `access_secret`. The `_plain_secret` saved at line 35 references the raw `access_secret` field, but it was never hashed. The `verify_secret()` method expects a bcrypt-hashed secret.
    - **Fix**: Use `Application.create_application()` which properly hashes the secret and returns it. ✅
- [x] **Hardcoded `User` import in views/authentication**: `views.py` line 18 and `authentication.py` import `User` directly from `models.py` instead of using `get_user_model()`. This **breaks the swappable model pattern** — if a project uses a custom User model, these views will query the wrong table.
    - **Fix**: Replace `from .models import User` with `User = get_user_model()` or `from .models import get_user_model`. ✅ Fixed in `views.py`, `authentication.py`, `decorators.py`, `serializers.py`, `google_auth_service.py`.

### Medium

- [x] **`datetime.utcnow()` deprecated**: `jwt_service.py` lines 33, 35, 152, 154 use `datetime.utcnow()` which is deprecated since Python 3.12. Will emit `DeprecationWarning` and may break in future Python versions.
    - **Fix**: Use `datetime.now(datetime.timezone.utc)` instead. ✅ Also replaced `utcfromtimestamp()` with `fromtimestamp(tz=timezone.utc)`.
- [x] **`default_app_config` deprecated**: `__init__.py` sets `default_app_config = 'tenxyte.apps.TenxyteConfig'`, deprecated since Django 3.2 and removed in Django 5.1+.
    - **Fix**: Remove this line. Django auto-discovers `AppConfig` from `apps.py`. ✅
- [x] **`signals` module missing**: `apps.py` line 19 tries `from . import signals` wrapped in `try/except ImportError`.
    - **Fix**: `signals.py` created with `post_save`/`post_delete` handlers for audit logging. ✅
- [x] **`print()` in `google_auth_service.py`**: Lines 49, 69, 94 use `print()` for error logging instead of the `logger`. Errors will be invisible in production with proper logging configs.
    - **Fix**: Replace `print(...)` with `logger.error(...)`. ✅ Added `import logging` and `logger = logging.getLogger(__name__)`.

### Low

- [ ] **OTP codes stored in plaintext**: `OTPCode.code` stores the generated code in cleartext in the database. If the DB is compromised, all active OTPs are exposed.
    - **Recommendation**: Store hashed OTP codes (SHA-256) and compare via hash.
- [x] **No automatic cleanup tasks**: `BlacklistedToken.cleanup_expired()` and expired `OTPCode`/`RefreshToken` records are never cleaned up automatically.
    - **Fix**: Management command `tenxyte_cleanup` created in `management/commands/tenxyte_cleanup.py`. ✅
- [x] **`CHANGELOG.md` missing**: Referenced in `MANIFEST.in` and `pyproject.toml` but does not exist in the project.
    - **Fix**: `CHANGELOG.md` created. ✅
- [ ] **`MIGRATION_GUIDE.md` missing**: Referenced in `MANIFEST.in` but does not exist.

---

## 🔑 7. RBAC (Role-Based Access Control)

### Permission System
- [ ] **Permission CRUD**: Test create/read/update/delete via `PermissionListView` and `PermissionDetailView`.
- [ ] **Permission Enforcement**: Verify `@require_permission('users.view')` actually blocks access for users without the permission.
- [ ] **Cascading Permissions**: Assign permission to role, role to user -> user should have permission via `has_permission()`.
- [ ] **Permission Removal Cascade**: Remove permission from role -> verify user loses access immediately.

### Role System
- [ ] **Role CRUD**: Test create/read/update/delete via `RoleListView` and `RoleDetailView`.
- [ ] **Default Role Assignment**: Register new user -> verify `is_default=True` role (`viewer`) is auto-assigned.
- [ ] **Multi-Role**: Assign 2+ roles to user -> verify `get_all_permissions()` returns the union of all permissions.
- [ ] **Role Removal**: Remove role from user -> verify permissions are recalculated.

### RBAC Decorators
- [ ] **`@require_role('admin')`**: Test access granted/denied based on role.
- [ ] **`@require_any_role(['admin', 'editor'])`**: Test OR logic.
- [ ] **`@require_all_roles(['admin', 'editor'])`**: Test AND logic.
- [ ] **`@require_permission('content.edit')`**: Test single permission check.
- [ ] **`@require_any_permission([...])`**: Test OR logic.
- [ ] **`@require_all_permissions([...])`**: Test AND logic.

### Seed Command
- [ ] **`python manage.py tenxyte_seed`**: Verify creates 28 permissions + 4 roles.
- [ ] **`--force` flag**: Verify deletes and recreates.
- [ ] **`--no-permissions` / `--no-roles`**: Verify selective creation.
- [ ] **`super_admin` role**: Verify receives `__all__` permissions (all 28).
- [ ] **Idempotency**: Run seed twice -> no duplicates, only updates.

---

## 🚦 8. Rate Limiting & Throttling

### IP-Based Throttles
- [ ] **`LoginThrottle`**: Verify 5 requests/min limit per IP on `/login/email/`.
- [ ] **`LoginHourlyThrottle`**: Verify 20 requests/hour limit.
- [ ] **`RegisterThrottle`**: Verify 3 requests/hour limit on `/register/`.
- [ ] **`PasswordResetThrottle`**: Verify 3 requests/hour on `/password/reset/request/`.
- [ ] **`OTPRequestThrottle`**: Verify 5 requests/hour on `/otp/request/`.
- [ ] **`OTPVerifyThrottle`**: Verify 5 requests/10min on OTP verify endpoints.

### Progressive Login Throttle
- [ ] **Exponential Backoff**: Verify lockout increases: 1min -> 2min -> 5min -> 15min -> 60min.
- [ ] **Cache-Based**: Verify uses Django cache, not DB.
- [ ] **IP Reset**: Verify successful login resets the progressive counter for that IP.

### Global Toggle
- [ ] **`TENXYTE_RATE_LIMITING_ENABLED = False`**: Verify all throttles are bypassed.
- [ ] **Per-endpoint Override**: Verify individual throttle classes can be overridden in settings.

---

## 🔒 9. Password Management

### Password Validator
- [ ] **Min/Max Length**: Test passwords below min (default 8) and above max (default 128).
- [ ] **Complexity Rules**: Test `REQUIRE_UPPERCASE`, `REQUIRE_LOWERCASE`, `REQUIRE_DIGIT`, `REQUIRE_SPECIAL` toggles.
- [ ] **Common Passwords**: Test "password123", "qwerty", "123456" are rejected.
- [ ] **Sequence Detection**: Test "abcdef", "123456", "qwerty" patterns.
- [ ] **Repetition Check**: Test "aaaa" (3+ consecutive identical chars) is rejected.
- [ ] **Personal Info Check**: Test password containing user's email or username is rejected.
- [ ] **Scoring**: Verify scoring 0-100 and strength labels (weak/fair/good/strong/excellent).

### Password History
- [ ] **`TENXYTE_PASSWORD_HISTORY_ENABLED = True`**: Change password 5 times, then try to reuse password #1 -> should be rejected.
- [ ] **History Count**: Verify `TENXYTE_PASSWORD_HISTORY_COUNT` (default 5) is respected.
- [ ] **bcrypt Comparison**: Verify `PasswordHistory.is_password_used()` correctly compares against bcrypt hashes.

### Password Reset Flow
- [ ] **Request Reset**: Send OTP via email.
- [ ] **Confirm Reset**: Verify OTP + new password -> password changed.
- [ ] **Expired OTP**: Verify expired OTP code is rejected.
- [ ] **Max Attempts**: Verify OTP rejected after `max_attempts` wrong guesses.

---

## 🏢 10. Multi-Application Support

### Application Auth Middleware
- [ ] **Valid Credentials**: `X-Access-Key` + `X-Access-Secret` headers -> `request.application` is set.
- [ ] **Invalid Key**: Wrong `X-Access-Key` -> 401 response.
- [ ] **Invalid Secret**: Correct key, wrong secret -> 401 response.
- [ ] **Missing Headers**: No headers on protected endpoint -> 401 response.
- [ ] **Exempt Paths**: Verify `TENXYTE_EXEMPT_PATHS` and `TENXYTE_EXACT_EXEMPT_PATHS` bypass application auth.

### Application CRUD
- [ ] **Create Application**: Verify `create_application()` returns plain secret ONCE, stores bcrypt hash.
- [ ] **Regenerate Credentials**: Verify old credentials are invalidated.
- [ ] **Delete Application**: Verify cascade behavior on RefreshTokens.

### Token Isolation
- [ ] **Cross-App Token Rejection**: Generate token for App A -> use with App B headers -> should be rejected by `JWTAuthentication` (`app_id` mismatch).

---

## 🔄 11. Session & Device Limits

### Session Limits
- [ ] **`TENXYTE_SESSION_LIMIT_ENABLED = True`**: Login from multiple sessions.
- [ ] **`deny` action**: Verify new login is rejected when limit reached.
- [ ] **`revoke_oldest` action**: Verify oldest session is revoked when limit reached.
- [ ] **Per-user override**: Set `user.max_sessions = 2` -> verify takes precedence over global default.
- [ ] **`max_sessions = 0`**: Verify means unlimited.

### Device Limits
- [ ] **`TENXYTE_DEVICE_LIMIT_ENABLED = True`**: Login from multiple devices.
- [ ] **`deny` action**: Verify new device rejected.
- [ ] **`revoke_oldest` action**: Verify oldest device sessions revoked.
- [ ] **Known device bypass**: Verify existing device is not counted as new.

---

## 📧 12. Communication Backends

### Email Backends
- [ ] **`ConsoleBackend`**: Verify OTP email logged to console (dev mode).
- [ ] **`DjangoBackend`**: Verify uses Django's `EmailMultiAlternatives` with HTML support.
- [ ] **`TemplateEmailBackend`**: Verify template rendering with context variables.
- [ ] **`SendGridBackend`**: Verify API key validation and error handling when library missing.
- [ ] **Backend Switching**: Change `TENXYTE_EMAIL_BACKEND` in settings -> verify correct backend is used.

### SMS Backends
- [ ] **`ConsoleBackend`**: Verify SMS logged to console.
- [ ] **`TwilioBackend`**: Verify credentials validation and error handling when library missing.
- [ ] **Backend Switching**: Change `TENXYTE_SMS_BACKEND` -> verify correct backend.

### Email Templates
- [ ] **OTP Email**: Verify HTML template renders correctly with code, validity, app_name.
- [ ] **Welcome Email**: Verify personalized greeting.
- [ ] **Password Changed Email**: Verify security warning included.
- [ ] **Security Alert Email**: Verify all alert types (new_login, session_revoked, account_locked, device_limit).

---

## 🧹 13. Code Quality & Consistency

### Import Consistency
- [ ] **`get_user_model()` usage**: Audit ALL files for direct `User` imports. Expected: only `models.py` defines `User`, everywhere else uses `get_user_model()` or the helper function.
    - **Files to check**: `views.py`, `authentication.py`, `decorators.py`, `serializers.py`, `services/*.py`
- [ ] **Relative vs Absolute imports**: Verify consistency within the package (`from .models` vs `from tenxyte.models`).

### Dual Configuration Modules
- [x] **`conf.py` vs `config.py` audit**:
    - `config.py` a été supprimé et fusionné dans `conf.py`. ✅
    - `conf.py` est maintenant le module unique de configuration avec noms canoniques `TENXYTE_*`.
    - [x] **Verify no contradiction**: Plus de contradiction possible — un seul module. ✅

### Error Response Format
- [ ] **Consistency**: Verify ALL error responses follow the same format: `{"error": "message", "code": "ERROR_CODE"}`.
- [ ] **HTTP Status Codes**: Verify correct codes (400 for validation, 401 for auth, 403 for permissions, 404 for not found).

### OpenAPI Documentation
- [ ] **`drf-spectacular` coverage**: Verify all 30+ endpoints have `@extend_schema` decorators.
- [ ] **Schema generation**: Run `python manage.py spectacular --validate` -> no warnings.
- [ ] **Request/Response schemas**: Verify serializers are correctly referenced.

---

## ✅ 14. Conclusions

### What Works Well

1. **Architecture extensible et professionnelle**: Le pattern Abstract → Concrete → Swappable est identique à celui de Django `auth.User`. C'est un excellent choix qui permet aux projets d'étendre les modèles sans modifier le package.

2. **Sécurité multicouche**: 5 couches de sécurité complémentaires:
    - Application Auth (API keys)
    - JWT avec blacklisting et rotation
    - 2FA TOTP avec backup codes hashés (SHA-256)
    - Rate limiting progressif (10 classes de throttle)
    - Audit logging (20+ types d'événements)

3. **Service Layer propre**: Bonne séparation `Views → Services → Models`. Les services (`AuthService`, `JWTService`, `TOTPService`, etc.) encapsulent la logique métier et sont réutilisables en dehors des vues.

4. **Multi-DB natif**: La détection automatique de `ObjectIdAutoField` pour MongoDB est élégante et transparente.

5. **DevEx soignée**: Commande `tenxyte_seed` pour bootstrap rapide, Console backends pour dev, tout désactivable via settings, 4 apps showcase.

6. **Couverture fonctionnelle**: Pour une v0.0.8, le package couvre un périmètre impressionnant: auth email/phone/Google, 2FA, OTP, RBAC, multi-app, rate limiting, audit, password history, session/device limits.

### Ce Qui Doit Être Corrigé (Priorité Haute)

| # | Issue | Fichier | Impact | Status |
|---|---|---|---|---|
| 1 | Import `tenxyte_auth` au lieu de `tenxyte` | `tests/conftest.py`, `test_views.py`, `test_otp.py` | Tests cassés | ✅ Fixed |
| 2 | `User` hardcodé au lieu de `get_user_model()` | `views.py`, `authentication.py`, `decorators.py`, `serializers.py`, `google_auth_service.py` | Swappable models cassé | ✅ Fixed |
| 3 | `datetime.utcnow()` déprécié | `jwt_service.py` | Warnings Python 3.12+ | ✅ Fixed |
| 4 | `default_app_config` déprécié | `__init__.py` | Warnings Django 5.1+ | ✅ Fixed |
| 5 | `Application` fixture mal initialisée | `tests/conftest.py` | Secret non hashé | ✅ Fixed |
| 6 | `print()` au lieu de `logger` | `google_auth_service.py` | Erreurs invisibles en prod | ✅ Fixed |
| 7 | `conf.py` / `config.py` duplication | `conf.py` (unique), `config.py` supprimé | `config.py` fusionné dans `conf.py`, noms canoniques `TENXYTE_JWT_*` | ✅ Fixed |

### Ce Qui Devrait Être Amélioré (Priorité Moyenne)

| # | Suggestion | Détail | Status |
|---|---|---|---|
| 1 | **Éclater `views.py`** (1431 lignes) | Séparé en `views/auth_views.py`, `views/rbac_views.py`, `views/twofa_views.py`, `views/application_views.py`, `views/password_views.py`, `views/otp_views.py`, `views/user_views.py` | ✅ Done |
| 2 | **Hasher les codes OTP** | `OTPCode.code` stocké en clair → utiliser SHA-256 comme pour les backup codes | ⏳ À faire |
| 3 | **Ajouter une commande `tenxyte_cleanup`** | `management/commands/tenxyte_cleanup.py` créée | ✅ Done |
| 4 | **Créer `signals.py`** | `signals.py` créé avec handlers audit logging | ✅ Done |
| 5 | **Utiliser `ModelViewSet`** pour RBAC/Applications | Les endpoints CRUD gagneraient en lisibilité avec des ViewSets + Routers | ⏳ À faire |
| 6 | **Créer `CHANGELOG.md`** | `CHANGELOG.md` créé | ✅ Done |
| 7 | **Tests multi-DB** | 50 tests × 4 backends : SQLite ✅, PostgreSQL 16.11 ✅, MySQL 8.4.8 ✅, MongoDB 8.2.2 ✅ | ✅ Done |
| 8 | **Structurer les tests** | `tests/unit/` (6 fichiers), `tests/integration/` (1), `tests/security/` (1), `tests/multidb/` (2) | ✅ Done |
| 9 | **Ajouter des tests de sécurité** | 30 tests : JWT tampering, brute-force, injection SQL/XSS, cross-app tokens, accès non-authentifié | ✅ Done |
| 10 | **Coverage > 80%** | 68.51% mesuré (seuil 60% atteint). `pytest-cov` intégré. Objectif 80% en cours | ⏳ 68.51% |

### Métriques Clés du Projet

| Métrique | Valeur |
|---|---|
| Lignes de code source | ~6 500 |
| Modèles Django | 10 (4 abstract + 6 concrete) |
| Endpoints API | 30+ |
| Services | 6 |
| Décorateurs | 8 |
| Throttles | 10 |
| Serializers | 16 |
| Settings configurables | 50+ |
| Permissions par défaut (seed) | 28 |
| Rôles par défaut (seed) | 4 (viewer, editor, admin, super_admin) |
| **Tests totaux** | **192** (unit: 92, integration: 20, security: 30, multidb: 50) |
| **Coverage** | **68.51%** (seuil minimum: 60%) |
| **Backends DB vérifiés** | **4** (SQLite, PostgreSQL, MySQL, MongoDB) |
| Fichiers de test | 10 (6 unit + 1 integration + 1 security + 2 multidb) |
| Dépendances core | 9 |
| Dépendances optionnelles | 5 |

### Verdict Final

**Tenxyte est un package d'authentification Django solide et ambitieux.** L'architecture est professionnelle (abstract models, service layer, pluggable backends), la couverture fonctionnelle est large, et les choix de sécurité sont pertinents.

**Progrès depuis l'analyse initiale :**
- ✅ **7/7 bugs prioritaires corrigés** (imports, User hardcodé, deprecations, config dupliquée)
- ✅ **7/10 suggestions moyennes implémentées** (views éclaté, signals, cleanup, CHANGELOG, tests multi-DB, structure tests, tests sécurité)
- ✅ **192 tests passent** (unit: 92, integration: 20, security: 30, multidb: 50)
- ✅ **4 backends DB vérifiés** : SQLite, PostgreSQL 16.11, MySQL 8.4.8, MongoDB 8.2.2
- ✅ **Coverage 68.51%** (seuil 60% atteint)

**Reste à faire :**
- ⏳ Hasher les codes OTP (SHA-256)
- ⏳ ModelViewSet pour RBAC/Applications
- ⏳ Coverage → 80%
- ⏳ Tests End-to-End (API Postman + frontend Vue 3)
- ⏳ Documentation avancée (ARCHITECTURE.md, SECURITY.md, INTEGRATION_GUIDE.md)
