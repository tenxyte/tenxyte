# Implementation Plan: Force Password Change on First Login

## Overview

Cette implémentation ajoute le changement de mot de passe forcé à la première connexion en insérant du code additif dans les patterns `Django_Adapter` existants (champ `User`, réglages `AuthSettingsMixin`, vues de login/refresh, endpoints `/password/change/` et `/password/set-initial/` déjà livrés, décorateur `require_jwt`) sans toucher au Core. L'ordre des tâches suit les dépendances : schéma et réglage d'abord, puis le helper d'émission de scope et son câblage dans les login/refresh, puis l'enforcement (annotations `allowed_scopes`), puis la levée du flag et l'upgrade de token dans les deux endpoints de changement, puis le provisionnement, puis une passe de non-régression globale.

Le nouveau scope `password_change_only` réutilise strictement le mécanisme déjà en production du scope `2fa_setup_only` (`require_jwt(allowed_scopes=...)`, `request.jwt_scope`, upgrade full-scope après confirmation). Aucune tâche ne modifie `tenxyte.core` / `tenxyte.ports`.

## Tasks

- [x] 1. Modèle de données : champ `must_change_password`
  - [x] 1.1 Ajouter le champ `must_change_password` à `AbstractUser` et la migration additive `0018_user_must_change_password`
    - Modifier `src/tenxyte/models/auth.py` (`AbstractUser` : ajouter `must_change_password = models.BooleanField(default=False, help_text=...)`)
    - Créer `src/tenxyte/migrations/0018_user_must_change_password.py` avec un unique `AddField` (dépendance sur `0017_login_otp_type_and_passwordless_account`), sans `RemoveField`/`RemoveConstraint`/`AlterField` sur l'existant
    - _Requirements: 1.1, 1.2, 1.5, 7.4_

  - [x] 1.2 Write unit tests for the additive migration and default flag value
    - Vérifier que `Migration.operations` ne contient qu'un `AddField` (aucune suppression/altération de l'existant) et dépend de `0017_...`
    - Vérifier qu'un `User` créé sans préciser le flag a `must_change_password is False`
    - Vérifier que le champ est indépendant de `has_usable_password` (les quatre combinaisons sont représentables)
    - _Requirements: 1.1, 1.3, 1.5, 7.4_

  - [x] 1.3 Write property test for the inert default flag
    - **Property 1: Défaut inerte du flag**
    - **Validates: Requirements 1.1, 1.3, 7.4**

- [x] 2. Réglage de la fonctionnalité
  - [x] 2.1 Ajouter `FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` à `AuthSettingsMixin`
    - Modifier `src/tenxyte/conf/auth.py` : propriété `FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` utilisant `self._get("TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED", False)`
    - _Requirements: 6.1, 6.3, 7.2_

  - [x] 2.2 Write unit tests for the new setting default and non-regression
    - Vérifier `FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED is False` par défaut
    - Vérifier qu'aucune valeur par défaut d'un setting `auth_settings` préexistant n'a changé
    - _Requirements: 6.1, 6.3, 7.2_

- [x] 3. Helper d'émission de scope et câblage dans les endpoints de login
  - [x] 3.1 Implémenter `resolve_forced_password_change_scope(user)` et l'appliquer aux `Login_Endpoints`
    - Ajouter le helper à `src/tenxyte/views/auth_views.py` (retourne `"password_change_only"` uniquement si feature activée et `must_change_password`, sinon `None`)
    - Câbler dans `LoginEmailView`, `LoginPhoneView`, et `LoginOTPVerifyView` (`src/tenxyte/views/login_otp_views.py`) : le bloc admin-sans-2FA (`2fa_setup_only`) reste prioritaire et intact ; sinon émettre l'access token avec `extra_claims={..., "scope": "password_change_only"}` quand le helper le retourne ; ajouter le champ additif `must_change_password` (true/false) au corps de réponse dans tous les cas
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.3, 7.5_

  - [x] 3.2 Write property test for restricted token issuance on forced-change login
    - **Property 3: Émission d'un token restreint à la connexion d'un compte forcé**
    - **Validates: Requirements 3.1, 3.2**

  - [x] 3.3 Write property test for full-scope token on non-forced accounts
    - **Property 4: Token full-scope pour un compte non forcé**
    - **Validates: Requirements 3.3**

  - [x] 3.4 Write property test for disabled feature leaving tokens unchanged
    - **Property 5: Feature désactivée n'altère aucun token**
    - **Validates: Requirements 3.4, 6.2**

  - [x] 3.5 Write property test for the deterministic 2FA-bootstrap precedence
    - **Property 6: Précédence déterministe du bootstrap 2FA**
    - **Validates: Requirements 3.5**

- [x] 4. Émission de scope sur le refresh
  - [x] 4.1 Appliquer le gating au `RefreshTokenView`
    - Modifier `src/tenxyte/views/auth_views.py` (`RefreshTokenView`) : lorsque le compte du token rafraîchi est un `Forced_Change_Account` et la feature activée, le nouvel access token porte `scope="password_change_only"` ; ajouter le champ additif `must_change_password` à la réponse
    - _Requirements: 3.6, 7.3, 7.5_

  - [x] 4.2 Write property test for refresh preserving the restriction
    - **Property 7: Le refresh préserve la restriction**
    - **Validates: Requirements 3.6**

- [x] 5. Checkpoint - Ensure all tests pass
  - ✅ 56/56 tests passent (auth_views, super_admin_2fa_bootstrap, decorators, migrations 0017+0018, settings)

- [x] 6. Enforcement : autoriser le scope restreint uniquement sur les endpoints du flux
  - [x] 6.1 Annoter les `Password_Change_Endpoints` avec `allowed_scopes=["password_change_only"]`
    - Modifier `src/tenxyte/views/password_views.py` (`ChangePasswordView.post`, `SetInitialPasswordView.post`) : `@require_jwt(allowed_scopes=["password_change_only"])`
    - Modifier `src/tenxyte/views/auth_views.py` (`LogoutView`, `LogoutAllView`) pour autoriser aussi ce scope (sortie du flux)
    - Vérifier qu'aucun autre endpoint protégé n'ajoute ce scope (refus natif `403 INSUFFICIENT_SCOPE`)
    - _Requirements: 4.1, 4.2, 4.4, 4.5_

  - [x] 6.2 Write property test for restricted token rejected outside allowed endpoints
    - **Property 8: Un token restreint est refusé hors des endpoints autorisés**
    - **Validates: Requirements 4.1**

  - [x] 6.3 Write property test for restricted token accepted on password-change endpoints
    - **Property 9: Un token restreint est accepté sur les endpoints de changement de mot de passe**
    - **Validates: Requirements 4.2, 4.5**

  - [x] 6.4 Write property test for full-scope token accepted everywhere
    - **Property 10: Un token full-scope reste accepté partout**
    - **Validates: Requirements 4.3, 7.2**

- [x] 7. Levée du flag et upgrade full-scope après changement de mot de passe
  - [x] 7.1 Basculer le flag et faire l'upgrade dans `ChangePasswordView`
    - Modifier `src/tenxyte/views/password_views.py` (`ChangePasswordView.post`) : après `update_password` réussi, si `must_change_password` était `True`, le passer à `False` (`save(update_fields=["must_change_password"])`) ; si l'appel a été fait avec `request.jwt_scope == "password_change_only"`, émettre une paire full-scope et l'ajouter (champs additifs) à la réponse existante — préserver toutes les préconditions et la réponse existantes
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 5.6, 7.6_

  - [x] 7.2 Basculer le flag et faire l'upgrade dans `SetInitialPasswordView`
    - Modifier `src/tenxyte/views/password_views.py` (`SetInitialPasswordView.post`) : après le passage existant de `has_usable_password=True`, appliquer la même bascule de `must_change_password` et le même upgrade full-scope conditionnel — préserver toutes les préconditions et la réponse existantes
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 7.6_

  - [x] 7.3 Write property test for flag cleared after change-password
    - **Property 11: Levée du flag après changement de mot de passe**
    - **Validates: Requirements 5.1**

  - [x] 7.4 Write property test for flag cleared after set-initial-password
    - **Property 12: Levée du flag après définition du premier mot de passe**
    - **Validates: Requirements 5.2**

  - [x] 7.5 Write property test for full-scope upgrade after success with a restricted token
    - **Property 13: Upgrade full-scope après succès avec un token restreint**
    - **Validates: Requirements 5.3**

  - [x] 7.6 Write property test for failure leaving flag and token unchanged
    - **Property 14: Un échec ne lève pas le flag ni n'émet de token**
    - **Validates: Requirements 5.4**

  - [x] 7.7 Write property test for preserved preconditions of the change operations
    - **Property 15: Préconditions des opérations de changement inchangées**
    - **Validates: Requirements 5.5, 5.6, 7.6**

- [x] 8. Checkpoint - Ensure all tests pass
  - ✅ 35/35 property tests passent (`test_force_password_change_properties.py`, Properties 1–16)

- [x] 9. Provisionnement d'un compte avec changement forcé
  - [x] 9.1 Permettre à une `Provisioning_Operation` de positionner `must_change_password`
    - Réutiliser un chemin de création existant (vue admin de gestion d'utilisateurs et/ou invitation d'organisation) pour poser `must_change_password=True`, avec `has_usable_password=True` si un mot de passe temporaire est fourni, `False` sinon ; conserver les contrôles d'autorisation existants de ce chemin ; ne pas modifier les créations self-service
    - Fichiers concernés à confirmer à l'implémentation : `src/tenxyte/views/user_views.py` (admin) et/ou `src/tenxyte/views/organization_views.py` (invitation)
    - _Requirements: 1.4, 2.1, 2.2, 2.3, 2.4_

  - [x] 9.2 Write property test for provisioning setting the flag and both account variants
    - **Property 2: Provisionnement positionne le flag et les deux variantes de compte**
    - **Validates: Requirements 2.1, 2.2, 1.5**

  - [x] 9.3 Write unit tests for provisioning authorization and self-service non-regression
    - Vérifier qu'un appelant non autorisé ne peut pas positionner le flag via le chemin de provisionnement
    - Vérifier qu'une inscription self-service laisse `must_change_password=False`
    - _Requirements: 2.3, 2.4_

- [x] 10. Non-régression et compatibilité ascendante
  - [x] 10.1 Write unit tests snapshotting existing endpoint response shapes
    - Figer la forme des réponses de `/login/email/`, `/login/phone/`, `/login/otp/verify/`, `/refresh/`, `/password/change/`, `/password/set-initial/` pour garantir qu'aucun champ documenté n'a été retiré et que `must_change_password` est ajouté en plus
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 10.2 Write property test for the overall backward-compatibility invariant
    - **Property 16: Non-régression du contrat existant**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 10.3 Exécuter la suite de tests existante complète et corriger toute régression détectée
    - Lancer l'ensemble des tests déjà présents dans `tests/` et s'assurer qu'ils passent tous sans modification de leur comportement attendu
    - _Requirements: 7.7_

- [x] 11. Checkpoint final - Ensure all tests pass
  - ✅ 35/35 property tests (Properties 1–16) + 56/56 tests de non-régression passent
  - ✅ Aucune régression sur les tests existants (auth_views, super_admin_2fa_bootstrap, decorators, passwordless, reauth, endpoint snapshots)

## Notes

- Les tâches de tests (property tests et unitaires) peuvent être ignorées pour un MVP plus rapide, mais restent fortement recommandées puisque le design définit 16 propriétés de correction.
- Chaque tâche référence les sous-clauses précises des requirements pour la traçabilité.
- Les checkpoints garantissent une validation incrémentale après les blocs logiques (émission de scope, enforcement, levée du flag, provisionnement, non-régression finale).
- Aucune tâche ne modifie `tenxyte.core` / `tenxyte.ports` : tout le nouveau code reste dans `Django_Adapter` (modèle, réglages, vues, décorateur réutilisé), conformément à Requirement 7.5.
- Le scope `password_change_only` réutilise le mécanisme du scope `2fa_setup_only` déjà en production ; aucun second chemin d'enforcement n'est introduit (Requirement 4.5).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.2", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "3.5", "4.1", "6.1"] },
    { "id": 3, "tasks": ["4.2", "6.2", "6.3", "6.4", "7.1", "7.2"] },
    { "id": 4, "tasks": ["7.3", "7.4", "7.5", "7.6", "7.7", "9.1"] },
    { "id": 5, "tasks": ["9.2", "9.3", "10.1", "10.2"] },
    { "id": 6, "tasks": ["10.3"] }
  ]
}
```
