# Requirements Document

## Introduction

Cette fonctionnalité ajoute la capacité de **forcer un utilisateur à changer (ou définir) son mot de passe à sa première connexion**, avant de pouvoir accéder à quoi que ce soit d'autre dans l'application. Elle couvre le cas d'usage où un compte est provisionné par un tiers :

- Un administrateur crée un compte pour un employé avec un mot de passe temporaire.
- Une organisation invite un membre (avec ou sans mot de passe temporaire).

Dans les deux cas, le compte est marqué comme devant changer son mot de passe. À la connexion, l'utilisateur reçoit un jeton d'accès **à portée restreinte** (`scope: "password_change_only"`) et la réponse de connexion signale explicitement l'obligation via un champ `must_change_password: true`. Tant que le mot de passe n'a pas été (re)défini, ce jeton restreint est refusé (HTTP 403) sur toutes les routes protégées sauf celles strictement nécessaires au changement de mot de passe. Une fois le mot de passe (re)défini, l'obligation est levée et une paire de jetons pleine portée est émise.

Cette fonctionnalité s'appuie sur l'infrastructure déjà livrée par la fonctionnalité `passwordless-phone` :

- Le modèle `User` possède déjà le champ `has_usable_password` distinguant un `Passwordless_Account` (créé/invité sans mot de passe utilisable) d'un compte doté d'un mot de passe choisi par son propriétaire.
- L'endpoint existant `POST /api/v1/auth/password/change/` sert au changement de mot de passe pour un compte doté d'un mot de passe utilisable.
- L'endpoint existant `POST /api/v1/auth/password/set-initial/` sert à la première définition de mot de passe pour un `Passwordless_Account`.
- Le décorateur `require_jwt` applique déjà un enforcement de portée (scope) : un jeton portant un claim `scope` non vide n'est accepté que sur les endpoints qui listent explicitement ce scope, sinon `403 INSUFFICIENT_SCOPE`. Le scope `2fa_setup_only` (bootstrap 2FA admin) est déjà en production et sert de modèle direct pour le nouveau scope `password_change_only`.

Le comportement est entièrement **additif et opt-in** : un nouveau champ `must_change_password` (défaut `False`), un nouveau scope de jeton, un nouveau champ de réponse, et un nouveau réglage désactivé par défaut. Aucun compte existant n'est affecté tant que le flag n'est pas positionné.

## Glossary

- **Must_Change_Password_Flag** : le nouveau champ booléen additif `must_change_password` sur le modèle `User` (défaut `False`), indiquant que l'utilisateur doit (re)définir son mot de passe avant tout autre accès.
- **Forced_Change_Account** : un compte utilisateur dont le `Must_Change_Password_Flag` vaut `True`.
- **Password_Change_Scope** : la valeur de scope `"password_change_only"` portée par le claim `scope` d'un jeton d'accès, restreignant ce jeton aux seuls endpoints du flux de changement de mot de passe.
- **Restricted_Password_Token** : un jeton d'accès émis avec le `Password_Change_Scope` pour un `Forced_Change_Account`.
- **Full_Scope_Token** : un jeton d'accès sans claim `scope` (ou avec un scope vide), accepté sur tous les endpoints, tel qu'émis aujourd'hui pour tout compte normal.
- **Feature_Enabled_Setting** : le réglage `TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` qui active ou désactive globalement l'émission et l'enforcement du `Restricted_Password_Token`, défaut désactivé.
- **Password_Change_Endpoints** : l'ensemble des endpoints autorisés pour un `Restricted_Password_Token` : `POST /api/v1/auth/password/change/` (comptes avec mot de passe utilisable) et `POST /api/v1/auth/password/set-initial/` (Passwordless_Account), plus les endpoints strictement nécessaires au déroulement du flux tels que définis en conception (au minimum la déconnexion).
- **Login_Endpoints** : les endpoints d'authentification existants qui émettent une paire de jetons : `LoginEmailView` (`/login/email/`), `LoginPhoneView` (`/login/phone/`) et `LoginOTPVerifyView` (`/login/otp/verify/`).
- **Change_Password_Operation** : l'opération existante `ChangePasswordView` (`POST /password/change/`) qui change le mot de passe d'un compte doté d'un mot de passe utilisable, après réauthentification (mot de passe courant ou OTP) via `ReauthService`.
- **Set_Initial_Password_Operation** : l'opération existante `SetInitialPasswordView` (`POST /password/set-initial/`) qui définit le premier mot de passe d'un `Passwordless_Account` après vérification d'un Login OTP, et passe `has_usable_password` à `True`.
- **Passwordless_Account** : un compte dont `has_usable_password` vaut `False` (défini par la fonctionnalité `passwordless-phone`).
- **Provisioning_Operation** : toute opération par laquelle un tiers (administrateur ou invitation d'organisation) crée un compte destiné à un autre utilisateur, avec ou sans mot de passe temporaire.
- **JWT_Service** : le service Core existant qui génère les paires de jetons access/refresh et les jetons d'accès à durée/scope personnalisés (`generate_new_token_pair`, `generate_access_token`).
- **Require_JWT_Decorator** : le décorateur existant `require_jwt` (avec son paramètre `allowed_scopes`) qui valide un jeton et applique l'enforcement de scope, exposant le scope courant via `request.jwt_scope`.
- **Core** : la couche applicative framework-agnostic existante (`tenxyte.core` / `tenxyte.ports`).
- **Django_Adapter** : la couche d'implémentation existante (`tenxyte.adapters.django`, `tenxyte.views`, `tenxyte.serializers`, `tenxyte.models`, `tenxyte.decorators`) qui relie le Core à Django/DRF.
- **Existing_Public_Contract** : l'ensemble des endpoints, formats de requête/réponse, codes HTTP, réglages, migrations et comportements déjà documentés ou couverts par des tests avant l'introduction de cette fonctionnalité.

## Requirements

### Requirement 1: Suivi de l'obligation de changer le mot de passe

**User Story:** En tant que système d'authentification, je veux mémoriser pour chaque compte s'il doit changer son mot de passe à la prochaine connexion, afin de pouvoir imposer ce changement.

#### Acceptance Criteria

1. THE System SHALL track, for every user account, a boolean Must_Change_Password_Flag indicating whether the account must set or change its password before accessing anything else, defaulting to false for every account.
2. THE System SHALL deliver the Must_Change_Password_Flag as an additive schema change (new field, default false) via a Django migration, without modifying or removing any existing model field, migration, or constraint.
3. WHEN a new account is created through a normal self-service registration flow, THE System SHALL leave the Must_Change_Password_Flag at its default value of false.
4. THE System SHALL allow a Provisioning_Operation to set the Must_Change_Password_Flag to true on the account it creates.
5. THE System SHALL treat the Must_Change_Password_Flag independently from has_usable_password, such that a Forced_Change_Account may be either a Passwordless_Account (no usable password) or an account with a usable temporary password.

### Requirement 2: Provisionnement d'un compte avec changement forcé

**User Story:** En tant qu'administrateur ou organisation, je veux créer un compte pour un autre utilisateur avec un mot de passe temporaire (ou sans mot de passe), afin qu'il définisse lui-même son mot de passe à sa première connexion.

#### Acceptance Criteria

1. WHEN a Provisioning_Operation creates an account with a temporary usable password, THE System SHALL set has_usable_password to true and the Must_Change_Password_Flag to true on that account.
2. WHEN a Provisioning_Operation creates an account without any usable password (invitation-style), THE System SHALL set has_usable_password to false and the Must_Change_Password_Flag to true on that account.
3. THE System SHALL restrict the ability to set the Must_Change_Password_Flag through a Provisioning_Operation to callers already authorized to create accounts on behalf of others, using the existing authorization checks of that provisioning path.
4. THE System SHALL NOT change the behavior of any existing self-service registration request that does not opt into forced password change.

### Requirement 3: Émission d'un jeton restreint à la connexion

**User Story:** En tant qu'utilisateur d'un compte provisionné, je veux qu'à ma connexion le système m'indique que je dois changer mon mot de passe et me donne un accès limité, afin d'être dirigé vers l'écran de changement de mot de passe.

#### Acceptance Criteria

1. WHERE Feature_Enabled_Setting is enabled AND a login through any Login_Endpoint succeeds for a Forced_Change_Account, THE System SHALL issue an access token carrying the Password_Change_Scope instead of a Full_Scope_Token.
2. WHERE Feature_Enabled_Setting is enabled AND a login through any Login_Endpoint succeeds for a Forced_Change_Account, THE System SHALL include a field must_change_password set to true in the login response body.
3. WHEN a login through any Login_Endpoint succeeds for an account whose Must_Change_Password_Flag is false, THE System SHALL issue a Full_Scope_Token and SHALL include must_change_password set to false in the login response body.
4. WHERE Feature_Enabled_Setting is disabled, THE System SHALL issue tokens for every login exactly as it did before this feature was introduced, and SHALL NOT restrict any token based on the Must_Change_Password_Flag.
5. WHEN both a forced password change and an existing admin 2FA bootstrap condition apply to the same login, THE System SHALL resolve the token scope deterministically according to a single documented precedence rule defined in the design, without issuing a token that is simultaneously ambiguous in scope.
6. THE System SHALL apply the same forced-change token logic to token issuance on token refresh, such that refreshing the tokens of a Forced_Change_Account does not grant a Full_Scope_Token while the Must_Change_Password_Flag remains true.

### Requirement 4: Restriction d'accès tant que le mot de passe n'est pas changé

**User Story:** En tant que système, je veux bloquer l'accès à toutes les routes protégées avec un jeton restreint, sauf celles nécessaires pour changer le mot de passe, afin d'imposer réellement le changement.

#### Acceptance Criteria

1. WHEN a request presents a Restricted_Password_Token to any protected endpoint that is not a Password_Change_Endpoint, THE System SHALL reject the request with HTTP 403 and a code indicating insufficient scope, without performing the endpoint's action.
2. WHEN a request presents a Restricted_Password_Token to a Password_Change_Endpoint, THE System SHALL accept the token for the purpose of that endpoint's scope check.
3. THE System SHALL continue to accept a Full_Scope_Token on every endpoint exactly as before, including on the Password_Change_Endpoints.
4. THE System SHALL expose the token's scope on the request so that endpoints can distinguish a Restricted_Password_Token from a Full_Scope_Token, reusing the existing scope-exposure mechanism.
5. THE System SHALL enforce the scope restriction using the existing Require_JWT_Decorator scope mechanism, without introducing a second, divergent enforcement path.

### Requirement 5: Levée de l'obligation après changement de mot de passe

**User Story:** En tant qu'utilisateur forcé de changer mon mot de passe, je veux qu'après avoir défini un nouveau mot de passe je récupère un accès complet, afin d'utiliser l'application normalement.

#### Acceptance Criteria

1. WHEN a Forced_Change_Account with a usable password completes the Change_Password_Operation successfully, THE System SHALL set its Must_Change_Password_Flag to false.
2. WHEN a Forced_Change_Account that is a Passwordless_Account completes the Set_Initial_Password_Operation successfully, THE System SHALL set its Must_Change_Password_Flag to false.
3. WHEN the Must_Change_Password_Flag transitions from true to false through a successful password change or initial-password set performed with a Restricted_Password_Token, THE System SHALL issue a fresh Full_Scope_Token pair in the operation's response so the user can continue without re-authenticating, mirroring the existing admin 2FA bootstrap upgrade behavior.
4. WHEN a Change_Password_Operation or Set_Initial_Password_Operation fails (invalid re-authentication, invalid OTP, non-compliant new password, or breached password), THE System SHALL leave the Must_Change_Password_Flag unchanged and SHALL NOT issue a Full_Scope_Token.
5. THE System SHALL allow a Restricted_Password_Token to reach the Change_Password_Operation for an account with a usable password and the Set_Initial_Password_Operation for a Passwordless_Account, consistent with the existing routing of those two operations by has_usable_password.
6. THE System SHALL NOT weaken any existing precondition of the Change_Password_Operation or Set_Initial_Password_Operation (current-password or OTP re-authentication, OTP proof, password complexity, breach check) when those operations are reached with a Restricted_Password_Token.

### Requirement 6: Configuration de la fonctionnalité

**User Story:** En tant qu'intégrateur de la librairie, je veux pouvoir activer ou désactiver le changement de mot de passe forcé, afin de l'adapter à mon application.

#### Acceptance Criteria

1. THE System SHALL provide Feature_Enabled_Setting to enable or disable the issuance and enforcement of the Restricted_Password_Token, defaulting to disabled.
2. WHERE Feature_Enabled_Setting is disabled, THE System SHALL still allow the Must_Change_Password_Flag to be stored and read, but SHALL NOT restrict any token or alter any login token based on that flag.
3. THE System SHALL introduce Feature_Enabled_Setting as a new setting with a safe default, and SHALL NOT change the default value or meaning of any existing setting.

### Requirement 7: Compatibilité ascendante et respect de l'architecture hexagonale

**User Story:** En tant que mainteneur de la librairie Tenxyte, je veux que l'ajout du changement de mot de passe forcé n'altère aucun comportement existant déjà validé et respecte la séparation Core/adapters en place, afin de ne pas introduire de régression ni de dette architecturale.

#### Acceptance Criteria

1. THE System SHALL implement every new capability described in Requirements 1 through 6 as additive changes: existing endpoints, existing serializer fields, existing response shapes, and existing settings SHALL retain their current behavior for every request that does not involve a Forced_Change_Account with the feature enabled.
2. WHERE Feature_Enabled_Setting is disabled (its default value) AND no account carries a true Must_Change_Password_Flag, THE System SHALL behave identically, for every existing endpoint and flow, to the behavior of the System before this feature was introduced.
3. THE System SHALL NOT change the request or response shape of any existing endpoint in a way that breaks a previously valid client request or removes a previously documented field; the must_change_password field SHALL be added as a new response field only.
4. THE System SHALL express the Must_Change_Password_Flag as an additive schema change (new field with a false default) delivered through a Django migration, and SHALL NOT modify or remove any existing model field, migration, or constraint.
5. THE System SHALL implement the token scope issuance in the Django_Adapter Login_Endpoints and refresh view by consuming the existing JWT_Service extra-claims mechanism, and SHALL implement enforcement through the existing Require_JWT_Decorator, without introducing Django-specific or scope-specific logic into the Core layer.
6. THE System SHALL reuse the existing Change_Password_Operation and Set_Initial_Password_Operation for clearing the Must_Change_Password_Flag, without creating a parallel password-change endpoint.
7. THE System SHALL ensure that all automated tests passing before this feature's implementation continue to pass after this feature's implementation, and SHALL add new automated tests covering Requirements 1 through 6.

## Notes de conception ouvertes

- Le scope `password_change_only` est modelé sur le scope `2fa_setup_only` déjà en production (`src/tenxyte/decorators.py`, `require_jwt(allowed_scopes=[...])`, `request.jwt_scope`, et l'upgrade full-scope réalisé par `TwoFactorConfirmView` après confirmation). La précédence exacte entre `2fa_setup_only` et `password_change_only` lorsqu'un admin doit à la fois configurer sa 2FA et changer son mot de passe temporaire est un point de conception (Requirement 3.5).
- L'ensemble précis des `Password_Change_Endpoints` autorisés pour un `Restricted_Password_Token` (au-delà de `/password/change/` et `/password/set-initial/`, par exemple `/logout/`, `/me/` en lecture) sera arrêté en conception (Requirement 3 du glossaire, Requirement 4.1/4.2).
- Le chemin exact de `Provisioning_Operation` (endpoint admin dédié, invitation d'organisation, ou setter réutilisant un chemin de création existant) et ses contrôles d'autorisation seront détaillés en conception (Requirement 2.3), en réutilisant les vues admin de gestion d'utilisateurs et/ou l'invitation d'organisation existantes.
- Le champ de réponse s'appelle `must_change_password` et est ajouté aux corps de réponse des `Login_Endpoints` et de `RefreshTokenView` sans retirer aucun champ existant.
