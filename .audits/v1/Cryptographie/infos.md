# Tenxyte — Stratégie de Chiffrement & Cryptographie

> **Audience** : équipe de développement, contributeurs, auditeurs de sécurité.
> **Périmètre** : toutes les primitives cryptographiques utilisées dans Tenxyte,
> leur emplacement exact dans le code, la motivation du choix, et une évaluation
> critique avec les meilleures alternatives.
> **Principe fondamental** : aucune valeur sensible, clé ou hash n'est divulguée.
> **Dernière mise à jour** : 2026-02-27

---

## Vue d'ensemble — Inventaire des primitives cryptographiques

| # | Primitive | Algorithme | Librairie | Utilisation |
|---|-----------|------------|-----------|-------------|
| 1 | Hachage de mot de passe | **bcrypt** | `bcrypt` | Mots de passe utilisateurs |
| 2 | Hachage de secret applicatif | **bcrypt + base64** | `bcrypt`, `base64` | Secrets `X-Access-Secret` |
| 3 | Signature JWT | **HMAC-SHA256 (HS256)** | `PyJWT` | Access tokens |
| 4 | Génération aléatoire sécurisée | **CSPRNG** (`secrets`) | stdlib Python | Tous les tokens |
| 5 | Hachage de tokens temporaires | **SHA-256** | `hashlib` | OTP, Magic Link |
| 6 | Hachage de codes de secours 2FA | **SHA-256** | `hashlib` | Backup codes TOTP |
| 7 | Vérification HIBP (k-anonymity) | **SHA-1** | `hashlib` | Breach check |
| 8 | TOTP (2FA) | **HMAC-SHA1 / RFC 6238** | `pyotp` | Authentification 2FA |
| 9 | WebAuthn / Passkeys | **FIDO2 (ECDSA P-256 / RS256)** | `py_webauthn` | Authentification passwordless |
| 10 | Identifiants de token JWT | **UUID v4** | `uuid` | Anti-replay (JTI) |

---

## 1. Hachage des mots de passe utilisateurs — bcrypt

### Emplacement

```
src/tenxyte/models/auth.py  →  AbstractUser.set_password()
                           →  AbstractUser.check_password()
src/tenxyte/models/security.py → PasswordHistory.is_password_used()
```

### Implémentation

```python
# Stockage
def set_password(self, raw_password: str):
    self.password = bcrypt.hashpw(
        raw_password.encode('utf-8'),
        bcrypt.gensalt()         # sel aléatoire 128 bits, work factor par défaut = 12
    ).decode('utf-8')

# Vérification
def check_password(self, raw_password: str) -> bool:
    return bcrypt.checkpw(
        raw_password.encode('utf-8'),
        self.password.encode('utf-8')
    )
```

### Pourquoi bcrypt ?

bcrypt est une **fonction de dérivation de clé à coût adaptatif** (*password
hashing function / KDF*). Ses propriétés clés :

| Propriété | bcrypt | MD5 | SHA-256 | SHA-512 |
|-----------|--------|-----|---------|---------|
| Sel intégré | ✅ | ❌ | ❌ | ❌ |
| Coût ajustable | ✅ | ❌ | ❌ | ❌ |
| Résistance GPU/ASIC | ✅ (mémoire-intensif) | ❌ | ❌ | ❌ |
| Résistance tables arc-en-ciel | ✅ | ❌ | ❌ | ❌ |
| Usage correct pour MDP | ✅ | ❌ jamais | ❌ jamais | ❌ jamais |

Le **sel aléatoire** par mot de passe (`bcrypt.gensalt()`) garantit que deux
utilisateurs avec le même mot de passe auront des hashs différents — rendant les
attaques par table arc-en-ciel impossibles.

Le **work factor** (coût) est encodé dans le hash lui-même, permettant de
migrer vers un coût plus élevé sans invalider les hashs existants.

### Évaluation critique

**Note : ✅ Excellent choix pour ce cas d'usage.**

Les seules alternatives modernes sérieuses à bcrypt sont :

- **Argon2id** (gagnant de la Password Hashing Competition 2015) — plus résistant
  aux attaques ASIC/GPU grâce à une empreinte mémoire configurable.
  C'est le choix **le plus recommandé en 2024** par les standards modernes
  (OWASP, NIST SP 800-63B).
- **scrypt** — similaire à Argon2 sur l'aspect mémoire, mais moins de contrôle.

> **Recommandation future** : migrer vers `argon2-cffi` (Argon2id) pour les
> nouveaux hashs. Les anciens hashs bcrypt restent valides — la migration peut
> se faire progressivement au login (re-hacher à la connexion).

---

## 2. Hachage des secrets applicatifs — bcrypt + base64

### Emplacement

```
src/tenxyte/models/application.py  →  AbstractApplication._hash_secret()
                                   →  AbstractApplication._verify_hashed_secret()
                                   →  AbstractApplication.verify_secret()
                                   →  AbstractApplication.create_application()
                                   →  AbstractApplication.regenerate_credentials()
```

### Implémentation

```python
@staticmethod
def _hash_secret(raw_secret: str) -> str:
    """Hash le secret et encode en base64 pour éviter les problèmes avec MongoDB."""
    hashed = bcrypt.hashpw(raw_secret.encode('utf-8'), bcrypt.gensalt())
    return base64.b64encode(hashed).decode('utf-8')

@staticmethod
def _verify_hashed_secret(raw_secret: str, stored_secret: str) -> bool:
    try:
        hashed = base64.b64decode(stored_secret.encode('utf-8'))
        return bcrypt.checkpw(raw_secret.encode('utf-8'), hashed)
    except Exception:
        return False
```

### Pourquoi bcrypt ici aussi ?

Les secrets applicatifs (`X-Access-Secret`) servent de **mot de passe de
service** entre l'application cliente et le backend. Ils possèdent les mêmes
risques qu'un mot de passe :
- Vol via backup de base de données
- Fuite via des logs applicatifs
- Exposition dans un dump SQL

Utiliser bcrypt garantit qu'un attaquant ayant accès à la base ne peut pas
dériver le secret en clair.

### Pourquoi le base64 ?

Les hashs bcrypt sont des **bytes bruts** qui peuvent contenir des octets nuls
ou des séquences non-UTF-8. Le `base64.b64encode()` les transforme en une
chaîne ASCII pure, évitant des problèmes de stockage avec des bases de données
non-SQL (MongoDB) ou des encodages inattendus.

### Génération du secret brut

```python
raw_secret = secrets.token_hex(32)   # 32 bytes = 256 bits d'entropie
access_key = secrets.token_hex(32)   # identifiant public, 256 bits
```

`secrets.token_hex(32)` génère 32 bytes cryptographiquement aléatoires
encodés en hexadécimal (64 caractères). Avec 256 bits d'entropie, une attaque
par force brute est **computationnellement infaisable** (2²⁵⁶ combinaisons).

### Évaluation critique

**Note : ✅ Excellent choix.**

Le wrapper base64 est un pragmatisme légitime documenté dans le code. bcrypt
est approprié ici car la vérification est effectuée à chaque requête —
l'overhead de calcul est tolérable pour un secret qui ne change pas souvent.

> **Attention** : la vérification bcrypt sur chaque requête HTTP peut devenir
> un goulot d'étranglement à très haute charge. Si les performances deviennent
> critiques, envisager un cache courte durée côté serveur (ex: HMAC-SHA256 du
> secret en mémoire Redis avec TTL de 60s), tout en conservant bcrypt pour le
> stockage persistant.

---

## 3. Signature des JSON Web Tokens — HMAC-SHA256 (HS256)

### Emplacement

```
src/tenxyte/services/jwt_service.py  →  JWTService.generate_access_token()
                                     →  JWTService.decode_token()
src/tenxyte/conf.py                 →  JWT_ALGORITHM (défaut: 'HS256')
```

### Implémentation

```python
# Génération
payload = {
    'type': 'access',
    'jti': str(uuid.uuid4()),   # UUID v4 pour anti-replay
    'user_id': str(user_id),
    'app_id': str(application_id),
    'iat': now,
    'exp': now + access_token_lifetime,
    'nbf': now,                 # Not Before
}
token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

# Vérification
payload = jwt.decode(
    token,
    self.secret_key,
    algorithms=[self.algorithm],
    options={'require': ['exp', 'iat', 'user_id', 'app_id']}
)
```

### Pourquoi HS256 ?

**HS256 = HMAC avec SHA-256**. C'est un algorithme de signature **symétrique** :
la même clé secrète est utilisée pour signer et pour vérifier.

Avantages dans ce contexte :
- **Simple** : une seule clé à gérer (pas d'infrastructure PKI)
- **Rapide** : HMAC-SHA256 est computationnellement très léger
- **Standard** : large support dans tous les frameworks et langages

Le paramètre `algorithms=[self.algorithm]` dans `jwt.decode()` est **critique** :
il empêche l'attaque `alg: none` où un attaquant pourrait forger un token en
déclarant qu'aucune signature n'est requise.

### Pourquoi UUID v4 (JTI) ?

Le `jti` (JWT ID) est un identifiant unique par token. Il permet :
1. L'**invalidation individuelle** d'un token (blacklisting par JTI)
2. La **protection anti-replay** : deux requêtes avec le même JTI sont détectées

UUID v4 génère 122 bits d'entropie aléatoire — la probabilité de collision est
astronomiquement faible (1/2¹²²).

### Évaluation critique

**Note : ✅ Bon choix, avec une nuance importante.**

HS256 est approprié pour une architecture **monolithique** où le serveur qui
émet et le serveur qui vérifie sont les mêmes. La clé doit rester strictement
côté serveur.

**Limite principale** : si l'architecture évolue vers des **microservices**,
HS256 impose de partager la clé secrète entre tous les services vérificateurs
— ce qui augmente la surface d'attaque.

> **Pour une architecture microservices**, préférer **RS256** (RSA-SHA256) ou
> **ES256** (ECDSA P-256) :
> - La clé **privée** reste uniquement sur le service d'authentification
> - La clé **publique** est distribuée à tous les services vérificateurs
> - La compromission d'un service vérificateur n'expose pas la clé de signature

> **Configuration actuelle à vérifier** : s'assurer que `TENXYTE_JWT_SECRET_KEY`
> est une clé dédiée, distincte de `SECRET_KEY` Django, générée avec au moins
> 256 bits d'entropie. Par défaut, Tenxyte utilise `SECRET_KEY` si aucune clé
> dédiée n'est setée.

---

## 4. Génération aléatoire sécurisée — module `secrets` (CSPRNG)

### Emplacement

Utilisé **systématiquement** dans tout le codebase pour générer des tokens :

```
src/tenxyte/models/application.py  →  secrets.token_hex(32)    — access_key, raw_secret
src/tenxyte/models/operational.py  →  secrets.token_urlsafe(64) — refresh_token
                                   →  secrets.randbelow(10)     — chiffre OTP
src/tenxyte/models/magic_link.py   →  secrets.token_urlsafe(48) — magic link token
src/tenxyte/models/auth.py         →  secrets.token_urlsafe(48) — anonymization_token
src/tenxyte/services/agent_service.py → secrets.token_urlsafe(64) — HITL confirmation token
                                       → secrets.choice(...)    — agent token (48 chars)
src/tenxyte/services/totp_service.py  → secrets.token_hex(...)  — backup codes
```

### Pourquoi le module `secrets` au lieu de `random` ?

Le module `random` de Python est un **générateur pseudo-aléatoire (PRNG)**
basé sur l'algorithme Mersenne Twister. Il est **déterministe** et **prédictible**
si on connaît l'état interne.

Le module `secrets` utilise le **générateur cryptographiquement sécurisé de
l'OS** (`/dev/urandom` sur Linux/macOS, `CryptGenRandom` sur Windows) — il
est conçu pour produire des valeurs imprévisibles même en ayant observé des
sorties passées.

| Comparaison | `random` | `secrets` |
|-------------|----------|-----------|
| Prédictible si état connu | ✅ (dangereux) | ❌ (sûr) |
| Usage cryptographique | ❌ jamais | ✅ |
| Réensemencé par l'OS | ❌ | ✅ |

### Entropie par type de token

| Token | Génération | Entropie |
|-------|-----------|----------|
| `access_key` | `token_hex(32)` | 256 bits |
| `raw_secret` | `token_hex(32)` | 256 bits |
| `refresh_token` | `token_urlsafe(64)` | 512 bits |
| `magic_link` | `token_urlsafe(48)` | 384 bits |
| `agent_token` | `secrets.choice(alphanum, 48)` | ~285 bits |
| `confirmation_token` HITL | `token_urlsafe(64)` | 512 bits |
| `anonymization_token` | `token_urlsafe(48)` | 384 bits |
| Chiffre OTP | `randbelow(10)` × 6 | ~20 bits (6 chiffres) |

> **Note sur les OTP** : les codes OTP à 6 chiffres n'ont que ~20 bits
> d'entropie par design — c'est acceptable grâce aux protections complémentaires
> (expiration courte, max 3–5 tentatives, rate limiting, single-use). L'entropie
> faible est compensée par l'unicité temporelle.

### Évaluation critique

**Note : ✅ Excellent usage généralisé et cohérent.**

L'utilisation systématique de `secrets` au lieu de `random` démontre une bonne
culture de sécurité cryptographique. Ce choix est conforme aux recommandations
OWASP et NIST.

> **Point à vérifier** : l'`agent_token` utilise `secrets.choice()` sur un
> alphabet alphanumérique à 62 caractères × 48 positions, soit log₂(62⁴⁸) ≈
> 285 bits d'entropie. Légèrement moins efficient que `token_urlsafe(36)` (288
> bits, URL-safe base64), mais largement suffisant et plus lisible dans les logs.

---

## 5. Hachage des tokens temporaires (OTP & Magic Link) — SHA-256

### Emplacement

```
src/tenxyte/models/operational.py  →  OTPCode._hash_code()
                                       OTPCode.generate()
                                       OTPCode.verify()

src/tenxyte/models/magic_link.py   →  MagicLinkToken._hash_token()
                                       MagicLinkToken.generate()
                                       MagicLinkToken.get_valid()
```

### Implémentation

```python
# OTP — stockage
def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

# OTP — génération
raw_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
otp = OTPCode.objects.create(code=cls._hash_code(raw_code), ...)
return otp, raw_code  # Le code brut est retourné une seule fois

# Magic Link — même pattern
raw_token = secrets.token_urlsafe(48)
instance = cls.objects.create(token=cls._hash_token(raw_token), ...)
return instance, raw_token
```

### Pourquoi SHA-256 ici (et pas bcrypt) ?

Contrairement aux mots de passe, les codes OTP et magic link tokens ont des
propriétés très différentes :

| Propriété | Mot de passe | OTP / Magic Link |
|-----------|-------------|------------------|
| Choisi par l'humain | ✅ | ❌ (aléatoire système) |
| Entropie faible | Possible | Non (ou compensée) |
| Usage long terme | Oui | Non (expiration courte) |
| Tentatives de brute-force à risque | Élevé | Faible (rate limit + expiration) |

Un code OTP généré par `secrets.randbelow(10)` × 6 a ~20 bits d'entropie
mais :
- Expire en **10–15 minutes**
- Est **à usage unique** (`is_used = True` après vérification)
- Est protégé par un **compteur de tentatives** (max 3–5)
- Est soumis au **rate limiting** (5 tentatives / 10 min par IP)

Ces contraintes rendent une attaque par brute-force impraticable même avec un
algorithme rapide comme SHA-256. Utiliser bcrypt ici ajouterait un overhead
inutile sans gain de sécurité réel.

Un magic link token généré par `token_urlsafe(48)` a **384 bits d'entropie** —
SHA-256 est amplement suffisant : il faudrait 2¹²⁸ opérations minimum pour
trouver une collision ou préimage.

### Pattern "stocker le hash, distribuer le brut"

Ce pattern est essentiel : la valeur brute n'est **jamais persistée**. Si la
base de données est compromise :
- L'attaquant obtient le hash SHA-256 du token
- Comme le token est aléatoire avec 384+ bits d'entropie, retrouver le brut
  par force brute est impossible
- De plus, les tokens expirés en quelques minutes deviennent inutilisables

### Évaluation critique

**Note : ✅ Excellent choix, bien motivé.**

SHA-256 pour des tokens à haute entropie et courte durée de vie est la pratique
standard (GitHub, Stripe, … utilisent la même approche). L'important est que les
tokens soient générés par le CSPRNG, ce qui est bien le cas ici.

---

## 6. Codes de secours 2FA — SHA-256

### Emplacement

```
src/tenxyte/services/totp_service.py  →  TOTPService.generate_backup_codes()
                                      →  TOTPService.verify_backup_code()
```

### Implémentation

```python
def generate_backup_codes(self) -> Tuple[List[str], List[str]]:
    plain_codes = []
    hashed_codes = []
    for _ in range(self.BACKUP_CODES_COUNT):   # 10 codes par défaut
        code = secrets.token_hex(4)            # 32 bits = 8 hex chars
        formatted_code = f"{code[:4]}-{code[4:]}"   # ex: "a1b2-c3d4"
        plain_codes.append(formatted_code)
        hashed = hashlib.sha256(formatted_code.encode()).hexdigest()
        hashed_codes.append(hashed)
    return plain_codes, hashed_codes   # plain: affiché UNE FOIS, hashed: stocké

def verify_backup_code(self, user: User, code: str) -> bool:
    ...
    code_hash = hashlib.sha256(formatted.encode()).hexdigest()
    if code_hash in user.backup_codes:
        user.backup_codes.remove(code_hash)  # consommé, inutilisable à nouveau
        user.save(update_fields=['backup_codes'])
        return True
```

### Pourquoi SHA-256 (et pas bcrypt) pour les backup codes ?

Un code de secours `a1b2-c3d4` est généré par `secrets.token_hex(4)`, soit
**32 bits d'entropie**. C'est moins qu'un mot de passe humain, mais :

1. L'accès aux codes de secours nécessite d'être authentifié (le 2FA a déjà
   été validé une première fois pour les afficher)
2. Chaque code est **détruit après utilisation**
3. Avec 32 bits d'entropie et 10 codes, la surface d'attaque est limitée

En pratique, SHA-256 est acceptable ici. Bcrypt ajouterait un overhead visible
au moment de la verification de chaque code dans la liste.

### Point de sécurité : stockage dans `JSONField`

Les codes hashés sont stockés dans `user.backup_codes` (un `JSONField`).
La vérification est une **comparaison d'égalité de strings** (`code_hash in user.backup_codes`).
Cette comparaison n'est pas à temps constant, mais comme les hashs SHA-256 sont
comparés (et non les codes bruts), l'attaque par timing sur les hashs ne révèle
pas d'information utile sur les codes originaux.

### Évaluation critique

**Note : ✅ Acceptable, amélioration possible.**

> **Amélioration recommandée** : utiliser `secrets.token_hex(8)` (64 bits)
> plutôt que `token_hex(4)` (32 bits) pour les codes de secours. Cela
> donne `a1b2c3d4-e5f6g7h8` — encore mémorisable mais beaucoup plus résistant.
> Cela n'impacte pas l'UX car les codes de secours ne sont saisis qu'en cas
> d'urgence.

---

## 7. Vérification de fuites — SHA-1 (HaveIBeenPwned k-anonymity)

### Emplacement

```
src/tenxyte/services/breach_check_service.py  →  BreachCheckService.is_pwned()
```

### Implémentation

```python
def is_pwned(self, password: str) -> Tuple[bool, int]:
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]    # Seuls les 5 premiers caractères partent sur le réseau
    suffix = sha1_hash[5:]    # Le suffixe reste local

    response = requests.get(f'https://api.pwnedpasswords.com/range/{prefix}')
    # L'API renvoie des centaines de suffixes → comparaison locale avec suffix
    for line in response.text.splitlines():
        line_suffix, _, count_str = line.partition(':')
        if line_suffix.upper() == suffix:
            return True, int(count_str.strip())
    return False, 0
```

### Pourquoi SHA-1 ici (et non SHA-256) ?

SHA-1 n'est **pas choisi** par Tenxyte — c'est **imposé par l'API HIBP** de Troy Hunt.
L'API Pwned Passwords est construite sur des hashs SHA-1 (pour raisons
historiques, la base existait avant les préoccupations sur SHA-1).

### Le protocole k-anonymity

C'est la partie réellement remarquable de cette implémentation :

1. Le serveur calcule `SHA1(password)` localement
2. Seuls les **5 premiers caractères hexadécimaux** (20 bits) sont envoyés à HIBP
3. L'API retourne ~500 suffixes correspondants (toutes les entrées partageant ce préfixe)
4. La comparaison complète du hash est faite **côté serveur, en local**
5. Le **mot de passe en clair** et le **hash complet** ne quittent jamais le serveur

Ce protocole garantit que même HIBP ne peut pas savoir quel mot de passe est
vérifié — seul un préfixe de 5 caractères sur 40 est divulgué, laissant 2³⁵
hashs possibles dans l'ambiguïté.

### SHA-1 est-il dangereux ici ?

SHA-1 est **cryptographiquement cassé** pour les applications nécessitant une
résistance aux collisions (signatures numériques, certificats TLS). Mais dans
ce contexte, SHA-1 est utilisé pour construire un **index de recherche** dans
une base de fuites connues — pas pour protéger un secret.

La menace ici n'est pas de trouver une collision SHA-1 mais de savoir si un
mot de passe donné est dans la base HIBP. SHA-1 reste parfaitement adapté à
cet usage de vérification d'appartenance à un ensemble.

### Évaluation critique

**Note : ✅ Correct et inévitable dans ce contexte.**

L'utilisation de SHA-1 est un compromis imposé par l'API externe, non un choix
architectural. Le protocole k-anonymity est exemplaire et devrait être cité
comme référence de *privacy by design*.

---

## 8. Authentification à deux facteurs — TOTP / HMAC-SHA1 (RFC 6238)

### Emplacement

```
src/tenxyte/services/totp_service.py  →  TOTPService.generate_secret()
                                      →  TOTPService.verify_code()
                                      →  TOTPService.get_provisioning_uri()
                                      →  TOTPService.generate_qr_code()
```

### Implémentation

```python
import pyotp

def generate_secret(self) -> str:
    return pyotp.random_base32()    # 160 bits, base32

def verify_code(self, secret: str, code: str, valid_window: int = 1) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)

def get_provisioning_uri(self, secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=self.ISSUER_NAME)
    # → otpauth://totp/Tenxyte:user@email.com?secret=XXX&issuer=Tenxyte
```

### Comment fonctionne TOTP (RFC 6238)

TOTP (*Time-based One-Time Password*) dérive un code à 6 chiffres à partir de :

```
TOTP(K, T) = HOTP(K, T)
           = Truncate(HMAC-SHA1(K, T))  mod 10^6

où K = secret partagé (base32)
   T = floor(Unix timestamp / 30)       ← période de 30 secondes
```

**HMAC-SHA1** est utilisé ici, pas SHA-1 seul. HMAC est une construction
*message authentication code* qui ajoute une clé secrète à SHA-1, ce qui
la rend résistante aux attaques de préimage et de longueur d'extension,
même si SHA-1 est vulnérable en tant que hash nu.

### Fenêtre de validité (`valid_window = 1`)

Le paramètre `valid_window=1` accepte les codes de la période courante ±1
période (soit ±30 secondes). Cela compense les légères dérives d'horloge
entre le serveur et l'appareil de l'utilisateur.

### Secret stocké

Le secret TOTP (`totp_secret`) est stocké **en clair** dans la base de données
(champ `CharField`). C'est la pratique standard — le secret TOTP doit être
accessible pour calculer le code attendu à chaque vérification, ce qui
empêche son hachage.

> **Implication** : la sécurité du 2FA TOTP dépend de la sécurité de la base
> de données. Si la DB est compromise, l'attaquant peut compromettre le 2FA.
> C'est une limitation inhérente à tous les systèmes TOTP (Google, GitHub, etc.)

### Évaluation critique

**Note : ✅ Implémentation standard et correcte.**

TOTP via `pyotp` est l'implémentation de référence en Python, utilisée par la
grande majorité des applications Django. La RFC 6238 est un standard IETF solide.

> **Alternative plus forte** : WebAuthn/FIDO2 (voir section 9) offre une
> résistance au phishing que TOTP ne peut pas garantir. TOTP est un excellent
> second facteur mais reste vulnérable au phishing en temps réel (*MITM attack*).

---

## 9. WebAuthn / Passkeys — FIDO2 (ECDSA / RS256)

### Emplacement

```
src/tenxyte/services/webauthn_service.py  →  WebAuthnService (toute la classe)
src/tenxyte/models/webauthn.py            →  WebAuthnCredential, WebAuthnChallenge
```

### Comment fonctionne WebAuthn

WebAuthn est un standard W3C / FIDO2 basé sur la **cryptographie asymétrique** :

1. **Enregistrement** :
   - Le serveur génère un challenge aléatoire
   - L'appareil de l'utilisateur génère une **paire de clés (privée/publique)**
   - La clé privée reste **sur l'appareil, jamais transmise**
   - La clé publique + la signature du challenge sont envoyées au serveur
   - Le serveur stocke la clé publique

2. **Authentification** :
   - Le serveur génère un nouveau challenge
   - L'appareil signe le challenge avec sa clé privée (déverrouillée par biométrie/PIN)
   - Le serveur vérifie la signature avec la clé publique stockée

### Algorithmes utilisés

Les algorithmes de signature dépendent de l'authenticator de l'utilisateur :

| Authenticator | Algorithme courant |
|---------------|-------------------|
| YubiKey, précision FIDO2 | **ECDSA P-256** (ES256) |
| Windows Hello, TPM | **RS256** (RSA 2048-bit) |
| Apple Touch/Face ID | **ECDSA P-256** |

**ECDSA P-256** est actuellement le plus répandu et recommandé :
- Clé de 256 bits ≈ sécurité RSA 3072 bits
- Signatures compactes (64 bytes vs 256+ bytes RSA)
- NIST curve, hardware-accelerated sur la plupart des puces

### Challenge unique et usage simple

```python
# WebAuthnChallenge.generate() utilise secrets (CSPRNG implicitement via py_webauthn)
challenge_instance, raw_challenge = WebAuthnChallenge.generate(
    operation='register',
    user=user,
    expiry_seconds=300     # 5 minutes de validité
)
# Le challenge est marqué 'used' dès consommation → anti-replay
```

### Avantage unique par rapport à TOTP

WebAuthn est **intrinsèquement résistant au phishing** : la signature inclut
l'identité du domaine (RP ID = `yourapp.com`). Une clé enregistrée sur
`yourapp.com` ne peut pas être utilisée pour s'authentifier sur `yourapp-evil.com`
— la vérification échouerait au niveau cryptographique.

### Évaluation critique

**Note : ✅ Meilleur second facteur (et potentiellement premier) disponible.**

L'implémentation via `py_webauthn` est solide. WebAuthn représente l'état de
l'art en authentification forte. La restriction au preset `robust` est logique —
WebAuthn nécessite un authenticator dédié.

> **Recommandation** : activer WebAuthn comme option dans le preset `medium`.
> Les navigateurs modernes supportent nativement les passkeys, rendant WebAuthn
> plus accessible qu'il y a quelques années.

---

## 10. Identifiants JWT — UUID v4

### Emplacement

```
src/tenxyte/services/jwt_service.py  →  JWTService.generate_access_token()
```

### Implémentation

```python
import uuid
jti = str(uuid.uuid4())  # UUID Version 4, 122 bits aléatoires
```

### Rôle cryptographique

Le `jti` (JWT ID) est intégré dans le payload JWT (signé par HS256) pour
permettre le blacklisting individuel d'un token. Ce n'est pas une primitive
cryptographique à proprement parler, mais un **nonce** (number used once).

UUID v4 utilise `os.urandom()` en Python pour ses 122 bits aléatoires (6 bits
sont fixes pour indiquer la version et la variante). Une dépendance à
`secrets.token_hex(16)` serait légèrement plus explicite sur l'intention
cryptographique, mais UUID v4 est tout aussi sûr pour cet usage.

### Évaluation critique

**Note : ✅ Acceptable et idiomatique.**

---

## Synthèse des choix cryptographiques

### Tableau récapitulatif

| Usage | Choix actuel | Standard industrie 2024 | Écart |
|-------|-------------|------------------------|-------|
| Hash mot de passe | bcrypt (work factor ~12) | Argon2id | Faible — bcrypt reste sûr |
| Hash secret applicatif | bcrypt + base64 | bcrypt / Argon2id | Aucun |
| Signature JWT | HS256 | HS256 (monolithe), RS256/ES256 (microservices) | Architecture dépendant |
| Génération tokens | `secrets` CSPRNG | `secrets` CSPRNG | Aucun |
| Hash tokens temporaires | SHA-256 | SHA-256 / BLAKE3 | Aucun |
| Hash backup codes 2FA | SHA-256 | SHA-256 | Entropie légèrement faible |
| HIBP breach check | SHA-1 (imposé) | SHA-1 (protocole HIBP) | Aucun (contraint externe) |
| TOTP 2FA | HMAC-SHA1 / RFC 6238 | HMAC-SHA1 / RFC 6238 | Aucun |
| Passwordless fort | WebAuthn FIDO2 | WebAuthn FIDO2 | Aucun |

### Ce qui est fait correctement ✅

1. **Séparation claire** entre primitives lentes (bcrypt pour les secrets persistants)
   et rapides (SHA-256 pour les tokens à haute entropie et courte durée)
2. **CSPRNG exclusif** — `random` n'est utilisé nulle part pour de la cryptographie
3. **Pattern "stocker le hash, distribuer le brut"** appliqué systématiquement
4. **Anti-replay JWT** via JTI + blacklist
5. **k-anonymity** pour la vérification HIBP — privacy by design
6. **WebAuthn** disponible pour le niveau de sécurité maximal
7. **Claims JWT requis** explicitement validés à chaque décodage
8. **Fenêtre TOTP minimale** (1 période ±30s) pour limiter la durée de validité d'un code

### Améliorations recommandées 🔧

1. **Argon2id** : migrer progressivement de bcrypt vers Argon2id pour les
   nouveaux mots de passe (`argon2-cffi` ≥ 21.3) — migration transparente
   au login
2. **RS256/ES256 JWT** : à envisager si l'architecture évolue vers des
   microservices qui vérifient les tokens sans les émettre
3. **Entropie backup codes** : passer de `secrets.token_hex(4)` (32 bits) à
   `secrets.token_hex(8)` (64 bits) pour les codes de secours 2FA
4. **Clé JWT dédiée** : toujours définir `TENXYTE_JWT_SECRET_KEY` distinct de
   `SECRET_KEY` Django, avec une rotation documentée
5. **Rotation des clés JWT** : documenter une procédure de rotation de la
   clé HS256 (invalide tous les tokens actifs — à planifier avec les équipes)

---

## Cas à risque zéro

Les éléments suivants sont **absents du codebase**, ce qui est une bonne nouvelle :

- ❌ Aucun `random.randint()`, `random.choice()` ou équivalent pour des tokens
- ❌ Aucun MD5 ou SHA-1 pour hacher des secrets persistants
- ❌ Aucun stockage de mot de passe en clair ou encodé Base64 (encodage ≠ chiffrement)
- ❌ Aucun chiffrement symétrique AES maison (qui serait error-prone)
- ❌ Aucun `alg: none` possible dans JWT (liste explicite d'algorithmes acceptés)
- ❌ Aucune clé cryptographique en dur dans le code source

---

*Ce document est destiné à la documentation interne. Il décrit les mécanismes
cryptographiques de manière analytique. Aucune valeur sensible (clé, sel,
hash) n'est divulguée.*
