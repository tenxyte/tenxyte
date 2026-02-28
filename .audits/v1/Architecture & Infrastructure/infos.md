# Tenxyte — Architecture & Infrastructure Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit en profondeur de l'architecture et de l'infrastructure du package
> Tenxyte.
> **Date** : 2026-02-27
> **Version auditée** : `0.9.1.7`

---

## 1. Présentation générale du projet

### Nature du projet

Tenxyte est un **package Python/Django open-source** distribué sur PyPI, destiné
à être intégré comme dépendance dans des projets Django tiers. Ce n'est pas une
application déployée : c'est une **bibliothèque de composants d'authentification
et d'autorisation** réutilisables.

- **Licence** : MIT
- **Statut** : Beta (Development Status :: 4 - Beta)
- **Dépôt** : https://github.com/tenxyte/tenxyte
- **Documentation** : https://tenxyte.readthedocs.io

### Périmètre fonctionnel

| Fonctionnalité | Module | Statut |
|---------------|--------|--------|
| Authentification email/téléphone+password | `auth_views.py` | ✅ Prod |
| JWT (access token + refresh token) | `jwt_service.py` | ✅ Prod |
| RBAC hiérarchique (Roles + Permissions) | `rbac_views.py`, `auth.py` | ✅ Prod |
| 2FA TOTP (Google Authenticator) | `totp_service.py`, `twofa_views.py` | ✅ Prod |
| 2FA OTP email/SMS | `otp_service.py`, `otp_views.py` | ✅ Prod |
| Magic Link (passwordless) | `magic_link_service.py` | ✅ Prod |
| WebAuthn / Passkeys (FIDO2) | `webauthn_service.py` | ✅ Prod |
| OAuth Social (Google, GitHub, Microsoft, Facebook) | `social_auth_service.py` | ✅ Prod |
| Breach Check (HaveIBeenPwned k-anonymity) | `breach_check_service.py` | ✅ Prod |
| Multi-tenant / Organizations (B2B) | `organization_views.py` | ✅ Prod |
| AIRS — Agent AI Token System | `agent_service.py`, `agent_views.py` | ✅ Prod |
| GDPR / Suppression de compte | `account_deletion_views.py` | ✅ Prod |
| Audit logging | `security.py` (AuditLog) | ✅ Prod |
| Dashboard & Stats | `dashboard_views.py` | ✅ Prod |
| Export de données (RGPD Art. 20) | `account_deletion_views.py` | ✅ Prod |

---

## 2. Stack technique

### Python & Django

| Composant | Version requise | Notes |
|-----------|----------------|-------|
| Python | ≥ 3.10 | Testé sur 3.10, 3.11, 3.12 |
| Django | ≥ 5.0 | Support Django 5.0, 5.1, 5.2 |
| Django REST Framework | ≥ 3.14 | API REST principale |
| drf-spectacular | ≥ 0.27 | Génération schema OpenAPI |

### Dépendances principales (toujours installées)

| Package | Version | Rôle |
|---------|---------|------|
| `PyJWT` | ≥ 2.8 | Signature/vérification JWT |
| `bcrypt` | ≥ 4.0 | Hachage mots de passe et secrets |
| `pyotp` | ≥ 2.9 | TOTP (2FA) |
| `qrcode[pil]` | ≥ 8.0 | Génération QR codes TOTP |
| `google-auth` | ≥ 2.20 | OAuth Google |
| `google-auth-oauthlib` | ≥ 1.0 | OAuth Google (flux web) |
| `django-cors-headers` | ≥ 4.0 | CORS (listing dans requirements, middleware maison aussi disponible) |

### Dépendances optionnelles (extras PyPI)

| Extra | Packages | Usage |
|-------|---------|-------|
| `[twilio]` | `twilio ≥ 9.0` | Backend SMS Twilio |
| `[sendgrid]` | `sendgrid ≥ 6.10` | Backend email SendGrid |
| `[mongodb]` | `django-mongodb-backend ≥ 5.0` | Support MongoDB |
| `[postgres]` | `psycopg2-binary ≥ 2.9` | Support PostgreSQL |
| `[mysql]` | `mysqlclient ≥ 2.2` | Support MySQL |
| `[all]` | Tous les extras | Installation complète |

> **Note** : `py_webauthn` est une dépendance optionnelle non listée dans
> `pyproject.toml` — importée lazily dans `webauthn_service.py`. Elle doit
> être installée manuellement pour activer les Passkeys.

---

## 3. Architecture du package

### Structure des répertoires

```
tenxyte/
├── pyproject.toml               # Build system (hatchling), metadata, dépendances
├── src/
│   └── tenxyte/
│       ├── __init__.py          # Public API & auto-setup Django signals
│       ├── apps.py              # AppConfig → déclenche la config automatique
│       ├── conf.py              # TenxyteSettings — centralise toute la config (887 lignes)
│       ├── authentication.py    # JWTAuthentication (DRF class-based)
│       ├── middleware.py        # 6 middlewares (CORS, SecurityHeaders, AppAuth, OrgContext, AgentToken, PIIRedaction)
│       ├── throttles.py         # 12 classes de rate limiting IP-based
│       ├── validators.py        # PasswordValidator (score 0-100, 10 règles)
│       ├── decorators.py        # @require_permission, @require_role, @require_org_member…
│       ├── signals.py           # Django signals (auto-setup modèles)
│       ├── urls.py              # 70+ endpoints regroupés par module
│       ├── filters.py           # Filtres DRF (QueryFilterBackend)
│       ├── pagination.py        # Pagination standard
│       ├── tenant_context.py    # ContextVar Python pour isolation tenant
│       ├── device_info.py       # Fingerprinting et matching de devices
│       ├── models/
│       │   ├── auth.py          # User, Role, Permission (RBAC hiérarchique)
│       │   ├── application.py   # Application (multi-app auth)
│       │   ├── operational.py   # OTPCode, RefreshToken, LoginAttempt
│       │   ├── security.py      # BlacklistedToken, AuditLog, PasswordHistory
│       │   ├── magic_link.py    # MagicLinkToken
│       │   ├── organization.py  # Organization, OrganizationRole, OrganizationMembership
│       │   ├── tenant.py        # BaseTenantModel (abstract, auto-org-filter)
│       │   ├── agent.py         # AgentToken, AgentPendingAction (AIRS)
│       │   ├── gdpr.py          # AccountDeletionRequest
│       │   ├── social.py        # SocialAccount (OAuth)
│       │   ├── webauthn.py      # WebAuthnCredential, WebAuthnChallenge
│       │   └── base.py          # AutoFieldClass, get_*_model() helpers
│       ├── services/            # Logique métier pure (14 services)
│       ├── views/               # 17 modules de vues DRF
│       ├── serializers/         # 11 modules de serializers
│       ├── migrations/          # 4 migrations (initial + AIRS + AuditLog AIRS)
│       ├── backends/            # Backends pluggables (email, SMS)
│       ├── tasks/               # Tâches périodiques (Celery-ready)
│       ├── management/          # Commandes Django custom
│       └── templates/           # Templates emails HTML
├── tests/
│   ├── settings.py              # Settings Django pour les tests
│   ├── unit/                    # Tests unitaires (~60 fichiers)
│   ├── integration/             # Tests d'intégration (tenant, agent, auth)
│   ├── security/                # Tests de sécurité (JWT, injection, etc.)
│   └── multidb/                 # Tests multi-base de données
```

### Modèle de déploiement

Tenxyte est un **package installable** (`pip install tenxyte`). L'utilisateur
(développeur Django) :

1. Installe le package dans son projet Django existant
2. Ajoute `'tenxyte'` dans `INSTALLED_APPS`
3. Configure les settings `TENXYTE_*` dans son `settings.py`
4. Inclut les URLs : `path('api/v1/', include('tenxyte.urls'))`
5. Applique les migrations : `python manage.py migrate`

Le package **n'impose pas** d'architecture de déploiement — il hérite des choix
du projet hôte (serveur WSGI/ASGI, base de données, cache, etc.).

---

## 4. Modèles de données (schéma)

### Tables créées par Tenxyte

| Table | Modèle | Description |
|-------|--------|-------------|
| `users` | `User` | Utilisateurs (swappable via `TENXYTE_USER_MODEL`) |
| `roles` | `Role` | Rôles RBAC |
| `permissions` | `Permission` | Permissions hiérarchiques |
| `user_roles` | M2M | Association utilisateur ↔ rôles |
| `user_permissions` | M2M | Permissions directes utilisateur |
| `role_permissions` | M2M | Association rôle ↔ permissions |
| `applications` | `Application` | Applications clientes (multi-app) |
| `refresh_tokens` | `RefreshToken` | Tokens de renouvellement JWT |
| `blacklisted_tokens` | `BlacklistedToken` | JTIs révoqués |
| `otp_codes` | `OTPCode` | Codes OTP temporaires |
| `login_attempts` | `LoginAttempt` | Historique des tentatives de login |
| `audit_logs` | `AuditLog` | Journal d'audit complet |
| `password_history` | `PasswordHistory` | Historique mots de passe (anti-réutilisation) |
| `magic_link_tokens` | `MagicLinkToken` | Tokens magic link |
| `social_accounts` | `SocialAccount` | Comptes OAuth liés |
| `webauthn_credentials` | `WebAuthnCredential` | Clés publiques FIDO2 |
| `webauthn_challenges` | `WebAuthnChallenge` | Challenges FIDO2 temporaires |
| `organizations` | `Organization` | Organisations (multi-tenant B2B) |
| `organization_roles` | `OrganizationRole` | Rôles dans une organisation |
| `organization_memberships` | `OrganizationMembership` | Membres et rôles |
| `agent_tokens` | `AgentToken` | Tokens de délégation agents IA |
| `agent_pending_actions` | `AgentPendingAction` | Actions HITL en attente |
| `account_deletion_requests` | `AccountDeletionRequest` | Demandes RGPD |

### Relations clés

```
User ──M2M──▶ Role ──M2M──▶ Permission ◀──M2M── User (direct)
              └── parent (self FK)         └── parent (self FK)

User ──1:N──▶ RefreshToken (application, device_info, ip)
User ──1:N──▶ AuditLog (action, ip, user_agent, application)
User ──1:N──▶ AgentToken (permissions déléguées, circuit breaker)
User ──M2M──▶ Organization (via OrganizationMembership + OrganizationRole)
Organization ──FK──▶ Organization (parent, hiérarchie ≤ 5 niveaux)

AgentToken ──1:N──▶ AgentPendingAction (HITL confirmation_token)
AgentToken ──FK──▶ AuditLog (traçabilité agent)
```

### Modèles swappables (pattern Django `AUTH_USER_MODEL`)

L'intégration suit le pattern Django natif de *swappable models* :

| Setting | Défaut | Rôle |
|---------|--------|------|
| `TENXYTE_USER_MODEL` | `'tenxyte.User'` | Modèle utilisateur |
| `TENXYTE_APPLICATION_MODEL` | `'tenxyte.Application'` | Application cliente |
| `TENXYTE_ROLE_MODEL` | `'tenxyte.Role'` | Rôle RBAC |
| `TENXYTE_PERMISSION_MODEL` | `'tenxyte.Permission'` | Permission RBAC |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Organisation |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Rôle dans org |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL`| `'tenxyte.OrganizationMembership'` | Membership |

---

## 5. Pipeline de requêtes HTTP

### Stack middleware (ordre de priorité)

```
MIDDLEWARE = [
    'tenxyte.middleware.CORSMiddleware',              # 1 - Cross-Origin
    'tenxyte.middleware.SecurityHeadersMiddleware',   # 2 - X-Frame, nosniff, etc.
    'tenxyte.middleware.ApplicationAuthMiddleware',   # 3 - X-Access-Key/Secret
    'tenxyte.middleware.OrganizationContextMiddleware', # 4 - X-Org-Slug (multi-tenant)
    'tenxyte.middleware.AgentTokenMiddleware',        # 5 - AgentBearer (AIRS)
    'tenxyte.middleware.PIIRedactionMiddleware',      # 6 - Masquage PII pour agents IA
]
```

Suivi de l'authentification DRF classique :
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',  # 7 - Bearer JWT
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'tenxyte.throttles.LoginThrottle',           # 8 - Rate limiting
        ...
    ]
}
```

### Flow d'authentification standard (login email)

```
Client → POST /api/v1/login/email/
  Headers: X-Access-Key, X-Access-Secret
  Body:    { email, password, [totp_code] }

[1] ApplicationAuthMiddleware   → vérifie bcrypt(access_secret)
[2] LoginEmailView.post()       → AuthService.authenticate_by_email()
[3] AuthService                 → user.check_password() (bcrypt)
[4] AuthService                 → TOTP verify si 2FA activé
[5] AuthService                 → enforce session/device limits
[6] AuthService                 → RefreshToken.generate() (secrets.token_urlsafe(64))
[7] JWTService                  → jwt.encode() HS256 + JTI UUID v4
[8] AuditLog.log('login')       → tracé IP, device, application

Response: { access_token, refresh_token, user }
```

### Chemins exemptés de l'authentification applicative

- `/admin/` (Django admin natif)
- `{API_PREFIX}/health/`
- `{API_PREFIX}/docs/`
- `{API_PREFIX}/` (racine exacte)

---

## 6. Système de configuration (`conf.py`)

### Architecture de résolution des settings

```
1. TENXYTE_<NOM> explicite dans settings.py  ← priorité absolue
       ↓ (si absent)
2. Valeur du preset TENXYTE_SHORTCUT_SECURE_MODE
       ↓ (si absent ou preset non défini)
3. Valeur par défaut de conf.py
```

### Presets de sécurité

| Preset | JWT access | Max login attempts | Lockout | Breach check | Audit | WebAuthn |
|--------|-----------|-------------------|---------|--------------|-------|---------|
| `starter` | 1h | 10 | 15 min | ❌ | ❌ | ❌ |
| `medium` | 15 min | 5 | 30 min | ✅ reject | ✅ | ❌ |
| `robust` | 5 min | 3 | 60 min | ✅ reject | ✅ | ✅ |

### Variables de configuration couvertes (non exhaustif)

```
JWT: JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_LIFETIME,
     JWT_REFRESH_TOKEN_LIFETIME, REFRESH_TOKEN_ROTATION, TOKEN_BLACKLIST_ENABLED

AUTH: APPLICATION_AUTH_ENABLED, ACCOUNT_LOCKOUT_ENABLED, MAX_LOGIN_ATTEMPTS,
      LOCKOUT_DURATION_MINUTES, RATE_LIMITING_ENABLED, RATE_LIMIT_WINDOW_MINUTES

PASSWORDS: PASSWORD_MIN_LENGTH (8), PASSWORD_MAX_LENGTH (128),
           PASSWORD_REQUIRE_UPPERCASE/LOWERCASE/DIGIT/SPECIAL,
           PASSWORD_HISTORY_ENABLED, PASSWORD_HISTORY_COUNT,
           BREACH_CHECK_ENABLED, BREACH_CHECK_REJECT

SESSIONS: SESSION_LIMIT_ENABLED, DEFAULT_MAX_SESSIONS, DEFAULT_SESSION_LIMIT_ACTION,
          DEVICE_LIMIT_ENABLED, DEFAULT_MAX_DEVICES, DEVICE_LIMIT_ACTION

2FA: TOTP_ISSUER, TOTP_VALID_WINDOW, BACKUP_CODES_COUNT,
     OTP_LENGTH, OTP_EMAIL_VALIDITY, OTP_PHONE_VALIDITY, OTP_MAX_ATTEMPTS,
     WEBAUTHN_ENABLED, WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME, WEBAUTHN_CHALLENGE_EXPIRY_SECONDS

MAGIC_LINK: MAGIC_LINK_ENABLED, MAGIC_LINK_EXPIRY_MINUTES, MAGIC_LINK_BASE_URL

HTTP: CORS_ENABLED, CORS_ALLOW_ALL_ORIGINS, CORS_ALLOWED_ORIGINS,
      SECURITY_HEADERS_ENABLED, SECURITY_HEADERS

MULTI-TENANT: ORGANIZATIONS_ENABLED, ORG_ROLE_INHERITANCE, ORG_MAX_DEPTH, ORG_MAX_MEMBERS

AIRS: AIRS_ENABLED, AIRS_DEFAULT_EXPIRY, AIRS_TOKEN_MAX_LIFETIME,
      AIRS_REQUIRE_EXPLICIT_PERMISSIONS, AIRS_CIRCUIT_BREAKER_ENABLED,
      AIRS_REDACT_PII, AIRS_BUDGET_TRACKING_ENABLED

AUDIT: AUDIT_LOGGING_ENABLED

THROTTLE: SIMPLE_THROTTLE_RULES (dict URL → rate)

MISC: BASE_URL, API_PREFIX, API_VERSION
```

---

## 7. Surface d'API REST (~70 endpoints)

### Groupes d'endpoints

| Groupe | Endpoints | Auth requise |
|--------|-----------|-------------|
| **Authentification** | `/login/email/`, `/login/phone/`, `/register/`, `/logout/`, `/logout/all/`, `/refresh/` | X-Access-Key uniquement |
| **Social OAuth** | `/social/<provider>/` (google, github, microsoft, facebook) | X-Access-Key uniquement |
| **OTP** | `/otp/request/`, `/otp/verify/email/`, `/otp/verify/phone/` | X-Access-Key + context |
| **Password** | `/password/reset/request/`, `/password/reset/confirm/`, `/password/change/`, `/password/strength/` | Mixed |
| **Profil utilisateur** | `/me/`, `/me/roles/` | JWT requis |
| **2FA TOTP** | `/2fa/setup/`, `/2fa/confirm/`, `/2fa/disable/`, `/2fa/status/`, `/2fa/backup-codes/` | JWT requis |
| **Magic Link** | `/magic-link/request/`, `/magic-link/verify/` | X-Access-Key uniquement |
| **WebAuthn** | `/webauthn/register/begin|complete/`, `/webauthn/authenticate/begin|complete/` | Mixed |
| **RBAC** | `/permissions/`, `/roles/`, `/users/<id>/roles/`, `/users/<id>/permissions/` | JWT + is_staff |
| **Applications** | `/applications/`, `/applications/<id>/regenerate/` | JWT + is_staff |
| **Admin utilisateurs** | `/admin/users/`, `/admin/users/<id>/ban|unban|lock|unlock/` | JWT + is_staff |
| **Admin sécurité** | `/admin/audit-logs/`, `/admin/login-attempts/`, `/admin/blacklisted-tokens/`, `/admin/refresh-tokens/` | JWT + is_staff |
| **GDPR** | `/request-account-deletion/`, `/confirm-account-deletion/`, `/export-user-data/` | JWT requis |
| **Admin GDPR** | `/admin/deletion-requests/` | JWT + is_staff |
| **AIRS Agents** | `/ai/tokens/`, `/ai/pending-actions/`, `/ai/tokens/<id>/heartbeat/report-usage/` | JWT + is_staff |
| **Organizations** | `/organizations/`, `/organizations/members/`, `/organizations/invitations/` | JWT + membership |
| **Dashboard** | `/dashboard/stats/`, `/dashboard/auth/`, `/dashboard/security/` | JWT + is_staff |

### Schéma OpenAPI

Disponible via `drf-spectacular`. Le schéma complet est généré dans
`openapi_schema.json` (371 KB brut, 364 KB optimisé).

---

## 8. Rate Limiting

### Throttle classes par endpoint

| Endpoint | Throttle | Limite |
|----------|---------|--------|
| `/login/*` | `LoginThrottle` | 5/min par IP |
| `/login/*` | `LoginHourlyThrottle` | 20/h par IP |
| `/register/` | `RegisterThrottle` | 3/h par IP |
| `/register/` | `RegisterDailyThrottle` | 10/j par IP |
| `/password/reset/request/` | `PasswordResetThrottle` | 3/h par IP |
| `/password/reset/request/` | `PasswordResetDailyThrottle` | 10/j par IP |
| `/otp/*` | `OTPRequestThrottle` | 5/h par IP |
| `/otp/verify/*` | `OTPVerifyThrottle` | 5/min par IP |
| `/refresh/` | `RefreshTokenThrottle` | 30/min par IP |
| `/magic-link/request/` | `MagicLinkRequestThrottle` | 3/h par IP |
| `/magic-link/verify/` | `MagicLinkVerifyThrottle` | 10/min par IP |
| Routes custom | `SimpleThrottleRule` | Configurable par URL |

Le **throttle progressif** (`ProgressiveLoginThrottle`) double la durée de
blocage après chaque échec (timeout = min(60 × 2^n, 3600 secondes)).

---

## 9. Module AIRS (Agent AI Restriction System)

### Concept

Permet de déléguer des permissions à des agents IA autonomes avec restrictions
explicites. Architecture à 4 niveaux :

1. **AgentToken** créé par un humain authentifié, avec subset de ses permissions
2. **Circuit Breaker** : suspend le token si seuils dépassés
3. **Dead Man's Switch** : révoque si pas de heartbeat
4. **HITL (Human-in-the-Loop)** : certaines actions nécessitent une confirmation humaine

### Authentification AIRS

Header : `Authorization: AgentBearer <token>`  
Format du token : 48 caractères alphanumériques générés par CSPRNG

### Données tracées par action agent

- `endpoint`, `method`, `status_code`, `actor` (agent_id)
- `prompt_trace_id` (traçabilité chaîne LLM)
- `on_behalf_of` (l'humain délégant)

---

## 10. Multi-tenancy (Organizations)

### Feature opt-in

Activé via `TENXYTE_ORGANIZATIONS_ENABLED = True`.

### Isolation des données (Hard Multi-Tenancy)

Le header `X-Org-Slug` identifie le tenant sur chaque requête.
Le middleware `OrganizationContextMiddleware` stocke l'organisation active dans
une **Python `ContextVar`** (thread-safe, request-scoped).

`BaseTenantModel` est un modèle abstrait qui surcharge `save()` et `delete()`
pour forcer l'attribution automatique de l'organisation courante.

### Hiérarchie des organisations

```
OrganizationA (niveau 1)
└── OrganizationB (niveau 2)
    └── OrganizationC (niveau 3)    ← max 5 niveaux (ORG_MAX_DEPTH)
```

L'héritage de rôles dans la hiérarchie est configurable (`ORG_ROLE_INHERITANCE`).

---

## 11. Conformité RGPD / GDPR

### Mécanismes implémentés

| Exigence RGPD | Implémentation |
|--------------|----------------|
| Droit à l'effacement (Art. 17) | Soft delete avec anonymisation des PII |
| Droit à la portabilité (Art. 20) | Export JSON des données utilisateur |
| Journalisation des accès | AuditLog complet avec IP, user_agent, action |
| Minimisation des données (AIRS) | PIIRedactionMiddleware masque les champs PII aux agents |
| Délai de rétention | AccountDeletionRequest avec délai de grâce configurable |

### Soft Delete — données anonymisées

```
email → "deleted_<id>@deleted.local"
first_name, last_name → ""
phone_country_code, phone_number → null
google_id → null
totp_secret, backup_codes → null/[]
is_2fa_enabled → false
is_active, is_staff, is_superuser → false
is_deleted, deleted_at → true/now()
anonymization_token → token cryptographique pour audit
```

---

## 12. Tests et qualité

### Structure des tests

| Dossier | Contenu | Nb fichiers |
|---------|---------|-------------|
| `tests/unit/` | Tests unitaires par service/vue/modèle | ~60 fichiers |
| `tests/integration/` | Tests d'intégration (tenant isolation, agent workflows) | 4 fichiers |
| `tests/security/` | Tests de sécurité explicites (JWT forgery, brute force, etc.) | 2 fichiers |
| `tests/multidb/` | Tests multi-base de données | ~7 fichiers |

### Configuration des tests

```ini
# pyproject.toml [tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
addopts = "--cov=tenxyte --cov-report=html --cov-report=term --cov-fail-under=60"
```

- Base de données de test : **SQLite en mémoire** (`:memory:`)
- Coverage minimum requis : **60%** (collected 1408 items : Total coverage: 98.17%)

### Linting & qualité code

- **Black** : formatage, line-length 120, Python 3.10+
- **Ruff** : linting rapide, line-length 120
- **mypy** : typage statique

---

## 13. Compatibilité bases de données

Tenxyte est compatible avec toutes les bases de données supportées par Django :

| Base de données | Support | Extra requis |
|----------------|---------|--------------|
| SQLite | ✅ natif | aucun |
| PostgreSQL | ✅ | `psycopg2-binary` ou `psycopg` |
| MySQL / MariaDB | ✅ | `mysqlclient` |
| MongoDB | ✅ | `django-mongodb-backend` |

> **Contrainte** : le champ `max_length=191` sur les champs uniques est une
> concession pour la compatibilité MySQL avec encodage `utf8mb4` (limite d'index
> à 767 bytes → 191 chars × 4 bytes/char).

---

## 14. Backends pluggables

### SMS

| Backend | Activation |
|---------|-----------|
| `ConsoleBackend` | Défaut dev (log au lieu d'envoyer) |
| `TwilioBackend` | `pip install tenxyte[twilio]` + config `TWILIO_*` |
| `NGHBackend` | Config `NGH_API_KEY`, `NGH_API_SECRET`, `NGH_SENDER_ID` |

### Email

| Backend | Activation |
|---------|-----------|
| `DjangoBackend` | Défaut (délègue à `EMAIL_BACKEND` Django) |
| `ConsoleBackend` | Dev |
| `SendGridBackend` | `pip install tenxyte[sendgrid]` + `SENDGRID_API_KEY` |
| `TemplateEmailBackend` | Templates HTML Jinja2 |

---

## 15. Points d'attention pour l'audit architectural

Les éléments suivants méritent une attention particulière lors de l'audit :

### Architecture

- [ ] **Couplage avec Django** : le package est fortement lié à Django/DRF — pas d'abstraction permettant un usage framework-agnostique
- [ ] **ContextVar vs thread-locals** : bien utilisé pour le tenant context (`tenant_context.py`), vérifier cohérence en cas d'async Django (ASGI)
- [ ] **Swappable models** : la résolution dynamique via `get_*_model()` introduit des dépendances circulaires potentielles à auditer
- [ ] **URLs conditionnelles** : les URLs organizations sont ajoutées conditionnellement au module-load (`if org_settings.ORGANIZATIONS_ENABLED`) — risque si la config change entre processus workers

### Infrastructure (côté intégrateur)

- [ ] **Cache** : le rate limiting et le circuit breaker AIRS utilisent `django.core.cache` — en production, Redis est indispensable (MemCache = non-persistant entre workers)
- [ ] **Tâches périodiques** : `BlacklistedToken.cleanup_expired()` doit être planifié (Celery Beat ou cron) — pas de scheduler intégré
- [ ] **ASGI/async** : les vues sont 100% synchrones — compatibilité ASGI via `sync_to_async` non testée explicitement
- [ ] **Migrations** : 4 migrations — la migration initiale (`0001_initial.py`, 35KB) est très large et crée toutes les tables en une seule transaction
- [ ] **`bcrypt` à chaque requête** : la vérification du `access_secret` applicatif utilise bcrypt sur **chaque requête** — goulot potentiel à haute charge

### Sécurité résiduelle à vérifier

- [ ] **JWT_SECRET_KEY** : par défaut, utilise `SECRET_KEY` Django — risque de réutilisation de clé si le secret Django est exposé
- [ ] **WebAuthn challenge** : le challenge raw est stocké en DB (pas hashé) — acceptable car à usage unique et TTL 5 min, mais à noter
- [ ] **`piiredaction` vs chiffrement** : le masquage PII (`***REDACTED***`) est côté réponse HTTP uniquement — les données sont toujours accessibles en DB par les agents qui ont accès à la base
- [ ] **HTTP_X_FORWARDED_FOR** : utilisé sans liste de proxies de confiance configurés — vérifier si l'intégrateur configure correctement `TRUSTED_PROXIES`

---

## 16. Threat Modeling (STRIDE/PASTA)

> Tenxyte ne fournit pas de modèle de menaces documenté. Cette section fournit
> les éléments nécessaires à l'auditeur pour conduire un exercice STRIDE ou PASTA
> à partir de l'architecture réelle.

### Composants à modéliser (Data Flow Diagram)

```
[Client] ──HTTPS──▶ [Proxy/LB] ──HTTP──▶ [Django/Gunicorn]
                                                │
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                 ▼
                          [DB SQL]          [Redis/Cache]    [External APIs]
                       (23 tables)       (rate-limiting,   (HIBP, Google, GitHub,
                                         circuit breaker,   Microsoft, Facebook,
                                         token blacklist)   Twilio, SendGrid)
```

### Analyse STRIDE par composant

#### 1. Pipeline d'authentification applicative (X-Access-Key/Secret)

| STRIDE | Menace | Mitigation en place | Lacune |
|--------|--------|--------------------|---------|
| **S**poofing | Forger les credentials d'une application | bcrypt sur access_secret | X-Forwarded-For forgeable (bypass IP throttle) |
| **T**ampering | Modifier le corps de la requête pour bypasser la validation | Serializers DRF stricts | N/A |
| **R**epudiation | Nier avoir utilisé l'API depuis une app | AuditLog par requête | Pas de signature des logs |
| **I**nfo disclosure | Réponse différente selon clé valide/invalide | Message uniforme `APP_AUTH_INVALID` | ✅ Couvert |
| **D**enial of Service | Épuiser les connexions bcrypt (O(n) CPU) | Rate limiting + access_secret 72 chars | bcrypt sur chaque requête = vecteur DoS |
| **E**levation | Application inactive bypasse ? | `is_active=True` vérifié au lookup | ✅ Couvert |

#### 2. JWT Access Token

| STRIDE | Menace | Mitigation en place | Lacune |
|--------|--------|--------------------|---------|
| **S**poofing | Forger un JWT | HS256 signé + algorithme whitelisté | Secret = SECRET_KEY Django (risque partage clé) |
| **T**ampering | Modifier le payload | Signature HMAC-SHA256 | ✅ Couvert |
| **R**epudiation | Nier avoir effectué une action | JTI UUID v4 + AuditLog | ✅ Couvert |
| **I**nfo disclosure | JWT décodable sans clé (base64) | Payload ne contient que user_id/app_id | Ne pas mettre de PII dans le payload |
| **D**enial of Service | Flood de tokens invalides | Rate limiting middleware | ✅ Partiellement couvert |
| **E**levation | Réutiliser un token après logout | Blacklist JTI + révocation refresh | ✅ Couvert |

#### 3. Module AIRS (AgentToken)

| STRIDE | Menace | Mitigation | Lacune |
|--------|--------|-----------|-------|
| **S**poofing | Forger un AgentToken | Lookup DB + validation état ACTIVE | Token en clair en DB |
| **T**ampering | Modifier les permissions d'un agent en cours d'exécution | Permissions figées à la création | ✅ Couvert |
| **R**epudiation | Agent nie avoir agi | AuditLog + prompt_trace_id | ✅ Couvert |
| **I**nfo disclosure | Agent accède à des PII en réponse | PIIRedactionMiddleware | Seulement en transit, pas en DB |
| **D**enial of Service | Agent en boucle infinie | Circuit breaker + budget tracking | ✅ Couvert |
| **E**levation | Agent acquiert plus de permissions que l'humain | Double passe RBAC (token + user) | ✅ Couvert |

#### 4. Base de données (couche stockage)

| STRIDE | Menace | Mitigation | Lacune |
|--------|--------|-----------|-------|
| **S**poofing | Accès DB sans authentification | Credentials DB configurés par l'intégrateur | Tenxyte ne valide pas les droits DB |
| **T**ampering | Modification directe des données (hors API) | Aucune — DB accessible par admin infra | Pas d'intégrité cryptographique des lignes |
| **R**epudiation | Modification de ligne sans trace | AuditLog couvre les actions API | Actions DB directes non tracées |
| **I**nfo disclosure | Dump de la DB → TOTP secrets et refresh tokens en clair | Chiffrement full-disk (infrastructure) | totp_secret et refresh_tokens non chiffrés en DB |
| **D**enial of Service | Requêtes lourdes / table scan | Indexes DB (à vérifier dans migrations) | Pas de pagination préventive sur audit_logs |
| **E**levation | Compte DB avec droits root utilisé en production | Devoir du moindre privilège (intégrateur) | Non adressé par Tenxyte |

### Vecteurs d'attaque prioritaires (résumé PASTA)

| Priorité | Vecteur | Impact | Probabilité |
|----------|---------|--------|------------|
| 🔴 P1 | Compromise `SECRET_KEY`/`JWT_SECRET_KEY` | Forgery de tout token JWT | Faible si secrets bien gérés |
| 🔴 P1 | Dump DB → refresh tokens + TOTP secrets en clair | Usurpation de sessions + 2FA bypass | Faible si DB protégée |
| 🟡 P2 | X-Forwarded-For forgery → bypass rate limiting | Brute force illimité | Élevée si derrière proxy non configuré |
| 🟡 P2 | Account takeover OAuth (email non vérifié) | Prise de contrôle compte existant | Moyenne (dépend du provider) |
| 🟡 P2 | TOTP replay (code réutilisé dans la fenêtre) | 2FA bypass | Faible (window 30s) |
| 🟢 P3 | IDOR sur endpoints admin | Accès données autres utilisateurs | Faible si auth is_staff correcte |
| 🟢 P3 | Mass assignment via PATCH /me/ | Élévation de privilèges | Faible si serializer correctement restreint |

---

## 17. Audit de la configuration de la base de données

> Tenxyte est un package — il ne configure pas directement la DB. Ces éléments
> sont à vérifier côté infrastructure de l'intégrateur.

### 17.1 Tables créées et données sensibles stockées

| Table | Données sensibles | Chiffrement en DB |
|-------|-----------------|-------------------|
| `users` | `password` (bcrypt), `totp_secret` (clair ⚠️), `backup_codes` (SHA-256) | ❌ Pas de chiffrement colonne |
| `refresh_tokens` | `token` (64 chars, clair ⚠️) | ❌ |
| `applications` | `access_secret_hash` (bcrypt) | ✅ Hashé |
| `agent_tokens` | `token` (48 chars, clair ⚠️) | ❌ |
| `social_accounts` | `access_token`, `refresh_token` OAuth (clair ⚠️) | ❌ |
| `audit_logs` | IP, user_agent, details JSON (PII potentiel) | ❌ |
| `magic_link_tokens` | `token_hash` (SHA-256) | ✅ Hashé |
| `otp_codes` | `code_hash` (SHA-256) | ✅ Hashé |

### 17.2 Points de configuration DB à auditer

| Contrôle | Questions pour l'auditeur |
|---------|---------------------------|
| **Droits DB** | L'utilisateur DB a-t-il uniquement `SELECT/INSERT/UPDATE/DELETE` sur les tables Tenxyte ? Pas de `DROP TABLE`, `CREATE USER`, `GRANT` ? |
| **Connexions TLS** | Les connexions Django → DB sont-elles chiffrées TLS ? (`OPTIONS: {'sslmode': 'require'}` dans `DATABASES`) |
| **Séparation des comptes DB** | Y a-t-il un compte DB distinct pour l'application vs. les migrations vs. les backups ? |
| **Backups** | Les backups sont-ils chiffrés à la destination (AES-256) ? |
| **Rétention des backups** | Les backups contiennent-ils des TOTP secrets et refresh tokens — quand sont-ils purgés ? |
| **Logs de requêtes** | Les logs slow-query contiennent-ils des valeurs de paramètres SQL (PII) ? |
| **Isolation réseau** | La DB est-elle accessible uniquement depuis les serveurs applicatifs (VPC, security group) ? |
| **Accès admin DB** | L'accès admin (pgAdmin, MySQL Workbench) se fait-il via VPN/bastion uniquement ? |

### 17.3 Configuration Django recommandée pour la sécurité DB

```python
# settings.py — configuration sécurisée PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],             # Compte avec droits minimaux uniquement
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',                  # TLS obligatoire
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 60,                        # Connexions persistantes (perf)
    }
}

# Grants SQL minimaux pour l'utilisateur applicatif
# GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
# REVOKE CREATE, DROP, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES FROM app_user;
```

### 17.4 Indexes — vérification (migrations)

```python
# Tenxyte crée automatiquement les indexes suivants (0001_initial.py) :
# - UNIQUE INDEX sur users.email
# - UNIQUE INDEX sur applications.access_key
# - INDEX sur refresh_tokens.user + application
# - INDEX sur otp_codes.user + expires_at
# - INDEX sur audit_logs.user + created_at
# - INDEX sur login_attempts.identifier + created_at
#
# ⚠️ À vérifier : les JOINs sur audit_logs.details (JSONField) ne sont pas
# indexés — les requêtes full-scan sur audit_logs volumineuse sont coûteuses.
```

---

## 18. SCA — Software Composition Analysis (Audit des dépendances)

### 18.1 Inventaire des dépendances avec historique de vulnérabilités

| Package | Version min | CVE notables historiques | Statut actuel |
|---------|------------|--------------------------|---------------|
| `Django` | ≥ 5.0 | SQL injection (CVE-2019-14234), XSS (CVE-2021-33203), ReDoS (CVE-2021-31542) | Maintenu — suivre django-security@googlegroups.com |
| `djangorestframework` | ≥ 3.14 | XSS (CVE-2020-25626) | Maintenu |
| `PyJWT` | ≥ 2.8 | **CVE-2022-29217** — `alg:none` bypass (< 2.4.0), **CVE-2017-11424** — RSA/HMAC confusion | **Corrigé en v2.x** — whitelist d'algorithme en place dans Tenxyte |
| `bcrypt` | ≥ 4.0 | Aucun CVE actif — dépendance C (cffi) | ✅ Sûr |
| `pyotp` | ≥ 2.9 | Aucun CVE connu | ✅ Sûr |
| `Pillow` (via qrcode) | **Non contraint** | **CVE-2023-44271** (DoS), **CVE-2022-45199** (buffer overflow), **CVE-2021-25289** (RCE) | ⚠️ Version effective non contrainte |
| `google-auth` | ≥ 2.20 | **CVE-2023-2203** — bypass validation token (< 2.0.0) | Corrigé en v2.x |
| `requests` | Transitif | **CVE-2023-32681** — redirect header leak (< 2.31.0) | À vérifier version installée |
| `py_webauthn` | **Non listé** | Inconnu — pas de contrainte de version | ⚠️ Version libre |
| `django-mongodb-backend` | ≥ 5.0 | Backend expérimental — moins audité | ⚠️ Usage limité |
| `twilio` | ≥ 9.0 (optionnel) | Aucun CVE critique récent | ✅ |
| `sendgrid` | ≥ 6.10 (optionnel) | Aucun CVE critique récent | ✅ |

### 18.2 Commandes d'audit recommandées

```bash
# 1. pip-audit — base de données PyPA Advisory
pip-audit
pip-audit --requirement requirements.txt
pip-audit --output-format json > pip_audit_report.json

# 2. safety — base OSV + PyUp
safety check
safety check --full-report
safety check --json > safety_report.json

# 3. Snyk — analyse complète + fix suggestions
snyk test --file=pyproject.toml
snyk monitor  # Monitoring continu + alerting

# 4. Liste des dépendances effectivement installées (freeze)
pip freeze > installed_packages.txt
pip list --outdated   # Packages obsolètes

# 5. Analyse statique sécurité
bandit -r src/tenxyte/ -f json -o bandit_report.json
semgrep --config "p/python" --config "p/django" src/tenxyte/ --json > semgrep_report.json

# 6. Vérifier spécifiquement py_webauthn (non contraint)
pip show py_webauthn   # Version effectivement installée

# 7. Vérifier Pillow (version effective via qrcode)
pip show Pillow
```

### 18.3 Risques liés à l'absence de lock file

```
Problème : Tenxyte n'a pas de requirements.txt ni de poetry.lock.
Les dépendances sont contraintes par des ranges (≥ X.Y) dans pyproject.toml.

Conséquence : deux installations du même package tenxyte dans le même
environnement peuvent avoir des versions différentes de dépendances
transitives — rendant la reproductibilité impossible et le SCA difficile.

Recommandation :
  - Publier un requirements.txt officiel avec des versions épinglées (==)
  - Ou utiliser pip-compile (pip-tools) pour générer un lock file
  - Monitorer avec Dependabot ou Renovate Bot sur le repo GitHub
```

### 18.4 Monitoring continu recommandé

| Outil | Fréquence | Action sur alerte |
|-------|----------|------------------|
| **Dependabot** (GitHub) | Quotidien | PR automatique de mise à jour |
| **Snyk monitor** | Temps réel | Email/Slack sur nouveau CVE |
| **pip-audit** (CI/CD) | À chaque build | Échec du pipeline si CVE critique |
| **safety** (pre-commit hook) | À chaque commit | Blocage commit si vulnérabilité |

```yaml
# Exemple GitHub Actions — SCA dans CI/CD
- name: Security audit
  run: |
    pip install pip-audit safety
    pip-audit --fail-on-severity high
    safety check --full-report
```

---

## 19. Liens utiles

| Ressource | URL |
|-----------|-----|
| Dépôt GitHub | https://github.com/tenxyte/tenxyte |
| Documentation | https://tenxyte.readthedocs.io |
| PyPI | https://pypi.org/project/tenxyte/ |
| Changelog | CHANGELOG.md du dépôt |
| Schema OpenAPI | `openapi_schema.json` (dans le dépôt) |
| Design Spec | `DESIGN_SPEC.json` (dans le dépôt) |
| Roadmap | `ROADMAP.md` (dans le dépôt) |
| Tests settings | `tests/settings.py` |
