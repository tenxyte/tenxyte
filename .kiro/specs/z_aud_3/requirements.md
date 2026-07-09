# Requirements Document

## Introduction

Cette spécification couvre la **Phase 3 « Multi-framework réel »** de la feuille de route issue de
`AUDIT.md` : rendre vérifiable la promesse framework-agnostic. L'état mesuré du code montre un
adapter FastAPI embryonnaire (2 endpoints sur 93, stubs DI non implémentés, logique métier inline)
alors que le Core possède déjà un pattern async dual éprouvé (`jwt_service`). La phase généralise
ce pattern (ports et services async), construit un socle FastAPI de production, livre la parité
d'endpoints en sept groupes, la **prouve** par une matrice automatique et une suite de contrat
partagée entre adapters, et comble l'écart frontend par des composants UI headless puis stylés
dans le SDK JS.

Sept chantiers :

1. **Ports async** — interfaces async additives des repositories et storages, pont sync→async
   générique.
2. **Complétion async du Core** — variantes `*_async` des services de chemin de requête, API sync
   intouchée.
3. **Socle FastAPI de production** — app factory, stack de référence SQLAlchemy 2.0 async +
   Alembic, middleware d'authentification d'application, settings par env, erreurs au format
   canonique, throttling.
4. **Parité d'endpoints** — groupes A (Auth), B (Password), C (OTP/passwordless/2FA), F (AIRS),
   D (RBAC/admin), E (Organisations), G (WebAuthn/Social/GDPR).
5. **Preuve de parité** — matrice automatique avec exclusions justifiées, suite de contrat
   partagée, couverture ≥ 90 % sur l'adapter, check anti-blocage d'event loop.
6. **Composants UI JS** — `@tenxyte/ui-headless` puis `@tenxyte/ui` (monorepo JS), avec contrat
   croisé fourni par ce repo (export OpenAPI + backend démo).
7. **Documentation** — quickstart FastAPI zéro-config, tableau de parité publié, guide async.

Tout est additif côté Django et côté API sync du Core.

## Glossary

- **Django_Adapter** : l'adapter Django existant (`tenxyte.adapters.django`, `tenxyte.views`,
  `tenxyte.urls`…) — 93 routes, contrat filaire de référence.
- **FastAPI_Adapter** : l'adapter FastAPI (`tenxyte.adapters.fastapi`) porté à parité par cette
  phase.
- **Wire_Contract** : le contrat filaire public de référence — chemins, formes de
  requêtes/réponses, codes HTTP, codes d'erreur (`{error, code, details}`), comportements
  anti-énumération, feature-flags (`FEATURE_DISABLED`), scopes de jeton (`2fa_setup_only`,
  `password_change_only`) — tels que documentés dans `endpoints.md` et implémentés par le
  Django_Adapter (qui tranche en cas d'ambiguïté).
- **Parity_Groups** : les sept groupes d'endpoints A (Auth de base), B (Password),
  C (OTP/Magic Link/Login OTP/2FA), D (RBAC/Applications/Admin/Dashboard), E (Organisations),
  F (AIRS + découverte), G (WebAuthn/Social/GDPR), livrés dans l'ordre A→B→C→F→D→E→G.
- **Parity_Matrix** : l'outil automatique (`scripts/parity_matrix.py`) diffant les routes du
  Django_Adapter et du FastAPI_Adapter, avec sa liste d'exclusions justifiées
  (`parity_exclusions.toml`) et sa sortie markdown publiable.
- **Contract_Suite** : la suite de tests HTTP partagée (`tests/contract/`) paramétrée par une
  fixture d'adapter, exécutée à l'identique contre le Django_Adapter et le FastAPI_Adapter.
- **Async_Ports** : les nouvelles interfaces async additives (`AsyncUserRepository` et ports de
  storage async) dont chaque méthode a la sémantique exacte de son homologue sync.
- **Sync_Bridge** : l'adaptateur générique enveloppant une implémentation sync en implémentation
  async via `asyncio.to_thread`, sur le modèle du pont existant de `jwt_service`.
- **JWT_Async_Pattern** : le pattern dual déjà en production dans `core/jwt_service.py`
  (protocole async optionnel, détection `hasattr(x, "*_async")`, repli `asyncio.to_thread`) —
  gabarit normatif de tout le chantier async.
- **Reference_Stack** : l'implémentation par défaut du FastAPI_Adapter — SQLAlchemy 2.0 async
  (aiosqlite en dev, asyncpg en prod), migrations Alembic, DI surchargeable.
- **App_Factory** : `create_tenxyte_app(settings)` (application complète) et
  `create_tenxyte_router(settings)` (router montable) remplaçant les stubs actuels.
- **Async_Purity_Check** : le contrôle AST automatisé (`scripts/check_async_purity.py`)
  interdisant tout appel bloquant (repo sync direct, `requests.*`, `time.sleep`…) dans les
  handlers `async def` du FastAPI_Adapter.
- **Coverage_Gate** : le seuil de couverture ≥ 90 % appliqué en CI spécifiquement au sous-arbre
  `src/tenxyte/adapters/fastapi/`.
- **Headless_Package** : le package npm `@tenxyte/ui-headless` (monorepo JS) — hooks et
  composants React sans style avec ARIA complet.
- **Styled_Package** : le package npm `@tenxyte/ui` — couche stylée thémable (tokens CSS,
  clair/sombre) construite sur le Headless_Package.
- **UI_Component_Set** : les sept composants du périmètre — `SignIn`, `SignUp`, `OTPInput`,
  `TwoFactorSetup`, `PasskeyButton`, `ForcedPasswordChange`, `OrgSwitcher`.
- **Contract_Fixtures** : les livrables de ce repo consommés par la CI JS — export OpenAPI
  versionné des deux adapters (`openapi/`) et backend démo docker
  (`examples/js-contract-backend/`).
- **Core** : la couche framework-agnostic existante (`tenxyte.core` / `tenxyte.ports`).
- **Existing_Public_Contract** : l'ensemble des endpoints, formats, réglages, migrations et
  comportements existants avant cette phase — incluant toutes les signatures sync du Core.

## Requirements

### Requirement 1: Ports async additifs

**User Story:** En tant qu'auteur d'adapter async, je veux des interfaces de repository async
officielles avec un pont sync automatique, afin d'implémenter un adapter non bloquant sans
réinventer la sémantique des ports.

#### Acceptance Criteria

1. THE System SHALL provide Async_Ports covering every method of the existing sync
   `UserRepository` and of the request-path storage ports (TOTP storage, magic link storage,
   WebAuthn storage, cache), each async method having the exact semantics of its sync
   counterpart.
2. THE Async_Ports SHALL be additive: no existing sync port interface, method signature, or
   semantic is modified or removed.
3. THE System SHALL provide a generic Sync_Bridge that wraps any sync port implementation into
   its async interface via `asyncio.to_thread`, following the JWT_Async_Pattern.
4. WHEN a consumer holds an implementation, THE resolution rule SHALL follow the
   JWT_Async_Pattern: use the native async method when present, otherwise fall back to the
   Sync_Bridge — never call a sync method directly from an async context.
5. THE System SHALL document the Async_Ports and the resolution rule in `docs/en/async_guide.md`
   and `docs/fr/async_guide.md`, citing `jwt_service` as the reference implementation.

### Requirement 2: Complétion async du Core

**User Story:** En tant que développeur FastAPI, je veux des variantes async des services Core
utilisés pendant une requête, afin qu'aucun appel de service ne bloque l'event loop.

#### Acceptance Criteria

1. THE System SHALL provide `*_async` variants for the request-path methods of
   `magic_link_service` and `session_service`, delegating storage access through the Async_Ports
   resolution rule.
2. THE System SHALL provide `*_async` variants for the storage-accessing methods of
   `totp_service`, keeping the CPU-bound cryptographic operations synchronous.
3. THE async variants SHALL share the business logic with their sync counterparts (extracted pure
   functions), so that no security-relevant logic is duplicated.
4. THE existing sync methods of every Core service SHALL remain unchanged in signature and
   behavior.
5. `core/jwt_service.py` SHALL NOT require changes (already dual) and SHALL be referenced as the
   normative template.

### Requirement 3: Socle FastAPI de production

**User Story:** En tant qu'intégrateur FastAPI, je veux une app factory zéro-config avec un stack
de référence complet, afin d'obtenir un backend d'auth fonctionnel sans implémenter moi-même les
dépendances.

#### Acceptance Criteria

1. THE System SHALL provide the App_Factory: `create_tenxyte_app(settings)` returning a runnable
   FastAPI application and `create_tenxyte_router(settings)` returning a mountable router, both
   wired to the Reference_Stack by default.
2. THE Reference_Stack SHALL implement the Async_Ports with SQLAlchemy 2.0 async (aiosqlite for
   development, asyncpg documented for production) and SHALL ship Alembic migrations for its
   schema.
3. THE existing DI functions SHALL default to the Reference_Stack while remaining overridable;
   no DI function SHALL raise `NotImplementedError` in the default configuration.
4. THE FastAPI_Adapter SHALL enforce application authentication (`X-Access-Key` /
   `X-Access-Secret`) with the same behavior as the Django_Adapter (including the
   `APP_AUTH_REQUIRED` 401 and the `TENXYTE_APPLICATION_AUTH_ENABLED` toggle).
5. THE FastAPI_Adapter SHALL resolve `TENXYTE_*` settings from environment variables (and
   optional programmatic overrides) with the same names and defaults as the Django provider.
6. THE FastAPI_Adapter SHALL return every error in the canonical `{error, code, details}` shape
   via a global exception handler, and SHALL apply request throttling equivalent to the
   Django_Adapter throttle classes on the same endpoint families.
7. THE existing inline business logic in `routers.py` (bcrypt check, hardcoded application id,
   hardcoded IP) SHALL be removed in favor of Core services, with client IP and device info
   extracted from the request.

### Requirement 4: Parité d'endpoints

**User Story:** En tant que client de l'API (frontend, SDK, agent), je veux le même contrat
filaire sur FastAPI que sur Django, afin de changer de backend sans changer une ligne de code
client.

#### Acceptance Criteria

1. THE FastAPI_Adapter SHALL implement every documented endpoint of the Parity_Groups, delivered
   in the order A → B → C → F → D → E → G.
2. FOR every implemented endpoint, THE FastAPI_Adapter SHALL reproduce the Wire_Contract: path
   under the configured prefix, request and response shapes, HTTP status codes, and error codes.
3. THE FastAPI_Adapter SHALL reproduce the anti-enumeration behaviors of the Wire_Contract
   (register, password reset, OTP login request/verify) with identical response shapes for
   existing and non-existing accounts.
4. THE FastAPI_Adapter SHALL reproduce the feature-flag behaviors (`FEATURE_DISABLED` 404 for
   disabled features) and the restricted token scopes (`2fa_setup_only`, `password_change_only`)
   with identical semantics.
5. WHERE a Django endpoint cannot or must not be ported (framework-specific), THE endpoint SHALL
   appear in the Parity_Matrix exclusion list with a written justification — silent omissions are
   not permitted.
6. THE AIRS group (F) SHALL include the discovery endpoint defined by `z_aud_2`, and its
   `conformance` output SHALL reflect the FastAPI runtime configuration.

### Requirement 5: Preuve de parité et qualité

**User Story:** En tant que mainteneur, je veux que la parité soit un invariant de CI, afin
qu'elle ne régresse pas silencieusement quand l'un des deux adapters évolue.

#### Acceptance Criteria

1. THE System SHALL provide the Parity_Matrix tool diffing Django routes against FastAPI routes,
   failing CI when a documented endpoint is missing and not present in the justified exclusion
   list, and emitting a publishable markdown table.
2. THE System SHALL provide the Contract_Suite, parameterized by adapter, reusing the existing
   response-shape snapshots and canonical-spec tests, and CI SHALL run it against both adapters
   with identical expectations.
3. THE Coverage_Gate (≥ 90 % on `src/tenxyte/adapters/fastapi/`) SHALL be enforced in CI.
4. THE Async_Purity_Check SHALL be enforced in CI: any blocking call pattern inside an
   `async def` handler of the FastAPI_Adapter SHALL fail the build.
5. WHEN the Conformance_Suite of `z_aud_2` (`spec/airs/conformance/`) is executed against the
   FastAPI_Adapter with all levels enabled, THE suite SHALL pass — proving that AIRS conformance
   is adapter-independent.

### Requirement 6: Composants UI headless puis stylés (SDK JS)

**User Story:** En tant que développeur frontend, je veux des composants d'authentification prêts
à l'emploi — d'abord sans style pour mon design system, puis stylés pour aller vite — afin de ne
plus reconstruire les écrans d'auth à chaque projet.

#### Acceptance Criteria

1. THE Headless_Package SHALL provide the UI_Component_Set as unstyled React components and hooks
   built on the existing `@tenxyte/core` SDK, emitting zero CSS.
2. EVERY component of the UI_Component_Set SHALL handle the full state machine of its flow as
   defined by the Wire_Contract: loading, field-level validation errors, error codes
   (`2FA_REQUIRED`, `ACCOUNT_LOCKED`, `OTP_INVALID`, `must_change_password: true`…), and success.
3. THE Headless_Package SHALL meet accessibility requirements: complete ARIA roles/attributes,
   keyboard navigation, and axe-core automated checks passing on every component.
4. THE Styled_Package SHALL build exclusively on the Headless_Package, providing a default theme
   through CSS custom properties with light and dark modes, without duplicating flow logic.
5. THE two packages SHALL be tested in the JS monorepo CI against the Contract_Fixtures backend
   (E2E), so that a Wire_Contract change breaks the JS build visibly.
6. THE repo SHALL provide the Contract_Fixtures: a versioned OpenAPI export of both adapters
   (with a CI check that both exports describe the same contract for shared endpoints) and a
   dockerized demo backend for JS E2E tests.

### Requirement 7: Documentation

**User Story:** En tant que nouvel utilisateur FastAPI, je veux un quickstart zéro-config
équivalent à celui de Django, afin d'obtenir un premier appel API en moins de cinq minutes.

#### Acceptance Criteria

1. THE `docs/en/fastapi_quickstart.md` and `docs/fr/fastapi_quickstart.md` SHALL be rewritten
   around the App_Factory: install (`pip install tenxyte[fastapi]`), create app, run uvicorn,
   first authenticated API call — validated by the timed manual test MT-1.
2. THE parity table generated by the Parity_Matrix SHALL be published in the documentation (EN
   and FR) and regenerated by CI.
3. THE `async_guide.md` (EN and FR) SHALL document the Async_Ports, the resolution rule, and the
   JWT_Async_Pattern as the reference.
4. THE UI packages SHALL be documented in `docs/*/integration/javascript/` (installation, theming,
   component reference).

### Requirement 8: Compatibilité ascendante et respect de l'architecture

**User Story:** En tant que mainteneur, je veux que ce chantier massif soit strictement additif
pour l'existant, afin que les utilisateurs Django et l'API sync ne subissent aucune régression.

#### Acceptance Criteria

1. THE Django_Adapter SHALL NOT be modified by this phase: no view, serializer, URL, setting,
   model, or migration changes; the full existing test suite SHALL pass without modification.
2. THE sync API of the Core SHALL remain unchanged: every existing public signature is preserved
   (snapshot-tested), and async additions SHALL NOT alter sync behavior.
3. THE FastAPI_Adapter SHALL consume only Core services and Async_Ports — no duplication of
   security logic (password checks, token generation, anti-enumeration) inside handlers.
4. THE new dependencies (SQLAlchemy async drivers, Alembic, throttling) SHALL be confined to the
   `[fastapi]` extra; the core install and the `[django]` extra SHALL be unaffected.
5. THE System SHALL ensure that all automated tests passing before this phase continue to pass
   after it; non-automatable verifications SHALL be recorded in `manual_tests.md`.

## Notes de conception ouvertes

- L'emplacement exact des Async_Ports (`ports/repositories.py` étendu vs nouveau module
  `ports/async_repositories.py`) est arrêté en conception — contrainte : import sans effet de
  bord et lisibilité de la doc.
- Le mécanisme de throttling FastAPI (slowapi vs implémentation maison sur le port cache) est
  arrêté en conception — contrainte : mêmes familles de limites que les throttle classes Django,
  testable avec le temps simulé.
- La stratégie multi-tenant du Reference_Stack (schéma unique en Phase 3, isolation par
  application comme Django) est confirmée en conception.
- Le découpage exact des composants `OrgSwitcher` et `ForcedPasswordChange` (headless : hook seul
  vs hook + composant) est arrêté avec l'équipe JS lors du kick-off du chantier UI.
- Les endpoints Django jugés non portables (ex : intégration admin Django) sont candidats à la
  liste d'exclusions — chaque cas est tranché en revue de conception, jamais unilatéralement.
