# API Endpoints Reference

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

### `POST /logout/all/` 🔒
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

### `POST /otp/request/` 🔒
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

### `POST /otp/verify/email/` 🔒
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

### `POST /otp/verify/phone/` 🔒
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

### `POST /password/change/` 🔒
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

### `GET /me/` 🔒
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

### `PATCH /me/` 🔒
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

### `GET /me/roles/` 🔒
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

### `GET /2fa/status/` 🔒
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

### `POST /2fa/setup/` 🔒
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

### `POST /2fa/confirm/` 🔒
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

### `POST /2fa/disable/` 🔒
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

### `POST /2fa/backup-codes/` 🔒
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

### `GET /permissions/` 🔒 `permissions.view`
List all permissions.

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

### `POST /permissions/` 🔒 `permissions.manage`
Create a permission.

**Request:**
```json
{ "code": "posts.publish", "name": "Publish Posts" }
```

**Response `201`:**
```json
{
  "id": "2",
  "code": "posts.publish",
  "name": "Publish Posts",
  "description": ""
}
```

### `GET /permissions/<id>/` 🔒 `permissions.view`
Get a permission.

**Response `200`:**
```json
{
  "id": "1",
  "code": "users.view",
  "name": "View users"
}
```

### `PUT /permissions/<id>/` 🔒 `permissions.manage`
Update a permission.

**Request:**
```json
{
  "code": "users.view",
  "name": "View all users"
}
```

**Response `200`:**
```json
{
  "id": "1",
  "code": "users.view",
  "name": "View all users"
}
```

### `DELETE /permissions/<id>/` 🔒 `permissions.manage`
Delete a permission.

**Response `204`:**
```json
{}
```

---

## RBAC — Roles

### `GET /roles/` 🔒 `roles.view`
List all roles.

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "name": "Editor",
      "description": "Can edit content"
    }
  ]
}
```

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

**Response `201`:**
```json
{
  "id": "1",
  "name": "Editor",
  "description": "Can edit content",
  "parent": null
}
```

### `GET /roles/<id>/` 🔒 `roles.view`
Get a role.

**Response `200`:**
```json
{
  "id": "1",
  "name": "Editor",
  "description": "Can edit content"
}
```

### `PUT /roles/<id>/` 🔒 `roles.manage`
Update a role.

**Request:**
```json
{
  "name": "Senior Editor",
  "description": "Can edit and publish"
}
```

**Response `200`:**
```json
{
  "id": "1",
  "name": "Senior Editor",
  "description": "Can edit and publish"
}
```

### `DELETE /roles/<id>/` 🔒 `roles.manage`
Delete a role.

**Response `204`:**
```json
{}
```

### `GET /roles/<id>/permissions/` 🔒 `roles.view`
List permissions assigned to a role.

**Response `200`:**
```json
[
  {
    "id": "1",
    "code": "posts.publish",
    "name": "Publish Posts"
  }
]
```

### `POST /roles/<id>/permissions/` 🔒 `roles.manage`
Assign permissions to a role.

**Request:**
```json
{
  "permission_ids": ["1", "2"]
}
```

**Response `200`:**
```json
{
  "message": "Permissions assigned successfully"
}
```

---

## RBAC — User Roles & Permissions

### `GET /users/<id>/roles/` 🔒 `users.manage`
List roles assigned to a user.

**Response `200`:**
```json
[
  {
    "id": "1",
    "name": "Editor"
  }
]
```

### `POST /users/<id>/roles/` 🔒 `users.manage`
Assign a role to a user.

**Request:**
```json
{
  "role_ids": ["1"]
}
```

**Response `200`:**
```json
{
  "message": "Roles assigned successfully"
}
```

### `DELETE /users/<id>/roles/` 🔒 `users.manage`
Remove a role from a user.

**Request:**
```json
{
  "role_ids": ["1"]
}
```

**Response `200`:**
```json
{
  "message": "Roles removed successfully"
}
```

### `GET /users/<id>/permissions/` 🔒 `users.manage`
List direct permissions for a user.

**Response `200`:**
```json
[
  {
    "id": "1",
    "code": "posts.view"
  }
]
```

### `POST /users/<id>/permissions/` 🔒 `users.manage`
Assign a direct permission to a user.

**Request:**
```json
{
  "permission_ids": ["1"]
}
```

**Response `200`:**
```json
{
  "message": "Permissions assigned successfully"
}
```

---

## Applications

### `GET /applications/` 🔒 `applications.view`
List all applications.

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
      "is_active": true
    }
  ]
}
```

### `POST /applications/` 🔒 `applications.manage`
Create an application.

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
  "id": "app_124",
  "name": "My Next.js App",
  "access_key": "ak_abc123",
  "access_secret": "as_def456"
}
```

### `GET /applications/<id>/` 🔒 `applications.view`
Get an application.

**Response `200`:**
```json
{
  "id": "app_124",
  "name": "My Next.js App",
  "access_key": "ak_abc123"
}
```

### `PUT /applications/<id>/` 🔒 `applications.manage`
Update an application.

**Request:**
```json
{
  "name": "Updated App Name"
}
```

**Response `200`:**
```json
{
  "id": "app_124",
  "name": "Updated App Name"
}
```

### `DELETE /applications/<id>/` 🔒 `applications.manage`
Delete an application.

**Response `204`:**
```json
{}
```

### `POST /applications/<id>/regenerate/` 🔒 `applications.manage`
Regenerate the application's access secret.

**Request:**
```json
{}
```

**Response `200`:**
```json
{
  "id": "app_124",
  "access_key": "ak_abc123",
  "access_secret": "as_new789"
}
```

---

## Admin — User Management

### `GET /admin/users/` 🔒 `users.view`
List all users with filtering and pagination.

Query params: `?search=john&is_active=true&page=1`

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "is_banned": false,
      "roles": ["admin"]
    }
  ]
}
```

### `GET /admin/users/<id>/` 🔒 `users.view`
Get a user's full profile.

**Response `200`:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_banned": false,
  "roles": ["admin"]
}
```

### `POST /admin/users/<id>/ban/` 🔒 `users.ban`
Ban a user.

**Request:**
```json
{ "reason": "Terms of service violation" }
```

**Response `200`:**
```json
{
  "message": "User banned successfully"
}
```

### `POST /admin/users/<id>/unban/` 🔒 `users.ban`
Unban a user.

**Response `200`:**
```json
{
  "message": "User unbanned successfully"
}
```

### `POST /admin/users/<id>/lock/` 🔒 `users.lock`
Lock a user account.

**Request:**
```json
{ "duration_minutes": 60 }
```

**Response `200`:**
```json
{
  "message": "User locked for 60 minutes"
}
```

### `POST /admin/users/<id>/unlock/` 🔒 `users.lock`
Unlock a user account.

**Response `200`:**
```json
{
  "message": "User unlocked successfully"
}
```

---

## Admin — Security

### `GET /admin/audit-logs/` 🔒 `audit.view`
List audit log entries.

Query params: `?action=login&user_id=1&from=2026-01-01`

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "action": "login",
      "user_id": 1,
      "timestamp": "2023-10-01T12:00:00Z",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0..."
    }
  ]
}
```

### `GET /admin/audit-logs/<id>/` 🔒 `audit.view`
Get a single audit log entry.

**Response `200`:**
```json
{
  "id": 1,
  "action": "login",
  "user_id": 1,
  "timestamp": "2023-10-01T12:00:00Z"
}
```

### `GET /admin/login-attempts/` 🔒 `audit.view`
List login attempts.

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user_id": 1,
      "email": "user@example.com",
      "successful": false,
      "ip_address": "127.0.0.1",
      "timestamp": "2023-10-01T12:00:00Z"
    }
  ]
}
```

### `GET /admin/blacklisted-tokens/` 🔒 `audit.view`
List active blacklisted tokens.

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "jti": "jti12345",
      "blacklisted_on": "2023-10-01T12:00:00Z"
    }
  ]
}
```

### `POST /admin/blacklisted-tokens/cleanup/` 🔒 `audit.manage`
Remove expired blacklisted tokens.

**Response `200`:**
```json
{
  "message": "10 expired tokens cleaned up",
  "deleted_count": 10
}
```

### `GET /admin/refresh-tokens/` 🔒 `audit.view`
List active refresh tokens.

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "jti": "rt123",
      "user_id": 1,
      "expires_at": "2023-11-01T12:00:00Z",
      "is_revoked": false
    }
  ]
}
```

### `POST /admin/refresh-tokens/<id>/revoke/` 🔒 `audit.manage`
Revoke a specific refresh token.

**Response `200`:**
```json
{
  "message": "Token revoked successfully"
}
```

---

## Admin — GDPR

### `GET /admin/deletion-requests/` 🔒 `gdpr.view`
List account deletion requests.

**Response `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user_id": 1,
      "status": "pending",
      "requested_at": "2023-10-01T12:00:00Z",
      "deletion_date": "2023-10-31T12:00:00Z"
    }
  ]
}
```

### `GET /admin/deletion-requests/<id>/` 🔒 `gdpr.view`
Get a deletion request.

**Response `200`:**
```json
{
  "id": 1,
  "user_id": 1,
  "status": "pending",
  "requested_at": "2023-10-01T12:00:00Z",
  "deletion_date": "2023-10-31T12:00:00Z"
}
```

### `POST /admin/deletion-requests/<id>/process/` 🔒 `gdpr.manage`
Process (execute) a deletion request.

**Request:**
```json
{}
```

**Response `200`:**
```json
{
  "message": "Account successfully deleted"
}
```

### `POST /admin/deletion-requests/process-expired/` 🔒 `gdpr.manage`
Process all expired grace period deletions.

**Response `200`:**
```json
{
  "message": "Processed 5 expired deletion requests",
  "processed_count": 5
}
```

---

## User — GDPR

### `POST /request-account-deletion/` 🔒
Request account deletion (starts grace period).

**Request:**
```json
{
  "reason": "No longer using the service"
}
```

**Response `201`:**
```json
{
  "message": "Account deletion requested",
  "deletion_date": "2023-10-31T12:00:00Z"
}
```

### `POST /confirm-account-deletion/` 🔒
Confirm account deletion request.

**Request:**
```json
{
  "confirmation_code": "123456"
}
```

**Response `200`:**
```json
{
  "message": "Account deletion confirmed"
}
```

### `POST /cancel-account-deletion/` 🔒
Cancel a pending deletion request.

**Request:**
```json
{}
```

**Response `200`:**
```json
{
  "message": "Account deletion cancelled"
}
```

### `GET /account-deletion-status/` 🔒
Get the status of the current deletion request.

**Response `200`:**
```json
{
  "has_pending_request": true,
  "status": "pending",
  "deletion_date": "2023-10-31T12:00:00Z"
}
```

### `POST /export-user-data/` 🔒
Export all personal data (GDPR Article 20).

**Request:**
```json
{}
```

**Response `200`:**
```json
{
  "profile": {},
  "activity": [],
  "security": {}
}
```

---

## Dashboard

All dashboard endpoints require `dashboard.view` permission.

### `GET /dashboard/stats/` 🔒 `dashboard.view`
Global cross-module statistics.

**Response `200`:**
```json
{
  "total_users": 1500,
  "active_users": 1200,
  "new_users_today": 15
}
```

### `GET /dashboard/auth/` 🔒 `dashboard.view`
Detailed authentication statistics (login rates, token stats, charts).

**Response `200`:**
```json
{
  "logins_today": 350,
  "failed_logins_today": 12,
  "active_sessions": 240
}
```

### `GET /dashboard/security/` 🔒 `dashboard.view`
Security statistics (audit summary, blacklisted tokens, suspicious activity).

**Response `200`:**
```json
{
  "total_banned_users": 5,
  "total_locked_users": 2,
  "suspicious_activities_7d": 18
}
```

### `GET /dashboard/gdpr/` 🔒 `dashboard.view`
GDPR compliance statistics.

**Response `200`:**
```json
{
  "pending_deletions": 3,
  "processed_deletions": 15,
  "data_exports_30d": 8
}
```

### `GET /dashboard/organizations/` 🔒 `dashboard.view`
Organization statistics (only if `TENXYTE_ORGANIZATIONS_ENABLED=True`).

**Response `200`:**
```json
{
  "total_organizations": 45,
  "active_organizations": 40,
  "average_members_per_org": 8.5
}
```

---

## Organizations (opt-in)

Enable with `TENXYTE_ORGANIZATIONS_ENABLED = True`.

All organization endpoints require the `X-Org-Slug` header to identify the target organization:
```
X-Org-Slug: acme-corp
```

### `POST /organizations/` 🔒
Create an organization.

**Request:**
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp"
}
```

**Response `201`:**
```json
{
  "id": "1",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "created_at": "2023-10-01T12:00:00Z"
}
```

### `GET /organizations/list/` 🔒
List organizations the current user belongs to.

**Response `200`:**
```json
[
  {
    "id": "1",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "role": "owner"
  }
]
```

### `GET /organizations/detail/` 🔒
Get organization details.

**Response `200`:**
```json
{
  "id": "1",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "created_at": "2023-10-01T12:00:00Z"
}
```

### `PATCH /organizations/update/` 🔒
Update an organization.

**Request:**
```json
{
  "name": "Acme Corporation"
}
```

**Response `200`:**
```json
{
  "id": "1",
  "name": "Acme Corporation",
  "slug": "acme-corp"
}
```

### `DELETE /organizations/delete/` 🔒
Delete an organization.

**Response `200`:**
```json
{
  "message": "Organization deleted successfully"
}
```

### `GET /organizations/tree/` 🔒
Get the full organization hierarchy tree.

**Response `200`:**
```json
{
  "id": "1",
  "name": "Acme Corp",
  "children": []
}
```

### `GET /organizations/members/` 🔒
List organization members.

**Response `200`:**
```json
[
  {
    "user_id": 1,
    "email": "user@example.com",
    "role": "member",
    "joined_at": "2023-10-01T12:00:00Z"
  }
]
```

### `POST /organizations/members/add/` 🔒
Add a member to an organization.

**Request:**
```json
{
  "user_id": 2,
  "role": "member"
}
```

**Response `201`:**
```json
{
  "message": "Member added successfully"
}
```

### `PATCH /organizations/members/<user_id>/` 🔒
Update a member's role.

**Request:**
```json
{
  "role": "admin"
}
```

**Response `200`:**
```json
{
  "message": "Member role updated"
}
```

### `DELETE /organizations/members/<user_id>/remove/` 🔒
Remove a member from an organization.

**Response `200`:**
```json
{
  "message": "Member removed successfully"
}
```

### `POST /organizations/invitations/` 🔒
Invite a user to an organization by email.

**Request:**
```json
{
  "email": "newuser@example.com",
  "role": "member"
}
```

**Response `201`:**
```json
{
  "message": "Invitation sent"
}
```

### `GET /org-roles/` 🔒
List organization-scoped roles.

**Response `200`:**
```json
[
  {
    "id": "1",
    "name": "Admin",
    "permissions": ["org.manage", "org.invite"]
  }
]
```

---

## WebAuthn / Passkeys (FIDO2)

Requires `TENXYTE_WEBAUTHN_ENABLED = True` and `pip install py-webauthn`.

### `POST /webauthn/register/begin/` 🔒
Begin passkey registration. Returns a challenge.

**Response `200`:**
```json
{ "challenge": "...", "rp": { "id": "yourapp.com", "name": "Your App" }, "user": { "id": "...", "name": "user@example.com", "displayName": "user@example.com" } }
```

### `POST /webauthn/register/complete/` 🔒
Complete passkey registration with the authenticator response.

**Request:**
```json
{ "id": "...", "rawId": "...", "response": { "clientDataJSON": "...", "attestationObject": "..." }, "type": "public-key" }
```

**Response `201`:**
```json
{
  "message": "Passkey registered successfully"
}
```

### `POST /webauthn/authenticate/begin/`
Begin passkey authentication. Returns a challenge.

**Request:**
```json
{ "email": "user@example.com" }
```

**Response `200`:**
```json
{ "challenge": "...", "timeout": 60000, "rpId": "yourapp.com" }
```

### `POST /webauthn/authenticate/complete/`
Complete passkey authentication. Returns JWT tokens.

**Request:**
```json
{ "id": "...", "rawId": "...", "response": { "clientDataJSON": "...", "authenticatorData": "...", "signature": "...", "userHandle": "..." }, "type": "public-key" }
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

### `GET /webauthn/credentials/` 🔒
List registered passkeys for the current user.

**Response `200`:**
```json
[
  {
    "id": "cred_123",
    "name": "YubiKey 5",
    "created_at": "2023-10-01T12:00:00Z"
  }
]
```

### `DELETE /webauthn/credentials/<id>/` 🔒
Delete a registered passkey.

**Response `200`:**
```json
{
  "message": "Passkey deleted"
}
```

## Legend

- 🔒 — Requires `Authorization: Bearer <access_token>`
- `permission.code` — Requires that specific permission
