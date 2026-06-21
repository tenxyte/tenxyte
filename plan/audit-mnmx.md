OK, je reprends là où j'en étais. Les deux agents d'audit sont revenus, et j'ai accumulé pas mal d'observations directes. Je consolide tout ça maintenant en un audit propre. Laisse-moi d'abord relire les résultats des agents et vérifier quelques points clés.

Pas de notes sauvegardées. Je relance les vérifications clés pour pouvoir te sortir un audit solide et factuel — basé sur le code réel, pas sur des suppositions.

J'ai assez de matière pour un audit solide et concret. Voici mon diagnostic — basé sur le code réel, pas la doc.

---

# 🩺 Audit complet — `tenxyte` v0.9.5

## TL;DR (la vraie réponse à ta question)

**Tenxyte est un package Python d'auth Django/FastAPI ambitieux et sincèrement impressionnant sur le papier** : JWT + RBAC + 2FA + Magic Links + Passkeys + Social OAuth + B2B multi-tenant + un système de tokens pour agents IA (AIRS) que personne d'autre n'a. ~29 200 lignes de code, ~30 700 lignes de tests (les tests dépassent le code — bon signe), 266 commits depuis février 2026, 4 contributeurs, CI sur Python 3.10–3.13 × Django 4.2–6.0.

**Mais en dessous, c'est un build qui se présente plus mature qu'il ne l'est.** Bêta réelle avec plusieurs "Phase 2" non livrées, deux/trois patterns de sécurité qui ne passent pas un audit sérieux, et un défaut de cohérence version/structure trahissant la vitesse à laquelle ça a été assemblé. Avant d'être une alternative sérieuse à Auth0/Clerk pour un client en prod, il y a un travail réel à faire — je te liste tout.

Score global que je donnerais honnêtement : **6.5/10 en beta, 4/10 pour prod** (à cause des points critiques ci-dessous).

---

## 🔴 CRITIQUES (à régler avant toute mise en prod)

### 1. Bcrypt avec pré-hash SHA-256 — pattern qui se mord la queue
**Fichier** : `src/tenxyte/adapters/django/crypto_service.py:49-53` et `:67-71`, plus `src/tenxyte/models/auth.py:319` et `src/tenxyte/models/security.py:304`

```python
# Pre-hash with SHA256 for bcrypt length compatibility
pre_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
return bcrypt.hashpw(pre_hash.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
```

Le code a déjà des commentaires `lgtm[py/weak-sensitive-data-hashing]` et `codeql[py/weak-sensitive-data-hashing]` qui **admettent** que c'est faible. Le SHA-256 n'apporte aucune sécurité ici — au contraire :
- Le mot de passe est tronqué à 64 caractères hex, ce qui **détruit l'entropie** (1.5 bits/car → 4 bits/car max sur 64 chars).
- bcrypt accepte des mots de passe jusqu'à **72 bytes nativement**, pas de problème de "length compatibility". Ce pré-hash est une légende urbaine.
- C'est recopié à 4 endroits différents (DRY violé).
- Les `# noqa` de lgtm/codeql ne suppriment pas la vulnérabilité, juste l'alerte.

**Fix** : supprimer le pré-hash. bcrypt direct, ou passer à Argon2 (`argon2-cffi`) qui gère nativement les longs mots de passe.

### 2. Validation des algorightmes JWT — OK, mais…
**Fichier** : `src/tenxyte/core/jwt_service.py:450`

```python
algorithms=[self.algorithm]
```
**Bon point** : `algorithms=` est bien passé à `jwt.decode()` → pas de confusion `none`/`HS256`/`RS256`. C'est solide. *Pas un bug, juste un highlight positif dans un projet où on s'attendrait au pire.*

### 3. Versioning incohérent
| Source | Version |
|---|---|
| `pyproject.toml:7` | `0.9.5` |
| `src/tenxyte/__init__.py:50` | `"0.0.8.3.9.7"` |
| `CHANGELOG.md` | "current = 0.9.4" |
| `next-steps.md` | "0.9.3.1.5.2" |
| 4 versions différentes en circulation | 🤦 |

**Impact** : le packaging va casser tôt ou tard. `pip show tenxyte` retournera `0.0.8.3.9.7` alors que le tag/release est 0.9.5. À fixer en une ligne, mais révélateur.

### 4. Middleware Application auth — placeholder "Phase 2" en prod
**Fichier** : `src/tenxyte/adapters/django/middleware.py:217-241`

```python
# TODO: Inject ApplicationRepository in Phase 2
# TODO: Create DjangoApplicationRepository in Phase 2
class PlaceholderApplicationRepository:
    def get_by_access_key(self, access_key: str):
        from tenxyte.models import Application
        try:
            return Application.objects.get(access_key=access_key, is_active=True)
```

Le `ApplicationAuthCoreMiddleware` est **instancie avec un placeholder** parce que le `DjangoApplicationRepository` n'existe pas. C'est fonctionnel par accident, mais l'architecture hexagonale est cassée à cet endroit précis : l'adapter "Django" parle directement à l'ORM au lieu de passer par le port. Même problème 4 fois dans `core/middleware.py` (lignes 397, 412, 416, 424) : JWT, CORS, org context → tout marqué `Phase 2`.

---

## 🟠 HAUTE PRIORITÉ

### 5. `print()` qui fuit dans la prod
**Fichiers** :
- `src/tenxyte/adapters/django/email_service.py:119,147` — erreurs d'envoi email
- `src/tenxyte/adapters/django/repositories.py:40,515` — `print(user.id, user.email)` ← **PII qui fuite en stdout** ⚠️
- `src/tenxyte/adapters/django/settings_provider.py:30,84` — `print(settings.jwt_secret)` ← **secret JWT en clair dans les logs** 🚨
- `src/tenxyte/core/env_provider.py:36` — idem

`src/tenxyte/core/email_service.py:534-549` c'est le mode "Console" qui s'affiche dans la console — ça c'est OK par design. Mais les `print()` dans les adapters Django et le `settings_provider` ne sont pas des consoles emails, ce sont des fuites de PII/secret en prod.

**Fix** : remplacer par `logger.warning(...)` ou supprimer.

### 6. Test coverage réelle vs annoncée
- Le README dit "1553 tests, 100% pass rate"
- J'ai compté **2 390 tests** dans 128 fichiers
- `pyproject.toml` impose `--cov-fail-under=90`
- CI fait `pytest tests/core/ -p no:django --no-cov -q` (sans coverage sur la matrix) puis coverage **uniquement sur Python 3.12**
- La matrix Django/Python a `fail-fast: false` → un échec ne bloque pas la matrix
- Tests FastAPI : 4 fichiers seulement (`tests/integration/fastapi/unit/`), contre 87 dans `tests/integration/django/unit/`
- Aucun test d'intégration end-to-end côté FastAPI, juste des unit tests sur les modèles/repos

→ **L'adapter FastAPI est clairement un PoC**, pas une intégration production-ready. La doc le dit d'ailleurs : "FastAPI (partial)".

### 7. Cache-poisoning attack sur X-Access-Secret
**Fichier** : `src/tenxyte/middleware.py:72-77`

```python
secret_hash = hashlib.sha256(access_secret.encode("utf-8")).hexdigest()
cache_key = f"app_auth_ok_{application.id}_{secret_hash}"

if not cache.get(cache_key):
    if not application.verify_secret(access_secret):
        return JsonResponse(...401...)
    cache.set(cache_key, True, 60)
```

Le secret est SHA-256é pour faire une clé de cache — c'est ok fonctionnellement. Mais :
- Le SHA-256 d'un secret est **une clé de cache déterministe** → un attaquant qui flood avec un mauvais secret peut **remplir le cache** (1 entrée valide pendant 60s max par bon secret, mais il peut faire 10⁶ entrées invalides pour DoS).
- 60s de cache sur une auth de secret serveur, c'est long : si on révoque une `Application`, elle reste valide 60s pour les requêtes déjà passées.
- Pas de `cache.incr()` / rate-limiting sur la construction de la clé.

Pas catastrophique, mais à surveiller.

### 8. WebAuthn et OAuth — besoin de revue ciblée
Je n'ai pas creusé ligne par ligne (trop long pour cet audit) mais :
- `src/tenxyte/core/webauthn_service.py` (~16k bytes)
- `src/tenxyte/services/social_auth_service.py` (~21k bytes)

Le **README annonce** PKCE, state parameter, redirect_uri whitelist. Le code semble cohérent (vu le `is_redirect_uri_allowed` exact-match et la mention de PKCE dans le changelog 0.9.4). Mais sans lecture complète je ne le certifie pas. **Recommandation** : un audit dédié WebAuthn + OAuth avant prod.

### 9. Multi-DB : MongoDB est-il vraiment supporté ?
`tests/integration/django/multidb/` a `settings_mongodb.py`. Mais la doc dit qu'il faut un fix spécial (`DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` + `MIGRATION_MODULES`). Et `tests/integration/django/multidb/` ne contient que **2 fichiers de settings + conftest + test_db_***. C'est un début, pas une couverture. Le CI ne semble pas tourner la matrix MongoDB.

→ MongoDB = annoncé, partiellement implémenté, pas réellement testé en CI.

---

## 🟡 MOYEN

### 10. Architecture hexagonale — partiellement tenue
- ✅ `core/` n'importe **pas** Django directement (vérifié avec grep `from django` → 0 hits dans `src/tenxyte/core/`).
- ✅ Ports bien définis dans `ports/repositories.py`
- ⚠️ Mais l'`ApplicationRepository` est un **placeholder** (voir point 4)
- ⚠️ Le `tenant_context.py` et `middleware.py` lisent directement `from django.conf import settings` dans plusieurs endroits

L'objectif "framework-agnostic" est tenu pour ~80% du code. Les 20% restants sont précisément là où c'est important (auth middleware, settings).

### 11. Sécurité globalement OK sur JWT
J'ai cherché les classiques :
- ✅ `algorithms=[self.algorithm]` partout dans `jwt.decode`
- ✅ `iss`/`aud` validés si configurés
- ✅ `jti` obligatoire → blacklist fonctionne
- ✅ `SENSITIVE_CLAIM_KEYS` blacklisté côté génération
- ✅ Clé de rotation via `JWT_PREVIOUS_SECRET_KEY`
- ✅ `hmac.compare_digest` utilisé pour les codes OTP (modèle `operational.py:95`) et crypto (`crypto_service.py:135`)
- ✅ Application secret hashé en bcrypt (`models/application.py:78`)

C'est le **point fort du projet** : la crypto JWT et la gestion des secrets sont propres, à l'exception du problème bcrypt/SHA-256.

### 12. Tests de sécurité
Trois fichiers dans `tests/integration/django/security/` :
- `test_idor_mass_assignment.py` ← **excellent**, exactement ce qu'il faut
- `test_race_conditions.py` ← **excellent**
- `test_security.py`

C'est mieux que ce que 95% des packages font. Mais vérifie qu'ils tournent réellement en CI (le job `django-tests` les exécute probablement, mais je n'ai pas vu de job dédié sécurité).

### 13. Documentation
- 703 lignes de README en EN, 28k bytes de README en FR
- Multilingue (EN + FR) — rare et appréciable
- `docs/en/` et `docs/fr/` miroirs
- Guides dédiés : quickstart, FastAPI, AIRS, organizations, settings, security, migration, troubleshooting
- Outils de validation : `scripts/validate_*.py`
- Génération auto : Postman collection, OpenAPI schema, site statique
- **Mais** : 4 versions dans 4 fichiers différents (cf. point 3) — incohérence maintenance

→ La doc est le **deuxième point fort** du projet après les tests.

### 14. Velocity / activité
- 266 commits sur ~4 mois
- Dépendabot actif (PRs régulières)
- 1 contributeur principal (boboprem1 = ~65% des commits) + 1 secondaire + Dependabot
- Beaucoup de merges de `develop` (suggère process de branches)
- **Risque bus factor = 1** sur la moitié du code

---

## 🟢 POSITIF (à préserver)

| Aspect | Note |
|---|---|
| Tests (quantité, organisation core/django/sécurité) | A |
| Architecture hexagonale (au moins l'intention) | B+ |
| Crypto JWT (alg pinning, rotation, blacklist) | A- |
| Surface fonctionnelle (RBAC + AIRS + 2FA + WebAuthn + OAuth) | A+ |
| Documentation (multilingue, complète) | A- |
| CI multi-Python × multi-Django | A |
| Coverage gate à 90% | B+ |
| Outils de validation/gen (OpenAPI, Postman) | A |
| MongoDB / multi-DB | C (annoncé, peu testé) |
| Bcrypt usage | D (le pré-hash est un anti-pattern) |
| FastAPI adapter | C (PoC, pas prod) |

---

## 🎯 Recommandations par priorité

**Avant de taguer la prochaine release (0.9.6 ou 0.9.5.1) :**
1. Fixer le bcrypt pré-hash → un seul endroit, sans SHA-256 préalable
2. Aligner les 4 versions divergentes
3. Supprimer les `print()` qui leakent PII/secret
4. Supprimer ou implémenter le `PlaceholderApplicationRepository`

**Avant de revendiquer "production-ready" :**
5. Implémenter les 4 TODOs "Phase 2" dans `core/middleware.py`
6. Tests d'intégration FastAPI réels (pas juste unit)
7. Activer MongoDB en CI matrix
8. Audit WebAuthn + OAuth dédié
9. Ajouter un deuxième mainteneur (bus factor)

**Nice to have :**
10. Découpler `tenant_context.py` et `middleware.py` du `django.conf.settings`
11. Réduire la fenêtre de cache sur X-Access-Secret (60s → 5-10s)
12. Ajouter un `settings.LOG_REDACTION` pour les champs sensibles

---

## Verdict honnête

Pour un **projet personnel/expérimental** : c'est du très beau travail, manifestement écrit par quelqu'un qui sait ce qu'il fait (les tests de sécurité IDOR/race-conditions, c'est pas courant).

Pour un **package que tu mettrais dans un client en prod** : il y a 4-5 points critiques à régler d'abord. Le code n'est pas "mal écrit" — il est **incomplet à des endroits stratégiques** (placeholder repo, TODOs Phase 2, FastAPI en PoC), et la crypto a un anti-pattern qui se reproduit.

Si c'est ton projet : tu as une base solide, mais annonce-le clairement comme **0.9 beta incomplète**, pas comme "production-ready" / "self-hosted Auth0" comme le marketing du README le suggère. Et règle le bcrypt AVANT tout le reste — c'est la note qui tombera en revue sécurité externe.

---

Tu veux que je creuse un point en particulier ? Je peux faire une revue ciblée WebAuthn/OAuth, ou un patch concret sur le bcrypt si tu veux que je l'attaque.