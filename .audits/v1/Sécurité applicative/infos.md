# Tenxyte — Sécurité Applicative Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit en profondeur de la sécurité applicative de Tenxyte : OWASP Top 10,
> flux d'authentification, et configuration des en-têtes HTTP / TLS.
> **Date** : 2026-02-27 | **Version** : `0.9.1.7`

---

## PARTIE A — OWASP Top 10 (2021)

---

### A01 — Broken Access Control

**Contexte** : Tenxyte est un package d'authentification — c'est le domaine où
le risque A01 est le plus élevé.

#### Mécanismes de contrôle d'accès en place

| Mécanisme | Couche | Implémentation |
|-----------|--------|----------------|
| Application auth (X-Access-Key + Secret) | Middleware couche 1 | `ApplicationAuthMiddleware` — bcrypt |
| JWT Bearer | DRF `JWTAuthentication` + `@require_jwt` | `PyJWT.decode()` HS256 |
| RBAC roles | `@require_role`, `@require_any_role`, `@require_all_roles` | DB lookup via `user.has_role()` |
| RBAC permissions | `@require_permission`, `@require_any_permission`, `@require_all_permissions` | DB lookup via `user.has_permission()` |
| Organisation (multi-tenant) | `@require_org_context`, `@require_org_membership`, `@require_org_role` | Header `X-Org-Slug` + DB |
| AIRS Agent double-passe | `@require_agent_clearance` | Permission vérifiée sur token ET sur user |
| Admin (staff uniquement) | `IsAdminUser` DRF ou `is_staff` check | Natif DRF |

#### Points critiques A01 à vérifier

**1. IDOR potentiel sur les endpoints admin**

```
GET /admin/users/<str:user_id>/          → Vérifier que seuls les staff accèdent
GET /admin/audit-logs/<str:log_id>/      → Vérifier filtrage par user si non-staff
GET /users/<str:user_id>/roles/          → Vérifier isolation (user A ne voit pas user B)
GET /applications/<str:app_id>/          → Isolation par owner
```

**2. Mass assignment via PATCH `/me/`**

```python
# À vérifier : les champs is_staff, is_banned, is_superuser sont-ils
# explicitement exclus du serializer de mise à jour du profil ?
# Si le serializer est trop permissif, un user peut s'auto-promouvoir.
```

**3. Bypass de l'isolation multi-tenant**

```python
# OrganizationContextMiddleware : si X-Org-Slug absent → request.organization = None
# Les décorateurs @require_org_context bloquent, mais si un endpoint ne
# les utilise pas, les données peuvent être accessibles sans contexte org.
```

**4. Bypass JWT via flag de développement**

```python
# decorators.py:63 — DANGEROUS
if not auth_settings.JWT_AUTH_ENABLED:
    request.user = None   # Aucune auth requise
    return _call_view(...)
```

**5. Escalade de privilèges AIRS**

Les agents IA reçoivent un **subset** des permissions de l'humain créateur.
Vérifier que le décorateur `@require_agent_clearance` interdit bien à un agent
d'utiliser des permissions que l'humain créateur n'a pas lui-même.

---

### A02 — Cryptographic Failures

*(Voir également le document `ENCRYPTION_STRATEGY.md`)*

| Donnée | Traitement | Conforme |
|--------|-----------|---------|
| Mots de passe | bcrypt (irréversible) | ✅ |
| Secrets applicatifs | bcrypt + base64 | ✅ |
| Tokens JWT | HS256 HMAC-SHA256 | ✅ (→ RS256 si microservices) |
| OTP codes | SHA-256 (haute entropie, TTL court) | ✅ |
| Refresh tokens | En clair en DB | ⚠️ (hash SHA-256 recommandé) |
| TOTP secret | En clair en DB | ⚠️ (AES-256-GCM recommandé) |
| Agent tokens | En clair en DB (48 chars CSPRNG) | ⚠️ Acceptable, à évaluer |

**TLS** : non géré par Tenxyte — responsabilité de l'infrastructure.
L'auditeur doit vérifier la configuration TLS du serveur hôte (voir Partie C).

---

### A03 — Injection

#### SQL Injection

Tenxyte utilise **exclusivement l'ORM Django** pour toutes les requêtes DB.
Aucun `raw()`, `cursor.execute()` ou interpolation de chaîne SQL identifié.

**Tests présents :**
```python
# test_security.py — TestInjectionProtection
payloads = [
    "' OR '1'='1",
    "admin@test.com' OR 1=1--",
    "'; DROP TABLE users;--",
    "admin@test.com' UNION SELECT * FROM users--",
]
# Résultat attendu : jamais 500, jamais 200
```

#### NoSQL Injection

Non applicable — Tenxyte cible Django ORM (SQL). Le backend MongoDB
utilise `django-mongodb-backend` qui paramétrise les requêtes.

#### Command Injection

Aucun `os.system()`, `subprocess`, ou `eval()` identifié dans le codebase.
Le seul code externe est :
- `requests.get/post()` vers les APIs OAuth (URLs construites depuis des constantes)
- `requests.get()` vers `api.pwnedpasswords.com` (URL construite statiquement)

#### Template Injection

Tenxyte est une API pure JSON — pas de templates Jinja2 évaluant des inputs
utilisateur côté serveur.

---

### A04 — Insecure Design

| Risque de conception | Statut |
|---------------------|--------|
| Pas de modélisation des menaces documentée | ⚠️ Non documenté |
| Règles métier de sécurité testées automatiquement | ✅ (`tests/security/`) |
| Période de grâce pour la suppression de compte | ✅ 30 jours |
| Double confirmation pour actions irréversibles (deletion) | ✅ Email + mot de passe + 2FA |
| Limite d'organisation (ORG_MAX_DEPTH = 5, ORG_MAX_MEMBERS configurable) | ✅ |
| Budget tracking pour agents IA | ✅ |
| Audit trail pour toutes actions sensibles | ✅ |

---

### A05 — Security Misconfiguration

#### Flags de sécurité désactivables (risque élevé si prod)

| Flag | Valeur dangereuse | Effet |
|------|------------------|-------|
| `TENXYTE_JWT_AUTH_ENABLED` | `False` | Bypass totalité auth JWT |
| `TENXYTE_APPLICATION_AUTH_ENABLED` | `False` | Bypass couche 1 (X-Access-Key) |
| `TENXYTE_RATE_LIMITING_ENABLED` | `False` | Désactive rate limiting |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED` | `False` | Désactive verrouillage après échecs |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS` | `True` | CORS ouvert à tous |
| `TENXYTE_AUDIT_LOGGING_ENABLED` | `False` | Aucun audit log |
| `TENXYTE_BREACH_CHECK_ENABLED` | `False` | Pas de vérification HIBP |

#### Chemins exemptés de l'authentification applicative

Par défaut (sans configuration explicite) :
```python
EXEMPT_PATHS = ['/admin/', '/health/', '/docs/']
EXACT_EXEMPT_PATHS = ['/']
```

> L'auditeur doit vérifier que `TENXYTE_EXEMPT_PATHS` n'est pas étendu
> inconsidérément en production (ex : exclure un endpoint sensible).

#### Configuration Django admin

Le Django admin (`/admin/`) est exempté de la couche `ApplicationAuthMiddleware`
mais reste protégé par le système d'auth Django natif (session + `is_staff`).

---

### A06 — Vulnerable and Outdated Components

| Package | Version requise | Risques historiques |
|---------|----------------|---------------------|
| `Django ≥ 5.0` | LTS | Suivre la liste CVE django-security@list |
| `PyJWT ≥ 2.8` | Maintenu | `alg:none` corrigé en v2 — **whitelist d'algorithme en place** |
| `bcrypt ≥ 4.0` | Stable | Dépendance C (cffi) |
| `Pillow` (via qrcode) | **Version non contrainte** | Historique de CVEs (buffer overflow, parsing images) |
| `py_webauthn` | **Non listé dans pyproject.toml** | Version inconnue, import lazy |
| `requests` (transitif) | **Non contraint** | Généralement sûr |

**Commandes de vérification suggérées :**
```bash
pip audit                              # CVE dans toutes les dépendances installées
safety check                           # Base OSV + PyPA Advisory
pip list --outdated                    # Composants dépassés
bandit -r src/tenxyte/ -f json         # Analyse statique sécurité
```

---

### A07 — Identification and Authentication Failures

*(Section la plus critique pour Tenxyte — voir Partie B pour le détail complet)*

**Résumé des mécanismes en place :**

| Risque OWASP A07 | Mitigation Tenxyte |
|-----------------|-------------------|
| Credentials par défaut faibles | Politique de MDP configurable (score 1–10) |
| Brute force login | `LoginThrottle` 5/min + 20/h + verrouillage progressif |
| Réutilisation de credential | `PasswordHistory` + breach check HIBP |
| Mauvaise gestion des sessions | Blacklist JTI + révocation refresh tokens |
| 2FA bypassable | TOTP valide uniquement pendant `TOTP_VALID_WINDOW` (configurable) |
| Reset password exploitable | Réponse uniforme 200 + token CSPRNG 48 chars |
| Credential stuffing | Rate limiting + lockout + breach check |
| Account enumeration | Réponse identique que l'email existe ou non |

---

### A08 — Software and Data Integrity Failures

| Risque | Évaluation |
|--------|-----------|
| Intégrité des tokens JWT | Signature HS256 obligatoire — algorithme en whitelist |
| Intégrité des magic links | SHA-256 du token CSPRNG (256 bits d'entropie) |
| Intégrité de la chaîne de confirmation GDPR | Token CSPRNG 48 chars (384 bits) |
| Intégrité des agents AIRS | Token statique CSPRNG + circuit breaker |
| Intégrité des codes backup 2FA | SHA-256 hashés avant stockage |
| Supply chain (PyPI) | Non protégé par hash de dépendances (`requirements.txt` absent) |

> **Point critique** : Tenxyte ne dispose pas d'un fichier `requirements.txt`
> ou `poetry.lock` contraignant les versions exactes des dépendances transitives.
> Une attaque de supply chain (dépendance compromise) pourrait passer inaperçue.

---

### A09 — Security Logging and Monitoring Failures

**Modèle `AuditLog` :** toutes les actions sensibles sont tracées.

| Information tracée | Présence |
|-------------------|---------|
| Action (type d'événement) | ✅ |
| Utilisateur | ✅ (FK nullable) |
| Adresse IP | ✅ |
| User-Agent | ✅ (tronqué à 500 chars) |
| Application cliente | ✅ (FK nullable) |
| Agent IA | ✅ (FK nullable) |
| Délégant humain (AIRS) | ✅ `on_behalf_of` |
| Prompt trace ID | ✅ (SI fourni par l'agent) |
| Timestamp | ✅ `created_at` |
| Détails contextuels | ✅ JSONField libre |

**Lacunes à documenter :**

- ❌ **Aucune purge automatique** : les logs s'accumulent indéfiniment
- ❌ **Aucune alerte temps-réel** : pas d'intégration SIEM, webhook, ou alerting
- ❌ **Pas de log de démarrage/arrêt** du serveur (géré par l'infrastructure)
- ⚠️ `logger.error(str(e))` dans les services expose potentiellement des détails
  techniques dans les logs applicatifs (pas dans les AuditLog)

---

### A10 — Server-Side Request Forgery (SSRF)

**Appels HTTP sortants dans Tenxyte :**

| Appel | URL | Contrôle |
|-------|-----|---------|
| HIBP breach check | `api.pwnedpasswords.com/range/<5chars>` | URL statique — **pas de SSRF** |
| Google OAuth token | `oauth2.googleapis.com/token` | URL statique — **pas de SSRF** |
| Google userinfo | `www.googleapis.com/oauth2/v3/userinfo` | URL statique — **pas de SSRF** |
| GitHub user | `api.github.com/user` | URL statique — **pas de SSRF** |
| Microsoft Graph | `graph.microsoft.com/v1.0/me` | URL statique — **pas de SSRF** |
| Facebook Graph | `graph.facebook.com/me` | URL statique — **pas de SSRF** |

**Aucun cas identifié** où une URL fournie par l'utilisateur est utilisée comme
destination d'un appel HTTP côté serveur. Risque SSRF **faible**.

---

## PARTIE B — Audit des flux d'authentification

---

### B1. Flux Email + Password

```
POST /login/email/
  Headers: X-Access-Key, X-Access-Secret
  Body:    { email, password, [totp_code] }

1. ApplicationAuthMiddleware → bcrypt.checkpw(access_secret)
2. LoginThrottle (5/min/IP) + LoginHourlyThrottle (20/h/IP)
3. AuthService.authenticate_by_email()
   a. User.objects.get(email__iexact=email)
   b. check_password(password)              → bcrypt
   c. is_active check + is_banned check
   d. is_account_locked() check             → locked_until > now()
   e. LoginAttempt.create(success=False)   SI échec
   f. ProgressiveLoginThrottle.record_failure() SI échec
   g. Si 2FA enabled → TOTP.verify(totp_code)
   h. Session limits check
   i. Device limits check
   j. RefreshToken.generate()              → CSPRNG 64 chars
   k. JWTService.generate_token_pair()     → HS256 + JTI UUID
   l. AuditLog.create('login')
```

**Points à vérifier :**
- [ ] Le `totp_code` est-il vérifié **avant** de générer les tokens JWT ?
- [ ] Que se passe-t-il si `is_banned=True` mais `is_active=True` (ordre des checks) ?
- [ ] Le TOTP peut-il être rejoué (anti-replay sur le code utilisé) ?
- [ ] Le `TOTP_VALID_WINDOW` par défaut accepte-t-il des codes passés/futurs ?

### B2. Flux Magic Link (Passwordless)

```
POST /magic-link/request/
  → Token CSPRNG 32 chars généré
  → hash = SHA-256(token) stocké en DB
  → Email envoyé avec token en clair (URL = BASE_URL + "?token=<token>")
  → TTL: MAGIC_LINK_EXPIRY_MINUTES (configurable)
  → Rate limit: 3/h par IP

POST /magic-link/verify/?token=<token>
  → hash = SHA-256(token) reçu
  → MagicLinkToken.objects.get(token_hash=hash, is_used=False, expires_at > now)
  → Si trouvé : mark is_used=True, générer JWT
```

**Points à vérifier :**
- [ ] Le token est-il invalidé immédiatement après utilisation (is_used=True) ?
- [ ] Les tokens expirés sont-ils nettoyés de la DB ?
- [ ] L'email de magic link contient-il le token en query param (risque Referer header) ?
- [ ] Le compte est-il créé si l'email est inconnu, ou le flow est-il rejeté ?

### B3. Flux TOTP / 2FA

```
Activation:
  GET /2fa/setup/         → génère un secret TOTP + QR code
  POST /2fa/confirm/      → vérifie le premier code TOTP → active 2FA

Utilisation:
  POST /login/email/ + totp_code → vérifié par pyotp.TOTP(secret).verify(code, valid_window)
  
  OU backup code:
  → SHA-256(backup_code) comparé à user.backup_codes (liste)
  → Code utilisé supprimé de la liste

Désactivation:
  POST /2fa/disable/ + password + totp_code → désactive 2FA
```

**Points à vérifier :**
- [ ] Le code TOTP peut-il être **réutilisé** pendant sa fenêtre de validité ?
  → Pas d'anti-replay identifié sur la validation TOTP (juste `TOTP_VALID_WINDOW`)
- [ ] Le nombre de tentatives de code TOTP erronées est-il limité ?
- [ ] Les backup codes utilisés sont-ils bien supprimés atomiquement ?
- [ ] Le `TOTP_VALID_WINDOW` permet combien de codes simultanément valides ?

> **⚠️ Risque TOTP replay** : `pyotp.TOTP.verify(code, valid_window=1)` valide
> le code actuel + `valid_window` codes passés/futurs. Si `valid_window ≥ 1`,
> une même code peut être utilisé deux fois dans la fenêtre de 30 secondes.
> Il n'y a pas de mécanisme d'enregistrement du dernier code valide utilisé
> pour prévenir ce replay (vérification à faire dans `totp_service.py`).

### B4. Flux Refresh Token

```
POST /refresh/
  Body: { refresh_token: "<64 chars>" }

1. RefreshTokenThrottle (30/min/IP)
2. RefreshToken.objects.get(token=refresh_token, is_revoked=False, expires_at > now)
3. user.is_active check + is_banned check
4. Si REFRESH_TOKEN_ROTATION → ancien token révoqué, nouveau token émis
5. Nouveau access JWT généré (HS256 + nouveau JTI)
6. Access token précédent mis en blacklist JTI (si TOKEN_BLACKLIST_ENABLED)
```

**Points à vérifier :**
- [ ] La rotation de refresh token est-elle activée par défaut ?
  → `TENXYTE_REFRESH_TOKEN_ROTATION` — valeur par défaut à vérifier dans `conf.py`
- [ ] Si rotation désactivée, un refresh token compromis reste valide pendant toute sa TTL
- [ ] Le refresh token est stocké **en clair** en DB — si la DB est compromise,
  tous les refresh tokens actifs sont exploitables

### B5. Flux WebAuthn / Passkeys (FIDO2)

```
Enregistrement:
  POST /webauthn/register/begin/  → challenge CSPRNG stocké (TTL 5min)
  POST /webauthn/register/complete/ → py_webauthn.verify_registration_response()
                                    → clé publique stockée (PEM/DER)

Authentification:
  POST /webauthn/authenticate/begin/     → challenge CSPRNG
  POST /webauthn/authenticate/complete/  → py_webauthn.verify_authentication_response()
                                        → signature ECDSA P-256 vérifiée
                                        → JWT généré
```

**Points à vérifier :**
- [ ] Les challenges WebAuthn sont-ils invalidés après utilisation ?
- [ ] La vérification du `rpId` est-elle stricte (pas de phishing via sous-domaine) ?
- [ ] `py_webauthn` version non contrainte dans `pyproject.toml` — vérifier la version installée

### B6. Flux Social OAuth

```
POST /social/<provider>/
  Body: { id_token|access_token|code, redirect_uri }

1. Provider.verify_id_token() ou exchange_code()
2. get_user_info() → dict normalisé
3. SocialAuthService.authenticate()
   a. Cherche SocialConnection (provider + provider_user_id)
   b. Si non trouvé → cherche User par email (case-insensitive)
   c. Si non trouvé → crée User + assigne rôle par défaut
   d. Crée/met à jour SocialConnection
   e. Génère JWT
```

**Points critiques :**
- [ ] **Account takeover via email matching** : si email non vérifié chez le provider
  mais correspondant à un compte existant → fusion automatique → accès au compte
- [ ] Le token OAuth transmis (`access_token`, `id_token`) est-il validé côté serveur ?
  → Oui pour Google (`id_token.verify_oauth2_token()`) mais vérifier GitHub/Facebook

### B7. Flux Réinitialisation de mot de passe

```
POST /password/reset/request/
  Body: { email }
  → Toujours 200 OK (anti-énumération)
  → Si compte trouvé: OTPCode généré (6 digits, SHA-256 hashé, TTL 15min)
  → PasswordResetThrottle: 3/h, 10/j

POST /password/reset/confirm/
  Body: { token, new_password }
  → OTPCode vérifié par SHA-256
  → Nouveau mot de passe validé (score ≥ seuil)
  → is_used=True sur l'OTPCode
  → Tous les refresh tokens révoqués (invalidation sessions actives)
  → AuditLog créé
```

**Points à vérifier :**
- [ ] Le token de reset est-il invalidé immédiatement après usage ?
- [ ] Toutes les sessions actives sont-elles révoquées après reset ?
- [ ] Le code OTP à 6 chiffres (10^6 = 1 million de possibilités) — le rate limiting est-il suffisant ?
- [ ] Un attaquant peut-il déclencher un reset sur un email connu pour provoquer un DoS (invalidation session) ?

### B8. Flux Agents IA (AIRS)

```
Authorization: AgentBearer <48-char-token>

1. AgentTokenMiddleware → AgentTokenService.validate(raw_token)
   a. DB lookup par token brut
   b. Vérif status = ACTIVE
   c. Vérif expires_at > now
   d. Vérif heartbeat (Dead Man's Switch)
2. AgentTokenService.check_circuit_breaker(agent_token)
   a. Si erreurs/budget dépassé → suspend
3. @require_agent_clearance(permission, hitl=True/False)
   a. Vérif permission sur le token ET sur l'utilisateur
   b. Si HITL → retour 202 + confirmation_token
   c. Si HITL confirmé (X-Action-Confirmation header) → exécution

Human-in-the-Loop:
POST /ai/pending-actions/<token>/confirm/
  → markaction confirmed → exécution décalée
POST /ai/pending-actions/<token>/deny/
  → mark action denied
```

**Points à vérifier :**
- [ ] Le `confirmation_token` HITL est-il à usage unique ?
- [ ] Y a-t-il un TTL sur les `AgentPendingAction` (expiration des confirmations) ?
- [ ] Un agent peut-il créer d'autres agents ? (vérifier `@require_agent_clearance` sur `/ai/tokens/`)
- [ ] L'agent hérite-t-il des permissions de l'humain ou peut-il en avoir plus ?

---

## PARTIE C — En-têtes HTTP et Configuration TLS

---

### C1. En-têtes de sécurité — `SecurityHeadersMiddleware`

**Fichier :** `src/tenxyte/middleware.py` (lignes 159–193)

Le middleware injecte les headers configurés via `TENXYTE_SECURITY_HEADERS`.

#### Headers par défaut (conf.py)

```python
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}
```

#### Analyse des headers par défaut

| Header | Valeur par défaut | Évaluation | Recommandation |
|--------|-----------------|------------|----------------|
| `X-Content-Type-Options` | `nosniff` | ✅ Correct | — |
| `X-Frame-Options` | `DENY` | ✅ Correct | — |
| `X-XSS-Protection` | `1; mode=block` | ⚠️ Obsolète | Ce header est déprécié par les navigateurs modernes. Utiliser CSP à la place. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | ✅ Correct | — |

#### Headers de sécurité ABSENTS par défaut

| Header manquant | Risque | Valeur recommandée |
|----------------|--------|-------------------|
| `Strict-Transport-Security` | HTTP downgrade, MitM | `max-age=31536000; includeSubDomains; preload` |
| `Content-Security-Policy` | XSS (même si API JSON) | `default-src 'none'; frame-ancestors 'none'` |
| `Permissions-Policy` | Accès aux APIs navigateur | `camera=(), microphone=(), geolocation=()` |
| `Cross-Origin-Resource-Policy` | Leakage de réponses cross-origin | `same-origin` |
| `Cross-Origin-Opener-Policy` | Side-channel attacks | `same-origin` |

> **Note** : `Strict-Transport-Security` est **personnalisable** via
> `TENXYTE_SECURITY_HEADERS` mais **non inclus par défaut**. L'intégrateur
> peut l'ajouter manuellement — mais il aurait dû être inclus par défaut
> pour une API d'authentification.

#### Configuration recommandée pour production

```python
TENXYTE_SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    # Supprimer X-XSS-Protection (obsolète)
}
```

### C2. Configuration CORS — `CORSMiddleware`

**Fichier :** `src/tenxyte/middleware.py` (lignes 97–156)

```python
response['Access-Control-Allow-Origin'] = origin   # Toujours l'origin exact, pas '*'
response['Vary'] = 'Origin'                         # Correct (nécessaire pour caching)
# Si CORS_ALLOW_CREDENTIALS → Access-Control-Allow-Credentials: true
# Access-Control-Max-Age → durée de cache du preflight
```

#### Configuration CORS par défaut (conf.py)

| Paramètre | Défaut | Risque |
|-----------|--------|--------|
| `CORS_ENABLED` | `False` (désactivé) | N/A si désactivé |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | ✅ Sûr |
| `CORS_ALLOWED_ORIGINS` | `[]` | À remplir |
| `CORS_ALLOW_CREDENTIALS` | `False` | ✅ Sûr par défaut |
| `CORS_ALLOWED_METHODS` | `['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']` | ✅ Standard |
| `CORS_ALLOWED_HEADERS` | `['Content-Type', 'Authorization', 'X-Access-Key', 'X-Access-Secret', 'X-Org-Slug', 'X-Prompt-Trace-ID', 'X-Action-Confirmation']` | ✅ Précis |

> **Risque si `CORS_ALLOW_ALL_ORIGINS = True`** : autorise n'importe quel
> domaine à envoyer des requêtes authentifiées. Si combiné avec
> `CORS_ALLOW_CREDENTIALS = True` → attaque CSRF/CORS aggravée.

#### Points à vérifier

- [ ] `CORS_ALLOW_ALL_ORIGINS = False` en production
- [ ] `CORS_ALLOWED_ORIGINS` contient uniquement les domaines légitimes
- [ ] `CORS_ALLOW_CREDENTIALS = False` sauf si nécessaire
- [ ] Le middleware maison CORS est utilisé **OU** `django-cors-headers` (ne pas avoir les deux)

### C3. Configuration TLS (responsabilité de l'intégrateur)

**Tenxyte ne gère pas TLS directement** — c'est la couche infrastructure
(nginx, Caddy, AWS ALB, Cloudflare, etc.).

#### Vérifications TLS à effectuer côté serveur

| Contrôle | Outil |
|---------|-------|
| Versions TLS acceptées (TLS ≥ 1.2 obligatoire, TLS 1.3 recommandé) | `openssl s_client`, testssl.sh |
| Suites de chiffrement (rejeter RC4, 3DES, export ciphers) | testssl.sh, ssllabs.com |
| Vérification du certificat (chaîne complète, non expiré) | ssllabs.com |
| HSTS préchargé | hstspreload.org |
| OCSP Stapling activé | `openssl s_client -status` |
| Sans SNI support (si multi-domaine) | testssl.sh |
| HTTP → HTTPS redirect (301 permanent, pas 302) | `curl -I http://...` |

#### Recommandations TLS minimum

```nginx
# nginx — configuration recommandée
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:
            ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:
            ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
ssl_prefer_server_ciphers off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
ssl_stapling on;
ssl_stapling_verify on;
```

### C4. Rate Limiting — Résistance aux abus

**Fichier** : `src/tenxyte/throttles.py`

| Throttle | Rate | Vecteur protégé | Contournable par X-FF ? |
|---------|------|----------------|------------------------|
| `LoginThrottle` | 5/min | Brute force password | ⚠️ OUI si X-FF non validé |
| `LoginHourlyThrottle` | 20/h | Credential stuffing | ⚠️ OUI |
| `RegisterThrottle` | 3/h | Spam compte | ⚠️ OUI |
| `RegisterDailyThrottle` | 10/j | Spam compte | ⚠️ OUI |
| `PasswordResetThrottle` | 3/h | Spam reset / DoS | ⚠️ OUI |
| `OTPRequestThrottle` | 5/h | Spam OTP email/SMS | ⚠️ OUI |
| `OTPVerifyThrottle` | 5/min | Brute force OTP (6 digits) | ⚠️ OUI |
| `RefreshTokenThrottle` | 30/min | Abus refresh | ⚠️ OUI |
| `MagicLinkRequestThrottle` | 3/h | Spam email | ⚠️ OUI |
| `MagicLinkVerifyThrottle` | 10/min | Brute force token | ⚠️ OUI |
| `ProgressiveLoginThrottle` | Exponentiel | Brute force avancé | ⚠️ OUI |

> **Vulnérabilité systémique** : tous les throttles lisent `X-Forwarded-For`
> sans liste de proxies de confiance (`TRUSTED_PROXIES`). Un attaquant
> peut forger cet header pour contourner tous les rate limits.
>
> **Solution** : utiliser `django-ipware` avec `IPWARE_META_PRECEDENCE_ORDER`
> limité aux IPs des proxies internes de confiance, ou configurer `TRUSTED_PROXIES`
> dans Tenxyte.

---

## PARTIE D — Checklist de l'auditeur

### Flux d'authentification

- [ ] Bypass 2FA possible (passer directement à l'endpoint post-login sans totp_code) ?
- [ ] Anti-replay TOTP (même code valide deux fois dans la fenêtre) ?
- [ ] Session invalidée à la déconnexion (blacklist JTI + révocation refresh) ?
- [ ] Déconnexion globale (`/logout/all/`) révoque tous les refresh tokens ?
- [ ] Reset password invalide les sessions actives ?
- [ ] L'email de magic link n'expose pas le token dans le Referer header ?
- [ ] Le compte OAuth fuse automatiquement sans consentement explicite ?

### Contrôle d'accès

- [ ] IDOR sur `/admin/users/<id>/` (utilisateur B peut-il lire les données de A) ?
- [ ] Mass assignment via `PATCH /me/` (champs privilégiés exclus du serializer) ?
- [ ] Accès aux endpoints `/admin/` sans `is_staff` → 403 ou 401 ?
- [ ] Isolation multi-tenant (données d'org A accessibles depuis org B) ?
- [ ] Un JWT d'app A est rejeté par app B (vérification `app_id` dans le token) ?

### En-têtes et TLS

- [ ] `Strict-Transport-Security` présent et correctement configuré ?
- [ ] `Content-Security-Policy` configuré ?
- [ ] `CORS_ALLOW_ALL_ORIGINS = False` en production ?
- [ ] TLS 1.0 et 1.1 désactivés ?
- [ ] Suites RC4, 3DES absentes de la négociation TLS ?
- [ ] Certificat valide et complet (chaîne de confiance) ?

### Configuration

- [ ] `TENXYTE_JWT_AUTH_ENABLED = True` (jamais False en production) ?
- [ ] `TENXYTE_APPLICATION_AUTH_ENABLED = True` ?
- [ ] `DEBUG = False` dans les settings Django de production ?
- [ ] `SECRET_KEY` Django différente de `TENXYTE_JWT_SECRET_KEY` ?
- [ ] Pas de credentials hardcodés dans le code ou .env committé ?
