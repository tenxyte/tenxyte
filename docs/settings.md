# Settings Reference

All Tenxyte settings are prefixed with `TENXYTE_` and have sensible defaults.
Override them in your Django `settings.py`.

---

## JWT

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_JWT_SECRET_KEY` | `SECRET_KEY` | Secret key for signing JWTs. Defaults to Django's `SECRET_KEY`. |
| `TENXYTE_JWT_ALGORITHM` | `'HS256'` | JWT signing algorithm. |
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
| `TENXYTE_CORS_ENABLED` | `False` | Enable built-in CORS middleware. |
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
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}
```

---

## Google OAuth

| Setting | Default | Description |
|---|---|---|
| `GOOGLE_CLIENT_ID` | `''` | Google OAuth Client ID. |
| `GOOGLE_CLIENT_SECRET` | `''` | Google OAuth Client Secret. |

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

---

## Organizations (B2B)

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_ORGANIZATIONS_ENABLED` | `False` | Enable the Organizations feature (opt-in). |
| `TENXYTE_ORG_ROLE_INHERITANCE` | `True` | Roles propagate down the org hierarchy. |
| `TENXYTE_ORG_MAX_DEPTH` | `5` | Maximum organization hierarchy depth. |
| `TENXYTE_ORG_MAX_MEMBERS` | `0` | Max members per org (0 = unlimited). |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Swappable Organization model. |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Swappable OrganizationRole model. |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL` | `'tenxyte.OrganizationMembership'` | Swappable OrganizationMembership model. |
