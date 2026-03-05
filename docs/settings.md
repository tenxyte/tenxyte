# Settings Reference

**Table of Contents**
- [Settings Priority](#settings-priority)
- [Shortcut Secure Mode](#shortcut-secure-mode) (1)
- [Core Settings](#core-settings) (6)
- [JWT](#jwt) (9)
- [Two-Factor Authentication (TOTP)](#two-factor-authentication-totp) (3)
- [OTP (Email / SMS Verification)](#otp-email--sms-verification) (4)
- [Password Policy](#password-policy) (9)
- [Rate Limiting & Account Lockout](#rate-limiting--account-lockout) (5)
- [Session & Device Limits](#session--device-limits) (6)
- [Multi-Application](#multi-application) (3)
- [CORS](#cors) (8)
- [Security Headers](#security-headers) (2)
- [Social Login (OAuth2)](#social-login-oauth2) (11)
- [WebAuthn / Passkeys (FIDO2)](#webauthn--passkeys-fido2) (4)
- [Breach Password Check (HaveIBeenPwned)](#breach-password-check-haveibeenpwned) (2)
- [Magic Link (Passwordless)](#magic-link-passwordless) (3)
- [SMS Backends](#sms-backends) (9)
- [Email Backends](#email-backends) (3)
- [Audit Logging](#audit-logging) (4)
- [Organizations (B2B)](#organizations-b2b) (8)
- [Swappable Models](#swappable-models) (4)

All Tenxyte settings are prefixed with `TENXYTE_` and have sensible defaults.
Override them in your Django `settings.py`.

---

## Shortcut Secure Mode

`TENXYTE_SHORTCUT_SECURE_MODE` applies a predefined combination of security settings in one line. Individual settings always take priority over the preset.

**Priority order:** explicit `TENXYTE_*` in `settings.py` > preset > default

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # 'development' | 'medium' | 'robust'
```

| Mode | Target use case |
|---|---|
| `development` | Prototypes, local dev, internal tools |
| `medium` | Public SaaS, B2C apps, startups |
| `robust` | Fintech, healthcare, B2B, GDPR-strict |

### Preset values

| Setting | `development` | `medium` | `robust` |
|---|---|---|---|
| `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | `3600` (1h) | `900` (15min) | `300` (5min) |
| `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | `2592000` (30d) | `604800` (7d) | `86400` (1d) |
| `TENXYTE_REFRESH_TOKEN_ROTATION` | `False` | `True` | `True` |
| `TENXYTE_MAX_LOGIN_ATTEMPTS` | `10` | `5` | `3` |
| `TENXYTE_LOCKOUT_DURATION_MINUTES` | `15` | `30` | `60` |
| `TENXYTE_PASSWORD_HISTORY_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_PASSWORD_HISTORY_COUNT` | `0` | `5` | `12` |
| `TENXYTE_BREACH_CHECK_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_BREACH_CHECK_REJECT` | `False` | `True` | `True` |
| `TENXYTE_MAGIC_LINK_ENABLED` | `False` | `True` | `False` |
| `TENXYTE_WEBAUTHN_ENABLED` | `False` | `False` | `True` |
| `TENXYTE_AUDIT_LOGGING_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEVICE_LIMIT_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEFAULT_MAX_DEVICES` | — | `5` | `2` |
| `TENXYTE_DEVICE_LIMIT_ACTION` | — | — | `'deny'` |
| `TENXYTE_SESSION_LIMIT_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEFAULT_MAX_SESSIONS` | — | — | `1` |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS` | `False` | `False` | `False` |
| `TENXYTE_SECURITY_HEADERS_ENABLED` | `False` | `True` | `True` |

> Settings marked `—` are not set by the preset and fall back to their individual defaults.

You can override any preset value individually:
```python
TENXYTE_SHORTCUT_SECURE_MODE = 'robust'
TENXYTE_WEBAUTHN_ENABLED = False  # opt-out of passkeys despite robust mode
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 600  # 10min instead of 5min
```

---

## Core Settings

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_BASE_URL` | `'http://127.0.0.1:8000'` | Base URL of the API. |
| `TENXYTE_API_VERSION` | `1` | API version number. |
| `TENXYTE_API_PREFIX` | `'/api/v1'` | Global API URL prefix. |
| `TENXYTE_TRUSTED_PROXIES` | `[]` | List of trusted proxy IPs/CIDRs for `X-Forwarded-For` validation. |
| `TENXYTE_NUM_PROXIES` | `0` | Number of upstream trusted proxies (e.g., Cloudflare + Nginx = 2). |
| `TENXYTE_VERBOSE_ERRORS` | `False` | Display full error details (e.g., exact missing role). Disable in production. |

---

## JWT

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_JWT_SECRET_KEY` | `None` (Required) | Dedicated secret key for signing JWTs. Must be set explicitly in production. In `DEBUG` mode, an ephemeral key is auto-generated. |
| `TENXYTE_JWT_ALGORITHM` | `'HS256'` | JWT signing algorithm. |
| `TENXYTE_JWT_PRIVATE_KEY` | `None` | RSA/ECDSA private key for signing JWTs (required for RS/PS/ES algorithms). |
| `TENXYTE_JWT_PUBLIC_KEY` | `None` | RSA/ECDSA public key for verifying JWTs (required for RS/PS/ES algorithms). |
| `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | `3600` | Access token lifetime in seconds (1 hour). |
| `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | `604800` | Refresh token lifetime in seconds (7 days). |
| `TENXYTE_JWT_AUTH_ENABLED` | `True` | Enable/disable JWT authentication. |
| `TENXYTE_TOKEN_BLACKLIST_ENABLED` | `True` | Blacklist access tokens on logout. |
| `TENXYTE_REFRESH_TOKEN_ROTATION` | `True` | Issue a new refresh token on every refresh (invalidates old one). |

---

## Two-Factor Authentication (TOTP)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_TOTP_ISSUER` | `'MyApp'` | Issuer name shown in authenticator apps (Google Authenticator, Authy). |
| `TENXYTE_TOTP_VALID_WINDOW` | `1` | Number of 30s periods accepted before/after current time. |
| `TENXYTE_BACKUP_CODES_COUNT` | `10` | Number of backup codes generated on 2FA setup. |

---

## OTP (Email / SMS Verification)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_OTP_LENGTH` | `6` | Length of OTP codes. |
| `TENXYTE_OTP_EMAIL_VALIDITY` | `15` | Email OTP validity in minutes. |
| `TENXYTE_OTP_PHONE_VALIDITY` | `10` | SMS OTP validity in minutes. |
| `TENXYTE_OTP_MAX_ATTEMPTS` | `5` | Max failed OTP attempts before invalidation. |

---

## Password Policy

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_PASSWORD_MIN_LENGTH` | `8` | Minimum password length. |
| `TENXYTE_PASSWORD_MAX_LENGTH` | `128` | Maximum password length. |
| `TENXYTE_BCRYPT_ROUNDS` | `12` | Work factor for bcrypt hashing. |
| `TENXYTE_PASSWORD_REQUIRE_UPPERCASE` | `True` | Require at least one uppercase letter. |
| `TENXYTE_PASSWORD_REQUIRE_LOWERCASE` | `True` | Require at least one lowercase letter. |
| `TENXYTE_PASSWORD_REQUIRE_DIGIT` | `True` | Require at least one digit. |
| `TENXYTE_PASSWORD_REQUIRE_SPECIAL` | `True` | Require at least one special character. |
| `TENXYTE_PASSWORD_HISTORY_ENABLED` | `True` | Prevent reuse of recent passwords. |
| `TENXYTE_PASSWORD_HISTORY_COUNT` | `5` | Number of previous passwords to check against. |

---

## Rate Limiting & Account Lockout

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_RATE_LIMITING_ENABLED` | `True` | Enable rate limiting on sensitive endpoints. |
| `TENXYTE_MAX_LOGIN_ATTEMPTS` | `5` | Failed attempts before account lockout. |
| `TENXYTE_LOCKOUT_DURATION_MINUTES` | `30` | Account lockout duration in minutes. |
| `TENXYTE_RATE_LIMIT_WINDOW_MINUTES` | `15` | Time window for counting login attempts. |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED` | `True` | Enable/disable account lockout after failures. |

### Custom Throttle Rules

Apply rate limits to any URL without creating a custom throttle class:

```python
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/products/': '100/hour',
    '/api/v1/search/': '30/min',
    '/api/v1/upload/': '5/hour',
    '/api/v1/health/$': '1000/min',  # $ = exact match
}
```

Requires adding to DRF config:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'tenxyte.throttles.SimpleThrottleRule',
    ],
}
```

---

## Session & Device Limits

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_SESSION_LIMIT_ENABLED` | `True` | Enable concurrent session limits. |
| `TENXYTE_DEFAULT_MAX_SESSIONS` | `1` | Max concurrent sessions per user. |
| `TENXYTE_DEFAULT_SESSION_LIMIT_ACTION` | `'revoke_oldest'` | Action when limit exceeded: `'deny'` or `'revoke_oldest'`. |
| `TENXYTE_DEVICE_LIMIT_ENABLED` | `True` | Enable unique device limits. |
| `TENXYTE_DEFAULT_MAX_DEVICES` | `1` | Max unique devices per user. |
| `TENXYTE_DEVICE_LIMIT_ACTION` | `'deny'` | Action when device limit exceeded: `'deny'` or `'revoke_oldest'`. |

Per-user overrides: set `user.max_sessions` or `user.max_devices` to override the default.

---

## Multi-Application

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_APPLICATION_AUTH_ENABLED` | `True` | Require `X-Access-Key` / `X-Access-Secret` headers. |
| `TENXYTE_EXEMPT_PATHS` | `['/admin/', '/api/v1/health/', '/api/v1/docs/']` | Paths exempt from app auth (prefix match). |
| `TENXYTE_EXACT_EXEMPT_PATHS` | `['/api/v1/']` | Paths exempt from app auth (exact match). |

---

## CORS

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_CORS_ENABLED` | `True` | Enable built-in CORS middleware. |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS` | `False` | Allow all origins (unsafe in production). |
| `TENXYTE_CORS_ALLOWED_ORIGINS` | `[]` | List of allowed origins. |
| `TENXYTE_CORS_ALLOW_CREDENTIALS` | `True` | Allow credentials (cookies, Authorization). |
| `TENXYTE_CORS_ALLOWED_METHODS` | `['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']` | Allowed HTTP methods. |
| `TENXYTE_CORS_ALLOWED_HEADERS` | See below | Allowed request headers. |
| `TENXYTE_CORS_EXPOSE_HEADERS` | `[]` | Headers exposed to the client. |
| `TENXYTE_CORS_MAX_AGE` | `86400` | Preflight cache duration in seconds. |

Default allowed headers: `Accept`, `Accept-Language`, `Content-Type`, `Authorization`, `X-Access-Key`, `X-Access-Secret`, `X-Requested-With`.

---

## Security Headers

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_SECURITY_HEADERS_ENABLED` | `False` | Add security headers to all responses. |
| `TENXYTE_SECURITY_HEADERS` | See below | Dict of header name → value. |

Default headers:
```python
{
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

---

## Social Login (OAuth2)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_SOCIAL_PROVIDERS` | `['google', 'github', 'microsoft', 'facebook']` | Enabled OAuth2 providers. |
| `TENXYTE_SOCIAL_AUTO_MERGE_ACCOUNTS` | `False` | Automatically merge social login with existing email account. |
| `TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL` | `True` | Reject social login if the email is not verified by the provider. |
| `GOOGLE_CLIENT_ID` | `''` | Google OAuth Client ID. |
| `GOOGLE_CLIENT_SECRET` | `''` | Google OAuth Client Secret. |
| `GITHUB_CLIENT_ID` | `''` | GitHub OAuth App Client ID. |
| `GITHUB_CLIENT_SECRET` | `''` | GitHub OAuth App Client Secret. |
| `MICROSOFT_CLIENT_ID` | `''` | Microsoft Azure AD Application (client) ID. |
| `MICROSOFT_CLIENT_SECRET` | `''` | Microsoft Azure AD Client Secret. |
| `FACEBOOK_APP_ID` | `''` | Facebook App ID. |
| `FACEBOOK_APP_SECRET` | `''` | Facebook App Secret. |

Endpoint: `POST /api/v1/auth/social/<provider>/` — where `<provider>` is `google`, `github`, `microsoft`, or `facebook`.

---

## WebAuthn / Passkeys (FIDO2)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_WEBAUTHN_ENABLED` | `False` | Enable passwordless authentication via Passkeys. |
| `TENXYTE_WEBAUTHN_RP_ID` | `'localhost'` | Relying Party ID — must match your domain (e.g. `'yourapp.com'`). |
| `TENXYTE_WEBAUTHN_RP_NAME` | `'Tenxyte'` | Name displayed in the browser Passkey prompt. |
| `TENXYTE_WEBAUTHN_CHALLENGE_EXPIRY_SECONDS` | `300` | WebAuthn challenge validity in seconds. |

Requires: `pip install py-webauthn`

---

## Breach Password Check (HaveIBeenPwned)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_BREACH_CHECK_ENABLED` | `False` | Check passwords against the HIBP Pwned Passwords API. |
| `TENXYTE_BREACH_CHECK_REJECT` | `True` | If `True`, reject breached passwords (HTTP 400). If `False`, warn in logs only. |

Uses k-anonymity — only the first 5 characters of the SHA-1 hash are sent to the API.

---

## Magic Link (Passwordless)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_MAGIC_LINK_ENABLED` | `False` | Enable passwordless login via email magic links. |
| `TENXYTE_MAGIC_LINK_EXPIRY_MINUTES` | `15` | Magic link validity in minutes. |
| `TENXYTE_MAGIC_LINK_BASE_URL` | `'https://yourapp.com'` | Base URL used to build the verification link sent by email. |

---

## SMS Backends

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_SMS_BACKEND` | `'tenxyte.backends.sms.ConsoleBackend'` | SMS backend class. |
| `TENXYTE_SMS_ENABLED` | `False` | Enable real SMS sending. |
| `TENXYTE_SMS_DEBUG` | `True` | Log SMS instead of sending. |
| `TWILIO_ACCOUNT_SID` | `''` | Twilio Account SID (if using Twilio backend). |
| `TWILIO_AUTH_TOKEN` | `''` | Twilio Auth Token. |
| `TWILIO_PHONE_NUMBER` | `''` | Twilio sender phone number. |
| `NGH_API_KEY` | `''` | NGH Corp API Key (if using NGH backend). |
| `NGH_API_SECRET` | `''` | NGH Corp API Secret. |
| `NGH_SENDER_ID` | `''` | NGH Corp Sender ID. |

Available SMS backends:
- `tenxyte.backends.sms.ConsoleBackend` — prints to console (development)
- `tenxyte.backends.sms.TwilioBackend` — sends via Twilio
- `tenxyte.backends.sms.NGHBackend` — sends via NGH Corp

---

## Email Backends

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_EMAIL_BACKEND` | `'tenxyte.backends.email.DjangoBackend'` | Email backend class. |
| `SENDGRID_API_KEY` | `''` | SendGrid API Key (if using SendGrid backend). |
| `SENDGRID_FROM_EMAIL` | `'noreply@example.com'` | SendGrid sender email. |

Available email backends:
- `tenxyte.backends.email.DjangoBackend` — uses Django's `EMAIL_BACKEND` (recommended)
- `tenxyte.backends.email.ConsoleBackend` — prints to console (development)
- `tenxyte.backends.email.SendGridBackend` — sends via SendGrid (legacy; prefer `django-anymail`)

---

## Audit Logging

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_AUDIT_LOGGING_ENABLED` | `True` | Enable audit log recording. |
| `TENXYTE_AUDIT_LOG_RETENTION_DAYS` | `90` | Days to retain audit logs before auto-purge (0 = infinite). |
| `TENXYTE_PURGE_IP_ON_DELETION` | `False` | Purge IP from logs when an account is deleted. |
| `TENXYTE_AGENT_ACTION_RETENTION_DAYS` | `7` | Retention days for pending Agent actions (HITL). |

---

## Organizations (B2B)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_ORGANIZATIONS_ENABLED` | `False` | Enable the Organizations feature (opt-in). |
| `TENXYTE_CREATE_DEFAULT_ORGANIZATION` | `True` | Create a default organization for new users. |
| `TENXYTE_ORG_ROLE_INHERITANCE` | `True` | Roles propagate down the org hierarchy. |
| `TENXYTE_ORG_MAX_DEPTH` | `5` | Maximum organization hierarchy depth. |
| `TENXYTE_ORG_MAX_MEMBERS` | `0` | Max members per org (0 = unlimited). |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Swappable Organization model. |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Swappable OrganizationRole model. |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL` | `'tenxyte.OrganizationMembership'` | Swappable OrganizationMembership model. |

---

## Swappable Models

Replace any core model with your own by pointing to a custom class that extends the corresponding `Abstract*` base.

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_USER_MODEL` | `'tenxyte.User'` | Swappable User model. Also set Django's `AUTH_USER_MODEL`. |
| `TENXYTE_APPLICATION_MODEL` | `'tenxyte.Application'` | Swappable Application model (multi-app auth). |
| `TENXYTE_ROLE_MODEL` | `'tenxyte.Role'` | Swappable Role model (RBAC). |
| `TENXYTE_PERMISSION_MODEL` | `'tenxyte.Permission'` | Swappable Permission model (RBAC). |

Example — custom User model:

```python
# myapp/models.py
from tenxyte.models import AbstractUser

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'

# settings.py
TENXYTE_USER_MODEL = 'myapp.CustomUser'
AUTH_USER_MODEL = 'myapp.CustomUser'  # required by Django
```

Example — custom Application model:

```python
# myapp/models.py
from tenxyte.models import AbstractApplication

class CustomApplication(AbstractApplication):
    webhook_url = models.URLField(blank=True)

    class Meta(AbstractApplication.Meta):
        db_table = 'custom_applications'

# settings.py
TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
```
