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

- [ ] 1. Fondations async du Core
  - [ ] 1.1 Créer les Async_Ports et le Sync_Bridge
    - Nouveau module `src/tenxyte/ports/async_repositories.py` : `AsyncUserRepository` (miroir
      exact de `UserRepository`), ports async des storages de requête (TOTP, magic link,
      WebAuthn, cache), `SyncToAsync*` (pont `to_thread`), résolveur `as_async()` — modules sync
      existants intouchés
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 1.2 Write property test for sync/async semantic equivalence
    - **Property 4: Équivalence sémantique sync/async des ports** (séquences d'opérations
      générées sur repo in-memory vs son pont)
    - **Validates: Requirements 1.1, 1.3**

  - [ ] 1.3 Write property test for normalized async resolution
    - **Property 6: Résolution async normalisée** (natif détecté par espionnage, pont en repli)
    - **Validates: Requirements 1.4, 2.1, 2.2**

  - [ ] 1.4 Ajouter les variantes async des services Core
    - `magic_link_service` et `session_service` : extraction des fonctions pures + méthodes
      `*_async` via `as_async(storage)` ; `totp_service` : accès storage async, crypto sync ;
      `jwt_service` inchangé (gabarit)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 1.5 Write sync-API snapshot test
    - **Property 5: L'API sync du Core est intouchée** (snapshot des signatures publiques)
    - **Validates: Requirements 1.2, 2.4, 8.2**

- [ ] 2. Socle FastAPI de production
  - [ ] 2.1 Implémenter settings, App_Factory et lifespan
    - `settings.py` (pydantic-settings, env `TENXYTE_*`, mêmes défauts que Django), `app.py`
      (`create_tenxyte_app` / `create_tenxyte_router`, lifespan engine async + healthcheck)
    - _Requirements: 3.1, 3.5_

  - [ ] 2.2 Implémenter le Reference_Stack
    - `models_sa.py` (SQLAlchemy 2.0 async, invariants sécurité : hash tokens, TOTP chiffré,
      bcrypt+pre-hash identiques au Core), `repositories_async.py` (implémentations des
      Async_Ports), `migrations/` Alembic, `deps.py` (DI par défaut surchargeable — fin des
      `NotImplementedError`)
    - _Requirements: 3.2, 3.3_

  - [ ] 2.3 Implémenter middleware, erreurs et throttling
    - `middleware.py` : `ApplicationAuthMiddleware` (parité `APP_AUTH_REQUIRED` + toggle),
      error handler global `{error, code, details}` (422 → 400 canonique) ; `throttling.py` sur
      le port cache (mêmes familles que Django, temps simulable) ; `security.py` (`require_jwt`
      en dépendance, scopes restreints, AgentBearer)
    - _Requirements: 3.4, 3.6_

  - [ ] 2.4 Write property tests for the production base
    - **Property 9: Format d'erreur canonique universel** (corpus de requêtes invalides générées)
    - **Property 10: Le stack de référence démarre sans surcharge** (register→login→me sur
      aiosqlite vierge)
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.6_

  - [ ] 2.5 Compléter l'extra `[fastapi]`
    - `pyproject.toml` : + aiosqlite, alembic, pydantic-settings (asyncpg documenté optionnel) ;
      core et `[django]` inchangés
    - _Requirements: 8.4_

- [ ] 3. Outillage de preuve (avant toute vague de parité)
  - [ ] 3.1 Implémenter la Parity_Matrix
    - `scripts/parity_matrix.py` (introspection des deux routeurs, normalisation, diff,
      `--groups`), `parity_exclusions.toml` (justifications obligatoires), sortie
      `docs/*/parity_table.md`
    - **Property 1 (socle)**
    - _Requirements: 5.1, 4.5_

  - [ ] 3.2 Créer la Contract_Suite paramétrée
    - `tests/contract/` : fixture `api` paramétrée {django, fastapi} ; refactor des snapshots de
      forme existants en assertions partagées (tests Django actuels inchangés dans leurs
      attentes) ; câblage CI double exécution
    - **Property 2 (socle)**
    - _Requirements: 5.2_

  - [ ] 3.3 Implémenter l'Async_Purity_Check
    - `scripts/check_async_purity.py` (AST, motifs interdits, ignore justifié) + job CI + cas de
      test du checker (un motif introduit → échec)
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
