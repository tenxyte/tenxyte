# Tenxyte — Security Strategy

> **Audience** : équipe de développement, développeurs intégrant Tenxyte.
> **Niveau de détail** : architecture et principes. Aucun secret, clé ou valeur
> sensible n'est divulgué dans ce document.
> **Dernière mise à jour** : 2026-02-27

---

## Vue d'ensemble

Tenxyte est un **package Django d'authentification multi-tenant** conçu selon le
principe de **défense en profondeur** (*Defense in Depth*) : plusieurs couches
de sécurité indépendantes coopèrent de telle sorte que la compromission d'une
seule couche n'entraîne pas la compromission du système entier.

Le schéma global du pipeline de sécurité sur chaque requête HTTP est :

```
Requête HTTP
     │
     ▼
[1] CORSMiddleware             — Contrôle de l'origine (Cross-Origin)
     │
     ▼
[2] SecurityHeadersMiddleware  — Injection des headers de sécurité HTTP
     │
     ▼
[3] ApplicationAuthMiddleware  — Authentification de l'application (X-Access-Key)
     │
     ▼
[4] OrganizationContextMiddleware — Isolation multi-tenant (X-Org-Slug)
     │
     ▼
[5] AgentTokenMiddleware       — Authentification AIRS (AgentBearer token)
     │
     ▼
[6] PIIRedactionMiddleware     — Masquage des données PII pour les agents IA
     │
     ▼
[7] JWTAuthentication (DRF)    — Authentification de l'utilisateur (Bearer JWT)
     │
     ▼
[8] Rate Limiting (Throttles)  — Protection brute-force et abus
     │
     ▼
[9] RBAC / Permissions         — Contrôle d'accès basé sur les rôles
     │
     ▼
  Logique métier (Views / Services)
```

---

## 1. Configuration et presets de sécurité (`conf.py`)

### Principe

Toutes les variables de configuration de sécurité sont centralisées dans
`tenxyte.conf.TenxyteSettings`. Elles sont résolues selon l'ordre de priorité :

1. **`TENXYTE_<NOM>` explicite dans `settings.py`** — priorité absolue
2. **Preset `TENXYTE_SHORTCUT_SECURE_MODE`** — valeurs groupées par profil
3. **Valeur par défaut de `conf.py`**

### Presets disponibles

| Preset    | Destination                        | JWT access | Lockout | Audit | Breach check |
|-----------|------------------------------------|------------|---------|-------|--------------|
| `starter` | Prototype, dev local               | 1h         | 10 err  | ❌    | ❌           |
| `medium`  | SaaS B2C, production standard      | 15 min     | 5 err   | ✅    | ✅           |
| `robust`  | Fintech, santé, données sensibles  | 5 min      | 3 err   | ✅    | ✅ + reject  |

> **Règle clé** : les secrets (`JWT_SECRET_KEY`, clés OAuth, tokens Twilio…) ne
> font **jamais** partie des presets — ils doivent toujours être définis
> manuellement dans `settings.py` (idéalement injectés via des variables
> d'environnement ou un gestionnaire de secrets).

---

## 2. Couche 1 — CORS (`CORSMiddleware`)

**Fichier :** `src/tenxyte/middleware.py`

### Rôle

Contrôle quelles **origines frontend** sont autorisées à communiquer avec l'API.
Protège contre les attaques **Cross-Site Request Forgery (CSRF)** côté navigateur.

### Comportement

- Désactivé par défaut (`TENXYTE_CORS_ENABLED = False`) — à activer en production.
- Gère les requêtes **preflight OPTIONS** (renvoie 200 sans passer dans la chaîne
  d'authentification).
- Ajoute les headers `Access-Control-Allow-Origin`, `Vary: Origin`, etc.

### Paramètres clés

| Paramètre                       | Défaut  | Rôle |
|---------------------------------|---------|------|
| `TENXYTE_CORS_ENABLED`          | `False` | Active le middleware |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS`| `False` | ⚠️ Dangereux en prod |
| `TENXYTE_CORS_ALLOWED_ORIGINS`  | `[]`    | Liste blanche d'origines |
| `TENXYTE_CORS_ALLOW_CREDENTIALS`| `True`  | Autorise les cookies / Authorization |
| `TENXYTE_CORS_MAX_AGE`          | 86400   | Cache du preflight (1 jour) |

### Recommandation

En production, définir explicitement `TENXYTE_CORS_ALLOWED_ORIGINS` avec la
liste des domaines frontend. Ne jamais activer `CORS_ALLOW_ALL_ORIGINS = True`
en production.

---

## 3. Couche 2 — Headers HTTP de sécurité (`SecurityHeadersMiddleware`)

**Fichier :** `src/tenxyte/middleware.py`

### Rôle

Injecte des **headers HTTP de sécurité** sur chaque réponse pour protéger les
navigateurs contre les attaques courantes.

### Headers par défaut

| Header                    | Valeur par défaut                      | Protection |
|---------------------------|----------------------------------------|------------|
| `X-Content-Type-Options`  | `nosniff`                              | MIME-sniffing |
| `X-Frame-Options`         | `DENY`                                 | Clickjacking |
| `X-XSS-Protection`        | `1; mode=block`                        | XSS legacy |
| `Referrer-Policy`         | `strict-origin-when-cross-origin`      | Fuite d'URL |

### Personnalisation

```python
# settings.py
TENXYTE_SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'",
}
```

> **Recommandation** : ajouter `Strict-Transport-Security` (HSTS) et une
> `Content-Security-Policy` adaptée à votre frontend en production.

---

## 4. Couche 3 — Authentification applicative (`ApplicationAuthMiddleware`)

**Fichier :** `src/tenxyte/middleware.py`

### Rôle

Première couche d'identité : valide que la **requête provient bien d'une
application enregistrée** (mobile, web, serveur tiers) et non d'un acteur
inconnu.

### Mécanisme

Deux headers HTTP sont requis sur chaque requête :

- `X-Access-Key` — identifiant public de l'application
- `X-Access-Secret` — secret hashé de l'application

Le secret est comparé via `application.verify_secret()` qui effectue une
comparaison **à temps constant** (bcrypt) pour empêcher les attaques temporelles.

### Modèle `Application`

Le modèle stocke :
- L'`access_key` (UUID public, stocké en clair)
- L'`access_secret` (hashé, jamais stocké en clair)
- Le flag `is_active` (désactiver = couper immédiatement l'accès)

### Chemins exemptés

Certains chemins bypassent volontairement cette couche :

- **Prefix match** : `/admin/`, `{API_PREFIX}/health/`, `{API_PREFIX}/docs/`
- **Match exact** : `{API_PREFIX}/`

Configurable via `TENXYTE_EXEMPT_PATHS` et `TENXYTE_EXACT_EXEMPT_PATHS`.

### Désactivation

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # ⚠️ Dev uniquement
```

---

## 5. Couche 4 — Isolation multi-tenant (`OrganizationContextMiddleware`)

**Fichiers :** `src/tenxyte/middleware.py`, `src/tenxyte/tenant_context.py`

### Rôle

Garantit l'**isolation stricte des données entre organisations** (tenants) dans
une architecture multi-tenant. C'est l'implémentation du *Hard Multi-Tenancy*.

### Mécanisme

1. Le client inclut le header `X-Org-Slug` dans chaque requête.
2. Le middleware résout l'organisation correspondante et s'assure qu'elle est
   `is_active = True`.
3. L'organisation est stockée dans une **Context Variable Python** (module
   `contextvars`), en dehors du thread global, pour éviter toute contamination
   entre requêtes concurrentes.
4. **Nettoyage garanti** : le bloc `finally` réinitialise le contexte à `None`
   en fin de requête, même en cas d'exception, pour éviter une fuite de contexte
   si le thread est réutilisé.

### Variables de contexte

```python
# tenxyte/tenant_context.py
_current_organization: ContextVar[Optional[Any]]  # Org active
_bypass_tenant_filtering: ContextVar[bool]         # Bypass admin (usage interne seulement)
```

> **Point de sécurité critique** : le bypass de filtrage tenant ne doit être
> activé que dans du code d'administration interne supervisé, jamais exposé à
> une API publique.

---

## 6. Couche 5 — Authentification AIRS / Agents IA (`AgentTokenMiddleware`)

**Fichiers :** `src/tenxyte/middleware.py`, `src/tenxyte/services/agent_service.py`

### Rôle

Module **AIRS** (Agent Interaction & Restriction System) : permet à des agents IA
autonomes d'agir au nom d'un utilisateur humain avec des permissions **explicitement
limitées** et sous supervision.

### Mécanisme d'authentification

Le header `Authorization: AgentBearer <token>` déclenche cette couche.

Le service `AgentTokenService.validate()` vérifie successivement :

1. **Existence** du token en base de données
2. **Statut** `ACTIVE` (pas `REVOKED`, `SUSPENDED`, `EXPIRED`)
3. **Expiration** explicite (`expires_at`)
4. **Dead Man's Switch** : si configuré, vérifie que le token a reçu un
   heartbeat assez récemment

### Contrôle des permissions : double passe RBAC

La validation des permissions d'un agent suit deux vérifications indépendantes :

1. **Scope du token** : la permission demandée est-elle dans la liste
   `granted_permissions` du token ?
2. **Permissions actuelles de l'humain** : l'utilisateur délégant
   possède-t-il *encore* cette permission ? (Changement de rôle post-création
   du token pris en compte en temps réel.)

> **Principe de moindre privilège** : un agent ne peut jamais avoir plus de
> permissions que l'humain qui l'a créé. Les permissions déléguées sont un
> sous-ensemble strict.

### Circuit Breaker

Mécanisme de suspension automatique si l'agent dépasse des seuils :

| Seuil                    | Action si dépassé            |
|--------------------------|------------------------------|
| `max_requests_per_minute`| Suspension `RATE_LIMIT`      |
| `max_requests_total`     | Suspension `RATE_LIMIT`      |
| `max_failed_requests`    | Suspension `ANOMALY`         |
| `budget_limit_usd`       | Suspension `BUDGET_EXCEEDED` |

Le compteur de requêtes par minute utilise le **cache Django** (Redis recommandé)
avec une incrémentation atomique pour éviter les race conditions.

### Audit automatique des mutations

Chaque action `POST/PUT/PATCH/DELETE` réussie par un agent est enregistrée dans
`AuditLog` avec :
- L'endpoint appelé
- La méthode HTTP
- L'`agent_id` (identifiant de l'agent IA)
- Le `prompt_trace_id` (traçabilité de la chaîne de pensée LLM)
- Le statut HTTP de la réponse

### Human-In-The-Loop (HITL)

Pour les actions nécessitant une approbation humaine, le service crée un
`AgentPendingAction` avec :
- Un `confirmation_token` cryptographiquement aléatoire (`secrets.token_urlsafe(64)`)
- Une expiration de 10 minutes par défaut
- Le payload complet de l'action à confirmer

L'humain confirme ou refuse via un endpoint dédié.

---

## 7. Couche 6 — Masquage PII (`PIIRedactionMiddleware`)

**Fichier :** `src/tenxyte/middleware.py`

### Rôle

Protège les **données à caractère personnel** (PII) en les masquant
automatiquement dans les réponses JSON lorsque la requête provient d'un agent IA.

### Champs masqués

```
email, phone, ssn, date_of_birth, address,
credit_card, password, totp_secret, backup_codes
```

### Comportement

- Actif uniquement si `TENXYTE_AIRS_REDACT_PII = True` **et** que la requête
  est authentifiée via `AgentToken`.
- Remplacement récursif dans l'arbre JSON (objets imbriqués et listes inclus).
- Valeur de remplacement : `"***REDACTED***"`.

---

## 8. Authentification JWT (`JWTAuthentication` + `JWTService`)

**Fichiers :** `src/tenxyte/authentication.py`, `src/tenxyte/services/jwt_service.py`

### Structure du token

Chaque access token JWT contient :

| Claim     | Description |
|-----------|-------------|
| `type`    | `"access"` |
| `jti`     | JWT ID unique (UUID v4) — utilisé pour le blacklisting |
| `user_id` | ID de l'utilisateur |
| `app_id`  | ID de l'application (lien avec la couche 3) |
| `iat`     | Issued At |
| `exp`     | Expiration |
| `nbf`     | Not Before |

### Validation au decode

La méthode `decode_token()` impose les claims requis :
`exp`, `iat`, `user_id`, `app_id` — un token sans ces claims est rejeté.

### Blacklist de tokens

À chaque logout (ou révocation de compte), le `jti` du token est ajouté à la
table `BlacklistedToken`. À chaque requête, le token décodé est vérifié contre
cette liste.

- Les entrées expirées sont nettoyables via `BlacklistedToken.cleanup_expired()`
  (tâche périodique recommandée avec Celery).

### Rotation des refresh tokens

Configurable via `TENXYTE_REFRESH_TOKEN_ROTATION`. Si activé, l'ancien refresh
token est invalidé lors du renouvellement, limitant la fenêtre d'exploitation en
cas de vol de token.

### Vérifications à l'authentification

Après décodage du token, `JWTAuthentication.authenticate()` vérifie :

1. `user.is_active` — compte actif
2. `user.is_account_locked()` — compte non verrouillé (temporaire)
3. `user.is_account_banned()` — compte non banni (permanent)
4. Cohérence `app_id` ↔ application rattachée à la requête

### Durées de vie recommandées

| Profil    | Access token | Refresh token |
|-----------|-------------|---------------|
| `starter` | 1 heure     | 30 jours      |
| `medium`  | 15 minutes  | 7 jours       |
| `robust`  | 5 minutes   | 1 jour        |

---

## 9. Gestion des mots de passe

### 9.1 Hachage (`AbstractUser`)

**Fichier :** `src/tenxyte/models/auth.py`

Tenxyte utilise **bcrypt** (via la librairie `bcrypt`) pour hacher les mots de
passe, avec un sel aléatoire généré automatiquement (`bcrypt.gensalt()`).

```python
def set_password(self, raw_password: str):
    self.password = bcrypt.hashpw(
        raw_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
```

> Bcrypt est conçu pour être intentionnellement lent, ce qui rend les attaques
> par force brute sur les hashs volés très coûteuses.

### 9.2 Validation (`PasswordValidator`)

**Fichier :** `src/tenxyte/validators.py`

Vérifications cumulées avec un système de **score 0–100** :

| Règle | Description |
|-------|-------------|
| Longueur minimale | Configurable (défaut : 8 ; `robust` recommande 12+) |
| Longueur maximale | 128 caractères pour prévenir les DoS |
| Majuscule requise | `TENXYTE_PASSWORD_REQUIRE_UPPERCASE` |
| Minuscule requise | `TENXYTE_PASSWORD_REQUIRE_LOWERCASE` |
| Chiffre requis | `TENXYTE_PASSWORD_REQUIRE_DIGIT` |
| Caractère spécial | `TENXYTE_PASSWORD_REQUIRE_SPECIAL` |
| Caractères uniques | Min. 5 caractères distincts |
| Mot de passe courant | Blacklist de ~70 mots de passe très communs |
| Séquences prévisibles | Détection de `1234`, `abcd`, `qwerty`… (4+ chars) |
| Inclusion email/username | Le mot de passe ne doit pas contenir l'identifiant |
| Répétitions | Pas plus de 3 caractères identiques consécutifs |

### 9.3 Historique des mots de passe (`PasswordHistory`)

**Fichier :** `src/tenxyte/models/security.py`

Empêche la réutilisation des N derniers mots de passe. Les anciens hashs sont
stockés en bcrypt et comparés lors d'un changement.

- `TENXYTE_PASSWORD_HISTORY_ENABLED` (défaut `True`)
- `TENXYTE_PASSWORD_HISTORY_COUNT` (défaut `5`)

### 9.4 Vérification de base de données de fuites (`BreachCheckService`)

**Fichier :** `src/tenxyte/services/breach_check_service.py`

Intégration avec l'API **HaveIBeenPwned (HIBP)** via le principe de
**k-anonymity** :

1. SHA-1 du mot de passe calculé localement.
2. Seuls les **5 premiers caractères** du hash sont envoyés à l'API HIBP.
3. L'API retourne tous les suffixes correspondants (plusieurs centaines).
4. La comparaison du suffixe complet est faite **localement**.
5. **Le mot de passe en clair ne quitte jamais le serveur.**

Si le mot de passe est trouvé dans des fuites :
- `TENXYTE_BREACH_CHECK_REJECT = True` → refus avec message explicite.
- `TENXYTE_BREACH_CHECK_REJECT = False` → avertissement dans les logs uniquement.

Un timeout de 5 secondes est appliqué : une indisponibilité de l'API HIBP ne
bloque pas l'inscription.

---

## 10. Authentification à deux facteurs (2FA)

### 10.1 TOTP (`TOTPService`)

**Fichier :** `src/tenxyte/services/totp_service.py`

Standard **RFC 6238 (TOTP)** via la librarie `pyotp`.

- Secret généré aléatoirement (base32, compatible Google Authenticator, Authy,
  Microsoft Authenticator…).
- QR code généré en base64 (jamais stocké, affiché une seule fois).
- Fenêtre de validité configurable (`TENXYTE_TOTP_VALID_WINDOW = 1` période de 30s).

**Codes de secours :**
- Générés avec `secrets.token_hex()` (cryptographiquement aléatoire).
- Stockés hashés via SHA-256.
- Affichés en clair *une seule fois* à l'utilisateur lors de l'activation.
- Consommés à l'usage (chaque code ne peut être utilisé qu'une fois).

### 10.2 OTP par email / SMS (`OTPService`)

**Fichier :** `src/tenxyte/services/otp_service.py`

Codes à usage unique pour :
- Vérification d'email (15 min de validité)
- Vérification de téléphone (10 min de validité)
- Réinitialisation de mot de passe (15 min de validité)

Protections :
- Les anciens codes non utilisés sont invalidés lors d'une nouvelle génération.
- Compteur de tentatives avec blocage après `TENXYTE_OTP_MAX_ATTEMPTS` essais.
- Réponse explicite du nombre de tentatives restantes.

---

## 11. Rate Limiting (`throttles.py`)

**Fichier :** `src/tenxyte/throttles.py`

### Principe

Toutes les classes de throttling héritent de `IPBasedThrottle` qui résout l'IP
réelle du client en prenant en compte les proxies (`HTTP_X_FORWARDED_FOR`).

### Throttles spécifiques

| Classe | Scope | Limite | Cible |
|--------|-------|--------|-------|
| `LoginThrottle` | `login` | 5/min | Brute force login |
| `LoginHourlyThrottle` | `login_hourly` | 20/h | Brute force login persistant |
| `RegisterThrottle` | `register` | 3/h | Spam d'inscriptions |
| `RegisterDailyThrottle` | `register_daily` | 10/j | Spam d'inscriptions journalier |
| `PasswordResetThrottle` | `password_reset` | 3/h | Spam reset password |
| `PasswordResetDailyThrottle` | `password_reset_daily` | 10/j | Spam reset journalier |
| `OTPRequestThrottle` | `otp_request` | 5/h | Spam d'envoi d'OTP |
| `OTPVerifyThrottle` | `otp_verify` | 5/min | Brute force OTP |
| `RefreshTokenThrottle` | `refresh` | 30/min | Refresh tokens |
| `MagicLinkRequestThrottle` | `magic_link_request` | 3/h | Spam magic links |
| `MagicLinkVerifyThrottle` | `magic_link_verify` | 10/min | Brute force magic link |

### Throttle progressif (`ProgressiveLoginThrottle`)

En cas d'échecs répétés, le délai de blocage augmente **exponentiellement** :

```
timeout = min(60 × 2^n_failures, 3600)  # Max 1 heure
```

Où `n_failures` est le nombre cumulé d'échecs pour cette IP (stocké en cache).
Le compteur est réinitialisé après un login réussi.

### Règles dynamiques (`SimpleThrottleRule`)

Permet de throttler n'importe quelle route via la configuration :

```python
# settings.py
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/products/': '100/hour',
    '/api/v1/search/': '30/min',
    '/api/v1/upload/': '5/hour',
    '/api/v1/health/$': '60/min',  # $ = match exact
}
```

---

## 12. Verrouillage de compte

**Fichier :** `src/tenxyte/models/auth.py`

### Verrouillage temporaire

Après `TENXYTE_MAX_LOGIN_ATTEMPTS` échecs consécutifs, le compte est verrouillé
pendant `TENXYTE_LOCKOUT_DURATION_MINUTES` minutes.

```python
def is_account_locked(self) -> bool:
    if not self.is_locked:
        return False
    if self.locked_until and timezone.now() > self.locked_until:
        self.unlock_account()  # Déverrouillage automatique
        return False
    return True
```

Le déverrouillage est **automatique** (vérification à chaque tentative) — aucune
intervention manuelle requise pour les verrous temporaires.

### Bannissement permanent

`is_banned = True` est une action **manuelle d'administration** irréversible via
`user.is_account_banned()`. Le JWT d'un utilisateur banni est rejeté même s'il
est cryptographiquement valide.

---

## 13. RBAC — Contrôle d'accès basé sur les rôles

**Fichier :** `src/tenxyte/models/auth.py`

### Modèle

```
Utilisateur
  ├── Rôles (ManyToMany)
  │     └── Permissions (ManyToMany)
  └── Permissions directes (ManyToMany)
```

### Permissions hiérarchiques

Une permission peut avoir une **permission parente**. Posséder une permission
parente octroie implicitement toutes ses permissions enfants.

```
invoices            ← parente
  ├── invoices.read
  ├── invoices.create
  └── invoices.delete
```

### Permissions dans le contexte organisationnel

En mode multi-tenant, les permissions sont vérifiées au niveau de
l'organisation (via le membership) avec support de l'héritage dans la hiérarchie
d'organisations (`ORG_ROLE_INHERITANCE`).

---

## 14. Gestion des sessions et des devices

### Limites de sessions concurrentes

- `TENXYTE_SESSION_LIMIT_ENABLED` (défaut `True`)
- `TENXYTE_DEFAULT_MAX_SESSIONS` (défaut `1`)
- `TENXYTE_DEFAULT_SESSION_LIMIT_ACTION` : `"deny"` ou `"revoke_oldest"`

La valeur `max_sessions` est surchargeable par utilisateur en base.

### Limites de devices

- `TENXYTE_DEVICE_LIMIT_ENABLED` (défaut `True`)
- `TENXYTE_DEFAULT_MAX_DEVICES` (défaut `1`)
- `TENXYTE_DEVICE_LIMIT_ACTION` : `"deny"` ou `"revoke_oldest"`

Les dépassements de devices sont tracés dans `AuditLog` avec l'action
`device_limit_exceeded`.

---

## 15. Journal d'audit (`AuditLog`)

**Fichier :** `src/tenxyte/models/security.py`

Chaque action sensible génère une entrée traçable dans la table `audit_logs` :

**Actions tracées :**

| Catégorie          | Exemples |
|--------------------|----------|
| Authentification   | `login`, `login_failed`, `logout`, `logout_all`, `token_refresh` |
| Mots de passe      | `password_change`, `password_reset_request`, `password_reset_complete` |
| 2FA                | `2fa_enabled`, `2fa_disabled`, `2fa_backup_used` |
| Compte             | `account_created`, `account_locked`, `email_verified`, `phone_verified` |
| RBAC               | `role_assigned`, `role_removed`, `permission_changed` |
| Applications       | `app_created`, `app_credentials_regenerated` |
| Sécurité           | `suspicious_activity`, `session_limit_exceeded`, `new_device_detected` |
| AIRS               | `agent_action` |

**Données enregistrées :**
- IP de la requête
- User-Agent (tronqué à 500 chars)
- Timestamp
- Payload JSON contextuel (`details`)
- Références vers l'agent IA et l'humain délégant (contexte AIRS)
- `prompt_trace_id` pour la traçabilité LLM

---

## 16. Conformité RGPD — Soft Delete

**Fichier :** `src/tenxyte/models/auth.py`

La suppression d'un compte est implémentée en **soft delete** : les données PII
sont anonymisées mais les entrées `AuditLog` sont préservées pour la conformité.

```python
def soft_delete(self, generate_token=True):
    # Anonymisation des données personnelles
    self.email = f"deleted_{self.id}@deleted.local"
    self.first_name = ""
    self.last_name = ""
    self.phone_country_code = None
    self.phone_number = None
    self.google_id = None
    self.totp_secret = None
    self.backup_codes = []
    self.is_2fa_enabled = False
    # Désactivation du compte
    self.is_deleted = True
    self.deleted_at = timezone.now()
    self.is_active = False
    self.is_staff = False
    self.is_superuser = False
    self.save()
```

Un `anonymization_token` est généré pour permettre l'identification du compte
anonymisé à des fins d'audit sans exposer les données personnelles.

---

## 17. Authentification passwordless

### Magic Link

**Fichier :** `src/tenxyte/services/magic_link_service.py`

- Token cryptographiquement aléatoire à usage unique.
- Expire après `TENXYTE_MAGIC_LINK_EXPIRY_MINUTES` minutes (défaut : 15).
- Désactivé dans le preset `robust` (vecteur d'attaque potentiel via compromission
  de boîte mail).

### WebAuthn / FIDO2 (Passkeys)

**Fichier :** `src/tenxyte/services/webauthn_service.py`

- Authentification biométrique/hardware sans mot de passe.
- Challenge à usage unique expirant en `TENXYTE_WEBAUTHN_CHALLENGE_EXPIRY_SECONDS`
  secondes (défaut : 300s).
- Recommandé dans le preset `robust`.

---

## 18. OAuth Social (Multi-provider)

**Fichier :** `src/tenxyte/services/social_auth_service.py`

Providers supportés : Google, GitHub, Microsoft, Facebook.

**Sécurité :**
- Vérification des tokens OAuth côté serveur (pas de trust côté client).
- Fusion automatique avec un compte existant si l'email correspond.
- Les secrets OAuth (`CLIENT_ID`, `CLIENT_SECRET`) sont **toujours** configurés
  manuellement — jamais dans les presets.

---

## 19. Gestion sécurisée des credentials applicatifs

**Fichier :** `src/tenxyte/models/application.py`

- L'`access_key` est un identifiant public (UUID).
- L'`access_secret` est un secret haché en bcrypt.
- La régénération des credentials crée un nouveau secret et invalide l'ancien
  immédiatement — tracé dans `AuditLog` avec l'action `app_credentials_regenerated`.

---

## 20. Recommandations de déploiement

| Domaine | Recommandation |
|---------|---------------|
| **JWT** | Utiliser une clé secrète dédiée (`TENXYTE_JWT_SECRET_KEY`), distincte de `SECRET_KEY` Django |
| **Cache** | Utiliser Redis pour le rate limiting et le circuit breaker AIRS (pas MemCache en prod) |
| **HTTPS** | Toujours déployer derrière HTTPS ; ajouter HSTS dans `TENXYTE_SECURITY_HEADERS` |
| **Secrets** | Injecter les secrets via variables d'environnement ou gestionnaire de secrets (Vault, AWS SSM…) |
| **Audit** | Archiver `AuditLog` régulièrement ; créer des alertes sur `suspicious_activity` |
| **Blacklist** | Planifier `BlacklistedToken.cleanup_expired()` périodiquement (tâche Celery) |
| **Preset** | Démarrer avec `medium`, passer à `robust` pour les données sensibles |
| **CORS** | Ne jamais configurer `CORS_ALLOW_ALL_ORIGINS = True` en production |
| **BREACH_CHECK** | Activer avec `BREACH_CHECK_REJECT = True` en production |
| **AIRS** | Toujours définir des `granted_permissions` explicites ; activer le circuit breaker |

---

*Ce document est destiné à la documentation interne. Il décrit la conception
et les mécanismes sans divulguer de valeurs sensibles, clés cryptographiques
ou détails permettant de contourner la sécurité.*
