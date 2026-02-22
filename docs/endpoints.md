# API Endpoints Reference

All endpoints are prefixed with your configured base path (e.g. `/api/auth/`).

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
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "login": false
}
```

**Response `201`:**
```json
{
  "message": "Registration successful",
  "user": { "id": 1, "email": "user@example.com", ... },
  "verification_required": { "email": true, "phone": false }
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
  "totp_code": "123456"
}
```
`totp_code` is only required if 2FA is enabled.

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
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

---

### `POST /login/phone/`
Login with phone number + password.

**Request:**
```json
{
  "phone_country_code": "+1",
  "phone_number": "5551234567",
  "password": "SecurePass123!",
  "totp_code": "123456"
}
```

---

### `POST /google/`
Authenticate via Google OAuth.

**Request (id_token):**
```json
{ "id_token": "<google-id-token>" }
```

**Request (authorization code):**
```json
{
  "code": "<authorization-code>",
  "redirect_uri": "https://yourapp.com/auth/callback"
}
```

---

## Magic Link (Passwordless)

Requires `TENXYTE_MAGIC_LINK_ENABLED = True`.

### `POST /magic-link/request/`
Request a magic link sent by email.

**Request:**
```json
{ "email": "user@example.com" }
```

**Response `200`:**
```json
{ "message": "Magic link sent" }
```

---

### `POST /magic-link/verify/`
Verify a magic link token and receive JWT tokens.

**Request:**
```json
{ "token": "<magic-link-token>" }
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
  "refresh_token": "eyJ..."
}
```

---

### `POST /logout/`
Logout (revokes refresh token + blacklists access token).

**Request:**
```json
{ "refresh_token": "eyJ..." }
```

---

### `POST /logout/all/` 🔒
Logout from all devices.

**Response `200`:**
```json
{ "message": "Logged out from 3 devices" }
```

---

## OTP Verification

### `POST /otp/request/`
Request an OTP code (email or phone verification).

**Request:**
```json
{ "type": "email" }
```
`type`: `"email"` or `"phone"`

---

### `POST /otp/verify/email/` 🔒
Verify email with OTP code.

**Request:**
```json
{ "code": "123456" }
```

---

### `POST /otp/verify/phone/` 🔒
Verify phone with OTP code.

**Request:**
```json
{ "code": "123456" }
```

---

## Password Management

### `POST /password/reset/request/`
Request a password reset email.

**Request:**
```json
{ "email": "user@example.com" }
```

---

### `POST /password/reset/confirm/`
Confirm password reset with OTP code.

**Request:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "NewSecurePass456!"
}
```

---

### `POST /password/change/` 🔒
Change password (requires current password).

**Request:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

---

### `POST /password/strength/`
Check password strength without saving.

**Request:**
```json
{ "password": "MyPassword123!" }
```

**Response `200`:**
```json
{
  "score": 4,
  "is_valid": true,
  "feedback": []
}
```

---

### `GET /password/requirements/`
Get the current password policy requirements.

---

## User Profile

### `GET /me/` 🔒
Get the current user's profile.

### `PATCH /me/` 🔒
Update the current user's profile.

**Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Doe"
}
```

---

### `GET /me/roles/` 🔒
Get the current user's roles and permissions.

---

## Two-Factor Authentication (2FA)

### `GET /2fa/status/` 🔒
Get 2FA status for the current user.

**Response `200`:**
```json
{
  "is_enabled": false,
  "has_backup_codes": false
}
```

---

### `POST /2fa/setup/` 🔒
Initiate 2FA setup. Returns QR code and backup codes.

**Response `200`:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "provisioning_uri": "otpauth://totp/...",
  "backup_codes": ["abc123", "def456", ...],
  "warning": "Save the backup codes securely."
}
```

---

### `POST /2fa/confirm/` 🔒
Confirm 2FA activation with a TOTP code.

**Request:**
```json
{ "code": "123456" }
```

---

### `POST /2fa/disable/` 🔒
Disable 2FA (requires TOTP code or backup code).

**Request:**
```json
{ "code": "123456" }
```

---

### `POST /2fa/backup-codes/` 🔒
Regenerate backup codes (invalidates old ones).

**Request:**
```json
{ "code": "123456" }
```

---

## RBAC — Permissions

### `GET /permissions/` 🔒 `permissions.view`
List all permissions.

### `POST /permissions/` 🔒 `permissions.manage`
Create a permission.

**Request:**
```json
{ "code": "posts.publish", "name": "Publish Posts" }
```

### `GET /permissions/<id>/` 🔒 `permissions.view`
Get a permission.

### `PUT /permissions/<id>/` 🔒 `permissions.manage`
Update a permission.

### `DELETE /permissions/<id>/` 🔒 `permissions.manage`
Delete a permission.

---

## RBAC — Roles

### `GET /roles/` 🔒 `roles.view`
List all roles.

### `POST /roles/` 🔒 `roles.manage`
Create a role.

**Request:**
```json
{
  "name": "Editor",
  "description": "Can edit content",
  "parent": null
}
```

### `GET /roles/<id>/` 🔒 `roles.view`
Get a role.

### `PUT /roles/<id>/` 🔒 `roles.manage`
Update a role.

### `DELETE /roles/<id>/` 🔒 `roles.manage`
Delete a role.

### `GET /roles/<id>/permissions/` 🔒 `roles.view`
List permissions assigned to a role.

### `POST /roles/<id>/permissions/` 🔒 `roles.manage`
Assign permissions to a role.

---

## RBAC — User Roles & Permissions

### `GET /users/<id>/roles/` 🔒 `users.manage`
List roles assigned to a user.

### `POST /users/<id>/roles/` 🔒 `users.manage`
Assign a role to a user.

### `DELETE /users/<id>/roles/` 🔒 `users.manage`
Remove a role from a user.

### `GET /users/<id>/permissions/` 🔒 `users.manage`
List direct permissions for a user.

### `POST /users/<id>/permissions/` 🔒 `users.manage`
Assign a direct permission to a user.

---

## Applications

### `GET /applications/` 🔒 `applications.view`
List all applications.

### `POST /applications/` 🔒 `applications.manage`
Create an application.

### `GET /applications/<id>/` 🔒 `applications.view`
Get an application.

### `PUT /applications/<id>/` 🔒 `applications.manage`
Update an application.

### `DELETE /applications/<id>/` 🔒 `applications.manage`
Delete an application.

### `POST /applications/<id>/regenerate/` 🔒 `applications.manage`
Regenerate the application's access secret.

---

## Admin — User Management

### `GET /admin/users/` 🔒 `users.view`
List all users with filtering and pagination.

Query params: `?search=john&is_active=true&page=1`

### `GET /admin/users/<id>/` 🔒 `users.view`
Get a user's full profile.

### `POST /admin/users/<id>/ban/` 🔒 `users.ban`
Ban a user.

**Request:**
```json
{ "reason": "Terms of service violation" }
```

### `POST /admin/users/<id>/unban/` 🔒 `users.ban`
Unban a user.

### `POST /admin/users/<id>/lock/` 🔒 `users.lock`
Lock a user account.

**Request:**
```json
{ "duration_minutes": 60 }
```

### `POST /admin/users/<id>/unlock/` 🔒 `users.lock`
Unlock a user account.

---

## Admin — Security

### `GET /admin/audit-logs/` 🔒 `audit.view`
List audit log entries.

Query params: `?action=login&user_id=1&from=2026-01-01`

### `GET /admin/audit-logs/<id>/` 🔒 `audit.view`
Get a single audit log entry.

### `GET /admin/login-attempts/` 🔒 `audit.view`
List login attempts.

### `GET /admin/blacklisted-tokens/` 🔒 `audit.view`
List active blacklisted tokens.

### `POST /admin/blacklisted-tokens/cleanup/` 🔒 `audit.manage`
Remove expired blacklisted tokens.

### `GET /admin/refresh-tokens/` 🔒 `audit.view`
List active refresh tokens.

### `POST /admin/refresh-tokens/<id>/revoke/` 🔒 `audit.manage`
Revoke a specific refresh token.

---

## Admin — GDPR

### `GET /admin/deletion-requests/` 🔒 `gdpr.view`
List account deletion requests.

### `GET /admin/deletion-requests/<id>/` 🔒 `gdpr.view`
Get a deletion request.

### `POST /admin/deletion-requests/<id>/process/` 🔒 `gdpr.manage`
Process (execute) a deletion request.

### `POST /admin/deletion-requests/process-expired/` 🔒 `gdpr.manage`
Process all expired grace period deletions.

---

## User — GDPR

### `POST /request-account-deletion/` 🔒
Request account deletion (starts grace period).

### `POST /confirm-account-deletion/` 🔒
Confirm account deletion request.

### `POST /cancel-account-deletion/` 🔒
Cancel a pending deletion request.

### `GET /account-deletion-status/` 🔒
Get the status of the current deletion request.

### `GET /export-user-data/` 🔒
Export all personal data (GDPR Article 20).

---

## Dashboard

All dashboard endpoints require `dashboard.view` permission.

### `GET /dashboard/stats/` 🔒 `dashboard.view`
Global cross-module statistics.

### `GET /dashboard/auth/` 🔒 `dashboard.view`
Detailed authentication statistics (login rates, token stats, charts).

### `GET /dashboard/security/` 🔒 `dashboard.view`
Security statistics (audit summary, blacklisted tokens, suspicious activity).

### `GET /dashboard/gdpr/` 🔒 `dashboard.view`
GDPR compliance statistics.

### `GET /dashboard/organizations/` 🔒 `dashboard.view`
Organization statistics (only if `TENXYTE_ORGANIZATIONS_ENABLED=True`).

---

## Organizations (opt-in)

Enable with `TENXYTE_ORGANIZATIONS_ENABLED = True`.

All organization endpoints require the `X-Org-Slug` header to identify the target organization:
```
X-Org-Slug: acme-corp
```

### `POST /organizations/` 🔒
Create an organization.

### `GET /organizations/list/` 🔒
List organizations the current user belongs to.

### `GET /organizations/detail/` 🔒
Get organization details.

### `PATCH /organizations/update/` 🔒
Update an organization.

### `DELETE /organizations/delete/` 🔒
Delete an organization.

### `GET /organizations/tree/` 🔒
Get the full organization hierarchy tree.

### `GET /organizations/members/` 🔒
List organization members.

### `POST /organizations/members/add/` 🔒
Add a member to an organization.

### `PATCH /organizations/members/<user_id>/` 🔒
Update a member's role.

### `DELETE /organizations/members/<user_id>/remove/` 🔒
Remove a member from an organization.

### `POST /organizations/invitations/` 🔒
Invite a user to an organization by email.

### `GET /org-roles/` 🔒
List organization-scoped roles.

---

## WebAuthn / Passkeys (FIDO2)

Requires `TENXYTE_WEBAUTHN_ENABLED = True` and `pip install py-webauthn`.

### `POST /webauthn/register/begin/` 🔒
Begin passkey registration. Returns a challenge.

**Response `200`:**
```json
{ "challenge": "...", "rp": { "id": "yourapp.com", "name": "Your App" }, ... }
```

---

### `POST /webauthn/register/complete/` 🔒
Complete passkey registration with the authenticator response.

**Request:**
```json
{ "id": "...", "rawId": "...", "response": { ... }, "type": "public-key" }
```

---

### `POST /webauthn/authenticate/begin/`
Begin passkey authentication. Returns a challenge.

**Request:**
```json
{ "email": "user@example.com" }
```

---

### `POST /webauthn/authenticate/complete/`
Complete passkey authentication. Returns JWT tokens.

**Request:**
```json
{ "id": "...", "rawId": "...", "response": { ... }, "type": "public-key" }
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

---

### `GET /webauthn/credentials/` 🔒
List registered passkeys for the current user.

---

### `DELETE /webauthn/credentials/<id>/` 🔒
Delete a registered passkey.

---

## Legend

- 🔒 — Requires `Authorization: Bearer <access_token>`
- `permission.code` — Requires that specific permission
