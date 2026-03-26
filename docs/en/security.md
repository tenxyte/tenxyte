# Security Guide

Tenxyte provides multiple layers of security out of the box.

## Table of Contents
- [Rate Limiting](#rate-limiting)
- [Account Lockout](#account-lockout)
- [Two-Factor Authentication (2FA / TOTP)](#two-factor-authentication-2fa--totp)
- [JWT Token Security](#jwt-token-security)
- [Session & Device Limits](#session--device-limits)
- [Password Security](#password-security)
- [Security Headers](#security-headers)
- [CORS](#cors)
- [Audit Logging](#audit-logging)
- [OTP Verification](#otp-verification)
- [Production Checklist](#production-checklist)

---

## Rate Limiting

### Built-in Throttle Classes

Tenxyte ships with pre-configured throttle classes for sensitive endpoints:

| Class | Default Rate | Applied to |
|---|---|---|
| `LoginThrottle` | 5/min | Login endpoints |
| `LoginHourlyThrottle` | 20/hour | Login endpoints |
| `RegisterThrottle` | 3/hour | Register endpoint |
| `RegisterDailyThrottle` | 10/day | Register endpoint |
| `RefreshTokenThrottle` | 30/min | Token refresh |
| `ProgressiveLoginThrottle` | Progressive | Login endpoints (increases delay after each failure) |
| `OTPRequestThrottle` | 5/hour | OTP request |
| `OTPVerifyThrottle` | 5/min | OTP verification |
| `PasswordResetThrottle` | 3/hour | Password reset request |
| `PasswordResetDailyThrottle` | 10/day | Password reset request |
| `MagicLinkRequestThrottle` | 3/hour | Magic link request |
| `MagicLinkVerifyThrottle` | 10/min | Magic link verification |

### Custom URL-Based Throttling

Apply rate limits to any URL without writing a custom class:

```python
# settings.py
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/products/': '100/hour',
    '/api/v1/search/': '30/min',
    '/api/v1/upload/': '5/hour',
    '/api/v1/health/$': '1000/min',  # $ = exact match
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'tenxyte.throttles.SimpleThrottleRule',
    ],
}
```

### Disable Throttling in Tests

```python
# In your test helpers
from unittest.mock import patch

with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
    response = client.post('/api/v1/auth/login/email/', data)
```

---

## Account Lockout

After `TENXYTE_MAX_LOGIN_ATTEMPTS` (default: 5) failed login attempts within `TENXYTE_RATE_LIMIT_WINDOW_MINUTES` (default: 15 min), the account is locked for `TENXYTE_LOCKOUT_DURATION_MINUTES` (default: 30 min).

```python
# settings.py
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = True
TENXYTE_MAX_LOGIN_ATTEMPTS = 5
TENXYTE_LOCKOUT_DURATION_MINUTES = 30
TENXYTE_RATE_LIMIT_WINDOW_MINUTES = 15
```

Locked accounts return `401` with `code: 'ACCOUNT_LOCKED'`.

### Exponential Lockout

When `TENXYTE_LOCKOUT_ESCALATION_ENABLED = True` (default), each consecutive lockout doubles the duration, capped at `TENXYTE_LOCKOUT_MAX_DURATION_MINUTES` (default: 1440 = 24h):

| Lockout # | Duration (base=30min) |
|---|---|
| 1st | 30 min |
| 2nd | 60 min |
| 3rd | 120 min |
| 4th | 240 min |
| 5th+ | 1440 min (24h cap) |

The counter resets after a successful login. Formula: `min(base × 2^(n-1), max_duration)`.

```python
TENXYTE_LOCKOUT_ESCALATION_ENABLED = True
TENXYTE_LOCKOUT_MAX_DURATION_MINUTES = 1440  # 24h cap
```

Admin unlock via API:
```bash
POST /api/v1/auth/admin/users/<id>/unlock/
```

---

## Two-Factor Authentication (2FA / TOTP)

### Setup Flow

1. User calls `POST /2fa/setup/` → receives QR code + backup codes
2. User scans QR code with Google Authenticator / Authy
3. User calls `POST /2fa/confirm/` with first TOTP code → 2FA activated

### Login with 2FA

```bash
POST /api/v1/auth/login/email/
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "totp_code": "123456"
}
```

If `totp_code` is missing when 2FA is enabled, the response is:
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

### Backup Codes

Generated at setup time (`TENXYTE_BACKUP_CODES_COUNT`, default: 10).
Each code is single-use. Regenerate with `POST /2fa/backup-codes/`.

### Configuration

```python
TENXYTE_TOTP_ISSUER = 'MyApp'        # Name shown in authenticator app
TENXYTE_TOTP_VALID_WINDOW = 1        # Accept ±1 period (30s tolerance)
TENXYTE_BACKUP_CODES_COUNT = 10
```

---

## JWT Token Security

### Algorithm

Tenxyte defaults to `HS256` (HMAC-SHA256). For production, switch to an asymmetric algorithm (`RS256`, `EdDSA`) to avoid sharing the signing secret across services:

```python
# settings.py
TENXYTE_JWT_ALGORITHM = 'RS256'
TENXYTE_JWT_PRIVATE_KEY = open('/secrets/jwt_private.pem').read()
TENXYTE_JWT_PUBLIC_KEY = open('/secrets/jwt_public.pem').read()
```

> **Note**: When `HS256` is detected, Tenxyte emits a `SecurityWarning` on service initialization. Use the `production` or `enterprise` secure mode preset to automatically switch to RS256.

### Access Token Blacklisting

When `TENXYTE_TOKEN_BLACKLIST_ENABLED = True` (default), access tokens are blacklisted on logout. This prevents token reuse even before expiry.

```python
TENXYTE_TOKEN_BLACKLIST_ENABLED = True
```

### Refresh Token Rotation

When `TENXYTE_REFRESH_TOKEN_ROTATION = True` (default), each call to `/refresh/` issues a **new** refresh token and invalidates the old one. This limits the damage from a stolen refresh token.

```python
TENXYTE_REFRESH_TOKEN_ROTATION = True
```

### Short-Lived Access Tokens

Access tokens expire after **15 minutes by default**. This limits the exposure window if a token is compromised. Rely on refresh tokens for session persistence:

```python
# Defaults — already secure
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 900    # 15 minutes
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 604800 # 7 days
```

### GDPR / Data Minimization

Avoid including PII (email, IP address, phone number, etc.) in JWT payloads. JWT tokens are base64-encoded and readable by anyone who intercepts them. Tenxyte emits a `SecurityWarning` if sensitive keys are detected in `extra_claims`:

```python
# ❌ Do NOT do this
jwt_service.generate_access_token(user_id, app_id, extra_claims={"email": user.email})

# ✅ Look up by user_id instead
user = User.objects.get(pk=decoded_token.user_id)
```

Claims that trigger the warning: `email`, `password`, `phone`, `phone_number`, `ip`, `ip_address`, `address`, `ssn`, `credit_card`, `dob`, `date_of_birth`.

### Required Claims

All issued tokens include `exp`, `iat`, and `jti`. When `JWT_ISSUER` or `JWT_AUDIENCE` are configured, `iss` and `aud` are also enforced as required claims — tokens missing them are rejected at the PyJWT decoding level.

### Key Rotation

Rotate JWT signing keys without invalidating active tokens. Set the **previous** key so existing tokens can still be verified during the transition:

```python
# 1. Generate a new key
# 2. Move the current key to PREVIOUS
TENXYTE_JWT_PREVIOUS_SECRET_KEY = '<old-key>'  # HS256
# or for RS256:
TENXYTE_JWT_PREVIOUS_PUBLIC_KEY = open('/secrets/old_jwt_public.pem').read()

# 3. Set the new key
TENXYTE_JWT_SECRET_KEY = '<new-key>'
```

New tokens are signed with the current key. On decode, if the primary key fails with `InvalidSignatureError`, Tenxyte retries with the previous key. Remove `PREVIOUS_*` once all old tokens have expired.

### Cookie-Based Refresh Tokens

Opt-in mode to transport refresh tokens in `HttpOnly; Secure; SameSite` cookies instead of the JSON body, preventing XSS-based token theft:

```python
TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED = True  # Default: False
TENXYTE_REFRESH_TOKEN_COOKIE_NAME = 'tenxyte_refresh'
TENXYTE_REFRESH_TOKEN_COOKIE_SAMESITE = 'Strict'
TENXYTE_REFRESH_TOKEN_COOKIE_PATH = '/api/v1/auth/'
```

When enabled:
- **Login/Refresh responses**: `refresh_token` is removed from the JSON body and set as a `Set-Cookie` header.
- **Refresh requests**: The server reads the refresh token from the cookie if the body is empty.
- **Logout**: The cookie is cleared with `max-age=0`.

> **Important**: This is **opt-in** and disabled by default. Clients must handle the absence of `refresh_token` in JSON responses.

---

## Session & Device Limits

### Session Limits

Limit how many concurrent sessions a user can have by rejecting or overriding logins. By default, Tenxyte restricts users to 1 session:

```python
TENXYTE_SESSION_LIMIT_ENABLED = True
TENXYTE_DEFAULT_MAX_SESSIONS = 1 # Overriden by the standard preset to 3
TENXYTE_DEFAULT_SESSION_LIMIT_ACTION = 'revoke_oldest'  # or 'deny'
```

Actions:
- `'revoke_oldest'` — revokes the oldest session to make room
- `'deny'` — rejects the new login attempt

Per-user override: set `user.max_sessions = 5` to override the default for that user.

### Device Limits

Limit how many unique devices a user can use by tracking structured device origins. By default, Tenxyte restricts users to 1 device:

```python
TENXYTE_DEVICE_LIMIT_ENABLED = True
TENXYTE_DEFAULT_MAX_DEVICES = 1 # Overriden by the standard preset to 5, high-security to 2
TENXYTE_DEVICE_LIMIT_ACTION = 'deny'  # or 'revoke_oldest'
```

Device identification uses the `device_info` field sent by the client (structured fingerprint string). Tenxyte uses smart matching — minor version differences (e.g. Chrome 122 vs 123) are treated as the same device.

**Device info format (v1):**
```
v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122
```

Build from User-Agent as fallback:
```python
from tenxyte.device_info import build_device_info_from_user_agent
device_info = build_device_info_from_user_agent(request.META.get('HTTP_USER_AGENT', ''))
```

---

## Password Security

### Password Policy

```python
TENXYTE_PASSWORD_MIN_LENGTH = 8
TENXYTE_PASSWORD_MAX_LENGTH = 128
TENXYTE_PASSWORD_REQUIRE_UPPERCASE = True
TENXYTE_PASSWORD_REQUIRE_LOWERCASE = True
TENXYTE_PASSWORD_REQUIRE_DIGIT = True
TENXYTE_PASSWORD_REQUIRE_SPECIAL = True
```

### Password History

Prevent users from reusing recent passwords:

```python
TENXYTE_PASSWORD_HISTORY_ENABLED = True
TENXYTE_PASSWORD_HISTORY_COUNT = 5  # Check against last 5 passwords
```

### Check Password Strength

```bash
POST /api/v1/auth/password/strength/
{ "password": "MyPassword123!" }
```

### NIST SP 800-63B Compliance

Accounts **without** 2FA enabled can be held to a higher minimum password length, per NIST SP 800-63B recommendations:

```python
TENXYTE_PASSWORD_MIN_LENGTH_NO_MFA = 15  # 0 = disabled (default)
```

When set to `15`, users without 2FA must use passwords of at least 15 characters. Users with 2FA active continue using the standard `PASSWORD_MIN_LENGTH` (default: 8).

---

## Security Headers

Add security headers to all responses. By default, Tenxyte provides a highly restrictive set of headers, but they are disabled (`False`) by default unless you use a secure preset or manually enable them:

```python
TENXYTE_SECURITY_HEADERS_ENABLED = False # Set to True to enable
TENXYTE_SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
}
```

Add the middleware:
```python
MIDDLEWARE = [
    ...
    'tenxyte.middleware.SecurityHeadersMiddleware',
]
```

---

## CORS

```python
TENXYTE_CORS_ENABLED = True
TENXYTE_CORS_ALLOWED_ORIGINS = [
    'https://yourapp.com',
    'http://localhost:3000',
]
TENXYTE_CORS_ALLOW_CREDENTIALS = True
```

Add the middleware:
```python
MIDDLEWARE = [
    'tenxyte.middleware.CORSMiddleware',  # Must be first
    ...
]
```

---

## Audit Logging

All security-relevant events are automatically logged to the `AuditLog` model:

| Event | Trigger |
|---|---|
| `login` | Successful login |
| `login_failed` | Failed login attempt |
| `logout` | User logout |
| `logout_all` | Logout from all devices |
| `token_refresh` | Access token refreshed |
| `password_change` | Password changed |
| `password_reset_request` | Password reset requested |
| `password_reset_complete` | Password reset completed |
| `2fa_enabled` | 2FA activated |
| `2fa_disabled` | 2FA deactivated |
| `2fa_backup_used` | 2FA Backup Code Used |
| `account_created` | Account Created |
| `account_locked` | Account locked after failures |
| `account_unlocked` | Account Unlocked |
| `email_verified` | Email Verified |
| `phone_verified` | Phone Verified |
| `role_assigned` | Role Assigned |
| `role_removed` | Role Removed |
| `permission_changed`| Permission Changed |
| `app_created` | Application Created |
| `app_credentials_regenerated` | Application Credentials Regenerated |
| `account_deleted` | Account Deleted |
| `suspicious_activity` | Suspicious Activity Detected |
| `session_limit_exceeded` | Session limit hit |
| `device_limit_exceeded` | Device limit hit |
| `new_device_detected` | Login from unrecognized device |
| `agent_action` | Agent Action Executed |

Query audit logs:
```bash
GET /api/v1/auth/admin/audit-logs/?action=login_failed&date_from=2026-01-01
```

---

## OTP Verification

Email and phone verification use time-limited OTP codes:

```python
TENXYTE_OTP_LENGTH = 6
TENXYTE_OTP_EMAIL_VALIDITY = 15   # minutes
TENXYTE_OTP_PHONE_VALIDITY = 10   # minutes
TENXYTE_OTP_MAX_ATTEMPTS = 5      # before invalidation
```

---

## Production Checklist

- [ ] Set `TENXYTE_JWT_SECRET_KEY` to a strong, unique secret (not `SECRET_KEY`)
- [ ] Switch to `TENXYTE_JWT_ALGORITHM = 'RS256'` and configure RSA keys
- [ ] Set `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` to ≤ 900 seconds (15 min) — **this is now the default**
- [ ] Enable `TENXYTE_REFRESH_TOKEN_ROTATION = True`
- [ ] Enable `TENXYTE_TOKEN_BLACKLIST_ENABLED = True`
- [ ] Set `TENXYTE_JWT_AUDIENCE` to your application identifier
- [ ] Enable `TENXYTE_SECURITY_HEADERS_ENABLED = True`
- [ ] Configure `TENXYTE_CORS_ALLOWED_ORIGINS` (never use `ALLOW_ALL_ORIGINS` in production)
- [ ] Set `TENXYTE_MAX_LOGIN_ATTEMPTS` to a reasonable value (5–10)
- [ ] Enable `TENXYTE_PASSWORD_HISTORY_ENABLED = True`
- [ ] Use HTTPS in production (required for `Strict-Transport-Security`)
- [ ] Rotate `Application` secrets regularly
- [ ] Ensure `extra_claims` do not contain PII (email, IP, phone…)
- [ ] Consider enabling cookie refresh token transport for web apps
- [ ] Consider enabling NIST password length for non-MFA accounts (`PASSWORD_MIN_LENGTH_NO_MFA = 15`)

---

## OAuth / Social Login Security

### PKCE (Proof Key for Code Exchange)

All OAuth providers support PKCE (RFC 7636). Clients should include `code_verifier` in the code exchange request:

```json
POST /api/v1/auth/social/google/
{
  "code": "<authorization-code>",
  "redirect_uri": "https://yourapp.com/auth/callback",
  "code_verifier": "<PKCE-code-verifier>"
}
```

The `code_verifier` is forwarded to the provider's token endpoint. This prevents authorization code interception attacks.

### Redirect URI Whitelist

Configure allowed redirect URIs per `Application` model. When the whitelist is non-empty, any `redirect_uri` not in the list returns `400 INVALID_REDIRECT_URI`:

```python
# Via Django admin or API
app.redirect_uris = [
    "https://yourapp.com/auth/callback",
    "https://staging.yourapp.com/auth/callback",
]
```

### Configurable OAuth Scopes

Override default scopes per provider:

```python
TENXYTE_SOCIAL_GOOGLE_SCOPES = 'openid email profile'
TENXYTE_SOCIAL_GITHUB_SCOPES = 'read:user user:email'
TENXYTE_SOCIAL_MICROSOFT_SCOPES = 'openid email profile'
TENXYTE_SOCIAL_FACEBOOK_SCOPES = 'email,public_profile'
```

---

*For the full list of settings with defaults, see [Settings Reference](settings.md).*

