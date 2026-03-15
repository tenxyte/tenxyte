# Référence des Points de Terminaison de l'API

## Sommaire

- [Référence des Points de Terminaison de l'API](#référence-des-points-de-terminaison-de-lapi)
  - [Authentification](#authentification)
    - [`POST /register/`](#post-register)
    - [`POST /login/email/`](#post-loginemail)
    - [`POST /login/phone/`](#post-loginphone)
  - [Connexion Sociale (Multi-Fournisseur)](#connexion-sociale-multi-fournisseur)
    - [`POST /social/<provider>/`](#post-socialprovider)
    - [`GET /social/<provider>/callback/`](#get-socialprovidercallback)
  - [Lien Magique (Sans mot de passe)](#lien-magique-sans-mot-de-passe)
    - [`POST /magic-link/request/`](#post-magic-linkrequest)
    - [`GET /magic-link/verify/?token=<token>`](#get-magic-linkverifytokentoken)
    - [`POST /refresh/`](#post-refresh)
    - [`POST /logout/`](#post-logout)
    - [`POST /logout/all/` ](#post-logoutall)
  - [Vérification OTP](#vérification-otp)
    - [`POST /otp/request/` ](#post-otprequest)
    - [`POST /otp/verify/email/` ](#post-otpverifyemail)
    - [`POST /otp/verify/phone/` ](#post-otpverifyphone)
  - [Gestion des Mots de Passe](#gestion-des-mots-de-passe)
    - [`POST /password/reset/request/`](#post-passwordresetrequest)
    - [`POST /password/reset/confirm/`](#post-passwordresetconfirm)
    - [`POST /password/change/` ](#post-passwordchange)
    - [`POST /password/strength/`](#post-passwordstrength)
    - [`GET /password/requirements/`](#get-passwordrequirements)
  - [Profil Utilisateur](#profil-utilisateur)
    - [`GET /me/` ](#get-me)
    - [`PATCH /me/` ](#patch-me)
    - [`GET /me/roles/` ](#get-meroles)
  - [Authentification à Deux Facteurs (2FA)](#authentification-à-deux-facteurs-2fa)
    - [`GET /2fa/status/` ](#get-2fastatus)
    - [`POST /2fa/setup/` ](#post-2fasetup)
    - [`POST /2fa/confirm/` ](#post-2faconfirm)
    - [`POST /2fa/disable/` ](#post-2fadisable)
    - [`POST /2fa/backup-codes/` ](#post-2fabackup-codes)
  - [RBAC — Permissions](#rbac--permissions)
    - [`GET /permissions/`  `permissions.view`](#get-permissions-permissionsview)
    - [`POST /permissions/`  `permissions.manage`](#post-permissions-permissionsmanage)
    - [`GET /permissions/<id>/`  `permissions.view`](#get-permissionsid-permissionsview)
    - [`PUT /permissions/<id>/`  `permissions.manage`](#put-permissionsid-permissionsmanage)
    - [`DELETE /permissions/<id>/`  `permissions.manage`](#delete-permissionsid-permissionsmanage)
  - [RBAC — Rôles](#rbac--rôles)
    - [`GET /roles/`  `roles.view`](#get-roles-rolesview)
    - [`POST /roles/`  `roles.manage`](#post-roles-rolesmanage)
    - [`GET /roles/<id>/`  `roles.view`](#get-rolesid-rolesview)
    - [`PUT /roles/<id>/`  `roles.manage`](#put-rolesid-rolesmanage)
    - [`DELETE /roles/<id>/`  `roles.manage`](#delete-rolesid-rolesmanage)
    - [`GET /roles/<id>/permissions/`  `roles.view`](#get-rolesidpermissions-rolesview)
    - [`POST /roles/<id>/permissions/`  `roles.manage`](#post-rolesidpermissions-rolesmanage)
  - [RBAC — Rôles et Permissions de l'Utilisateur](#rbac--rôles-et-permissions-de-lutilisateur)
    - [`GET /users/<id>/roles/`  `users.manage`](#get-usersidroles-usersmanage)
    - [`POST /users/<id>/roles/`  `users.manage`](#post-usersidroles-usersmanage)
    - [`DELETE /users/<id>/roles/`  `users.manage`](#delete-usersidroles-usersmanage)
    - [`GET /users/<id>/permissions/`  `users.manage`](#get-usersidpermissions-usersmanage)
    - [`POST /users/<id>/permissions/`  `users.manage`](#post-usersidpermissions-usersmanage)
  - [Applications](#applications)
    - [`GET /applications/`  `applications.view`](#get-applications-applicationsview)
    - [`POST /applications/`  `applications.manage`](#post-applications-applicationsmanage)
    - [`GET /applications/<id>/`  `applications.view`](#get-applicationsid-applicationsview)
    - [`PUT /applications/<id>/`  `applications.manage`](#put-applicationsid-applicationsmanage)
    - [`DELETE /applications/<id>/`  `applications.manage`](#delete-applicationsid-applicationsmanage)
    - [`POST /applications/<id>/regenerate/`  `applications.manage`](#post-applicationsidregenerate-applicationsmanage)
  - [Admin — Gestion des Utilisateurs](#admin--gestion-des-utilisateurs)
    - [`GET /admin/users/`  `users.view`](#get-adminusers-usersview)
    - [`GET /admin/users/<id>/`  `users.view`](#get-adminusersid-usersview)
    - [`POST /admin/users/<id>/ban/`  `users.ban`](#post-adminusersidban-usersban)
    - [`POST /admin/users/<id>/unban/`  `users.ban`](#post-adminusersidunban-usersban)
    - [`POST /admin/users/<id>/lock/`  `users.lock`](#post-adminusersidlock-userslock)
    - [`POST /admin/users/<id>/unlock/`  `users.lock`](#post-adminusersidunlock-userslock)
  - [Admin — Sécurité](#admin--sécurité)
    - [`GET /admin/audit-logs/`  `audit.view`](#get-adminaudit-logs-auditview)
    - [`GET /admin/audit-logs/<id>/`  `audit.view`](#get-adminaudit-logsid-auditview)
    - [`GET /admin/login-attempts/`  `audit.view`](#get-adminlogin-attempts-auditview)
    - [`GET /admin/blacklisted-tokens/`  `audit.view`](#get-adminblacklisted-tokens-auditview)
    - [`POST /admin/blacklisted-tokens/cleanup/`  `security.view`](#post-adminblacklisted-tokenscleanup-securityview)
    - [`GET /admin/refresh-tokens/`  `audit.view`](#get-adminrefresh-tokens-auditview)
    - [`POST /admin/refresh-tokens/<id>/revoke/`  `security.view`](#post-adminrefresh-tokensidrevoke-securityview)
  - [Admin — RGPD](#admin--rgpd)
    - [`GET /admin/deletion-requests/`  `gdpr.view`](#get-admindeletion-requests-gdprview)
    - [`GET /admin/deletion-requests/<id>/`  `gdpr.admin`](#get-admindeletion-requestsid-gdpradmin)
    - [`POST /admin/deletion-requests/<id>/process/`  `gdpr.process`](#post-admindeletion-requestsidprocess-gdprprocess)
    - [`POST /admin/deletion-requests/process-expired/`  `gdpr.process`](#post-admindeletion-requestsprocess-expired-gdprprocess)
  - [Utilisateur — RGPD](#utilisateur--rgpd)
    - [`POST /request-account-deletion/` ](#post-request-account-deletion)
    - [`POST /confirm-account-deletion/` ](#post-confirm-account-deletion)
    - [`POST /cancel-account-deletion/` ](#post-cancel-account-deletion)
    - [`GET /account-deletion-status/` ](#get-account-deletion-status)
    - [`POST /export-user-data/` ](#post-export-user-data)
  - [Dashboard](#dashboard)
    - [`GET /dashboard/stats/`  `dashboard.view`](#get-dashboardstats-dashboardview)
    - [`GET /dashboard/auth/`  `dashboard.view`](#get-dashboardauth-dashboardview)
    - [`GET /dashboard/security/`  `dashboard.view`](#get-dashboardsecurity-dashboardview)
    - [`GET /dashboard/gdpr/`  `dashboard.view`](#get-dashboardgdpr-dashboardview)
    - [`GET /dashboard/organizations/`  `dashboard.view`](#get-dashboardorganizations-dashboardview)
  - [Organisations (optionnel)](#organisations-optionnel)
    - [`POST /organizations/` ](#post-organizations)
    - [`GET /organizations/list/` ](#get-organizationslist)
    - [`GET /organizations/detail/` ](#get-organizationsdetail)
    - [`PATCH /organizations/update/`  `org.manage`](#patch-organizationsupdate-orgmanage)
    - [`DELETE /organizations/delete/`  `org.owner`](#delete-organizationsdelete-orgowner)
    - [`GET /organizations/tree/` ](#get-organizationstree)
    - [`GET /organizations/members/` ](#get-organizationsmembers)
    - [`POST /organizations/members/add/`  `org.members.invite`](#post-organizationsmembersadd-orgmembersinvite)
    - [`PATCH /organizations/members/<user_id>/`  `org.members.manage`](#patch-organizationsmembersuserid-orgmembersmanage)
    - [`DELETE /organizations/members/<user_id>/remove/`  `org.members.remove`](#delete-organizationsmembersuseridremove-orgmembersremove)
    - [`POST /organizations/invitations/`  `org.members.invite`](#post-organizationsinvitations-orgmembersinvite)
    - [`GET /org-roles/` ](#get-org-roles)
  - [WebAuthn / Passkeys (FIDO2)](#webauthn--passkeys-fido2)
    - [`POST /webauthn/register/begin/` ](#post-webauthnregisterbegin)
    - [`POST /webauthn/register/complete/` ](#post-webauthnregistercomplete)
    - [`POST /webauthn/authenticate/begin/`](#post-webauthnauthenticatebegin)
    - [`POST /webauthn/authenticate/complete/`](#post-webauthnauthenticatecomplete)
    - [`GET /webauthn/credentials/` ](#get-webauthncredentials)
    - [`DELETE /webauthn/credentials/<id>/` ](#delete-webauthncredentialsid)
  - [Légende](#légende)

---


Tous les points de terminaison sont préfixés par votre chemin de base configuré (ex : `/api/v1/auth/`).

Chaque requête **doit** inclure les identifiants de l'application :
```
X-Access-Key: <your-access-key>
X-Access-Secret: <your-access-secret>
```

Les points de terminaison authentifiés nécessitent en plus :
```
Authorization: Bearer <access_token>
```

Les points de terminaison multi-locataires (organisations) nécessitent :
```
X-Org-Slug: <organization-slug>
```

---

## Authentification

### `POST /register/`
Enregistrer un nouvel utilisateur.

**Requête :**
```json
{
  "email": "user@example.com",
  "phone_country_code": "+1",
  "phone_number": "5551234567",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "login": false,
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`email` ou `phone_country_code` + `phone_number` est requis.
`login` : Si vrai, retourne les jetons JWT pour une connexion immédiate.
`device_info` : Informations facultatives d'empreinte numérique de l'appareil.

**Réponse `201` :**
```json
{
  "message": "Registration successful",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "phone_country_code": "+1",
    "phone_number": "5551234567",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "roles": [],
    "permissions": [],
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": null
  },
  "verification_required": {
    "email": true,
    "phone": false
  }
}
```

Si `login: true` dans la requête, inclut également :
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

### `POST /login/email/`
Connexion avec e-mail + mot de passe.

**Requête :**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "totp_code": "123456",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`totp_code` n'est requis que si la 2FA est activée.
`device_info` : Informations facultatives d'empreinte numérique de l'appareil.

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "phone": "+15551234567",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false
  }
}
```

**Réponse `401` (2FA requise) :**
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Réponse `401` (Identifiants invalides) :**
```json
{
  "error": "Invalid credentials",
  "code": "LOGIN_FAILED"
}
```

**Réponse `403` (2FA administrateur requise) :**
```json
{
  "error": "Administrators must have 2FA enabled to login.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Réponse `409` (Limite de sessions dépassée) :**
```json
{
  "error": "Session limit exceeded",
  "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
  "code": "SESSION_LIMIT_EXCEEDED"
}
```

**Réponse `423` (Compte verrouillé) :**
```json
{
  "error": "Account locked",
  "details": "Account has been locked due to too many failed login attempts.",
  "code": "ACCOUNT_LOCKED",
  "retry_after": 1800
}
```

---

### `POST /login/phone/`
Connexion avec numéro de téléphone + mot de passe.

**Requête :**
```json
{
  "phone_country_code": "+1",
  "phone_number": "5551234567",
  "password": "SecurePass123!",
  "totp_code": "123456",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`totp_code` n'est requis que si la 2FA est activée.
`device_info` : Informations facultatives d'empreinte numérique de l'appareil.

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "phone": "+15551234567",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false
  }
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "phone_country_code": ["Invalid country code format. Use +XX format."],
    "phone_number": ["Phone number must be 9-15 digits."]
  }
}
```

**Réponse `401` (2FA requise) :**
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Réponse `401` (Identifiants invalides) :**
```json
{
  "error": "Invalid credentials",
  "code": "LOGIN_FAILED"
}
```

**Réponse `403` (2FA administrateur requise) :**
```json
{
  "error": "Administrators must have 2FA enabled to login.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Réponse `409` (Limite de sessions dépassée) :**
```json
{
  "error": "Session limit exceeded",
  "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
  "code": "SESSION_LIMIT_EXCEEDED"
}
```

**Réponse `423` (Compte verrouillé) :**
```json
{
  "error": "Account locked",
  "details": "Account has been locked due to too many failed login attempts.",
  "code": "ACCOUNT_LOCKED",
  "retry_after": 1800
}
```

---

## Connexion Sociale (Multi-Fournisseur)

Nécessite une configuration du fournisseur social (Google, GitHub, Microsoft, Facebook).

### `POST /social/<provider>/`
S'authentifier via un fournisseur OAuth2.

**Fournisseurs :** `google`, `github`, `microsoft`, `facebook`

**Requête (access_token) :**
```json
{
  "access_token": "********...",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```

**Requête (code d'autorisation) :**
```json
{
  "code": "<authorization-code>",
  "redirect_uri": "https://yourapp.com/auth/callback",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```

**Requête (jeton d'ID Google) :**
```json
{
  "id_token": "<google-id-token>",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`device_info` : Informations facultatives d'empreinte numérique de l'appareil.

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "roles": [],
    "permissions": []
  },
  "message": "Authentication successful",
  "provider": "google",
  "is_new_user": false
}
```

**Réponse `400` (Fournisseur invalide) :**
```json
{
  "error": "Unsupported provider",
  "code": "INVALID_PROVIDER",
  "supported_providers": ["google", "github", "microsoft", "facebook"]
}
```

**Réponse `401` (Échec de l'authentification du fournisseur) :**
```json
{
  "error": "Provider authentication failed",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Réponse `401` (Échec de l'authentification sociale) :**
```json
{
  "error": "Social authentication failed",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

### `GET /social/<provider>/callback/`
Point de terminaison de rappel OAuth2 pour le flux de code d'autorisation.

**Paramètres de requête :**
- `code` (requis) : Code d'autorisation du fournisseur
- `redirect_uri` (requis) : URI de redirection d'origine
- `state` (facultatif) : Paramètre CSRF/état

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "roles": [],
    "permissions": []
  },
  "provider": "google",
  "is_new_user": false
}
```

**Réponse `302` (Redirection avec jetons) :**
```
Location: https://yourapp.com/auth/callback?access_token=eyJ...&refresh_token=eyJ...
```

**Réponse `400` (Fournisseur invalide) :**
```json
{
  "error": "Provider 'xyz' is not supported.",
  "code": "PROVIDER_NOT_SUPPORTED"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Authorization code is required",
  "code": "MISSING_CODE"
}
```

**Réponse `400` (redirect_uri manquant) :**
```json
{
  "error": "redirect_uri is required",
  "code": "MISSING_REDIRECT_URI"
}
```

**Réponse `400` (Erreur de rappel) :**
```json
{
  "error": "OAuth2 callback processing failed",
  "code": "CALLBACK_ERROR",
  "details": "An unexpected error occurred during authentication."
}
```

**Réponse `401` (Échec de l'échange de code) :**
```json
{
  "error": "Failed to exchange authorization code",
  "code": "CODE_EXCHANGE_FAILED"
}
```

**Réponse `401` (Échec de l'authentification du fournisseur) :**
```json
{
  "error": "Could not retrieve user data from google",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Réponse `401` (Échec de l'authentification sociale) :**
```json
{
  "error": "Social authentication failed",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

## Lien Magique (Sans mot de passe)

Nécessite `TENXYTE_MAGIC_LINK_ENABLED = True`.

### `POST /magic-link/request/`
Demander un lien magique envoyé par e-mail.

**Requête :**
```json
{
  "email": "user@example.com",
  "validation_url": "https://app.example.com/auth-magic/link/verify"
}
```

**Réponse `200` :**
```json
{
  "message": "If this email is registered, a magic link has been sent."
}
```

**Réponse `400` (URL de validation manquante) :**
```json
{
  "error": "Validation URL is required",
  "code": "VALIDATION_URL_REQUIRED"
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Too many magic link requests",
  "retry_after": 3600
}
```

---

### `GET /magic-link/verify/?token=<token>`
Vérifier un jeton de lien magique et recevoir les jetons JWT.

**Réponse `200` :**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 42,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "message": "Magic link verified successfully",
  "session_id": "uuid-string",
  "device_id": "uuid-string"
}
```

**Réponse `400` (Jeton manquant) :**
```json
{
  "error": "Token is required",
  "code": "TOKEN_REQUIRED"
}
```

**Réponse `401` (Jeton invalide/utilisé/expiré) :**
```json
{
  "error": "Invalid magic link token",
  "details": "The token provided is not valid",
  "code": "INVALID_TOKEN"
}
```

---

### `POST /refresh/`
Rafraîchir le jeton d'accès.

**Requête :**
```json
{ "refresh_token": "eyJ..." }
```

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "refresh_token": ["This field is required."]
  }
}
```

**Réponse `401` (Jeton de rafraîchissement invalide/expiré) :**
```json
{
  "error": "Refresh token expired or revoked",
  "code": "REFRESH_FAILED"
}
```

---

### `POST /logout/`
Déconnexion (révoque le jeton de rafraîchissement + met le jeton d'accès sur liste noire).

**Requête :**
```json
{ "refresh_token": "eyJ..." }
```

**En-têtes (facultatif) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{ "message": "Logged out successfully" }
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "refresh_token": ["This field is required."]
  }
}
```

---

### `POST /logout/all/` 
Déconnexion de tous les appareils.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{ "message": "Logged out from 3 devices" }
```

**Réponse `401` (Non autorisé) :**
```json
{
  "error": "Authentication credentials were not provided",
  "details": "JWT token is required"
}
```

---

## Vérification OTP

### `POST /otp/request/` 
Demander un code OTP (vérification d'e-mail ou de téléphone).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{ "otp_type": "email" }
```
`otp_type` : `"email"` ou `"phone"`

**Réponse `200` :**
```json
{
  "message": "OTP verification code sent",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email",
  "masked_recipient": "u***@example.com"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "otp_type": ["Enter a valid choice."]
  }
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Too many OTP requests",
  "retry_after": 300
}
```

---

### `POST /otp/verify/email/` 
Vérifier l'e-mail avec le code OTP.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{ "code": "123456" }
```

**Réponse `200` :**
```json
{
  "message": "Email verified successfully",
  "email_verified": true,
  "verified_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Ensure this field has no more than 6 characters."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "Invalid OTP code",
  "details": "The code provided is incorrect or has expired",
  "code": "INVALID_OTP"
}
```

---

### `POST /otp/verify/phone/` 
Vérifier le téléphone avec le code OTP.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{ "code": "123456" }
```

**Réponse `200` :**
```json
{
  "message": "Phone verified successfully",
  "phone_verified": true,
  "verified_at": "2024-01-01T12:00:00Z",
  "phone_number": "+33612345678"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Ensure this field has no more than 6 characters."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "Invalid OTP code",
  "details": "The code provided is incorrect or has expired",
  "code": "INVALID_OTP"
}
```

---

## Gestion des Mots de Passe

### `POST /password/reset/request/`
Demander un e-mail de réinitialisation de mot de passe.

**Requête (e-mail) :**
```json
{ "email": "user@example.com" }
```

**Requête (téléphone) :**
```json
{
  "phone_country_code": "+33",
  "phone_number": "612345678"
}
```

**Réponse `200` :**
```json
{
  "message": "Password reset code sent",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": "Email or phone number is required"
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Too many password reset requests",
  "retry_after": 3600
}
```

---

### `POST /password/reset/confirm/`
Confirmer la réinitialisation du mot de passe avec le code OTP.

**Requête (e-mail) :**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Requête (téléphone) :**
```json
{
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "otp_code": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Réponse `200` :**
```json
{
  "message": "Password reset successful",
  "tokens_revoked": 3,
  "password_safe": true
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "new_password": ["Password must be at least 8 characters long."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "OTP code has expired",
  "details": "Please request a new password reset code",
  "code": "OTP_EXPIRED"
}
```

---

### `POST /password/change/` 
Changer de mot de passe (nécessite le mot de passe actuel).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

**Réponse `200` :**
```json
{
  "message": "Password changed successfully",
  "password_strength": "strong",
  "sessions_revoked": 2
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "new_password": ["Password must be at least 8 characters long."]
  }
}
```

**Réponse `401` (Mot de passe actuel incorrect) :**
```json
{
  "error": "Current password is incorrect",
  "code": "INVALID_PASSWORD"
}
```

---

### `POST /password/strength/`
Vérifier la force du mot de passe sans l'enregistrer.

**Requête :**
```json
{ 
  "password": "MyPassword123!",
  "email": "user@example.com"
}
```

**Réponse `200` :**
```json
{
  "score": 4,
  "strength": "Strong",
  "is_valid": true,
  "errors": [],
  "requirements": {
    "min_length": 12,
    "require_lowercase": true,
    "require_uppercase": true,
    "require_numbers": true,
    "require_special": true
  }
}
```

**Réponse `200` (Mot de passe faible) :**
```json
{
  "score": 1,
  "strength": "Weak",
  "is_valid": false,
  "errors": [
    "Password must be at least 12 characters long.",
    "Password must contain at least one number.",
    "Password must contain at least one special character."
  ],
  "requirements": {
    "min_length": 12,
    "require_lowercase": true,
    "require_uppercase": true,
    "require_numbers": true,
    "require_special": true
  }
}
```

---

### `GET /password/requirements/`
Obtenir les exigences actuelles de la politique de mot de passe.

**Réponse `200` :**
```json
{
  "requirements": {
    "min_length": 12,
    "require_lowercase": true,
    "require_uppercase": true,
    "require_numbers": true,
    "require_special": true
  },
  "min_length": 12,
  "max_length": 128
}
```

---

## Profil Utilisateur

### `GET /me/` 
Obtenir le profil de l'utilisateur actuel.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**En-têtes (facultatif) :**
```
X-Org-Slug: organization-slug
```

**Réponse `200` :**
```json
{
  "id": 12345,
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "phone": "+33612345678",
  "avatar": "https://cdn.example.com/avatars/john.jpg",
  "bio": "Software developer passionate about security",
  "timezone": "Europe/Paris",
  "language": "fr",
  "is_active": true,
  "is_verified": true,
  "date_joined": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-20T14:22:00Z",
  "custom_fields": {
    "department": "Engineering",
    "employee_id": "EMP001"
  },
  "preferences": {
    "email_notifications": true,
    "sms_notifications": false,
    "marketing_emails": false,
    "two_factor_enabled": true
  },
  "organization_context": {
    "current_org": {
      "id": "org_abc123",
      "name": "Acme Corp",
      "slug": "acme-corp"
    },
    "roles": ["admin"],
    "permissions": ["users.view"]
  }
}
```

### `PATCH /me/` 
Mettre à jour le profil de l'utilisateur actuel.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**En-têtes (facultatif) :**
```
X-Org-Slug: organization-slug
```

**Requête :**
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "username": "janedoe",
  "phone": "+33612345678",
  "bio": "Senior developer",
  "timezone": "Europe/Paris",
  "language": "fr",
  "custom_fields": {
    "department": "Engineering"
  }
}
```

**Réponse `200` :**
```json
{
  "message": "Profile updated successfully",
  "updated_fields": ["first_name", "last_name"],
  "user": {
    "id": 12345,
    "email": "john.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "username": "janedoe",
    "phone": "+33612345678",
    "bio": "Senior developer",
    "timezone": "Europe/Paris",
    "language": "fr",
    "is_active": true,
    "is_verified": true,
    "date_joined": "2024-01-15T10:30:00Z",
    "last_login": "2024-01-20T14:22:00Z"
  },
  "verification_required": {
    "email_changed": false,
    "phone_changed": false
  }
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "phone": ["Invalid phone format"],
    "username": ["Username already taken"]
  }
}
```

---

### `GET /me/roles/` 
Obtenir les rôles et permissions de l'utilisateur actuel.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**En-têtes (facultatif) :**
```
X-Org-Slug: organization-slug
```

**Réponse `200` :**
```json
{
  "roles": ["admin", "user"],
  "permissions": ["users.view", "users.manage", "roles.view"]
}
```

---

## Authentification à Deux Facteurs (2FA)

### `GET /2fa/status/` 
Obtenir le statut 2FA de l'utilisateur actuel.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "is_enabled": false,
  "backup_codes_remaining": 0
}
```

---

### `POST /2fa/setup/` 
Initier la configuration de la 2FA. Retourne un code QR et des codes de secours.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "message": "Scan the QR code with your authenticator app, then confirm with a code.",
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "provisioning_uri": "otpauth://totp/...",
  "backup_codes": ["abc123", "def456", ...],
  "warning": "Save the backup codes securely. They will not be shown again."
}
```

**Réponse `400` (2FA déjà activée) :**
```json
{
  "error": "2FA is already enabled",
  "code": "2FA_ALREADY_ENABLED"
}
```

---

### `POST /2fa/confirm/` 
Confirmer l'activation de la 2FA avec un code TOTP.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{ "code": "123456" }
```

**Réponse `200` :**
```json
{
  "message": "2FA enabled successfully",
  "is_enabled": true
}
```

**Réponse `400` (Code invalide) :**
```json
{
  "error": "Invalid TOTP code",
  "details": "The code provided is incorrect or outside the valid time window",
  "code": "INVALID_CODE"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Code is required",
  "code": "CODE_REQUIRED"
}
```

---

### `POST /2fa/disable/` 
Désactiver la 2FA (nécessite un code TOTP ou un code de secours).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "code": "123456",
  "password": "UserP@ss123!"
}
```

**Réponse `200` :**
```json
{
  "message": "2FA disabled successfully",
  "is_enabled": false
}
```

**Réponse `400` (Code invalide) :**
```json
{
  "error": "Invalid TOTP code",
  "details": "The code provided is incorrect",
  "code": "INVALID_CODE"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Code is required",
  "code": "CODE_REQUIRED"
}
```

---

### `POST /2fa/backup-codes/` 
Régénérer les codes de secours (invalide les anciens).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{ "code": "123456" }
```

**Réponse `200` :**
```json
{
  "message": "Backup codes regenerated",
  "backup_codes": ["AB12CD34", "EF56GH78", "IJ90KL12", "MN34OP56", "QR78ST90", "UV12WX34", "YZ56AB78", "CD90EF12", "GH34IJ56", "KL78MN90"],
  "warning": "Save these codes securely. They will not be shown again."
}
```

**Réponse `400` (Code invalide) :**
```json
{
  "error": "Invalid TOTP code",
  "details": "The TOTP code provided is incorrect",
  "code": "INVALID_CODE"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "TOTP code is required",
  "code": "CODE_REQUIRED"
}
```

---

## RBAC — Permissions

### `GET /permissions/`  `permissions.view`
Lister toutes les permissions.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans le code, le nom
- `parent` : Filtrer par parent (null pour les permissions racines, ou ID du parent)
- `ordering` : Trier par code, nom, date de création (par défaut : code)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "code": "users.view",
      "name": "View users",
      "description": "Can view user list"
    }
  ]
}
```

### `POST /permissions/`  `permissions.manage`
Créer une permission.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "code": "posts.publish",
  "name": "Publish Posts",
  "description": "Can publish blog posts",
  "parent_code": "posts.manage"
}
```

**Réponse `201` :**
```json
{
  "id": "2",
  "code": "posts.publish",
  "name": "Publish Posts",
  "description": "Can publish blog posts",
  "parent": {
    "id": "1",
    "code": "posts.manage"
  },
  "children": [],
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Permission with this code already exists."]
  }
}
```

### `GET /permissions/<id>/`  `permissions.view`
Obtenir une permission.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "users.view",
  "name": "View users",
  "description": "Can view user list",
  "parent": null,
  "children": [
    {
      "id": "2",
      "code": "users.view.profile"
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

### `PUT /permissions/<id>/`  `permissions.manage`
Mettre à jour une permission.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "name": "View all users",
  "description": "Can view all users in the system",
  "parent_code": null
}
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "users.view",
  "name": "View all users",
  "description": "Can view all users in the system",
  "parent": null,
  "children": [
    {
      "id": "2",
      "code": "users.view.profile"
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "parent_code": ["Parent permission not found"]
  }
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /permissions/<id>/`  `permissions.manage`
Supprimer une permission.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "message": "Permission deleted"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

---

## RBAC — Rôles

### `GET /roles/`  `roles.view`
Lister tous les rôles.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans le code, le nom
- `is_default` : Filtrer par is_default (true/false)
- `ordering` : Trier par code, nom, date de création (par défaut : nom)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "code": "editor",
      "name": "Editor",
      "is_default": false
    }
  ]
}
```

### `POST /roles/`  `roles.manage`
Créer un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "code": "editor",
  "name": "Editor",
  "description": "Can edit content",
  "permission_codes": ["posts.edit", "posts.view"],
  "is_default": false
}
```

**Réponse `201` :**
```json
{
  "id": "1",
  "code": "editor",
  "name": "Editor",
  "description": "Can edit content",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Edit posts",
      "description": "Can edit blog posts"
    }
  ],
  "is_default": false,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Role with this code already exists."]
  }
}
```

### `GET /roles/<id>/`  `roles.view`
Obtenir un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "editor",
  "name": "Editor",
  "description": "Can edit content",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Edit posts",
      "description": "Can edit blog posts"
    }
  ],
  "is_default": false,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `PUT /roles/<id>/`  `roles.manage`
Mettre à jour un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "name": "Senior Editor",
  "description": "Can edit and publish content",
  "permission_codes": ["posts.edit", "posts.publish", "posts.view"],
  "is_default": false
}
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "editor",
  "name": "Senior Editor",
  "description": "Can edit and publish content",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Edit posts",
      "description": "Can edit blog posts"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publish posts",
      "description": "Can publish blog posts"
    }
  ],
  "is_default": false,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["Permission 'invalid.code' not found"]
  }
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /roles/<id>/`  `roles.manage`
Supprimer un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "message": "Role deleted"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `GET /roles/<id>/permissions/`  `roles.view`
Lister les permissions assignées à un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "role_id": "1",
  "role_code": "editor",
  "permissions": [
    {
      "id": "1",
      "code": "posts.publish",
      "name": "Publish Posts",
      "description": "Can publish blog posts",
      "parent": null,
      "children": [],
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `POST /roles/<id>/permissions/`  `roles.manage`
Assigner des permissions à un rôle.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "permission_codes": ["posts.edit", "posts.publish"]
}
```

**Réponse `200` :**
```json
{
  "message": "2 permission(s) added",
  "added": ["posts.edit", "posts.publish"],
  "role_code": "editor",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Edit posts",
      "description": "Can edit blog posts"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publish posts",
      "description": "Can publish blog posts"
    }
  ]
}
```

**Réponse `200` (Certaines déjà assignées) :**
```json
{
  "message": "1 permission(s) added",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "role_code": "editor",
  "permissions": [...]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["This field is required."]
  }
}
```

**Réponse `400` (Permissions non trouvées) :**
```json
{
  "error": "Some permissions not found",
  "code": "PERMISSIONS_NOT_FOUND",
  "not_found": ["invalid.permission"]
}
```

---

## RBAC — Rôles et Permissions de l'Utilisateur

### `GET /users/<id>/roles/`  `users.manage`
Lister les rôles assignés à un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "user_id": "1",
  "roles": [
    {
      "id": "1",
      "code": "editor",
      "name": "Editor",
      "is_default": false
    }
  ]
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /users/<id>/roles/`  `users.manage`
Assigner un rôle à un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "role_code": "editor"
}
```

**Réponse `200` :**
```json
{
  "message": "Role assigned",
  "roles": ["editor", "user"]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "role_code": ["This field is required."]
  }
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

**Réponse `404` (Rôle non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "ROLE_NOT_FOUND"
}
```

### `DELETE /users/<id>/roles/`  `users.manage`
Supprimer un rôle pour un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (requis) :**
- `role_code` : Code du rôle à supprimer

**Requête :**
```
DELETE /users/123/roles/?role_code=editor
```

**Réponse `200` :**
```json
{
  "message": "Role removed",
  "roles": ["user"]
}
```

**Réponse `400` (Paramètre manquant) :**
```json
{
  "error": "role_code query parameter required",
  "code": "MISSING_PARAM"
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

**Réponse `404` (Rôle non trouvé) :**
```json
{
  "error": "Role not found",
  "code": "ROLE_NOT_FOUND"
}
```

### `GET /users/<id>/permissions/`  `users.manage`
Lister les permissions directes d'un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "user_id": "1",
  "email": "user@example.com",
  "direct_permissions": [
    {
      "id": "1",
      "code": "posts.view",
      "name": "View posts",
      "description": "Can view blog posts",
      "parent": null,
      "children": [],
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "all_permissions": ["posts.view", "posts.edit", "users.view"]
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /users/<id>/permissions/`  `users.manage`
Assigner une permission directe à un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "permission_codes": ["posts.edit", "posts.publish"]
}
```

**Réponse `200` :**
```json
{
  "message": "2 permission(s) added",
  "added": ["posts.edit", "posts.publish"],
  "user_id": "1",
  "direct_permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Edit posts",
      "description": "Can edit blog posts"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publish posts",
      "description": "Can publish blog posts"
    }
  ]
}
```

**Réponse `200` (Certaines déjà assignées) :**
```json
{
  "message": "1 permission(s) added",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "user_id": "1",
  "direct_permissions": [...]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["This field is required."]
  }
}
```

**Réponse `400` (Permissions non trouvées) :**
```json
{
  "error": "Some permissions not found",
  "code": "PERMISSIONS_NOT_FOUND",
  "not_found": ["invalid.permission"]
}
```

---

## Applications

### `GET /applications/`  `applications.view`
Lister toutes les applications.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans le nom, la description
- `is_active` : Filtrer par statut actif (true/false)
- `ordering` : Trier par nom, date de création (par défaut : nom)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "app_123",
      "name": "My Client App",
      "description": "Frontend application for user dashboard",
      "access_key": "ak_abc123def456",
      "is_active": true,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### `POST /applications/`  `applications.manage`
Créer une application.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "name": "My Next.js App",
  "description": "Frontend client"
}
```

**Réponse `201` :**
```json
{
  "message": "Application created successfully",
  "application": {
    "id": "app_124",
    "name": "My Next.js App",
    "description": "Frontend client",
    "access_key": "ak_abc123def456",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "credentials": {
    "access_key": "ak_abc123def456",
    "access_secret": "as_def456ghi789"
  },
  "warning": "Save the access_secret now! It will never be shown again."
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "name": ["This field is required."]
  }
}
```

### `GET /applications/<id>/`  `applications.view`
Obtenir une application.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "app_124",
  "name": "My Next.js App",
  "description": "Frontend client application",
  "access_key": "ak_abc123def456",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `PUT /applications/<id>/`  `applications.manage`
Mettre à jour une application.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "name": "Updated App Name",
  "description": "Updated description",
  "is_active": true
}
```

**Réponse `200` :**
```json
{
  "id": "app_124",
  "name": "Updated App Name",
  "description": "Updated description",
  "access_key": "ak_abc123def456",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Validation error",
  "details": {
    "name": ["This field may not be blank."]
  }
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /applications/<id>/`  `applications.manage`
Supprimer une application.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "message": "Application \"My App\" deleted successfully"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `POST /applications/<id>/regenerate/`  `applications.manage`
Régénérer le secret d'accès de l'application.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "confirmation": "REGENERATE"
}
```

**Réponse `200` :**
```json
{
  "message": "Credentials regenerated successfully",
  "application": {
    "id": "app_124",
    "name": "My Next.js App",
    "description": "Frontend client",
    "access_key": "ak_new123def456",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T13:00:00Z"
  },
  "credentials": {
    "access_key": "ak_new123def456",
    "access_secret": "as_new789ghi012"
  },
  "warning": "Save the access_secret now! It will never be shown again.",
  "old_credentials_invalidated": true
}
```

**Réponse `400` (Confirmation requise) :**
```json
{
  "error": "Confirmation required",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

---

## Admin — Gestion des Utilisateurs

### `GET /admin/users/`  `users.view`
Lister tous les utilisateurs avec filtrage et pagination.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans l'e-mail, le prénom, le nom
- `is_active` : Filtrer par statut actif (true/false)
- `is_locked` : Filtrer par compte verrouillé (true/false)
- `is_banned` : Filtrer par compte banni (true/false)
- `is_deleted` : Filtrer par compte supprimé (true/false)
- `is_email_verified` : Filtrer par e-mail vérifié (true/false)
- `is_2fa_enabled` : Filtrer par 2FA activée (true/false)
- `role` : Filtrer par code de rôle
- `date_from` : Créé après (AAAA-MM-JJ)
- `date_to` : Créé avant (AAAA-MM-JJ)
- `ordering` : Trier par e-mail, date de création, dernière connexion, prénom
- `page` : Numéro de page
- `page_size` : Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "is_locked": false,
      "is_banned": false,
      "is_deleted": false,
      "is_email_verified": true,
      "is_phone_verified": false,
      "is_2fa_enabled": true,
      "roles": ["admin", "user"],
      "created_at": "2024-01-01T12:00:00Z",
      "last_login": "2024-01-01T13:00:00Z"
    }
  ]
}
```

### `GET /admin/users/<id>/`  `users.view`
Obtenir le profil complet d'un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "email": "user@example.com",
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_locked": false,
  "locked_until": null,
  "is_banned": false,
  "is_deleted": false,
  "deleted_at": null,
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_2fa_enabled": true,
  "is_staff": false,
  "is_superuser": false,
  "max_sessions": 5,
  "max_devices": 3,
  "roles": ["admin", "user"],
  "permissions": ["users.view", "users.manage", "posts.edit"],
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z",
  "last_login": "2024-01-01T14:00:00Z"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/ban/`  `users.ban`
Bannir un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "reason": "Terms of service violation"
}
```

**Réponse `200` :**
```json
{
  "message": "User banned successfully",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": false,
    "is_banned": true,
    "roles": ["user"],
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-01T13:00:00Z"
  }
}
```

**Réponse `400` (Déjà banni) :**
```json
{
  "error": "User already banned",
  "code": "ALREADY_BANNED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/unban/`  `users.ban`
Débannir un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```
POST /admin/users/123/unban/
```

**Réponse `200` :**
```json
{
  "message": "User unbanned successfully",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_banned": false,
    "roles": ["user"],
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-01T13:00:00Z"
  }
}
```

**Réponse `400` (Pas banni) :**
```json
{
  "error": "User is not banned",
  "code": "NOT_BANNED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/lock/`  `users.lock`
Verrouiller un compte utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "duration_minutes": 60,
  "reason": "Suspicious login activity detected"
}
```

**Réponse `200` :**
```json
{
  "message": "User locked for 60 minutes",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_locked": true,
    "locked_until": "2024-01-01T14:00:00Z",
    "roles": ["user"],
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-01T13:00:00Z"
  }
}
```

**Réponse `400` (Déjà verrouillé) :**
```json
{
  "error": "User already locked",
  "code": "ALREADY_LOCKED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/unlock/`  `users.lock`
Déverrouiller un compte utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```
POST /admin/users/123/unlock/
```

**Réponse `200` :**
```json
{
  "message": "User unlocked successfully",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_locked": false,
    "locked_until": null,
    "roles": ["user"],
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-01T13:00:00Z"
  }
}
```

**Réponse `400` (Pas verrouillé) :**
```json
{
  "error": "User is not locked",
  "code": "NOT_LOCKED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

---

## Admin — Sécurité

### `GET /admin/audit-logs/`  `audit.view`
Lister les entrées du journal d'audit.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `user_id` : Filtrer par ID utilisateur
- `action` : Filtrer par action (login, login_failed, password_change, etc.)
- `ip_address` : Filtrer par adresse IP
- `application_id` : Filtrer par ID d'application
- `date_from` : Après la date (AAAA-MM-JJ)
- `date_to` : Avant la date (AAAA-MM-JJ)
- `ordering` : Trier par created_at, action, utilisateur
- `page` : Numéro de page
- `page_size` : Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "user": "123",
      "user_email": "user@example.com",
      "action": "login",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "application": "app_456",
      "application_name": "My Client App",
      "details": {
        "success": true,
        "method": "password"
      },
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### `GET /admin/audit-logs/<id>/`  `audit.view`
Get a single audit log entry.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "user": "123",
  "user_email": "user@example.com",
  "action": "login",
  "ip_address": "127.0.0.1",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "application": "app_456",
  "application_name": "My Client App",
  "details": {
    "success": true,
    "method": "password"
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Audit log not found",
  "code": "NOT_FOUND"
}
```

### `GET /admin/login-attempts/`  `audit.view`
List login attempts.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `identifier` : Filtrer par identifiant (email/téléphone)
- `ip_address` : Filtrer par adresse IP
- `success` : Filtrer par succès/échec (true/false)
- `date_from`: After date (YYYY-MM-DD)
- `date_to`: Before date (YYYY-MM-DD)
- `ordering`: Trier par created_at, identifier, ip_address
- `page`: Numéro de page
- `page_size`: Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "identifier": "user@example.com",
      "ip_address": "127.0.0.1",
      "application": "app_456",
      "success": false,
      "failure_reason": "Invalid password",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### `GET /admin/blacklisted-tokens/`  `audit.view`
List active blacklisted tokens.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `user_id`: Filtrer par ID utilisateur
- `reason`: Filtrer par raison (logout, password_change, security)
- `expired`: Filtrer par expiration (true/false)
- `ordering`: Trier par blacklisted_at, expires_at
- `page`: Numéro de page
- `page_size`: Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "token_jti": "jti123456789",
      "user": "123",
      "user_email": "user@example.com",
      "blacklisted_at": "2024-01-01T12:00:00Z",
      "expires_at": "2024-01-01T18:00:00Z",
      "reason": "logout",
      "is_expired": false
    }
  ]
}
```

### `POST /admin/blacklisted-tokens/cleanup/`  `security.view`
Remove expired blacklisted tokens.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```
POST /admin/blacklisted-tokens/cleanup/
```

**Réponse `200` :**
```json
{
  "message": "10 expired tokens cleaned up",
  "deleted_count": 10
}
```

### `GET /admin/refresh-tokens/`  `audit.view`
List active refresh tokens.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `user_id`: Filtrer par ID utilisateur
- `application_id`: Filtrer par ID d'application
- `is_revoked`: Filtrer par révocation (true/false)
- `expired`: Filtrer par expiration (true/false)
- `ordering`: Trier par created_at, expires_at, last_used_at
- `page`: Numéro de page
- `page_size`: Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "user": "123",
      "user_email": "user@example.com",
      "application": "app_456",
      "application_name": "My Client App",
      "device_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "ip_address": "127.0.0.1",
      "is_revoked": false,
      "is_expired": false,
      "expires_at": "2024-02-01T12:00:00Z",
      "created_at": "2024-01-01T12:00:00Z",
      "last_used_at": "2024-01-01T13:00:00Z"
    }
  ]
}
```

### `POST /admin/refresh-tokens/<id>/revoke/`  `security.view`
Revoke a specific refresh token.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```
POST /admin/refresh-tokens/123/revoke/
```

**Réponse `200` :**
```json
{
  "message": "Token revoked successfully",
  "token": {
    "id": "1",
    "user": "123",
    "user_email": "user@example.com",
    "application": "app_456",
    "application_name": "My Client App",
    "device_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "ip_address": "127.0.0.1",
    "is_revoked": true,
    "is_expired": false,
    "expires_at": "2024-02-01T12:00:00Z",
    "created_at": "2024-01-01T12:00:00Z",
    "last_used_at": "2024-01-01T13:00:00Z"
  }
}
```

**Réponse `400` (Déjà révoqué) :**
```json
{
  "error": "Token already revoked",
  "code": "ALREADY_REVOKED"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Refresh token not found",
  "code": "NOT_FOUND"
}
```

---

## Admin — GDPR

### `GET /admin/deletion-requests/`  `gdpr.view`
List account deletion requests.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `user_id`: Filtrer par ID utilisateur
- `status`: Filtrer par statut (pending, confirmation_sent, confirmed, completed, cancelled)
- `date_from` : Date de demande après le (AAAA-MM-JJ)
- `date_to` : Date de demande avant le (AAAA-MM-JJ)
- `grace_period_expiring`: Filtrer par expiration de la période de grâce (true/false)
- `ordering`: Trier par requested_at, grace_period_ends_at, status
- `page`: Numéro de page
- `page_size`: Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "user": "123",
      "user_email": "user@example.com",
      "status": "pending",
      "requested_at": "2024-01-01T12:00:00Z",
      "confirmed_at": null,
      "grace_period_ends_at": "2024-01-31T12:00:00Z",
      "completed_at": null,
      "ip_address": "127.0.0.1",
      "reason": "No longer need the account",
      "admin_notes": null,
      "processed_by": null,
      "processed_by_email": null,
      "is_grace_period_expired": false
    }
  ]
}
```

### `GET /admin/deletion-requests/<id>/`  `gdpr.admin`
Get a deletion request.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "user": "123",
  "user_email": "user@example.com",
  "status": "pending",
  "requested_at": "2024-01-01T12:00:00Z",
  "confirmed_at": null,
  "grace_period_ends_at": "2024-01-31T12:00:00Z",
  "completed_at": null,
  "ip_address": "127.0.0.1",
  "reason": "No longer need the account",
  "admin_notes": null,
  "processed_by": null,
  "processed_by_email": null,
  "is_grace_period_expired": false
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Deletion request not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/<id>/process/`  `gdpr.process`
Process (execute) a deletion request.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "confirmation": "PERMANENTLY DELETE",
  "admin_notes": "Processed per user request - GDPR compliance"
}
```

**Réponse `200` :**
```json
{
  "message": "Account deletion processed successfully",
  "deletion_completed": true,
  "processed_at": "2024-01-15T10:30:00Z",
  "data_anonymized": true,
  "audit_log_id": "123",
  "user_notified": true,
  "request": {
    "id": "1",
    "user": "123",
    "user_email": "user@example.com",
    "status": "completed",
    "requested_at": "2024-01-01T12:00:00Z",
    "confirmed_at": "2024-01-02T12:00:00Z",
    "grace_period_ends_at": "2024-01-31T12:00:00Z",
    "completed_at": "2024-01-15T10:30:00Z",
    "ip_address": "127.0.0.1",
    "reason": "No longer need the account",
    "admin_notes": "Processed per user request - GDPR compliance",
    "processed_by": "456",
    "processed_by_email": "admin@example.com",
    "is_grace_period_expired": false
  }
}
```

**Réponse `400` (Confirmation requise) :**
```json
{
  "error": "Explicit confirmation required",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Réponse `400` (Non confirmé) :**
```json
{
  "error": "Cannot process request with status \"pending\". Only confirmed requests can be processed.",
  "code": "REQUEST_NOT_CONFIRMED"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Deletion request not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/process-expired/`  `gdpr.process`
Process all expired grace period deletions.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```
POST /admin/deletion-requests/process-expired/
```

**Réponse `200` :**
```json
{
  "message": "5 deletion(s) processed, 0 failed",
  "processed": 5,
  "failed": 0
}
```

---

## User — GDPR

### `POST /request-account-deletion/` 
Demander la suppression du compte (démarre la période de grâce).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "password": "current_password",
  "otp_code": "123456",
  "reason": "No longer using the service"
}
```

**Réponse `201` :**
```json
{
  "message": "Account deletion request created successfully",
  "deletion_request_id": 123,
  "scheduled_deletion_date": "2024-02-15T10:30:00Z",
  "grace_period_days": 30,
  "cancellation_token": "cancel_abc123def456",
  "data_retention_policy": {
    "anonymization_after": "30 days",
    "final_deletion_after": "90 days"
  }
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

**Réponse `400` (Déjà en attente) :**
```json
{
  "error": "Account deletion already pending",
  "code": "DELETION_ALREADY_PENDING",
  "existing_request": {
    "scheduled_deletion_date": "2024-02-15T10:30:00Z",
    "cancellation_token": "cancel_abc123"
  }
}
```

### `POST /confirm-account-deletion/` 
Confirm account deletion request.

**Requête :**
```json
{
  "token": "confirm_abc123def456"
}
```

**Réponse `200` :**
```json
{
  "message": "Account deletion confirmed successfully",
  "deletion_confirmed": true,
  "grace_period_ends": "2024-02-15T10:30:00Z",
  "cancellation_instructions": "Use the cancellation token from the initial request to cancel before the grace period ends."
}
```

**Réponse `400` (Jeton requis) :**
```json
{
  "error": "Confirmation token is required"
}
```

**Réponse `400` (Jeton invalide) :**
```json
{
  "error": "Invalid confirmation token",
  "code": "INVALID_TOKEN"
}
```

**Réponse `410` (Jeton expiré) :**
```json
{
  "error": "Confirmation token has expired",
  "code": "TOKEN_EXPIRED",
  "expired_at": "2024-01-16T10:30:00Z"
}
```

### `POST /cancel-account-deletion/` 
Cancel a pending deletion request.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "password": "CurrentPassword123!"
}
```

**Réponse `200` :**
```json
{
  "message": "Account deletion cancelled successfully",
  "deletion_cancelled": true,
  "account_reactivated": true,
  "cancellation_time": "2024-01-15T14:30:00Z",
  "security_note": "Your account has been reactivated and you can continue using the service normally."
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

**Réponse `404` (Aucune suppression en attente) :**
```json
{
  "error": "No pending deletion request found",
  "code": "NO_PENDING_DELETION"
}
```

### `GET /account-deletion-status/` 
Get the status of the current deletion request.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "total_requests": 2,
  "active_request": {
    "id": "123",
    "status": "pending",
    "requested_at": "2024-01-15T10:30:00Z",
    "grace_period_ends_at": "2024-02-14T10:30:00Z",
    "days_remaining": 15
  },
  "history": [
    {
      "id": "123",
      "status": "pending",
      "requested_at": "2024-01-15T10:30:00Z",
      "confirmed_at": null,
      "completed_at": null,
      "reason": "No longer using the service"
    },
    {
      "id": "100",
      "status": "cancelled",
      "requested_at": "2023-12-01T09:00:00Z",
      "confirmed_at": null,
      "completed_at": "2023-12-02T10:00:00Z",
      "reason": "Changed mind"
    }
  ]
}
```

### `POST /export-user-data/` 
Export all personal data (GDPR Article 20).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "password": "CurrentPassword123!"
}
```

**Réponse `200` :**
```json
{
  "user_info": {
    "id": "123",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-15T10:30:00Z"
  },
  "roles": [
    {
      "id": "1",
      "name": "user",
      "description": "Standard user role"
    }
  ],
  "permissions": [
    "profile.view",
    "profile.edit"
  ],
  "applications": [
    {
      "id": "app_456",
      "name": "My Client App",
      "created_at": "2024-01-05T09:00:00Z"
    }
  ],
  "audit_logs": [
    {
      "action": "login",
      "timestamp": "2024-01-15T10:30:00Z",
      "ip_address": "127.0.0.1"
    }
  ],
  "export_metadata": {
    "exported_at": "2024-01-15T14:30:00Z",
    "export_format": "json",
    "total_records": 15,
    "data_retention_policy": "Available for 30 days"
  }
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

---

## Tableau de bord

Tous les points de terminaison du tableau de bord nécessitent la permission `dashboard.view`.

### `GET /dashboard/stats/`  `dashboard.view`
Statistiques globales multi-modules.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `period` : Période d'analyse (7d, 30d, 90d) - par défaut : 7d
- `compare` : Inclure la comparaison avec la période précédente (true/false)
- `X-Org-Slug` : Slug de l'organisation pour filtrer par organisation

**Réponse `200` :**
```json
{
  "summary": {
    "total_users": 1500,
    "active_users": 1200,
    "total_organizations": 25,
    "total_applications": 85,
    "active_sessions": 240,
    "pending_deletions": 3
  },
  "trends": {
    "user_growth": 0.15,
    "login_success_rate": 0.95,
    "application_usage": 0.08,
    "security_incidents": 0.02
  },
  "organization_context": {
    "current_org": {
      "id": "org_123",
      "name": "Acme Corp",
      "user_count": 150
    },
    "org_users_only": true
  },
  "charts": {
    "daily_logins": [
      {"date": "2024-01-09", "count": 350},
      {"date": "2024-01-10", "count": 380}
    ],
    "user_registrations": [
      {"date": "2024-01-09", "count": 15},
      {"date": "2024-01-10", "count": 18}
    ],
    "security_events": [
      {"date": "2024-01-09", "count": 5},
      {"date": "2024-01-10", "count": 3}
    ]
  }
}
```

### `GET /dashboard/auth/`  `dashboard.view`
Statistiques détaillées d'authentification (taux de connexion, stats des jetons, graphiques).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "login_stats": {
    "today": {
      "total": 350,
      "success_count": 338,
      "failed_count": 12,
      "success_rate": 0.966
    },
    "this_week": {
      "total": 2450,
      "success_count": 2365,
      "failed_count": 85,
      "success_rate": 0.965
    },
    "this_month": {
      "total": 10500,
      "success_count": 10185,
      "failed_count": 315,
      "success_rate": 0.970
    }
  },
  "login_by_method": {
    "password": 320,
    "social_google": 25,
    "social_github": 5
  },
  "registration_stats": {
    "today": 15,
    "this_week": 95,
    "this_month": 420
  },
  "token_stats": {
    "active_refresh_tokens": 240,
    "blacklisted_tokens": 8,
    "expired_today": 12
  },
  "top_login_failure_reasons": [
    {"reason": "Invalid password", "count": 45},
    {"reason": "Account not found", "count": 28},
    {"reason": "Account locked", "count": 12}
  ],
  "charts": {
    "logins_per_day_7d": [
      {"date": "2024-01-09", "success": 338, "failed": 12},
      {"date": "2024-01-10", "success": 355, "failed": 15}
    ]
  }
}
```

### `GET /dashboard/security/`  `dashboard.view`
Statistiques de sécurité (résumé d'audit, jetons mis sur liste noire, activité suspecte).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "audit_summary_24h": {
    "total_events": 1250,
    "login_attempts": 350,
    "failed_logins": 12,
    "password_changes": 8,
    "account_locks": 2
  },
  "blacklisted_tokens": {
    "active": 8,
    "expired_today": 12,
    "total_created_24h": 5
  },
  "suspicious_activity": {
    "last_24h": 3,
    "last_7d": 18,
    "top_ips": [
      {"ip_address": "192.168.1.100", "events": 15},
      {"ip_address": "10.0.0.50", "events": 8}
    ]
  },
  "account_security": {
    "locked_accounts": 2,
    "banned_accounts": 5,
    "2fa_adoption_rate": 0.35,
    "password_changes_today": 8
  }
}
```

### `GET /dashboard/gdpr/`  `dashboard.view`
Statistiques de conformité RGPD.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "deletion_requests": {
    "total": 18,
    "by_status": {
      "pending": 3,
      "confirmation_sent": 2,
      "confirmed": 5,
      "completed": 15,
      "cancelled": 2
    },
    "grace_period_expiring_7d": 2
  },
  "data_exports": {
    "total_today": 2,
    "total_this_month": 8
  }
}
```

### `GET /dashboard/organizations/`  `dashboard.view`
Statistiques des organisations (uniquement si `TENXYTE_ORGANIZATIONS_ENABLED=True`).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` (Activé) :**
```json
{
  "enabled": true,
  "total_organizations": 45,
  "active": 40,
  "with_sub_orgs": 12,
  "members": {
    "total": 382,
    "avg_per_org": 8.5,
    "by_role": {
      "owner": 45,
      "admin": 90,
      "member": 247
    }
  },
  "top_organizations": [
    {
      "name": "Acme Corp",
      "slug": "acme-corp",
      "members": 25
    },
    {
      "name": "Tech Startup",
      "slug": "tech-startup",
      "members": 18
    }
  ]
}
```

**Réponse `200` (Désactivé) :**
```json
{
  "enabled": false
}
```

---

## Organisations (optionnel)

Activez avec `TENXYTE_ORGANIZATIONS_ENABLED = True`.

Tous les points de terminaison d'organisation nécessitent l'en-tête `X-Org-Slug` pour identifier l'organisation cible :
```
X-Org-Slug: acme-corp
```

### `POST /organizations/` 
Créer une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Technology company specializing in software solutions",
  "parent_id": null,
  "metadata": {
    "industry": "technology",
    "size": "medium"
  },
  "max_members": 100
}
```

**Réponse `201` :**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Technology company specializing in software solutions",
  "created_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "member_count": 1,
  "max_members": 100,
  "parent": null,
  "metadata": {
    "industry": "technology",
    "size": "medium"
  }
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "slug": ["Organization with this slug already exists"],
  "parent_id": ["Parent organization not found"]
}
```

### `GET /organizations/list/` 
Lister les organisations auxquelles l'utilisateur actuel appartient.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans le nom et le slug
- `is_active` : Filtrer par statut actif (true/false)
- `parent` : Filtrer par parent (null = organisations racines)
- `ordering` : Trier par nom, slug, date de création (avec - pour l'ordre décroissant)
- `page` : Numéro de page
- `page_size` : Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Acme Corp",
      "slug": "acme-corp",
      "description": "Technology company specializing in software solutions",
      "member_count": 15,
      "max_members": 100,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "Tech Startup",
      "slug": "tech-startup",
      "description": "Innovative tech startup",
      "member_count": 8,
      "max_members": 50,
      "is_active": true,
      "created_at": "2024-01-20T14:15:00Z"
    }
  ]
}
```

### `GET /organizations/detail/` 
Obtenir les détails de l'organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Réponse `200` :**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Technology company specializing in software solutions",
  "metadata": {
    "industry": "technology",
    "size": "medium"
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:15:00Z",
  "member_count": 15,
  "max_members": 100,
  "parent": null,
  "children": [
    {
      "id": 5,
      "name": "Acme Subsidiary",
      "slug": "acme-subsidiary"
    }
  ],
  "user_role": "owner",
  "user_permissions": [
    "org.manage",
    "org.members.invite",
    "org.members.manage"
  ]
}
```

**Réponse `403` (Pas membre) :**
```json
{
  "error": "Access denied: You are not a member of this organization",
  "code": "NOT_MEMBER"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Organization not found",
  "code": "NOT_FOUND"
}
```

### `PATCH /organizations/update/`  `org.manage`
Mettre à jour une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Requête :**
```json
{
  "name": "Acme Corporation",
  "slug": "acme-corporation",
  "description": "Updated technology company description",
  "parent_id": null,
  "metadata": {
    "industry": "technology",
    "size": "large"
  },
  "max_members": 200,
  "is_active": true
}
```

**Réponse `200` :**
```json
{
  "id": 1,
  "name": "Acme Corporation",
  "slug": "acme-corporation",
  "description": "Updated technology company description",
  "updated_at": "2024-01-20T15:30:00Z",
  "is_active": true,
  "member_count": 15,
  "max_members": 200,
  "parent": null,
  "metadata": {
    "industry": "technology",
    "size": "large"
  }
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Cannot set max_members below current member count",
  "code": "INVALID_MEMBER_LIMIT"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "You don't have permission to manage this organization",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

### `DELETE /organizations/delete/`  `org.owner`
Supprimer une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Réponse `200` :**
```json
{
  "message": "Organization deleted successfully"
}
```

**Réponse `400` (A des organisations filles) :**
```json
{
  "error": "Cannot delete organization with child organizations",
  "code": "HAS_CHILDREN"
}
```

**Réponse `403` (Pas propriétaire) :**
```json
{
  "error": "Only organization owners can delete organizations",
  "code": "NOT_OWNER"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Organization not found",
  "code": "NOT_FOUND"
}
```

### `GET /organizations/tree/` 
Obtenir l'arbre complet de la hiérarchie de l'organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Réponse `200` :**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "depth": 0,
  "is_root": true,
  "member_count": 25,
  "children": [
    {
      "id": 5,
      "name": "Acme Subsidiary",
      "slug": "acme-subsidiary",
      "depth": 1,
      "is_root": false,
      "member_count": 8,
      "children": [
        {
          "id": 12,
          "name": "Acme Team",
          "slug": "acme-team",
          "depth": 2,
          "is_root": false,
          "member_count": 3,
          "children": []
        }
      ]
    },
    {
      "id": 6,
      "name": "Acme Division",
      "slug": "acme-division",
      "depth": 1,
      "is_root": false,
      "member_count": 12,
      "children": []
    }
  ]
}
```

### `GET /organizations/members/` 
Lister les membres de l'organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Paramètres de requête (facultatif) :**
- `search` : Recherche dans l'e-mail, le prénom, le nom
- `role` : Filtrer par rôle (owner, admin, member)
- `status` : Filtrer par statut (active, inactive, pending)
- `ordering` : Trier par joined_at, user.email, rôle
- `page` : Numéro de page
- `page_size` : Éléments par page (max 100)

**Réponse `200` :**
```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 42,
        "email": "admin@acme.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "role": "admin",
      "role_display": "Administrator",
      "permissions": [
        "org.manage",
        "org.members.invite",
        "org.members.manage"
      ],
      "inherited_permissions": [],
      "effective_permissions": [
        "org.manage",
        "org.members.invite",
        "org.members.manage"
      ],
      "joined_at": "2024-01-15T10:30:00Z",
      "status": "active"
    },
    {
      "id": 2,
      "user": {
        "id": 43,
        "email": "user@acme.com",
        "first_name": "Jane",
        "last_name": "Smith"
      },
      "role": "member",
      "role_display": "Member",
      "permissions": [
        "org.view"
      ],
      "inherited_permissions": [
        "org.view"
      ],
      "effective_permissions": [
        "org.view"
      ],
      "joined_at": "2024-01-20T14:15:00Z",
      "status": "active"
    }
  ]
}
```

### `POST /organizations/members/add/`  `org.members.invite`
Ajouter un membre à une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Requête :**
```json
{
  "user_id": 2,
  "role_code": "member"
}
```

**Réponse `201` :**
```json
{
  "id": 25,
  "user": {
    "id": 2,
    "email": "newmember@acme.com",
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "role": "member",
  "role_display": "Member",
  "joined_at": "2024-01-20T15:30:00Z",
  "status": "active"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Cannot add owner as regular member",
  "code": "INVALID_ROLE_FOR_OWNER"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "You don't have permission to invite members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "User not found",
  "code": "USER_NOT_FOUND"
}
```

### `PATCH /organizations/members/<user_id>/`  `org.members.manage`
Mettre à jour le rôle d'un membre.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Paramètres de chemin :**
- `user_id` : ID de l'utilisateur à mettre à jour

**Requête :**
```json
{
  "role_code": "admin"
}
```

**Réponse `200` :**
```json
{
  "id": 25,
  "user": {
    "id": 2,
    "email": "member@acme.com",
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "role": "admin",
  "role_display": "Administrator",
  "updated_at": "2024-01-20T16:00:00Z"
}
```

**Réponse `400` (Impossible de rétrograder le dernier propriétaire) :**
```json
{
  "error": "Cannot demote the last owner of the organization",
  "code": "LAST_OWNER_CANNOT_BE_DEMOTED"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "You don't have permission to manage members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Membre non trouvé) :**
```json
{
  "error": "Member not found",
  "code": "MEMBER_NOT_FOUND"
}
```

### `DELETE /organizations/members/<user_id>/remove/`  `org.members.remove`
Supprimer un membre d'une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Paramètres de chemin :**
- `user_id` : ID de l'utilisateur à supprimer

**Réponse `200` :**
```json
{
  "message": "Member removed successfully"
}
```

**Réponse `400` (Impossible de supprimer le dernier propriétaire) :**
```json
{
  "error": "Cannot remove the last owner of the organization",
  "code": "LAST_OWNER_CANNOT_BE_REMOVED"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "You don't have permission to remove members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Membre non trouvé) :**
```json
{
  "error": "Member not found",
  "code": "MEMBER_NOT_FOUND"
}
```

### `POST /organizations/invitations/`  `org.members.invite`
Inviter un utilisateur dans une organisation par e-mail.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Requête :**
```json
{
  "email": "newuser@example.com",
  "role_code": "member",
  "expires_in_days": 7
}
```

**Réponse `201` :**
```json
{
  "id": 123,
  "email": "newuser@example.com",
  "role": "member",
  "role_display": "Member",
  "token": "inv_abc123def456",
  "expires_at": "2024-01-27T15:30:00Z",
  "invited_by": {
    "id": 42,
    "email": "admin@acme.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "organization": {
    "id": 1,
    "name": "Acme Corp",
    "slug": "acme-corp"
  },
  "status": "pending",
  "created_at": "2024-01-20T15:30:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "User is already a member of this organization",
  "code": "ALREADY_MEMBER"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "You don't have permission to invite members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

### `GET /org-roles/` 
Lister les rôles liés à l'organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
[
  {
    "code": "owner",
    "name": "Propriétaire",
    "description": "Contrôle total sur l'organisation",
    "weight": 100,
    "permissions": [
      {
        "code": "org.manage",
        "name": "Manage Organization",
        "description": "Can manage all organization settings"
      },
      {
        "code": "org.members.invite",
        "name": "Invite Members",
        "description": "Can invite new members to the organization"
      },
      {
        "code": "org.members.manage",
        "name": "Manage Members",
        "description": "Can manage existing members"
      },
      {
        "code": "org.members.remove",
        "name": "Remove Members",
        "description": "Can remove members from organization"
      }
    ],
    "is_system_role": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "code": "admin",
    "name": "Administrateur",
    "description": "Accès administratif sans propriété",
    "weight": 80,
    "permissions": [
      {
        "code": "org.members.invite",
        "name": "Invite Members",
        "description": "Can invite new members to the organization"
      },
      {
        "code": "org.members.manage",
        "name": "Manage Members",
        "description": "Can manage existing members"
      }
    ],
    "is_system_role": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "code": "member",
    "name": "Membre",
    "description": "Membre standard de l'organisation",
    "weight": 20,
    "permissions": [
      {
        "code": "org.view",
        "name": "View Organization",
        "description": "Can view organization details"
      }
    ],
    "is_system_role": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

## WebAuthn / Passkeys (FIDO2)

Nécessite `TENXYTE_WEBAUTHN_ENABLED = True` et `pip install py-webauthn`.

### `POST /webauthn/register/begin/` 
Commencer l'enregistrement d'une clé d'accès (passkey). Retourne un défi (challenge).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "challenge": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
  "rp": {
    "name": "Tenxyte",
    "id": "localhost:8000"
  },
  "user": {
    "id": "MTIzNDU2Nzg5MA",
    "name": "user@example.com",
    "displayName": "user@example.com"
  },
  "pubKeyCredParams": [
    {
      "type": "public-key",
      "alg": -7
    },
    {
      "type": "public-key",
      "alg": -257
    },
    {
      "type": "public-key",
      "alg": -8
    }
  ],
  "timeout": 300000,
  "authenticatorSelection": {
    "authenticatorAttachment": "platform",
    "userVerification": "preferred",
    "requireResidentKey": false
  },
  "attestation": "direct"
}
```

**Réponse `400` (WebAuthn désactivé) :**
```json
{
  "error": "WebAuthn is not enabled",
  "code": "WEBAUTHN_DISABLED"
}
```

### `POST /webauthn/register/complete/` 
Terminer l'enregistrement de la clé d'accès avec la réponse de l'authentifieur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "challenge_id": 12345,
  "credential": {
    "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "rawId": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiQTNINUQ3RTlGMUcyRzRIOEk4SjBLMUwyTTNONE81UDZRN1I4UzlUMFUxVjJXM1g0WTVaNiIsIm9yaWdpbiI6Imh0dHBzOi8vbG9jYWxob3N0OjgwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
      "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NBAAAAAAAAAAAAAAAAAAAAAAAAAAAAEGZ1bGxzY3JlZW5fYXR0ZXN0YXRpb26hYXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NBAAAAAAAAAAAAAAAAAAAAAAAAAAAAEGZ1bGxzY3JlZW5fYXR0ZXN0YXRpb24"
    },
    "type": "public-key",
    "clientExtensionResults": {}
  },
  "device_name": "iPhone 14 Pro"
}
```

**Réponse `201` :**
```json
{
  "message": "Passkey registered successfully",
  "credential": {
    "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "name": "iPhone 14 Pro",
    "created_at": "2024-01-20T16:30:00Z",
    "last_used_at": null,
    "device_type": "mobile",
    "is_active": true
  }
}
```

**Réponse `400` (Identifiant invalide) :**
```json
{
  "error": "Invalid WebAuthn credential response",
  "code": "INVALID_CREDENTIAL"
}
```

**Réponse `400` (Identifiant en double) :**
```json
{
  "error": "This credential is already registered",
  "code": "DUPLICATE_CREDENTIAL"
}
```

### `POST /webauthn/authenticate/begin/`
Commencer l'authentification par clé d'accès. Retourne un défi (challenge).

**Requête :**
```json
{
  "email": "user@example.com"
}
```

**Réponse `200` :**
```json
{
  "challenge": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
  "rpId": "localhost:8000",
  "allowCredentials": [
    {
      "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
      "type": "public-key"
    }
  ],
  "userVerification": "preferred",
  "timeout": 300000
}
```

**Réponse `200` (Mode clé résidente) :**
```json
{
  "challenge": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
  "rpId": "localhost:8000",
  "allowCredentials": [],
  "userVerification": "required",
  "timeout": 300000
}
```

**Réponse `400` (Utilisateur non trouvé) :**
```json
{
  "error": "User not found",
  "code": "USER_NOT_FOUND"
}
```

### `POST /webauthn/authenticate/complete/`
Terminer l'authentification par clé d'accès. Retourne les jetons JWT.

**Requête :**
```json
{
  "challenge_id": 12345,
  "credential": {
    "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "rawId": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiQTNINUQ3RTlGMUcyRzRIOEk4SjBLMUwyTTNONE81UDZRN1I4UzlUMFUxVjJXM1g0WTVaNiIsIm9yaWdpbiI6Imh0dHBzOi8vbG9jYWxob3N0OjgwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2UsImF1dGhlbnRpY2F0b3JEYXRhIjoiU1RaTVlJYlJibUZpYkdsemNHRnpjM2R2Y21PyVgybGtJam9pUTFWVFZFOU5SVkpmTVRJek5EVTJJaXdpYVhOemRXVmtYMlJoZEdVaU9pSXlNREkwTFRFd0xURXdWREV3T2pBd09qQXdXaUlzSW1WNGNHbHllVjlrWVhSbElqb2lNakF5TlMweE1DMHhNRlF4TURvd01Eb3dNRm9pTENKd2NtOWtkV04wSWpvaWRIbHJMVzl3WlhKaGRHOXlJaXdpYldGamFHbHVaVjltYVc1blpYSndjbWx1ZENJNklqRXlNelExTmpjNE9UQXhNak0wSW4wPQ",
      "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAAAQ",
      "signature": "MEUCIQCdwBCrP_zZyGLYQh9a5r3U9k4FzJg2dJ7L7fJgQIgYKj8pXuYqJ5fX9r8tY2L3K4J7G6H5F4Z3E2D1C0B8A",
      "userHandle": "MTIzNDU2Nzg5MA"
    },
    "type": "public-key",
    "clientExtensionResults": {}
  },
  "device_info": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
}
```

**Réponse `200` :**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 42,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "last_login": "2024-01-20T17:00:00Z"
  },
  "message": "Authentication successful",
  "credential_used": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6"
}
```

**Réponse `400` (Assertion invalide) :**
```json
{
  "error": "Invalid WebAuthn assertion",
  "code": "INVALID_ASSERTION"
}
```

**Réponse `401` (Échec de l'authentification) :**
```json
{
  "error": "Authentication failed",
  "code": "AUTH_FAILED"
}
```

### `GET /webauthn/credentials/` 
Lister les clés d'accès enregistrées pour l'utilisateur actuel.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "credentials": [
    {
      "id": 1,
      "device_name": "iPhone 14 Pro",
      "created_at": "2024-01-15T10:30:00Z",
      "last_used_at": "2024-01-20T16:45:00Z",
      "authenticator_type": "platform",
      "is_resident_key": true,
      "is_active": true
    },
    {
      "id": 2,
      "device_name": "YubiKey 5",
      "created_at": "2024-01-10T14:20:00Z",
      "last_used_at": "2024-01-18T09:15:00Z",
      "authenticator_type": "cross-platform",
      "is_resident_key": false,
      "is_active": true
    }
  ]
}
```

### `DELETE /webauthn/credentials/<id>/` 
Supprimer une clé d'accès enregistrée.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de chemin :**
- `id` : ID de la clé d'accès à supprimer

**Réponse `204` :**
(pas de contenu - suppression réussie)

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Passkey not found",
  "code": "NOT_FOUND"
}
```

## Légende

-  — Nécessite `Authorization: Bearer <access_token>`
- `permission.code` — Nécessite cette permission spécifique
