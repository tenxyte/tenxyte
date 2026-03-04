# API Endpoints Reference

## Table of Contents

- [API Endpoints Reference](#api-endpoints-reference)
  - [Authentication](#authentication)
    - [`POST /register/`](#post-register)
    - [`POST /login/email/`](#post-loginemail)
    - [`POST /login/phone/`](#post-loginphone)
  - [Social Login (Multi-Provider)](#social-login-multi-provider)
    - [`POST /social/<provider>/`](#post-socialprovider)
    - [`GET /social/<provider>/callback/`](#get-socialprovidercallback)
  - [Magic Link (Passwordless)](#magic-link-passwordless)
    - [`POST /magic-link/request/`](#post-magic-linkrequest)
    - [`GET /magic-link/verify/?token=<token>`](#get-magic-linkverifytokentoken)
    - [`POST /refresh/`](#post-refresh)
    - [`POST /logout/`](#post-logout)
    - [`POST /logout/all/` ](#post-logoutall)
  - [OTP Verification](#otp-verification)
    - [`POST /otp/request/` ](#post-otprequest)
    - [`POST /otp/verify/email/` ](#post-otpverifyemail)
    - [`POST /otp/verify/phone/` ](#post-otpverifyphone)
  - [Password Management](#password-management)
    - [`POST /password/reset/request/`](#post-passwordresetrequest)
    - [`POST /password/reset/confirm/`](#post-passwordresetconfirm)
    - [`POST /password/change/` ](#post-passwordchange)
    - [`POST /password/strength/`](#post-passwordstrength)
    - [`GET /password/requirements/`](#get-passwordrequirements)
  - [User Profile](#user-profile)
    - [`GET /me/` ](#get-me)
    - [`PATCH /me/` ](#patch-me)
    - [`GET /me/roles/` ](#get-meroles)
  - [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
    - [`GET /2fa/status/` ](#get-2fastatus)
    - [`POST /2fa/setup/` ](#post-2fasetup)
    - [`POST /2fa/confirm/` ](#post-2faconfirm)
    - [`POST /2fa/disable/` ](#post-2fadisable)
    - [`POST /2fa/backup-codes/` ](#post-2fabackup-codes)
  - [RBAC — Permissions](#rbac-permissions)
    - [`GET /permissions/`  `permissions.view`](#get-permissions-permissionsview)
    - [`POST /permissions/`  `permissions.manage`](#post-permissions-permissionsmanage)
    - [`GET /permissions/<id>/`  `permissions.view`](#get-permissionsid-permissionsview)
    - [`PUT /permissions/<id>/`  `permissions.manage`](#put-permissionsid-permissionsmanage)
    - [`DELETE /permissions/<id>/`  `permissions.manage`](#delete-permissionsid-permissionsmanage)
  - [RBAC — Roles](#rbac-roles)
    - [`GET /roles/`  `roles.view`](#get-roles-rolesview)
    - [`POST /roles/`  `roles.manage`](#post-roles-rolesmanage)
    - [`GET /roles/<id>/`  `roles.view`](#get-rolesid-rolesview)
    - [`PUT /roles/<id>/`  `roles.manage`](#put-rolesid-rolesmanage)
    - [`DELETE /roles/<id>/`  `roles.manage`](#delete-rolesid-rolesmanage)
    - [`GET /roles/<id>/permissions/`  `roles.view`](#get-rolesidpermissions-rolesview)
    - [`POST /roles/<id>/permissions/`  `roles.manage`](#post-rolesidpermissions-rolesmanage)
  - [RBAC — User Roles & Permissions](#rbac-user-roles-permissions)
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
  - [Admin — User Management](#admin-user-management)
    - [`GET /admin/users/`  `users.view`](#get-adminusers-usersview)
    - [`GET /admin/users/<id>/`  `users.view`](#get-adminusersid-usersview)
    - [`POST /admin/users/<id>/ban/`  `users.ban`](#post-adminusersidban-usersban)
    - [`POST /admin/users/<id>/unban/`  `users.ban`](#post-adminusersidunban-usersban)
    - [`POST /admin/users/<id>/lock/`  `users.lock`](#post-adminusersidlock-userslock)
    - [`POST /admin/users/<id>/unlock/`  `users.lock`](#post-adminusersidunlock-userslock)
  - [Admin — Security](#admin-security)
    - [`GET /admin/audit-logs/`  `audit.view`](#get-adminaudit-logs-auditview)
    - [`GET /admin/audit-logs/<id>/`  `audit.view`](#get-adminaudit-logsid-auditview)
    - [`GET /admin/login-attempts/`  `audit.view`](#get-adminlogin-attempts-auditview)
    - [`GET /admin/blacklisted-tokens/`  `audit.view`](#get-adminblacklisted-tokens-auditview)
    - [`POST /admin/blacklisted-tokens/cleanup/`  `security.view`](#post-adminblacklisted-tokenscleanup-securityview)
    - [`GET /admin/refresh-tokens/`  `audit.view`](#get-adminrefresh-tokens-auditview)
    - [`POST /admin/refresh-tokens/<id>/revoke/`  `security.view`](#post-adminrefresh-tokensidrevoke-securityview)
  - [Admin — GDPR](#admin-gdpr)
    - [`GET /admin/deletion-requests/`  `gdpr.view`](#get-admindeletion-requests-gdprview)
    - [`GET /admin/deletion-requests/<id>/`  `gdpr.admin`](#get-admindeletion-requestsid-gdpradmin)
    - [`POST /admin/deletion-requests/<id>/process/`  `gdpr.process`](#post-admindeletion-requestsidprocess-gdprprocess)
    - [`POST /admin/deletion-requests/process-expired/`  `gdpr.process`](#post-admindeletion-requestsprocess-expired-gdprprocess)
  - [User — GDPR](#user-gdpr)
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
  - [Organizations (opt-in)](#organizations-opt-in)
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
  - [WebAuthn / Passkeys (FIDO2)](#webauthn-passkeys-fido2)
    - [`POST /webauthn/register/begin/` ](#post-webauthnregisterbegin)
    - [`POST /webauthn/register/complete/` ](#post-webauthnregistercomplete)
    - [`POST /webauthn/authenticate/begin/`](#post-webauthnauthenticatebegin)
    - [`POST /webauthn/authenticate/complete/`](#post-webauthnauthenticatecomplete)
    - [`GET /webauthn/credentials/` ](#get-webauthncredentials)
    - [`DELETE /webauthn/credentials/<id>/` ](#delete-webauthncredentialsid)
  - [Legend](#legend)

---


All endpoints are prefixed with your configured base path (e.g. `/api/v1/auth/`).

Every request **must** include application credentials:
```
X-Access-Key: <your-access-key>
X-Access-Secret: <your-access-secret>
```

Authenticated endpoints additionally require:
```
Authorization: Bearer <access_token>
```

---

## Authentication

### `POST /register/`
Register a new user.

**Request:**
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
`email` or `phone_country_code` + `phone_number` is required.
`login`: If true, returns JWT tokens for immediate login.
`device_info`: Optional device fingerprinting info.

**Response `201`:**
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

If `login: true` in request, also includes:
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
Login with email + password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "totp_code": "123456",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`totp_code` is only required if 2FA is enabled.
`device_info`: Optional device fingerprinting info.

**Response `200`:**
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

**Response `401` (2FA required):**
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Response `401` (Invalid credentials):**
```json
{
  "error": "Invalid credentials",
  "code": "LOGIN_FAILED"
}
```

**Response `403` (Admin 2FA required):**
```json
{
  "error": "Administrators must have 2FA enabled to login.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Response `409` (Session limit exceeded):**
```json
{
  "error": "Session limit exceeded",
  "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
  "code": "SESSION_LIMIT_EXCEEDED"
}
```

**Response `423` (Account locked):**
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
Login with phone number + password.

**Request:**
```json
{
  "phone_country_code": "+1",
  "phone_number": "5551234567",
  "password": "SecurePass123!",
  "totp_code": "123456",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`totp_code` is only required if 2FA is enabled.
`device_info`: Optional device fingerprinting info.

**Response `200`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "phone_country_code": ["Invalid country code format. Use +XX format."],
    "phone_number": ["Phone number must be 9-15 digits."]
  }
}
```

**Response `401` (2FA required):**
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

**Response `401` (Invalid credentials):**
```json
{
  "error": "Invalid credentials",
  "code": "LOGIN_FAILED"
}
```

**Response `403` (Admin 2FA required):**
```json
{
  "error": "Administrators must have 2FA enabled to login.",
  "code": "ADMIN_2FA_SETUP_REQUIRED"
}
```

**Response `409` (Session limit exceeded):**
```json
{
  "error": "Session limit exceeded",
  "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
  "code": "SESSION_LIMIT_EXCEEDED"
}
```

**Response `423` (Account locked):**
```json
{
  "error": "Account locked",
  "details": "Account has been locked due to too many failed login attempts.",
  "code": "ACCOUNT_LOCKED",
  "retry_after": 1800
}
```

---

## Social Login (Multi-Provider)

Requires social provider configuration (Google, GitHub, Microsoft, Facebook).

### `POST /social/<provider>/`
Authenticate via OAuth2 provider.

**Providers:** `google`, `github`, `microsoft`, `facebook`

**Request (access_token):**
```json
{
  "access_token": "ya29.a0AfH6SMC...",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```

**Request (authorization code):**
```json
{
  "code": "<authorization-code>",
  "redirect_uri": "https://yourapp.com/auth/callback",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```

**Request (Google ID token):**
```json
{
  "id_token": "<google-id-token>",
  "device_info": "v=1|os=windows;osv=11|device=desktop"
}
```
`device_info`: Optional device fingerprinting info.

**Response `200`:**
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

**Response `400` (Invalid provider):**
```json
{
  "error": "Unsupported provider",
  "code": "INVALID_PROVIDER",
  "supported_providers": ["google", "github", "microsoft", "facebook"]
}
```

**Response `401` (Provider auth failed):**
```json
{
  "error": "Provider authentication failed",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Response `401` (Social auth failed):**
```json
{
  "error": "Social authentication failed",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

### `GET /social/<provider>/callback/`
OAuth2 callback endpoint for authorization code flow.

**Query Parameters:**
- `code` (required): Authorization code from provider
- `redirect_uri` (required): Original redirect URI
- `state` (optional): CSRF/state parameter

**Response `200`:**
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

**Response `302` (Redirect with tokens):**
```
Location: https://yourapp.com/auth/callback?access_token=eyJ...&refresh_token=eyJ...
```

**Response `400` (Invalid provider):**
```json
{
  "error": "Provider 'xyz' is not supported.",
  "code": "PROVIDER_NOT_SUPPORTED"
}
```

**Response `400` (Missing code):**
```json
{
  "error": "Authorization code is required",
  "code": "MISSING_CODE"
}
```

**Response `400` (Missing redirect_uri):**
```json
{
  "error": "redirect_uri is required",
  "code": "MISSING_REDIRECT_URI"
}
```

**Response `400` (Callback error):**
```json
{
  "error": "OAuth2 callback processing failed",
  "code": "CALLBACK_ERROR",
  "details": "An unexpected error occurred during authentication."
}
```

**Response `401` (Code exchange failed):**
```json
{
  "error": "Failed to exchange authorization code",
  "code": "CODE_EXCHANGE_FAILED"
}
```

**Response `401` (Provider auth failed):**
```json
{
  "error": "Could not retrieve user data from google",
  "code": "PROVIDER_AUTH_FAILED"
}
```

**Response `401` (Social auth failed):**
```json
{
  "error": "Social authentication failed",
  "code": "SOCIAL_AUTH_FAILED"
}
```

---

## Magic Link (Passwordless)

Requires `TENXYTE_MAGIC_LINK_ENABLED = True`.

### `POST /magic-link/request/`
Request a magic link sent by email.

**Request:**
```json
{
  "email": "user@example.com",
  "validation_url": "https://app.example.com/auth-magic/link/verify"
}
```

**Response `200`:**
```json
{
  "message": "If this email is registered, a magic link has been sent."
}
```

**Response `400` (Validation URL missing):**
```json
{
  "error": "Validation URL is required",
  "code": "VALIDATION_URL_REQUIRED"
}
```

**Response `429` (Rate limited):**
```json
{
  "error": "Too many magic link requests",
  "retry_after": 3600
}
```

---

### `GET /magic-link/verify/?token=<token>`
Verify a magic link token and receive JWT tokens.

**Response `200`:**
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

**Response `400` (Token missing):**
```json
{
  "error": "Token is required",
  "code": "TOKEN_REQUIRED"
}
```

**Response `401` (Invalid/used/expired token):**
```json
{
  "error": "Invalid magic link token",
  "details": "The token provided is not valid",
  "code": "INVALID_TOKEN"
}
```

---

### `POST /refresh/`
Refresh the access token.

**Request:**
```json
{ "refresh_token": "eyJ..." }
```

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "refresh_token": ["This field is required."]
  }
}
```

**Response `401` (Invalid/expired refresh token):**
```json
{
  "error": "Refresh token expired or revoked",
  "code": "REFRESH_FAILED"
}
```

---

### `POST /logout/`
Logout (revokes refresh token + blacklists access token).

**Request:**
```json
{ "refresh_token": "eyJ..." }
```

**Headers (optional):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{ "message": "Logged out successfully" }
```

**Response `400` (Validation error):**
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
Logout from all devices.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{ "message": "Logged out from 3 devices" }
```

**Response `401` (Unauthorized):**
```json
{
  "error": "Authentication credentials were not provided",
  "details": "JWT token is required"
}
```

---

## OTP Verification

### `POST /otp/request/` 
Request an OTP code (email or phone verification).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{ "otp_type": "email" }
```
`otp_type`: `"email"` or `"phone"`

**Response `200`:**
```json
{
  "message": "OTP verification code sent",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email",
  "masked_recipient": "u***@example.com"
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "otp_type": ["Enter a valid choice."]
  }
}
```

**Response `429` (Rate limited):**
```json
{
  "error": "Too many OTP requests",
  "retry_after": 300
}
```

---

### `POST /otp/verify/email/` 
Verify email with OTP code.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{ "code": "123456" }
```

**Response `200`:**
```json
{
  "message": "Email verified successfully",
  "email_verified": true,
  "verified_at": "2024-01-01T12:00:00Z"
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Ensure this field has no more than 6 characters."]
  }
}
```

**Response `401` (Invalid/expired code):**
```json
{
  "error": "Invalid OTP code",
  "details": "The code provided is incorrect or has expired",
  "code": "INVALID_OTP"
}
```

---

### `POST /otp/verify/phone/` 
Verify phone with OTP code.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{ "code": "123456" }
```

**Response `200`:**
```json
{
  "message": "Phone verified successfully",
  "phone_verified": true,
  "verified_at": "2024-01-01T12:00:00Z",
  "phone_number": "+33612345678"
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Ensure this field has no more than 6 characters."]
  }
}
```

**Response `401` (Invalid/expired code):**
```json
{
  "error": "Invalid OTP code",
  "details": "The code provided is incorrect or has expired",
  "code": "INVALID_OTP"
}
```

---

## Password Management

### `POST /password/reset/request/`
Request a password reset email.

**Request (email):**
```json
{ "email": "user@example.com" }
```

**Request (phone):**
```json
{
  "phone_country_code": "+33",
  "phone_number": "612345678"
}
```

**Response `200`:**
```json
{
  "message": "Password reset code sent",
  "otp_id": "uuid-string",
  "expires_at": "2024-01-01T12:00:00Z",
  "channel": "email"
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": "Email or phone number is required"
}
```

**Response `429` (Rate limited):**
```json
{
  "error": "Too many password reset requests",
  "retry_after": 3600
}
```

---

### `POST /password/reset/confirm/`
Confirm password reset with OTP code.

**Request (email):**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Request (phone):**
```json
{
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "otp_code": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Response `200`:**
```json
{
  "message": "Password reset successful",
  "tokens_revoked": 3,
  "password_safe": true
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "new_password": ["Password must be at least 8 characters long."]
  }
}
```

**Response `401` (Invalid/expired code):**
```json
{
  "error": "OTP code has expired",
  "details": "Please request a new password reset code",
  "code": "OTP_EXPIRED"
}
```

---

### `POST /password/change/` 
Change password (requires current password).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

**Response `200`:**
```json
{
  "message": "Password changed successfully",
  "password_strength": "strong",
  "sessions_revoked": 2
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "new_password": ["Password must be at least 8 characters long."]
  }
}
```

**Response `401` (Invalid current password):**
```json
{
  "error": "Current password is incorrect",
  "code": "INVALID_PASSWORD"
}
```

---

### `POST /password/strength/`
Check password strength without saving.

**Request:**
```json
{ 
  "password": "MyPassword123!",
  "email": "user@example.com"
}
```

**Response `200`:**
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

**Response `200` (Weak password):**
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
Get the current password policy requirements.

**Response `200`:**
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

## User Profile

### `GET /me/` 
Get the current user's profile.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Headers (optional):**
```
X-Org-Slug: organization-slug
```

**Response `200`:**
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
Update the current user's profile.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Headers (optional):**
```
X-Org-Slug: organization-slug
```

**Request:**
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

**Response `200`:**
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

**Response `400` (Validation error):**
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
Get the current user's roles and permissions.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Headers (optional):**
```
X-Org-Slug: organization-slug
```

**Response `200`:**
```json
{
  "roles": ["admin", "user"],
  "permissions": ["users.view", "users.manage", "roles.view"]
}
```

---

## Two-Factor Authentication (2FA)

### `GET /2fa/status/` 
Get 2FA status for the current user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{
  "is_enabled": false,
  "backup_codes_remaining": 0
}
```

---

### `POST /2fa/setup/` 
Initiate 2FA setup. Returns QR code and backup codes.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `400` (2FA already enabled):**
```json
{
  "error": "2FA is already enabled",
  "code": "2FA_ALREADY_ENABLED"
}
```

---

### `POST /2fa/confirm/` 
Confirm 2FA activation with a TOTP code.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{ "code": "123456" }
```

**Response `200`:**
```json
{
  "message": "2FA enabled successfully",
  "is_enabled": true
}
```

**Response `400` (Invalid code):**
```json
{
  "error": "Invalid TOTP code",
  "details": "The code provided is incorrect or outside the valid time window",
  "code": "INVALID_CODE"
}
```

**Response `400` (Code missing):**
```json
{
  "error": "Code is required",
  "code": "CODE_REQUIRED"
}
```

---

### `POST /2fa/disable/` 
Disable 2FA (requires TOTP code or backup code).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "code": "123456",
  "password": "UserP@ss123!"
}
```

**Response `200`:**
```json
{
  "message": "2FA disabled successfully",
  "is_enabled": false
}
```

**Response `400` (Invalid code):**
```json
{
  "error": "Invalid TOTP code",
  "details": "The code provided is incorrect",
  "code": "INVALID_CODE"
}
```

**Response `400` (Code missing):**
```json
{
  "error": "Code is required",
  "code": "CODE_REQUIRED"
}
```

---

### `POST /2fa/backup-codes/` 
Regenerate backup codes (invalidates old ones).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{ "code": "123456" }
```

**Response `200`:**
```json
{
  "message": "Backup codes regenerated",
  "backup_codes": ["AB12CD34", "EF56GH78", "IJ90KL12", "MN34OP56", "QR78ST90", "UV12WX34", "YZ56AB78", "CD90EF12", "GH34IJ56", "KL78MN90"],
  "warning": "Save these codes securely. They will not be shown again."
}
```

**Response `400` (Invalid code):**
```json
{
  "error": "Invalid TOTP code",
  "details": "The TOTP code provided is incorrect",
  "code": "INVALID_CODE"
}
```

**Response `400` (Code missing):**
```json
{
  "error": "TOTP code is required",
  "code": "CODE_REQUIRED"
}
```

---

## RBAC — Permissions

### `GET /permissions/`  `permissions.view`
List all permissions.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `search`: Search in code, name
- `parent`: Filter by parent (null for root permissions, or parent ID)
- `ordering`: Order by code, name, created_at (default: code)

**Response `200`:**
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
Create a permission.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "code": "posts.publish",
  "name": "Publish Posts",
  "description": "Can publish blog posts",
  "parent_code": "posts.manage"
}
```

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Permission with this code already exists."]
  }
}
```

### `GET /permissions/<id>/`  `permissions.view`
Get a permission.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

### `PUT /permissions/<id>/`  `permissions.manage`
Update a permission.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "View all users",
  "description": "Can view all users in the system",
  "parent_code": null
}
```

**Response `200`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "parent_code": ["Parent permission not found"]
  }
}
```

**Response `404` (Not found):**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /permissions/<id>/`  `permissions.manage`
Delete a permission.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{
  "message": "Permission deleted"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Permission not found",
  "code": "NOT_FOUND"
}
```

---

## RBAC — Roles

### `GET /roles/`  `roles.view`
List all roles.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `search`: Search in code, name
- `is_default`: Filter by is_default (true/false)
- `ordering`: Order by code, name, created_at (default: name)

**Response `200`:**
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
Create a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "code": "editor",
  "name": "Editor",
  "description": "Can edit content",
  "permission_codes": ["posts.edit", "posts.view"],
  "is_default": false
}
```

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "code": ["Role with this code already exists."]
  }
}
```

### `GET /roles/<id>/`  `roles.view`
Get a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `PUT /roles/<id>/`  `roles.manage`
Update a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "Senior Editor",
  "description": "Can edit and publish content",
  "permission_codes": ["posts.edit", "posts.publish", "posts.view"],
  "is_default": false
}
```

**Response `200`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["Permission 'invalid.code' not found"]
  }
}
```

**Response `404` (Not found):**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /roles/<id>/`  `roles.manage`
Delete a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{
  "message": "Role deleted"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `GET /roles/<id>/permissions/`  `roles.view`
List permissions assigned to a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Role not found",
  "code": "NOT_FOUND"
}
```

### `POST /roles/<id>/permissions/`  `roles.manage`
Assign permissions to a role.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "permission_codes": ["posts.edit", "posts.publish"]
}
```

**Response `200`:**
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

**Response `200` (Some already assigned):**
```json
{
  "message": "1 permission(s) added",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "role_code": "editor",
  "permissions": [...]
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["This field is required."]
  }
}
```

**Response `400` (Permissions not found):**
```json
{
  "error": "Some permissions not found",
  "code": "PERMISSIONS_NOT_FOUND",
  "not_found": ["invalid.permission"]
}
```

---

## RBAC — User Roles & Permissions

### `GET /users/<id>/roles/`  `users.manage`
List roles assigned to a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /users/<id>/roles/`  `users.manage`
Assign a role to a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "role_code": "editor"
}
```

**Response `200`:**
```json
{
  "message": "Role assigned",
  "roles": ["editor", "user"]
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "role_code": ["This field is required."]
  }
}
```

**Response `404` (User not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

**Response `404` (Role not found):**
```json
{
  "error": "Role not found",
  "code": "ROLE_NOT_FOUND"
}
```

### `DELETE /users/<id>/roles/`  `users.manage`
Remove a role from a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (required):**
- `role_code`: Role code to remove

**Request:**
```
DELETE /users/123/roles/?role_code=editor
```

**Response `200`:**
```json
{
  "message": "Role removed",
  "roles": ["user"]
}
```

**Response `400` (Missing parameter):**
```json
{
  "error": "role_code query parameter required",
  "code": "MISSING_PARAM"
}
```

**Response `404` (User not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

**Response `404` (Role not found):**
```json
{
  "error": "Role not found",
  "code": "ROLE_NOT_FOUND"
}
```

### `GET /users/<id>/permissions/`  `users.manage`
List direct permissions for a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /users/<id>/permissions/`  `users.manage`
Assign a direct permission to a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "permission_codes": ["posts.edit", "posts.publish"]
}
```

**Response `200`:**
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

**Response `200` (Some already assigned):**
```json
{
  "message": "1 permission(s) added",
  "added": ["posts.publish"],
  "already_assigned": ["posts.edit"],
  "user_id": "1",
  "direct_permissions": [...]
}
```

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "permission_codes": ["This field is required."]
  }
}
```

**Response `400` (Permissions not found):**
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
List all applications.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `search`: Search in name, description
- `is_active`: Filter by active status (true/false)
- `ordering`: Order by name, created_at (default: name)

**Response `200`:**
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
Create an application.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "My Next.js App",
  "description": "Frontend client"
}
```

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "name": ["This field is required."]
  }
}
```

### `GET /applications/<id>/`  `applications.view`
Get an application.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `PUT /applications/<id>/`  `applications.manage`
Update an application.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "Updated App Name",
  "description": "Updated description",
  "is_active": true
}
```

**Response `200`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Validation error",
  "details": {
    "name": ["This field may not be blank."]
  }
}
```

**Response `404` (Not found):**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `DELETE /applications/<id>/`  `applications.manage`
Delete an application.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{
  "message": "Application \"My App\" deleted successfully"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

### `POST /applications/<id>/regenerate/`  `applications.manage`
Regenerate the application's access secret.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "confirmation": "REGENERATE"
}
```

**Response `200`:**
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

**Response `400` (Confirmation required):**
```json
{
  "error": "Confirmation required",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Application not found",
  "code": "NOT_FOUND"
}
```

---

## Admin — User Management

### `GET /admin/users/`  `users.view`
List all users with filtering and pagination.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `search`: Search in email, first_name, last_name
- `is_active`: Filter by active status (true/false)
- `is_locked`: Filter by locked account (true/false)
- `is_banned`: Filter by banned account (true/false)
- `is_deleted`: Filter by deleted account (true/false)
- `is_email_verified`: Filter by email verified (true/false)
- `is_2fa_enabled`: Filter by 2FA enabled (true/false)
- `role`: Filter by role code
- `date_from`: Created after (YYYY-MM-DD)
- `date_to`: Created before (YYYY-MM-DD)
- `ordering`: Sort by email, created_at, last_login, first_name
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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
Get a user's full profile.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/ban/`  `users.ban`
Ban a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "reason": "Terms of service violation"
}
```

**Response `200`:**
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

**Response `400` (Already banned):**
```json
{
  "error": "User already banned",
  "code": "ALREADY_BANNED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/unban/`  `users.ban`
Unban a user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```
POST /admin/users/123/unban/
```

**Response `200`:**
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

**Response `400` (Not banned):**
```json
{
  "error": "User is not banned",
  "code": "NOT_BANNED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/lock/`  `users.lock`
Lock a user account.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "duration_minutes": 60,
  "reason": "Suspicious login activity detected"
}
```

**Response `200`:**
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

**Response `400` (Already locked):**
```json
{
  "error": "User already locked",
  "code": "ALREADY_LOCKED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/users/<id>/unlock/`  `users.lock`
Unlock a user account.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```
POST /admin/users/123/unlock/
```

**Response `200`:**
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

**Response `400` (Not locked):**
```json
{
  "error": "User is not locked",
  "code": "NOT_LOCKED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "User not found",
  "code": "NOT_FOUND"
}
```

---

## Admin — Security

### `GET /admin/audit-logs/`  `audit.view`
List audit log entries.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `user_id`: Filter by user ID
- `action`: Filter by action (login, login_failed, password_change, etc.)
- `ip_address`: Filter by IP address
- `application_id`: Filter by application ID
- `date_from`: After date (YYYY-MM-DD)
- `date_to`: Before date (YYYY-MM-DD)
- `ordering`: Sort by created_at, action, user
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Audit log not found",
  "code": "NOT_FOUND"
}
```

### `GET /admin/login-attempts/`  `audit.view`
List login attempts.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `identifier`: Filter by identifier (email/phone)
- `ip_address`: Filter by IP address
- `success`: Filter by success/failure (true/false)
- `date_from`: After date (YYYY-MM-DD)
- `date_to`: Before date (YYYY-MM-DD)
- `ordering`: Sort by created_at, identifier, ip_address
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `user_id`: Filter by user ID
- `reason`: Filter by reason (logout, password_change, security)
- `expired`: Filter by expired (true/false)
- `ordering`: Sort by blacklisted_at, expires_at
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```
POST /admin/blacklisted-tokens/cleanup/
```

**Response `200`:**
```json
{
  "message": "10 expired tokens cleaned up",
  "deleted_count": 10
}
```

### `GET /admin/refresh-tokens/`  `audit.view`
List active refresh tokens.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `user_id`: Filter by user ID
- `application_id`: Filter by application ID
- `is_revoked`: Filter by revoked (true/false)
- `expired`: Filter by expired (true/false)
- `ordering`: Sort by created_at, expires_at, last_used_at
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```
POST /admin/refresh-tokens/123/revoke/
```

**Response `200`:**
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

**Response `400` (Already revoked):**
```json
{
  "error": "Token already revoked",
  "code": "ALREADY_REVOKED"
}
```

**Response `404` (Not found):**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `user_id`: Filter by user ID
- `status`: Filter by status (pending, confirmation_sent, confirmed, completed, cancelled)
- `date_from`: Requested after date (YYYY-MM-DD)
- `date_to`: Requested before date (YYYY-MM-DD)
- `grace_period_expiring`: Filter by grace period expiring (true/false)
- `ordering`: Sort by requested_at, grace_period_ends_at, status
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Deletion request not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/<id>/process/`  `gdpr.process`
Process (execute) a deletion request.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "confirmation": "PERMANENTLY DELETE",
  "admin_notes": "Processed per user request - GDPR compliance"
}
```

**Response `200`:**
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

**Response `400` (Confirmation required):**
```json
{
  "error": "Explicit confirmation required",
  "code": "CONFIRMATION_REQUIRED"
}
```

**Response `400` (Not confirmed):**
```json
{
  "error": "Cannot process request with status \"pending\". Only confirmed requests can be processed.",
  "code": "REQUEST_NOT_CONFIRMED"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Deletion request not found",
  "code": "NOT_FOUND"
}
```

### `POST /admin/deletion-requests/process-expired/`  `gdpr.process`
Process all expired grace period deletions.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```
POST /admin/deletion-requests/process-expired/
```

**Response `200`:**
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
Request account deletion (starts grace period).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "password": "current_password",
  "otp_code": "123456",
  "reason": "No longer using the service"
}
```

**Response `201`:**
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

**Response `400` (Invalid password):**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

**Response `400` (Already pending):**
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

**Request:**
```json
{
  "token": "confirm_abc123def456"
}
```

**Response `200`:**
```json
{
  "message": "Account deletion confirmed successfully",
  "deletion_confirmed": true,
  "grace_period_ends": "2024-02-15T10:30:00Z",
  "cancellation_instructions": "Use the cancellation token from the initial request to cancel before the grace period ends."
}
```

**Response `400` (Token required):**
```json
{
  "error": "Confirmation token is required"
}
```

**Response `400` (Invalid token):**
```json
{
  "error": "Invalid confirmation token",
  "code": "INVALID_TOKEN"
}
```

**Response `410` (Token expired):**
```json
{
  "error": "Confirmation token has expired",
  "code": "TOKEN_EXPIRED",
  "expired_at": "2024-01-16T10:30:00Z"
}
```

### `POST /cancel-account-deletion/` 
Cancel a pending deletion request.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "password": "CurrentPassword123!"
}
```

**Response `200`:**
```json
{
  "message": "Account deletion cancelled successfully",
  "deletion_cancelled": true,
  "account_reactivated": true,
  "cancellation_time": "2024-01-15T14:30:00Z",
  "security_note": "Your account has been reactivated and you can continue using the service normally."
}
```

**Response `400` (Invalid password):**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

**Response `404` (No pending deletion):**
```json
{
  "error": "No pending deletion request found",
  "code": "NO_PENDING_DELETION"
}
```

### `GET /account-deletion-status/` 
Get the status of the current deletion request.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "password": "CurrentPassword123!"
}
```

**Response `200`:**
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

**Response `400` (Invalid password):**
```json
{
  "error": "Invalid password",
  "details": {
    "password": ["Invalid password"]
  }
}
```

---

## Dashboard

All dashboard endpoints require `dashboard.view` permission.

### `GET /dashboard/stats/`  `dashboard.view`
Global cross-module statistics.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Query Parameters (optional):**
- `period`: Analysis period (7d, 30d, 90d) - default: 7d
- `compare`: Include comparison with previous period (true/false)
- `X-Org-Slug`: Organization slug for filtering by organization

**Response `200`:**
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
Detailed authentication statistics (login rates, token stats, charts).

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `404` (Not found):**
```json
{
  "error": "Organization not found",
  "code": "NOT_FOUND"
}
```

### `PATCH /organizations/update/`  `org.manage`
Update an organization.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Request:**
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

**Response `200`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Cannot set max_members below current member count",
  "code": "INVALID_MEMBER_LIMIT"
}
```

**Response `403` (Insufficient permissions):**
```json
{
  "error": "You don't have permission to manage this organization",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

### `DELETE /organizations/delete/`  `org.owner`
Delete an organization.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Response `200`:**
```json
{
  "message": "Organization deleted successfully"
}
```

**Response `400` (Has child organizations):**
```json
{
  "error": "Cannot delete organization with child organizations",
  "code": "HAS_CHILDREN"
}
```

**Response `403` (Not owner):**
```json
{
  "error": "Only organization owners can delete organizations",
  "code": "NOT_OWNER"
}
```

**Response `404` (Not found):**
```json
{
  "error": "Organization not found",
  "code": "NOT_FOUND"
}
```

### `GET /organizations/tree/` 
Get the full organization hierarchy tree.

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
List organization members.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Query Parameters (optional):**
- `search`: Search in email, first name, last name
- `role`: Filter by role (owner, admin, member)
- `status`: Filter by status (active, inactive, pending)
- `ordering`: Sort by joined_at, user.email, role
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response `200`:**
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
Add a member to an organization.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Request:**
```json
{
  "user_id": 2,
  "role_code": "member"
}
```

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "Cannot add owner as regular member",
  "code": "INVALID_ROLE_FOR_OWNER"
}
```

**Response `403` (Insufficient permissions):**
```json
{
  "error": "You don't have permission to invite members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Response `404` (User not found):**
```json
{
  "error": "User not found",
  "code": "USER_NOT_FOUND"
}
```

### `PATCH /organizations/members/<user_id>/`  `org.members.manage`
Update a member's role.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Path Parameters:**
- `user_id`: ID of the user to update

**Request:**
```json
{
  "role_code": "admin"
}
```

**Response `200`:**
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

**Response `400` (Cannot demote last owner):**
```json
{
  "error": "Cannot demote the last owner of the organization",
  "code": "LAST_OWNER_CANNOT_BE_DEMOTED"
}
```

**Response `403` (Insufficient permissions):**
```json
{
  "error": "You don't have permission to manage members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Response `404` (Member not found):**
```json
{
  "error": "Member not found",
  "code": "MEMBER_NOT_FOUND"
}
```

### `DELETE /organizations/members/<user_id>/remove/`  `org.members.remove`
Remove a member from an organization.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Path Parameters:**
- `user_id`: ID of the user to remove

**Response `200`:**
```json
{
  "message": "Member removed successfully"
}
```

**Response `400` (Cannot remove last owner):**
```json
{
  "error": "Cannot remove the last owner of the organization",
  "code": "LAST_OWNER_CANNOT_BE_REMOVED"
}
```

**Response `403` (Insufficient permissions):**
```json
{
  "error": "You don't have permission to remove members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

**Response `404` (Member not found):**
```json
{
  "error": "Member not found",
  "code": "MEMBER_NOT_FOUND"
}
```

### `POST /organizations/invitations/`  `org.members.invite`
Invite a user to an organization by email.

**Headers (required):**
```
Authorization: Bearer <access_token>
X-Org-Slug: acme-corp
```

**Request:**
```json
{
  "email": "newuser@example.com",
  "role_code": "member",
  "expires_in_days": 7
}
```

**Response `201`:**
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

**Response `400` (Validation error):**
```json
{
  "error": "User is already a member of this organization",
  "code": "ALREADY_MEMBER"
}
```

**Response `403` (Insufficient permissions):**
```json
{
  "error": "You don't have permission to invite members",
  "code": "INSUFFICIENT_PERMISSIONS"
}
```

### `GET /org-roles/` 
List organization-scoped roles.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
[
  {
    "code": "owner",
    "name": "Owner",
    "description": "Full control over the organization",
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
    "name": "Administrator",
    "description": "Administrative access without ownership",
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
    "name": "Member",
    "description": "Standard organization member",
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

Requires `TENXYTE_WEBAUTHN_ENABLED = True` and `pip install py-webauthn`.

### `POST /webauthn/register/begin/` 
Begin passkey registration. Returns a challenge.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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

**Response `400` (WebAuthn disabled):**
```json
{
  "error": "WebAuthn is not enabled",
  "code": "WEBAUTHN_DISABLED"
}
```

### `POST /webauthn/register/complete/` 
Complete passkey registration with the authenticator response.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Request:**
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

**Response `201`:**
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

**Response `400` (Invalid credential):**
```json
{
  "error": "Invalid WebAuthn credential response",
  "code": "INVALID_CREDENTIAL"
}
```

**Response `400` (Duplicate credential):**
```json
{
  "error": "This credential is already registered",
  "code": "DUPLICATE_CREDENTIAL"
}
```

### `POST /webauthn/authenticate/begin/`
Begin passkey authentication. Returns a challenge.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response `200`:**
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

**Response `200` (Resident key mode):**
```json
{
  "challenge": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
  "rpId": "localhost:8000",
  "allowCredentials": [],
  "userVerification": "required",
  "timeout": 300000
}
```

**Response `400` (User not found):**
```json
{
  "error": "User not found",
  "code": "USER_NOT_FOUND"
}
```

### `POST /webauthn/authenticate/complete/`
Complete passkey authentication. Returns JWT tokens.

**Request:**
```json
{
  "challenge_id": 12345,
  "credential": {
    "id": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "rawId": "A3B5C7D9E1F2G4H6I8J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiQTNINUQ3RTlGMUcyRzRIOEk4SjBLMUwyTTNONE81UDZRN1I4UzlUMFUxVjJXM1g0WTVaNiIsIm9yaWdpbiI6Imh0dHBzOi8vbG9jYWxob3N0OjgwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2UsImF1dGhlbnRpY2F0b3JEYXRhIjoiU1RaTVlJYlJibUZpYkdsemNHRnpjM2R2Y21WeVgybGtJam9pUTFWVFZFOU5SVkpmTVRJek5EVTJJaXdpYVhOemRXVmtYMlJoZEdVaU9pSXlNREkwTFRFd0xURXdWREV3T2pBd09qQXdXaUlzSW1WNGNHbHllVjlrWVhSbElqb2lNakF5TlMweE1DMHhNRlF4TURvd01Eb3dNRm9pTENKd2NtOWtkV04wSWpvaWRIbHJMVzl3WlhKaGRHOXlJaXdpYldGamFHbHVaVjltYVc1blpYSndjbWx1ZENJNklqRXlNelExTmpjNE9UQXhNak0wSW4wPQ",
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

**Response `200`:**
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

**Response `400` (Invalid assertion):**
```json
{
  "error": "Invalid WebAuthn assertion",
  "code": "INVALID_ASSERTION"
}
```

**Response `401` (Authentication failed):**
```json
{
  "error": "Authentication failed",
  "code": "AUTH_FAILED"
}
```

### `GET /webauthn/credentials/` 
List registered passkeys for the current user.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
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
Delete a registered passkey.

**Headers (required):**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `id`: ID of the passkey to delete

**Response `204`:**
(no content - successful deletion)

**Response `404` (Not found):**
```json
{
  "error": "Passkey not found",
  "code": "NOT_FOUND"
}
```

## Legend

-  — Requires `Authorization: Bearer <access_token>`
- `permission.code` — Requires that specific permission
