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

  - [x] 6.2 Contract_Suite + matrice sur A+B (anti-énumération reset incluse)
    - `parity_matrix --groups=A,B` : vert. `tests/contract/` étendu (task 7.3, fait en même temps
      que l'extension à C — voir cette tâche pour le détail : `test_group_b_shapes.py`,
      `password/requirements`, `password/reset/request` (Property 3, y compris la variante
      "corps vide" du cas compte-inconnu, comportement Django réel préservé, voir docstring)).
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

  - [x] 7.2 Write property test for feature-flag and scope parity
    - **Property 8: Parité des feature-flags et des scopes** (combinatoire flags × endpoints,
      scopes `2fa_setup_only`/`password_change_only`) — `test_feature_flag_scope_parity_property.py`
      (5 tests). Seuls les flags réellement câblés dans le Reference_Stack aujourd'hui sont
      couverts (`otp_login_enabled`, `magic_link_enabled`) — `WEBAUTHN_ENABLED`/`AIRS_ENABLED`/
      `FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` (aussi nommés dans `design.md`) n'existent
      pas encore côté FastAPI (Vagues F/G non commencées, force-password-change explicitement
      hors périmètre — voir docstring `routers/auth.py`) ; à étendre quand ces vagues arriveront.
      **Trouvaille documentée, pas un bug** : `magic_link_enabled=False` ne produit PAS le même
      `404 FEATURE_DISABLED` générique que `otp_login_enabled=False` — comportement Django réel
      déjà vérifié en tâche 7.1 (`request/` → `503 SERVICE_UNAVAILABLE`, `verify/` → `401
      MAGIC_LINK_INVALID`, indissociable d'un token simplement invalide). Le test combinatoire de
      scope (`test_scope_allow_list_enforced_consistently_across_every_protected_endpoint`) couvre
      les 14 endpoints actuellement protégés par JWT × 4 scopes de jetons (plein, `2fa_setup_only`,
      `password_change_only`, un scope arbitraire inconnu) — 56 combinaisons en une seule requête
      chacune, un jeton neuf par appel (pas de réutilisation : `logout/all/` blackliste réellement
      le jeton qui l'appelle, un jeton réutilisé aurait pollué les assertions suivantes — trouvé et
      corrigé pendant l'écriture du test lui-même, pas dans le code produit).
    - **Validates: Requirements 4.4**

  - [x] 7.3 Contract_Suite + matrice sur A+B+C
    - `parity_matrix --groups=A,B,C` : vert. `tests/contract/conftest.py` gagne `get()` (les deux
      clients — `2fa/status`, `password/requirements`, `magic-link/verify` sont des GET),
      `register_and_login()` (helper partagé : inscription + connexion, identique sur les deux
      adapters puisque Group A est déjà prouvé) et une normalisation de corps vide (`{}` au lieu
      d'un crash `.json()`/`response.data is None` — nécessaire pour `password/reset/request`,
      dont la branche compte-inconnu renvoie un corps HTTP réellement vide côté Django, `Response
      (status=200)` sans `data`) et une normalisation `JsonResponse` (`@require_jwt`'s propre
      court-circuit d'échec d'auth renvoie du Django brut, pas un DRF `Response`, donc pas de
      `.data`). `test_group_b_shapes.py` (3 tests), `test_group_c_shapes.py` (5 tests) : pas une
      couverture exhaustive de chaque endpoint des deux groupes (même échelle que
      `test_group_a_shapes.py`, qui n'en couvre pas non plus la totalité) mais un échantillon
      représentatif — forme du succès + anti-énumération là où elle s'applique
      (`password/reset/request`, `magic-link/request`) + parité du 401 `AUTH_REQUIRED`.
    - _Requirements: 5.1, 5.2_

- [x] 8. Checkpoint - Ensure all tests pass
  - Vagues A–C vertes sous toutes les gates : `parity_matrix --groups=A,B,C` (27/114 dont 100 %
    de A+B+C), `check_async_purity.py` (aucun motif bloquant), Contract_Suite (22 tests, deux
    adapters), coverage FastAPI 94%+ (seuil CI 90 %), suite Django complète (2238 passed, 5
    skipped, aucune régression), `ruff`/`black` propres sur `src/`.

- [ ] 9. Vague de parité F — AIRS
  - [x] 9.1 Porter le groupe F
    - **Contrat extrait par recherche exhaustive** de `views/agent_views.py`,
      `services/agent_service.py`, `models/agent.py`, `middleware.py`'s `AgentAuthMiddleware`,
      `conf/airs.py`, **et** la spec normative `spec/airs/AIRS-1.0.md` (§2–11) elle-même — porté
      contre le protocole normatif, pas seulement contre le code Django, avec les clauses
      `[AIRS-<LEVEL>-n]` citées en commentaire dans `airs_service.py`/`routers/airs.py`.
      **Blocage architectural trouvé avant tout code** : `AgentTokenService.create()` exige de
      vérifier que l'utilisateur humain détient réellement chaque permission déléguée
      (`has_permission`/`has_org_permission`, RBAC complet — rôles, hiérarchie, octrois directs)
      — c'est-à-dire le Groupe D, qui arrive *après* F dans l'ordre A→B→C→F→D→E→G. Décision
      utilisateur (confirmée) : bypass `is_superuser` uniquement, rejet pour tout le monde
      d'autre — fail-closed, aucune régression de sécurité par rapport à Django, mais seul un
      superuser peut utiliser la délégation de permissions tant que le Groupe D n'existe pas.
      Documenté en tête de `airs_service.py`.
      **Infrastructure construite** : `AgentTokenDB`/`AgentPendingActionDB` (nouvelles tables,
      `models_sa.py` — `granted_permissions` en JSON, pas de M2M vers une table `Permission`
      inexistante) ; `airs_service.py` (create/validate/revoke/suspend/revoke_all/heartbeat/
      check_circuit_breaker/create_pending_action/confirm/deny/report_usage, framework-agnostic
      au même sens que `otp_service.py` — AIRS n'a jamais été extrait vers Core côté Django non
      plus, donc rien à réutiliser) ; `routers/airs.py` (12 endpoints).
      **`resolve_agent_token_async` reproduit `AgentAuthMiddleware`** (enabled-check → validation
      du token → circuit breaker, mêmes codes `AGENT_TOKEN_<raison>`/`AIRS_DISABLED` qu'en Annexe
      A) en dépendance locale aux deux endpoints qui en ont besoin (`heartbeat`,
      `report-usage`) plutôt qu'en middleware global — le Reference_Stack n'a encore aucun autre
      endpoint métier pour laquelle une authentification `AgentBearer` site-wide aurait un sens
      (Groupes D/E).
      **Non répliqué, documenté** : le double-comptage de `current_request_count` (le middleware
      Django valide et incrémente une fois, puis la vue elle-même revalide et incrémente une
      deuxième fois sans jamais lire `request.agent_token` — effet de bord d'un code mort, pas un
      contrat délibéré ; aucun test de la Conformance_Suite ne vérifie un compte exact, seul le
      franchissement de seuil compte).
      **Erreurs non codées répliquées telles quelles** (vérifiées directement dans
      `agent_views.py`, pas supposées) : `AIRS is disabled` (400), `Application context required`
      (400), `Organization not found` (404), l'en-tête `Authorization` absent/malformé et le
      mismatch id-de-token sur heartbeat/report-usage (401/403) — aucun de ces cinq n'a de champ
      `code` côté Django réel, construits ici via `JSONResponse` brut plutôt que
      `TenxyteAPIError` (qui exige un `code`).
      **Trouvaille de fidélité au spec, corrigée avant qu'elle ne devienne un vrai gap** : la
      découverte annonçait `"trace"` sans qu'aucune persistance de `X-Prompt-Trace-ID` n'existe
      réellement — violation directe de `[AIRS-CORE-19]` ("MUST NOT claim a level... without
      satisfying every normative clause"). Corrigé en ajoutant `AgentActionLogDB` (table d'audit
      minimale, `models_sa.py`) et `airs_service.sanitize_prompt_trace_id`/`log_agent_action_async`
      — persistance réelle sur `heartbeat`/`report-usage`, testée (`test_wellformed_trace_id_is_durably_persisted`).
      Organisations (`organization`) acceptées et renvoyées mais jamais utilisées pour autoriser
      quoi que ce soit (pas de table `Organization` — Groupe E) ; une recherche sur une table
      toujours vide renvoie honnêtement 404 "Organization not found" pour n'importe quel slug,
      donc le comportement observable ne diverge pas silencieusement.
      25 tests (`test_airs_router.py`), aucun mock, base aiosqlite éphémère réelle.
      `parity_matrix --groups=F` : **12/12, vert** (nécessitait de renommer les path params
      FastAPI `{token_id}`/`{path_token}` en `{pk}`/`{token}` pour matcher exactement les noms de
      convertisseur Django `<int:pk>`/`<str:token>` — le comparateur du script matche les chemins
      littéralement, pas juste "est un paramètre").
      **Restant pour 9.2** : `require_agent_clearance`-équivalent (dépendance FastAPI) + endpoints
      de démo `_conformance_probe/`/`_hitl_probe/` + équivalent `seed_and_serve.py` + job CI —
      nécessaires pour exécuter `spec/airs/conformance/` (les 5 fichiers `test_*.py`, ~21 tests)
      contre le Reference_Stack ; le hook optionnel `revoke_delegating_user_permission` ne sera
      pas fourni côté FastAPI (RBAC non implémenté — le test correspondant skippera proprement,
      exactement comme prévu par le design du conftest partagé).
    - _Requirements: 4.1, 4.2, 4.4, 4.6_

  - [x] 9.2 Exécuter la Conformance_Suite z_aud_2 contre FastAPI
    - **Property 11: Conformité AIRS indépendante de l'adapter** — nouveau job CI
      `airs-conformance-fastapi` (`airs-conformance` était déjà pris par la version Django —
      deux jobs ne peuvent pas partager un ID, même nom d'esprit que `fastapi-tests`/
      `django-tests`/`core-tests` déjà voisins dans ce workflow) contre l'app FastAPI éphémère,
      tous niveaux (`core`/`hitl`/`guards`/`budget`/`trace`).
      **Construit** : `airs_clearance.py` (`require_agent_clearance`, équivalent FastAPI du
      décorateur Django — ne gate que les appelants `AgentBearer`, laisse passer tout le reste
      sans condition, exactement comme Django n'inspecte `request.agent_token` que pour ce
      schéma) ; `AgentClearancePending` + son exception handler (`errors.py`) pour le contrat
      202 `pending_confirmation` (`[AIRS-HITL-3]`) — un handler d'exception plutôt qu'un
      court-circuit ad-hoc par endpoint, pour que n'importe quel endpoint protégé obtienne le
      contrat 202 gratuitement ; `spec/airs/conformance/tenxyte_ci_fastapi/` (miroir FastAPI de
      `tenxyte_ci/` côté Django) — `demo_views.py` (`_conformance_probe/`/`_hitl_probe/`,
      réutilisés tels quels par `test_airs_clearance.py`, pas dupliqués) et `seed_and_serve.py`.
      `resolve_agent_token_async` déplacé de `routers/airs.py` vers `airs_service.py` (tâche
      9.1) pour être partageable entre le routeur canonique et `airs_clearance.py` sans import
      circulaire.
      **`seed_and_serve.py` sème un superuser, pas un utilisateur RBAC normal** (contrairement à
      Django) — conséquence directe de la décision de la tâche 9.1 (bypass superuser
      uniquement) : sans ça, `issue_token()` échouerait dès la première requête. Le JWT est miné
      directement (pas de login HTTP) pour éviter le bootstrap 2FA qu'un superuser sans MFA
      recevrait sur un vrai login. Aucun hook `revoke_delegating_user_permission` fourni — le
      test correspondant skip proprement, comme prévu.
      **Bug de test réel trouvé et corrigé pendant la vérification locale** (pas un bug produit) :
      `base_url` incluait initialement `settings.api_prefix` (`http://host:port/api/v1`) — httpx
      `Client(base_url=...)` *concatène* plutôt que remplace un chemin absolu passé à `.post()`
      quand `base_url` porte déjà un chemin, donnant `/api/v1/api/v1/ai/tokens/` (404). Corrigé en
      alignant sur la convention exacte de Django : `base_url` est une origine nue
      (`http://host:port`, sans chemin), chaque endpoint découvert porte son chemin complet.
      **Vérifié localement en conditions réelles avant tout job CI** (pas seulement "ça devrait
      marcher") : serveur FastAPI éphémère démarré, `spec/airs/conformance/` (hors
      `negative_control`) exécuté contre lui — **22 passed, 2 skipped** (exactement les deux
      skips documentés ci-dessus), confirmant que la conformité AIRS est bien indépendante de
      l'adapter. 9 tests unitaires supplémentaires (`test_airs_clearance.py`) couvrant
      Double Validation et le cycle HITL confirm/deny/replay directement.
    - **Validates: Requirements 4.6, 5.5**

  - [x] 9.3 Contract_Suite + matrice sur A+B+C+F
    - `parity_matrix --groups=A,B,C,F` : vert (39/114). `test_group_f_shapes.py` (4 tests ×
      2 adapters = 8) : découverte (forme documentée + identique anonyme/authentifié,
      `[AIRS-DISC-2]`), `ai/tokens/` (liste vide pour un utilisateur neuf, 401 si non
      authentifié). Volontairement plus étroit que A–C : exercer `ai/tokens/` (create) exigerait
      un Delegating User détenant réellement la permission demandée sur les **deux** adapters —
      le vrai RBAC Django (rôles/octrois directs) contre le bypass `is_superuser` uniquement du
      Reference_Stack (voir `airs_service.py`) — et l'`api` fixture n'a encore aucun moyen
      partagé de promouvoir un utilisateur `register_and_login()` vers l'un ou l'autre état.
      Laissé pour une extension future plutôt que bricolé ici ; la Conformance_Suite AIRS (tâche
      9.2) exerce déjà l'émission de tokens de bout en bout sur les deux adapters, Double
      Validation incluse, donc ce n'est pas un vrai trou de couverture côté comportement — juste
      de la portée non couverte par le Contract_Suite lui-même.
      **Trouvaille réelle, vérifiée, documentée plutôt que masquée** :
      `test_token_list_requires_auth_on_both_adapters` ne compare que le code de statut (401 sur
      les deux), pas la forme du corps — `AgentTokenListCreateView` utilise le DRF
      `IsAuthenticated` brut (jamais migré vers le format canonique `{error, code}` du reste de
      `agent_views.py`), donc son 401 est `{"detail": "Authentication credentials were not
      provided."}` (le défaut DRF), vérifié directement via `APIRequestFactory`, pas supposé —
      alors que le FastAPI_Adapter renvoie toujours la forme canonique via `require_jwt()`.
    - _Requirements: 5.1, 5.2_

- [x] Checkpoint Vague F : `parity_matrix --groups=F` (12/12), Conformance_Suite AIRS verte sur
  les deux adapters (22 passed, 2 skipped côté FastAPI — mêmes deux skips que documentés en 9.2),
  Contract_Suite étendue, coverage FastAPI 94%+ (seuil CI 90 %), suite Django complète (2238
  passed, 5 skipped, aucune régression à chaque commit de la vague), `ruff`/`black` propres sur
  `src/`.

- [x] 10. Vague de parité D — RBAC, applications, admin
  - [x] 10.1 Porter le groupe D (46 endpoints — la plus grosse vague du plan, largement plus
    grande que les précédentes ; découpée en chunks committables séparément plutôt qu'en un seul
    gros commit, même logique que les vagues précédentes)
    - **Chunk 1/5 fait — RBAC core (19/46)** : `permissions/*` (5), `roles/*` (5),
      `roles/{id}/permissions/*` (3), `users/{id}/roles/*` (3), `users/{id}/permissions/*` (3).
      **Contrat extrait par recherche exhaustive** de `views/rbac_views.py`,
      `serializers/rbac_serializers.py`, `filters.py` (`apply_permission_filters`/
      `apply_role_filters`), `pagination.py` (`TenxytePagination` — forme exacte
      count/page/page_size/total_pages/next/previous/results), et `models/auth.py`
      (`AbstractPermission`/`AbstractRole`/`User.has_permission`/
      `_get_effective_permission_codes`/`assign_role`/`remove_role`/`get_all_roles`).
      **Nouvelle infrastructure** : `PermissionDB`/`RoleDB` + trois tables d'association pures
      (`role_permissions_table`/`user_roles_table`/`user_direct_permissions_table`, `models_sa.py`
      — interrogées directement via `select`/`insert`/`delete`, pas de `relationship(secondary=…)`
      ORM, cohérent avec le reste de l'adapter qui évite le lazy-loading async) ; `rbac_service.py`
      (framework-agnostic au même sens que `otp_service.py`/`airs_service.py` — Django n'a jamais
      extrait le RBAC vers Core non plus) ; `pagination.py` (nouveau, réutilisable par tous les
      futurs endpoints listés de la vague D — `next`/`previous` construits via
      `request.url.include_query_params()`/`remove_query_params()`, vérifiés identiques au
      comportement exact de `get_next_link`/`get_previous_link` de DRF, y compris le retrait du
      paramètre `page` pour revenir à la page 1) ; `security.require_permission(code)` (nouvelle
      dépendance, compose `require_jwt()` bare + `rbac_service.has_permission_async`).
      **Hiérarchie des permissions répliquée exactement** : détenir une permission accorde
      implicitement tous ses descendants (et, formulation équivalente utilisée par
      `has_permission_async`, une permission est détenue si elle est directe OU si un ancêtre
      l'est) — vérifié par test contre une hiérarchie parent/enfant réelle. Bypass `is_superuser`
      **et** bypass rôle `super_admin` répliqués tous les deux (le second est facile à manquer en
      lisant vite `has_permission()` — capturé en lisant le code au lieu de le supposer).
      **Message d'erreur générique répliqué fidèlement** : `TENXYTE_VERBOSE_ERRORS` vaut `False`
      par défaut côté Django, donc un refus de permission renvoie toujours `{"error": "Permission
      denied.", "code": "PERMISSION_REQUIRED"}` — jamais le code de permission spécifique qui a
      manqué (`f"Permission required: {code}"` n'est produit qu'en mode verbeux, non répliqué).
      **Non répliqué, documenté** : le fallback MongoDB de `_safe_add_permissions`/
      `_safe_remove_permissions` (contourne un problème du collecteur de suppression Django ORM
      spécifique à MongoDB — sans objet pour le backend SQLAlchemy du Reference_Stack).
      **`me/roles/` (Vague A) corrigé au passage** : retournait `{"roles": [], "permissions": []}`
      en dur, documenté comme dépendant du Groupe D depuis sa création — maintenant que le RBAC
      existe, branché sur `rbac_service.get_all_role_codes_async`/`effective_permission_codes_async`,
      exactement comme Django's `MyRolesView`.
      14 tests (`test_rbac_router.py`), aucun mock, base aiosqlite éphémère réelle — CRUD complet
      permissions/rôles, hiérarchie, pagination (25 permissions créées pour forcer une 2ᵉ page),
      filtres (`search`, `parent=null`), erreurs (`NOT_FOUND`, `VALIDATION_ERROR`,
      `PERMISSIONS_NOT_FOUND`, `ROLE_NOT_FOUND`, `MISSING_PARAM`), bypass superuser/`super_admin`,
      refus générique, `me/roles/` avec données réelles.
      `parity_matrix` : 58/114 endpoints Django portés au total (19 nouveaux) — Groupe D pas
      encore gaté (`--groups=D` échouerait tant que les 27 endpoints restants ne sont pas prêts),
      Groupes A/B/C/F toujours verts.
      **Restant (chunks 2 à 5)** : `applications/*` (7 — réutilise `ApplicationDB`, déjà
      existante depuis la Vague A) ; `admin/users/*` (8 — nécessite d'étendre `UserDB`
      avec `is_banned`/`is_locked`/`locked_until`/`is_deleted`/`must_change_password`/
      `max_sessions`/`max_devices`, plus la logique d'anonymisation RGPD du soft-delete de
      Django, vérifiée dans `models/auth.py`) ; admin sécurité (7 — `AuditLogDB`/
      `LoginAttemptDB` nouvelles tables, plus persistance requêtable de la blacklist JWT,
      actuellement en mémoire seulement côté Reference_Stack) ; `dashboard/*` (5 — agrégations
      en lecture seule sur tout ce qui précède).
    - **Chunk 2/5 fait — Applications (7/46, 26/46 cumulé)** : `applications/*` — liste (avec
      pagination/recherche/filtre `is_active`), création (émet `access_key`/`access_secret` en
      clair une seule fois, jamais restitué ensuite), détail, mise à jour complète, activation/
      désactivation (`PATCH`), suppression, régénération des identifiants (exige
      `{"confirmation": "REGENERATE"}`). **Contrat extrait** de `views/application_views.py`,
      `serializers/application_serializers.py`, `filters.py` (`apply_application_filters`).
      **Réutilise `ApplicationDB`** (créée en Vague A pour l'auth `X-Access-Key`/
      `X-Access-Secret` — voir `application_auth.py`) plutôt qu'une nouvelle table ; colonnes de
      suivi Vague A (`description`/`updated_at`) ajoutées à `models_sa.py` car les colonnes
      d'origine ne couvraient que les besoins de `ApplicationAuthMiddleware`, pas toute la surface
      CRUD de ce chunk. `application_service.py` (nouveau, framework-agnostic même logique que
      `rbac_service.py`) ; `routers/applications.py` (nouveau, 7 endpoints, tous gatés par
      `require_permission` — `applications.view`/`create`/`update`/`delete`/`regenerate`,
      réutilise `pagination.py` du chunk 1 telle quelle).
      5 tests (`test_applications_router.py`), aucun mock, base aiosqlite éphémère réelle — cycle
      de vie CRUD complet, activation/désactivation avec rejet `INVALID_FIELDS` si aucun champ,
      régénération avec rejet `CONFIRMATION_REQUIRED` puis succès, pagination/recherche (22
      applications créées pour forcer une 2ᵉ page), refus générique de permission.
      `parity_matrix` : 65/114 endpoints Django portés au total (7 nouveaux) — Groupes A/B/C/F
      toujours verts ; coverage FastAPI 92.89 % (seuil CI 90 %) ; suite Django complète relancée,
      aucune régression.
      **Restant (chunks 3 à 5)** : `admin/users/*` (8) ; admin sécurité (7) ; `dashboard/*` (5) —
      inchangé par rapport à la note laissée au chunk 1.
    - **Chunk 3/5 fait — Admin Users (8/46, 33/46 cumulé)** : `admin/users/*` — liste (pagination
      + 8 filtres + recherche + tri), détail, mise à jour partielle, suppression (soft-delete
      RGPD), bannissement, débannissement, verrouillage, déverrouillage. **Contrat extrait** de
      `views/user_views.py` (`UserListView`/`UserDetailView`/`UserBanView`/`UserUnbanView`/
      `UserLockView`/`UserUnlockView`), `serializers/user_admin_serializers.py`, `filters.py`
      (`apply_user_filters`), et — point important — de `adapters/django/repositories.py`'s
      `DjangoUserRepository` (ce que la vue appelle réellement), pas seulement des serializers.
      **`UserDB` étendue** (`models_sa.py`) : `is_locked`/`locked_until`/`lockout_count`/
      `is_banned`/`is_deleted`/`deleted_at`/`anonymization_token`/`must_change_password`/
      `max_sessions`/`max_devices`. `admin_user_service.py` (nouveau, framework-agnostic même
      logique que `rbac_service.py`/`application_service.py`) ; `routers/admin_users.py`
      (nouveau, 8 endpoints, tous gatés par `require_permission` —
      `users.view`/`update`/`delete`/`ban`/`lock`). `pagination.py`'s `_apply_ordering` (privée,
      dupliquée dans `rbac_service.py` depuis le chunk 1) **extraite et partagée** en
      `pagination.apply_ordering`, réutilisée par les trois services de tri de la vague D
      (`rbac_service.py` mis à jour pour l'utiliser, sans changement de comportement — 19 tests
      RBAC relancés, toujours verts).
      **Deux trouvailles réelles, vérifiées en lisant `DjangoUserRepository` (pas supposées),
      répliquées plutôt que « corrigées »** (documentées en détail dans le docstring de module de
      `admin_user_service.py`) :
      1. `AdminUserUpdateSerializer` valide `is_staff`/`is_superuser`/`max_sessions`/
         `max_devices` en entrée, mais `DjangoUserRepository.update_user()` — la seule chose que
         la vue appelle pour persister — ne reconnaît que `first_name`/`last_name`/`email`/
         `is_active`/`is_email_verified`/`phone_country_code`/`phone_number`/
         `is_phone_verified`/`username`/`bio`/`timezone`/`language`/`custom_fields`. Ces quatre
         champs passent la validation et sont silencieusement ignorés — aucune erreur, aucun
         effet. `must_change_password` est le seul cas particulier (`DJANGO_ONLY_FIELDS` dans la
         vue, appliqué directement au modèle Django, en contournant le Core repository).
      2. `UserBanView`/`UserLockView` acceptent toutes deux un champ `reason` documenté comme
         « stocké dans le journal d'audit », mais `DjangoUserRepository.ban()`/`lock()` ne le
         persistent nulle part — aucune écriture `AuditLog` sur ce chemin (le chunk 4 ajoutera une
         vraie persistance d'audit-log, mais même une fois en place, cet appel précis ne
         l'alimente pas). `reason` est accepté, validé, puis abandonné.
      **Deux implémentations de soft-delete chez Django, une seule utilisée par l'API admin** :
      `AbstractUser.delete()` (override du `.delete()` Django ORM — anonymisation lourde : email
      `deleted_{id}_{timestamp}@anonymized.local`, vide aussi téléphone/TOTP/backup_codes) et
      `User.soft_delete()` (anonymisation plus légère : email `deleted_{id}@deleted.local`,
      prénom/nom vidés, révoque les refresh tokens). `DjangoUserRepository.soft_delete()` appelle
      exclusivement la seconde — c'est elle qui a été répliquée dans `soft_delete_async`
      (révocation des refresh tokens non répliquée : le Reference_Stack n'a pas de table de
      sessions persistée à révoquer, les refresh tokens n'y sont retrouvés que par hash).
      **Verrouillage avec escalade exponentielle répliquée exactement** : `lock_account()`
      double la durée à chaque verrouillage consécutif (`duration * 2^(lockout_count-1)`),
      plafonné à 1440 min (valeur par défaut de `LOCKOUT_MAX_DURATION_MINUTES`, codée en dur côté
      Reference_Stack faute d'équivalent de ce setting) — vérifié par test (verrouillage à 10 min,
      déverrouillage, second verrouillage à 10 min → 20 min effectifs).
      6 tests (`test_admin_users_router.py`), aucun mock, base aiosqlite éphémère réelle — liste/
      détail/404, mise à jour avec vérification explicite que les champs de privilège sont bien
      ignorés (trouvaille 1 testée, pas seulement documentée), soft-delete + rejet
      `ALREADY_DELETED` en double suppression, cycle ban/unban avec rejets `ALREADY_BANNED`/
      `NOT_BANNED`, cycle lock/unlock avec escalade et rejets `ALREADY_LOCKED`/`NOT_LOCKED`, refus
      générique de permission.
      `parity_matrix` : 73/114 endpoints Django portés au total (8 nouveaux) — Groupes A/B/C/F
      toujours verts ; coverage FastAPI 92.56 % (seuil CI 90 %, 203 tests) ; suite Django complète
      relancée, aucune régression.
      **Restant (chunks 4-5/5)** : admin sécurité (7 — `AuditLogDB`/`LoginAttemptDB` nouvelles
      tables, plus persistance requêtable de la blacklist JWT) ; `dashboard/*` (5 — agrégations
      en lecture seule).
    - **Chunk 4/5 fait — Admin Security (7/46, 40/46 cumulé)** : `admin/audit-logs/*` (liste +
      détail), `admin/login-attempts/*` (liste), `admin/blacklisted-tokens/*` (liste + cleanup),
      `admin/refresh-tokens/*` (liste + revoke). **Contrat extrait** de `views/security_views.py`
      (`AuditLogListView`/`AuditLogDetailView`/`LoginAttemptListView`/`BlacklistedTokenListView`/
      `BlacklistedTokenCleanupView`/`RefreshTokenListView`/`RefreshTokenRevokeView`),
      `serializers/security_serializers.py`, `filters.py` (`apply_audit_log_filters`/
      `apply_login_attempt_filters`).
      **Trouvaille vérifiée en lisant le code plutôt que supposée** : les 7 endpoints exigent tous
      la même permission `security.view` — y compris les deux actions `POST` (cleanup, revoke),
      qui n'ont **pas** de permission d'écriture séparée type `security.manage`. Répliqué à
      l'identique.
      **Nouvelles tables** (`models_sa.py`) : `BlacklistedTokenDB`, `AuditLogDB` (sous-ensemble de
      `tenxyte.models.security.AuditLog` — seulement les champs qu'`AuditLogSerializer` expose
      réellement ; le contexte AIRS du modèle Django — `agent_token`/`on_behalf_of`/
      `prompt_trace_id` — n'est pas dans ce serializer, donc pas répliqué ici), `LoginAttemptDB`.
      `RefreshTokenDB` (Vague A) étendue avec `application_id`/`device_info`/`ip_address`/
      `last_used_at` pour couvrir la forme complète d'`RefreshTokenAdminSerializer`.
      **`BlacklistedTokenDB` réellement alimentée, pas une coquille vide** : contrairement à
      `AuditLogDB`/`LoginAttemptDB` (voir note de portée ci-dessous), le blacklisting est câblé
      dans les 3 points d'appel réels qui blacklistent déjà un token en mémoire
      (`routers/auth.py`'s `logout`/`logout_all`, `routers/twofa.py`'s blacklist du token
      bootstrap au confirm 2FA) via `admin_security_service.record_blacklisted_token_async`,
      appelé **en plus de** (pas à la place de) `InMemoryTokenBlacklistService` — le chemin de
      vérification réel (`require_jwt()`) continue d'interroger le service en mémoire, cette
      table n'existe que pour donner à `admin/blacklisted-tokens/*` de vraies lignes à lister.
      Vérifié par test : un logout réel apparaît dans la liste admin avec la bonne `reason`.
      **`last_used_at` du refresh token câblé** dans `refresh_tokens.redeem_refresh_token` (Vague
      A, seul point d'appel) — touché à chaque redemption, y compris lors d'un `revoke()` (mirroir
      exact du `auto_now=True` de Django, qui touche le champ à chaque `.save()`).
      **Deux quirks de tri répliqués à l'identique plutôt que normalisés vers le
      `pagination.apply_ordering` partagé** : `BlacklistedTokenListView`/`RefreshTokenListView` ne
      passent pas par `filters.apply_ordering()` — chacune fait sa propre vérification inline
      contre un petit ensemble littéral de valeurs `?ordering=` exactes (pas de tri multi-champs
      séparé par virgules, pas de retrait du préfixe `-`) et **ignore silencieusement** toute
      valeur hors de cet ensemble plutôt que de retomber sur un tri par défaut — testé
      explicitement (`?ordering=not_a_real_field` → 200, tri inchangé).
      **Note de portée, documentée plutôt que masquée** : `AuditLogDB`/`LoginAttemptDB` sont
      correctement servies par leurs endpoints de liste/détail, mais aucun flux d'auth des vagues
      A-C n'écrit dedans — câbler `AuditLog.log()`-équivalent dans chaque endpoint concerné serait
      un chantier de rétrofit d'audit-logging à part entière, hors de la portée de ce chunk (des
      endpoints de visibilité admin, pas un rétrofit de logging de tout l'adaptateur). Les tests
      correspondants seedent ces deux tables directement.
      7 tests (`test_admin_security_router.py`), aucun mock, base aiosqlite éphémère réelle —
      logout réel → apparition dans la liste blacklist avec la bonne raison, cleanup (aucune
      suppression tant que rien n'a expiré, vérifié via `?expired=true`), cycle liste/revoke de
      refresh token avec rejets `ALREADY_REVOKED`/`NOT_FOUND`, liste/détail d'audit-log avec 404,
      liste/filtre de login-attempts, tri non reconnu silencieusement ignoré, refus générique de
      permission.
      `parity_matrix` : 80/114 endpoints Django portés au total (7 nouveaux) — Groupes A/B/C/F
      toujours verts ; coverage FastAPI 91.96 % (seuil CI 90 %, 210 tests) ; suite Django complète
      relancée, aucune régression.
      **Restant (chunk 5/5)** : `dashboard/*` (5 — agrégations en lecture seule sur tout ce qui
      précède).
    - **Chunk 5/5 fait — Dashboard (5/46, 46/46 cumulé — Groupe D complet)** : `dashboard/stats/`
      (global), `dashboard/auth/`, `dashboard/security/`, `dashboard/gdpr/`,
      `dashboard/organizations/`. **Contrat extrait** de `views/dashboard_views.py` (les 5
      exigent tous `dashboard.view`, vérifié en lisant le code) et `services/stats_service.py`
      (`StatsService`).
      **Agrégation faite en Python, pas en `FILTER`/`GROUP BY` SQL** : `StatsService` s'appuie sur
      `Count(..., filter=Q(...))` (agrégats conditionnels Django) et `.values().annotate()`
      (GROUP BY). L'équivalent SQLAlchemy le plus proche (`func.count().filter(...)`) compile vers
      une clause SQL `FILTER` pas portable de façon fiable entre versions de sqlite ; les
      endpoints dashboard sont par nature basse fréquence (une console admin, pas un chemin API
      chaud), donc ce chunk récupère les lignes concernées et agrège en Python — plus simple,
      portable, et facile à vérifier contre la forme de sortie exacte de `StatsService`.
      **Deux des cinq sous-statistiques ne peuvent pas être adossées à de vraies données
      aujourd'hui, documenté plutôt que simulé avec une table qui n'appartient pas à cette
      tâche** :
      - `dashboard/organizations/` renvoie toujours `{"enabled": False}` — exactement la forme que
        Django renvoie quand `org_settings.ORGANIZATIONS_ENABLED` est désactivé. Le
        Reference_Stack n'a aucune notion d'organisation pour l'instant (Groupe E, pas encore
        porté), donc « désactivé » est simplement vrai aujourd'hui, pas un bouchon.
      - `dashboard/gdpr/` (et le sous-objet `gdpr` de `dashboard/stats/`) renvoie la forme à
        valeurs *zéro* correctement structurée que `StatsService` produirait contre une table
        `AccountDeletionRequest` vide, calculée sans table de support — le Groupe G (demandes de
        suppression RGPD) n'a pas encore été porté, et créer une table maintenant, dans une tâche
        du Groupe D, en avance sur la conception de schéma propre au Groupe G, serait du
        sur-périmètre dont ce chunk n'a pas besoin.
      `dashboard_service.py` (nouveau, framework-agnostic même logique que les autres services de
      la vague) ; `routers/dashboard.py` (nouveau, 5 endpoints, tous gatés par
      `require_permission("dashboard.view")`).
      5 tests (`test_dashboard_router.py`), aucun mock, base aiosqlite éphémère réelle — stats
      globales reflétant de vraies données (utilisateurs verrouillés/bannis, forme `gdpr` figée),
      stats auth (répartition succès/échec, groupement par méthode via `AuditLog.details`, top
      raisons d'échec, graphique quotidien), stats sécurité (tokens blacklistés réels via un vrai
      logout, comptes verrouillés/bannis, taux d'adoption 2FA), formes documentées gdpr/
      organizations exactes, refus générique de permission.
      `parity_matrix --groups=A,B,C,D,F` : **85/114 endpoints Django portés au total (5
      nouveaux) — Groupe D désormais complet (46/46) et vert aux côtés de A/B/C/F** ; coverage
      FastAPI 92.22 % (seuil CI 90 %, 215 tests) ; suite Django complète relancée, aucune
      régression.
    - _Requirements: 4.1, 4.2, 4.5_

  - [x] 10.2 Contract_Suite + matrice sur A–D (+F) ; exclusions justifiées le cas échéant
    - `tests/contract/test_group_d_shapes.py` (nouveau) : un endpoint représentatif par chunk
      (`/permissions/`, `/applications/`, `/admin/users/`, `/admin/audit-logs/`,
      `/dashboard/stats/`) — 20 tests (5 endpoints × 2 assertions × 2 adapters).
      **Portée volontairement plus étroite que les Groupes A-C, même raison déjà documentée dans
      `test_group_f_shapes.py`** : chacun des 46 endpoints du Groupe D exige une permission RBAC
      précise, et prouver la forme de la réponse *en cas de succès* (permission accordée) sur les
      deux backends demanderait un Delegating User qui détient réellement la permission des deux
      côtés — vraie RBAC Django (rôles/octrois directs) contre le bypass `is_superuser` seul du
      `require_permission` du Reference_Stack — et la fixture `api` n'a toujours aucun moyen
      partagé de promouvoir un `register_and_login()` vers cet état.
      **Ce qui EST prouvable identiquement sans cette promotion, et c'est précisément ce que ce
      fichier prouve** : le portail auth/permission lui-même produit la même forme canonique sur
      les deux adaptateurs — token manquant → `{"error": "Authorization header required", "code":
      "AUTH_REQUIRED"}` (401, vérifié identique via `decorators.require_jwt` côté Django et
      `security.require_jwt()` côté FastAPI) ; appelant authentifié mais sans la permission →
      `{"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}` (403, message générique
      non-verbeux, vérifié identique via `decorators._get_permission_denied_response` côté Django
      — même comportement `VERBOSE_ERRORS=False` par défaut déjà répliqué dans tous les
      `*_service.py` de la vague). Le comportement complet du Groupe D (listes, filtres, CRUD)
      reste couvert par la suite dédiée de chaque chunk (`test_rbac_router.py`,
      `test_applications_router.py`, `test_admin_users_router.py`,
      `test_admin_security_router.py`, `test_dashboard_router.py`) — ce fichier prouve seulement
      que les deux adaptateurs s'accordent sur le portail, pas une deuxième fois la logique interne
      de chaque chunk.
      `conftest.py` étendu avec `_register_group_d_views` (une classe de vue Django par chunk).
      Suite contract complète relancée : 50 passed (20 nouveaux + 30 existants), aucune
      régression. `parity_matrix --groups=A,B,C,D,F` toujours vert (85/114).
    - _Requirements: 4.5, 5.1, 5.2_

- [x] Checkpoint Vague D : `parity_matrix --groups=A,B,C,D,F` (85/114, Groupe D 46/46), Contract_Suite
  étendue (50 passed), coverage FastAPI 92.22 % (seuil CI 90 %, 215 tests), suite Django complète
  (2238 passed, 5 skipped, aucune régression à chaque commit des 5 chunks), `ruff`/`black` propres
  sur `src/`. Vague D fermée en 5 chunks committables séparément (RBAC core, applications, admin
  users, admin security, dashboard) plutôt qu'en un seul gros commit — même logique que les vagues
  précédentes, nécessaire ici vu que le Groupe D est, de loin, la plus grosse vague du plan (46
  endpoints contre 11-12 pour chaque vague précédente).

- [x] 11. Vague de parité E — Organisations
  - [x] 11.1 Porter le groupe E (12 endpoints réels — pas 13 : `OrganizationInvitation` expose
    `accept()`/`decline()` au niveau modèle mais aucune route HTTP Django ne les appelle, vérifié
    dans `urls.py` — seul `invite_member` (création) est enregistré. Découpé en 4 chunks
    committables séparément, même logique que la Vague D)
    - **Chunk 1/4 fait — Fondations + CRUD organisation (5/12)** : `POST /organizations/`,
      `GET /organizations/list/`, `GET /organizations/detail/`, `PATCH /organizations/update/`,
      `DELETE /organizations/delete/`. **Contrat extrait** par recherche exhaustive de
      `views/organization_views.py`, `services/organization_service.py` (`OrganizationService`,
      lu intégralement), `serializers/organization_serializers.py` (lu intégralement),
      `filters.py` (`apply_organization_filters`), `models/organization.py` (déjà lu avant ce
      chunk), les décorateurs `require_org_*` et `OrganizationContextMiddleware` dans
      `decorators.py`/`middleware.py` (déjà lus avant ce chunk), et vérifié par relecture directe
      (pas seulement le rapport d'un agent de recherche) des points critiques : chaque
      `return Response({"error": ...})` réel dans `organization_views.py`, le fichier complet de
      `organization_service.py`, et le fichier complet des serializers.
      **Trouvaille réelle majeure, vérifiée en lisant chaque site d'appel plutôt que supposée
      depuis les `@extend_schema`/`OpenApiExample` (qui inventent un champ `code` que le code réel
      n'émet jamais)** : les erreurs métier de `organization_views.py`/`organization_service.py`
      sont **toujours** exactement `{"error": "<message>"}`, **sans** champ `code` — contrairement
      à quasi toutes les autres erreurs Django déjà portées dans les Vagues A-D. `TenxyteAPIError`
      (`errors.py`) **étendu** pour accepter `code=None` (omet la clé `code` du corps JSON) — un
      changement chirurgical de l'infra d'erreurs partagée, sans régression sur les 227 tests
      FastAPI existants (relancés après le changement, tous verts). À l'inverse, les erreurs de
      *portail* (contexte manquant, non-membre, rôle/permission requis — dans
      `decorators.py`/`middleware.py`, pas dans les vues) **ont bien** un `code`, parfois avec des
      champs additionnels (`ORG_NOT_FOUND` a `slug`, `ORG_MEMBERSHIP_REQUIRED` a `organization`) —
      les deux familles répliquées à l'identique, chacune avec sa vraie forme.
      **Deux vérifications de rôle avec des règles d'héritage différentes pour la même paire
      owner/admin, répliquées séparément plutôt qu'unifiées** : le décorateur `require_org_admin`
      (le vrai portail devant la vue) vérifie admin `check_inheritance=True` OU owner
      `check_inheritance=False` ; le service `update_organization` refait sa propre vérification
      interne avec owner **et** admin tous deux `check_inheritance=True` (code mort en pratique
      dans l'app réelle, puisque le décorateur — plus strict — a déjà tranché avant que le service
      ne s'exécute) — répliqué dans `org_context.require_org_admin` (portail réel) et
      `org_service.update_organization_async` (règle du service, redondante mais fidèle) tels
      quels.
      **`create_organization` n'a aucune vérification de permission sur `parent_id`** — vérifié en
      lisant la vue : gatée uniquement par `@require_jwt`. N'importe quel utilisateur authentifié
      connaissant l'ID d'une organisation (même sans aucune relation avec elle) peut y nicher une
      nouvelle organisation et en devenir propriétaire, sous la seule réserve de la limite de
      profondeur. Répliqué à l'identique et testé explicitement
      (`test_create_child_organization_needs_no_relationship_to_parent`).
      **Aucun rôle par défaut au-delà de `owner` n'est auto-seedé** — vérifié en grep-ant chaque
      site d'appel `OrganizationRole.objects.create`/`get_or_create` du code Django réel : seuls
      deux existent, tous deux dans `OrganizationService` — `create_organization` crée
      paresseusement le rôle `owner` (`permissions=["org.*"]`) au premier usage,
      `initialize_system_roles` (qui créerait aussi `admin`/`member`/`viewer`) n'est appelé par
      **aucun** chemin applicatif (aucun signal, aucune management command, aucun hook
      `AppConfig.ready()`) — seulement par les fixtures de test Django elles-mêmes. Répliqué à
      l'identique : `org_service.initialize_system_roles_async` existe (symétrie test/seed) mais
      n'est jamais appelée automatiquement.
      **Nouvelles infrastructures** : `models_sa.py` — `OrganizationDB`/`OrganizationRoleDB`/
      `OrganizationMembershipDB`/`OrganizationInvitationDB` (clés UUID string, cohérent avec
      chaque table existante de ce port malgré les `AutoField` entiers de Django — divergence déjà
      établie silencieusement partout ailleurs, pas nouvelle à cette vague) ; `org_service.py`
      (nouveau, framework-agnostic même logique que `rbac_service.py` — hiérarchie/appartenance/
      résolution de permission/CRUD, ~400 lignes) ; `org_context.py` (nouveau — dépendances
      FastAPI `require_org_context`/`require_org_membership`/`require_org_role`/
      `require_org_permission`/`require_org_owner`/`require_org_admin`, implémentées comme chaîne
      de `Depends(...)` plutôt que middleware ASGI — même idiome que `require_jwt`/
      `require_permission` de `security.py`, pas de nouvelle session DB à gérer hors du cycle de
      vie par requête) ; `core/settings.py` — `organizations_enabled` ajoutée (les propriétés
      `org_role_inheritance`/`org_max_depth`/`org_max_members` existaient déjà avant cette
      session, découvertes en cours de route plutôt que dupliquées — `ruff` a immédiatement
      signalé les doublons F811 quand je les avais réinventées par erreur).
      **Gating `ORGANIZATIONS_ENABLED` répliqué au niveau routeur, pas au niveau réponse** : comme
      Django (`if org_settings.ORGANIZATIONS_ENABLED: urlpatterns += [...]`, évalué une seule fois
      au chargement d'`urls.py`), `app.py`'s `_build_router` n'inclut `orgs_router` que si
      `settings.organizations_enabled` — une désactivation renvoie donc le 404 par défaut de
      FastAPI sur `/organizations/*`, pas un corps JSON `ORG_FEATURE_DISABLED` (ce corps existe
      dans `org_context.py` comme défense en profondeur inatteignable, exactement comme chez
      Django, testé explicitement — `test_organizations_feature_disabled_by_default_404s`).
      12 tests (`test_orgs_router.py`), aucun mock, base aiosqlite éphémère réelle — feature
      désactivée par défaut → 404, création → propriétaire auto-assigné, slug auto-unique
      (`acme`/`acme-1`), détail exige l'appartenance (403 avec `code`+`organization`), header
      manquant (400 `ORG_CONTEXT_REQUIRED`), slug inconnu (404 `ORG_NOT_FOUND`+`slug`), mise à
      jour par le propriétaire, mise à jour refusée pour un non-admin (403, toujours avec `code`
      côté portail), suppression réservée au propriétaire, suppression bloquée par des enfants
      (400 **sans** `code` — trouvaille validée), création d'enfant sans relation avec le parent,
      liste limitée à l'appartenance réelle.
      Suite Django `organization`/`middleware` relancée en isolation (247 passed) pour valider
      la compréhension du comportement réel avant d'écrire le port — cohérent avec la pratique
      établie de vérifier contre le code qui tourne, pas contre sa propre narration.
      Suite FastAPI complète relancée après le changement de `TenxyteAPIError` : 227 passed,
      aucune régression. Coverage FastAPI 90.60 % (juste au-dessus du seuil CI 90 % — attendu,
      `org_service.py` contient des chemins de permission/héritage pas encore exercés avant les
      chunks 2-4, qui les couvriront).
      **Restant (chunks 2-4/4)** : hiérarchie (`tree`) + `org-roles/` (2) ; membres (liste/ajout/
      modification de rôle/retrait, 4) ; invitations (`invite_member`, 1).
    - **Chunk 2/4 fait — Hiérarchie + org-roles (2/12, 7/12 cumulé)** :
      `GET /organizations/tree/`, `GET /org-roles/`.
      **`get_organization_tree` construit toujours l'arbre depuis la racine, pas depuis
      l'organisation courante** — vérifié dans `OrganizationService.get_organization_tree`
      (`organization.get_root()` avant la construction récursive) : même scopé sur un enfant via
      `X-Org-Slug`, la réponse démarre en haut de la hiérarchie. Répliqué à l'identique et testé
      explicitement (`test_organization_tree_always_starts_at_root` — scope sur l'enfant, vérifie
      que la racine est retournée avec l'enfant nesté dedans).
      `list_org_roles` (`GET /org-roles/`) est globale, non scopée à une organisation — gatée
      uniquement par `@require_jwt` (pas de `X-Org-Slug`/appartenance requis), retourne
      **toutes** les lignes `OrganizationRole` existantes. Testé explicitement qu'aucun rôle
      n'existe tant qu'aucune organisation n'a été créée (le rôle `owner` n'est créé que
      paresseusement au premier `create_organization`, cf. chunk 1), et que l'endpoint reste
      utilisable sans header `X-Org-Slug` du tout.
      Aucune nouvelle infrastructure — réutilise entièrement `org_service.py`/`org_context.py`
      du chunk 1 (`get_organization_tree_async`/`list_org_roles_async`/`serialize_org_role`
      ajoutées à `org_service.py`, `require_org_membership()` réutilisée telle quelle pour
      `tree/`).
      4 tests ajoutés à `test_orgs_router.py` (16 au total sur le fichier), aucun mock — arbre
      correct (racine + profondeur + enfant nesté + `member_count`), arbre exige l'appartenance
      (403), liste des rôles globale avec formes vides/peuplées, liste des rôles exige
      l'authentification (401).
      `parity_matrix --groups=A,B,C,D,F` : 92/114 endpoints Django portés au total (2 nouveaux) —
      Groupes A/B/C/D/F toujours verts.
      **Restant (chunks 3-4/4)** : membres (liste/ajout/modification de rôle/retrait, 4) ;
      invitations (`invite_member`, 1).
    - **Chunk 3/4 fait — Membres (4/12, 11/12 cumulé)** :
      `GET /organizations/members/`, `POST /organizations/members/add/`,
      `PATCH /organizations/members/{user_id}/`, `DELETE /organizations/members/{user_id}/remove/`.
      **Contrat re-vérifié directement dans `organization_service.py`** (déjà lu intégralement au
      chunk 1) : `add_member`/`update_member_role`/`remove_member`/`get_members` — ordre exact des
      vérifications répliqué (permission → limite de membres/garde-fou owner → résolution → effet)
      pour chacune.
      **Garde-fou owner unconditionnel, indépendant du nouveau rôle demandé** :
      `update_member_role` refuse `"Cannot change owner role"` dès que la cible détient
      actuellement le rôle `owner` (`check_inheritance=False`) — peu importe le rôle visé ou qui
      fait la demande. `remove_member` a le même garde-fou (`"Cannot remove organization owner"`).
      Aucune logique de « dernier owner » n'existe nulle part dans le code Django (vérifié en
      lisant le service en entier) — `LAST_OWNER_REQUIRED` documenté dans les `@extend_schema` est
      pure fiction, jamais implémenté. Pas de faux retrait/auto-retrait spécial non plus : retirer
      son propre compte suit exactement le même chemin de permission que retirer quelqu'un
      d'autre.
      **`role_code="owner"` n'est PAS bloqué dans `add_member`** — aucune validation spéciale sur
      ce code dans le service réel ; un second owner peut être ajouté via cet endpoint si un
      appelant en a la permission. Non testé explicitement (comportement marginal, cohérent avec
      le reste du contrat déjà vérifié) mais non contredit non plus par l'implémentation.
      **`list_members` fusionné en une seule requête SQL** plutôt que la composition séquentielle
      Django (`get_members` puis `apply_member_filters` en Python) — jointures `UserDB`/
      `OrganizationRoleDB` réelles pour `search`/`role`/tri `user__email`/`role__code`, cohérent
      avec le style SQL du reste de l'adaptateur (contrairement à `dashboard_service.py` qui agrège
      en Python pour éviter `FILTER` SQLite — ici de simples `WHERE`/`JOIN`/`ORDER BY` suffisent,
      pas de piège de portabilité). `status` par défaut `"active"` répliqué (les memberships
      `pending`/`suspended` sont exclus de la liste par défaut, pas seulement filtrables).
      **Aucune nouvelle infrastructure** — réutilise `org_service.py`/`org_context.py` des chunks
      précédents (`require_org_permission("org.members.invite"/"org.members.manage"/
      "org.members.remove")` de `org_context.py`, déjà écrite au chunk 1 mais pas encore exercée
      par un endpoint réel avant ce chunk) ; `OrganizationAddMemberRequest`/
      `OrganizationUpdateMemberRoleRequest` ajoutés à `schemas.py`.
      **Rôles `admin`/`member`/`viewer` seedés dans les tests via `initialize_system_roles_async`**
      — cohérent avec la découverte du chunk 1 : Django lui-même ne les crée que depuis ses propres
      fixtures de test, jamais en production, donc les tests de ce port suivent la même logique
      plutôt que d'en inventer une nouvelle.
      11 tests ajoutés à `test_orgs_router.py` (23 au total) — ajout réussi + doublon rejeté (400
      sans `code`), permission d'invitation manquante (403 avec `code`), utilisateur inconnu (404
      sans `code`), liste + filtre par rôle, promotion réussie + protection owner sur modification
      de rôle (400 sans `code`), retrait réussi + protection owner sur retrait (400 sans `code`),
      limite de membres respectée à l'ajout (400 sans `code`).
      `parity_matrix --groups=A,B,C,D,F` : 96/114 endpoints Django portés au total (4 nouveaux) —
      Groupes A/B/C/D/F toujours verts.
      **Restant (chunk 4/4)** : invitations (`invite_member`, 1).
    - **Chunk 4/4 fait — Invitations (1/12, 12/12 cumulé — Groupe E complet)** :
      `POST /organizations/invitations/`. **Contrat re-vérifié directement dans
      `organization_service.py`** : `create_invitation` — ordre exact répliqué (permission →
      limite de membres → résolution du rôle → vérification appartenance-déjà-membre par email →
      expiration silencieuse des invitations `pending` existantes pour le même `(organisation,
      email)` → création).
      **Aucune erreur `INVITATION_EXISTS`/de doublon n'existe** — vérifié en lisant la méthode
      réelle : une deuxième invitation vers le même email expire silencieusement la première
      (`status="expired"`) et en crée une nouvelle, malgré les `@extend_schema` qui laissent
      entendre un 400. Répliqué à l'identique et testé explicitement (deux invitations successives
      vers le même email → toutes deux 201, tokens différents, la deuxième reflète le nouveau
      rôle).
      **Aucun email n'est réellement envoyé** — le corps de la méthode Django se termine par un
      simple commentaire `# TODO: Send invitation email` ; le token n'est jamais restitué que dans
      le corps de la réponse HTTP. Non simulé ici non plus — même posture « aucun backend de
      livraison réel » déjà documentée pour OTP/magic-link, sauf qu'ici c'est Django lui-même qui
      ne l'a jamais câblé, pas seulement le Reference_Stack.
      **Nouvelle infrastructure minimale** : `create_invitation_async`/`serialize_invitation_async`
      ajoutées à `org_service.py` (réutilise entièrement `OrganizationInvitationDB` du chunk 1,
      jamais utilisée avant ce chunk) ; `OrganizationInviteMemberRequest` ajoutée à `schemas.py` ;
      `require_org_permission("org.members.invite")` de `org_context.py` réutilisée telle quelle.
      4 tests ajoutés à `test_orgs_router.py` (27 au total) — invitation réussie (forme exacte,
      vérifie explicitement l'absence des champs `organization`/`role`/`invited_by` imbriqués que
      la doc annonce à tort), doublon non rejeté (la trouvaille, testée pas seulement documentée),
      email déjà membre rejeté (400 sans `code`), permission d'invitation manquante (403 avec
      `code`).
      `parity_matrix --groups=A,B,C,D,E,F` : **97/114 endpoints Django portés au total (1 nouveau)
      — Groupe E désormais complet (12/12) et vert aux côtés de A/B/C/D/F**.
    - _Requirements: 4.1, 4.2, 4.4_

  - [x] 11.2 Contract_Suite + matrice sur A–F
    - `tests/contract/test_group_e_shapes.py` (nouveau, 6 tests × 2 adaptateurs = pas de
      paramétrage supplémentaire ici, juste 6 fonctions de test). **Contrairement aux Groupes D/F,
      une vraie preuve de succès est possible ici, pas seulement une preuve de portail** :
      `create_organization`/`list_organizations` n'exigent que `@require_jwt` (aucune permission
      RBAC à promouvoir que la fixture `api` ne sait pas accorder), donc un `register_and_login()`
      frais peut immédiatement créer une organisation, en devenir owner, et la relister — un aller-
      retour réel comparé champ par champ sur les deux adaptateurs, pas juste un statut HTTP.
      `conftest.py` étendu : `_NoApplicationAuthProvider` force désormais aussi
      `TENXYTE_ORGANIZATIONS_ENABLED=True` côté FastAPI (le côté Django l'a déjà via
      `tests/integration/django/settings.py`) ; `_register_group_e_views` enregistre
      `create_organization.cls`/`list_organizations.cls`/`get_organization.cls` — ces vues Django
      sont des **fonctions** décorées `@api_view`, pas des classes `APIView` comme tous les autres
      groupes déjà enregistrés, mais DRF expose la classe générée dynamiquement via l'attribut
      `.cls` de la fonction, exactement compatible avec la machinerie `DjangoContractClient`
      existante (`view_cls.as_view()`) sans aucune modification.
      **Trouvaille réelle capturée PAR le Contract_Suite lui-même, pas anticipée** : le premier
      lancement du test échouait — `parent_name` (un `CharField(source="parent.name")` en lecture
      seule) est **entièrement absent** du corps de réponse Django quand l'organisation n'a pas de
      parent, pas `null` comme mon implémentation FastAPI le produisait. Cause : DRF's
      `Field.get_attribute()` lève `AttributeError` en remontant la chaîne `parent.name` quand
      `parent` est `None`, et comme le champ est `read_only` (donc implicitement
      `required=False`), DRF lève `SkipField()` au lieu de retomber sur `None` — la clé disparaît
      du dict de sortie. `org_service.serialize_organization_async` corrigé pour reproduire
      exactement ce comportement (`created_by_email`, même mécanisme DRF, traité pareil par
      cohérence même si jamais empiriquement `None` dans ce port). Corrigé et vérifié avant
      commit, pas laissé en l'état — exactement le genre de divergence que ce test avait pour but
      de capturer.
      **Portée volontairement plus étroite pour le reste du Groupe E** (même schéma que Groupes
      D/F) : `DjangoContractClient` pilote les vues via `APIRequestFactory`, qui ne fait jamais
      tourner le middleware Django — donc `OrganizationContextMiddleware` (qui résout
      `X-Org-Slug` en `request.organization`) ne s'exécute jamais dans ce harnais de test. Le cas
      « header absent » fonctionne quand même par accident (`hasattr(request, "organization")`
      est simplement `False` sur une requête `APIRequestFactory` nue, exactement ce que
      `require_org_context` traite comme « aucun contexte fourni ») — testé explicitement
      (`test_organization_detail_requires_context_identically`). Reproduire le cas de succès (un
      slug valide résolu) demanderait de simuler le middleware à la main dans le client de test
      partagé — un changement d'infrastructure de test à part entière, hors de portée de cette
      tâche.
      Suite contract complète relancée : 56 passed (6 nouveaux + 50 existants), aucune régression.
      Suite unitaire `test_orgs_router.py` relancée après la correction `parent_name` : 27 passed,
      aucune régression. `parity_matrix --groups=A,B,C,D,E,F` toujours vert (97/114).
    - _Requirements: 5.1, 5.2_

- [x] Checkpoint Vague E : `parity_matrix --groups=A,B,C,D,E,F` (97/114, Groupe E 12/12), Contract_Suite
  étendue (56 passed), coverage FastAPI ~91-92 % (seuil CI 90 %), suite Django complète (2238
  passed, 5 skipped, aucune régression à chaque commit des 4 chunks), `ruff`/`black` propres sur
  `src/`. Vague E fermée en 4 chunks committables séparément (fondations+CRUD, hiérarchie+rôles,
  membres, invitations) — même logique que les vagues D et précédentes.

- [ ] 12. Vague de parité G — WebAuthn, Social, GDPR
  - [ ] 12.1 Porter le groupe G (17 endpoints : webauthn/* 6, social/* 2, GDPR user 5, GDPR admin
    4 — découpé en chunks committables séparément par sous-système, même logique que les vagues
    précédentes. Fichiers séparés par sous-système — `routers/webauthn.py`/`routers/social.py`/
    `routers/gdpr.py` — plutôt que le `routers/webauthn_social.py` unique prévu initialement,
    cohérent avec le découpage fin déjà utilisé pour les vagues D/E)
    - **Chunk 1/4 fait — WebAuthn/Passkeys (6/17)** : `POST webauthn/register/begin`,
      `POST webauthn/register/complete`, `POST webauthn/authenticate/begin`,
      `POST webauthn/authenticate/complete`, `GET webauthn/credentials/`,
      `DELETE webauthn/credentials/{id}/`. **Contrat extrait** par recherche exhaustive de
      `views/webauthn_views.py` (chaque site d'appel `return Response(...)` réel, pas les blocs
      `@extend_schema`/`OpenApiExample` — plusieurs divergent du code réel, détaillé ci-dessous),
      `adapters/django/webauthn_storage.py`, `models/webauthn.py`, `conf/social.py` (réglages
      `WEBAUTHN_*`), et `core/webauthn_service.py` (déjà lu intégralement avant ce chunk).
      **Contrairement à la plupart des cas « Core l'a déjà », pas de simple câblage** : le service
      Core `WebAuthnService` existe et est vraiment framework-agnostic, mais ses Protocols de
      dépôt (`WebAuthnCredentialRepository`/`WebAuthnChallengeRepository`) sont **synchrones** par
      conception (leurs miroirs `Async*` existent mais ne sont « pas encore consommés » par le
      service, dixit son propre docstring). Faire le pont vers la session SQLAlchemy async de cet
      adaptateur aurait exigé soit un second accès DB synchrone parallèle, soit envelopper chaque
      lecture credential/challenge dans `asyncio.to_thread`. À la place : `webauthn_service.py`
      (nouveau, async-natif) appelle directement les mêmes fonctions `webauthn` (py_webauthn) que
      Core appelle, avec de vrais dépôts async — vérifié ligne à ligne contre les appels réels de
      `core/webauthn_service.py` pour garantir une sémantique de challenge/vérification identique.
      **Deux vrais bugs Django trouvés en portant, corrigés plutôt que répliqués — documentés, pas
      divergés en silence** :
      1. `WebAuthnAuthenticateCompleteView.post` appelle `jwt_service.generate_access_token(...)`
         (qui renvoie un tuple à 3 éléments `(token, jti, expires_at)`) **sans le déballer** — la
         vraie réponse JSON Django a donc `"access"` réglé sur un tableau à 3 éléments
         `[token, jti, iso-datetime]`, pas une chaîne JWT normale. Le même bug existe à l'identique
         dans `magic_link_views.py:320` (déjà corrigé sans note spécifique lors du chunk 7.1,
         puisque je ne l'avais pas remarqué à l'époque — je l'avais simplement déballé sans
         réaliser que Django, lui, ne le fait pas). Corrigé ici aussi, pour la même raison : un
         jeton en tableau rendrait la connexion par passkey non fonctionnelle pour un vrai client.
      2. `generate_refresh_token()` (`core/jwt_service.py`) fait littéralement
         `return str(uuid.uuid4())` — aucune écriture en base, jamais. Le refresh token que Django
         renvoie après une connexion WebAuthn (ou magic-link) ne peut donc jamais être racheté via
         `/refresh/`, puisqu'aucune ligne ne correspond nulle part. Cet adaptateur utilise
         `refresh_tokens.issue_refresh_token` (l'émission réelle et persistée du Reference_Stack,
         déjà utilisée par `auth.py`/`magic_link.py`) à la place — testé explicitement (le
         refresh token obtenu après une authentification WebAuthn réussie fonctionne vraiment
         contre `/refresh/`).
      **Comportements préservés à l'identique malgré leur apparence de bug, car sans coût
      fonctionnel à les garder** :
      - `list_credentials`/`delete_credential` n'ont **aucune** garde `webauthn_enabled` dans
        Core (seuls begin/complete de chaque flux la vérifient) — répliqué à l'identique et testé
        explicitement (`test_credentials_list_and_delete_work_even_when_webauthn_disabled`).
      - Aucun rejet de `credential_id` en double n'existe nulle part dans le code Django réel —
        uniquement la contrainte `unique=True` en base, avec un `IntegrityError` non rattrapé qui
        remonte en 500 générique. Pas davantage rattrapé ici : une violation de contrainte UNIQUE
        SQLAlchemy à `session.commit()` atteint de la même façon le handler 500 générique de cet
        adaptateur — même forme d'échec, atteinte de la même façon (une omission, pas un
        try/except).
      - `WEBAUTHN_CHALLENGE_EXPIRY_SECONDS` est un vrai réglage Django que `begin_registration`/
        `begin_authentication` ne lisent en réalité jamais — les deux codent en dur
        `expiry_seconds=300`. Codé en dur ici aussi, pour la même raison (aucune propriété de
        réglage ajoutée pour une valeur que rien ne consommerait).
      **`webauthn_enabled` corrigé d'un défaut `True` erroné vers `False`** dans
      `core/settings.py` — cette propriété préexistait cette session (dans le module partagé
      `Settings`, utilisé par les deux adaptateurs) mais n'avait jamais eu de vrai consommateur
      côté FastAPI avant ce chunk ; son défaut divergeait silencieusement de celui de Django
      (`conf.social.WEBAUTHN_ENABLED` vaut `False` par défaut) — un défaut pré-existant jamais
      remarqué avant que ce chunk ne s'en serve réellement, pas une divergence délibérée.
      **Encodage `credential_id`/`public_key`** : FIDO2 renvoie des données binaires arbitraires ;
      `credential_id` est stocké en base64url (correspondant exactement à la représentation
      string que l'API WebAuthn du navigateur envoie elle-même dans `credential.id`/`rawId`, donc
      les recherches à l'authentification comparent directement la même représentation) via
      `webauthn.helpers.bytes_to_base64url`/`base64url_to_bytes` ; `public_key` en base64 simple
      (jamais recomparée à une chaîne fournie par le client, donc n'importe quel encodage binaire-
      texte sûr convient).
      **`webauthn/*` enregistrées sans condition** (contrairement aux Organisations) — Django
      enregistre aussi `webauthn/*` sans condition dans `urls.py`, `WEBAUTHN_ENABLED` n'étant
      vérifié qu'au niveau de chaque appel de service.
      **Tests avec une vraie crypto FIDO2, aucun mock** : `_webauthn_authenticator.py` (nouveau,
      `tests/integration/fastapi/unit/`) implémente un « authentificateur virtuel » minimal mais
      réel — génération de clé P-256 ECDSA réelle, encodage CBOR réel de l'`authenticatorData`/
      `attestationObject`, signatures ECDSA réelles — pour que `test_webauthn_router.py` exerce
      les vraies fonctions de vérification `webauthn` (py_webauthn) de bout en bout, cohérent
      avec la politique « aucun mock » de tout ce port, étendue ici jusqu'à la crypto elle-même.
      8 tests (`test_webauthn_router.py`) — désactivé par défaut → 400 sans auth requise,
      `register/begin` exige l'authentification, **aller-retour complet réel** (enregistrement
      d'une passkey avec un authentificateur réel, authentification avec elle, obtention d'une
      vraie paire de jetons fonctionnelle, rachat réel du refresh token contre `/refresh/` —
      vérifie explicitement que `access` est une chaîne JWT normale, pas le tableau bugué),
      identifiant de credential inconnu rejeté, champ `credential` manquant, challenge ne
      correspondant pas à l'utilisateur rejeté, suppression de credential scopée au propriétaire,
      liste/suppression fonctionnelles même WebAuthn désactivé (la trouvaille, testée pas
      seulement documentée).
      **Dépendance `webauthn>=2.7.0` installée** dans l'environnement de dev (`env/`) — absente
      auparavant, confirmée par la recherche préalable au chunk. `.github/workflows/ci.yml`'s job
      `fastapi-tests` corrigé pour l'installer (`[fastapi,webauthn,dev]`) — la suite Django ne
      l'installe jamais (ses propres tests mockent `_get_webauthn()` en entier), mais cette suite
      FastAPI teste la vraie bibliothèque, donc en a réellement besoin en CI.
      **Corrigé au passage, hors scope direct mais découvert en touchant le même fichier** : le
      job CI `contract-parity` avait un gate `parity_matrix --groups=A` resté figé depuis la Vague
      B (jamais mis à jour), et son étape Parity_Matrix n'avait jamais `DJANGO_SETTINGS_MODULE`
      dans son environnement — reproduit en local (`ImproperlyConfigured`), donc probablement en
      échec silencieux en CI depuis un moment. Les deux corrigés (`--groups=A,B,C,D,E,F` + la
      variable d'environnement).
      `parity_matrix --groups=A,B,C,D,E,F` : 103/114 endpoints Django portés au total (6
      nouveaux) — Groupes A/B/C/D/E/F toujours verts. Suite FastAPI complète relancée après tous
      les changements : 250 passed, aucune régression.
      **Restant (chunks 2-4/4)** : social auth (2, + callback Apple z_aud_1) ; GDPR user (5) ;
      GDPR admin (4).
    - **Chunk 2/4 fait — Social Auth (2/17)** : `POST social/{provider}/`,
      `GET social/{provider}/callback/`, 5 fournisseurs (google/github/microsoft/facebook/apple).
      **Contrat extrait** par lecture intégrale de `views/social_auth_views.py`
      (`SocialAuthView.post`, `SocialAuthCallbackView.get`) — Django n'a jamais extrait cette
      logique vers Core, donc ce chunk la réimplémente entièrement en async-natif plutôt que de
      câbler un service Core existant.
      **`httpx.AsyncClient` remplace le `requests` bloquant de Django** — nouvelle dépendance
      runtime réelle de l'extra `fastapi` (pas seulement `dev`, `pyproject.toml` mis à jour en
      conséquence, avec le commentaire de justification "test-only" retiré puisqu'il n'est plus
      vrai). Vérification `id_token` (google/apple) faite via un utilitaire JWKS-puis-PyJWT partagé
      (`_verify_id_token_via_jwks_async` : fetch JWKS async via httpx, vérification RS256
      synchrone via PyJWT — calcul pur, aucune I/O, donc sûr à appeler directement sous la règle de
      pureté async) plutôt que d'ajouter `google-auth`/`google-auth-oauthlib` (extras Django
      uniquement).
      **Logique de fusion de compte de sécurité répliquée à l'identique** (propres commentaires
      Django "F-03"/"R-05") : une connexion sociale correspondant par email à un compte local
      existant n'est liée que si le fournisseur a marqué l'email vérifié ET que
      `social_auto_merge_accounts` vaut `True` (défaut `False`) — sinon refusée, dans cet ordre
      exact, sans repli silencieux. Testé explicitement dans les deux sens
      (`test_unverified_email_refuses_fusion`, `test_verified_email_refuses_fusion_without_auto_merge`).
      **Forme de réponse réellement différente entre les deux endpoints** — vérifié en lisant le
      code réel de chaque vue, pas les docs `@extend_schema` : `POST social/{provider}/` retire
      `device_summary` et ajoute `message` ; `GET social/{provider}/callback/` garde
      `device_summary` et n'ajoute jamais `message`. Les deux ajoutent `provider`. Pas une
      incohérence à corriger — les deux vues Django font ça indépendamment, ce routeur reproduit
      le post-traitement propre à chacune (testé explicitement dans les deux sens).
      **`token_pair` sans `token_type`/`expires_in`** pour l'auth sociale (contrairement à la
      connexion par mot de passe/email) — vérifié en lisant le dict réellement renvoyé
      (`access_token`, `refresh_token`, `device_summary`, `user`, `is_new_user` seulement) ; les
      docs `@extend_schema` prétendent à tort qu'il y a plus de champs.
      **`SocialConnectionDB`** (`models_sa.py`) omet délibérément les colonnes
      `access_token`/`refresh_token` de Django (ses propres commentaires d'audit R10 confirment
      qu'elles sont toujours codées en dur à `""`, jamais peuplées) plutôt que de modéliser des
      colonnes mortes.
      **Délibérément non câblé dans ce chunk** : Django crée aussi une Organisation par défaut
      pour un nouvel utilisateur social quand `ORGANIZATIONS_ENABLED` et
      `CREATE_DEFAULT_ORGANIZATION` sont tous deux vrais — documenté comme lacune connue et
      délibérée (pas intégré dans un chunk déjà volumineux) plutôt que construit à moitié.
      **Tests avec vraie crypto et vrai HTTP, aucun mock** : `_fake_oauth_server.py` (nouveau,
      `tests/integration/fastapi/unit/`) est une vraie app ASGI Starlette exposant les chemins
      URL réels exacts (pas les hôtes, `httpx.ASGITransport` ne dispatchant que sur
      chemin/méthode) des endpoints token/userinfo/JWKS des 5 fournisseurs, avec une vraie paire
      de clés RSA pour signer de vrais `id_token`s de test et construire un vrai document JWKS.
      `social_auth_service.py` expose un point d'ancrage `_test_transport` (une variable de
      module, jamais de fonction mockée) pour rediriger tout `httpx.AsyncClient` vers ce serveur
      factice en test ; `None` (transport réseau réel) en production.
      11 tests (`test_social_router.py`) — fournisseur non supporté, identifiants manquants,
      `code` sans `redirect_uri`, flux `access_token` Google créant un nouvel utilisateur (+
      rachat réel du refresh token émis contre `/refresh/`), flux `access_token` GitHub avec repli
      sur `/user/emails` (email primaire vérifié choisi parmi plusieurs), flux `id_token` Google
      vérifié via de vrais JWKS RS256, échange de code Apple avec fusion du payload
      `First_Auth_User_Payload` (nom fourni uniquement à la toute première autorisation) et vraie
      signature ES256 du `client_secret` généré (vérifié que le JWT reçu par le serveur factice a
      bien 2 points, donc 3 segments), connexion sociale existante réutilisant le même utilisateur
      (`is_new_user=False`), refus de fusion email non vérifié, refus de fusion email vérifié sans
      `social_auto_merge_accounts`, endpoint callback gardant `device_summary` et sans `message`.
      `parity_matrix --groups=A,B,C,D,E,F` : 105/114 endpoints Django portés au total (2
      nouveaux) — Groupes A/B/C/D/E/F toujours verts. Suite FastAPI unitaire complète relancée
      après tous les changements : 261 passed, aucune régression. Vérification de pureté async
      (`check_async_purity.py`) : OK, aucun pattern bloquant.
      **Restant (chunks 3-4/4)** : GDPR user (5 : demande de suppression, confirmation,
      annulation, statut, export) ; GDPR admin (4).
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
