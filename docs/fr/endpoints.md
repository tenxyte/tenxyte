# Référence des Points de Terminaison (Endpoints)

## Table des Matières

- [Référence des Points de Terminaison](#référence-des-points-de-terminaison)
  - [Authentification](#authentification)
    - [`POST /register/`](#post-register)
    - [`POST /login/email/`](#post-loginemail)
    - [`POST /login/phone/`](#post-loginphone)
  - [Connexion Sociale (Multi-Fournisseurs)](#connexion-sociale-multi-fournisseurs)
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
  - [RBAC — Rôles et Permissions Utilisateur](#rbac--rôles-et-permissions-utilisateur)
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
  - [Tableau de Bord](#tableau-de-bord)
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
X-Access-Key: <votre-access-key>
X-Access-Secret: <votre-access-secret>
```

Les points de terminaison authentifiés nécessitent en plus :
```
Authorization: Bearer <access_token>
```

Les points de terminaison multi-locataires (organisations) nécessitent :
```
X-Org-Slug: <slug-organisation>
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
  "first_name": "Jean",
  "last_name": "Dupont",
  "login": false,
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`email` ou `phone_country_code` + `phone_number` est requis.
`login` : Si vrai, renvoie des jetons JWT pour une connexion immédiate.
`device_info` : Informations optionnelles sur l'empreinte numérique de l'appareil (device fingerprinting).

**Réponse `201` :**
```json
{
  "message": "Enregistrement réussi",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": "+15551234567",
    "avatar": null,
    "bio": null,
    "timezone": null,
    "language": null,
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": null,
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
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
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop"
}
```

---

### `POST /login/email/`
Connexion avec email + mot de passe.

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
`device_info` : Informations optionnelles sur l'empreinte numérique de l'appareil (device fingerprinting).

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": "+15551234567",
    "avatar": "https://cdn.example.com/avatars/user.jpg",
    "bio": null,
    "timezone": "Europe/Paris",
    "language": "fr",
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": "2023-10-02T08:30:00Z",
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
  }
}
```

**Réponse `401` (2FA requise) :**
```json
{
  "error": "Code 2FA requis",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Réponse `401` (Identifiants invalides) :**
```json
{
  "error": "Identifiants invalides",
  "code": "LOGIN_FAILED"
}
```

**Réponse `403` (2FA administrateur requise) :**
```json
{
  "error": "Les administrateurs doivent avoir la 2FA activée pour se connecter.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Réponse `409` (Limite de sessions dépassée) :**
```json
{
  "error": "Limite de sessions dépassée",
  "code": "SESSION_LIMIT_EXCEEDED",
  "details": {}
}
```

**Réponse `423` (Compte verrouillé) :**
```json
{
  "error": "Compte verrouillé suite à trop de tentatives de connexion échouées",
  "code": "ACCOUNT_LOCKED",
  "details": {}
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
`device_info` : Informations optionnelles sur l'empreinte numérique de l'appareil.

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": "+15551234567",
    "avatar": "https://cdn.example.com/avatars/user.jpg",
    "bio": null,
    "timezone": "Europe/Paris",
    "language": "fr",
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": "2023-10-02T08:30:00Z",
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
  }
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "phone_country_code": ["Format de code pays invalide. Utilisez le format +XX."],
    "phone_number": ["Le numéro de téléphone doit comporter entre 9 et 15 chiffres."]
  }
}
```

**Réponse `401` (2FA requise) :**
```json
{
  "error": "Code 2FA requis",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Réponse `401` (Identifiants invalides) :**
```json
{
  "error": "Identifiants invalides",
  "code": "LOGIN_FAILED"
}
```

**Réponse `403` (2FA administrateur requise) :**
```json
{
  "error": "Les administrateurs doivent avoir la 2FA activée pour se connecter.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Response `409` (Session limit exceeded):**
```json
{
  "error": "Session limit exceeded",
  "code": "SESSION_LIMIT_EXCEEDED",
  "details": {}
}
```

**Response `423` (Account locked):**
```json
{
  "error": "Account locked due to too many failed login attempts",
  "code": "ACCOUNT_LOCKED",
  "details": {}
}
```

---

## Connexion Sociale (Multi-Fournisseurs)

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
  "code": "<code-d-autorisation>",
  "redirect_uri": "https://votre-app.com/auth/callback",
  "code_verifier": "<vérificateur-PKCE>",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`code_verifier` : Vérificateur PKCE optionnel (RFC 7636). Requis si la requête d'autorisation incluait un `code_challenge`.

**Requête (Google ID token) :**
```json
{
  "id_token": "<google-id-token>",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`device_info` : Informations optionnelles sur l'empreinte numérique de l'appareil (device fingerprinting).

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": null,
    "avatar": "https://lh3.googleusercontent.com/a/...",
    "bio": null,
    "timezone": null,
    "language": null,
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": "2023-10-02T08:30:00Z",
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
  },
  "message": "Authentification réussie",
  "provider": "google",
  "is_new_user": false
}
```

**Réponse `400` (Fournisseur invalide) :**
```json
{
  "error": "Fournisseur non supporté",
  "code": "INVALID_PROVIDER",
  "supported_providers": ["google", "github", "microsoft", "facebook"]
}
```

**Réponse `401` (Échec de l'authentification fournisseur) :**
```json
{
  "error": "L'authentification du fournisseur a échoué",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Réponse `401` (Échec de l'authentification sociale) :**
```json
{
  "error": "L'authentification sociale a échoué",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

### `GET /social/<provider>/callback/`
Point de terminaison de rappel (callback) OAuth2 pour le flux de code d'autorisation.

**Paramètres de requête :**
- `code` (requis) : Code d'autorisation du fournisseur
- `redirect_uri` (requis) : URI de redirection d'origine
- `code_verifier` (optionnel) : Vérificateur PKCE (RFC 7636)
- `state` (optionnel) : Paramètre d'état/CSRF

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": null,
    "avatar": "https://lh3.googleusercontent.com/a/...",
    "bio": null,
    "timezone": null,
    "language": null,
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": "2023-10-02T08:30:00Z",
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
  },
  "provider": "google",
  "is_new_user": false
}
```

**Réponse `302` (Redirection avec jetons) :**
```
Location: https://votre-app.com/auth/callback?access_token=eyJ...&refresh_token=eyJ...
```

**Réponse `400` (Fournisseur invalide) :**
```json
{
  "error": "Le fournisseur 'xyz' n'est pas supporté.",
  "code": "PROVIDER_NOT_SUPPORTED"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Le code d'autorisation est requis",
  "code": "MISSING_CODE"
}
```

**Réponse `400` (redirect_uri manquant) :**
```json
{
  "error": "redirect_uri est requis",
  "code": "MISSING_REDIRECT_URI"
}
```

**Réponse `400` (Erreur de rappel) :**
```json
{
  "error": "Échec du traitement du rappel OAuth2",
  "code": "CALLBACK_ERROR",
  "details": {}
}
```

**Réponse `401` (Échec de l'échange de code) :**
```json
{
  "error": "Échec de l'échange du code d'autorisation",
  "code": "CODE_EXCHANGE_FAILED"
}
```

**Réponse `401` (Échec de l'authentification fournisseur) :**
```json
{
  "error": "Impossible de récupérer les données utilisateur de google",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Réponse `400` (URI de redirection invalide) :**
```json
{
  "error": "redirect_uri n'est pas dans la liste blanche de l'application",
  "code": "INVALID_REDIRECT_URI"
}
```

**Réponse `401` (Échec de l'authentification sociale) :**
```json
{
  "error": "L'authentification sociale a échoué",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

## Lien Magique (Sans mot de passe)

Nécessite `TENXYTE_MAGIC_LINK_ENABLED = True`.

### `POST /magic-link/request/`
Demander un lien magique envoyé par email.

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
  "message": "Si cet email est enregistré, un lien magique a été envoyé."
}
```

**Réponse `400` (URL de validation manquante) :**
```json
{
  "error": "L'URL de validation est requise",
  "code": "VALIDATION_URL_REQUIRED"
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Trop de requêtes de liens magiques",
  "retry_after": 3600
}
```

---

### `GET /magic-link/verify/?token=<token>`
Vérifier un jeton de lien magique et recevoir des jetons JWT.

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": null,
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "username": null,
    "phone": null,
    "avatar": "https://cdn.example.com/avatars/user.jpg",
    "bio": null,
    "timezone": "Europe/Paris",
    "language": "fr",
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "created_at": "2023-10-01T12:00:00Z",
    "last_login": "2023-10-02T08:30:00Z",
    "custom_fields": null,
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "marketing_emails": false
    },
    "roles": [],
    "permissions": []
  },
  "message": "Lien magique vérifié avec succès",
  "session_id": "uuid-string",
  "device_id": "uuid-string"
}
```

**Réponse `400` (Jeton manquant) :**
```json
{
  "error": "Le jeton est requis",
  "code": "TOKEN_REQUIRED"
}
```

**Réponse `401` (Jeton invalide/utilisé/expiré) :**
```json
{
  "error": "Jeton de lien magique invalide",
  "code": "INVALID_TOKEN",
  "details": {}
}
```

---

### `POST /refresh/`
Rafraîchir le jeton d'accès.

**Requête :**
```json
{ "refresh_token": "eyJ..." }
```

> **Mode cookie :** Lorsque `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, le champ `refresh_token` est optionnel. S'il est omis ou vide, le serveur lit le jeton depuis le cookie `HttpOnly` défini lors de la connexion. Dans ce mode, la réponse omet également `refresh_token` du corps JSON (il est renouvelé via `Set-Cookie`).

**Réponse `200` :**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 86400,
  "device_summary": null
}
```

**Réponse `400` (Jeton de rafraîchissement manquant) :**
```json
{
  "error": "refresh_token is required",
  "code": "MISSING_REFRESH_TOKEN"
}
```

**Réponse `401` (Jeton de rafraîchissement invalide/expiré) :**
```json
{
  "error": "Le jeton de rafraîchissement a expiré ou a été révoqué",
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

**En-têtes (optionnels) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{ "message": "Déconnexion réussie" }
```

> **Mode cookie :** Lorsque `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, le serveur efface également le cookie du jeton de rafraîchissement via `Set-Cookie` avec `max-age=0`.

**Réponse `400` (Jeton de rafraîchissement manquant) :**
```json
{
  "error": "refresh_token is required",
  "code": "MISSING_REFRESH_TOKEN"
}
```

---

### `POST /logout/all/` 
Se déconnecter de tous les appareils.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{ "message": "Déconnecté de 3 appareils" }
```

**Réponse `401` (Non autorisé) :**
```json
{
  "error": "Les identifiants d'authentification n'ont pas été fournis",
  "code": "UNAUTHORIZED",
  "details": {}
}
```


---

## Vérification OTP

### `POST /otp/request/` 
Demander un code OTP (vérification d'email ou de téléphone).

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
  "message": "Code de vérification OTP envoyé",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email",
  "masked_recipient": "u***@example.com"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "otp_type": ["Entrez un choix valide."]
  }
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Trop de requêtes OTP",
  "retry_after": 300
}
```

---

### `POST /otp/verify/email/` 
Vérifier l'email avec le code OTP.

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
  "message": "Email vérifié avec succès",
  "email_verified": true,
  "verified_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "code": ["Assurez-vous que ce champ n'a pas plus de 6 caractères."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "Code OTP invalide",
  "code": "INVALID_OTP",
  "details": {}
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
  "message": "Téléphone vérifié avec succès",
  "phone_verified": true,
  "verified_at": "2024-01-01T12:00:00Z",
  "phone_number": "+33612345678"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "code": ["Assurez-vous que ce champ n'a pas plus de 6 caractères."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "Code OTP invalide",
  "code": "INVALID_OTP",
  "details": {}
}
```

---

## Gestion des Mots de Passe

### `POST /password/reset/request/`
Demander un email de réinitialisation de mot de passe.

**Requête (email) :**
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
  "message": "Code de réinitialisation de mot de passe envoyé",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "code": "VALIDATION_ERROR",
  "details": {
    "non_field_errors": ["L'email ou le numéro de téléphone est requis"]
  }
}
```

**Réponse `429` (Limite de débit atteinte) :**
```json
{
  "error": "Trop de requêtes de réinitialisation de mot de passe",
  "retry_after": 3600
}
```

---

### `POST /password/reset/confirm/`
Confirmer la réinitialisation du mot de passe avec le code OTP.

**Requête (email) :**
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
  "message": "Réinitialisation du mot de passe réussie",
  "tokens_revoked": 3,
  "password_safe": true
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "new_password": ["Le mot de passe doit comporter au moins 8 caractères."]
  }
}
```

**Réponse `401` (Code invalide/expiré) :**
```json
{
  "error": "Le code OTP a expiré",
  "code": "OTP_EXPIRED",
  "details": {}
}
```

---

### `POST /password/change/` 
Changer le mot de passe (nécessite le mot de passe actuel).

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
  "message": "Mot de passe changé avec succès",
  "password_strength": "strong",
  "sessions_revoked": 2
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "new_password": ["Le mot de passe doit comporter au moins 8 caractères."]
  }
}
```

**Réponse `401` (Mot de passe actuel invalide) :**
```json
{
  "error": "Le mot de passe actuel est incorrect",
  "code": "INVALID_PASSWORD"
}
```

---

### `POST /password/strength/`
Vérifier la force du mot de passe sans l'enregistrer.

**Requête :**
```json
{ 
  "password": "MonMotDePasse123!",
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
    "Le mot de passe doit comporter au moins 12 caractères.",
    "Le mot de passe doit contenir au moins un chiffre.",
    "Le mot de passe doit contenir au moins un caractère spécial."
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

**En-têtes (optionnels) :**
```
X-Org-Slug: organization-slug
```

**Réponse `200` :**
```json
{
  "id": 12345,
  "email": "jean.dupont@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "username": "jeandupont",
  "phone": "+33612345678",
  "avatar": "https://cdn.example.com/avatars/john.jpg",
  "bio": "Développeur passionné par la sécurité",
  "timezone": "Europe/Paris",
  "language": "fr",
  "is_active": true,
  "is_verified": true,
  "date_joined": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-20T14:22:00Z",
  "custom_fields": {
    "department": "Ingénierie",
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

**En-têtes (optionnels) :**
```
X-Org-Slug: organization-slug
```

**Requête :**
```json
{
  "first_name": "Jean",
  "last_name": "Dupont",
  "username": "jeandupont",
  "phone": "+33612345678",
  "bio": "Développeur Senior",
  "timezone": "Europe/Paris",
  "language": "fr",
  "custom_fields": {
    "department": "Ingénierie"
  }
}
```

**Réponse `200` :**
```json
{
  "message": "Profil mis à jour avec succès",
  "updated_fields": ["first_name", "last_name"],
  "user": {
    "id": 12345,
    "email": "jean.dupont@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "username": "jeandupont",
    "phone": "+33612345678",
    "bio": "Développeur Senior",
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
  "error": "Erreur de validation",
  "details": {
    "phone": ["Format de téléphone invalide"],
    "username": ["Ce nom d'utilisateur est déjà pris"]
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

**En-têtes (optionnels) :**
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

## Authentification à deux facteurs (2FA)

### `GET /2fa/status/` 
Obtenir le statut 2FA pour l'utilisateur actuel.

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
Initier la configuration de la 2FA. Renvoie un code QR et des codes de secours.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "message": "Scannez le code QR avec votre application d'authentification, puis confirmez avec un code.",
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "provisioning_uri": "otpauth://totp/...",
  "backup_codes": ["abc123", "def456", ...],
  "warning": "Conservez les codes de secours en lieu sûr. Ils ne seront plus affichés."
}
```

**Réponse `400` (2FA déjà activée) :**
```json
{
  "error": "La 2FA est déjà activée",
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
  "message": "2FA activée avec succès",
  "is_enabled": true
}
```

**Réponse `400` (Code invalide) :**
```json
{
  "error": "Code TOTP invalide",
  "details": "Le code fourni est incorrect ou en dehors de la fenêtre temporelle valide",
  "code": "INVALID_CODE"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Le code est requis",
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
  "message": "2FA désactivée avec succès",
  "is_enabled": false
}
```
 
**Réponse `400` (Code invalide) :**
```json
{
  "error": "Code TOTP invalide",
  "details": "Le code fourni est incorrect",
  "code": "INVALID_CODE"
}
```
 
**Réponse `400` (Code manquant) :**
```json
{
  "error": "Le code est requis",
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
  "message": "Codes de secours régénérés",
  "backup_codes": ["AB12CD34", "EF56GH78", "IJ90KL12", "MN34OP56", "QR78ST90", "UV12WX34", "YZ56AB78", "CD90EF12", "GH34IJ56", "KL78MN90"],
  "warning": "Conservez ces codes en lieu sûr. Ils ne seront plus affichés."
}
```

**Réponse `400` (Code invalide) :**
```json
{
  "error": "Code TOTP invalide",
  "details": "Le code TOTP fourni est incorrect",
  "code": "INVALID_CODE"
}
```

**Réponse `400` (Code manquant) :**
```json
{
  "error": "Le code TOTP est requis",
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

**Paramètres de requête (optionnels) :**
- `search` : Recherche dans le code, le nom
- `parent` : Filtrer par parent (null pour les permissions racines, ou ID parent)
- `ordering` : Trier par code, nom, created_at (par défaut : code)

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
      "name": "Voir les utilisateurs",
      "description": "Peut voir la liste des utilisateurs"
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
  "name": "Publier des articles",
  "description": "Peut publier des articles de blog",
  "parent_code": "posts.manage"
}
```

**Réponse `201` :**
```json
{
  "id": "2",
  "code": "posts.publish",
  "name": "Publier des articles",
  "description": "Peut publier des articles de blog",
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
  "error": "Erreur de validation",
  "details": {
    "code": ["Une permission avec ce code existe déjà."]
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
  "name": "Voir les utilisateurs",
  "description": "Peut voir la liste des utilisateurs",
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
  "error": "Permission non trouvée",
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
  "name": "Voir tous les utilisateurs",
  "description": "Peut voir tous les utilisateurs du système",
  "parent_code": null
}
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "users.view",
  "name": "Voir tous les utilisateurs",
  "description": "Peut voir tous les utilisateurs du système",
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
  "error": "Erreur de validation",
  "details": {
    "parent_code": ["Permission parente non trouvée"]
  }
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Permission non trouvée",
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
  "message": "Permission supprimée"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Permission non trouvée",
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

**Paramètres de requête (optionnels) :**
- `search` : Recherche dans le code, le nom
- `is_default` : Filtrer par is_default (true/false)
- `ordering` : Trier par code, nom, created_at (par défaut : name)

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
      "name": "Éditeur",
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
  "name": "Éditeur",
  "description": "Peut éditer le contenu",
  "permission_codes": ["posts.edit", "posts.view"],
  "is_default": false
}
```

**Réponse `201` :**
```json
{
  "id": "1",
  "code": "editor",
  "name": "Éditeur",
  "description": "Peut éditer le contenu",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Éditer les articles",
      "description": "Peut éditer les articles de blog"
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
  "error": "Erreur de validation",
  "details": {
    "code": ["Un rôle avec ce code existe déjà."]
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
  "name": "Éditeur",
  "description": "Peut éditer le contenu",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Éditer les articles",
      "description": "Peut éditer les articles de blog"
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
  "error": "Rôle non trouvé",
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
  "name": "Éditeur Senior",
  "description": "Peut éditer et publier du contenu",
  "permission_codes": ["posts.edit", "posts.publish", "posts.view"],
  "is_default": false
}
```

**Réponse `200` :**
```json
{
  "id": "1",
  "code": "editor",
  "name": "Éditeur Senior",
  "description": "Peut éditer et publier du contenu",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Éditer les articles",
      "description": "Peut éditer les articles de blog"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publier les articles",
      "description": "Peut publier des articles de blog"
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
  "error": "Erreur de validation",
  "details": {
    "permission_codes": ["Permission 'invalid.code' non trouvée"]
  }
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Rôle non trouvé",
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
  "message": "Rôle supprimé"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Rôle non trouvé",
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
      "name": "Publier des articles",
      "description": "Peut publier des articles de blog",
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
  "error": "Rôle non trouvé",
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
  "message": "2 permission(s) ajoutée(s)",
  "added": ["posts.edit", "posts.publish"],
  "role_code": "editor",
  "permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Éditer les articles",
      "description": "Peut éditer les articles de blog"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publier les articles",
      "description": "Peut publier des articles de blog"
    }
  ]
}
```

**Réponse `200` (Certaines déjà assignées) :**
```json
{
  "message": "1 permission(s) ajoutée(s)",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "role_code": "editor",
  "permissions": [...]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "permission_codes": ["Ce champ est requis."]
  }
}
```

**Réponse `400` (Permissions non trouvées) :**
```json
{
  "error": "Certaines permissions n'ont pas été trouvées",
  "code": "PERMISSIONS_NOT_FOUND",
  "not_found": ["invalid.permission"]
}
```

---

## RBAC — Rôles et Permissions des Utilisateurs

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
      "name": "Éditeur",
      "is_default": false
    }
  ]
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
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
  "message": "Rôle assigné",
  "roles": ["editor", "user"]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "role_code": ["Ce champ est requis."]
  }
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
  "code": "NOT_FOUND"
}
```

**Réponse `404` (Rôle non trouvé) :**
```json
{
  "error": "Rôle non trouvé",
  "code": "ROLE_NOT_FOUND"
}
```

### `DELETE /users/<id>/roles/`  `users.manage`
Retirer un rôle à un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (requis) :**
- `role_code` : Code du rôle à retirer

**Requête :**
```
DELETE /users/123/roles/?role_code=editor
```

**Réponse `200` :**
```json
{
  "message": "Rôle retiré",
  "roles": ["user"]
}
```

**Réponse `400` (Paramètre manquant) :**
```json
{
  "error": "Le paramètre de requête role_code est requis",
  "code": "MISSING_PARAM"
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
  "code": "NOT_FOUND"
}
```

**Réponse `404` (Rôle non trouvé) :**
```json
{
  "error": "Rôle non trouvé",
  "code": "ROLE_NOT_FOUND"
}
```

### `GET /users/<id>/permissions/`  `users.manage`
Lister les permissions directes pour un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "user_id": "1",
  "email": "utilisateur@example.com",
  "direct_permissions": [
    {
      "id": "1",
      "code": "posts.view",
      "name": "Voir les articles",
      "description": "Peut voir les articles de blog",
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
  "error": "Utilisateur non trouvé",
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
  "message": "2 permission(s) ajoutée(s)",
  "added": ["posts.edit", "posts.publish"],
  "user_id": "1",
  "direct_permissions": [
    {
      "id": "1",
      "code": "posts.edit",
      "name": "Éditer les articles",
      "description": "Peut éditer les articles de blog"
    },
    {
      "id": "2",
      "code": "posts.publish",
      "name": "Publier les articles",
      "description": "Peut publier des articles de blog"
    }
  ]
}
```

**Réponse `200` (Certaines déjà assignées) :**
```json
{
  "message": "1 permission(s) ajoutée(s)",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "user_id": "1",
  "direct_permissions": [...]
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "permission_codes": ["Ce champ est requis."]
  }
}
```

**Réponse `400` (Permissions non trouvées) :**
```json
{
  "error": "Certaines permissions n'ont pas été trouvées",
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

**Paramètres de requête (optionnels) :**
- `search` : Recherche dans le nom, la description
- `is_active` : Filtrer par statut actif (true/false)
- `ordering` : Trier par nom, created_at (par défaut : name)

**Réponse `200` :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "app_123",
      "name": "Mon App Client",
      "description": "Application frontend pour le tableau de bord utilisateur",
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
  "name": "Mon App Next.js",
  "description": "Client frontend"
}
```

**Réponse `201` :**
```json
{
  "message": "Application créée avec succès",
  "application": {
    "id": "app_124",
    "name": "Mon App Next.js",
    "description": "Client frontend",
    "access_key": "ak_abc123def456",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "credentials": {
    "access_key": "ak_abc123def456",
    "access_secret": "as_def456ghi789"
  },
  "warning": "Enregistrez le code secret (access_secret) maintenant ! Il ne sera plus jamais affiché."
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "name": ["Ce champ est requis."]
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
  "name": "Mon App Next.js",
  "description": "Application client frontend",
  "access_key": "ak_abc123def456",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Application non trouvée",
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
  "name": "Nom de l'app mis à jour",
  "description": "Description mise à jour",
  "is_active": true
}
```

**Réponse `200` :**
```json
{
  "id": "app_124",
  "name": "Nom de l'app mis à jour",
  "description": "Description mise à jour",
  "access_key": "ak_abc123def456",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Erreur de validation",
  "details": {
    "name": ["Ce champ ne peut pas être vide."]
  }
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Application non trouvée",
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
  "message": "L'application \"My App\" a été supprimée avec succès"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Application non trouvée",
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
  "message": "Identifiants régénérés avec succès",
  "application": {
    "id": "app_124",
    "name": "Mon App Next.js",
    "description": "Client frontend",
    "access_key": "ak_new123def456",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T13:00:00Z"
  },
  "credentials": {
    "access_key": "ak_new123def456",
    "access_secret": "as_new789ghi012"
  },
  "warning": "Enregistrez le code secret (access_secret) maintenant ! Il ne sera plus jamais affiché.",
  "old_credentials_invalidated": true
}
```

**Réponse `400` (Confirmation requise) :**
```json
{
  "error": "Confirmation requise",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Application non trouvée",
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

**Paramètres de requête (optionnels) :**
- `search` : Recherche dans l'email, le prénom, le nom
- `is_active` : Filtrer par statut actif (true/false)
- `is_locked` : Filtrer par compte verrouillé (true/false)
- `is_banned` : Filtrer par compte banni (true/false)
- `is_deleted` : Filtrer par compte supprimé (true/false)
- `is_email_verified` : Filtrer par email vérifié (true/false)
- `is_2fa_enabled` : Filtrer par 2FA activée (true/false)
- `role` : Filtrer par code de rôle
- `date_from` : Créé après (YYYY-MM-DD)
- `date_to` : Créé avant (YYYY-MM-DD)
- `ordering` : Trier par email, created_at, last_login, first_name
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
      "email": "utilisateur@example.com",
      "first_name": "Jean",
      "last_name": "Dupont",
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
  "email": "utilisateur@example.com",
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "first_name": "Jean",
  "last_name": "Dupont",
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
  "error": "Utilisateur non trouvé",
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
  "reason": "Violation des conditions d'utilisation"
}
```

**Réponse `200` :**
```json
{
  "message": "Utilisateur banni avec succès",
  "user": {
    "id": "1",
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
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
  "error": "L'utilisateur est déjà banni",
  "code": "ALREADY_BANNED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
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
  "message": "Utilisateur débanni avec succès",
  "user": {
    "id": "1",
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
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
  "error": "L'utilisateur n'est pas banni",
  "code": "NOT_BANNED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/lock/`  `users.lock`
Verrouiller le compte d'un utilisateur.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "duration_minutes": 60,
  "reason": "Activité de connexion suspecte détectée"
}
```

**Réponse `200` :**
```json
{
  "message": "Utilisateur verrouillé pendant 60 minutes",
  "user": {
    "id": "1",
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
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
  "error": "L'utilisateur est déjà verrouillé",
  "code": "ALREADY_LOCKED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/unlock/`  `users.lock`
Déverrouiller le compte d'un utilisateur.

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
  "message": "Compte utilisateur déverrouillé avec succès",
  "user": {
    "id": "1",
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
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
  "error": "L'utilisateur n'est pas verrouillé",
  "code": "NOT_LOCKED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
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

**Paramètres de requête (optionnels) :**
- `user_id` : Filtrer par ID utilisateur
- `action` : Filtrer par action (login, login_failed, password_change, etc.)
- `ip_address` : Filtrer par adresse IP
- `application_id` : Filtrer par ID d'application
- `date_from` : Après la date (YYYY-MM-DD)
- `date_to` : Avant la date (YYYY-MM-DD)
- `ordering` : Trier par created_at, action, user
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
      "user_email": "utilisateur@example.com",
      "action": "login",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "application": "app_456",
      "application_name": "Mon App Client",
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
Obtenir une entrée unique du journal d'audit.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "user": "123",
  "user_email": "utilisateur@example.com",
  "action": "login",
  "ip_address": "127.0.0.1",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "application": "app_456",
  "application_name": "Mon App Client",
  "details": {
    "success": true,
    "method": "password"
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Entrée du journal d'audit non trouvée",
  "code": "NOT_FOUND"
}
```

### `GET /admin/login-attempts/`  `audit.view`
Lister les tentatives de connexion.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (optionnels) :**
- `identifier` : Filtrer par identifiant (email/téléphone)
- `ip_address` : Filtrer par adresse IP
- `success` : Filtrer par succès/échec (true/false)
- `date_from` : Après la date (YYYY-MM-DD)
- `date_to` : Avant la date (YYYY-MM-DD)
- `ordering` : Trier par created_at, identifier, ip_address
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
      "identifier": "utilisateur@example.com",
      "ip_address": "127.0.0.1",
      "application": "app_456",
      "success": false,
      "failure_reason": "Mot de passe invalide",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### `GET /admin/blacklisted-tokens/`  `audit.view`
Lister les jetons sur liste noire actifs.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (optionnels) :**
- `user_id` : Filtrer par ID utilisateur
- `reason` : Filtrer par motif (logout, password_change, security)
- `expired` : Filtrer par expiration (true/false)
- `ordering` : Trier par blacklisted_at, expires_at
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
      "token_jti": "jti123456789",
      "user": "123",
      "user_email": "utilisateur@example.com",
      "blacklisted_at": "2024-01-01T12:00:00Z",
      "expires_at": "2024-01-01T18:00:00Z",
      "reason": "logout",
      "is_expired": false
    }
  ]
}
```

### `POST /admin/blacklisted-tokens/cleanup/`  `security.view`
Supprimer les jetons expirés de la liste noire.

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
  "message": "10 jetons expirés ont été nettoyés",
  "deleted_count": 10
}
```

### `GET /admin/refresh-tokens/`  `audit.view`
Lister les jetons de rafraîchissement actifs.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (optionnels) :**
- `user_id` : Filtrer par ID utilisateur
- `application_id` : Filtrer par ID d'application
- `is_revoked` : Filtrer par statut révoqué (true/false)
- `expired` : Filtrer par expiration (true/false)
- `ordering` : Trier par created_at, expires_at, last_used_at
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
      "user_email": "utilisateur@example.com",
      "application": "app_456",
      "application_name": "Mon App Client",
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
Révoquer un jeton de rafraîchissement spécifique.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "confirmation": "REVOKE"
}
```

**Réponse `200` :**
```json
{
  "message": "Jeton révoqué avec succès",
  "token": {
    "id": "1",
    "user": "123",
    "user_email": "utilisateur@example.com",
    "application": "app_456",
    "application_name": "Mon App Client",
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
  "error": "Le jeton est déjà révoqué",
  "code": "ALREADY_REVOKED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Jeton de rafraîchissement non trouvé",
  "code": "NOT_FOUND"
}
```

---

## Admin — RGPD

### `GET /admin/deletion-requests/`  `gdpr.view`
Lister les demandes de suppression de compte.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (optionnels) :**
- `user_id` : Filtrer par ID utilisateur
- `status` : Filtrer par statut (pending, confirmation_sent, confirmed, completed, cancelled)
- `date_from` : Demandé après la date (YYYY-MM-DD)
- `date_to` : Demandé avant la date (YYYY-MM-DD)
- `grace_period_expiring` : Filtrer par période de grâce expirante (true/false)
- `ordering` : Trier par requested_at, grace_period_ends_at, status
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
      "user_email": "utilisateur@example.com",
      "status": "pending",
      "requested_at": "2024-01-01T12:00:00Z",
      "confirmed_at": null,
      "grace_period_ends_at": "2024-01-31T12:00:00Z",
      "completed_at": null,
      "ip_address": "127.0.0.1",
      "reason": "Plus besoin du compte",
      "admin_notes": null,
      "processed_by": null,
      "processed_by_email": null,
      "is_grace_period_expired": false
    }
  ]
}
```

### `GET /admin/deletion-requests/<id>/`  `gdpr.admin`
Obtenir une demande de suppression.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Réponse `200` :**
```json
{
  "id": "1",
  "user": "123",
  "user_email": "utilisateur@example.com",
  "status": "pending",
  "requested_at": "2024-01-01T12:00:00Z",
  "confirmed_at": null,
  "grace_period_ends_at": "2024-01-31T12:00:00Z",
  "completed_at": null,
  "ip_address": "127.0.0.1",
  "reason": "Plus besoin du compte",
  "admin_notes": null,
  "processed_by": null,
  "processed_by_email": null,
  "is_grace_period_expired": false
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Demande de suppression non trouvée",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/<id>/process/`  `gdpr.process`
Traiter (exécuter) une demande de suppression.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "confirmation": "SUPPRIMER DÉFINITIVEMENT",
  "admin_notes": "Traité suite à la demande de l'utilisateur - conformité RGPD"
}
```

**Réponse `200` :**
```json
{
  "message": "Suppression du compte traitée avec succès",
  "deletion_completed": true,
  "processed_at": "2024-01-15T10:30:00Z",
  "data_anonymized": true,
  "audit_log_id": "123",
  "user_notified": true,
  "request": {
    "id": "1",
    "user": "123",
    "user_email": "utilisateur@example.com",
    "status": "completed",
    "requested_at": "2024-01-01T12:00:00Z",
    "confirmed_at": "2024-01-02T12:00:00Z",
    "grace_period_ends_at": "2024-01-31T12:00:00Z",
    "completed_at": "2024-01-15T10:30:00Z",
    "ip_address": "127.0.0.1",
    "reason": "Plus besoin du compte",
    "admin_notes": "Traité suite à la demande de l'utilisateur - conformité RGPD",
    "processed_by": "456",
    "processed_by_email": "admin@example.com",
    "is_grace_period_expired": false
  }
}
```

**Réponse `400` (Confirmation requise) :**
```json
{
  "error": "Confirmation explicite requise",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Réponse `400` (Non confirmée) :**
```json
{
  "error": "Impossible de traiter la demande avec le statut \"en attente\". Seules les demandes confirmées peuvent être traitées.",
  "code": "REQUEST_NOT_CONFIRMED"
}
```

**Réponse `404` (Non trouvé) :**
```json
{
  "error": "Demande de suppression non trouvée",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/process-expired/`  `gdpr.process`
Traiter toutes les suppressions dont la période de grâce est expirée.

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
  "message": "5 suppression(s) traitée(s), 0 échouée(s)",
  "processed": 5,
  "failed": 0
}
```

---

## Utilisateur — RGPD

### `POST /request-account-deletion/` 
Demander la suppression du compte (commence la période de grâce).

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Requête :**
```json
{
  "password": "mot_de_passe_actuel",
  "otp_code": "123456",
  "reason": "N'utilise plus le service"
}
```

**Réponse `201` :**
```json
{
  "message": "Demande de suppression de compte créée avec succès",
  "deletion_request_id": 123,
  "scheduled_deletion_date": "2024-02-15T10:30:00Z",
  "grace_period_days": 30,
  "cancellation_token": "cancel_abc123def456",
  "data_retention_policy": {
    "anonymization_after": "30 jours",
    "final_deletion_after": "90 jours"
  }
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Mot de passe invalide",
  "details": {
    "password": ["Mot de passe invalide"]
  }
}
```

**Réponse `400` (Déjà en attente) :**
```json
{
  "error": "Suppression de compte déjà en attente",
  "code": "DELETION_ALREADY_PENDING",
  "existing_request": {
    "scheduled_deletion_date": "2024-02-15T10:30:00Z",
    "cancellation_token": "cancel_abc123"
  }
}
```

### `POST /confirm-account-deletion/` 
Confirmer la demande de suppression de compte.

**Requête :**
```json
{
  "token": "confirm_abc123def456"
}
```

**Réponse `200` :**
```json
{
  "message": "Suppression du compte confirmée avec succès",
  "deletion_confirmed": true,
  "grace_period_ends": "2024-02-15T10:30:00Z",
  "cancellation_instructions": "Utilisez le jeton d'annulation de la demande initiale pour annuler avant la fin de la période de grâce."
}
```}
}
```

**Réponse `400` (Déjà en attente) :**
```json
{
  "error": "Suppression de compte déjà en attente",
  "code": "DELETION_ALREADY_PENDING",
  "existing_request": {
    "scheduled_deletion_date": "2024-02-15T10:30:00Z",
    "cancellation_token": "cancel_abc123"
  }
}
```

### `POST /confirm-account-deletion/` 
Confirmer la demande de suppression de compte.

**Requête :**
```json
{
  "token": "confirm_abc123def456"
}
```

**Réponse `200` :**
```json
{
  "message": "Suppression du compte confirmée avec succès",
  "deletion_confirmed": true,
  "grace_period_ends": "2024-02-15T10:30:00Z",
  "cancellation_instructions": "Utilisez le jeton d'annulation de la demande initiale pour annuler avant la fin de la période de grâce."
}
```

**Réponse `400` (Jeton requis) :**
```json
{
  "error": "Le jeton de confirmation est requis"
}
```

**Réponse `400` (Jeton invalide) :**
```json
{
  "error": "Jeton de confirmation invalide",
  "code": "INVALID_TOKEN"
}
```

**Réponse `410` (Jeton expiré) :**
```json
{
  "error": "Le jeton de confirmation a expiré",
  "code": "TOKEN_EXPIRED",
  "expired_at": "2024-01-16T10:30:00Z"
}
```

### `POST /cancel-account-deletion/` 
Annuler une demande de suppression en attente.

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
  "message": "Suppression du compte annulée avec succès",
  "deletion_cancelled": true,
  "account_reactivated": true,
  "cancellation_time": "2024-01-15T14:30:00Z",
  "security_note": "Votre compte a été réactivé et vous pouvez continuer à utiliser le service normalement."
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Mot de passe invalide",
  "details": {
    "password": ["Mot de passe invalide"]
  }
}
```

**Réponse `404` (Aucune suppression en attente) :**
```json
{
  "error": "Aucune demande de suppression en attente trouvée",
  "code": "NO_PENDING_DELETION"
}
```

### `GET /account-deletion-status/` 
Obtenir le statut de la demande de suppression actuelle.

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
      "reason": "N'utilise plus le service"
    },
    {
      "id": "100",
      "status": "cancelled",
      "requested_at": "2023-12-01T09:00:00Z",
      "confirmed_at": null,
      "completed_at": "2023-12-02T10:00:00Z",
      "reason": "A changé d'avis"
    }
  ]
}
```

### `POST /export-user-data/` 
Exporter toutes les données personnelles (RGPD Article 20).

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
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-15T10:30:00Z"
  },
  "roles": [
    {
      "id": "1",
      "name": "user",
      "description": "Rôle utilisateur standard"
    }
  ],
  "permissions": [
    "profile.view",
    "profile.edit"
  ],
  "applications": [
    {
      "id": "app_456",
      "name": "Mon App Client",
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
    "data_retention_policy": "Disponible pendant 30 jours"
  }
}
```

**Réponse `400` (Mot de passe invalide) :**
```json
{
  "error": "Mot de passe invalide",
  "details": {
    "password": ["Mot de passe invalide"]
  }
}
```

---

## Tableau de bord

Tous les points de terminaison du tableau de bord nécessitent la permission `dashboard.view`.

### `GET /dashboard/stats/`  `dashboard.view`
Statistiques globales inter-modules.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de requête (optionnels) :**
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
Statistiques d'authentification détaillées (taux de connexion, stats des jetons, graphiques).

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
Security statistics (audit summary, blacklisted tokens, suspicious activity).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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
GDPR compliance statistics.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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
Organization statistics (only if `TENXYTE_ORGANIZATIONS_ENABLED=True`).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200` (Enabled):**
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

**Response `200` (Disabled):**
```json
{
  "enabled": false
}
```

---

## Organizations (opt-in)

Enable with `TENXYTE_ORGANIZATIONS_ENABLED = True`.

All organization endpoints require the `X-Org-Slug` header to identify the target organization:
```
X-Org-Slug: acme-corp
```

### `POST /organizations/` 
Create an organization.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
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

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "slug": ["Organization with this slug already exists"],
  "parent_id": ["Parent organization not found"]
}
```

### `GET /organizations/list/` 
List organizations the current user belongs to.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `search`: Search in name and slug
- `is_active`: Filter by active status (true/false)
- `parent`: Filter by parent (null = root organizations)
- `ordering`: Sort by name, slug, created_at (with - for descending)
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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
Get organization details.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Response `200`:**
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

**Response `403` (Not member):**
```json
{
  "error": "Access denied: You are not a member of this organization",
  "code": "NOT_MEMBER"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Organisation non trouvée",
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
  "description": "Mise à jour de la description de l'entreprise technologique",
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
  "description": "Mise à jour de la description de l'entreprise technologique",
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
  "error": "Impossible de définir max_members en dessous du nombre actuel de membres",
  "code": "INVALID_MEMBER_LIMIT"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "Vous n'avez pas la permission de gérer cette organisation",
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
  "message": "Organisation supprimée avec succès"
}
```

**Réponse `400` (A des organisations enfants) :**
```json
{
  "error": "Impossible de supprimer une organisation ayant des organisations enfants",
  "code": "HAS_CHILDREN"
}
```

**Réponse `403` (Pas propriétaire) :**
```json
{
  "error": "Seuls les propriétaires de l'organisation peuvent supprimer des organisations",
  "code": "NOT_OWNER"
}
```

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Organisation non trouvée",
  "code": "NOT_FOUND"
}
```

### `GET /organizations/tree/` 
Obtenir l'arborescence complète de la hiérarchie de l'organisation.

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

**Paramètres de requête (optionnels) :**
- `search` : Recherche dans l'email, le prénom, le nom
- `role` : Filtrer par rôle (owner, admin, member)
- `status` : Filtrer par statut (active, inactive, pending)
- `ordering` : Trier par joined_at, user.email, role
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
        "first_name": "Jean",
        "last_name": "Dupont"
      },
      "role": "admin",
      "role_display": "Administrateur",
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
        "email": "utilisateur@acme.com",
        "first_name": "Jeanne",
        "last_name": "Martin"
      },
      "role": "member",
      "role_display": "Membre",
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
    "email": "nouveaumembre@acme.com",
    "first_name": "Jeanne",
    "last_name": "Martin"
  },
  "role": "member",
  "role_display": "Membre",
  "joined_at": "2024-01-20T15:30:00Z",
  "status": "active"
}
```

**Réponse `400` (Erreur de validation) :**
```json
{
  "error": "Impossible d'ajouter le propriétaire en tant que membre standard",
  "code": "INVALID_ROLE_FOR_OWNER"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "Vous n'avez pas la permission d'inviter des membres",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Utilisateur non trouvé) :**
```json
{
  "error": "Utilisateur non trouvé",
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
    "email": "membre@acme.com",
    "first_name": "Jeanne",
    "last_name": "Martin"
  },
  "role": "admin",
  "role_display": "Administrateur",
  "updated_at": "2024-01-20T16:00:00Z"
}
```

**Réponse `400` (Impossible de rétrograder le dernier propriétaire) :**
```json
{
  "error": "Impossible de rétrograder le dernier propriétaire de l'organisation",
  "code": "LAST_OWNER_CANNOT_BE_DEMOTED"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "Vous n'avez pas la permission de gérer les membres",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Membre non trouvé) :**
```json
{
  "error": "Membre non trouvé",
  "code": "MEMBER_NOT_FOUND"
}
```

### `DELETE /organizations/members/<user_id>/remove/`  `org.members.remove`
Retirer un membre d'une organisation.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Paramètres de chemin :**
- `user_id` : ID de l'utilisateur à retirer

**Réponse `200` :**
```json
{
  "message": "Membre retiré avec succès"
}
```

**Réponse `400` (Impossible de retirer le dernier propriétaire) :**
```json
{
  "error": "Impossible de retirer le dernier propriétaire de l'organisation",
  "code": "LAST_OWNER_CANNOT_BE_REMOVED"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "Vous n'avez pas la permission de retirer des membres",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Réponse `404` (Membre non trouvé) :**
```json
{
  "error": "Membre non trouvé",
  "code": "MEMBER_NOT_FOUND"
}
```

### `POST /organizations/invitations/`  `org.members.invite`
Inviter un utilisateur dans une organisation par email.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Requête :**
```json
{
  "email": "nouvelutilisateur@example.com",
  "role_code": "member",
  "expires_in_days": 7
}
```

**Réponse `201` :**
```json
{
  "id": 123,
  "email": "nouvelutilisateur@example.com",
  "role": "member",
  "role_display": "Membre",
  "token": "inv_abc123def456",
  "expires_at": "2024-01-27T15:30:00Z",
  "invited_by": {
    "id": 42,
    "email": "admin@acme.com",
    "first_name": "Jean",
    "last_name": "Dupont"
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
  "error": "L'utilisateur est déjà membre de cette organisation",
  "code": "ALREADY_MEMBER"
}
```

**Réponse `403` (Permissions insuffisantes) :**
```json
{
  "error": "Vous n'avez pas la permission d'inviter des membres",
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
        "name": "Gérer l'organisation",
        "description": "Peut gérer tous les paramètres de l'organisation"
      },
      {
        "code": "org.members.invite",
        "name": "Inviter des membres",
        "description": "Peut inviter de nouveaux membres dans l'organisation"
      },
      {
        "code": "org.members.manage",
        "name": "Gérer les membres",
        "description": "Peut gérer les membres existants"
      },
      {
        "code": "org.members.remove",
        "name": "Retirer des membres",
        "description": "Peut retirer des membres de l'organisation"
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
        "name": "Inviter des membres",
        "description": "Peut inviter de nouveaux membres dans l'organisation"
      },
      {
        "code": "org.members.manage",
        "name": "Gérer les membres",
        "description": "Peut gérer les membres existants"
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
        "name": "Voir l'organisation",
        "description": "Peut voir les détails de l'organisation"
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
Commencer l'enregistrement d'une passkey. Retourne un challenge.

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
    "name": "utilisateur@example.com",
    "displayName": "utilisateur@example.com"
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
  "error": "WebAuthn n'est pas activé",
  "code": "WEBAUTHN_DISABLED"
}
```

### `POST /webauthn/register/complete/` 
Terminer l'enregistrement de la passkey avec la réponse de l'authentificateur.

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
  "message": "Passkey enregistrée avec succès",
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
  "error": "Réponse d'identifiant WebAuthn invalide",
  "code": "INVALID_CREDENTIAL"
}
```

**Réponse `400` (Identifiant en double) :**
```json
{
  "error": "Cet identifiant est déjà enregistré",
  "code": "DUPLICATE_CREDENTIAL"
}
```

### `POST /webauthn/authenticate/begin/`
Commencer l'authentification par passkey. Retourne un challenge.

**Requête :**
```json
{
  "email": "utilisateur@example.com"
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
  "error": "Utilisateur non trouvé",
  "code": "USER_NOT_FOUND"
}
```

### `POST /webauthn/authenticate/complete/`
Terminer l'authentification par passkey. Retourne des jetons JWT.

**Requête :**
```json
{
  "challenge_id": 12345,
  "credential": {
    "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "rawId": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiQTNINUQ3RTlGMUcyRzRIOEk4SjBLMUwyTTNONE81UDZRN1I4UzlUMFUxVjJXM1g0WTVaNiIsIm9yaWdpbiI6Imh0dHBzOi8vbG9jYWxob3N0OjgwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2UsImF1dGhlbnRpY2F0b3JEYXRhIjoiU1RaTVlJYlJibUZpYkdsemNHRnpjM2R2Y21WeVgybGtJam9pUTFWVFZFOU5SVkpmTVRJek5EVVJOUVhNRVFDTVVGYXFkZDFXVkdSVVJVTlFWTmxjbU56TTJSdlkyMVZlVjlyYkd0SmFtOXBUTFZXVlZWRk9VNVNWaXBsVFZKWlVpMXBOVEl6TkRVMklpd2lhWE56ZFdWa1gyUmhkR1VpT2lJeU1ESTBMVEV3TFRFd1ZERXdPakF3T2pBd1dpSXNJbVY0Y0dseWVWOWtZWFJsSWpvaU1qQXlOUzB4TUMweE1GUXhNRG93TURvd01Gb2lMQ0p3Y205a2RXTjBJam9pZEhscmN6VmtMblI1Y0dVaWFXTjBJam9pYVc1emRHRndZV2RwYldGemJHVjBJam9pYUdWcmN5NWllVzlpYldGbmFIUnZjR1Z6Y3lJZ2IyNXBaV3c2SUdGNWRXUm9aVzVwWm13aUlpd2laWE53YVdKMWJHVnpJanA3SW1sa1pXNW5aWFFpT2lJeU1ESTBMVEV3TFRFd1ZERXdPakF3T2pBd1dpSjki",
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
    "email": "utilisateur@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "is_active": true,
    "last_login": "2024-01-20T17:00:00Z"
  },
  "message": "Authentification réussie",
  "credential_used": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6"
}
```

**Réponse `400` (Assertion invalide) :**
```json
{
  "error": "Assertion WebAuthn invalide",
  "code": "INVALID_ASSERTION"
}
```

**Réponse `401` (Authentification échouée) :**
```json
{
  "error": "L'authentification a échoué",
  "code": "AUTH_FAILED"
}
```

### `GET /webauthn/credentials/` 
Lister les passkeys enregistrées pour l'utilisateur actuel.

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
Supprimer une passkey enregistrée.

**En-têtes (requis) :**
```
Authorization: Bearer <access_token>
```

**Paramètres de chemin :**
- `id` : ID de la passkey à supprimer

**Réponse `204` :**
(aucun contenu - suppression réussie)

**Réponse `404` (Non trouvée) :**
```json
{
  "error": "Passkey non trouvée",
  "code": "NOT_FOUND"
}
```

## Points de terminaison Agent IA (AIRS)

Tenxyte inclut un ensemble complet de points de terminaison pour la sécurité d'identité et d'exécution des agents IA (AIRS) — gestion des jetons d'agent, heartbeats, actions en attente et rapports d'utilisation :

| Méthode | Point de terminaison | Description |
|---|---|---|
| `GET/POST` | `/ai/tokens/` | Lister / créer des jetons d'agent |
| `GET/PUT/DELETE` | `/ai/tokens/<id>/` | Détail d'un jeton d'agent |
| `POST` | `/ai/tokens/<id>/revoke/` | Révoquer un jeton d'agent |
| `POST` | `/ai/tokens/<id>/suspend/` | Suspendre un jeton d'agent |
| `POST` | `/ai/tokens/<id>/heartbeat/` | Ping de heartbeat de l'agent |
| `POST` | `/ai/tokens/<id>/report-usage/` | Rapporter les métriques d'utilisation |
| `POST` | `/ai/tokens/revoke-all/` | Révoquer tous les jetons d'agent |
| `GET` | `/ai/pending-actions/` | Lister les actions en attente (human-in-the-loop) |
| `POST` | `/ai/pending-actions/<id>/approve/` | Approuver une action en attente |
| `POST` | `/ai/pending-actions/<id>/reject/` | Rejeter une action en attente |

→ Voir le [Guide AIRS](airs.md) pour la documentation complète des requêtes/réponses, les niveaux d'habilitation et la gestion du cycle de vie des agents.

---

## Légende

-  — Nécessite `Authorization: Bearer <access_token>`
- `permission.code` — Nécessite cette permission spécifique
