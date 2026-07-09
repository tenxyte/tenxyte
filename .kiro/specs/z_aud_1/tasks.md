# Implementation Plan: Phase 1 « Crédibilité » (z_aud_1)

## Overview

Cette implémentation consolide Tenxyte vers la 1.0 en quatre blocs ordonnés par dépendances :
d'abord le code runtime additif (Apple Sign-In) et l'Import_Guard — les deux seuls chantiers
touchant `src/` ; puis le packaging (qui dépend de l'Import_Guard) ; puis les livrables
documentaires et CI (indépendants entre eux) ; enfin la release engineering 1.0 qui scelle le
tout. Une ultime release 0.9.x d'avertissement précède la publication de la 1.0.

Aucune tâche ne modifie `tenxyte.core` / `tenxyte.ports` (hors ajout d'une exception import-safe
dans `exceptions.py`). Les vérifications non automatisables sont tracées dans `manual_tests.md`
avec référence croisée depuis les tâches concernées (marqueur `[MT-x]`).

## Tasks

- [ ] 1. Apple Sign-In : provider et settings
  - [ ] 1.1 Ajouter les settings Apple à `SocialSettingsMixin`
    - Modifier `src/tenxyte/conf/social.py` : propriétés `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`,
      `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` (convention `getattr(settings, ..., "")` identique aux
      providers existants) ; étendre le défaut de `SOCIAL_PROVIDERS` à
      `["google", "github", "microsoft", "facebook", "apple"]`
    - _Requirements: 5.8, 5.9_

  - [ ] 1.2 Implémenter `AppleOAuthProvider`
    - Ajouter à `src/tenxyte/services/social_auth_service.py` : `_generate_client_secret()`
      (JWT ES256 via PyJWT/cryptography, jamais persisté), `exchange_code()` (POST
      `appleid.apple.com/auth/token`), `verify_id_token()` (PyJWKClient fail-closed : signature,
      iss, aud, exp ; un refresh JWKS max sur kid inconnu), `get_user_info()` (retourne None + log,
      chemin nominal = verify_id_token), normalisation `email_verified` string→bool
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ] 1.3 Câbler le provider dans la vue sociale et l'orchestrateur
    - Modifier `src/tenxyte/views/social_auth_views.py` : router `apple` (flow id_token comme
      Google), accepter le champ optionnel `user` (First_Auth_User_Payload) et enrichir
      `first_name`/`last_name` ; mettre à jour `supported_providers` dans `INVALID_PROVIDER`
    - Vérifier que `SocialAuthService.authenticate` fonctionne sans modification (dict normalisé
      identique) et que le F-03 s'applique
    - _Requirements: 5.7, 5.9, 5.10, 5.11_

  - [ ] 1.4 Write unit tests for the Apple client secret and settings
    - Header (`alg=ES256`, `kid`) et claims exacts avec une clé EC de test ; deux appels → deux
      JWT distincts, aucune persistance ; défauts `SOCIAL_PROVIDERS` (4 anciens inchangés + apple)
    - _Requirements: 5.2, 5.8, 5.9_

  - [ ] 1.5 Write property test for well-formed ephemeral Apple client secret
    - **Property 5: Le client secret Apple est un JWT ES256 bien formé et éphémère**
    - **Validates: Requirements 5.2**

  - [ ] 1.6 Write property test for fail-closed id_token validation
    - **Property 6: Validation fail-closed de l'Apple_ID_Token** (signature altérée, iss/aud
      faux, exp passé, kid inconnu, JWKS injoignable → None, zéro effet de bord)
    - **Validates: Requirements 5.4, 5.5**

  - [ ] 1.7 Write property test for normalized Apple user dict
    - **Property 7: Normalisation du dict utilisateur Apple** (email_verified multi-types,
      private relay, sub aléatoires)
    - **Validates: Requirements 5.6**

  - [ ] 1.8 Write property test for optional first-auth user payload
    - **Property 8: Le payload de première autorisation est optionnel**
    - **Validates: Requirements 5.7**

  - [ ] 1.9 Write unit tests for existing-provider non-regression and F-03 on Apple
    - **Property 9** (suites google/github/microsoft/facebook inchangées et vertes) et
      **Property 10** (email Apple non vérifié + compte local → refus F-03)
    - **Validates: Requirements 5.10, 5.11, 8.1**

  - [ ] 1.10 Documenter le provider Apple
    - `docs/en/endpoints.md` + `docs/fr/endpoints.md` : provider `apple` dans les sections
      sociales (+ notes `form_post` et Private_Relay_Email) ; `docs/en/settings.md` +
      `docs/fr/settings.md` : les 4 settings `APPLE_*` ; passer `scripts/validate_endpoints.py`
    - _Requirements: 5.12_

- [ ] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Import_Guard (PEP 562)
  - [ ] 3.1 Ajouter `TenxyteMissingDependencyError` et refactorer `tenxyte/__init__.py`
    - Ajouter l'exception (héritant d'`ImportError`, import-safe sans Django) à
      `src/tenxyte/exceptions.py` en veillant à ce que ce module reste importable sans Django
    - Refactorer `src/tenxyte/__init__.py` : top-level = version + symboles Core uniquement ;
      table `_DJANGO_SYMBOLS` ; `__getattr__` PEP 562 avec message
      `pip install tenxyte[django]` ; `__dir__` surchargé ; `__all__` explicite
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ] 3.2 Write property test for import without Django
    - **Property 1: Import sans Django réussit et expose le Core** (sous-processus / patching
      `sys.modules` pour simuler l'absence de Django)
    - **Validates: Requirements 2.3**

  - [ ] 3.3 Write property test for explicit failure on Django-only symbols
    - **Property 2: Accès à un symbole Django-only sans Django échoue explicitement**
    - **Validates: Requirements 2.4**

  - [ ] 3.4 Write unit tests for guard transparency with Django installed
    - **Property 3: Transparence de l'Import_Guard avec Django présent** (tous les symboles
      historiques résolus à l'identique ; la suite de tests existante sert de filet)
    - **Validates: Requirements 2.5, 8.2**

  - [ ] 3.5 Write the public-API snapshot test
    - **Property 4: Snapshot des exports publics** — test comparant `tenxyte.__all__` à la liste
      du Stability_Contract, échouant sur toute disparition
    - **Validates: Requirements 1.4**

- [ ] 4. Inversion du packaging
  - [ ] 4.1 Inverser les extras dans `pyproject.toml`
    - `dependencies` = contenu actuel de `[core]` ; `[django]` = stack Django complète ;
      `[core]` = alias no-op documenté déprécié ; `[all]` = django + fastapi + features ;
      extras restants inchangés
    - _Requirements: 2.1, 2.2, 2.6_

  - [ ] 4.2 Write dependency-set equivalence test
    - **Property 12: Équivalence des ensembles de dépendances** (parse `pyproject.toml`,
      `deps(1.0) ∪ extras[django](1.0) == deps(0.9.6.4)`)
    - **Validates: Requirements 2.1, 2.2, 2.5**

  - [ ] 4.3 Ajouter la matrice d'installation en CI
    - Job `install-matrix` dans `.github/workflows/ci.yml` : venvs propres pour `""`,
      `"[django]"`, `"[core]"`, `"[django,webauthn]"` ; smoke import + version ; smoke Django
      (migration check + quickstart) quand la stack est présente, smoke Core (JWT/TOTP) sinon
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [ ] 4.4 Rédiger la section « 0.9 → 1.0 » du guide de migration
    - `docs/en/MIGRATION_GUIDE.md` + `docs/fr/MIGRATION_GUIDE.md` : commande d'install,
      comportement de l'Import_Guard, garantie « zéro changement runtime avec [django] »
    - _Requirements: 2.8_

  - [ ] 4.5 Préparer l'ultime release 0.9.x d'avertissement
    - `DeprecationWarning` à l'import annonçant l'inversion de packaging en 1.0 ; note README ;
      entrée CHANGELOG ; publication tracée `[MT-6]`
    - _Requirements: 2.7_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass (including install-matrix), ask the user if questions arise.

- [ ] 6. Politique de sécurité et divulgation
  - [ ] 6.1 Rédiger `SECURITY.md`
    - Racine du dépôt : versions supportées (1.0.x ✅ / 0.9.x critiques 6 mois / < 0.9 ❌),
      canal GitHub PVR exclusif, SLA (72 h / 7 j / 14-30-90 j), embargo ≤ 90 j, crédit,
      périmètre in/out, processus advisory→CVE, lien `docs/security-audit/`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ] 6.2 Activer GitHub Private Vulnerability Reporting `[MT-4]`
    - Action manuelle sur le dépôt ; vérification consignée dans `manual_tests.md` §4
    - _Requirements: 3.8_

- [ ] 7. Signature et attestation des releases
  - [ ] 7.1 Migrer `publish.yml` vers Trusted Publishing + attestations
    - `permissions: id-token: write`, `environment: pypi`, `pypa/gh-action-pypi-publish` avec
      `attestations: true`, suppression de toute référence au token PyPI
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 7.2 Configurer le Trusted Publisher côté PyPI et l'environnement GitHub `[MT-5]`
    - Actions manuelles (PyPI pending publisher, environnement `pypi` protégé, purge du secret) ;
      vérification consignée dans `manual_tests.md` §5
    - _Requirements: 4.1, 4.3_

  - [ ] 7.3 Documenter la procédure de release et de vérification
    - Doc mainteneur (CONTRIBUTING ou runbook) : tags signés, déclenchement du workflow,
      commande de vérification des attestations pour les consommateurs
    - _Requirements: 4.4, 4.5_

- [ ] 8. Contrat de stabilité et dossier d'audit
  - [ ] 8.1 Rédiger `docs/en/stability.md` + `docs/fr/stability.md`
    - Énumération de la Public_API_Surface, politique SemVer, Deprecation_Policy, liste explicite
      du non-couvert ; cohérence avec le `__all__` du snapshot (tâche 3.5)
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [ ] 8.2 Rédiger le modèle de menaces
    - `docs/security-audit/threat-model.md` : actifs, acteurs, STRIDE léger par domaine (JWT,
      OTP, WebAuthn, AIRS, reset, orgs), hypothèses de déploiement
    - _Requirements: 6.1_

  - [ ] 8.3 Rédiger le périmètre d'audit
    - `docs/security-audit/audit-scope.md` : modules in-scope (jwt/totp/webauthn/otp/agent/
      decorators + flows), exclusions, environnement de test fourni
    - _Requirements: 6.2_

  - [ ] 8.4 Rédiger la checklist pré-audit ASVS
    - `docs/security-audit/pre-audit-checklist.md` : ASVS L2 V2/V3/V6, statut + référence de
      code par point ; liens depuis `SECURITY.md`
    - _Requirements: 6.3, 6.4_

- [ ] 9. Release engineering 1.0
  - [ ] 9.1 Basculer la version et le classifieur
    - `pyproject.toml` : `version = "1.0.0"`, classifieur `5 - Production/Stable` ; test
      unitaire de cohérence version/classifieur
    - _Requirements: 7.1_

  - [ ] 9.2 CHANGELOG 1.0.0 et mise à jour des READMEs
    - Entrée 1.0.0 (Breaking packaging / Added apple, SECURITY.md, attestations, stability) ;
      `README.md` + `README.fr.md` : quickstart avec `pip install tenxyte[django]`
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ] 9.3 Vérifier l'invariance du schéma
    - **Property 11: Invariance du schéma de données** — test : 25 migrations, zéro
      `makemigrations` en attente
    - **Validates: Requirements 8.1**

- [ ] 10. Non-régression finale et validation manuelle
  - [ ] 10.1 Exécuter la suite de tests existante complète
    - L'intégralité de `tests/` passe sans modification d'aucun test existant
    - _Requirements: 8.4_

  - [ ] 10.2 Dérouler la campagne de tests manuels
    - Exécuter `manual_tests.md` §1–§7 (installation, Apple E2E, PVR, Trusted Publishing,
      attestations, SECURITY.md, release 0.9.x) et consigner les résultats dans le registre
    - _Requirements: 3.8, 4.5, 5.*, 8.4_

- [ ] 11. Checkpoint final - Ensure all tests pass
  - Ensure all tests pass, manual test register complete, ask the user before tagging v1.0.0.

## Notes

- Les tâches marquées `[MT-x]` ont une contrepartie obligatoire dans `manual_tests.md` : la tâche
  n'est cochable qu'après consignation du résultat dans le registre d'exécution.
- La release 0.9.x d'avertissement (4.5) peut être publiée dès que 4.4 est prête — elle ne dépend
  pas du reste de la phase.
- Aucune tâche ne modifie `tenxyte.core` / `tenxyte.ports` hors l'exception import-safe (3.1),
  conformément à Requirement 8.3.
- La réalisation de l'audit externe lui-même est hors périmètre : les tâches 8.2–8.4 produisent
  le dossier remis au prestataire.
- Property tests : Hypothesis ≥ 100 exemples, référencés au format
  **Feature: z_aud_1, Property N: <texte>**, réseau Apple entièrement mocké.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "6.1", "8.1", "8.2", "8.3"] },
    { "id": 1, "tasks": ["1.2", "3.1", "6.2", "7.1", "8.4"] },
    { "id": 2, "tasks": ["1.3", "1.4", "1.5", "1.6", "1.7", "3.2", "3.3", "3.4", "3.5", "7.2", "7.3"] },
    { "id": 3, "tasks": ["1.8", "1.9", "1.10", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4"] },
    { "id": 5, "tasks": ["4.5", "9.1", "9.2", "9.3"] },
    { "id": 6, "tasks": ["10.1", "10.2"] }
  ]
}
```
