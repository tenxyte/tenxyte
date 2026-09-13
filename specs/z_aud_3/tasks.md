# Implementation Plan: Phase 3 « Multi-framework réel » (z_aud_3)

## Overview

L'implémentation suit la chaîne de dépendances : **fondations async** (ports + services Core,
prérequis de tout handler FastAPI non bloquant), puis **socle FastAPI** (factory, stack de
référence, middleware — prérequis de tout endpoint), puis **outillage de preuve** (matrice,
Contract_Suite, purity check — installés AVANT la première vague de parité pour gater dès le
début), puis les **vagues de parité A→B→C→F→D→E→G** (D8), chacune close par un checkpoint, puis
les **fixtures de contrat JS** et le chantier **UI headless/stylé** (monorepo JS, tracé ici),
enfin la **documentation** et la non-régression finale.

Aucune tâche ne modifie l'adapter Django ni les signatures sync du Core. Les vérifications non
automatisables portent le marqueur `[MT-x]` renvoyant à `manual_tests.md`.

## Tasks

- [x] 1. Fondations async du Core
  - [x] 1.1 Créer les Async_Ports et le Sync_Bridge
    - Nouveau module `src/tenxyte/ports/async_repositories.py` : `AsyncUserRepository` (miroir
      exact de `UserRepository`), `SyncToAsyncUserRepository` (pont `to_thread`), résolveur
      `as_async()`. Ports async des storages de requête : TOTP (`AsyncTOTPStorage`) et magic
      link — déjà existants, colocalisés avec leur service, non dupliqués ici ; WebAuthn
      (`AsyncWebAuthnCredentialRepository`/`AsyncWebAuthnChallengeRepository`, nouveaux, ajoutés
      dans `core/webauthn_service.py` par cohérence avec cette convention existante) ; cache
      (`core/cache_service.py`'s `CacheService` ABC a déjà ses méthodes async intégrées). Modules
      sync existants intouchés.
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Write property test for sync/async semantic equivalence
    - **Property 4: Équivalence sémantique sync/async des ports** (séquences d'opérations
      générées sur repo in-memory vs son pont) — `tests/core/test_async_user_repository.py`
    - **Validates: Requirements 1.1, 1.3**

  - [x] 1.3 Write property test for normalized async resolution
    - **Property 6: Résolution async normalisée** (natif détecté par espionnage, pont en repli)
      — `tests/core/test_async_user_repository.py`
    - **Validates: Requirements 1.4, 2.1, 2.2**

  - [x] 1.4 Ajouter les variantes async des services Core
    - **Déjà fait avant cette phase** (constat vérifié par introspection AST, pas seulement
      lecture) : `magic_link_service` (2/2 méthodes publiques ont leur variante `*_async` via
      `hasattr`/`to_thread`), `session_service` (4/4), `totp_service` (6/6 méthodes accédant au
      storage ; les 6 restantes sont des fonctions pures CPU-bound — génération/vérification
      cryptographique sans accès storage — qui doivent rester sync par la Requirement 2.2
      elle-même). L'état des lieux de `design.md` ("0 % async") ne correspondait plus au code
      actuel. `jwt_service` inchangé (gabarit).
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 1.5 Write sync-API snapshot test
    - **Property 5: L'API sync du Core est intouchée** (snapshot des signatures publiques) —
      `tests/core/test_async_ports_sync_api_unchanged.py`
    - **Validates: Requirements 1.2, 2.4, 8.2**

- [ ] 2. Socle FastAPI de production
  - [x] 2.1 Implémenter settings, App_Factory et lifespan
    - `settings.py` — **pas de pydantic-settings** : `core/env_provider.py`'s `EnvSettingsProvider`
      résout déjà `TENXYTE_*` framework-agnostiquement (constat vérifié, testé) ; ce module est un
      simple `get_default_settings()` dessus. `app.py` (`create_tenxyte_app` / `create_tenxyte_router`,
      lifespan engine async + `/health`) — testé pour de vrai (boot sur aiosqlite éphémère, aucun
      `NotImplementedError`).
    - _Requirements: 3.1, 3.5_

  - [ ] 2.2 Implémenter le Reference_Stack
    - **Partiel.** Fait : `models_sa.py` (SQLAlchemy 2.0 async — `UserDB` + `RefreshTokenDB`,
      construit incrémentalement au fil des vagues plutôt que le schéma complet en une fois),
      `repositories_async.py` (`SQLAlchemyAsyncUserRepository`, testé end-to-end sur aiosqlite
      réel — create/get/update_last_login/set_mfa_secret/verify_email/list_all/count/delete),
      `deps.py` (DI par défaut surchargeable, plus de `NotImplementedError` pour ce qui existe).
      **Restant :** `migrations/` Alembic (le lifespan crée le schéma via
      `Base.metadata.create_all` pour le dev/tests — pas un substitut aux migrations pour la prod) ;
      tables des vagues B–G (roles, permissions, organizations, agent_tokens, ...) à ajouter au fil
      de l'eau, pas en avance de phase.
    - _Requirements: 3.2, 3.3_

  - [x] 2.3 Implémenter middleware, erreurs et throttling
    - Fait : `errors.py` — `register_exception_handlers(app)`, format canonique
      `{error, code, details}` universel, y compris pour les erreurs natives FastAPI/Starlette
      (422 validation → 400 `VALIDATION_ERROR`, 404/405 natifs, 500 masqué `INTERNAL_ERROR` sans
      fuite d'exception), `TenxyteAPIError` pour lever une erreur canonique directement depuis un
      handler/dépendance. `application_auth.py` — `ApplicationAuthMiddleware` (parité exacte :
      `APP_AUTH_REQUIRED`/`APP_AUTH_INVALID`/`APP_AUTH_ORIGIN_REQUIRED`/`APP_AUTH_ORIGIN_DENIED`,
      modes clé+secret et clé seule/Origin, toggle `TENXYTE_APPLICATION_AUTH_ENABLED`, mêmes
      `exempt_paths`/`exact_exempt_paths` que Django — réutilise les properties déjà
      framework-agnostiques de `core/settings.py`), `ApplicationDB` (bcrypt+base64, même schéma de
      hash que `AbstractApplication`), câblé dans l'App_Factory ; endpoint `/health` déplacé sous
      `{api_prefix}/health/` pour matcher l'exemption par défaut. 10 tests, tous verts contre une
      vraie app + vraie DB éphémère. Fait aussi : `security.py` — dépendance FastAPI
      `require_jwt(allowed_scopes=None)` (idiome DI, pas décorateur), parité avec
      `tenxyte.decorators.require_jwt` : extraction Bearer, mêmes 6 codes d'erreur
      (`AUTH_REQUIRED`, `TOKEN_INVALID`, `TOKEN_APP_MISMATCH`, `USER_NOT_FOUND`, `USER_INACTIVE`,
      `INSUFFICIENT_SCOPE`), même sémantique de scope restreint (token pleine portée accepté
      partout, token à `scope` n'est accepté que sur les endpoints qui le listent explicitement),
      check de mismatch app_id via `request.state.application`. Exclu délibérément (hors scope
      actuel) : l'échappatoire `JWT_AUTH_ENABLED` du décorateur Django (documentée
      "DANGEROUS - testing only" côté Django elle-même, pas un requirement FastAPI, et n'existe
      pas sur `core/settings.py`) et l'enforcement du lockout de compte (dépend du service Core
      `AccountLockout`, pas encore porté). 6 tests dans `test_security.py`, tous verts contre une
      vraie app + vraie DB éphémère + vrais tokens signés. AgentBearer confirmé hors scope de
      cette tâche : c'est un mécanisme propre au groupe AIRS, porté avec le routeur `airs.py` à la
      tâche 9.1 (vague F), pas une pièce générique du socle. Fait enfin : `throttling.py` —
      `rate_limit(*scopes)`, dépendance FastAPI empilable (comme les `throttle_classes` DRF),
      même table scope→rate que les 13 sous-classes `IPBasedThrottle` de `tenxyte.throttles`
      (login, login_hourly, register, register_daily, password_reset, password_reset_daily,
      otp_request, otp_verify, login_otp_request, login_otp_request_daily, refresh,
      magic_link_request, magic_link_verify). Le comptage réutilise tel quel
      `CacheService.check_rate_limit_async` (déjà l'algorithme fixed-window "lire, rejeter si au
      plafond, sinon incrémenter + expirer au premier coup" de `SimpleRateThrottle` de DRF) —
      rien à réimplémenter côté algorithme. `app.state.tenxyte_cache_service` ajouté à
      l'App_Factory. Testé à temps simulé pour de vrai (monkeypatch de `time.time` dans
      `core/cache_service.py`, seul point où ce module lit l'horloge) plutôt qu'avec de vrais
      `sleep()` : fenêtre qui expire, IPs indépendantes, scopes empilés qui bloquent sur le plus
      restrictif. 7 tests dans `test_throttling.py`, tous verts. Exclu délibérément :
      `ProgressiveLoginThrottle` (backoff exponentiel, une bookkeeping au-dessus d'un throttle de
      base, pas une famille de scope distincte) et `SimpleThrottleRule` (throttling de path
      arbitraire piloté par settings — mécanisme générique séparé) ; résolution d'IP minimale
      (`request.client.host`, sans la chaîne de confiance `X-Forwarded-For`/`TRUSTED_PROXIES`
      des throttles Django — durcissement sécurité hors scope de cette tâche, pas d'équivalent
      sur `core/settings.py`).
    - _Requirements: 3.4, 3.6_

  - [ ] 2.4 Write property tests for the production base
    - **Property 9 (faite) :** `tests/integration/fastapi/unit/test_errors.py` — corpus Hypothesis
      de requêtes invalides + JSON malformé + 404/405/500 natifs + erreur applicative custom,
      tous canoniques.
    - **Property 10 (moitié socle, faite) :** `tests/integration/fastapi/unit/test_app_factory.py`
      prouve pour de vrai le boot sans surcharge (aucun `NotImplementedError`) et un round-trip
      complet `AsyncUserRepository` sur aiosqlite réel. **Moitié `register→login→me` HTTP :**
      attend le router Auth de la vague A (tâche 5.1).
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.6**

  - [x] 2.5 Compléter l'extra `[fastapi]`
    - `pyproject.toml` : + `aiosqlite>=0.20`, `alembic>=1.13` (asyncpg documenté en commentaire,
      pas une dépendance dure — la stack dev/CI tourne sur aiosqlite). **Pas de
      pydantic-settings** — même décision qu'en 2.1 : `EnvSettingsProvider` couvre déjà la
      résolution de settings depuis l'environnement, ajouter une deuxième machinerie de config
      aurait été redondant. `core` et `[django]` inchangés.
    - _Requirements: 8.4_

- [ ] 3. Outillage de preuve (avant toute vague de parité)
  - [x] 3.1 Implémenter la Parity_Matrix
    - `scripts/parity_matrix.py` : introspection réelle des deux côtés — Django via
      `tenxyte.urls.urlpatterns` (résolution des méthodes HTTP par introspection de la classe de
      vue DRF / fonction `@api_view`, pas une liste recopiée à la main), FastAPI via
      `create_tenxyte_router().routes` — normalisées à la même forme `(MÉTHODE, /chemin/)`
      (convertisseurs Django `<type:nom>` → `{nom}`). `group_of(path)` classe chaque route dans
      son Parity_Group (A–G) par préfixe, table dérivée des listes d'endpoints propres à chaque
      tâche de vague (5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1) — couverture totale vérifiée par
      test (aucune route réelle sans groupe). `parity_exclusions.toml` créé (vide pour l'instant
      — aucune route de `tenxyte.urls` n'est Django-only aujourd'hui), raison vide rejetée au
      chargement. Sortie `docs/{en,fr}/parity_table.md` régénérée (114 endpoints, tous 🔜 vague
      planifiée — aucune vague livrée). CLI : `--groups` absent → rapport seul, jamais
      d'échec (bootstrap de l'outil avant toute vague) ; `--groups=X,Y` ou `--groups=all` → échec
      si un gap non excusé existe dans un groupe nommé. 31 tests dans `test_parity_matrix.py`.
    - **Property 1 (socle)**
    - _Requirements: 5.1, 4.5_

  - [ ] 3.2 Créer la Contract_Suite paramétrée
    - `tests/contract/` : fixture `api` paramétrée {django, fastapi} ; refactor des snapshots de
      forme existants en assertions partagées (tests Django actuels inchangés dans leurs
      attentes) ; câblage CI double exécution
    - **Property 2 (socle)**
    - _Requirements: 5.2_

  - [x] 3.3 Implémenter l'Async_Purity_Check
    - `scripts/check_async_purity.py` : AST walk de chaque `AsyncFunctionDef` sous
      `adapters/fastapi/`, interdit — appel non-awaité à une méthode de port sync
      *distinctive* (`get_by_id`, `get_by_email`, `update_last_login`, `set_mfa_secret`,
      `verify_email` de `UserRepository` ; `add_to_blacklist`, `is_blacklisted`,
      `remove_from_blacklist`, `check_rate_limit`, `reset_rate_limit` de `CacheService`) ;
      `requests.<verbe>(...)` ; `time.sleep(...)` ; `open(...)` hors `asyncio.to_thread`/
      `anyio.to_thread.run_sync`. **Écart documenté délibéré :** les verbes génériques
      (`get`/`set`/`create`/`update`/`delete`/`count`/`exists`/`list_all`/`increment`/`expire`/
      `ttl`) sont explicitement exclus de la liste — ils entrent en collision avec des API
      omniprésentes déjà utilisées légitimement dans l'adaptateur (`dict.get`, `Headers.get`,
      `AsyncSession.get`/`.delete`), ce qui aurait rendu `# async-purity: ignore` du bruit plutôt
      qu'un signal de revue réel ; la liste retenue reste assez distinctive pour qu'un appel non
      awaité soit sans ambiguïté un bug (appel sync direct ou `await` oublié). Un appel déjà
      `await`-é n'est jamais signalé, quelle que soit la méthode. Une `def` sync imbriquée dans
      une `async def` est hors périmètre (elle s'exécute de façon synchrone quand appelée, pas
      sur la boucle événementielle). Job CI `async-purity` ajouté à `.github/workflows/ci.yml`
      (aucune installation du package nécessaire — le checker ne fait que parser du texte
      source). **Violation réelle trouvée et documentée** (pas corrigée en douce) : deux appels
      non-awaités dans `routers.py` — le routeur PoC déjà marqué pour suppression à la tâche
      5.1 — annotés `# async-purity: ignore[PoC router, removed at z_aud_3 task 5.1]` plutôt que
      modifiés, puisque ce fichier entier disparaît à la vague A. 11 tests dans
      `test_check_async_purity.py`, dont un qui tourne le checker contre le vrai répertoire
      `adapters/fastapi/` (garde de non-régression : tout nouveau motif bloquant introduit le
      fait échouer).
    - **Property 7: Pureté async des handlers**
    - **Validates: Requirements 5.4**

  - [ ] 3.4 Câbler la Coverage_Gate FastAPI
    - Job CI `fastapi-tests` : matrice Python 3.10–3.13, `--cov=tenxyte.adapters.fastapi
      --cov-fail-under=90`
    - _Requirements: 5.3_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Fondations + socle + outillage verts ; suite Django intacte ; ask the user if questions arise.

- [ ] 5. Vague de parité A — Auth de base
  - [ ] 5.1 Porter le groupe A
    - `routers/auth.py` : register, login/email, login/phone, refresh, logout, logout/all,
      me (GET/PATCH), me/roles — contrat Django strict (anti-énumération register, lockout,
      bootstrap 2FA `2fa_setup_only`, `must_change_password`, cookie refresh opt-in) ;
      suppression du `routers.py` PoC (divergences documentées au CHANGELOG adapter)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 5.2 Write property test for anti-enumeration parity (groupe A)
    - **Property 3: Parité de l'anti-énumération** (register)
    - **Validates: Requirements 4.3**

  - [ ] 5.3 Contract_Suite + matrice sur A
    - Suite du groupe verte sur les deux adapters ; `parity_matrix --groups=A` verte
    - _Requirements: 5.1, 5.2_

- [ ] 6. Vague de parité B — Password
  - [ ] 6.1 Porter le groupe B
    - `routers/password.py` : reset request/confirm, change, set-initial, strength,
      requirements — incluant scope `password_change_only`, HIBP, historique
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 6.2 Contract_Suite + matrice sur A+B (anti-énumération reset incluse)
    - **Property 3 (reset)** · _Requirements: 4.3, 5.1, 5.2_

- [ ] 7. Vague de parité C — OTP, passwordless, 2FA
  - [ ] 7.1 Porter le groupe C
    - `routers/otp_2fa.py` : otp/request, otp/verify/email|phone, login/otp/request|verify,
      magic-link/request|verify, 2fa/status|setup|confirm|disable|backup-codes — feature-flags
      (`FEATURE_DISABLED`), anti-énumération login OTP, réauthentification OTP
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 7.2 Write property test for feature-flag and scope parity
    - **Property 8: Parité des feature-flags et des scopes** (combinatoire flags × endpoints,
      scopes `2fa_setup_only`/`password_change_only`)
    - **Validates: Requirements 4.4**

  - [ ] 7.3 Contract_Suite + matrice sur A+B+C
    - _Requirements: 5.1, 5.2_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Vagues A–C vertes sous toutes les gates ; ask the user if questions arise.

- [ ] 9. Vague de parité F — AIRS
  - [ ] 9.1 Porter le groupe F
    - `routers/airs.py` : ai/tokens (CRUD, revoke, suspend, heartbeat, report-usage,
      revoke-all), ai/pending-actions (list, confirm, deny), découverte `.well-known/airs`
      (conformance reflétant la config FastAPI) — AgentBearer, double RBAC, HITL 202,
      `X-Prompt-Trace-ID`
    - _Requirements: 4.1, 4.2, 4.4, 4.6_

  - [ ] 9.2 Exécuter la Conformance_Suite z_aud_2 contre FastAPI
    - **Property 11: Conformité AIRS indépendante de l'adapter** — job CI `airs-conformance`
      contre l'app FastAPI éphémère, tous niveaux
    - **Validates: Requirements 4.6, 5.5**

  - [ ] 9.3 Contract_Suite + matrice sur A+B+C+F
    - _Requirements: 5.1, 5.2_

- [ ] 10. Vague de parité D — RBAC, applications, admin
  - [ ] 10.1 Porter le groupe D
    - `routers/rbac.py` : permissions/*, roles/*, users/<id>/roles|permissions, applications/*,
      admin/users/* (dont PATCH `must_change_password`, ban/unban/lock/unlock), admin sécurité
      (audit-logs, login-attempts, blacklisted/refresh tokens), dashboard/*
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ] 10.2 Contract_Suite + matrice sur A–D (+F) ; exclusions justifiées le cas échéant
    - _Requirements: 4.5, 5.1, 5.2_

- [ ] 11. Vague de parité E — Organisations
  - [ ] 11.1 Porter le groupe E
    - `routers/orgs.py` : organizations/* (CRUD, tree, members, invitations), org-roles —
      contexte `X-Org-Slug`, héritage de rôles, gating `ORGANIZATIONS_ENABLED`
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ] 11.2 Contract_Suite + matrice sur A–F
    - _Requirements: 5.1, 5.2_

- [ ] 12. Vague de parité G — WebAuthn, Social, GDPR
  - [ ] 12.1 Porter le groupe G
    - `routers/webauthn_social.py` : webauthn/* (6), social/<provider>/ (+ callback, Apple
      z_aud_1 inclus), GDPR user (deletion request/confirm/cancel/status, export) et admin
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ] 12.2 Contract_Suite + matrice COMPLÈTE (tous groupes)
    - **Property 1 (finale)** — 100 % porté ou exclu-justifié
    - **Validates: Requirements 4.1, 4.5, 5.1**

- [ ] 13. Checkpoint - Ensure all tests pass
  - Parité complète sous toutes les gates ; ask the user if questions arise.

- [ ] 14. Fixtures de contrat pour le SDK JS
  - [ ] 14.1 Export OpenAPI des deux adapters + check de drift
    - `scripts/export_openapi.py` → `openapi/tenxyte-django.json` + `tenxyte-fastapi.json` ;
      job CI `openapi-drift` comparant les endpoints partagés
    - **Property 12: Les exports OpenAPI décrivent le même contrat**
    - **Validates: Requirements 6.6**

  - [ ] 14.2 Backend démo docker pour la CI JS
    - `examples/js-contract-backend/` : compose FastAPI + seed déterministe, consommé par les
      E2E du monorepo JS
    - _Requirements: 6.5, 6.6_

- [ ] 15. Composants UI (monorepo JS — tracé ici, implémenté là-bas)
  - [ ] 15.1 Livrer `@tenxyte/ui-headless` (7 composants) `[MT-5]`
    - SignIn, SignUp, OTPInput, TwoFactorSetup, PasskeyButton, ForcedPasswordChange,
      OrgSwitcher — hooks + compound components, machines à états du Wire_Contract, zéro CSS,
      ARIA complet, tests vitest + testing-library + axe ; E2E contre le backend démo
    - **Property 13 (volet headless)** · _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [ ] 15.2 Livrer `@tenxyte/ui` (couche stylée) `[MT-6]`
    - Thème par défaut sur tokens `--tenxyte-*`, clair/sombre, zéro logique de flux propre
    - **Property 13 (volet styled)** · _Requirements: 6.4, 6.5_

- [ ] 16. Documentation
  - [ ] 16.1 Réécrire les quickstarts FastAPI `[MT-1]`
    - `docs/en/fastapi_quickstart.md` + FR : install → factory → uvicorn → premier appel ;
      validé chronométré par MT-1
    - _Requirements: 7.1_

  - [ ] 16.2 Publier la table de parité et le guide async
    - `parity_table.md` (EN/FR, régénérée en CI) ; `async_guide.md` mis à jour (Async_Ports,
      résolution, gabarit jwt_service) ; doc UI dans `integration/javascript/`
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 17. Non-régression finale et validation manuelle
  - [ ] 17.1 Vérifier la non-régression Django totale
    - **Property 14: Non-régression Django totale** — suite existante verte sans modification,
      zéro migration Django ajoutée, zéro fichier Django_Adapter modifié
    - **Validates: Requirements 8.1, 8.5**

  - [ ] 17.2 Dérouler la campagne de tests manuels
    - Exécuter `manual_tests.md` MT-1 à MT-7 et compléter le registre
    - _Requirements: 7.1, 6.3, 6.4_

- [ ] 18. Checkpoint final - Ensure all tests pass
  - Toutes gates vertes (parité, contrat, couverture, pureté, conformité, drift), registre manuel
    complet ; ask the user before announcing multi-framework GA.

## Notes

- Les tâches marquées `[MT-x]` ont une contrepartie obligatoire dans `manual_tests.md`.
- Règle de fusion des vagues (design §Jalonnement) : une vague n'est mergée que si tests du
  groupe + Contract_Suite du groupe + matrice cumulée + purity + Coverage_Gate sont verts.
- Le job CI Django existant est volontairement inchangé : sa stabilité EST le test du
  Requirement 8.1.
- Les tâches 15.x s'exécutent dans le monorepo JS ; elles sont cochées ici sur preuve (lien PR +
  résultat MT-5/MT-6 au registre).
- Property tests : Hypothesis ≥ 100 exemples, docstring **Feature: z_aud_3, Property N: <texte>**.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "2.1"] },
    { "id": 2, "tasks": ["1.5", "2.2", "2.5"] },
    { "id": 3, "tasks": ["2.3", "3.1", "3.3"] },
    { "id": 4, "tasks": ["2.4", "3.2", "3.4"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3"] },
    { "id": 6, "tasks": ["6.1", "6.2"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 8, "tasks": ["9.1", "9.2", "9.3"] },
    { "id": 9, "tasks": ["10.1", "10.2"] },
    { "id": 10, "tasks": ["11.1", "11.2"] },
    { "id": 11, "tasks": ["12.1", "12.2"] },
    { "id": 12, "tasks": ["14.1", "14.2", "16.1"] },
    { "id": 13, "tasks": ["15.1", "16.2"] },
    { "id": 14, "tasks": ["15.2", "17.1", "17.2"] }
  ]
}
```
