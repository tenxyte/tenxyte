# Implementation Plan: Passwordless Phone Login (OTP)

## Overview

Cette implémentation ajoute une connexion passwordless par OTP téléphonique en insérant du code additif dans les patterns `Django_Adapter` existants (vues DRF, serializers, throttles, `OTPService` legacy) sans toucher au Core. L'ordre des tâches suit les dépendances naturelles : schéma de données et réglages en premier, puis le service OTP de connexion, puis les deux nouveaux endpoints publics, puis la porte de réauthentification partagée (`ReauthService`) et son câblage dans les actions sensibles existantes, puis `Set_Initial_Password_Operation`, et enfin une passe de non-régression globale.

## Tasks

- [x] 1. Modèle de données : type OTP `login` et champ `has_usable_password`
  - [x] 1.1 Ajouter le choix `login` à `OTPCode.TYPE_CHOICES`, le champ `has_usable_password` (défaut `True`) à `User`, et la migration additive `0017_login_otp_type_and_passwordless_account`
    - Modifier `src/tenxyte/models/operational.py` (`OTPCode.TYPE_CHOICES` : ajouter `("login", "Login OTP")`, aucune valeur retirée)
    - Modifier `src/tenxyte/models/auth.py` (ajouter `has_usable_password = models.BooleanField(default=True, ...)`)
    - Créer `src/tenxyte/migrations/0017_login_otp_type_and_passwordless_account.py` avec uniquement `AddField`/`AlterField` (dépendance sur `0016_normalize_phone_country_code`), sans `RemoveField`/`RemoveConstraint`
    - _Requirements: 1.6, 6.1, 8.6_

  - [x] 1.2 Write unit tests for the additive migration and OTP type acceptance
    - Vérifier que `Migration.operations` ne contient que des `AddField`/`AlterField` ajoutant un choix (aucune suppression de champ/contrainte/choix existant)
    - Vérifier que `OTPCode.objects.create(..., otp_type="login")` est accepté sans erreur de validation
    - Vérifier que tous les comptes existants (créés sans le champ) obtiennent `has_usable_password=True` par défaut
    - _Requirements: 8.6_

- [x] 2. Réglages de la fonctionnalité
  - [x] 2.1 Ajouter `OTP_LOGIN_ENABLED`, `OTP_LOGIN_AUTO_REGISTER`, `OTP_LOGIN_VALIDITY_MINUTES` à `AuthSettingsMixin`
    - Modifier `src/tenxyte/conf/auth.py`, section "OTP Settings" : trois nouvelles propriétés utilisant `self._get("TENXYTE_...", default)` avec les défauts `False`, `True`, `10`
    - _Requirements: 5.1, 5.2, 5.3, 8.7_

  - [x] 2.2 Write unit tests for new settings defaults and non-regression
    - Vérifier `OTP_LOGIN_ENABLED is False`, `OTP_LOGIN_AUTO_REGISTER is True`, `OTP_LOGIN_VALIDITY_MINUTES == 10` par défaut
    - Vérifier qu'aucune valeur par défaut d'un setting `auth_settings` préexistant n'a changé
    - _Requirements: 5.1, 5.2, 5.3, 8.7_

- [x] 3. Génération et vérification du Login OTP dans `OTPService`
  - [x] 3.1 Implémenter `OTPService.generate_login_otp(user)` et `OTPService.verify_login_otp(user, code)`
    - Ajouter à `src/tenxyte/services/otp_service.py`, calqués sur `generate_password_reset_otp`/`verify_password_reset_otp` : invalidation des anciens `login` OTP non utilisés, durée issue de `auth_settings.OTP_LOGIN_VALIDITY_MINUTES`, aucune mutation de flag utilisateur dans `verify_login_otp`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 3.2 Write property test for Login OTP generation invalidation
    - **Property 1: Génération de Login OTP invalide les codes précédents**
    - **Validates: Requirements 1.1**

  - [x] 3.3 Write property test for configured validity duration
    - **Property 2: La durée de validité suit le réglage configuré**
    - **Validates: Requirements 1.2**

  - [x] 3.4 Write property test for successful verification marking code used
    - **Property 3: Une vérification correcte marque le code comme utilisé et réussit**
    - **Validates: Requirements 1.4**

  - [x] 3.5 Write property test for verification failure without authentication effect
    - **Property 4: Tout échec de vérification est signalé sans authentifier**
    - **Validates: Requirements 1.5**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Throttles dédiés à la demande d'OTP de connexion
  - [x] 5.1 Implémenter `LoginOTPRequestThrottle` (5/min) et `LoginOTPRequestDailyThrottle` (20/day)
    - Ajouter à `src/tenxyte/throttles.py`, distincts de `RegisterThrottle`/`RegisterDailyThrottle`
    - _Requirements: 4.1_

  - [x] 5.2 Write unit test verifying throttle scopes are dedicated and distinct
    - Vérifier que les scopes `login_otp_request`/`login_otp_request_daily` diffèrent de `register`/`register_daily`
    - _Requirements: 4.1_

- [x] 6. Serializers pour connexion OTP, réauthentification et premier mot de passe
  - [x] 6.1 Implémenter `LoginOTPRequestSerializer`, `LoginOTPVerifySerializer`, `SetInitialPasswordSerializer`, `ReauthSerializer`
    - Créer `src/tenxyte/serializers/login_otp_serializers.py` avec les quatre serializers (champ `otp_code`, jamais `code`, cohérent avec `PasswordResetConfirmSerializer`)
    - `validate_phone_country_code` appelle `normalize_phone_country_code()` sur les deux serializers concernés
    - `SetInitialPasswordSerializer.validate_new_password` appelle `validate_password`
    - Exporter les quatre classes depuis `src/tenxyte/serializers/__init__.py`
    - _Requirements: 2.2, 2.3, 7.3, 7.6, 6.4_

  - [x] 6.2 Write unit tests for the new serializers
    - Normalisation de `phone_country_code` (avec/sans `+`)
    - Rejet des champs manquants/malformés (`phone_number`, `otp_code` de mauvaise longueur)
    - `SetInitialPasswordSerializer` rejette un mot de passe non conforme
    - `ReauthSerializer` accepte `password` seul, `otp_code` seul, ou aucun des deux (validation métier faite ailleurs)
    - _Requirements: 2.2, 2.3, 7.6_

- [x] 7. Implémenter `Login_OTP_Request_View`
  - [x] 7.1 Créer `Login_OTP_Request_View`
    - Créer `src/tenxyte/views/login_otp_views.py`, `POST {API_PREFIX}/auth/login/otp/request/`, `permission_classes = [AllowAny]`, `throttle_classes = [LoginOTPRequestThrottle, LoginOTPRequestDailyThrottle]`
    - Logique : `FEATURE_DISABLED` (404) si désactivé ; `validate_application_required` ; validation serializer ; résolution utilisateur par téléphone (`is_deleted=False`) ; génération/envoi OTP si trouvé ; création `Passwordless_Account` (`has_usable_password=False`, `is_phone_verified=False`) si `OTP_LOGIN_AUTO_REGISTER` et absent ; réponse anti-énumération de forme identique si auto-register désactivé et compte absent
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 6.2_

  - [x] 7.2 Write property test for no effect when feature is disabled
    - **Property 5: Effet nul de `Login_OTP_Request_View` quand la fonctionnalité est désactivée**
    - **Validates: Requirements 2.1**

  - [x] 7.3 Write property test for malformed requests rejected without side effect
    - **Property 6: Rejet des requêtes malformées sans effet de bord**
    - **Validates: Requirements 2.3**

  - [x] 7.4 Write property test for missing required application blocking generation
    - **Property 7: Application requise et absente bloque toute génération**
    - **Validates: Requirements 2.4**

  - [x] 7.5 Write property test for existing account request generating and sending a code
    - **Property 8: Requête pour un compte existant génère et envoie un code pour ce compte**
    - **Validates: Requirements 2.5**

  - [x] 7.6 Write property test for auto-registration creating a properly initialized passwordless account
    - **Property 9: L'auto-enregistrement crée un compte passwordless correctement initialisé**
    - **Validates: Requirements 2.6, 6.2**

  - [x] 7.7 Write property test for anti-enumeration on the OTP request response
    - **Property 10: Anti-énumération sur la demande d'OTP de connexion**
    - **Validates: Requirements 2.7**

- [x] 8. Implémenter `Login_OTP_Verify_View`
  - [x] 8.1 Créer `Login_OTP_Verify_View`
    - Ajouter à `src/tenxyte/views/login_otp_views.py`, `POST {API_PREFIX}/auth/login/otp/verify/`, `permission_classes = [AllowAny]`, `throttle_classes = [OTPVerifyThrottle]`
    - Logique : `FEATURE_DISABLED` (404) si désactivé ; validation serializer ; résolution utilisateur (401 générique `OTP_INVALID` si absent, forme strictement identique à un code incorrect) ; `verify_login_otp` ; `Account_Status_Checks` (423 verrouillé, 401 autre échec) ; `is_phone_verified = True` sur succès ; bloc 2FA identique à `LoginPhoneView` ; émission de jetons via `JWT_Service` et persistance du `RefreshToken` ; réponse 200 de forme identique à `/login/phone/`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 4.2_

  - [x] 8.2 Write property test for no effect when feature is disabled
    - **Property 11: Effet nul de `Login_OTP_Verify_View` quand la fonctionnalité est désactivée**
    - **Validates: Requirements 3.1**

  - [x] 8.3 Write property test for identical anti-enumeration response
    - **Property 12: Anti-énumération sur la vérification — réponse générique identique**
    - **Validates: Requirements 3.4, 3.6**

  - [x] 8.4 Write property test for account status checks blocking token issuance with expected HTTP codes
    - **Property 13: Les contrôles de statut de compte bloquent l'émission de jeton avec le code HTTP attendu**
    - **Validates: Requirements 3.8, 3.9**

  - [x] 8.5 Write property test for successful login marking phone as verified
    - **Property 14: Le login OTP réussi marque le téléphone comme vérifié**
    - **Validates: Requirements 3.10**

  - [x] 8.6 Write property test for the 2FA gate on token issuance
    - **Property 15: La porte 2FA n'émet un jeton que si le code TOTP est valide**
    - **Validates: Requirements 3.11, 3.12**

  - [x] 8.7 Write property test for success response shape matching `/login/phone/`
    - **Property 16: La réponse de succès a la même forme que `/login/phone/`**
    - **Validates: Requirements 3.13**

- [x] 9. Câbler le routing des endpoints de connexion OTP
  - [x] 9.1 Ajouter les routes et exports pour `Login_OTP_Request_View`/`Login_OTP_Verify_View`
    - Modifier `src/tenxyte/urls.py` (section `# Login`) : `login/otp/request/`, `login/otp/verify/`
    - Modifier `src/tenxyte/views/__init__.py` : exporter les deux nouvelles vues
    - _Requirements: 8.1, 8.3_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implémenter `ReauthService`
  - [x] 11.1 Créer `ReauthService.verify(user, password, otp_code)`
    - Créer `src/tenxyte/services/reauth_service.py` : mot de passe correct → succès ; sinon `otp_code` valide (via `verify_login_otp`) → succès ; sinon échec `REAUTH_REQUIRED`
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 11.2 Write property test for the reauthentication gate
    - **Property 17: Porte de réauthentification des actions sensibles**
    - **Validates: Requirements 6.4, 6.5**

  - [x] 11.3 Write property test for backward-compatible current-password path
    - **Property 18: Compatibilité ascendante du mot de passe actuel**
    - **Validates: Requirements 6.6, 8.4**

- [x] 12. Câbler `ReauthService` et la restriction passwordless dans les actions sensibles existantes
  - [x] 12.1 Ajouter la garde `has_usable_password` et `ReauthService` à `ChangePasswordView`
    - Modifier `src/tenxyte/views/password_views.py` : si `request.user.has_usable_password is False` → 400 `PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD` sans consulter `ReauthService` ; sinon déléguer la vérification à `ReauthService.verify(user, password=..., otp_code=...)`
    - _Requirements: 6.4, 6.6, 6.7, 8.4_

  - [x] 12.2 Write property test for passwordless accounts never setting a password via change-password
    - **Property 19: Un compte passwordless ne peut jamais définir son mot de passe via le changement de mot de passe existant**
    - **Validates: Requirements 6.7**

  - [x] 12.3 Accepter un `OTP_Reauth_Challenge` dans `TwoFactorDisableView` via `ReauthService`
    - Modifier `src/tenxyte/views/twofa_views.py` : accepter `password` OU `otp_code` en plus du code TOTP, en déléguant à `ReauthService.verify`
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 12.4 Accepter un `OTP_Reauth_Challenge` dans les vues de suppression/export de compte
    - Modifier `src/tenxyte/views/account_deletion_views.py` (`request_account_deletion`, `cancel_account_deletion`, `export_user_data`) pour déléguer la preuve d'identité à `ReauthService.verify` (mot de passe ou `otp_code`) au lieu du seul `check_password`
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 12.5 Accepter un `OTP_Reauth_Challenge` dans la suppression du compte courant
    - Modifier `src/tenxyte/views/user_views.py` (`DeleteAccountView.delete`) pour déléguer la preuve d'identité à `ReauthService.verify`
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 12.6 Write unit tests for reauthentication wiring across sensitive action views
    - Vérifier pour chaque vue modifiée (12.3, 12.4, 12.5) que le mot de passe correct et l'OTP valide sont tous deux acceptés, et que l'absence des deux renvoie `REAUTH_REQUIRED`
    - _Requirements: 6.4, 6.5, 6.6_

- [x] 13. Implémenter `Set_Initial_Password_Operation`
  - [x] 13.1 Créer `SetInitialPasswordView`
    - Modifier `src/tenxyte/views/password_views.py` : `POST {API_PREFIX}/auth/password/set-initial/`, authentifié (`@require_jwt`), sans `AllowAny`
    - Logique : `ALREADY_HAS_PASSWORD` (400) si `has_usable_password` déjà vrai ; validation serializer ; `verify_login_otp` obligatoire (aucune substitution par mot de passe) ; contrôle anti-fuite (HIBP) ; `update_password` puis `has_usable_password=True`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 13.2 Write property test for OTP login availability regardless of initial-password status
    - **Property 20: L'authentification OTP reste disponible indépendamment de la définition d'un mot de passe**
    - **Validates: Requirements 7.2**

  - [x] 13.3 Write property test for the OTP gate of Set_Initial_Password_Operation
    - **Property 21: Porte OTP de `Set_Initial_Password_Operation`**
    - **Validates: Requirements 7.3, 7.4**

  - [x] 13.4 Write property test for successful initial password creation
    - **Property 22: Succès de `Set_Initial_Password_Operation`**
    - **Validates: Requirements 7.5, 6.3**

  - [x] 13.5 Write property test for non-conforming password leaving state unchanged
    - **Property 23: Un mot de passe non conforme ne modifie aucun état**
    - **Validates: Requirements 7.6**

  - [x] 13.6 Write property test for accounts already having a password being rejected
    - **Property 24: Un compte déjà doté d'un mot de passe ne peut pas utiliser `Set_Initial_Password_Operation`**
    - **Validates: Requirements 7.7**

  - [x] 13.7 Write property test for dual login availability after setting the first password
    - **Property 25: Double disponibilité après création du premier mot de passe**
    - **Validates: Requirements 7.8**

  - [x] 13.8 Câbler la route `/password/set-initial/`
    - Modifier `src/tenxyte/urls.py` (section `# Password management`) et `src/tenxyte/views/__init__.py` pour exposer `SetInitialPasswordView`
    - _Requirements: 8.1, 8.3_

- [x] 14. Non-régression et compatibilité ascendante
  - [x] 14.1 Write unit tests snapshotting existing endpoint response shapes
    - Figer la forme des réponses de `/register/`, `/login/email/`, `/login/phone/`, `/password/change/`, `/2fa/disable/`, endpoints de suppression de compte, pour garantir qu'aucun champ documenté n'a été retiré
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 14.2 Exécuter la suite de tests existante complète et corriger toute régression détectée
    - Lancer l'ensemble des tests déjà présents dans `tests/` et s'assurer qu'ils passent tous sans modification de leur comportement attendu
    - _Requirements: 8.8_

- [x] 15. Checkpoint final - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Les tâches marquées `*` sont optionnelles (tests) et peuvent être ignorées pour un MVP plus rapide, mais restent fortement recommandées puisque le design définit 25 propriétés de correction.
- Chaque tâche référence les sous-clauses précises des requirements pour la traçabilité.
- Les checkpoints garantissent une validation incrémentale après les blocs logiques (OTP service, endpoints publics, réauthentification/actions sensibles, non-régression finale).
- Les tests de propriétés (`hypothesis`, ≥100 exemples) valident les 25 propriétés du design ; les tests unitaires couvrent les exemples concrets, codes d'erreur, câblage des routes/throttles et valeurs par défaut.
- Aucune tâche ne modifie `tenxyte.core`/`tenxyte.ports` : tout le nouveau code reste dans `Django_Adapter` (vues, serializers, modèles, services legacy), conformément à Requirement 8.5.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "5.1", "6.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "3.1", "5.2", "6.2"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "3.5", "7.1"] },
    { "id": 3, "tasks": ["7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "8.1", "11.1"] },
    { "id": 4, "tasks": ["8.2", "8.3", "8.4", "8.5", "8.6", "8.7", "9.1", "11.2", "11.3", "12.1", "12.3", "12.4", "12.5"] },
    { "id": 5, "tasks": ["12.2", "12.6", "13.1"] },
    { "id": 6, "tasks": ["13.2", "13.3", "13.4", "13.5", "13.6", "13.7", "13.8"] },
    { "id": 7, "tasks": ["14.1", "14.2"] }
  ]
}
```
