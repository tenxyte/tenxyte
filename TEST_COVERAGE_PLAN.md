# Plan d'amélioration du coverage — Tenxyte

## Situation actuelle (mise à jour Feb 2026)

**Total coverage : 70.67%** (527 tests, 0 échecs)

| Module | Coverage avant | Coverage actuel | Fichier de test |
|---|---|---|---|
| `services/organization_service.py` | **0%** | **94%** | `test_organization_service.py` ✅ |
| `views/organization_views.py` | **0%** | **94%** | `test_organization_views.py` ✅ |
| `views/account_deletion_views.py` | **39%** | **95%** | `test_account_deletion.py` ✅ |
| `services/account_deletion_service.py` | **17%** | **79%** | `test_account_deletion.py` ✅ |
| `views/gdpr_admin_views.py` | **32%** | **91%** | `test_gdpr_admin_views.py` ✅ |
| `views/security_views.py` | **41%** | **93%** | `test_security_views.py` ✅ |
| `filters.py` | **46%** | **~75%** | `test_filters.py` ✅ |
| `services/email_service.py` | **30%** | **82%** | `test_email_service_deletion.py` ✅ |
| `decorators.py` | **38%** | **~75%** | `test_decorators.py` ✅ |
| `views/application_views.py` | **42%** | **96%** | `test_application_views.py` ✅ |
| `views/rbac_views.py` | **41%** | **84%** | `test_rbac_views.py` ✅ |
| `services/google_auth_service.py` | **25%** | **96%** | `test_google_auth_service.py` ✅ |
| `backends/email.py` | **52%** | **100%** | `test_email_backends.py` ✅ |
| `backends/sms.py` | **49%** | **100%** | `test_sms_backends.py` ✅ |
| `services/auth_service.py` | **67%** | **51%** | partiellement couvert |
| `views/auth_views.py` | **69%** | **37%** | partiellement couvert |

### Bugs corrigés lors des tests
- `filters.py` : champ `joined_at` → `created_at` dans `apply_member_filters`
- `decorators.py` : `require_org_admin` bloquait les owners → accepte `owner` ou `admin`
- `models/organization.py` : `has_permission` ne gérait pas les wildcards (`org.*`)
- `views/account_deletion_views.py` : `hasattr` mal positionné dans la list comprehension `applications`
- `services/email_service.py` : import `settings` manquant

---

## Phase 1 — Décorateurs RBAC & `require_jwt` (Priorité critique) ✅

> **Gain estimé : +8–10 pts → ~77%**

`decorators.py` est le cœur du système de sécurité. Coverage actuel : **38%** — le pire score côté logique métier.

### Fichier : `tests/unit/test_decorators.py` [NEW]

**Tests à écrire :**

#### `require_jwt`
- [x] Requête sans header `Authorization` → 401
- [x] Token mal-formé → 401
- [x] Token valide → vue appelée normalement
- [x] Token blacklisté (invalide) → 401
- [x] Désactivé via `TENXYTE_JWT_AUTH_ENABLED = False` → vue appelée sans vérification
- [x] Utilisateur inactif → 401
- [x] App ID mismatch → 401
- [x] Fonctionne comme décorateur de méthode (CBV)

#### `require_role / require_any_role / require_all_roles`
- [x] Utilisateur avec le bon rôle → accès accordé
- [x] Utilisateur sans le rôle → 403
- [x] `require_any_role` : au moins un rôle correspond → accès
- [x] `require_any_role` : aucun rôle → 403
- [x] `require_all_roles` : tous les rôles présents → accès
- [x] `require_all_roles` : un seul manquant → 403

#### `require_permission / require_any_permission / require_all_permissions`
- [x] Permission directe → accès accordé
- [x] Permission via rôle → accès accordé
- [x] Aucune permission → 403
- [x] `require_any_permission` avec une perm valide → accès
- [x] `require_any_permission` sans aucune perm → 403
- [x] `require_all_permissions` toutes présentes → accès
- [x] `require_all_permissions` une manquante → 403

#### `rate_limit`
- [x] Sous la limite → vue appelée
- [x] Dépassement limite → 429
- [x] Désactivé via `TENXYTE_RATE_LIMITING_ENABLED = False` → vue toujours appelée

#### `get_client_ip`
- [x] Avec `HTTP_X_FORWARDED_FOR`
- [x] Sans header → `REMOTE_ADDR`
- [x] Multiple IPs dans X-Forwarded-For → première IP

---

## Phase 2 — Views Application & RBAC (Priorité haute) ✅

> **Gain estimé : +6–8 pts → ~84%**

### Fichier : `tests/unit/test_application_views.py` [NEW]

`views/application_views.py` — coverage actuel **100%** (était 42%)

- [x] `GET /applications/` avec permission → liste paginée
- [x] `GET /applications/` sans permission → 403
- [x] `POST /applications/` → création
- [x] `POST /applications/` données invalides → 400
- [x] `GET /applications/<id>/` → détails
- [x] `GET /applications/<id>/` inexistant → 404
- [x] `PUT /applications/<id>/` → mise à jour
- [x] `DELETE /applications/<id>/` → suppression
- [x] `POST /applications/<id>/regenerate/` → nouveaux credentials

### Extension de : `tests/unit/test_direct_permissions.py` & `test_hierarchical_permissions.py`
Nouveaux fichiers : `tests/unit/test_rbac_views.py`

`views/rbac_views.py` — coverage actuel **100%** (était 41%)

- [x] `GET /permissions/` paginé + filtres
- [x] `POST /permissions/` création
- [x] `PUT/DELETE /permissions/<id>/`
- [x] `GET /roles/` liste + filtres
- [x] `POST /roles/` → `RoleListView.post`
- [x] `GET/PUT/DELETE /roles/<id>/`
- [x] `POST /roles/<id>/permissions/` → ajouter permissions
- [x] `DELETE /roles/<id>/permissions/` → retirer permissions
- [x] `GET/POST/DELETE /users/<id>/roles/`
- [x] `GET/POST/DELETE /users/<id>/permissions/`

---

## Phase 3 — Backends Email & SMS (Priorité moyenne-haute) ✅

> **Gain estimé : +3–4 pts → ~87%**

### Fichier : `tests/unit/test_email_backends.py` [NEW]

`backends/email.py` — coverage actuel **100%** (était 52%)

- [x] `ConsoleBackend.send_email` → loggé sans exception
- [x] `DjangoBackend.send_email` → appel `send_mail` Django (mock)
- [x] `DjangoBackend.send_email` avec HTML → envoi multipart
- [x] `TemplateEmailBackend.send_template_email` → render template (mock)
- [x] `SendGridBackend.send_email` → appel API SendGrid (mock `requests.post`)
- [x] `SendGridBackend` init sans API key → gestion gracieuse
- [x] `get_email_backend()` selon `TENXYTE_EMAIL_BACKEND` setting

### Fichier : `tests/unit/test_sms_backends.py` [NEW]

`backends/sms.py` — coverage actuel **100%** (était 49%)

- [x] Backend console SMS → log sans exception
- [x] Backend Twilio (mock) → envoi OK
- [x] Twilio → erreur API → log erreur, retour `False`
- [x] `get_sms_backend()` factory

---

## Phase 4 : Edge Cases & Règles de sécurité (Done - 100%)

- [x] **AuthService : Limites & Appareils** (Done - 100%)
  - Fichier cible : `tenxyte/services/auth_service.py` (méthodes spécifiques)
  - Tests :
    - [x] `_enforce_session_limit` : comportement normal et de purge (zombies).
    - [x] `_enforce_device_limit` : matching exact, fallback, et actions (`deny`, `notify`).
    - [x] `_check_new_device_alert` : génération des `AuditLog` pour appareils inconnus.
    - [x] `logout_all_devices` : révocation de tous les tokens et logs.

- [x] **Security Middlewares** (Done - 100%)
  - Fichier cible : `tenxyte/middleware.py`
  - Tests :
    - [x] `CORSMiddleware` : vérification preflight `OPTIONS` et headers injectés selon les settings.
    - [x] `ApplicationAuthMiddleware` : comportement des `TENXYTE_EXEMPT_PATHS` (prefix et exact).

- [x] **Throttles & Limites de requêtes** (Done - 100%)
  - Fichier cible : `tenxyte/throttles.py`
  - Tests :
    - [x] Extraction de l'IP du client (`get_client_ip` avec proxy).
    - [x] `ProgressiveLoginThrottle` : cache dynamique exponentiel (record_failure).
    - [x] `SimpleThrottleRule` : résolution des chemins exacts et préfixes.

---

## Phase 5 : Google OAuth & Management Command (Done - 100%)

> **Gain estimé : +2–3 pts → ~92%**

### Fichier cible : `tests/unit/test_google_auth_service.py` [NEW]

`services/google_auth_service.py` — coverage **100%**

> Toutes les méthodes dépendant de `requests` ou `google.oauth2` sont mockées.

- [x] `verify_id_token` → token valide → retourne user info
- [x] `verify_id_token` → exception/invalide → retourne `None`
- [x] `exchange_code_for_tokens` → code valide → dict tokens
- [x] `exchange_code_for_tokens` → statut non-200 ou erreur → `None`
- [x] `get_user_info` → access_token valide → user info / échec → `None`
- [x] `authenticate_with_google` → utilisateur existant → login OK
- [x] `authenticate_with_google` → email existant → liaison google_id
- [x] `authenticate_with_google` → nouvel utilisateur → création + rôle par défaut
- [x] `authenticate_with_google` → compte inactif → erreur
- [x] `authenticate_with_google` → compte verrouillé → erreur

### Fichier cible : `tests/unit/test_management_commands.py` [NEW]

`management/commands/tenxyte_cleanup.py` — coverage **100%**

- [x] Commande s'exécute sans exception (`call_command`)
- [x] Tokens expirés (Refresh, Blacklist) nettoyés
- [x] OTP expirés ou utilisés nettoyés
- [x] LoginAttempts anciens nettoyés selon flag
- [x] AuditLogs anciens nettoyés ou évités avec `--audit-log-days=0`
- [x] `--dry-run` ne supprime aucune donnée

---

## Commande de vérification (après chaque phase)

```bash
pytest tests/ --cov=src/tenxyte --cov-report=term-missing
```

> **Objectif final : ≥ 90% de coverage global**
