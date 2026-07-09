# 📋 Plan d'action — `tenxyte` v0.9.5

> Basé sur l'audit `plan/audit-mnmx.md` du 2026-06-11.
> Score actuel : **6.5/10 en beta**, **4/10 pour prod**.
> Objectif cible : **8.5/10 en beta**, **8/10 pour prod** après Phase 3.

## Convention de sévérité

- 🔴 **CRITIQUE** : bloque toute mise en prod
- 🟠 **HAUTE** : doit être résolu avant le tag "production-ready"
- 🟡 **MOYENNE** : dette technique à régler sur le moyen terme
- 🟢 **BASSE** : nice to have, qualité de vie

## Convention de statut

- `[ ]` à faire
- `[~]` en cours
- `[x]` terminé
- `[!]` bloqué

---

# 🔴 Phase 1 — Stop-the-bleeding (avant la prochaine release 0.9.6)

> **Durée estimée** : 1 à 2 semaines.
> **Gating** : aucun de ces items ne doit rester ouvert pour qu'un client puisse évaluer `tenxyte` sérieusement.
> **Release** : `0.9.6` (patch de sécurité).

## 1.1 — Bcrypt : supprimer le pré-hash SHA-256 (audit §1)

- [ ] **1.1.1** — Décider de la stratégie hashing : bcrypt direct (sans pré-hash) **OU** migration vers Argon2 (`argon2-cffi`).
  - Décision recommandée : **Argon2** (gère nativement les longs mots de passe, moderne, pas de légende urbaine à expliquer).
  - Alternative conservatrice : **bcrypt direct**, sans le pré-hash, en gardant l'API stable.
- [ ] **1.1.2** — Modifier `src/tenxyte/adapters/django/crypto_service.py` :
  - Supprimer `import hashlib` et le bloc `pre_hash = hashlib.sha256(...).hexdigest()` aux lignes 49-53 et 67-71.
  - Remplacer par bcrypt direct (`bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())`).
  - Supprimer les commentaires `# lgtm[py/weak-sensitive-data-hashing] # codeql[py/weak-sensitive-data-hashing]` (devenus inutiles).
- [ ] **1.1.3** — Modifier `src/tenxyte/models/auth.py:319` et `:329` (même pattern dupliqué).
- [ ] **1.1.4** — Modifier `src/tenxyte/models/security.py:304` (idem).
- [ ] **1.1.5** — Centraliser la logique hashing dans `tenxyte.core.crypto` (créer le module si absent) pour éviter la duplication à 4 endroits (DRY).
- [ ] **1.1.6** — Ajouter un test de régression : un mot de passe > 72 bytes doit toujours être hashé correctement (cap actuel cassé si on garde le SHA-256 hex).
- [ ] **1.1.7** — Écrire une **migration de données** `0024_hash_format_migration.py` :
  - Pour chaque `User` existant, vérifier que `password_hash` commence par `bcrypt$...` ou `argon2$...`.
  - Si l'ancien format SHA-256→bcrypt est détecté, **rehasher** à la prochaine connexion (`needs_rehash = True` côté `set_password`).
  - Tester avec une base de données SQLite de dev contenant ~1000 users fictifs.
- [ ] **1.1.8** — Mettre à jour le test `tests/integration/django/unit/test_auth_service_core.py` avec un cas mot de passe long.
- [ ] **1.1.9** — Documenter le choix dans `docs/en/security.md` et `docs/fr/security.md` (section "Password storage").
- [ ] **1.1.10** — Ajouter une note dans `CHANGELOG.md` sous `## [0.9.6] - Security`.

## 1.2 — Versioning : aligner les 4 sources (audit §3)

- [ ] **1.2.1** — Lister toutes les sources de version (audit en a trouvé 4) :
  - `pyproject.toml:7` → `0.9.5`
  - `src/tenxyte/__init__.py:50` → `"0.0.8.3.9.7"`
  - `CHANGELOG.md` (header `## [Unreleased]`)
  - `next-steps.md` (mention "0.9.3.1.5.2")
- [ ] **1.2.2** — Décider d'une source de vérité unique : `pyproject.toml` (standard actuel) **+** lecture dynamique dans `__init__.py` (`from importlib.metadata import version; __version__ = version("tenxyte")`).
- [ ] **1.2.3** — Modifier `src/tenxyte/__init__.py` :
  - Remplacer `__version__ = "0.0.8.3.9.7"` par lecture dynamique.
  - Garder un fallback en dur `"0.0.0+unknown"` si le package n'est pas installé.
- [ ] **1.2.4** — Mettre à jour `CHANGELOG.md` :
  - Ajouter `## [0.9.6] - YYYY-MM-DD` au-dessus de `## [0.9.4]`.
  - Lister les correctifs Phase 1 (bcrypt, prints, placeholder).
- [ ] **1.2.5** — Purger `next-steps.md` des mentions de version (ce fichier est un plan, pas un changelog).
- [ ] **1.2.6** — Ajouter un test `tests/test_version_consistency.py` qui :
  - Lit `pyproject.toml` et `__init__.py`.
  - Vérifie qu'ils rapportent la même version.
  - Échoue en CI si divergence.

## 1.3 — `print()` qui leakent PII/secret en prod (audit §5)

- [ ] **1.3.1** — Faire un grep exhaustif `print(` dans `src/tenxyte/**/*.py` (déjà fait dans l'audit, lister exhaustivement).
- [ ] **1.3.2** — `src/tenxyte/adapters/django/email_service.py:119` → remplacer par `logger.warning("Failed to send email: %s", e)`.
- [ ] **1.3.3** — `src/tenxyte/adapters/django/email_service.py:147` → idem.
- [ ] **1.3.4** — `src/tenxyte/adapters/django/repositories.py:40` → **supprimer** le `print(user.id, user.email)` (PII, aucun intérêt).
- [ ] **1.3.5** — `src/tenxyte/adapters/django/repositories.py:515` → idem pour `print(org.id, org.name)`.
- [ ] **1.3.6** — `src/tenxyte/adapters/django/settings_provider.py:30` → **supprimer** `print(settings.jwt_secret_key)` ← SECRET JWT, critique.
- [ ] **1.3.7** — `src/tenxyte/adapters/django/settings_provider.py:84` → **supprimer** `print(settings.jwt_access_token_lifetime)`.
- [ ] **1.3.8** — `src/tenxyte/core/env_provider.py:36` → **supprimer** `print(settings.jwt_secret)`.
- [ ] **1.3.9** — `src/tenxyte/core/email_service.py:534-549` → conserver (mode Console d'email, comportement attendu par design).
- [ ] **1.3.10** — Ajouter un test `tests/integration/django/unit/test_no_print_in_prod.py` :
  - Liste blanche : `tenxyte/core/email_service.py` (mode Console).
  - Liste noire : tous les autres fichiers.
  - `grep -rn 'print(' src/tenxyte` doit retourner 0 hors whitelist.
  - Brancher en pre-commit hook (`pre-commit-config.yaml`).
- [ ] **1.3.11** — Configurer le logger dans `tenxyte/__init__.py` (handler par défaut `NullHandler` pour éviter le `No handlers could be found` warning en prod).
- [ ] **1.3.12** — Documenter dans `docs/en/security.md` la politique de logging : "aucun PII ni secret ne doit transiter par les logs".

## 1.4 — `PlaceholderApplicationRepository` (audit §4)

- [ ] **1.4.1** — Créer `src/tenxyte/adapters/django/repositories.py::DjangoApplicationRepository` (la classe existe peut-être déjà partiellement, vérifier).
- [ ] **1.4.2** — Faire hériter `DjangoApplicationRepository` de l'interface `ApplicationRepository` définie dans `src/tenxyte/ports/repositories.py`.
- [ ] **1.4.3** — Implémenter `get_by_access_key(access_key: str) -> Optional[Application]` proprement (déjà fait dans le placeholder, juste déplacer).
- [ ] **1.4.4** — Implémenter `get_by_id(app_id: str)`, `create(...)`, `update(...)`, `delete(...)`, `list_active()`.
- [ ] **1.4.5** — Modifier `src/tenxyte/adapters/django/middleware.py:217-241` :
  - Supprimer les `TODO: Phase 2`.
  - Supprimer la classe `PlaceholderApplicationRepository` inline.
  - Injecter `DjangoApplicationRepository()` dans `ApplicationAuthCoreMiddleware`.
- [ ] **1.4.6** — Ajouter un test `tests/integration/django/unit/test_application_repository.py` :
  - `get_by_access_key` retourne l'app si `is_active=True`.
  - Retourne `None` si `is_active=False` ou si l'app n'existe pas.
  - Round-trip `create/update/delete`.
- [ ] **1.4.7** — Vérifier que la suite de tests existante (`test_security.py`, `test_auth_views.py`) passe toujours après le refactor.

---

# 🟠 Phase 2 — Production-readiness (avant le tag "0.10.0 production-ready")

> **Durée estimée** : 4 à 6 semaines.
> **Gating** : 0 TODO "Phase 2" restant dans le code.
> **Release** : `0.10.0` (mineure, communication marketing revue).

## 2.1 — Implémenter les TODOs "Phase 2" du core middleware (audit §4)

- [ ] **2.1.1** — `src/tenxyte/core/middleware.py:397` → `ApplicationAuthCoreMiddleware.__call__` : implémenter la **vraie validation JWT** (pas juste passer au suivant).
  - Décoder le header `Authorization: Bearer <token>`.
  - Vérifier la signature avec la `Settings.jwt_verifying_key`.
  - Vérifier `jti` non blacklisté via `TokenBlacklistService`.
  - Attacher `request.user_id` et `request.app_id`.
- [ ] **2.1.2** — `src/tenxyte/core/middleware.py:412-416` → `CORSMiddlewareCore.__call__` :
  - Implémenter la gestion preflight `OPTIONS`.
  - Ajouter les headers CORS (`Access-Control-Allow-Origin/Methods/Headers/Credentials`).
  - Configurable via `Settings.cors_allowed_origins` (et `cors_allow_credentials`, etc.).
- [ ] **2.1.3** — `src/tenxyte/core/middleware.py:424` → `OrganizationContextMiddleware.__call__` :
  - Lire le header `X-Org-Slug`.
  - Charger l'org via `OrganizationRepository.get_by_slug()`.
  - Vérifier que l'utilisateur courant est membre (`OrganizationMembership`).
  - Attacher `request.organization` et `request.org_role`.
- [ ] **2.1.4** — Refactorer `src/tenxyte/middleware.py` (l'ancien, non-core) pour qu'il délègue 100% à `core/middleware.py` au lieu de dupliquer la logique.
- [ ] **2.1.5** — Tests pour chaque middleware refactoré (3 fichiers de tests à créer dans `tests/core/`).
- [ ] **2.1.6** — Vérifier la compatibilité ascendante : un projet qui utilisait l'ancien `tenxyte.middleware.ApplicationAuthMiddleware` doit continuer à fonctionner.

## 2.2 — Cache-poisoning : durcir X-Access-Secret (audit §7)

- [ ] **2.2.1** — Réduire la fenêtre de cache de 60s à **5-10s** (configurable `TENXYTE_APP_AUTH_CACHE_TTL`).
- [ ] **2.2.2** — Ajouter un rate-limit sur la **construction** de la clé de cache (avant le SHA-256) :
  - `cache.incr(f"app_auth_attempt_{app_id}_{ip}", 1)` avec TTL 60s.
  - Si `> 10` (configurable), retourner 429 avant même d'appeler `verify_secret`.
- [ ] **2.2.3** — Implémenter une révocation immédiate :
  - Quand une `Application.is_active` passe à `False`, invalider toutes les entrées `app_auth_ok_{app.id}_*` du cache.
  - Utiliser un tag/versioning : `cache.set(f"app_auth_version_{app.id}", uuid, None)` et inclure dans la clé.
- [ ] **2.2.4** — Ajouter un test `tests/integration/django/security/test_app_auth_cache.py` :
  - Vérifier le TTL configurable.
  - Vérifier que la révocation prend effet immédiatement.
  - Vérifier le rate-limit par IP.

## 2.3 — FastAPI adapter : passer de PoC à prod-ready (audit §6)

- [ ] **2.3.1** — Lister exhaustivement ce qui marche vs ce qui manque côté FastAPI :
  - ✅ Routers (login, register, refresh) — vu dans `adapters/fastapi/routers.py`
  - ❓ Middleware CORS/JWT équivalent à Django
  - ❓ Tests d'intégration end-to-end (TestClient + JWT roundtrip)
  - ❓ Support `X-Access-Key/Secret` côté FastAPI
  - ❓ Migrations (FastAPI n'a pas de `migrate` — quelle stratégie ?)
  - ❓ WebAuthn/OAuth
- [ ] **2.3.2** — Réécrire `tests/integration/fastapi/test_e2e_auth_flow.py` (TestClient + register → login → me → logout).
- [ ] **2.3.3** — Ajouter `src/tenxyte/adapters/fastapi/middleware.py` (CORS + Application auth).
- [ ] **2.3.4** — Documenter clairement dans `docs/en/fastapi_quickstart.md` ce qui marche **et** ce qui ne marche pas encore.
- [ ] **2.3.5** — Décider : soit investir pour atteindre parité Django, soit dégrader le marketing ("Django full · FastAPI alpha").
- [ ] **2.3.6** — Si décision = parité Django, découper en sous-tâches 2.3.6.x par feature (WebAuthn, OAuth, AIRS, etc.).

## 2.4 — Multi-DB : MongoDB réellement supporté et testé (audit §9)

- [ ] **2.4.1** — Ajouter MongoDB à la matrix CI `ci.yml` :
  - Service MongoDB dans `services:` du job `multidb-tests`.
  - Version 6.0 ou 7.0.
- [ ] **2.4.2** — Étendre `tests/integration/django/multidb/test_db_*.py` :
  - Couvrir **toutes** les migrations (`./manage.py migrate` sans erreur).
  - Couvrir register/login/me/logout sur MongoDB.
  - Couvrir les modèles abstraits (`AbstractUser`, `AbstractRole`, `AbstractApplication`).
- [ ] **2.4.3** — Vérifier chaque migration dans `src/tenxyte/migrations/` :
  - Pas de `models.AutoField` (MongoDB ne supporte pas).
  - Pas de `unique_together` (préférer `UniqueConstraint`).
  - Pas de `db_index=True` sur des champs non supportés.
- [ ] **2.4.4** — Documenter dans `docs/en/quickstart.md#mongodb` la procédure complète (déjà partiellement fait, vérifier qu'elle est juste).
- [ ] **2.4.5** — Décider : MongoDB est-il un **objectif v1.0** ou un **v2.0** ? Si v2.0, déclasser le marketing.

## 2.5 — Audit WebAuthn + OAuth ciblé (audit §8)

- [ ] **2.5.1** — Engager (ou faire) un audit ciblé de `src/tenxyte/core/webauthn_service.py` (16k bytes).
  - Vérifier la génération/stockage du challenge (TTL, single-use).
  - Vérifier la vérification de signature (`webauthn` library).
  - Vérifier la validation du `counter` (anti-clone authenticator).
  - Vérifier le handling des resident keys.
  - Vérifier le `rp_id` (pas de confusion, pas d'injection).
- [ ] **2.5.2** — Engager (ou faire) un audit ciblé de `src/tenxyte/services/social_auth_service.py` (21k bytes).
  - Vérifier la génération/vérification du `state` parameter.
  - Vérifier l'implémentation PKCE (`code_verifier` → `code_challenge` SHA-256).
  - Vérifier la whitelist `redirect_uri` (exact match, pas de prefix).
  - Vérifier la validation `id_token` (signature, `iss`, `aud`, `nonce`).
  - Vérifier le stockage du `access_token` utilisateur (chiffré en DB ?).
  - Vérifier le rate-limit par provider.
- [ ] **2.5.3** — Documenter les findings dans `docs/en/security.md` section "Known limitations" si des risques résiduels persistent.

## 2.6 — Tests : fixer la couverture et la matrix (audit §6)

- [ ] **2.6.1** — Activer `--cov` sur **toutes** les versions Python de la matrix (pas seulement 3.12).
- [ ] **2.6.2** — Activer `fail-fast: true` sur les jobs critiques (security, core), garder `false` sur la matrix de compat.
- [ ] **2.6.3** — Ajouter un job dédié `security-tests` qui ne fait que tourner `tests/integration/django/security/`.
- [ ] **2.6.4** — Mettre à jour le README : "1553 tests" → "2 390 tests" (le vrai chiffre).
- [ ] **2.6.5** — Documenter la stratégie de test dans `docs/en/testing.md` (déjà partiellement fait, vérifier).

---

# 🟡 Phase 3 — Dette technique et qualité (avant la v1.0)

> **Durée estimée** : 2 à 3 mois.
> **Gating** : 0 `print()` en prod, 0 `TODO` en prod, bus factor ≥ 2.
> **Release** : `1.0.0` (premier "vrai" release stable).

## 3.1 — Architecture hexagonale : finir le découplage (audit §10)

- [ ] **3.1.1** — Auditer `src/tenxyte/tenant_context.py` : remplacer tous les `from django.conf import settings` par injection via `SettingsProvider`.
- [ ] **3.1.2** — Idem pour `src/tenxyte/middleware.py` (l'ancien, pas le core).
- [ ] **3.1.3** — Idem pour `src/tenxyte/decorators.py` (vérifier qu'il ne tape pas directement dans Django settings).
- [ ] **3.1.4** — Créer un test `tests/core/test_no_django_leak.py` :
  - Importe tous les modules de `tenxyte.core`.
  - Vérifie qu'aucun n'a `from django` dans son `__dict__` ou ses imports runtime.
  - Lance l'import dans un `subprocess` avec Django désinstallé pour confirmer.
- [ ] **3.1.5** — Documenter l'architecture dans `docs/en/architecture.md` (probablement déjà fait, relire et compléter).

## 3.2 — Bus factor : on-boarder un 2ème mainteneur (audit §14)

- [ ] **3.2.1** — Identifier 2-3 contributeurs potentiels (réseau, communautés Python auth, open-source).
- [ ] **3.2.2** — Documenter les "ownership zones" du code :
  - `core/` → un owner
  - `adapters/django/` → un autre
  - `adapters/fastapi/` → un autre
  - `views/` → le propriétaire principal
  - `services/` → un autre
- [ ] **3.2.3** — Écrire un `CONTRIBUTING.md` à jour (vérifier l'existant).
- [ ] **3.2.4** — Labeliser les issues GitHub par "good first issue" pour attirer les contributeurs.
- [ ] **3.2.5** — Setup un CODEOWNERS (`.github/CODEOWNERS`).

## 3.3 — `LOG_REDACTION` et hardening logging (audit §12)

- [ ] **3.3.1** — Implémenter un filtre de logging `RedactionFilter` dans `tenxyte.core.logging` :
  - Blacklist de patterns regex (email, JWT-like, `Bearer xxx`, `password=...`, etc.).
  - Activable via `TENXYTE_LOG_REDACTION_ENABLED = True` (default).
- [ ] **3.3.2** — L'appliquer au logger `tenxyte` par défaut.
- [ ] **3.3.3** — Documenter dans `docs/en/security.md` section "Log redaction".
- [ ] **3.3.4** — Ajouter un test qui vérifie qu'un `logger.info("password=secret")` produit `password=***` en sortie.

## 3.4 — Quick wins de qualité

- [ ] **3.4.1** — Supprimer les 4 `TODO`/FIXME restants identifiés dans l'audit :
  - `core/middleware.py:397, 412, 416, 424` (couvert par Phase 2.1)
  - `services/organization_service.py:544` (`TODO: Send invitation email`) → implémenter ou transformer en `NotImplementedError` documenté.
  - `services/account_deletion_service.py:384` (`TODO: Envoyer email de rejet`) → idem.
- [ ] **3.4.2** — Supprimer les `tests/*.py` qui contiennent `# TODO: Implémenter avec service email` (4 occurrences dans `test_auth_service_email_alerts.py`).
- [ ] **3.4.3** — `tests/core/test_timing_attack_mitigation.py` a 3 `# TODO: Implémenter au niveau du service core` → les implémenter ou supprimer les tests.
- [ ] **3.4.4** — Ajouter `mypy` à la CI (déjà dans `pyproject.toml` mais pas dans `.github/workflows/ci.yml` visiblement).
- [ ] **3.4.5** — Ajouter `ruff check` à la CI (idem).
- [ ] **3.4.6** — Supprimer `docs/en`/`docs/fr` miroirs inutiles (synchroniser ou dédupliquer — 1 seul des deux doit être source).

## 3.5 — Performance / Scalabilité

- [ ] **3.5.1** — Benchmarker le login JWT sur un projet exemple (`examples/`) avec `locust` ou `k6` (un script `scripts/k6_load_test.js` existe déjà, l'utiliser).
- [ ] **3.5.2** — Documenter les chiffres dans `docs/en/performance.md` (p50, p95, p99 sur register/login/me).
- [ ] **3.5.3** — Profiler les vues les plus lentes (auth_views, organization_views) avec `cProfile`.
- [ ] **3.5.4** — Identifier les N+1 queries (Django Debug Toolbar) et les fixer via `select_related`/`prefetch_related`.

## 3.6 — Marketing / Communication

- [ ] **3.6.1** — Revoir le README :
  - "production-ready" → nuancer.
  - "self-hosted Auth0" → "self-hosted Auth0 **alternative en beta**".
  - Chiffre de tests à jour.
  - Statut FastAPI honnête.
- [ ] **3.6.2** — Ajouter un badge "Build status" CI.
- [ ] **3.6.3** — Ajouter un `SECURITY.md` (politique de disclosure).
- [ ] **3.6.4** — Ajouter un `CODE_OF_CONDUCT.md`.

---

# 🟢 Phase 4 — Nice to have (post-1.0)

> **Durée estimée** : au long cours, opportuniste.
> **Pas de gating** — ces items améliorent l'expérience mais ne bloquent rien.

## 4.1 — UX / DX

- [ ] **4.1.1** — Une CLI `tenxyte` (Typer) : `tenxyte init`, `tenxyte doctor`, `tenxyte rotate-secret`.
- [ ] **4.1.2** — Un dashboard admin web minimal (Django Admin amélioré) pour visualiser users/orgs/audit logs.
- [ ] **4.1.3** — Templates emails `src/tenxyte/templates/emails/` plus jolis (probablement déjà bien, vérifier).
- [ ] **4.1.4** — Une UI React/Vue pour le flow login/register (exposer en static ou npm package).

## 4.2 — Intégrations

- [ ] **4.2.1** — Support SAML 2.0 (entreprise).
- [ ] **4.2.2** — Support LDAP (legacy on-prem).
- [ ] **4.2.3** — Webhooks (events: `user.created`, `password.changed`, `agent_token.suspended`).
- [ ] **4.2.4** — Export/import d'audit logs (CSV, JSON).
- [ ] **4.2.5** — Provider d'OIDC pour que `tenxyte` devienne IdP (vs rester SP).

## 4.3 — AIRS (AI Responsibility & Security) — compléter

- [ ] **4.3.1** — Vérifier que `src/tenxyte/models/agent.py` couvre bien :
  - `AgentToken` (revocation, scope, budget).
  - `AgentPendingAction` (HITL workflow).
  - `CircuitBreaker` (RPM, total, budget).
  - `DeadMansSwitch` (heartbeat).
  - `PromptTrace` (forensic).
- [ ] **4.3.2** — Tests d'intégration AIRS : créer un agent, lui donner un budget, le voir se faire suspendre après dépassement.
- [ ] **4.3.3** — Documentation AIRS : exemple end-to-end d'un agent qui appelle l'API, fait une action sensible, déclenche un HITL, est approuvé, continue.

## 4.4 — Documentation

- [ ] **4.4.1** — Migrer `docs/en` et `docs/fr` vers une source unique + i18n.
- [ ] **4.4.2** — Ajouter un `docs/en/tutorials/` (au moins 3 tutoriels pas-à-pas).
- [ ] **4.4.3** — Vidéo démo (5 min) sur YouTube.
- [ ] **4.4.4** — Une page `tenxyte.dev` (ou `tenxyte.io`).

## 4.5 — Observabilité

- [ ] **4.5.1** — OpenTelemetry tracing (auto-instrumentation Django + custom spans sur auth flow).
- [ ] **4.5.2** — Prometheus metrics (`tenxyte_login_total`, `tenxyte_login_failures_total`, `tenxyte_jwt_decode_duration_seconds`).
- [ ] **4.5.3** — Sentry integration (déjà partiellement via les settings ? vérifier).

---

# 📊 Tableau récapitulatif

| Phase | Items | Sévérité max | Release cible | Effort |
|---|---|---|---|---|
| **Phase 1** | 4 sections / ~35 tâches | 🔴 Critique | `0.9.6` | 1-2 semaines |
| **Phase 2** | 6 sections / ~40 tâches | 🟠 Haute | `0.10.0` | 4-6 semaines |
| **Phase 3** | 6 sections / ~35 tâches | 🟡 Moyenne | `1.0.0` | 2-3 mois |
| **Phase 4** | 5 sections / ~25 tâches | 🟢 Basse | post-1.0 | opportuniste |

# 🎯 Definition of Done — par release

**`0.9.6` (Phase 1 complétée)**
- [ ] Tous les items 1.1 à 1.4 sont cochés
- [ ] `grep -rn 'print(' src/tenxyte` retourne 0 hors email Console
- [ ] `pip show tenxyte` et `pyproject.toml` rapportent la même version
- [ ] Aucun test ne référence le pré-hash SHA-256
- [ ] Les mots de passe > 72 chars sont hashés correctement (test de régression)

**`0.10.0` (Phase 2 complétée)**
- [ ] 0 `TODO`/`FIXME` dans `src/tenxyte/core/middleware.py`
- [ ] 0 `PlaceholderApplicationRepository` dans le code
- [ ] MongoDB fait partie de la matrix CI et tous les tests passent
- [ ] Audit WebAuthn + OAuth documenté (findings + mitigations)
- [ ] README honnête sur FastAPI ("alpha" / "experimental")

**`1.0.0` (Phase 3 complétée)**
- [ ] Bus factor ≥ 2 (au moins 2 contributeurs actifs sur les 3 derniers mois)
- [ ] 0 `print()` en prod, 0 `TODO`/`FIXME` en prod
- [ ] `mypy` + `ruff` verts en CI
- [ ] `SECURITY.md` + `CODE_OF_CONDUCT.md` publiés
- [ ] Benchmarking public

# 📝 Notes

- **Ce plan est vivant** : ne pas hésiter à déplacer un item entre phases si l'effort se révèle différent.
- **Bus factor** : si on perd l'unique mainteneur, **tout ce plan est gelé** — c'est le risque #1.
- **Phase 1 avant tout** : un client qui regarde `tenxyte` aujourd'hui verra le bcrypt pré-hashé et les prints PII. C'est disqualifiant en 30 secondes de revue.
- **Phase 4 est du post-1.0** : ne pas s'y attaquer avant que la v1.0 ne sorte, sinon dispersion.

---

*Plan généré le 2026-06-12 à partir de `plan/audit-mnmx.md` du 2026-06-11.*
