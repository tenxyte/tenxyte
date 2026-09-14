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
    - **Ajouté à la tâche 5.1** (découvert manquant en construisant le routeur Auth) :
      `AuthenticationService.authenticate_async` — même JWT_Async_Pattern (méthode `*_async` du
      `PasswordUserLookup` utilisée si présente par `hasattr`, sinon pont `to_thread`), seule
      pièce du Core auth pas encore async avant cette découverte. 4 tests dans
      `tests/core/test_auth_service_async.py`, dont un test de propriété Hypothesis (sync/bridge
      s'accordent sur tous les scénarios : inconnu, mauvais mot de passe, bon mot de passe,
      inactif, banni, verrouillé) et un test espion prouvant qu'un lookup natif async n'appelle
      jamais ses méthodes sync.
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
    - **Property 10 (complète) :** `tests/integration/fastapi/unit/test_app_factory.py` prouve
      pour de vrai le boot sans surcharge (aucun `NotImplementedError`), un round-trip complet
      `AsyncUserRepository` sur aiosqlite réel, et — maintenant que le routeur Auth de la vague A
      existe (tâche 5.1) — le parcours HTTP complet `register → login → me` contre une vraie app
      + vraie DB éphémère.
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

  - [x] 3.2 Créer la Contract_Suite paramétrée
    - `tests/contract/conftest.py` : fixture `api` paramétrée `{django, fastapi}` — côté Django,
      invoque la classe de vue DRF directement via `APIRequestFactory` (même technique que
      `test_endpoint_response_shape_snapshots.py`), pontée par `asgiref.sync_to_async` (l'ORM
      Django refuse l'accès DB synchrone depuis une boucle événementielle sans ce pont) ; côté
      FastAPI, `create_tenxyte_app()` réel sur `httpx.AsyncClient(ASGITransport(...))`, zéro
      mock des deux côtés. `tests/contract/shapes.py` : constantes de forme (`REGISTER_*`,
      `LOGIN_EMAIL_*`, `LOGIN_PHONE_*`) extraites de
      `test_endpoint_response_shape_snapshots.py` — désormais la source unique importée par les
      deux suites (tests Django existants **inchangés dans leurs attentes**, juste réécrits pour
      importer au lieu de redéfinir). `tests/contract/test_group_a_shapes.py` : 3 tests
      (register — champs top-level + sous-objet `user`, login/email — champs + `token_type`),
      6 exécutions au total (× 2 adaptateurs), toutes vertes. Job CI `contract-parity` ajouté
      (suite + `parity_matrix --groups=A` — **intentionnellement rouge** tant que `login/phone`
      n'est pas porté, signal correct plutôt que masqué par un `|| true`). **Bug de contrat réel
      trouvé en cours de route** : le test initial utilisait un mot de passe sans majuscule ni
      chiffre — accepté par le `RegisterRequest` FastAPI (aucune validation de force du mot de
      passe), rejeté par le validateur Django (`validators.validate_password`, couplé à
      `conf.auth_settings` donc non réutilisable tel quel côté FastAPI). **Écart documenté,
      pas corrigé dans cette tâche** : la validation de force de mot de passe + le check HIBP ne
      sont pas encore portés côté FastAPI (le test de contrat utilise un mot de passe qui
      satisfait déjà les deux côtés, en attendant ce portage — probablement Groupe B, où
      `password/strength`/`password/requirements` vivent côté Django).
      **Deuxième bug réel trouvé, plus sérieux, corrigé** : les tests de contrat
      `@pytest.mark.django_db` (rollback par savepoint) faisaient fuiter en écriture réelle et
      permanente les utilisateurs créés côté Django vers la base de test partagée (SQLite
      `:memory:`), visibles par des tests sans rapport (`test_filters.py`,
      `test_management_commands.py`, `test_tenxyte_cleanup.py`) exécutés plus tard dans la même
      session — reproductible à 100 % dès que la Contract_Suite tournait avant eux. Cause : le
      pont `asgiref.sync_to_async` exécute l'ORM Django sur un thread ouvrier séparé (nécessaire
      — le garde-fou async de Django lève `SynchronousOnlyOperation` sinon), thread qui n'est pas
      celui sur lequel pytest-django a ouvert le savepoint de rollback du test ; les écritures
      passaient donc par une connexion différente, jamais annulée. Corrigé en passant les tests
      de contrat à `@pytest.mark.django_db(transaction=True)` (nettoyage par `flush`, valide
      quel que soit le thread/la connexion qui a écrit) — vérifié : plus aucune fuite,
      `test_filters.py`/`test_management_commands.py`/`test_tenxyte_cleanup.py` verts après la
      Contract_Suite.
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

  - [x] 3.4 Câbler la Coverage_Gate FastAPI
    - Job CI `fastapi-tests` ajouté à `.github/workflows/ci.yml` : matrice Python 3.10–3.13
      (`pip install -e ".[fastapi,dev]"`, `-p no:django` — pas de dépendance Django), suite
      complète sur chaque version ; gate de couverture `--cov=tenxyte.adapters.fastapi
      --cov-fail-under=90` sur Python 3.12 (même schéma que `core-tests`), artefact remonté au
      job `coverage` agrégateur. `httpx>=0.27` ajouté à l'extra `dev` (test-only — l'ASGITransport
      des tests, jamais importé par le code runtime de l'adaptateur). Vérifié localement :
      91.24 % sur `tenxyte.adapters.fastapi`, gate 90 % franchie.
    - _Requirements: 5.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Fondations (tâche 1) + socle (tâche 2) + outillage (tâche 3) verts ; suite Django intacte.
    Vérifié après coup (au moment où 2.4/3.2/3.4 ont fermé) plutôt qu'en s'arrêtant dessus, car
    aucune question ne s'est posée nécessitant l'utilisateur — suite complète : 2842 passed,
    5 skipped, 97.56% de couverture.

- [ ] 5. Vague de parité A — Auth de base
  - [x] 5.1 Porter le groupe A
    - **Contrat extrait par recherche exhaustive de `views/auth_views.py` +
      `views/user_views.py`** (serializers, codes d'erreur exacts, asymétrie
      `IsAuthenticated`-vs-`require_jwt` entre `MeView` et `MyRolesView`, `TokenPair` opaque —
      `session_id`/`device_id` toujours `null` en réalité, `refresh_token` toujours un UUID
      opaque jamais un JWT). `routers/auth.py` porté et testé pour de vrai (28 tests dans
      `test_auth_router.py`) : `register` (anti-énumération, `login=True`, validation),
      `login/email` (succès, anti-énumération mot de passe, lockout via `CacheService` à
      `max_login_attempts`/`lockout_duration`, bootstrap 2FA `2fa_setup_only` 15 min pour
      admin sans MFA, 2FA normal requis + vérifié via `SQLAlchemyTOTPStorage` — lecture seule,
      TOTP réel avec `pyotp`), **`login/phone`** (suivi initialement séparé, complété dans la
      foulée : `UserDB.phone_country_code`/`phone_number` ajoutées comme colonnes indexées
      dédiées — mirées dans le `metadata` du `User` port en lecture, le dataclass Core n'ayant
      pas de champs téléphone propres — ; `SQLAlchemyPhonePasswordLookup` + logique de login
      partagée avec `login/email` extraite dans un helper `_login()` commun ; `register` reste
      email-only, aucun des deux adaptateurs ne peut créer un compte téléphone via cette tâche),
      `refresh` (rotation via un nouveau module `refresh_tokens.py` —
      `jwt_service.refresh_tokens_async` s'est révélé inutilisable hors Django : il importe
      `tenxyte.models.RefreshToken` en dur), `logout`/`logout/all` (révocation réelle, blacklist
      JWT), `me` GET/PATCH (`allow_any_scope=True`, nouveau paramètre de `require_jwt` — parité
      avec l'absence d'enforcement de scope de `IsAuthenticated`), `me/roles` (scope enforcé,
      listes vides — pas de RBAC dans le Reference_Stack). Cookie refresh opt-in implémenté pour
      de vrai (`refresh_token_cookie_enabled` existait déjà sur `core/settings.py`). Suppression
      du `routers.py` PoC + son test, divergences documentées dans `CHANGELOG.md` sous
      `[Unreleased]`. **Ajout Core nécessaire** : `AuthenticationService.authenticate_async`
      (voir tâche 1.4). **Explicitement hors scope (documenté, pas silencieux)** :
      *inscription* par téléphone (`RegisterRequest` reste email-only — la règle croisée
      `validate()` de Django n'est pas répliquée) ; `must_change_password`/`password_change_only`
      (champ Django-only, feature désactivée par défaut, spec séparée
      `specs/force_password_change_on_first_login/` non exécutée) ; RBAC réel sur `me/roles`
      (Groupe D, tâche 10.1) ; listing admin `RefreshTokenDB` (Groupe D). `errors.py`'s
      `TenxyteAPIError` étendu avec un champ `extra` (champs top-level additionnels —
      `retry_after`, `requires_2fa` — au-delà de `error`/`code`/`details`, nécessaires pour
      quelques réponses Django qui en portent plus).
      **Bug réel trouvé par exécution (pas juste par lecture)** : un mot de passe de plus de 72
      octets UTF-8 (indépendant du nombre de caractères — des caractères multi-octets suffisent
      largement en dessous de toute limite en caractères) fait planter `bcrypt.hashpw`/
      `bcrypt.checkpw` avec un 500 non géré, découvert par le test de propriété Hypothesis
      d'anti-énumération (5.2) générant des mots de passe arbitraires. Corrigé : `register`
      rejette proprement (400 `VALIDATION_ERROR`) avant d'appeler bcrypt ; `check_password_async`
      (dans `auth_lookup.py`) traite un mot de passe trop long comme un mot de passe incorrect
      (retourne `False`) plutôt que de planter. `_run_dummy_check`/`_run_dummy_check_async`
      (`core/auth_service.py`) n'avaient PAS ce bug — leur `except Exception: pass` avalait déjà
      la `ValueError`. Deux tests de régression ajoutés (`test_register_password_over_72_bytes_*`,
      `test_login_password_over_72_bytes_*`).
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.2 Write property test for anti-enumeration parity (groupe A)
    - **Property 3: Parité de l'anti-énumération (register)** —
      `test_register_anti_enumeration_property.py`, Hypothesis génère email/mot de passe,
      compare la *forme* (clés + types) de la réponse pour un compte existant vs inexistant :
      identique dans les deux cas (201, mêmes clés).
    - **Validates: Requirements 4.3**

  - [x] 5.3 Contract_Suite + matrice sur A
    - `parity_matrix --groups=A` : **vert** (9/9 endpoints du groupe portés). La Contract_Suite
      (tâche 3.2) tourne verte sur `register`/`login/email` (6/6) ; `login/phone` couvert
      directement dans `test_auth_router.py` (3 tests, dont un qui fige — comme le fait déjà le
      snapshot Django — que `/login/email/` et `/login/phone/` renvoient le même jeu de clés)
      plutôt que dans la Contract_Suite elle-même, faute d'un point d'amorçage
      backend-spécifique dans la fixture `api` (voir la note dans `tests/contract/conftest.py`) ;
      étendre la Contract_Suite à `refresh`/`logout`/`logout/all`/`me`/`me/roles` reste ouvert
      mais ne bloque plus ce jalon — `parity_matrix` (qui gate réellement CI) est déjà vert.
    - _Requirements: 5.1, 5.2_

- [ ] 6. Vague de parité B — Password
  - [x] 6.1 Porter le groupe B
    - **Contrat extrait par recherche exhaustive de `views/password_views.py` +
      `serializers/password_serializers.py`** — recherche qui a aussi trouvé plusieurs
      divergences doc/code réelles côté Django lui-même (pas des trouvailles côté FastAPI) :
      `PasswordResetConfirmView` n'a jamais de code `OTP_EXPIRED`/champ `details` (toujours
      `{"error", "code": "RESET_FAILED"}`) et n'a JAMAIS de rejet 400 sur mot de passe compromis
      (200 + `password_safe: false` seulement) ; `ChangePasswordView`'s vrai message de rejet
      HIBP diffère du texte documenté ; `PasswordStrengthView`/`PasswordRequirementsView`'s
      `requirements` est une `list[str]`, pas l'objet `{"min_length": ..., ...}` documenté ;
      et surtout — **`PasswordHistory.add_password` est défini mais jamais appelé nulle part**,
      donc le rejet `PASSWORD_REUSED` documenté est fictif : ne PAS le porter aurait été une
      régression de parité, pas un raccourci.
      **Les 6/6 endpoints désormais portés et testés pour de vrai** (34 tests dans
      `test_password_router.py`, complétés en deux temps) : `password/strength` (calculateur de
      force réimplémenté — pas une réutilisation de `tenxyte.validators` : ce module fait
      `from .conf import auth_settings`, qui importe `django.conf.settings` au chargement, donc
      inimportable depuis un process FastAPI sans Django ; réimplémentation pilotée par les
      propriétés déjà existantes sur `core/settings.py` — `password_min_length`,
      `password_require_uppercase/lowercase/digit/special` —, formes structurelles identiques,
      messages en anglais plutôt que le catalogue français de Django, qu'aucun contrat d'API
      raisonnable n'exige de reproduire mot pour mot), `password/requirements`, `password/change`
      (reauth par mot de passe actuel réel, check HIBP réel — `breach_check.py`, même raison de
      réimplémentation que `tenxyte.services.breach_check_service` : import Django au
      chargement —, hash + révocation réelle des sessions, **et désormais aussi un rejet réel des
      mots de passe faibles** — `password_strength.validate()` en gate avant le reauth, manquant
      dans la première passe). `core/settings.py` gagne `breach_check_reject` (n'existait pas,
      seul `breach_check_enabled` y était déjà) et `otp_login_validity_minutes` (la seule
      expiration OTP réellement pilotée par un setting côté Django — les autres, voir tâche 7.1,
      sont des littéraux en dur malgré des settings `OTP_EMAIL_VALIDITY`/`OTP_PHONE_VALIDITY`
      jamais lus). Une fois le stockage OTP construit (tâche 7.1) : `password/reset/request`
      (anti-énumération — 200 à corps vide si compte inconnu, 200 avec `otp_id`/`expires_at` si
      trouvé, exactement le comportement Django réel — même si les DEUX cas ne sont PAS
      byte-identiques, Django lui-même ne le garantit pas ici, seul le code 200 l'est),
      `password/reset/confirm` (compte inconnu et code invalide donnent le même code
      `RESET_FAILED` — reproduit tel quel ; check HIBP **non bloquant** — `password_safe: false`
      dans la réponse, mot de passe quand même réinitialisé — comportement Django réel vérifié,
      pas un raccourci), `password/set-initial` (garde-fou compte déjà pourvu d'un mot de passe,
      OTP de type `login` obligatoire comme preuve, aucun mot de passe existant à vérifier).
      OTP-based reauth sur `password/change` reste hors scope (réutiliserait un OTP de type
      `login` en dehors du flux de login lui-même — plus que ce que cet endpoint justifie à lui
      seul) : un `otp_code` seul (sans `current_password`) donne toujours `REAUTH_REQUIRED`.
      Également hors scope, à raison (comportement Django réel, pas un manque) : historique de
      mots de passe (voir plus haut — code mort côté Django), et la branche
      `must_change_password`/upgrade de scope sur changement/reset réussi (le scope
      `password_change_only` n'est émis nulle part par défaut — même constat que pour le
      Groupe A). `parity_matrix --groups=B` : **6/6, vert**.
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 6.2 Contract_Suite + matrice sur A+B (anti-énumération reset incluse)
    - `parity_matrix --groups=A,B` : vert (tâche 6.1 fermée). Reste à faire : étendre
      `tests/contract/` (tâche 3.2) aux nouveaux endpoints de A et B — Property 3 (reset) n'a
      pour l'instant qu'un test direct (`test_password_reset_request_unknown_account_is_anti_enumeration`
      dans `test_password_router.py`), pas encore un test de contrat partagé avec le côté Django.
    - **Property 3 (reset)** · _Requirements: 4.3, 5.1, 5.2_

- [ ] 7. Vague de parité C — OTP, passwordless, 2FA
  - [x] 7.1 Porter le groupe C
    - **Contrat extrait par recherche exhaustive** de `views/otp_views.py`,
      `views/login_otp_views.py`, `views/magic_link_views.py`, `views/twofa_views.py`,
      `services/otp_service.py`, et du modèle `OTPCode` (`models/operational.py`) — recherche
      qui a confirmé que Django n'a **jamais extrait l'OTP vers Core** (contrairement à
      TOTP/MagicLink) : `OTPService` est 100 % couplé à l'ORM Django, donc pas de "réimplémen­
      tation évitant un import Django" possible ici comme pour `password_strength.py`/
      `breach_check.py` — il fallait un algorithme neuf, vérifié contre le comportement Django
      *réel* (constaté, pas documenté) : codes à 6 chiffres (`secrets.randbelow`, pas `random`),
      seul le hash SHA-256 est stocké (jamais le code en clair), vérification par
      `hmac.compare_digest`, comptage des tentatives via `UPDATE` conditionnel **atomique**
      (jamais lecture-puis-écriture Python, pour éviter une race entre vérifications
      concurrentes), `max_attempts` toujours 3 (le vrai défaut du modèle — le setting
      `OTP_MAX_ATTEMPTS` existe mais n'est lu nulle part), expirations 15/10/15 min pour
      email/téléphone/reset (littéraux en dur côté Django malgré des settings
      `OTP_EMAIL_VALIDITY`/`OTP_PHONE_VALIDITY` jamais lus — non répliqués, porter un setting
      mort n'aurait aucun sens), 10 min pour `login` (seule expiration réellement pilotée par un
      setting côté Django — `core/settings.py` gagne `otp_login_validity_minutes`).
      **Infrastructure construite** : `OTPCodeDB` (nouvelle table, `models_sa.py`),
      `otp_service.py` (`generate_otp`/`verify_otp`, framework-agnostic, algorithme ci-dessus) ;
      `SQLAlchemyTOTPStorage` (`totp_storage.py`) passe de lecture-seule à lecture/écriture
      complète — `save_totp_secret_async`/`save_backup_codes_async`/`enable_2fa_async`/
      `disable_2fa_async` implémentés (délèguent à de nouvelles méthodes Reference_Stack-only
      sur `SQLAlchemyAsyncUserRepository`) ; `UserDB` gagne les colonnes `phone_verified` et
      `backup_codes` (JSON, codes de secours hashés bcrypt — jamais le texte en clair). Le
      dataclass Core `User` (port partagé Django+FastAPI) gagne `phone_verified: bool` par
      cohérence avec `email_verified` existant.
      **Bug réel trouvé et corrigé côté Django, pas côté FastAPI** (découvert en ajoutant
      `phone_verified` juste à côté) : `DjangoUserRepository._django_user_to_core` lisait
      `getattr(django_user, "email_verified", False)` — mais le champ du modèle s'appelle
      `is_email_verified`, pas `email_verified` ; l'attribut n'existait donc jamais et
      `email_verified` retombait TOUJOURS sur `False`, quel que soit le vrai statut de
      vérification, pour tout objet `User` Core construit depuis Django. Corrigé
      (`getattr(django_user, "is_email_verified", False)`), suite Django complète relancée pour
      confirmer l'absence de régression avant de committer ce correctif.
      **8 des 11 endpoints du groupe désormais portés et testés pour de vrai** :
      `routers/otp.py` (8 tests dans `test_otp_router.py`) — `otp/request` (email/téléphone,
      `NO_EMAIL`/`NO_PHONE` si le champ manque sur le compte, livraison "fire-and-forget" comme
      Django — aucun backend email/SMS réel dans le Reference_Stack, un simple log tient lieu
      d'envoi, ce qui est observationnellement identique à Django du point de vue de l'appelant
      puisque Django lui-même renvoie 200 sans vérifier si l'envoi a réussi), `otp/verify/email`,
      `otp/verify/phone` (marquent `email_verified`/`phone_verified`, code générique
      `OTP_VERIFICATION_FAILED` pour tous les échecs — comportement Django réel confirmé, pas
      une simplification : les codes `INVALID_OTP`/`OTP_EXPIRED`/`MAX_ATTEMPTS_REACHED` des
      exemples `@extend_schema` sont de la documentation aspirationnelle, jamais produits par le
      vrai code). Complète aussi la tâche 6.1 (`password/reset/*`, `password/set-initial`), qui
      dépendait de cette même infrastructure OTP.
      `routers/twofa.py` (10 tests dans `test_twofa_router.py`) — `2fa/status`, `2fa/setup`
      (`TOTPService.setup_2fa_async` écrit secret + codes de secours via `SQLAlchemyTOTPStorage`,
      désormais en écriture complète), `2fa/confirm` (active le MFA, upgrade bootstrap → token
      plein scope + blacklist du token bootstrap quand `auth.scope == "2fa_setup_only"` — même
      mécanique que Django, vérifiée par un test qui reconfirme que le token bootstrap est
      *rejeté* après usage), `2fa/disable` (reauth par mot de passe uniquement — même raison que
      `password/change/`, voir le docstring du module —, désactive), `2fa/backup-codes`
      (régénération, vérifiée avec un code du pas TOTP suivant pour éviter la protection anti-
      rejeu légitime qui aurait autrement rejeté un `now()` répété dans la même fenêtre de 30s).
      Contrairement à Django (deux écritures séparées — `TOTPStorage.enable_2fa`/`disable_2fa`
      **et** `user_repo.enable_mfa`/`disable_mfa`, deux champs distincts sur `User`), le
      Reference_Stack n'a qu'un seul signal (`mfa_type`) donc `SQLAlchemyTOTPStorage.
      enable_2fa_async`/`disable_2fa_async` appellent déjà `enable_mfa`/`disable_mfa`
      en interne — pas de double écriture nécessaire côté routeur. `app.state.tenxyte_totp_service`
      ajouté (instance unique construite dans le lifespan, pas une par requête — sa
      `replay_protection` doit survivre entre requêtes pour protéger réellement contre le
      rejeu ; corrige au passage un bug latent dans `routers/auth.py`'s `_login()`, qui
      instanciait un `TOTPService` neuf à chaque connexion, rendant sa protection anti-rejeu
      inopérante depuis la Vague A — la connexion utilise maintenant la même instance partagée).
      **Deuxième bug réel trouvé et corrigé, celui-ci dans le code FastAPI déjà livré** (Vague A) :
      la branche anti-énumération de `register` construisait à la main un dict `user` différent
      en forme de celui que produit `_serialize_user()` sur le chemin réel (clés manquantes —
      `username`/`avatar`/`roles`/... —, et `phone: ""` au lieu de `phone: None`) : exactement le
      signal d'énumération que cet endpoint existe pour empêcher. Trouvé par le test de propriété
      Hypothesis d'anti-énumération (tâche 5.2) sur un exemple qu'il n'avait pas exploré
      auparavant. Corrigé en construisant un `User` synthétique et en le passant par la même
      `_serialize_user()` que le chemin réel, garantissant une forme identique par construction
      plutôt que par appariement manuel.
      **Les 4 derniers endpoints du groupe (`login/otp/request`, `login/otp/verify`,
      `magic-link/request`, `magic-link/verify`) portés et testés** — `parity_matrix --groups=C` :
      **12/12, vert** (le groupe compte en réalité 12 endpoints, pas 11 comme estimé plus haut ;
      décompte corrigé après génération complète de `docs/{en,fr}/parity_table.md`).
      `core.magic_link_service.MagicLinkService` s'est confirmé 100 % framework-agnostic et déjà
      async-complet à la lecture (aucun import Django dans le fichier) — seul un repository
      Reference_Stack manquait : `magic_link_repo.py` (`SQLAlchemyMagicLinkRepository` +
      `SQLAlchemyUserLookup`, async uniquement — même convention que `SQLAlchemyTOTPStorage` :
      les méthodes sync du Protocol lèvent `NotImplementedError`), adossé à `MagicLinkTokenDB`
      (déjà créé). `email` n'est pas une colonne de `MagicLinkTokenDB` (comme le vrai modèle
      Django `MagicLinkToken`, qui n'en a pas non plus) — dérivé via une seconde requête sur
      `UserDB`, à l'identique de `DjangoMagicLinkRepository.get_by_token`'s `token_obj.user.email`.
      Livraison email adossée à `ConsoleEmailService` (déjà fourni par Core, imprime au lieu
      d'envoyer) — même posture "aucun backend réel câblé" que `otp_service.py`.
      `routers/magic_link.py` (9 tests, `test_magic_link_router.py`) préserve deux
      excentricités **réelles** de `MagicLinkVerifyView` plutôt que de les "corriger" (ce qui
      serait une rupture de parité) : la réponse de `verify/` utilise les clés `access`/`refresh`
      (pas `access_token`/`refresh_token` comme partout ailleurs), et `application_id` n'est
      jamais transmis ni à `request_magic_link` ni à `verify_magic_link` par la vue Django
      elle-même, rendant sa propre vérification de correspondance d'application morte en
      pratique.
      `login/otp` a nécessité deux nouvelles properties Core (`Settings.otp_login_enabled`,
      défaut `False`, et `otp_login_auto_register`, défaut `True` — `otp_login_validity_minutes`
      existait déjà) et un `LoginOTPRequestRequest`/`LoginOTPVerifyRequest` (schemas.py).
      `routers/login_otp.py` (12 tests, `test_login_otp_router.py`) réplique fidèlement
      `_login()` (bootstrap admin 2FA, vérification TOTP normale, anti-énumération) sans le
      mot de passe — la vérification pré-consommation du code (2FA requis AVANT que l'OTP soit
      marqué utilisé, pour permettre une seconde passe OTP+TOTP) est couverte par un test dédié.
      Le port phone-only Django (compte sans email) n'existe pas dans le Reference_Stack
      (`UserDB.email` reste `nullable=False, unique=True`) — l'auto-inscription y génère un email
      placeholder unique non routable (`{uuid4()}@passwordless.invalid`), documenté dans le
      routeur comme un compromis de schéma, pas un oubli.
      **Trouvaille vérifiée, pré-existante côté Django, non corrigée ici** (voir le docstring de
      `routers/login_otp.py` et `test_verify_unknown_account_and_wrong_code_both_401_otp_invalid`) :
      l'anti-énumération de `login/otp/verify/` ne tient qu'au niveau statut/`code` — le champ
      `error` diffère réellement selon le cas (compte inconnu → `"Invalid or expired code"` ;
      compte réel sans code en attente → `"No login code found"` ; compte réel avec code actif et
      mauvaise tentative → `"Invalid code. N attempt(s) remaining."`). C'est le comportement réel
      de `LoginOTPVerifyView`/`OTPService.verify_login_otp`, pas une régression introduite par ce
      port — répliqué tel quel plutôt que silencieusement durci, ce qui serait une amélioration
      hors périmètre de cette tâche de parité.
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
