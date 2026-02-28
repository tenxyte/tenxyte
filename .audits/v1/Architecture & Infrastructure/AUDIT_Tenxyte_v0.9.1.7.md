# Audit Architecture & Infrastructure
## Tenxyte — Package d'Authentification Python/Django
### Version auditée : `0.9.1.7` · Date : 2026-02-28 · Statut : Beta

---

> **Auditeur** : Analyse automatisée — Architecture & Infrastructure Review  
> **Périmètre** : Architecture logicielle, infrastructure de déploiement, sécurité applicative, conformité réglementaire, gestion des dépendances  
> **Méthodologie** : STRIDE/PASTA, OWASP ASVS L2, CWE Top 25, analyse statique de l'architecture

---

## Sommaire exécutif

Tenxyte est un package Python/Django open-source de composants d'authentification et d'autorisation, distribué sur PyPI sous licence MIT. La version `0.9.1.7` couvre un périmètre fonctionnel remarquablement large pour un package en statut Beta : JWT, RBAC hiérarchique, 2FA (TOTP + OTP), Magic Link, WebAuthn/FIDO2, OAuth social (4 providers), multi-tenancy B2B, conformité RGPD, et un système de délégation de permissions pour agents IA (AIRS).

L'analyse révèle une **base architecturale solide**, avec une couverture de tests à 98.17% et une implémentation rigoureuse de nombreux mécanismes de sécurité. Cependant, plusieurs vulnérabilités et risques résiduels significatifs ont été identifiés qui doivent être adressés **avant publication stable**.

### Tableau de bord des risques

| Domaine | Niveau de risque | Criticité |
|---------|-----------------|-----------|
| Stockage de secrets sensibles en clair (DB) | 🔴 CRITIQUE | Immédiat |
| Partage clé JWT / Django SECRET_KEY | 🔴 CRITIQUE | Immédiat |
| X-Forwarded-For sans proxies de confiance | 🟠 ÉLEVÉ | Avant publication |
| Dépendance `py_webauthn` non contrainte | 🟠 ÉLEVÉ | Avant publication |
| Pillow version non contrainte (CVE actifs) | 🟠 ÉLEVÉ | Avant publication |
| bcrypt sur chaque requête (vecteur DoS) | 🟡 MOYEN | Planifié |
| URLs conditionnelles au module-load | 🟡 MOYEN | Planifié |
| Absence de lock file (reproductibilité) | 🟡 MOYEN | Planifié |
| Audit logs sans signature cryptographique | 🟡 MOYEN | Planifié |
| Migration initiale monolithique | 🟢 FAIBLE | À surveiller |

---

## 1. Architecture générale

### 1.1 Évaluation du modèle de distribution

Tenxyte adopte le modèle de **package installable Django reusable app**, ce qui est le choix architectural correct pour ce type de bibliothèque. L'intégrateur conserve le contrôle total sur son infrastructure (base de données, cache, serveur WSGI/ASGI), et Tenxyte ne s'impose pas dans les décisions de déploiement.

**Points positifs :**

- Respect scrupuleux du pattern Django (`INSTALLED_APPS`, migrations, `settings.py`)
- Modèles swappables (`TENXYTE_USER_MODEL`, etc.) alignés sur le pattern natif `AUTH_USER_MODEL` — permet l'extension sans fork
- Auto-setup via `AppConfig.ready()` et signals Django — réduction de la friction à l'intégration
- Système de configuration centralisé (`conf.py`, 887 lignes) avec presets de sécurité (`starter`, `medium`, `robust`) — bonne pratique pour guider les intégrateurs vers des configurations sûres par défaut

**Point d'attention :**

La documentation doit impérativement préciser que le preset `starter` (JWT 1h, 10 tentatives, pas de breach check, pas d'audit) **ne doit jamais être utilisé en production**. L'absence d'un preset `production` explicite est un risque de mauvaise configuration chez les intégrateurs inexpérimentés.

### 1.2 Structure des répertoires et séparation des responsabilités

La structure `src/tenxyte/` avec séparation `models/`, `services/`, `views/`, `serializers/` respecte une architecture en couches correcte. Les 14 services encapsulent la logique métier indépendamment des vues DRF, ce qui est une bonne pratique de testabilité et de maintenabilité.

La présence de `middleware.py` (6 middlewares), `throttles.py` (12 classes), `decorators.py`, et `filters.py` comme modules distincts indique une bonne modularité.

**Observation :** `conf.py` à 887 lignes représente un fichier de configuration particulièrement volumineux. Bien que fonctionnellement justifié par la richesse des options, une décomposition en sous-modules (`conf/jwt.py`, `conf/auth.py`, `conf/airs.py`) améliorerait la lisibilité et la maintenabilité à long terme.

### 1.3 Couplage framework

Le package est **fortement couplé à Django/DRF**, sans couche d'abstraction permettant un usage framework-agnostique. Ce choix est défendable pour un package qui se positionne explicitement comme une extension Django, mais doit être documenté clairement dans le README pour éviter des tentatives d'intégration hors-périmètre.

---

## 2. Sécurité applicative

### 2.1 🔴 CRITIQUE — Secrets sensibles stockés en clair en base de données

L'analyse du schéma de données révèle que plusieurs champs hautement sensibles sont stockés **en clair** dans la base de données :

| Table | Champ | Risque en cas de dump DB |
|-------|-------|--------------------------|
| `users` | `totp_secret` | Reconstruction complète du facteur TOTP de tous les utilisateurs |
| `refresh_tokens` | `token` (64 chars) | Usurpation de sessions actives sans besoin du mot de passe |
| `agent_tokens` | `token` (48 chars) | Usurpation de délégations agents IA |
| `social_accounts` | `access_token`, `refresh_token` OAuth | Accès aux comptes OAuth des utilisateurs |
| `audit_logs` | IP, user_agent, details JSON | Exposition de PII opérationnelles |

**Impact :** Un attaquant ayant accès à un dump de la base de données (via injection SQL, compromission du compte DB, backup non chiffré, ou accès physique) peut immédiatement usurper l'identité de tous les utilisateurs actifs et contourner le 2FA.

**Recommandations :**

```python
# Option 1 : Chiffrement applicatif avec django-cryptography
from django_cryptography.fields import encrypt

class User(AbstractBaseUser):
    totp_secret = encrypt(models.CharField(max_length=32, null=True))

# Option 2 : Hachage des refresh tokens (pattern déjà utilisé pour magic_link et OTP)
# Stocker SHA-256(token) en DB, comparer SHA-256(token_fourni) à chaque vérification
# Même approche que BlacklistedToken et OTPCode — cohérence architecturale

# Option 3 : Chiffrement au niveau colonne (PostgreSQL pgcrypto)
# Nécessite configuration côté intégrateur — documenter comme best practice
```

La stratégie de hachage des refresh tokens (option 2) est la plus cohérente architecturalement, car elle est déjà appliquée pour les `magic_link_tokens` et `otp_codes`. **Son absence pour les refresh tokens représente une incohérence de sécurité majeure.**

Pour le `totp_secret`, le chiffrement applicatif symétrique est préférable au hachage (car le secret doit être récupérable pour la vérification TOTP).

### 2.2 🔴 CRITIQUE — JWT_SECRET_KEY partage la SECRET_KEY Django par défaut

Par défaut, `JWT_SECRET_KEY` utilise `SECRET_KEY` Django. Cette configuration crée un **vecteur de risque par réutilisation de clé** : la `SECRET_KEY` Django est utilisée pour de nombreuses opérations cryptographiques (sessions, CSRF, signatures d'URLs signées). Si cette clé est compromise ou rotée, **tous les JWT émis deviennent invalides simultanément**, provoquant une déconnexion globale et un incident de disponibilité.

Inversement, si un attaquant obtient la `SECRET_KEY` (via une variable d'environnement exposée, un `.env` committé, etc.), il peut forger des JWT valides indéfiniment.

**Recommandation :** Forcer l'utilisation d'une clé dédiée et lever une `ImproperlyConfigured` exception si `JWT_SECRET_KEY` n'est pas explicitement définie en production.

```python
# conf.py — validation au démarrage
import warnings
from django.core.exceptions import ImproperlyConfigured

if not user_settings.get('JWT_SECRET_KEY'):
    if not settings.DEBUG:
        raise ImproperlyConfigured(
            "TENXYTE_JWT_SECRET_KEY must be explicitly set in production. "
            "Do not rely on Django's SECRET_KEY for JWT signing."
        )
    warnings.warn(
        "JWT_SECRET_KEY defaults to SECRET_KEY. Set TENXYTE_JWT_SECRET_KEY explicitly.",
        SecurityWarning
    )
```

### 2.3 🟠 ÉLEVÉ — X-Forwarded-For sans liste de proxies de confiance

Le module de rate limiting utilise l'IP du client extraite de `HTTP_X_FORWARDED_FOR`. Sans configuration de `TRUSTED_PROXIES`, un attaquant peut **forger ce header** pour contourner entièrement le rate limiting par IP :

```http
POST /api/v1/login/email/ HTTP/1.1
X-Forwarded-For: 1.2.3.4
# → Chaque requête semble provenir d'une IP différente
```

**Impact :** Rend les `LoginThrottle`, `PasswordResetThrottle`, et tous les throttles IP-based inopérants — ouvre la porte au brute force sans limitation.

**Recommandation :** Intégrer la configuration Django `TRUSTED_PROXIES` ou implémenter une validation du header dans `device_info.py`, et **documenter explicitement** que l'intégrateur doit configurer `USE_X_FORWARDED_HOST` et les IPs de proxy de confiance.

### 2.4 Authentification et gestion des tokens JWT

**Points positifs :**

- Algorithme HS256 whitelisté — protection contre l'attaque `alg:none` (CVE-2022-29217)
- JTI UUID v4 sur chaque token — révocation granulaire possible
- Blacklist des tokens révoqués avec cleanup périodique
- Rotation des refresh tokens configurable
- TTL court sur les access tokens (5 min en mode `robust`)

**Point d'attention :** L'algorithme HS256 implique que le même secret signe et vérifie les tokens. Dans une architecture micro-services où plusieurs services vérifieraient les tokens Tenxyte, tous devraient partager ce secret. Pour ce cas d'usage, documenter la migration vers RS256 (clé privée/publique) comme évolution recommandée.

### 2.5 Module 2FA (TOTP, OTP, WebAuthn)

**TOTP :**
- Bibliothèque `pyotp ≥ 2.9` — robuste, aucun CVE connu
- `TOTP_VALID_WINDOW` configurable — attention, une fenêtre > 1 (30s de tolérance de part et d'autre) augmente la surface d'attaque de replay
- Les codes backup sont hashés en SHA-256 — **correct**
- **Observation :** Le TOTP replay dans la fenêtre active n'est pas explicitement adressé. Implémenter un cache des codes TOTP récemment utilisés (TTL 30s) pour prévenir la réutilisation.

**WebAuthn/FIDO2 :**
- Le challenge WebAuthn est stocké en clair en DB avec TTL 5 min — **acceptable** car à usage unique, mais à documenter
- `py_webauthn` non listée dans `pyproject.toml` — voir section dépendances (§4.2)
- L'activation de WebAuthn sans audit spécifique de `webauthn_service.py` est risquée pour la v1.0

### 2.6 Module AIRS (Agent AI Restriction System)

Le module AIRS est architecturalement innovant et sa conception de sécurité est globalement réfléchie :

- Subset de permissions (jamais d'élévation au-delà de l'humain délégant) — **correct**
- Circuit breaker + Dead Man's Switch + HITL — défense en profondeur
- PIIRedactionMiddleware pour masquer les données sensibles aux agents — **bonne pratique**

**Lacunes identifiées :**

Le token agent est stocké en **clair en DB** (48 chars CSPRNG). Appliquer le même pattern de hachage SHA-256 que les autres tokens pour la cohérence architecturale.

La `PIIRedactionMiddleware` opère **uniquement sur les réponses HTTP** — les agents ayant accès direct à la base de données (via ORM dans un contexte Django shell, par exemple) ne sont pas couverts. Documenter clairement cette limitation.

### 2.7 OAuth Social — Risque de prise de contrôle de compte

L'authentification OAuth avec 4 providers (Google, GitHub, Microsoft, Facebook) expose un vecteur d'attaque classique : si un utilisateur existe avec l'email `alice@example.com` et qu'un attaquant crée un compte GitHub avec ce même email non vérifié, le flux OAuth pourrait lier ce compte au compte Alice existant.

**Recommandation :** Vérifier que `social_auth_service.py` conditionne la liaison de compte OAuth à la **vérification préalable de l'email** côté provider avant association automatique. Documenter explicitement ce comportement dans la documentation de sécurité.

---

## 3. Infrastructure et déploiement

### 3.1 Cache et rate limiting en production

Le rate limiting, le circuit breaker AIRS, et la blacklist de tokens utilisent `django.core.cache`. En production sans Redis, le cache Django par défaut est **LocMemCache** — local au processus, non partagé entre workers Gunicorn.

**Conséquence pratique :** Avec 4 workers Gunicorn, le rate limiting effectif est multiplié par 4. Un attaquant peut envoyer 5 tentatives × 4 workers = 20 requêtes de login par minute sans déclencher aucun throttle.

**Recommandation :** Lever une `ImproperlyConfigured` exception (ou au minimum un avertissement critique au démarrage) si `django.core.cache.backends.locmem.LocMemCache` est détecté en mode production (`DEBUG=False`) avec le rate limiting activé.

```python
# Vérification au démarrage dans AppConfig.ready()
from django.core.cache import cache
if not settings.DEBUG and isinstance(cache, LocMemCache) and tenxyte_settings.RATE_LIMITING_ENABLED:
    warnings.warn(
        "LocMemCache detected with rate limiting enabled. "
        "Rate limits are per-worker and ineffective in multi-process deployments. "
        "Configure Redis cache for production.",
        RuntimeWarning
    )
```

### 3.2 Compatibilité ASGI / Async Django

Toutes les vues Tenxyte sont **100% synchrones**. Avec Django 5.x et son support ASGI natif, les intégrateurs pourraient déployer Tenxyte derrière Daphne ou Uvicorn.

**Impact :** En mode ASGI, Django exécute les vues sync dans un pool de threads via `sync_to_async`. Le `ContextVar` utilisé dans `tenant_context.py` fonctionne correctement en mode async (les `ContextVar` Python sont nativement async-safe). Cependant, l'absence de tests explicites ASGI est un risque résiduel, notamment pour les middlewares.

**Recommandation :** Ajouter des tests d'intégration ASGI dans `tests/integration/` et documenter le support ASGI comme "expérimental" jusqu'à validation complète.

### 3.3 Tâches périodiques — Absence de scheduler intégré

`BlacklistedToken.cleanup_expired()` doit être planifié manuellement par l'intégrateur. Sans cette tâche, la table `blacklisted_tokens` grossit indéfiniment, dégradant les performances des vérifications JWT.

**Recommandation :** Documenter explicitement les tâches à planifier avec les intervalles recommandés, et fournir des exemples de configuration pour Celery Beat et cron :

```python
# Tâches périodiques à configurer (documentation recommandée)
CELERY_BEAT_SCHEDULE = {
    'cleanup-blacklisted-tokens': {
        'task': 'tenxyte.tasks.cleanup_blacklisted_tokens',
        'schedule': crontab(hour=3, minute=0),  # Quotidien à 3h
    },
    'cleanup-expired-otp': {
        'task': 'tenxyte.tasks.cleanup_expired_otp',
        'schedule': crontab(minute='*/15'),  # Toutes les 15 min
    },
    'cleanup-webauthn-challenges': {
        'task': 'tenxyte.tasks.cleanup_webauthn_challenges',
        'schedule': crontab(minute='*/10'),
    },
}
```

### 3.4 Performance — bcrypt à chaque requête applicative

`ApplicationAuthMiddleware` vérifie `bcrypt(access_secret)` sur **chaque requête authentifiée**. bcrypt est intentionnellement lent (coût computationnel élevé). Sur un serveur à haute charge (>100 req/s), cette vérification peut représenter un goulot d'étranglement significatif et constitue un **vecteur de DoS** : un attaquant envoyant des requêtes avec n'importe quel `X-Access-Key` valide mais `X-Access-Secret` invalide force des calculs bcrypt coûteux.

**Recommandations :**

1. Mettre en cache le résultat de la vérification `bcrypt(access_secret)` dans Redis avec un TTL court (60-300 secondes) : `cache.set(f"app_auth:{access_key}:{hash(access_secret)}", True, timeout=300)`
2. Appliquer un rate limit strict sur les erreurs d'authentification applicative avant d'atteindre le calcul bcrypt
3. Documenter le facteur de coût bcrypt recommandé et son impact sur les performances selon la charge attendue

### 3.5 Migration initiale monolithique

La migration `0001_initial.py` (35 KB) crée toutes les tables en une seule transaction. Sur une base de données volumineuse ou avec des contraintes de migration live (zero-downtime deployments), cette approche peut poser des problèmes de verrouillage.

**Recommandation :** Pour la v1.0, envisager de scinder la migration initiale en plusieurs migrations thématiques (`0001_users_rbac`, `0002_tokens_sessions`, `0003_organizations`, `0004_airs`). Cela facilite également les rollbacks partiels en cas de problème.

### 3.6 URLs conditionnelles au module-load

```python
# urls.py — exemple du problème
if org_settings.ORGANIZATIONS_ENABLED:
    urlpatterns += organizations_urls
```

Si la configuration Django est rechargée ou si des workers ont des états de configuration différents (race condition au démarrage, modification de settings à chaud), certains workers peuvent avoir des URL routing différents.

**Recommandation :** Utiliser une vue qui retourne 404 ou 503 si le module est désactivé, plutôt que de conditionner l'inclusion des URLs au moment du chargement du module.

---

## 4. Gestion des dépendances (SCA)

### 4.1 Vulnérabilités actives

| Package | CVE | Sévérité | Action requise |
|---------|-----|----------|----------------|
| `Pillow` (via qrcode) | CVE-2023-44271 (DoS), CVE-2022-45199 (buffer overflow), CVE-2021-25289 (RCE) | 🔴 CRITIQUE | Contraindre `Pillow >= 10.0.1` dans `pyproject.toml` |
| `requests` (transitif) | CVE-2023-32681 (redirect header leak) | 🟠 ÉLEVÉ | Contraindre `requests >= 2.31.0` |
| `PyJWT` | CVE-2022-29217 (corrigé en v2.4+) | ✅ Couvert | Vérifier whitelist d'algorithme en place |

### 4.2 Dépendances non contraintes

**`py_webauthn`** : Non listée dans `pyproject.toml`, importée lazily dans `webauthn_service.py`. L'absence de contrainte de version signifie qu'une version majeure avec changements breaking ou contenant une vulnérabilité peut être installée silencieusement.

**Action requise :**

```toml
# pyproject.toml — ajout recommandé
[project.optional-dependencies]
webauthn = ["py_webauthn>=2.0,<3.0"]
```

Et documenter l'installation : `pip install tenxyte[webauthn]`

**`Pillow`** : Version effectivement installée non contrainte (dépendance transitive via `qrcode[pil]`). Des CVE critiques (dont un RCE) existent sur les versions antérieures.

```toml
# Contrainte minimale à ajouter
"Pillow>=10.0.1",  # CVE-2023-44271, CVE-2022-45199, CVE-2021-25289
```

### 4.3 Absence de lock file

Tenxyte ne dispose pas de `requirements.txt` épinglé ni de `poetry.lock`. Deux installations du même package `tenxyte==0.9.1.7` dans des environnements différents peuvent avoir des versions transitives différentes.

**Impact :** Reproductibilité des builds impossible, SCA difficile, risque d'installation silencieuse de versions vulnérables.

**Recommandation :** Publier un fichier `requirements-locked.txt` (via `pip-compile`) dans le dépôt GitHub, et activer Dependabot pour les alertes automatiques.

### 4.4 Pipeline CI/CD recommandé pour la sécurité des dépendances

```yaml
# .github/workflows/security.yml
name: Security Audit
on: [push, pull_request, schedule: [{cron: '0 6 * * 1'}]]

jobs:
  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install audit tools
        run: pip install pip-audit safety bandit
      - name: SCA - pip-audit
        run: pip-audit --fail-on-severity high
      - name: SCA - safety
        run: safety check --full-report
      - name: SAST - bandit
        run: bandit -r src/tenxyte/ -ll -f json -o bandit_report.json
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: '*_report.json'
```

---

## 5. Conformité RGPD / GDPR

### 5.1 Analyse des mécanismes implémentés

| Exigence RGPD | Article | Implémentation | Évaluation |
|--------------|---------|----------------|------------|
| Droit à l'effacement | Art. 17 | Soft delete + anonymisation des PII | ✅ Correct — anonymisation exhaustive |
| Droit à la portabilité | Art. 20 | Export JSON | ✅ Présent |
| Journalisation des accès | Art. 30 | AuditLog (IP, user_agent, action) | ✅ Présent |
| Minimisation (agents IA) | Art. 5(1)(c) | PIIRedactionMiddleware | ⚠️ Limité à la couche HTTP |
| Délai de rétention | Art. 5(1)(e) | AccountDeletionRequest avec délai de grâce | ✅ Présent |
| Consentement explicite | Art. 7 | Non implémenté (hors périmètre) | ℹ️ À la charge de l'intégrateur |
| DPA / Transferts hors UE | Art. 44-49 | Non adressé | ℹ️ À documenter pour SendGrid/Twilio |

### 5.2 Points d'attention RGPD

**`audit_logs`** stocke des IPs et user-agents sans mécanisme de rétention automatique configuré. En RGPD, les logs opérationnels sont considérés comme des données personnelles. Documenter la durée de rétention recommandée et fournir une commande de purge ou une tâche périodique.

**SendGrid / Twilio** : L'utilisation de ces services implique un transfert de données personnelles (email, numéro de téléphone) vers des sous-traitants américains. L'intégrateur doit s'assurer que ces transferts sont encadrés par des mécanismes appropriés (SCCs, DPA). Documenter cette obligation dans le README.

**Export RGPD (Art. 20)** : Vérifier que l'export JSON inclut les données des comptes OAuth liés (`social_accounts`) et les logs d'audit relatifs à l'utilisateur — ces données sont soumises au droit à la portabilité.

---

## 6. Qualité du code et observabilité

### 6.1 Couverture de tests

La couverture à **98.17%** sur 1408 items de test est exceptionnelle et constitue l'un des points les plus solides du package. La présence de tests dédiés à la sécurité (`tests/security/`) et aux scénarios multi-base de données (`tests/multidb/`) témoigne d'une rigueur au-dessus de la moyenne.

**Lacune :** La couverture minimale configurée dans `pytest.ini` est de **60%** (`--cov-fail-under=60`). Cette valeur est trop basse pour un package de sécurité critique. Aligner le seuil avec la réalité du projet :

```ini
# pyproject.toml
addopts = "--cov=tenxyte --cov-report=html --cov-report=term --cov-fail-under=90"
```

**Lacune :** Seuls **2 fichiers** de tests de sécurité explicites sont répertoriés dans `tests/security/`. Étendre la couverture aux vecteurs d'attaque identifiés dans l'analyse STRIDE (forge JWT, bypass OAuth, injection de headers).

### 6.2 Observabilité et monitoring

Tenxyte fournit un `AuditLog` complet et un `dashboard_views.py` pour les statistiques. Cependant, **aucun mécanisme d'alerting en temps réel** n'est intégré :

- Pas d'émission de métriques (Prometheus, StatsD, Datadog)
- Pas de signaux Django sur les événements de sécurité (brute force détecté, lockout, login depuis nouvel appareil)
- Pas d'intégration webhook pour les alertes de sécurité

**Recommandation :** Émettre des signaux Django sur les événements critiques, permettant aux intégrateurs de les connecter à leurs systèmes d'alerte :

```python
# signals.py — exemples recommandés
account_locked = Signal()           # providing_args: ['user', 'ip', 'attempts']
suspicious_login_detected = Signal() # providing_args: ['user', 'ip', 'reason']
agent_circuit_breaker_triggered = Signal()
```

### 6.3 Intégrité des audit logs

Les entrées `AuditLog` ne sont pas signées cryptographiquement. Un attaquant ayant accès en écriture à la base de données peut modifier ou supprimer des entrées de log sans laisser de trace.

Pour un package positionné sur la conformité et la sécurité, documenter cette limitation et proposer une stratégie de protection des logs (append-only database user, export vers un système de log immuable comme CloudWatch ou Loki).

---

## 7. Recommandations prioritaires

### Blocantes pour la publication en v1.0

| # | Recommandation | Effort | Impact |
|---|----------------|--------|--------|
| R1 | Hasher les `refresh_tokens` en DB (SHA-256, cohérence avec OTP/magic_link) | Moyen | 🔴 CRITIQUE |
| R2 | Chiffrer `totp_secret` en DB (AES-256 via django-cryptography ou champ custom) | Moyen | 🔴 CRITIQUE |
| R3 | Contraindre `Pillow >= 10.0.1` dans `pyproject.toml` | Faible | 🔴 CRITIQUE |
| R4 | Ajouter `py_webauthn` comme extra optionnel contraint dans `pyproject.toml` | Faible | 🟠 ÉLEVÉ |
| R5 | Avertissement/erreur si `JWT_SECRET_KEY` == `SECRET_KEY` Django en production | Faible | 🔴 CRITIQUE |
| R6 | Documenter et valider la configuration `TRUSTED_PROXIES` pour le rate limiting | Faible | 🟠 ÉLEVÉ |
| R7 | Contraindre `requests >= 2.31.0` (dépendance transitive, CVE-2023-32681) | Faible | 🟠 ÉLEVÉ |

### Hautement recommandées avant publication

| # | Recommandation | Effort |
|---|----------------|--------|
| R8 | Cache Redis obligatoire en production pour le rate limiting (warning au démarrage) | Faible |
| R9 | Hasher les `agent_tokens` en DB (cohérence architecturale) | Moyen |
| R10 | Hasher les OAuth `access_token` / `refresh_token` en DB | Moyen |
| R11 | Remplacer le preset `starter` par un preset `development` avec avertissement clair | Faible |
| R12 | Publier un `requirements-locked.txt` et activer Dependabot | Faible |
| R13 | Corriger le seuil de coverage à 90% dans `pyproject.toml` | Faible |
| R14 | Ajouter des signaux Django sur les événements de sécurité critiques | Moyen |
| R15 | Documenter les tâches périodiques à planifier avec exemples Celery Beat | Faible |

### Évolutions pour les versions futures

| # | Recommandation | Horizon |
|---|----------------|---------|
| R16 | Support RS256 pour architectures multi-services | v1.1 |
| R17 | Refactoring `conf.py` en sous-modules thématiques | v1.1 |
| R18 | Tests d'intégration ASGI explicites | v1.1 |
| R19 | Rétention automatique des `audit_logs` | v1.2 |
| R20 | Décomposition de la migration initiale | v1.2 |

---

## 8. Conclusion

Tenxyte `0.9.1.7` est un package techniquement ambitieux qui adresse un périmètre fonctionnel large avec une qualité de code et une couverture de tests remarquables. L'architecture est globalement solide, bien structurée, et suit les conventions Django.

Cependant, **deux vulnérabilités critiques** (secrets sensibles en clair en DB, partage de clé JWT/Django) et **deux risques élevés** (Pillow non contraint avec CVE actifs, X-Forwarded-For sans proxies de confiance) **doivent impérativement être corrigés avant toute publication en v1.0 stable**.

Une fois ces corrections appliquées, Tenxyte présente un niveau de maturité sécurité supérieur à la majorité des packages d'authentification Django disponibles sur PyPI. Le module AIRS (délégation de permissions aux agents IA) est particulièrement innovant et bien conçu pour un espace encore peu standardisé.

**Verdict : Publication en v1.0 conditionnelle à la résolution des items R1–R7.**

---

*Audit réalisé le 2026-02-28 · Tenxyte v0.9.1.7 · Méthodologie : STRIDE, OWASP ASVS L2, CWE Top 25*
