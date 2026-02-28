# Audit de Sécurité — Qualité du Code & Surface d'Attaque
## Package : **Tenxyte** — Module d'Authentification
### Version auditée : `0.9.1.7` | Date : 2026-02-27

---

> **Classification** : Confidentiel — Usage interne pré-publication  
> **Périmètre** : Qualité du code, surface d'attaque, sécurité des endpoints, gestion des secrets, dépendances, logs & observabilité  
> **Référentiels** : OWASP Authentication Cheat Sheet, NIST SP 800-63B, RFC 9110, RFC 6238

---

## Table des matières

1. [Synthèse exécutive](#1-synthèse-exécutive)
2. [Tableau de bord des risques](#2-tableau-de-bord-des-risques)
3. [Qualité du code](#3-qualité-du-code)
4. [Surface d'attaque — Points d'entrée](#4-surface-dattaque--points-dentrée)
5. [Couche d'accès — Décorateurs](#5-couche-daccès--décorateurs)
6. [Validation des entrées](#6-validation-des-entrées)
7. [Gestion des erreurs & fuite d'information](#7-gestion-des-erreurs--fuite-dinformation)
8. [Injection & sécurité ORM](#8-injection--sécurité-orm)
9. [Gestion des secrets & configuration](#9-gestion-des-secrets--configuration)
10. [Dépendances & supply chain](#10-dépendances--supply-chain)
11. [Analyse statique (SAST)](#11-analyse-statique-sast)
12. [Logs & observabilité](#12-logs--observabilité)
13. [Audit des API REST](#13-audit-des-api-rest)
14. [Ce qui est correctement géré](#14-ce-qui-est-correctement-géré)
15. [Plan de remédiation priorisé](#15-plan-de-remédiation-priorisé)
16. [Conclusion & verdict](#16-conclusion--verdict)

---

## 1. Synthèse exécutive

Le module Tenxyte v0.9.1.7 est un package d'authentification Django à spectre large couvrant l'authentification JWT, les connexions sociales OAuth2, la 2FA TOTP, WebAuthn, les magic links, le RBAC multi-tenant, les tokens d'agents IA et un système GDPR complet. L'architecture est globalement solide et démontre une maturité de conception supérieure à la moyenne des modules d'authentification open source.

**Points forts majeurs :** l'usage exclusif de l'ORM Django (protection SQL), la whitelist explicite d'algorithmes JWT contre l'attaque `alg:none`, l'usage de `secrets.token_urlsafe()` pour tous les tokens, un système de rate limiting multi-niveaux et une gestion rigoureuse des secrets (aucun hardcodé).

**Points critiques bloquant la publication :** deux vulnérabilités de catégorie haute/critique doivent être corrigées avant mise en production : le contournement de rate limiting via `X-Forwarded-For` non validé, et l'existence de flags de désactivation des protections sans garde-fous de détection en environnement de production. Plusieurs points de sévérité moyenne requièrent également une attention avant publication publique.

**Verdict global : Publication conditionnée à la résolution des points critiques et hauts. Le module ne doit pas être publié en l'état sans les remédiations décrites en section 15.**

---

## 2. Tableau de bord des risques

| # | Vulnérabilité | Sévérité | CVSS estimé | Statut |
|---|---------------|----------|-------------|--------|
| R-01 | `X-Forwarded-For` non validé → bypass rate limiting | 🔴 Haute | 7.5 | ❌ À corriger |
| R-02 | `TENXYTE_JWT_AUTH_ENABLED = False` → accès sans auth | 🔴 Critique (si prod) | 9.1 | ❌ À corriger |
| R-03 | `TENXYTE_CORS_ALLOW_ALL_ORIGINS = True` en configuration par défaut | 🔴 Haute | 7.2 | ❌ À corriger |
| R-04 | Timing attack sur le login par email (bcrypt non exécuté si email inexistant) | 🟠 Moyenne | 5.3 | ❌ À corriger |
| R-05 | Fusion automatique de comptes OAuth par email sans confirmation | 🟠 Moyenne | 6.1 | ❌ À corriger |
| R-06 | Comparaisons OTP/backup codes sans `hmac.compare_digest` | 🟡 Faible-Moyenne | 3.7 | ⚠️ À considérer |
| R-07 | `py_webauthn` sans contrainte de version dans `pyproject.toml` | 🟠 Moyenne | 5.0 | ❌ À corriger |
| R-08 | `str(e)` exposé dans certaines réponses API (fuite d'info interne) | 🟡 Faible | 3.1 | ⚠️ À corriger |
| R-09 | Messages d'erreur révélant le code de rôle/permission attendu | 🟡 Faible | 2.6 | ⚠️ À documenter |
| R-10 | N+1 queries sur la hiérarchie RBAC des organisations | 🟢 Performance | — | ⚠️ À optimiser |
| R-11 | Tests de sécurité manquants (IDOR, mass assignment, race conditions) | 🟠 Moyenne | — | ❌ À couvrir |

---

## 3. Qualité du code

### 3.1 Outillage qualité

La chaîne d'outillage qualité est complète et bien configurée pour un package Python moderne :

| Outil | Configuration | Évaluation |
|-------|-------------|-----------|
| **pytest** + **pytest-cov** | Coverage ≥ 60%, HTML + terminal | ✅ Présent — seuil acceptable mais améliorable |
| **Black** | line-length 120, Python 3.10+ | ✅ Standard |
| **Ruff** | line-length 120, target py310 | ✅ Linting rapide et strict |
| **mypy** | ≥ 1.0 | ⚠️ Présent mais couverture partielle |

**Observation :** le seuil de couverture de 60% est un minimum défensif. Pour un module d'authentification exposé publiquement, un seuil de **80%** est recommandé par les standards de l'industrie (OWASP ASVS v4.0 §V11). La couverture actuelle est jugée insuffisante pour une publication.

### 3.2 Typage statique

Le typage mypy est présent dans les services avec des signatures explicites (`Tuple[bool, Optional[Dict], str]`) et l'utilisation systématique de `@wraps` dans les décorateurs. En revanche, les modèles sont partiellement typés et les vues (DRF) peu typées.

**Recommandation :** activer `mypy --strict` progressivement sur les modules critiques (`services/`, `decorators.py`). Les types partiels dans les modèles représentent un risque de régression silencieuse lors des montées de version Django.

### 3.3 Couverture de tests

| Catégorie | Fichiers | Appréciation |
|-----------|---------|--------------|
| `tests/unit/` | ~60 fichiers | ✅ Large couverture fonctionnelle |
| `tests/integration/` | 4 fichiers | ⚠️ Insuffisant pour la multi-tenancy |
| `tests/security/` | 2 fichiers | ⚠️ Bonne base mais lacunes identifiées |
| `tests/multidb/` | ~7 fichiers | ✅ PostgreSQL, MySQL, MongoDB |

Les tests de sécurité existants (751 lignes, 9 classes) sont une base solide. Les lacunes sont détaillées en section R-11.

---

## 4. Surface d'attaque — Points d'entrée

### 4.1 Headers HTTP

| Header | Utilisé par | Validation | Risque |
|--------|------------|-----------|--------|
| `Authorization: Bearer <jwt>` | `JWTAuthentication`, `@require_jwt` | PyJWT.decode() + whitelist HS256 | ✅ Sûr |
| `Authorization: AgentBearer <token>` | `AgentTokenMiddleware` | Lookup DB + validation état | ✅ Sûr |
| `X-Access-Key` | `ApplicationAuthMiddleware` | Lookup DB par clé exacte | ✅ Sûr |
| `X-Access-Secret` | `ApplicationAuthMiddleware` | `bcrypt.checkpw()` | ✅ Temps constant |
| `X-Org-Slug` | `OrganizationContextMiddleware` | Lookup DB + `is_active` | ✅ Sûr |
| `X-Forwarded-For` | `IPBasedThrottle`, `get_client_ip()` | `split(',')[0]` — **non validé** | 🔴 **R-01** |
| `X-Action-Confirmation` | `require_agent_clearance` (HITL) | Lookup DB par token | ✅ Sûr |
| `HTTP_USER_AGENT` | `device_info.py`, `AuditLog` | Tronqué à 500 chars, stocké brut | ✅ Acceptable |

**R-01 — Détail `X-Forwarded-For`** : trois implémentations identiques (`IPBasedThrottle`, `decorators.py::get_client_ip()`, `account_deletion_views.py::_get_client_ip()`) appliquent toutes le pattern `split(',')[0]` sans vérification d'une liste de proxies de confiance (`TRUSTED_PROXIES`). Un attaquant peut forger librement ce header pour présenter une IP arbitraire et contourner intégralement le rate limiting basé sur l'IP. Il s'agit d'un vecteur d'attaque documenté (OWASP) contre les systèmes de throttling.

**Correction proposée :**
```python
# Exemple de validation avec liste de proxies de confiance
TRUSTED_PROXIES = getattr(settings, 'TENXYTE_TRUSTED_PROXIES', [])

def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for and TRUSTED_PROXIES:
        # Valider que la requête provient d'un proxy de confiance
        remote_addr = request.META.get('REMOTE_ADDR')
        if remote_addr in TRUSTED_PROXIES:
            return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
```

### 4.2 Corps de requête (endpoints exposés)

L'ensemble des 14 endpoints d'entrée utilisent des serializers DRF pour la validation — aucun parsing manuel de JSON n'a été identifié. Ce point est positif. Les validations clés sont :

- **`POST /register/`** : validation multi-couche avec score de complexité (section 6.1). ✅
- **`POST /login/email/`** : pas de timing constant (voir R-04). ❌
- **`POST /2fa/confirm/`** : validation RFC 6238 via `pyotp`. ✅
- **`POST /webauthn/register/complete/`** : délégué à `py_webauthn.verify_*()` (voir R-07). ⚠️
- **`POST /ai/tokens/`** : champs `granted_permissions`, `budget_*` — vérifier la validation des limites numériques (absence de valeurs négatives ou excessives).

### 4.3 Paramètres URL (Path Parameters)

Les paramètres `<str:id>` ne sont pas filtrés par Django au niveau du routage. La sécurité repose entièrement sur l'utilisation de l'ORM (paramétrage automatique). Aucun `raw()` ou `cursor.execute()` n'a été identifié — ce point est validé.

**Point à vérifier :** les endpoints `/users/<str:user_id>/roles/`, `/applications/<str:app_id>/` et `/admin/users/<str:user_id>/ban/` doivent impérativement vérifier l'autorisation au niveau objet (IDOR). Ce vecteur est absent des tests de sécurité actuels (voir R-11).

---

## 5. Couche d'accès — Décorateurs

**Fichier :** `src/tenxyte/decorators.py` (704 lignes)

La couche de décorateurs est architecturalement cohérente et couvre un spectre d'autorisation large :

- **Authentification :** `@require_jwt`, `@require_verified_email`, `@require_verified_phone`
- **Rate limiting :** `@rate_limit(max, window)` — cache Django, clé IP ou user_id
- **RBAC :** `@require_role`, `@require_any_role`, `@require_all_roles`, `@require_permission`, `@require_any_permission`, `@require_all_permissions`
- **Organisation :** `@require_org_context`, `@require_org_membership`, `@require_org_role`, `@require_org_permission`, `@require_org_owner`, `@require_org_admin`
- **AIRS (agents IA) :** `@require_agent_clearance` — double passe RBAC + HITL

### R-02 — Bypass JWT via flag de désactivation

```python
# decorators.py ligne 63
if not auth_settings.JWT_AUTH_ENABLED:
    request.user = None      # ⚠️ user = None !
    request.jwt_payload = None
    return _call_view(...)   # Vue appelée sans authentification
```

Ce chemin de code est documenté `# DANGEROUS — for testing only` mais aucun mécanisme ne détecte ou prévient son activation en production. Si `TENXYTE_JWT_AUTH_ENABLED = False` est appliqué (par erreur de configuration, variable d'environnement non sanitisée, ou fichier `.env` de développement commité), **l'intégralité des vues protégées par `@require_jwt` devient accessible avec `request.user = None`**, provoquant soit un accès non autorisé, soit des crashs 500 si les vues présupposent un user non null.

**Correction proposée :** ajouter une validation au démarrage :
```python
# Dans AppConfig.ready() ou en début de decorators.py
from django.conf import settings as django_settings
import warnings

if not auth_settings.JWT_AUTH_ENABLED:
    if not django_settings.DEBUG:
        raise ImproperlyConfigured(
            "TENXYTE_JWT_AUTH_ENABLED=False is forbidden in production. "
            "Set DEBUG=True to use this flag."
        )
    warnings.warn(
        "JWT authentication is DISABLED. This is a critical security risk.",
        SecurityWarning, stacklevel=2
    )
```

---

## 6. Validation des entrées

### 6.1 Validation des mots de passe

Le système de validation par score (0–10) est une implémentation robuste et bien pensée :

```
Longueur 8–128 chars          → rejet immédiat si hors plage
Majuscule / Minuscule / Chiffre / Caractère spécial → score +1 chacun
≥ 5 caractères uniques         → score +1
Pas de séquences (qwerty, 1234…) → score +1
Pas dans blacklist (~70 mots)   → score +1
Pas d'email/username dans le MDP → score +1
Pas de répétitions (3+)         → score +1
```

**Point fort :** la borne supérieure à 128 caractères est une protection explicite contre les attaques DoS via bcrypt (complexité en O(n) pour les longues chaînes). Ce mécanisme est conforme aux recommandations NIST SP 800-63B. ✅

### 6.2 Validation des emails

La validation est déléguée aux serializers DRF (`EmailField` + `EmailValidator` Django) avec normalisation `.lower()` dans `AuthService`. L'utilisation de `email__iexact=email` en lookup est correcte mais crée un risque de cohérence si des emails en majuscules ont été insérés directement en base.

**Recommandation :** ajouter une contrainte de normalisation au niveau du modèle `User` (override de `save()` ou signal `pre_save`) pour garantir que tous les emails sont stockés en minuscules, indépendamment du chemin d'insertion.

### 6.3 Validation des paramètres URL

Les `<str:id>` Django ne filtrent pas les caractères spéciaux. La sécurité repose sur l'ORM (paramétrage automatique des requêtes). Aucun `raw()` identifié — validé.

---

## 7. Gestion des erreurs & fuite d'information

### 7.1 Comportements anti-énumération (points positifs)

| Situation | Réponse | Verdict |
|-----------|---------|---------|
| Email inexistant au reset password | `200 OK` | ✅ Anti-énumération correct |
| `X-Access-Key` invalide | `401 + APP_AUTH_INVALID` | ✅ Pas de distinction clé/secret |
| User non trouvé au login | `401 + "Invalid credentials"` | ✅ Même message que mauvais MDP |
| Token GDPR invalide | `404` | ✅ Pas de détail |

### 7.2 Fuites d'information identifiées

**R-09 — Messages d'erreur des décorateurs RBAC :**
```
"Role required: admin"        → révèle le code du rôle attendu
"Permission required: users.write" → révèle la permission attendue  
"Organization role "owner" required" → révèle le rôle org
```
Ces messages facilitent la reconnaissance d'une application pour un attaquant ayant obtenu un token JWT valide mais insuffisant. Selon le modèle de menace, ces informations peuvent être considérées acceptables pour les intégrateurs (facilite le débogage) ou problématiques en contexte public.

**Recommandation :** rendre la verbosité configurable via un flag `TENXYTE_VERBOSE_ERRORS` (défaut `False` en production).

**R-08 — `str(e)` dans les réponses d'erreur :**
```python
except SomeException as e:
    logger.error(f"Error: {e}")
    return False, None, str(e)  # ⚠️ Peut exposer paths, noms de tables, messages DB
```
La propagation de `str(e)` dans la réponse HTTP expose potentiellement des informations système (chemins de fichiers, noms de tables, messages d'erreur de base de données). Ce pattern doit être systématiquement remplacé par des messages d'erreur génériques côté client, le détail technique étant conservé côté log serveur.

**Correction proposée :**
```python
except SomeException as e:
    logger.error("Operation failed", exc_info=True)  # Détail dans les logs
    return False, None, "An internal error occurred"  # Message générique côté client
```

---

## 8. Injection & sécurité ORM

### 8.1 Résistance à l'injection SQL — Validé ✅

L'intégralité du codebase utilise l'ORM Django (`.filter()`, `.get()`, `.create()`). Aucun `raw()` ni `cursor.execute()` identifié. Les tests d'injection présents (4 payloads SQL sur `email`, 3 sur `password`) retournent `401` ou `429`, jamais `500`. Cette protection est considérée **solide**.

### 8.2 Résistance XSS

Tenxyte est une API REST JSON pure sans rendu HTML serveur. Les données utilisateur (`first_name`, `last_name`) sont stockées en texte brut (comportement correct pour une API JSON). La responsabilité de l'échappement HTML revient à l'application hôte.

**Point de vigilance :** documenter explicitement dans le README/SECURITY.md que Tenxyte ne sanitize pas les données pour le contexte HTML et que l'intégrateur est responsable de l'échappement XSS dans son frontend.

### 8.3 Comparaisons à temps constant (R-06)

| Emplacement | Méthode | Temps constant ? |
|------------|---------|-----------------|
| `application.verify_secret()` | `bcrypt.checkpw()` | ✅ Nativement constant |
| `OTPCode.verify()` | `self.code == self._hash_code(code)` | ❌ Python `==` |
| `BackupCode.verify_backup_code()` | `code_hash in user.backup_codes` | ❌ Python `in` sur liste |
| `MagicLinkToken.get_valid()` | Lookup DB par hash | ✅ DB fait la comparaison |
| `WebAuthnChallenge.is_valid()` | `py_webauthn.verify_*()` | ✅ Géré par la librairie |

Bien que les codes OTP soient à durée de vie courte et générés aléatoirement (limitant l'utilité pratique d'une timing attack), les bonnes pratiques cryptographiques recommandent `hmac.compare_digest()` pour toute comparaison de valeurs sensibles :

```python
import hmac
# Remplacer
if self.code == self._hash_code(code): ...
# Par
if hmac.compare_digest(self.code, self._hash_code(code)): ...
```

---

## 9. Gestion des secrets & configuration

### 9.1 Secrets dans le code source — Validé ✅

Aucune valeur sensible hardcodée identifiée dans l'ensemble du codebase. Tous les secrets sont lus via `django.conf.settings` : `TENXYTE_JWT_SECRET_KEY`, clés OAuth (Google, GitHub, Microsoft, Facebook), `TWILIO_ACCOUNT_SID/AUTH_TOKEN`, `SENDGRID_API_KEY`. Ce point est conforme aux bonnes pratiques (12-Factor App).

### 9.2 Flags de désactivation dangereux (R-02, R-03)

| Flag | Effet si désactivé | Niveau de risque |
|------|--------------------|-----------------|
| `TENXYTE_JWT_AUTH_ENABLED = False` | Toutes les vues `@require_jwt` accessibles sans token | 🔴 Critique |
| `TENXYTE_RATE_LIMITING_ENABLED = False` | Rate limiting désactivé globalement | 🔴 Haute |
| `TENXYTE_APPLICATION_AUTH_ENABLED = False` | Première couche d'auth bypassée | 🔴 Haute |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False` | Pas de verrouillage après N échecs | 🟠 Moyenne |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS = True` | CORS ouvert à toutes les origines | 🔴 Haute |

**R-03 — CORS ouvert :** la configuration par défaut `TENXYTE_CORS_ALLOW_ALL_ORIGINS = True` représente un risque élevé en production. Les requêtes cross-origin depuis n'importe quel domaine sont autorisées, permettant des attaques CSRF sur les endpoints utilisant des cookies de session et exposant les données API à des sites tiers.

**Correction proposée :** inverser le défaut à `False` et forcer la configuration explicite :
```python
# conf.py
TENXYTE_CORS_ALLOW_ALL_ORIGINS = False  # Défaut sécurisé
TENXYTE_CORS_ALLOWED_ORIGINS = []       # Doit être configuré explicitement
```

**Recommandation globale :** implémenter une vérification au démarrage (`AppConfig.ready()`) qui lève une `ImproperlyConfigured` si l'un des flags de désactivation critique est actif en dehors de `DEBUG=True`.

---

## 10. Dépendances & supply chain

### 10.1 Dépendances directes

| Package | Version min | Statut | Risque |
|---------|------------|--------|--------|
| `Django` | ≥ 5.0 | ✅ LTS actif | Suivre les bulletins `django-security` |
| `djangorestframework` | ≥ 3.14 | ✅ Maintenu | Faible |
| `PyJWT` | ≥ 2.8 | ✅ Vulnérabilité `alg:none` corrigée en v2 | Vérifier qu'aucune version < 2.0 n'est installable |
| `bcrypt` | ≥ 4.0 | ✅ Sûr | Dépendance C (cffi) — auditer la build |
| `pyotp` | ≥ 2.9 | ✅ Pure Python, sûr | Faible |
| `qrcode[pil]` | ≥ 8.0 | ⚠️ Pillow : historique de CVEs | Vérifier la version Pillow effective |
| `google-auth` | ≥ 2.20 | ✅ Maintenu | Faible |
| `requests` | Transitif | ✅ Maintenu | Vérifier les timeouts dans `social_auth_service.py` |

### 10.2 Dépendances optionnelles à risque

| Package | Risque |
|---------|--------|
| `twilio ≥ 9.0` | Large surface client HTTP — données personnelles (SMS) |
| `sendgrid ≥ 6.10` | Emails — données personnelles en transit |
| `django-mongodb-backend ≥ 5.0` | Backend expérimental, moins audité |
| **`py_webauthn`** | **Version non contrainte dans `pyproject.toml`** — risque de régression majeure (R-07) |

**R-07 — `py_webauthn` sans pinning :** la dépendance WebAuthn est importée via lazy import (`_get_webauthn()`) sans contrainte de version. Une mise à jour majeure cassante ne serait pas bloquée par les contraintes de `pyproject.toml`. Ajouter `py_webauthn>=2.0,<3.0` (ou la borne adaptée) dans les dépendances optionnelles.

### 10.3 Commandes de vérification recommandées

```bash
# Audit CVE des dépendances
pip-audit --requirement requirements.txt --fail-on-severity high

# Safety (base NVD + PyPI Advisory)
safety check

# Vérification des dépendances transitives
pip-audit --fix --dry-run
```

---

## 11. Analyse statique (SAST)

### 11.1 Patterns dangereux — Résultats

| Pattern | Présence | Verdict |
|---------|----------|---------|
| `eval()` / `exec()` / `compile()` | ❌ Absent | ✅ Sûr |
| `__import__()` dynamique | ❌ Absent | ✅ Sûr |
| `pickle.loads()` / `pickle.load()` | ❌ Absent | ✅ Sûr |
| `yaml.load()` sans `Loader=` | ❌ Absent | ✅ Sûr |
| `subprocess.call()` / `os.system()` | ❌ Absent | ✅ Sûr |
| `open(user_input)` (path traversal) | ❌ Absent | ✅ Sûr |
| `random.random()` pour secrets | ❌ Absent | ✅ `secrets.token_urlsafe()` utilisé partout |
| `hashlib.sha1()` | ✅ Présent dans `breach_check_service.py` | ⚠️ Intentionnel (protocole k-anonymity HIBP) — faux positif bandit attendu |
| `DEBUG = True` hardcodé | ❌ Absent | ✅ Sûr |
| Secrets hardcodés | ❌ Absent | ✅ Sûr |

### 11.2 Tests de sécurité manquants (R-11)

Les vecteurs suivants ne sont couverts ni par `tests/security/` ni par d'autres suites :

| Vecteur | Risque | Priorité |
|---------|--------|---------|
| **Mass assignment** via `PATCH /me/` (`is_staff`, `is_banned`, `is_superuser`) | Élévation de privilèges | 🔴 Haute |
| **IDOR** sur `/users/<id>/`, `/applications/<app_id>/` | Accès aux données d'autres utilisateurs | 🔴 Haute |
| **Race condition** sur `OTPCode.verify()` | Double vérification simultanée, brute-force | 🟠 Moyenne |
| **Forced browsing** sur chemins admin sans `is_staff` | Escalade horizontale | 🔴 Haute |
| **HTTP method override** (headers `X-HTTP-Method-Override`) | Contournement des vérifications de méthode | 🟡 Faible |
| **Content-Type manipulation** (envoi non-JSON vers endpoints JSON) | Parser confusion / erreurs 500 | 🟠 Moyenne |
| **DoS mot de passe long > 128 chars** | Vérifier que le rejet est bien en O(1) | 🟡 Partiel |

### 11.3 Intégration CI/CD SAST recommandée

```yaml
# .github/workflows/security.yml
jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Bandit
        run: pip install bandit && bandit -r src/tenxyte/ -f json -o bandit.json -ll
        continue-on-error: false
      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/python p/django p/secrets
      - name: pip-audit
        run: pip install pip-audit && pip-audit --fail-on-severity high
```

---

## 12. Logs & observabilité

### 12.1 AuditLog — Données métier (points positifs)

Le modèle `AuditLog` couvre les événements critiques avec une discipline exemplaire : aucun mot de passe, token JWT, refresh token, secret TOTP, `X-Access-Secret`, code OTP ni clé API OAuth n'est loggué. Ce point est **conforme** aux exigences PCI-DSS et RGPD.

### 12.2 Logs techniques — Risques résiduels

```python
# Pattern risqué identifié dans services/
except SomeException as e:
    logger.error(f"Error: {e}")  # ⚠️ str(e) peut exposer des détails internes
```

`str(e)` dans les logs applicatifs peut exposer des paths de fichiers, des noms de tables ou des messages d'erreur DB. **Remplacer systématiquement par `logger.error("msg", exc_info=True)`** qui conserve la stack trace côté serveur sans l'exposer.

### 12.3 Lacunes d'observabilité critiques

| Lacune | Impact | Recommandation |
|--------|--------|----------------|
| **Pas d'alerting temps réel** | Les intrusions ne déclenchent aucune alerte | Webhook Django signal sur `AuditLog.post_save` |
| **Révocation de sessions non tracée** dans AuditLog | Impossibilité d'établir la chronologie d'un incident | Ajouter action `session_revoked` |
| **Pas de `X-Request-ID`** | Impossibilité de tracer une requête de bout en bout | Middleware de propagation du request ID |
| **Circuit breaker AIRS non tracé** | Les suspensions d'agents absentes de l'historique d'audit | Logger dans `circuit_breaker.trigger()` |

### 12.4 Checklist déploiement observabilité

- [ ] Le serveur WSGI/ASGI (Gunicorn, uvicorn) ne logue pas le header `Authorization`
- [ ] `django.request` logger n'inclut pas les corps de requête
- [ ] Logs centralisés (ELK, Datadog, CloudWatch) avec accès restreint et IAM
- [ ] Rétention des logs applicatifs définie (distincte des AuditLog)
- [ ] `TENXYTE_AUDIT_LOGGING_ENABLED = True` en production
- [ ] Alerte configurée après N `login_failed` consécutifs (OWASP recommande N ≤ 5)

---

## 13. Audit des API REST

### 13.1 Codes HTTP — Conformité RFC 9110

La gestion des codes HTTP est correcte et conforme : distinction `401` (non authentifié) vs `403` (authentifié mais non autorisé) appliquée systématiquement. Les serializers DRF retournent `400` pour les erreurs de validation, `429` pour le rate limiting. ✅

### 13.2 Verbosité des messages d'erreur

| Endpoint | Message | Risque |
|---------|---------|--------|
| `POST /login/email/` | `"Invalid credentials"` (email inexistant OU mauvais MDP) | ✅ Aucune énumération |
| `POST /password/reset/request/` | `200 OK "If this email exists..."` | ✅ Anti-énumération |
| `POST /register/` email déjà utilisé | `400 {"email": ["...already exists"]}` | ⚠️ Révèle qu'un email existe |
| `@require_role` échoue | `"Role required: <role_code>"` | ⚠️ Révèle le rôle attendu (R-09) |
| `X-Org-Slug` inconnu | `"Organization not found"` | ⚠️ Confirme qu'un slug n'existe pas |

L'énumération des emails à l'inscription est un compromis UX/sécurité courant. Elle doit être documentée explicitement comme comportement intentionnel avec recommandation de mitigation pour les intégrateurs (CAPTCHA, rate limit strict sur `/register/`).

### 13.3 Timing attack sur le login (R-04)

**Vulnérabilité :** lors d'un login par email, si l'email n'existe pas, la fonction retourne immédiatement (`DoesNotExist` → ~1ms). Si l'email existe mais le mot de passe est incorrect, `bcrypt.checkpw()` s'exécute (~100ms). Cette différence de temps permet à un attaquant de déterminer si un email est enregistré par mesure du temps de réponse, bypassing l'anti-énumération textuelle.

**Correction — Option A (recommandée) :** exécuter bcrypt même si l'email n'existe pas :
```python
DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt())

def authenticate_by_email(self, email, password):
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        bcrypt.checkpw(password.encode(), DUMMY_HASH)  # Temps constant
        return False, None, "Invalid credentials"
    ...
```

**Correction — Option B :** délai artificiel uniforme (moins propre, ajoute de la latence globale).

### 13.4 Fusion automatique de comptes OAuth (R-05)

La fusion automatique de comptes basée sur l'email lors d'une connexion sociale (`social_auth_service.py`) sans confirmation explicite de l'utilisateur est un vecteur d'account takeover. Un attaquant contrôlant un provider OAuth compromis peut usurper l'identité de n'importe quel utilisateur dont il connaît l'email.

**Recommandation :** implémenter une étape de confirmation avant la fusion (email de confirmation envoyé à l'adresse existante), ou documenter clairement cette décision de design et les conditions de confiance accordées aux providers.

---

## 14. Ce qui est correctement géré

Ce tableau synthétise les protections jugées **solides et conformes aux standards** :

| Protection | Mécanisme | Standard de référence |
|-----------|-----------|----------------------|
| Injection SQL | ORM Django paramétré — exclusif | OWASP A03 |
| JWT forgery (`alg:none`) | `algorithms=[self.algorithm]` whitelist explicite | RFC 7518 |
| Token bruteforce | CSPRNG (`secrets.token_urlsafe`) + 256–512 bits d'entropie | NIST SP 800-63B |
| Credential stuffing | Rate limiting multi-niveaux + verrouillage progressif | OWASP |
| Token reuse après logout | Blacklist JTI + révocation refresh token | RFC 7009 |
| Cross-app token usage | Vérification `app_id` dans le token vs header | Defense in depth |
| Password spraying | Throttle exponentiel progressif | OWASP |
| Timing attack sur app secret | `bcrypt.checkpw()` (comparaison nativement constante) | Cryptographie pratique |
| Account enumeration (login) | Réponses uniformes `"Invalid credentials"` | OWASP |
| Account enumeration (reset) | `200 OK` pour emails inexistants | OWASP |
| DoS via bcrypt | Borne supérieure à 128 chars | NIST SP 800-63B |
| Secrets dans le code | Aucun hardcodé — tout via `settings` | 12-Factor App |
| AIRS privilege escalation | Double passe RBAC (token AND utilisateur) | Principle of least privilege |
| Fonctions pseudo-aléatoires | `secrets.token_urlsafe()` exclusivement | Python Security |

---

## 15. Plan de remédiation priorisé

### Bloquant avant publication

| Priorité | Réf. | Action | Effort |
|----------|------|--------|--------|
| 🔴 P0 | R-02 | Ajouter garde-fou `ImproperlyConfigured` si `JWT_AUTH_ENABLED=False` hors `DEBUG` | ~2h |
| 🔴 P0 | R-03 | Inverser le défaut de `TENXYTE_CORS_ALLOW_ALL_ORIGINS` à `False` | ~1h |
| 🔴 P0 | R-11 | Ajouter tests IDOR sur `/users/<id>/`, `/applications/<id>/` | ~1j |
| 🔴 P0 | R-11 | Ajouter tests mass assignment sur `PATCH /me/` | ~4h |
| 🔴 P1 | R-01 | Implémenter `TENXYTE_TRUSTED_PROXIES` et valider `X-Forwarded-For` | ~4h |
| 🔴 P1 | R-04 | Exécuter bcrypt dummy si email non trouvé (timing constant) | ~2h |
| 🟠 P1 | R-07 | Contraindre la version de `py_webauthn` dans `pyproject.toml` | ~30min |
| 🟠 P1 | R-05 | Documenter ou sécuriser la fusion de comptes OAuth | ~1j |

### Recommandé avant publication

| Priorité | Réf. | Action | Effort |
|----------|------|--------|--------|
| 🟠 P2 | R-08 | Remplacer `str(e)` dans les réponses API par messages génériques | ~4h |
| 🟠 P2 | R-11 | Ajouter tests race condition `OTPCode.verify()` | ~4h |
| 🟡 P3 | R-06 | Remplacer `==` par `hmac.compare_digest` pour OTP et backup codes | ~2h |
| 🟡 P3 | R-09 | Flag `TENXYTE_VERBOSE_ERRORS` pour contrôler la verbosité des erreurs RBAC | ~2h |
| 🟡 P3 | — | Ajouter `X-Request-ID` middleware pour la traçabilité | ~4h |
| 🟡 P3 | — | Webhook `AuditLog.post_save` pour alerting temps réel | ~1j |
| 🟡 P4 | — | Relever le seuil de coverage à 80% minimum | ~2j |
| 🟡 P4 | — | Normalisation email au niveau modèle (contrainte `pre_save`) | ~2h |

---

## 16. Conclusion & verdict

Tenxyte v0.9.1.7 est un module d'authentification de conception solide, démontrant une bonne maîtrise des vecteurs d'attaque classiques sur les systèmes d'authentification (SQL injection, JWT forgery, credential stuffing, timing attacks sur les secrets applicatifs). L'architecture en couches (middleware → décorateurs → services), l'usage exclusif de l'ORM Django et les choix cryptographiques (bcrypt, CSPRNG, TOTP RFC 6238) sont des indicateurs positifs de maturité.

Cependant, **le module ne doit pas être publié en l'état.** Quatre points bloquants (R-01, R-02, R-03, R-11) constituent des risques de sécurité directement exploitables ou facilement introduisibles par erreur de configuration, et deux points additionnels (R-04, R-07) sont suffisamment sérieux pour justifier correction avant publication publique sur PyPI.

Une fois les remédiations P0/P1 appliquées, une validation formelle des correctifs et une passe SAST complète (bandit + semgrep) sont recommandées avant la release `1.0.0`.

---

*Audit réalisé sur la base du brief technique Tenxyte v0.9.1.7 — 2026-02-27*  
*Références : OWASP Authentication Cheat Sheet v2023, NIST SP 800-63B, RFC 7519 (JWT), RFC 6238 (TOTP), RFC 9110 (HTTP), OWASP ASVS v4.0*
