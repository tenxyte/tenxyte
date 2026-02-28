# Tenxyte — Code Quality & Attack Surface Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit en profondeur de la qualité du code et de la surface d'attaque du
> package Tenxyte.
> **Date** : 2026-02-27
> **Version auditée** : `0.9.1.7`

---

## 1. Métriques de qualité du code

### Outils de qualité configurés

| Outil | Configuration | Seuil |
|-------|-------------|-------|
| **pytest** | `pyproject.toml [tool.pytest.ini_options]` | Coverage ≥ 60% |
| **pytest-cov** | HTML + terminal report | `--cov-fail-under=60` |
| **Black** | line-length 120, Python 3.10+ | Formatage automatique |
| **Ruff** | line-length 120, target py310 | Linting rapide |
| **mypy** | ≥ 1.0 | Typage statique |

### Typage statique (mypy)

Le codebase utilise des **type hints** Python partout dans les services et certains
modèles, mais leur couverture est **partielle** :

- **Services** : signatures de retour typées (`Tuple[bool, Optional[Dict], str]`)
- **Modèles** : partiellement typés
- **Views** : peu typées (DRF gère son propre système de types)
- **Décorateurs** : `@wraps` utilisé systématiquement (bonne pratique)

### Couverture de tests

| Catégorie | Fichiers | Tests |
|-----------|---------|-------|
| `tests/unit/` | ~60 fichiers | Services, vues, modèles, serializers |
| `tests/integration/` | 4 fichiers | Tenant isolation, agent workflow, auth |
| `tests/security/` | 2 fichiers | Tests d'attaque explicites |
| `tests/multidb/` | ~7 fichiers | PostgreSQL, MySQL, MongoDB |
| **Seuil minimum** | — | **60% de coverage** |

---

## 2. Surface d'attaque — Points d'entrée

### 2.1 Headers HTTP parsés (vecteurs d'injection)

| Header | Utilisé par | Validation |
|--------|------------|-----------|
| `Authorization: Bearer <jwt>` | `JWTAuthentication`, `require_jwt` | `PyJWT.decode()` — signé HS256 |
| `Authorization: AgentBearer <token>` | `AgentTokenMiddleware` | Lookup DB + validation état |
| `X-Access-Key` | `ApplicationAuthMiddleware` | Lookup DB par clé exacte |
| `X-Access-Secret` | `ApplicationAuthMiddleware` | `bcrypt.checkpw()` |
| `X-Org-Slug` | `OrganizationContextMiddleware` | Lookup DB + `is_active` |
| `X-Forwarded-For` | `IPBasedThrottle`, `decorators.get_client_ip()` | `split(',')[0]` — **non validé** |
| `X-Action-Confirmation` | `require_agent_clearance` (HITL) | Lookup DB par token |
| `HTTP_USER_AGENT` | `device_info.py`, `AuditLog` | Tronqué à 500 chars, stocké brut |

> **⚠️ Risque `X-Forwarded-For`** : deux implémentations différentes existent :
> - `IPBasedThrottle` : `request.META.get('HTTP_X_FORWARDED_FOR')` → `split(',')[0]`
> - `decorators.py get_client_ip()` : même pattern
> - `account_deletion_views.py _get_client_ip()` : même pattern
>
> Sans liste de proxies de confiance configurée (`TRUSTED_PROXIES`), un attaquant
> peut forger cette valeur pour bypasser le rate limiting basé sur l'IP.
> **C'est un vecteur d'attaque classique contre les systèmes de rate limiting.**

### 2.2 Corps de requête (JSON body — points d'entrée)

| Endpoint | Champs pris en compte | Validation |
|---------|----------------------|-----------|
| `POST /register/` | `email`, `password`, `password_confirm`, `first_name`, `last_name`, `phone_*` | Serializer DRF |
| `POST /login/email/` | `email`, `password`, `totp_code` | Serializer DRF |
| `POST /login/phone/` | `phone_country_code`, `phone_number`, `password` | Serializer DRF |
| `POST /social/<provider>/` | Dépend du provider (code/token) | Serializer + appel API externe |
| `POST /otp/request/` | `otp_type` | Enum validation |
| `POST /otp/verify/email/` | `code` (6 chiffres) | Hash comparaison |
| `POST /password/reset/confirm/` | `token`, `new_password` | Serializer DRF |
| `POST /password/change/` | `old_password`, `new_password` | bcrypt verify |
| `POST /2fa/confirm/` | `totp_code` (6 chiffres) | RFC 6238 |
| `POST /magic-link/verify/` | `token` | Hash SHA-256 |
| `POST /webauthn/register/complete/` | JSON WebAuthn assertion | `py_webauthn.verify_*()` |
| `POST /ai/tokens/` | `agent_id`, `granted_permissions`, `expires_at`, `heartbeat_*`, `budget_*` | Serializer DRF |
| `POST /request-account-deletion/` | `password`, `otp_code`, `reason` | Serializer + bcrypt |
| `POST /export-user-data/` | `password` | bcrypt verify |
| `POST /confirm-account-deletion/` | `token` | Lookup DB direct |

### 2.3 Paramètres URL (path parameters)

| Pattern | Paramètre | Risque |
|---------|----------|--------|
| `/permissions/<str:permission_id>/` | `permission_id` | Objet non trouvé → 404 géré |
| `/roles/<str:role_id>/` | `role_id` | Idem |
| `/users/<str:user_id>/roles/` | `user_id` | Vérifier autorisation is_staff |
| `/applications/<str:app_id>/` | `app_id` | Idem |
| `/ai/tokens/<int:pk>/` | `pk` (int) | DRF gère la conversion |
| `/ai/pending-actions/<str:token>/confirm/` | `token` (opaque) | Lookup DB |
| `/social/<str:provider>/` | `provider` | Whitelist via `PROVIDER_REGISTRY` |
| `/admin/users/<str:user_id>/ban/` | `user_id` | Droit is_staff requis |
| `/webauthn/credentials/<int:credential_id>/` | `credential_id` | Filtrage par `user=request.user` |

---

## 3. Système de décorateurs — Couche d'accès

**Fichier :** `src/tenxyte/decorators.py` (704 lignes)

### Inventaire des décorateurs

| Décorateur | Type | Niveau |
|-----------|------|--------|
| `@require_jwt` | Auth | JWT valide + user actif + non verrouillé |
| `@require_verified_email` | Auth | require_jwt + email vérifié |
| `@require_verified_phone` | Auth | require_jwt + téléphone vérifié |
| `@rate_limit(max, window)` | Rate | Cache Django (IP ou user_id) |
| `@require_role(code)` | RBAC | require_jwt + rôle exact |
| `@require_any_role([codes])` | RBAC | require_jwt + un des rôles |
| `@require_all_roles([codes])` | RBAC | require_jwt + tous les rôles |
| `@require_permission(code)` | RBAC | require_jwt + permission exacte |
| `@require_any_permission([codes])` | RBAC | require_jwt + une des permissions |
| `@require_all_permissions([codes])` | RBAC | require_jwt + toutes les permissions |
| `@require_org_context` | Org | Header X-Org-Slug présent |
| `@require_org_membership` | Org | require_org_context + membre actif |
| `@require_org_role(code)` | Org | require_org_context + rôle org |
| `@require_org_permission(code)` | Org | require_org_context + permission org |
| `@require_org_owner` | Org | Shortcut require_org_role('owner') |
| `@require_org_admin` | Org | owner OU admin (avec héritage) |
| `@require_agent_clearance(perm, hitl)` | AIRS | Double passe RBAC agent + HITL |

### Vecteur : bypass JWT via `TENXYTE_JWT_AUTH_ENABLED = False`

```python
# decorators.py ligne 63
if not auth_settings.JWT_AUTH_ENABLED:
    request.user = None      # ⚠️ user = None !
    request.jwt_payload = None
    return _call_view(...)   # Vue appelée sans auth
```

> **Risque critique** : si `TENXYTE_JWT_AUTH_ENABLED = False` est activé en
> production (documenté comme "DANGEROUS — for testing only"), **toutes les
> vues protégées par `@require_jwt` deviennent accessibles sans token** et avec
> `request.user = None`. Les vues qui ne vérifient pas `request.user is None`
> pourraient crasher ou fournir un accès non autorisé. L'auditeur doit vérifier
> que ce flag n'est jamais activé en production.

---

## 4. Surface d'attaque — Vecteurs connus testés

### 4.1 Tests de sécurité existants (`tests/security/test_security.py`)

Le fichier contient 751 lignes organisées en **9 classes de tests** couvrant :

| Classe | Attaques testées |
|--------|-----------------|
| `TestJWTSecurity` | Token modifié (tampering), mauvaise clé de signature (wrong secret), token expiré, attaque `alg:none`, token blacklisté, chaîne aléatoire, Bearer vide |
| `TestApplicationAuthSecurity` | Credentials absents, access_key invalide, bonne clé+mauvais secret, application inactive |
| `TestBruteForceProtection` | Multiples tentatives échouées, compte verrouillé, verrouillage expiré |
| `TestInjectionProtection` | SQL injection dans email, SQL injection dans password, XSS dans inscription, XSS dans profil |
| `TestUnauthenticatedAccess` | Accès /me/, /password/change/, /otp/request/, /2fa/status/, /me/roles/ sans JWT |
| `TestRefreshTokenSecurity` | Refresh token révoqué, faux refresh token, logout invalide le token |
| `TestCrossApplicationSecurity` | Token app A utilisé avec credentials app B |
| `TestPasswordResetSecurity` | Email inexistant (pas de fuite d'info — 200 OK), format email invalide |
| `TestAccountBanningSecurity` | Token valide d'un utilisateur banni, login banni, tokens post-ban, ban persistant après unlock, audit logs ban/unban |

### 4.2 Tests de sécurité MANQUANTS identifiés

| Vecteur | Risque | Absent de la suite |
|---------|--------|-------------------|
| **Mass assignment** via `/me/` PATCH (champs `is_staff`, `is_banned`, `is_superuser`) | Élévation de privilèges | ✅ À vérifier |
| **IDOR (Insecure Direct Object Reference)** sur `/users/<id>/` | Accès aux données d'autres users | ✅ À vérifier |
| **Race condition** sur `OTPCode.verify()` | Double vérification simultanée | ✅ À vérifier |
| **Forced browsing** des chemins admin sans `is_staff` | Escalade horizontale | ✅ À vérifier |
| **HTTP method override** (POST → PUT via header) | Contournement method check | ✅ À vérifier |
| **DoS par mot de passe long** (> 128 chars — mais validé) | CPU bcrypt | Partiellement protégé |
| **Content-Type manipulation** (non-JSON vers endpoints JSON) | Parser confusion | ✅ À vérifier |
| **CSRF** (si cookies sont utilisés avec le frontend) | Session hijacking | N/A si pure API |
| **Timing attack sur `access_secret`** | Bypass auth app | Mitigé par bcrypt |
| **JWT `kid` injection** | RCE si parsing custom du `kid` | Non applicable (pas de kid) |

---

## 5. Validation des entrées

### 5.1 Validation des mots de passe

**Fichier :** `src/tenxyte/validators.py`

La validation est **multi-couche avec score** :

```
Longueur 8–128 chars     → rejet immédiat si hors plage
Majuscule                → score +1
Minuscule                → score +1
Chiffre                  → score +1
Caractère spécial        → score +1
≥ 5 caractères uniques   → score +1
Pas de séquence (4+)     → score +1 (qwerty, 1234, abcd…)
Pas dans blacklist ~70   → score +1
Pas d'email/username     → score +1
Pas de répétition (3+)   → score +1
                         ────────────
                         Score 0–10 | Seuil configurable
```

**Longueur max à 128 chars** : protection contre les attaques DoS via bcrypt
(bcrypt prend O(n) pour des strings très longues).

### 5.2 Validation des emails

Délégué aux **serializers DRF** (`EmailField`) et validateur Django natif
(`EmailValidator`). Pas de normalisation custom systématique — `.lower()` 
appliqué dans `AuthService.authenticate_by_email()` et `register_user()`.

> **Point de vérification** : s'assurer que les emails dans la table `users` sont
> toujours stockés en minuscules. La recherche utilise `email__iexact=email` ce
> qui est correct mais peut causer des incohérences si un email en majuscules
> a été inséré directement en DB.

### 5.3 Validation des paramètres URL

Les `<str:id>` dans les URLs Django ne filtrent pas les caractères spéciaux par
défaut. L'auditeur doit vérifier que les vues correspondantes traitent ces
paramètres via l'ORM Django (qui paramétrise les requêtes SQL) et ne les
interpolent pas dans des chaînes SQL brutes.

---

## 6. Gestion des erreurs et fuite d'informations

### 6.1 Comportements intentionnels anti-énumération

| Situation | Réponse | Code |
|-----------|---------|------|
| Email inexistant au reset password | `200 OK` | Anti-enumération email |
| access_key invalide | `401 + code: APP_AUTH_INVALID` | Pas de distinction clé/secret |
| User non trouvé au login | `401 + "Invalid credentials"` | Même message que mauvais MDP |
| Token de confirmation GDPR invalide | `404` | Pas de détail |

### 6.2 Fuites d'information potentielles

| Source | Information potentiellement fuite |
|--------|----------------------------------|
| `require_role` erreur : `"Role required: <role_code>"` | Révèle le code exact du rôle attendu |
| `require_permission` erreur : `"Permission required: <code>"` | Révèle la permission attendue |
| `require_org_role` erreur : `"Organization role "<code>" required"` | Révèle le rôle org |
| Réponses 400/422 des serializers DRF | Détails des champs invalides (comportement DRF standard) |
| `agenttoken.agent_id` dans AuditLog (si accessible) | Identifiant de l'agent IA |

### 6.3 Gestion des exceptions

Les services retournent systématiquement des tuples `(bool, data, error_string)`
— les exceptions ne remontent pas au niveau des vues. Le pattern est :

```python
try:
    result = operation()
    return True, result, ''
except SomeException as e:
    logger.error(f"Error: {e}")
    return False, None, str(e)  # ⚠️ str(e) peut exposer des détails de l'erreur
```

> **Risque** : `str(e)` retourné dans certaines réponses API peut exposer des
> messages d'exception système (noms de tables, messages d'erreur DB, chemins
> de fichiers). L'auditeur devra vérifier les cas où `error` est directement
> retourné dans la réponse HTTP.

---

## 7. Injection et sécurité ORM

### 7.1 Résistance à l'injection SQL

**Django ORM** paramétrise automatiquement toutes les requêtes construites via
les méthodes `.filter()`, `.get()`, `.create()`. Aucun `raw()` ou `cursor.execute()`
n'a été identifié dans le codebase principal.

**Tests d'injection présents :**
- 4 payloads SQL dans le champ `email` de login
- 3 payloads SQL dans le champ `password`
- Résultat attendu : 401 ou 429, jamais 500

### 7.2 Résistance XSS

Tenxyte est une **API REST pure JSON** — pas de templates HTML serveurs (sauf
emails). Les données utilisateur sont stockées telles quelles (pas d'échappement
HTML côté serveur, ce qui est correct pour une API JSON pure).

**Risque** : si l'intégrateur utilise les données Tenxyte dans un contexte HTML
sans échappement, les données stockées (`first_name`, `last_name` contenant
`<script>alert(1)</script>`) deviendraient du XSS stocké. Ce n'est pas un
problème de Tenxyte mais de l'application hôte.

**Test présent :** `TestInjectionProtection.test_xss_in_user_profile()` vérifie
que les payloads XSS sont stockés **en texte brut** (pas exécutés côté serveur).

---

## 8. Gestion des secrets et de la configuration

### 8.1 Secrets dans le code source

Grep de l'ensemble du codebase — **aucune valeur sensible en dur** identifiée.
Tous les secrets sont lus depuis `settings.py` via `django.conf.settings` :

- `settings.GOOGLE_CLIENT_ID/SECRET`
- `settings.GITHUB_CLIENT_ID/SECRET`
- `settings.MICROSOFT_CLIENT_ID/SECRET`
- `settings.FACEBOOK_APP_ID/SECRET`
- `settings.TENXYTE_JWT_SECRET_KEY` (fallback sur `SECRET_KEY`)
- `settings.TWILIO_ACCOUNT_SID/AUTH_TOKEN`
- `settings.SENDGRID_API_KEY`

### 8.2 Flags de désactivation dangereux

Plusieurs flags permettent de **désactiver des protections de sécurité** —
documentés comme "dev only" mais nécessitent une vérification stricte en prod :

| Flag | Effet si désactivé | Commentaire code |
|------|--------------------|-----------------|
| `TENXYTE_JWT_AUTH_ENABLED = False` | Toutes les vues `@require_jwt` accessibles sans token | `# DANGEROUS` |
| `TENXYTE_RATE_LIMITING_ENABLED = False` | Rate limiting désactivé partout | `# Skip rate limiting if disabled` |
| `TENXYTE_APPLICATION_AUTH_ENABLED = False` | Première couche d'auth bypassée | Configurable |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False` | Pas de verrouillage après N échecs | Configurable |

> **Recommandation de l'auditeur** : vérifier que ces flags ne peuvent pas être
> influencés par des variables d'environnement non sanitisées ou des fichiers
> de config de développement commitées par erreur.

---

## 9. Dépendances et supply chain

### Dépendances directes — Analyse de risque

| Package | Version min | CVE connus | Notes |
|---------|------------|------------|-------|
| `Django` | ≥ 5.0 | ✅ Actives LTS | Mise à jour critique suivre django-security |
| `djangorestframework` | ≥ 3.14 | ✅ Maintenu | Processus de release sûr |
| `PyJWT` | ≥ 2.8 | Historique vulnérabilités `alg:none` — **corrigé dans v2** | Vérifier que les versions < 2.0 ne sont pas installées |
| `bcrypt` | ≥ 4.0 | ✅ Sûr | Dépendance C (cffi) — auditer la build |
| `pyotp` | ≥ 2.9 | ✅ Sûr | Pure Python |
| `qrcode[pil]` | ≥ 8.0 | `Pillow` : historique de vulnérabilités | Vérifier la version de Pillow effectivement installée |
| `google-auth` | ≥ 2.20 | ✅ Maintenu | |
| `google-auth-oauthlib` | ≥ 1.0 | ✅ Maintenu | |
| `requests` | Transitif | ✅ Maintenu | Utilisé dans `social_auth_service.py` |

### Dépendances optionnelles — Risque

| Package | Risque spécifique |
|---------|------------------|
| `twilio ≥ 9.0` | Large surface : client HTTP tiers pour SMS |
| `sendgrid ≥ 6.10` | Envoie des emails — données personnelles en transit |
| `django-mongodb-backend ≥ 5.0` | Backend expérimental — moins audité que psycopg2 |
| `py_webauthn` (non listé dans pyproject.toml, import lazily) | **Version non contrainte** — risque de régression |

> **Risque `py_webauthn`** : la dépendance WebAuthn est importée via
> `_get_webauthn()` (lazy import) sans pinning de version dans `pyproject.toml`.
> Une mise à jour majeure cassante de `py_webauthn` ne serait pas détectée par
> les contraintes de version.

### Outils de vérification recommandés

```bash
# Vérification des CVE dans les dépendances
pip audit
safety check

# Analyse statique de sécurité
bandit -r src/tenxyte/
semgrep --config "p/python" src/tenxyte/

# Dépendances transitives
pip-audit --requirement requirements.txt
```

---

## 10. Patterns de code à auditer en priorité

### 10.1 Comparaisons à temps constant

| Emplacement | Comparaison | Temps constant ? |
|------------|------------|-----------------|
| `application.verify_secret()` | bcrypt.checkpw | ✅ (bcrypt est constant) |
| `OTPCode.verify()` | `self.code == self._hash_code(code)` | ❌ Python `==` sur strings |
| `WebAuthnChallenge.is_valid()` | Comparaison directe | ✅ (géré par py_webauthn) |
| `BackupCode` dans `verify_backup_code()` | `code_hash in user.backup_codes` | ❌ Python `in` sur liste |
| `MagicLinkToken.get_valid()` | Lookup DB par hash | ✅ (DB fait la comparaison) |

> **Risque timing attack sur OTP/backup codes** : bien que les codes OTP soient
> générés aléatoirement et à durée de vie courte (limitant l'utilité d'une
> attaque timing), l'auditeur devrait recommander `hmac.compare_digest()` à la
> place de `==` pour toute comparaison de valeurs sensibles.

### 10.2 Récursion et boucles potentiellement infinies

```python
# models/organization.py — hiérarchie d'organisations
# get_parent_chain() / has_parent() → potentiellement récursif
# Protégé par ORG_MAX_DEPTH = 5 (configurable)
```

> **Risque** : si `ORG_MAX_DEPTH` est élevé et que la hiérarchie est profonde,
> les requêtes traversant la hiérarchie (pour la résolution de rôles RBAC)
> peuvent générer **N requêtes DB** (N = profondeur). Risque N+1 queries.

### 10.3 Champs JSONField avec données arbitraires

| Champ | Modèle | Risque |
|-------|--------|--------|
| `audit_logs.details` | `AuditLog` | Contenu libre — peut contenir des PII si mal utilisé |
| `agent_pending_actions.payload` | `AgentPendingAction` | Payload brut de la requête agent — potentiellement sensible |
| `users.backup_codes` | `User` | Liste de hashs SHA-256 — correct |

### 10.4 Imports lazy et dépendances circulaires

```python
# Patterns d'imports dans les décorateurs et services
from .conf import org_settings           # Dans les fonctions wrapper
from tenxyte.services.agent_service import AgentTokenService  # Lazy dans décorateur
from .services.email_service import EmailService              # Lazy dans models/gdpr.py
```

Ces imports lazys évitent les dépendances circulaires mais peuvent masquer des
erreurs d'import jusqu'à l'exécution (pas détectées par mypy sans configuration).

---

## 11. Points de configuration impactant la surface d'attaque

```python
# settings.py — variables influençant la surface d'attaque

# Désactivation de protections (⚠️ UNIQUEMENT DEV)
TENXYTE_JWT_AUTH_ENABLED = False          # Bypass toute auth JWT
TENXYTE_RATE_LIMITING_ENABLED = False     # Désactive rate limiting
TENXYTE_APPLICATION_AUTH_ENABLED = False  # Désactive couche 1 auth

# Chemins exemptés de l'auth applicative
TENXYTE_EXEMPT_PATHS = ['/admin/', '/health/', '/docs/']
TENXYTE_EXACT_EXEMPT_PATHS = ['/']

# Throttle rules custom (élargit la surface d'entrée)
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/search/': '1000/hour',  # Risque si trop libéral
}

# Providers OAuth activés (réduit la surface si restreint)
TENXYTE_SOCIAL_PROVIDERS = ['google']  # Réduire à necessaire

# CORS (risque élevé si mal configuré)
TENXYTE_CORS_ALLOW_ALL_ORIGINS = True   # ⚠️ DANGEROUS en prod

# AIRS actions nécessitant confirmation humaine
TENXYTE_AIRS_CONFIRMATION_REQUIRED = ['payments.create', 'users.delete']
```

---

## 12. Résumé des risques par catégorie

### Risques critiques à vérifier

| # | Risque | Localisation | Sévérité |
|---|--------|-------------|---------|
| 1 | `X-Forwarded-For` non validé → bypass rate limiting | `throttles.py`, `decorators.py` | Haute |
| 2 | `TENXYTE_JWT_AUTH_ENABLED = False` → accès sans auth | `decorators.py:63` | Critique (si prod) |
| 3 | `TENXYTE_CORS_ALLOW_ALL_ORIGINS` → CORS ouvert | `middleware.py`, `conf.py` | Haute |
| 4 | Comparaisons OTP/backup codes sans `hmac.compare_digest` | `operational.py`, `totp_service.py` | Faible-Moyenne |
| 5 | N+1 queries sur la hiérarchie d'organisations RBAC | `organization.py` | Faible (perf) |
| 6 | `py_webauthn` sans version contrainte | `pyproject.toml` | Moyenne |
| 7 | `str(e)` retourné dans certaines réponses d'erreur | `services/*.py` | Faible |
| 8 | Fusion automatique de comptes OAuth par email | `social_auth_service.py` | Moyenne |

### Ce qui est bien géré

| Protection | Mécanisme |
|-----------|-----------|
| SQL injection | ORM Django paramétré exclusivement |
| JWT forgery (`alg:none`) | `algorithms=[self.algorithm]` whitelist explicite |
| Token bruteforce | CSPRNG + 256–512 bits d'entropie |
| Credential stuffing | Rate limiting multi-niveaux + verrouillage compte |
| Token reuse après logout | Blacklist JTI + révocation refresh token |
| Cross-app token usage | Vérification `app_id` dans le token vs header |
| Password spraying | Progressive throttle exponentiel |
| AIRS privilege escalation | Double passe RBAC (token AND utilisateur actuel) |
| Timing attack sur app secret | bcrypt (comparaison en temps constant nativement) |
| Account enumeration | Réponses uniformes (200 OK sur email inexistant) |

---

## 13. SAST — Static Application Security Testing

> La section 9 mentionnait `bandit` et `semgrep` comme outils. Cette section
> détaille les patterns dangereux recherchés, les résultats attendus, et
> les intégrations CI/CD recommandées.

### 13.1 Patterns dangereux — inventaire dans le codebase

| Pattern | Présence dans Tenxyte | Verdict |
|---------|----------------------|---------|
| `eval()` | ❌ Absent | ✅ Sûr |
| `exec()` | ❌ Absent | ✅ Sûr |
| `compile()` | ❌ Absent | ✅ Sûr |
| `__import__()` dynamique | ❌ Absent | ✅ Sûr |
| `pickle.loads()` / `pickle.load()` | ❌ Absent | ✅ Sûr |
| `yaml.load()` sans `Loader=` | ❌ Absent | ✅ Sûr |
| `subprocess.call()` / `os.system()` | ❌ Absent | ✅ Sûr |
| `open(user_input)` (path traversal) | ❌ Absent | ✅ Sûr |
| `tempfile.mktemp()` (race condition) | ❌ Absent | ✅ Sûr |
| `hashlib.md5()` / `hashlib.sha1()` sans `usedforsecurity=False` | `breach_check_service.py` — SHA-1 pour HIBP | ⚠️ Connu et intentionnel (protocole k-anonymity) |
| `random.random()` pour secrets | ❌ Absent — `secrets.token_urlsafe()` utilisé partout | ✅ Sûr |
| `assert` pour validation de sécurité | À vérifier dans les tests | ✅ Acceptable dans les tests |
| `DEBUG = True` hardcodé | ❌ Absent dans le package | ✅ Sûr |
| `ALLOWED_HOSTS = ['*']` | ❌ Absent dans le package | ✅ Sûr |

### 13.2 Commandes SAST à exécuter

```bash
# 1. Bandit — analyse de sécurité Python
bandit -r src/tenxyte/ \
  -f json \
  -o bandit_report.json \
  --severity-level medium \
  --confidence-level medium

# Afficher uniquement les erreurs sans le code source
bandit -r src/tenxyte/ -ll -ii

# 2. Semgrep — règles Django + Python sécurité
semgrep --config "p/python" \
        --config "p/django" \
        --config "p/secrets" \
        src/tenxyte/ \
        --json \
        --output semgrep_report.json

# Règles spécifiques à l'injection
semgrep --config "p/sql-injection" src/tenxyte/

# 3. Flake8 avec plugins sécurité
pip install flake8 flake8-bandit flake8-bugbear
flake8 src/tenxyte/ --select=S,B

# 4. Vérification SHA-1 (HIBP — intentionnel)
grep -r "sha1\|md5" src/tenxyte/ --include="*.py"
# → Résultat attendu : breach_check_service.py uniquement
```

### 13.3 Intégration CI/CD recommandée

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Bandit SAST
        run: |
          pip install bandit
          bandit -r src/tenxyte/ -f json -o bandit.json -ll
        continue-on-error: false

      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/python
            p/django
            p/secrets

      - name: pip-audit
        run: |
          pip install pip-audit
          pip-audit --fail-on-severity high
```

### 13.4 Résultats attendus de bandit sur Tenxyte

| Règle Bandit | Résultat attendu | Justification |
|-------------|-----------------|---------------|
| `B303` (MD5/SHA1 dangereux) | ⚠️ Faux positif sur `breach_check_service.py` | SHA-1 pour k-anonymity HIBP — intentionnel |
| `B324` (hashlib insecure) | ⚠️ Même cas | Idem |
| `B105–B107` (passwords hardcodés) | ✅ 0 résultat | Aucun secret en dur |
| `B110` (try/except/pass) | ⚠️ Possible | Patterns try/except dans services |
| `B506` (yaml.load) | ✅ 0 résultat | yaml non utilisé |
| `B403/B301` (pickle/marshal) | ✅ 0 résultat | Non utilisé |
| `B608` (SQL injection) | ✅ 0 résultat | ORM exclusif |

---

## 14. Audit des logs et de l'observabilité

> Un système d'authentification doit logger **les bons événements** sans jamais
> logger de données sensibles (mots de passe, tokens, clés JWT).

### 14.1 Ce que Tenxyte logue (AuditLog — données métier)

Le modèle `AuditLog` trace les événements de sécurité critiques :

| Événement | Action loggée | Données sensibles dans les logs ? |
|-----------|--------------|----------------------------------|
| Connexion réussie | `login` | IP, user_agent, device — ✅ PAS de token |
| Connexion échouée | `login_failed` | IP, user_agent — ✅ PAS de password |
| Changement mot de passe | `password_change` | IP — ✅ PAS de hash/ancien mot de passe |
| Activation 2FA | `2fa_enabled` | IP — ✅ PAS de totp_secret |
| Reset mot de passe | `password_reset_request` + `complete` | IP — ✅ PAS du token OTP |
| Session révoquée | (via refresh token revocation) | ⚠️ Non directement tracé en AuditLog |
| Déconnexion | `logout` / `logout_all` | IP — ✅ Safe |
| Token régénéré (app) | `app_credentials_regenerated` | ✅ PAS du nouveau secret |

### 14.2 Ce que Tenxyte logue (logger Python — logs techniques)

```python
# Pattern identifié dans les services (ex: services/auth_service.py)
import logging
logger = logging.getLogger(__name__)

# Pattern typique — RISQUE : str(e) peut exposer des détails internes
except SomeException as e:
    logger.error(f"Error: {e}")          # ⚠️ message d'exception en clair
    return False, None, str(e)
```

| Information loggée | Sûr ? | Recommandation |
|-------------------|-------|----------------|
| Messages d'exception `str(e)` | ⚠️ Dépend | Peut contenir des paths, noms de tables, données partielles |
| Stack traces (`exc_info=True`) | ✅ Techniques seulement | Acceptable côté serveur si logs sécurisés |
| IP addresses dans les services | ✅ Opérationnel | Acceptable |
| Headers HTTP dans les logs | ✅ Non loggués directement | Vérifier la config du serveur WSGI |

### 14.3 Ce qui ne doit JAMAIS apparaître dans les logs

| Donnée | Présence dans les logs Tenxyte |
|--------|-------------------------------|
| Mots de passe en clair | ❌ Absent — jamais loggué |
| Tokens JWT complets | ❌ Absent — jamais loggués |
| Refresh tokens | ❌ Absent — jamais loggués |
| Secrets TOTP | ❌ Absent — jamais loggué |
| `X-Access-Secret` header | ❌ Absent — jamais loggué |
| Codes OTP en clair | ❌ — stockés/comparés via hash uniquement |
| Clés API OAuth | ❌ Absent — jamais loggués |

### 14.4 Lacunes d'observabilité identifiées

| Lacune | Impact opérationnel | Recommandation |
|--------|--------------------|----|
| **No real-time alerting** | Les intrusions ne déclenchent aucune alerte | Intégrer un webhook signaux Django sur AuditLog |
| **Révocation de sessions non tracée** dans AuditLog | Impossible de savoir si une session spécifique a été révoquée | Ajouter action `session_revoked` dans AuditLog |
| **`logger.error(str(e))`** peut exposer des détails | Message d'exception potentiellement sensible dans les logs applicatifs | Remplacer par `logger.error("msg", exc_info=True)` |
| **Pas de corrélation request_id** | Impossible de tracer une requête de bout en bout | Ajouter `X-Request-ID` header et le propager dans les logs |
| **Circuit breaker AIRS non tracé en AuditLog** | Les suspensions d'agents ne sont pas dans l'historique d'audit | Ajouter log dans `circuit_breaker.trigger()` |

### 14.5 Checklist observabilité pour l'auditeur

- [ ] Le WSGI/ASGI server (Gunicorn, uvicorn) logue-t-il le header `Authorization` ? → RISQUE si oui
- [ ] Les logs Django (`django.request`) incluent-ils les corps de requêtes ? → RISQUE si oui
- [ ] Les logs sont-ils centralisés (ELK, Datadog, CloudWatch) avec accès restreint ?
- [ ] La rétention des logs applicatifs est-elle définie (distincte des AuditLog) ?
- [ ] `TENXYTE_AUDIT_LOGGING_ENABLED = True` en production ?
- [ ] Les actions `login_failed` déclenchent-elles une alerte après N échecs consécutifs ?

---

## 15. Audit des API REST

> Vérification de la cohérence de l'exposition des endpoints : codes HTTP,
> verbosité des erreurs, timings uniformes.

### 15.1 Cohérence des codes HTTP retournés

| Situation | Code attendu | Code Tenxyte | Commentaire |
|-----------|-------------|-------------|-------------|
| JWT absent ou invalide | `401` | `401` | ✅ Correct |
| JWT valide mais rôle insuffisant | `403` | `403` | ✅ Correct — `@require_role` retourne 403 |
| JWT valide mais permission insuffisante | `403` | `403` | ✅ Correct |
| Application non authentifiée (X-Access-Key absent) | `401` | `401` | ✅ Correct |
| Ressource non trouvée (404) | `404` | `404` | ✅ Correct — DRF gère |
| Rate limit dépassé | `429` | `429` | ✅ Correct — DRF throttle |
| Validation échouée (mauvais format) | `400` | `400` | ✅ Correct — Serializer DRF |
| Tentative de login sur compte banni | `403` | `403` | ✅ Correct — distinct du 401 |
| Tentative de login sur compte verrouillé | `403` | `403` | ✅ Correct |
| Opération admin sans `is_staff` | `403` | `403` | ✅ Correct |
| Email inexistant au reset password (anti-énumération) | `200` | `200 OK` | ✅ Intentionnel |

> **Point positif** : la distinction `401` (non authentifié) vs `403` (authentifié
> mais non autorisé) est correctement implémentée dans Tenxyte, conformément à la
> sémantique HTTP/RFC 9110.

### 15.2 Verbosité des messages d'erreur — analyse

| Endpoint | Message d'erreur retourné | Risque d'énumération |
|---------|--------------------------|---------------------|
| `POST /login/email/` avec email inexistant | `{"error": "Invalid credentials"}` | ✅ Aucun — même que mauvais MDP |
| `POST /login/email/` avec mauvais MDP | `{"error": "Invalid credentials"}` | ✅ Aucun |
| `POST /password/reset/request/` email inexistant | `200 OK {"message": "If this email exists..."}` | ✅ Anti-énumération |
| `POST /register/` avec email déjà utilisé | `400 + {"email": ["...already exists"]}` | ⚠️ Révèle qu'un email existe |
| `@require_role` échoue | `{"error": "Role required: <role_code>"}` | ⚠️ Révèle le code du rôle attendu |
| `@require_permission` échoue | `{"error": "Permission required: <code>"}` | ⚠️ Révèle la permission attendue |
| `ApplicationAuthMiddleware` invalide | `{"error": "APP_AUTH_INVALID"}` | ✅ Aucune distinction clé/secret |
| `X-Org-Slug` inconnu | `{"error": "Organization not found"}` | ⚠️ Confirme qu'un org-slug n'existe pas |

### 15.3 Timings uniformes — analyse des risques d'énumération temporelle

| Opération | Timing variable ? | Risque |
|-----------|-----------------|--------|
| Login email — user inexistant vs mauvais MDP | ⚠️ **OUI** — bcrypt uniquement si user trouvé | Timing attack possible pour énumérer les emails |
| Login email — compte actif vs banni | ⚠️ Légèrement variable | Très faible (banni vérifié après bcrypt) |
| Magic link request — email existant vs inexistant | ⚠️ Potentiellement variable (envoi email) | Dépend du backend email |
| Reset password — même réponse 200 OK | ✅ Intentionnel mais timing d'envoi email variable | Voir note ci-dessous |

> **⚠️ Risque timing attack sur l'email de login** :
> Si l'email n'existe pas → `User.objects.get()` lève `DoesNotExist` → retour **sans bcrypt**.
> Si l'email existe mais mot de passe incorrect → `check_password()` → **bcrypt s'exécute** (~100ms).
> Un attaquant peut mesurer le temps de réponse pour déterminer si un email est enregistré.
>
> **Mitigations possibles** :
> ```python
> # Option A : exécuter bcrypt même si user non trouvé (dummy hash)
> if not user:
>     bcrypt.checkpw(b"dummy", DUMMY_HASH)  # Constant time
>     return False, None, "Invalid credentials"
>
> # Option B : délai artificiel uniforme
> time.sleep(max(0, TARGET_DELAY - elapsed))
> ```

### 15.4 Exposition des endpoints sensibles — surface de reconnaissance

| Information exposable | Via quel endpoint | Protection |
|----------------------|------------------|------------|
| Liste des rôles RBAC existants | `GET /roles/` | `is_staff` requis |
| Liste des permissions | `GET /permissions/` | `is_staff` requis |
| Liste des utilisateurs | `GET /admin/users/` | `is_staff` requis |
| Format exact des erreurs de validation | Tout endpoint `POST` (DRF) | Inévitable mais utile pour les intégrateurs |
| Statut d'une application (active/inactive) | Réponse 401 si inactive | Confirme que la clé existe |

### 15.5 Checklist REST API pour l'auditeur

- [ ] `401` vs `403` : vérifier la distinction pour tous les endpoints
- [ ] Timing attack login : mesurer le temps de réponse avec email existant vs inexistant
- [ ] Le message d'erreur de `POST /register/` révèle-t-il qu'un email est pris ?
- [ ] Les messages `"Role required: <code>"` sont-ils acceptables pour l'intégrateur ?
- [ ] Les réponses d'erreur DRF standard sont-elles filtrées avant d'atteindre les clients ?
- [ ] Y a-t-il un endpoint de healthcheck qui expose des informations système ?
- [ ] Les réponses `OPTIONS` CORS révèlent-elles les méthodes et headers acceptés ?

