# Requirements Document

## Introduction

Cette fonctionnalité ajoute une connexion passwordless native par téléphone, basée sur un code OTP envoyé par SMS (ou WhatsApp via le backend SMS configuré). Elle introduit deux nouveaux endpoints publics :

- `POST /api/v1/auth/login/otp/request/` : demande d'un code OTP de connexion pour un numéro de téléphone donné, avec inscription automatique optionnelle si le numéro n'existe pas encore.
- `POST /api/v1/auth/login/otp/verify/` : vérification du code OTP et émission des jetons JWT (access/refresh), en répliquant les contrôles de sécurité et le format de réponse de l'endpoint `POST /api/v1/auth/login/phone/` existant.

Cette fonctionnalité remplace le contournement fragile actuellement utilisé (register-or-login avec mot de passe dérivé), qui provoque des `429` inutiles sur `/register/` et entre en conflit avec le changement de mot de passe.

Un point de conception est explicitement traité dans ce document : les comptes créés ou authentifiés uniquement par OTP téléphonique peuvent n'avoir aucun mot de passe utilisable (mot de passe aléatoire/inutilisable). Or plusieurs endpoints sensibles existants (changement de mot de passe, désactivation du 2FA, suppression de compte, annulation de suppression, export de données) exigent aujourd'hui la saisie du mot de passe actuel. Ce document définit le comportement attendu pour ces comptes "sans mot de passe utilisable", ainsi qu'un mécanisme dédié permettant à un tel compte de définir volontairement un premier mot de passe (via vérification OTP) pour cesser d'être un compte passwordless, sans jamais rendre cette création de mot de passe obligatoire.

## Glossary

- **OTP_Service** : le service applicatif existant (`OTPService`) responsable de générer, envoyer et vérifier les codes OTP.
- **Login_OTP_Request_View** : la nouvelle vue `POST /api/v1/auth/login/otp/request/` qui initie une connexion passwordless.
- **Login_OTP_Verify_View** : la nouvelle vue `POST /api/v1/auth/login/otp/verify/` qui finalise la connexion passwordless.
- **Login_OTP_Code** : un code OTP de type `login`, généré par OTP_Service, valide pendant une durée configurable et lié à un unique utilisateur.
- **Auto_Register_Setting** : le réglage `TENXYTE_OTP_LOGIN_AUTO_REGISTER` qui contrôle si un compte est créé automatiquement lorsque le numéro de téléphone fourni n'existe pas.
- **Feature_Enabled_Setting** : le réglage `TENXYTE_OTP_LOGIN_ENABLED` qui active ou désactive globalement la fonctionnalité de connexion OTP.
- **Passwordless_Account** : un compte utilisateur qui n'a jamais eu de mot de passe défini par son propriétaire (créé via inscription automatique passwordless, ou dont le mot de passe a été remplacé par une valeur aléatoire inutilisable), et qui ne peut donc pas fournir un mot de passe valable pour les actions sensibles.
- **Sensitive_Password_Action** : toute action existante qui exige la saisie du mot de passe actuel de l'utilisateur pour être autorisée, incluant le changement de mot de passe (`/password/change/`), la désactivation du 2FA (`/2fa/disable/`), la suppression de compte (`DELETE /me/`), la demande/annulation de suppression de compte et l'export des données utilisateur.
- **OTP_Reauth_Challenge** : une vérification OTP de type `login` utilisée comme preuve d'identité alternative au mot de passe, pour un Passwordless_Account, lors d'une Sensitive_Password_Action.
- **Account_Status_Checks** : l'ensemble des contrôles de sécurité existants effectués sur un compte lors de l'authentification (compte actif, non banni, non verrouillé).
- **JWT_Service** : le service Core existant qui génère les paires de jetons access/refresh.
- **Set_Initial_Password_Operation** : l'opération dédiée par laquelle un Passwordless_Account définit volontairement son premier mot de passe, faisant passer ce compte du statut Passwordless_Account à celui de compte avec mot de passe.
- **Core** : la couche applicative framework-agnostic existante (`tenxyte.core` / `tenxyte.ports`) qui définit les ports (interfaces de repository, service JWT, etc.) indépendamment de Django.
- **Django_Adapter** : la couche d'implémentation existante (`tenxyte.adapters.django`, `tenxyte.views`, `tenxyte.serializers`, `tenxyte.models`) qui relie le Core à Django/DRF.
- **Existing_Public_Contract** : l'ensemble des endpoints, formats de requête/réponse, codes HTTP, réglages, migrations et comportements déjà documentés ou couverts par des tests avant l'introduction de cette fonctionnalité.

## Requirements

### Requirement 1: Génération et vérification d'un code OTP de type connexion

**User Story:** En tant que système d'authentification, je veux disposer d'un type d'OTP dédié à la connexion, afin de pouvoir authentifier un utilisateur par téléphone sans mot de passe.

#### Acceptance Criteria

1. THE OTP_Service SHALL provide a method to generate a Login_OTP_Code for a given user, invalidating any previously unused Login_OTP_Code for that user.
2. WHEN a Login_OTP_Code is generated for a user, THE OTP_Service SHALL set its validity duration to the value configured in `TENXYTE_OTP_LOGIN_VALIDITY_MINUTES`.
3. THE OTP_Service SHALL provide a method to verify a Login_OTP_Code against a user-supplied code, returning a success flag and an error message.
4. WHEN a supplied code matches a valid, unexpired, unused Login_OTP_Code within the allowed attempt count, THE OTP_Service SHALL mark that Login_OTP_Code as used and report success.
5. IF a supplied code does not match, is expired, or has exceeded the maximum attempt count, THEN THE OTP_Service SHALL report failure with a descriptive error message and SHALL NOT mark the account as authenticated.
6. THE OTP_Service SHALL accept `login` as a valid value for the OTP type field used to store Login_OTP_Code records.

### Requirement 2: Demande de code OTP de connexion

**User Story:** En tant qu'utilisateur, je veux demander un code OTP de connexion avec mon numéro de téléphone, afin de me connecter sans mot de passe.

#### Acceptance Criteria

1. WHERE Feature_Enabled_Setting is disabled, THE Login_OTP_Request_View SHALL reject every request without generating or sending a Login_OTP_Code.
2. WHEN Feature_Enabled_Setting is enabled and a request to Login_OTP_Request_View provides a phone country code and phone number, THE Login_OTP_Request_View SHALL validate that both fields are present and correctly formatted before proceeding.
3. IF the request is missing a required field or the phone fields are malformed, THEN THE Login_OTP_Request_View SHALL respond with a validation error and SHALL NOT generate a Login_OTP_Code.
4. WHEN application authentication is required by configuration and no valid application is resolved from the request, THE Login_OTP_Request_View SHALL respond with an application authentication error and SHALL NOT generate a Login_OTP_Code.
5. WHEN a non-deleted user account already exists with the supplied phone country code and phone number, THE Login_OTP_Request_View SHALL generate a Login_OTP_Code for that account and send it via the phone OTP delivery channel.
6. WHERE Auto_Register_Setting is enabled and no non-deleted user account exists with the supplied phone country code and phone number, THE Login_OTP_Request_View SHALL create a new phone-only user account with `is_phone_verified` set to false, and SHALL generate and send a Login_OTP_Code for that new account.
7. WHERE Auto_Register_Setting is disabled and no non-deleted user account exists with the supplied phone country code and phone number, THE Login_OTP_Request_View SHALL respond with the same success response shape used when an account exists, and SHALL NOT send any OTP and SHALL NOT reveal that the account does not exist.
8. WHEN a Login_OTP_Code is successfully generated and sent, THE Login_OTP_Request_View SHALL respond with HTTP 200 and a body containing a message, an OTP identifier, an expiration timestamp, and the delivery channel.

### Requirement 3: Vérification du code OTP et connexion

**User Story:** En tant qu'utilisateur, je veux vérifier le code OTP reçu par téléphone, afin d'obtenir mes jetons de connexion sans mot de passe.

#### Acceptance Criteria

1. WHERE Feature_Enabled_Setting is disabled, THE Login_OTP_Verify_View SHALL reject every request completely, without any internal processing, without verifying any code, and without issuing any token.
2. WHEN Feature_Enabled_Setting is enabled and a request to Login_OTP_Verify_View provides a phone country code, phone number, and code, THE Login_OTP_Verify_View SHALL validate that all required fields are present before proceeding.
3. IF no non-deleted user account exists with the supplied phone country code and phone number, THEN THE Login_OTP_Verify_View SHALL respond with HTTP 401 and a generic invalid-code error, without revealing that the account does not exist.
4. WHEN the resolved account exists, THE Login_OTP_Verify_View SHALL verify the supplied code against that account's Login_OTP_Code using OTP_Service.
5. IF the code verification fails, THEN THE Login_OTP_Verify_View SHALL respond with HTTP 401 and an error identifying an invalid or expired code, without issuing any token.
6. WHEN the code verification succeeds, THE Login_OTP_Verify_View SHALL apply the same Account_Status_Checks used by the existing phone password login (active, not banned, not locked) before issuing any token.
7. IF Account_Status_Checks fail for a reason other than a locked account, THEN THE Login_OTP_Verify_View SHALL respond with HTTP 401 and an error describing the failed check, without issuing any token.
8. IF Account_Status_Checks determine the account is locked, THEN THE Login_OTP_Verify_View SHALL respond with HTTP 423 and an error describing the lock, without issuing any token.
9. WHEN code verification and Account_Status_Checks succeed, THE Login_OTP_Verify_View SHALL set the account's `is_phone_verified` flag to true.
10. WHERE the resolved account has a multi-factor authentication type other than none, THE Login_OTP_Verify_View SHALL require a valid `totp_code` field in the request before issuing any token, applying the same two-factor verification logic used by the existing phone password login.
11. IF a multi-factor authentication code is required but missing or invalid, THEN THE Login_OTP_Verify_View SHALL respond with HTTP 401 and a two-factor-required or invalid-code error, without issuing any token.
12. WHEN code verification, Account_Status_Checks, and any required two-factor verification succeed, THE Login_OTP_Verify_View SHALL update the account's last-login timestamp, generate a new access/refresh token pair via JWT_Service, and persist the refresh token using the same persistence logic as the existing phone password login.
13. WHEN a token pair is issued by Login_OTP_Verify_View, THE Login_OTP_Verify_View SHALL respond with HTTP 200 using the same response field structure as the existing phone password login (access token, refresh token, token type, expiration values, serialized user, requires_2fa, session identifier, device identifier).

### Requirement 4: Limitation de débit dédiée

**User Story:** En tant qu'opérateur du système, je veux que les nouveaux endpoints OTP de connexion soient limités en débit indépendamment de l'inscription et de la connexion par mot de passe, afin d'éviter les abus.

#### Acceptance Criteria

1. THE Login_OTP_Request_View SHALL apply rate limiting rules dedicated to the login OTP request flow, separate from the rate limiting rules applied to `/register/`.
2. THE Login_OTP_Verify_View SHALL apply the existing OTP verification rate limiting rules used by other OTP verification endpoints.

### Requirement 5: Configuration de la fonctionnalité

**User Story:** En tant qu'intégrateur de la librairie, je veux pouvoir activer, configurer et désactiver la connexion OTP par téléphone, afin de l'adapter à mon application.

#### Acceptance Criteria

1. THE System SHALL provide a setting to enable or disable the entire login-by-phone-OTP feature, defaulting to disabled.
2. THE System SHALL provide a setting to control whether a new account is automatically created when the supplied phone number does not match an existing account, defaulting to enabled.
3. THE System SHALL provide a setting to configure the validity duration in minutes of a Login_OTP_Code, defaulting to 10 minutes.

### Requirement 6: Comptes sans mot de passe utilisable et actions sensibles

**User Story:** En tant qu'utilisateur ayant créé mon compte uniquement par OTP téléphonique, je veux pouvoir effectuer les actions sensibles de mon compte (changer de mot de passe, désactiver le 2FA, supprimer mon compte, exporter mes données) sans connaître un mot de passe que je n'ai jamais défini, afin de ne pas être bloqué par une fonctionnalité qui suppose l'existence d'un mot de passe.

#### Acceptance Criteria

1. THE System SHALL track, for every user account, whether that account currently has a usable password defined by its owner, distinguishing a Passwordless_Account from an account with a user-defined password.
2. WHEN a new account is created through Login_OTP_Request_View auto-registration, THE System SHALL mark that account as a Passwordless_Account.
3. WHEN a Passwordless_Account completes the Set_Initial_Password_Operation defined in Requirement 7, THE System SHALL mark that account as no longer a Passwordless_Account.
4. WHEN a Sensitive_Password_Action is requested, THE System SHALL accept a valid OTP_Reauth_Challenge as an alternative to the current-password field, regardless of whether the requesting account is a Passwordless_Account.
5. IF a Sensitive_Password_Action is requested without providing either a valid current password or a valid OTP_Reauth_Challenge, THEN THE System SHALL reject the request with an error indicating that re-authentication is required.
6. WHEN an account that is not a Passwordless_Account requests a Sensitive_Password_Action using its current password, THE System SHALL continue to accept that current password exactly as it does today.
7. THE System SHALL NOT allow a Passwordless_Account to complete the existing change-password operation (which requires a current password) as a means of setting its first password; a Passwordless_Account SHALL only be able to set its first password through the Set_Initial_Password_Operation defined in Requirement 7.

### Requirement 7: Création volontaire d'un mot de passe pour un compte passwordless

**User Story:** En tant qu'utilisateur ayant un compte passwordless (créé ou authentifié uniquement par OTP téléphonique), je veux pouvoir définir un mot de passe si je le souhaite, afin de pouvoir aussi me connecter par mot de passe à l'avenir tout en gardant la possibilité de me connecter par OTP.

#### Acceptance Criteria

1. THE System SHALL provide a Set_Initial_Password_Operation, distinct from the existing change-password operation, allowing a Passwordless_Account to voluntarily define its first password.
2. THE Set_Initial_Password_Operation SHALL be optional: THE System SHALL NOT require a Passwordless_Account to define a password in order to continue authenticating via Login_OTP_Verify_View.
3. WHEN a Passwordless_Account requests the Set_Initial_Password_Operation, THE System SHALL require a valid OTP_Reauth_Challenge (a fresh Login_OTP_Code verification for that account's phone number) as proof of phone ownership, and SHALL NOT accept a current password in place of that OTP verification since a Passwordless_Account has no usable current password.
4. IF the Set_Initial_Password_Operation is requested without a valid OTP_Reauth_Challenge, THEN THE System SHALL reject the request with an error indicating that OTP verification is required, and SHALL NOT set any password.
5. WHEN the Set_Initial_Password_Operation is requested with a valid OTP_Reauth_Challenge and a new password meeting the System's existing password complexity rules, THE System SHALL set that password on the account and mark the account as no longer a Passwordless_Account.
6. IF the supplied new password does not meet the System's existing password complexity rules, THEN THE System SHALL reject the request with a validation error and SHALL NOT set any password or change the account's Passwordless_Account status.
7. WHEN an account that is not a Passwordless_Account requests the Set_Initial_Password_Operation, THE System SHALL reject the request, since that account already has a user-defined password and must use the existing change-password operation instead.
8. WHEN the Set_Initial_Password_Operation succeeds, THE System SHALL allow that account to subsequently authenticate through both the existing password-based login endpoints and Login_OTP_Verify_View.

### Requirement 8: Compatibilité ascendante et respect de l'architecture hexagonale

**User Story:** En tant que mainteneur de la librairie Tenxyte, je veux que l'ajout du login passwordless par OTP n'altère aucun comportement existant déjà validé et respecte la séparation Core/adapters en place, afin de ne pas introduire de régression ni de dette architecturale pour les intégrateurs existants.

#### Acceptance Criteria

1. THE System SHALL implement every new capability described in Requirements 1 through 7 as additive changes: existing endpoints, existing serializer fields, existing response shapes, and existing settings SHALL retain their current behavior for every request that does not opt into the new login-by-phone-OTP feature or the Set_Initial_Password_Operation.
2. WHERE Feature_Enabled_Setting is disabled (its default value), THE System SHALL behave identically, for every existing endpoint and flow, to the behavior of the System before this feature was introduced.
3. THE System SHALL NOT change the request or response shape of any existing endpoint (including `/register/`, `/login/email/`, `/login/phone/`, `/password/change/`, `/2fa/disable/`, account deletion endpoints) in a way that breaks a previously valid client request or removes a previously documented field.
4. IF an existing Sensitive_Password_Action is requested using only a valid current password and no OTP_Reauth_Challenge, THEN THE System SHALL accept it exactly as it does today, regardless of whether OTP_Reauth_Challenge support has been added.
5. THE System SHALL implement Login_OTP_Request_View, Login_OTP_Verify_View, and the Set_Initial_Password_Operation as Django_Adapter components that consume Core ports (repository and JWT service interfaces) the same way existing views such as the phone password login already do, without introducing Django-specific logic into the Core layer.
6. THE System SHALL express the new `login` Login_OTP_Code type and the Passwordless_Account tracking field as additive schema changes (new field, new choice value) delivered through a Django migration, and SHALL NOT modify or remove any existing model field, migration, or constraint.
7. THE System SHALL introduce TENXYTE_OTP_LOGIN_ENABLED, TENXYTE_OTP_LOGIN_AUTO_REGISTER, and TENXYTE_OTP_LOGIN_VALIDITY_MINUTES as new settings with safe defaults, and SHALL NOT change the default value or meaning of any existing setting.
8. THE System SHALL ensure that all automated tests passing before this feature's implementation continue to pass after this feature's implementation, and SHALL add new automated tests covering Requirements 1 through 7.

## Notes de conception ouvertes

- Requirement 6 et 7 fixent le comportement attendu (autoriser une preuve OTP en alternative au mot de passe pour les actions sensibles, et une opération dédiée de création de mot de passe initial pour les comptes passwordless), mais le mécanisme concret (nouveau champ sur le modèle `User`, format exact de l'`OTP_Reauth_Challenge`, endpoint et serializer exacts du Set_Initial_Password_Operation, endpoints exacts impactés dans `account_deletion_views.py`, `password_views.py`, `twofa_views.py`, `user_views.py`) sera détaillé en phase de conception.
- Le champ `phone_country_code` est déjà normalisé sans `+` en base ; les nouveaux endpoints doivent réutiliser `normalize_phone_country_code` et n'ajouter le `+` qu'à l'affichage, cohérent avec le reste du code.
- `PasswordResetConfirmSerializer` utilise déjà `otp_code` (et non `code`) ; les nouveaux serializers OTP de connexion doivent rester cohérents avec cette convention pour le champ code.
