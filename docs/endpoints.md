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

### `POST /permissions/` 🔒 `permissions.manage`
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

### `GET /permissions/<id>/` 🔒 `permissions.view`
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

### `PUT /permissions/<id>/` 🔒 `permissions.manage`
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

### `DELETE /permissions/<id>/` 🔒 `permissions.manage`
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

### `GET /roles/` 🔒 `roles.view`
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

### `POST /roles/` 🔒 `roles.manage`
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

### `GET /roles/<id>/` 🔒 `roles.view`
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

### `PUT /roles/<id>/` 🔒 `roles.manage`
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

### `DELETE /roles/<id>/` 🔒 `roles.manage`
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

### `GET /roles/<id>/permissions/` 🔒 `roles.view`
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

### `POST /roles/<id>/permissions/` 🔒 `roles.manage`
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

### `GET /users/<id>/roles/` 🔒 `users.manage`
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

### `POST /users/<id>/roles/` 🔒 `users.manage`
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

### `DELETE /users/<id>/roles/` 🔒 `users.manage`
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

### `GET /users/<id>/permissions/` 🔒 `users.manage`
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

### `POST /users/<id>/permissions/` 🔒 `users.manage`
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

### `GET /applications/` 🔒 `applications.view`
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

### `POST /applications/` 🔒 `applications.manage`
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

### `GET /applications/<id>/` 🔒 `applications.view`
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

### `PUT /applications/<id>/` 🔒 `applications.manage`
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

### `DELETE /applications/<id>/` 🔒 `applications.manage`
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

### `POST /applications/<id>/regenerate/` 🔒 `applications.manage`
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

### `GET /admin/users/` 🔒 `users.view`
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

### `GET /admin/users/<id>/` 🔒 `users.view`
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

### `POST /admin/users/<id>/ban/` 🔒 `users.ban`
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

### `POST /admin/users/<id>/unban/` 🔒 `users.ban`
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

### `POST /admin/users/<id>/lock/` 🔒 `users.lock`
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

### `POST /admin/users/<id>/unlock/` 🔒 `users.lock`
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

### `GET /admin/audit-logs/` 🔒 `audit.view`
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

### `GET /admin/audit-logs/<id>/` 🔒 `audit.view`
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

### `GET /admin/login-attempts/` 🔒 `audit.view`
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

### `GET /admin/blacklisted-tokens/` 🔒 `audit.view`
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

### `POST /admin/blacklisted-tokens/cleanup/` 🔒 `security.view`
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

### `GET /admin/refresh-tokens/` 🔒 `audit.view`
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

### `POST /admin/refresh-tokens/<id>/revoke/` 🔒 `security.view`
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

### `GET /admin/deletion-requests/` 🔒 `gdpr.view`
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

### `GET /admin/deletion-requests/<id>/` 🔒 `gdpr.admin`
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

### `POST /admin/deletion-requests/<id>/process/` 🔒 `gdpr.process`
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

### `POST /admin/deletion-requests/process-expired/` 🔒 `gdpr.process`
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

### `POST /request-account-deletion/` 🔒
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

### `POST /confirm-account-deletion/` 🔒
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

### `POST /cancel-account-deletion/` 🔒
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

### `GET /account-deletion-status/` 🔒
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

### `POST /export-user-data/` 🔒
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
