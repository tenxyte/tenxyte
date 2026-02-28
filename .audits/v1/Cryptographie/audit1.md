# AUDIT DE SÉCURITÉ CRYPTOGRAPHIQUE
## Tenxyte Authentication Model
### Analyse complète des primitives cryptographiques

---

| Attribut | Valeur |
|---|---|
| Document | Audit Cryptographique — Rapport Final |
| Produit | Tenxyte Authentication Framework |
| Version auditée | 1.0 (pré-publication) |
| Date | 27 Février 2026 |
| Auditeur | Audit IA Assisté — Revue indépendante |
| Confidentialité | Usage interne / Équipe de développement |
| Périmètre | 10 primitives cryptographiques, 6 couches de sécurité |

> **NOTE GLOBALE : B+ / APTE À LA PUBLICATION**
> 1 vulnérabilité critique à corriger avant release · 2 points importants à adresser

---

## 1. Périmètre & Méthodologie

Cet audit couvre l'ensemble des primitives cryptographiques documentées dans la stratégie de chiffrement Tenxyte v1.0. L'analyse a été conduite en combinant la revue de code statique, l'examen des choix architecturaux, et la comparaison aux standards de l'industrie en vigueur (OWASP, NIST SP 800-63B, FIPS 140-3).

### Inventaire des primitives auditées

| # | Primitive | Algorithme | Librairie | Verdict |
|---|---|---|---|---|
| 1 | Hachage mot de passe | bcrypt (work factor 12) | `bcrypt` | **✓ Solide — Troncature à corriger** |
| 2 | Hash secret applicatif | bcrypt + base64 | `bcrypt` | ✓ Excellent |
| 3 | Signature JWT | HMAC-SHA256 (HS256) | `PyJWT` | ✓ Correct — Fallback à risque |
| 4 | Génération aléatoire | CSPRNG (secrets) | stdlib Python | ✓ Exemplaire |
| 5 | Hash tokens temporaires | SHA-256 | `hashlib` | ✓ Excellent |
| 6 | Hash backup codes 2FA | SHA-256 | `hashlib` | ~ Acceptable — Entropie faible |
| 7 | HIBP breach check | SHA-1 (k-anonymity) | `hashlib` | ✓ Correct (contraint externe) |
| 8 | TOTP 2FA | HMAC-SHA1 / RFC 6238 | `pyotp` | ✓ Standard — Secret exposable |
| 9 | WebAuthn / Passkeys | FIDO2 (ECDSA P-256) | `py_webauthn` | ✓ État de l'art |
| 10 | JWT ID (anti-replay) | UUID v4 | `uuid` | ✓ Acceptable |

### Critères d'évaluation

Chaque primitive a été évaluée selon cinq axes : (1) adéquation algorithmique au cas d'usage, (2) résistance aux vecteurs d'attaque connus, (3) qualité de l'entropie générée, (4) conformité aux standards actuels NIST/OWASP/RFC, et (5) robustesse de l'implémentation effective dans le code.

---

## 2. Constatations Critiques — Action Requise Avant Publication

> 🔴 **CRITIQUE — CVE-class · Troncature silencieuse bcrypt à 72 octets**
>
> **Fichiers concernés :** `src/tenxyte/models/auth.py` → `set_password()`, `check_password()`
> **Fichiers concernés :** `src/tenxyte/models/security.py` → `PasswordHistory.is_password_used()`

bcrypt tronque silencieusement tout input dépassant 72 octets. En UTF-8, un seul caractère peut peser jusqu'à 4 octets. La conséquence directe est qu'un attaquant connaissant les 72 premiers octets d'un mot de passe long peut s'authentifier avec un suffixe différent — sans que le système ne détecte l'anomalie.

### Scénario d'attaque concret

Soit un utilisateur dont le mot de passe est une longue phrase de passe de 90 caractères ASCII (90 octets). Un attaquant qui a exfiltré les 72 premiers caractères peut s'authentifier avec n'importe quelle chaîne ayant le même préfixe de 72 octets, quelle que soit la fin. Le hash produit par bcrypt sera identique.

**❌ Code actuel (vulnérable)**

```python
def set_password(self, raw: str):
    self.password = bcrypt.hashpw(
        raw.encode("utf-8"),  # ← tronqué à 72 octets
        bcrypt.gensalt()
    ).decode("utf-8")
```

**✅ Correction recommandée**

```python
def set_password(self, raw: str):
    pre = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()  # → 64 octets hex, < 72
    self.password = bcrypt.hashpw(
        pre.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")
```

Le pré-hashage SHA-256 produit toujours exactement 64 octets hexadécimaux — en-dessous de la limite bcrypt — quelle que soit la longueur ou l'encodage du mot de passe original. Cette correction doit être appliquée de manière identique dans `check_password()` et `PasswordHistory.is_password_used()`. Les hashs existants devront être remplacés à la prochaine connexion (re-hachage transparent au login).

---

## 3. Points Importants — À Adresser en Priorité Post-Launch

> 🟠 **IMPORTANT — Fallback JWT vers `SECRET_KEY` Django**
>
> **Fichier concerné :** `src/tenxyte/conf.py` · `JWTService.__init__()`
> **Risque :** Couplage fort entre clé de signature JWT et clé maîtresse Django

La configuration actuelle utilise `SECRET_KEY` Django comme valeur de repli si `TENXYTE_JWT_SECRET_KEY` n'est pas définie. Dans Django, `SECRET_KEY` est la clé maîtresse qui protège simultanément les sessions, les tokens CSRF, les messages signés, les cookies, et les tokens de réinitialisation de mot de passe. Ce couplage crée deux risques distincts.

**Premier risque :** une rotation planifiée de la clé JWT (bonne pratique) entraîne mécaniquement une rotation de `SECRET_KEY`, ce qui invalide instantanément toutes les sessions actives de tous les utilisateurs, tous les tokens CSRF en cours, et tous les liens de réinitialisation de mot de passe en transit — un incident opérationnel majeur non lié à la sécurité.

**Second risque :** une fuite de la clé JWT (via une surface d'attaque quelconque) expose simultanément la capacité de forger des sessions Django et des tokens CSRF. Ces deux secrets doivent impérativement être isolés.

```python
# conf.py — Rendre TENXYTE_JWT_SECRET_KEY obligatoire
JWT_SECRET_KEY = os.environ.get("TENXYTE_JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ImproperlyConfigured(
        "TENXYTE_JWT_SECRET_KEY must be set. Generate with:"
        " python -c \"import secrets; print(secrets.token_hex(32))\""
    )
```

---

> 🟠 **IMPORTANT — Secret TOTP stocké en clair dans la base de données**
>
> **Fichier concerné :** `src/tenxyte/models/auth.py` → `totp_secret` (`CharField`)
> **Risque :** Un dump de la base expose tous les secrets TOTP, permettant de générer des codes valides

Le document original justifie ce choix en citant Google et GitHub comme références. Cette comparaison est techniquement correcte mais architecturalement trompeuse : ces acteurs disposent de protections de base de données (chiffrement at-rest, HSM, cloisonnement réseau strict) généralement absentes d'une infrastructure naissante.

**La menace concrète :** un attaquant obtenant un dump de la base de données (via injection SQL, backup compromis, accès insider) peut immédiatement générer des codes TOTP valides pour l'ensemble des utilisateurs ayant activé le 2FA — neutralisant complètement la valeur du second facteur.

Solution pragmatique sans HSM : chiffrement applicatif symétrique avec AES-256-GCM via Fernet. La clé de chiffrement réside en variable d'environnement ou dans un gestionnaire de secrets (Vault, AWS KMS). Un dump de la base sans la clé d'environnement est alors inexploitable.

```python
# Installation : pip install cryptography
from cryptography.fernet import Fernet

TOTP_KEY = Fernet(os.environ["TENXYTE_TOTP_ENCRYPTION_KEY"])

# Stockage du secret
encrypted = TOTP_KEY.encrypt(raw_totp_secret.encode()).decode()

# Lecture du secret pour vérification
raw_secret = TOTP_KEY.decrypt(stored_encrypted.encode()).decode()
```

---

## 4. Améliorations — Bonnes Pratiques Manquantes

### 4.1 Comparaison backup codes sans `hmac.compare_digest`

> 🟡 **MINEUR — Comparaison non time-constant des codes de secours**
>
> **Fichier :** `src/tenxyte/services/totp_service.py` → `verify_backup_code()`
> **Risque réel :** Faible (hashs SHA-256 comparés, pas les codes bruts) — Mais mauvaise pratique défensive

Le document argumente correctement que la comparaison de hashs SHA-256 ne révèle pas d'information sur les codes bruts via une attaque timing. L'argument est juste. Cependant, la pratique défensive standard — et celle qui survivra à d'éventuelles revues d'auditeurs tiers — consiste à utiliser `hmac.compare_digest()` pour toute comparaison de valeurs liées à l'authentification, sans exception.

```python
import hmac

# Avant (in user.backup_codes — comparaison ordinaire)
if code_hash in user.backup_codes:

# Après (time-constant — défensif)
if any(hmac.compare_digest(code_hash, stored) for stored in user.backup_codes):
```

### 4.2 Work factor bcrypt implicite et non configurable

La valeur de 12 rounds est une dépendance implicite à la valeur par défaut de la librairie bcrypt Python, qui pourrait théoriquement changer lors d'une mise à jour. Plus concrètement, l'ajustement du work factor en production (recommandé tous les 2 ans à mesure que la puissance de calcul augmente) nécessite une modification du code source plutôt qu'un paramètre de configuration.

```python
# conf.py — Externaliser le work factor
BCRYPT_ROUNDS = int(os.environ.get("TENXYTE_BCRYPT_ROUNDS", "12"))

# auth.py — Utiliser la configuration
bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
```

### 4.3 Entropie des codes de secours 2FA insuffisante

Les codes de secours actuels utilisent `secrets.token_hex(4)`, soit 32 bits d'entropie. Bien que protégés par leur caractère à usage unique, cette valeur est en-dessous du seuil de 64 bits recommandé par OWASP pour les secrets d'authentification dérivés de l'aléatoire système. Le passage à `token_hex(8)` double l'entropie sans impact UX perceptible, les codes de secours n'étant saisis qu'en situation d'urgence.

```python
# Avant  (32 bits — ex: "a1b2-c3d4")
code = secrets.token_hex(4)
formatted = f"{code[:4]}-{code[4:]}"

# Après  (64 bits — ex: "a1b2c3d4-e5f6g7h8")
code = secrets.token_hex(8)
formatted = f"{code[:8]}-{code[8:]}"
```

### 4.4 Absence de timeout sur l'appel HTTP HIBP

L'appel à l'API HaveIBeenPwned lors de l'enregistrement d'un utilisateur ne spécifie pas de timeout. En l'absence de timeout, si l'API externe est lente ou indisponible, le thread Django reste bloqué indéfiniment, ce qui peut être exploité comme vecteur d'épuisement de ressources (DoS indirect) en envoyant de nombreuses requêtes d'enregistrement simultanées.

```python
# Avant
response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")

# Après — timeout explicite + gestion de l'échec
try:
    response = requests.get(
        f"https://api.pwnedpasswords.com/range/{prefix}",
        timeout=3,
    )
except requests.exceptions.Timeout:
    return False, 0  # fail-open : ne pas bloquer l'inscription
```

---

## 5. Points Forts — Ce Qui Est Fait Correctement

L'audit met en évidence une base cryptographique saine, démontrant une culture de sécurité au-dessus de la moyenne pour un projet en phase de première publication. Les éléments suivants sont notables et constituent de bonnes références pour d'autres projets.

| Point fort | Description | Impact |
|---|---|---|
| CSPRNG systématique | Module `secrets` utilisé sans exception — jamais `random` | Critique |
| Pattern store-hash / distribute-raw | Aucun secret brut persisté en base de données | Critique |
| Whitelist d'algorithmes JWT | `algorithms=[algo]` empêche l'attaque `alg:none` | Critique |
| Anti-replay JWT via JTI | UUID v4 par token + blacklist pour invalidation | Élevé |
| k-anonymity HIBP | Seul le préfixe SHA-1 (5 chars) quitte le serveur | Élevé |
| Séparation lent/rapide | bcrypt pour secrets persistants, SHA-256 pour tokens court-terme | Élevé |
| WebAuthn FIDO2 | Résistance au phishing intrinsèque — état de l'art | Élevé |
| Claims JWT requis | `require: [exp, iat, user_id, app_id]` à chaque décodage | Moyen |
| Fenêtre TOTP minimale | `valid_window=1` (±30s) — équilibre sécurité/UX | Moyen |
| Aucune clé hardcodée | Zéro secret en clair dans le code source | Critique |
| Documentation cryptographique | Rare et précieux — facilite les audits futurs | Organisationnel |

> ✅ **Absence confirmée des anti-patterns les plus dangereux**
>
> - Aucun MD5 ou SHA-1 pour hacher des secrets persistants
> - Aucun stockage de mot de passe en clair ou simplement encodé (Base64 ≠ chiffrement)
> - Aucun chiffrement symétrique AES implémenté manuellement (error-prone)
> - Aucun `random.randint()` / `random.choice()` pour des valeurs cryptographiques
> - Aucune clé cryptographique ou secret hardcodé dans le source code

---

## 6. Roadmap des Recommandations

| Priorité | Action | Fichier(s) | Effort | Impact |
|---|---|---|---|---|
| 🔴 **P0** | Corriger troncature bcrypt (pré-SHA256) | `auth.py`, `security.py` | 1h | **Critique** |
| 🟠 **P1** | Rendre `TENXYTE_JWT_SECRET_KEY` obligatoire | `conf.py` | 30min | Élevé |
| 🟠 **P1** | Chiffrer le secret TOTP avec Fernet | `auth.py`, `totp_service.py` | 2h | Élevé |
| 🟡 **P2** | `hmac.compare_digest` pour backup codes | `totp_service.py` | 15min | Moyen |
| 🟡 **P2** | Externaliser `BCRYPT_ROUNDS` en config | `conf.py`, `auth.py` | 30min | Faible |
| 🟡 **P2** | `token_hex(8)` pour backup codes 2FA | `totp_service.py` | 10min | Moyen |
| 🟡 **P2** | Timeout 3s sur appel HIBP | `breach_check_service.py` | 10min | Opérationnel |
| 🔵 **P3** | Migration progressive vers Argon2id | `auth.py`, `requirements.txt` | 3h | Futur |
| 🔵 **P3** | RS256/ES256 si évolution microservices | `conf.py`, `jwt_service.py` | 4h | Architectural |

---

## 7. Scorecard Final

| Domaine | Note actuelle | Note post-corrections P0/P1 | Référence industrie |
|---|---|---|---|
| Hachage mots de passe | B+ (troncature) | A | Argon2id = A+ |
| Secrets applicatifs | A | A | bcrypt / Argon2id |
| JWT & gestion tokens | B+ (fallback) | A- | HS256 monolithe |
| Génération aléatoire | A+ | A+ | secrets CSPRNG |
| 2FA (TOTP + WebAuthn) | B+ (secret clair) | A | FIDO2 + RFC6238 |
| Privacy by design | A | A | k-anonymity HIBP |
| Sécurité défensive | B (compare_digest) | A- | Timing-safe compares |
| Documentation | A | A | Rare et précieux |
| **GLOBAL** | **B+** | **A-** | **A (avec Argon2id)** |

---

> **Conclusion**
>
> Tenxyte présente une base cryptographique significativement au-dessus de la moyenne des projets d'authentification open-source. La correction de la troncature bcrypt (P0, estimée à 1h) est le seul bloquant absolu avant publication. Les corrections P1 (JWT fallback + chiffrement TOTP) sont fortement recommandées dans les 2 semaines suivant le lancement. Le projet peut être publié après résolution du P0.

---

*Document généré le 27 Février 2026 · Audit IA Assisté · Usage interne Tenxyte*