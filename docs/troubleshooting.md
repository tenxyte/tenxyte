# Troubleshooting Guide

Common issues and solutions when integrating Tenxyte.

---

## Installation & Settings

### `tenxyte.setup()` has no effect

**Symptom:** `INSTALLED_APPS`, `AUTH_USER_MODEL`, or `MIDDLEWARE` are not being configured automatically.

**Cause:** `tenxyte.setup()` must be called **before** any other Django imports that trigger app loading.

**Fix:**
```python
# settings.py — must be at the very top, before other Django settings
import tenxyte
tenxyte.setup()
```

Do not call it inside `if TYPE_CHECKING:` blocks or inside functions.

---

### `ImproperlyConfigured: TENXYTE_JWT_SECRET_KEY must be set in production`

**Cause:** Running with `DEBUG=False` without a dedicated JWT secret.

**Fix:**
```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'your-strong-dedicated-jwt-secret'  # NOT Django's SECRET_KEY
```

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

### Migrations fail with `table tenxyte_user already exists`

**Cause:** A previous partial migration or a conflicting `AUTH_USER_MODEL`.

**Fix:**
```bash
python manage.py migrate tenxyte --fake-initial
```

If the issue persists, check that `AUTH_USER_MODEL = 'tenxyte.User'` is set **before** running the first migration.

---

## Authentication & JWT

### `401 TOKEN_EXPIRED` immediately after login

**Symptom:** The access token is accepted at login but rejected on the next request.

**Cause:** Server clock is out of sync, or `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` is set too low.

**Fix:**
```python
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 900  # 15 minutes (in seconds)
```
Also ensure the server clock is synchronised (NTP).

---

### `401 TOKEN_BLACKLISTED` after logout

**Symptom:** Token is rejected even though the user just logged in again.

**Cause:** The old token was blacklisted but the client is still sending it.

**Fix:** Ensure the client replaces the stored tokens with the new `TokenPair` received from the re-login response.

---

### `403 2FA_REQUIRED` — user can't log in

**Cause:** 2FA is enabled on the account but the client isn't sending `totp_code`.

**Fix:** Include the TOTP code in the login request body:
```json
{
  "email": "user@example.com",
  "password": "...",
  "totp_code": "123456"
}
```

If the user has lost access to their authenticator app, use a backup code or the admin unlock endpoint:
```bash
POST /api/v1/auth/admin/users/<id>/disable-2fa/
```

---

## Rate Limiting

### All requests return `429` in tests

**Cause:** Rate limiting is active and the test runner shares a cache key.

**Fix:** Disable throttling for tests:
```python
# tests/settings.py
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}
```

Or mock it per-test:
```python
from unittest.mock import patch

with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
    response = client.post('/api/v1/auth/login/email/', data)
```

---

### `X-Forwarded-For` spoofing / wrong IP in rate limiting

**Cause:** The app is behind a proxy but `TENXYTE_TRUSTED_PROXIES` is not configured.

**Fix:**
```python
TENXYTE_TRUSTED_PROXIES = ['10.0.0.1']  # your proxy/load balancer IP
```

Only IPs in this list will have their `X-Forwarded-For` header trusted.

---

## Multi-Tenant / Organizations

### `404 ORG_NOT_FOUND`

**Cause:** The `X-Org-Slug` header value does not match any existing organization.

**Fix:** Double-check the slug value. Slugs are lowercase and URL-safe:
```bash
curl -H "X-Org-Slug: acme-corp" http://localhost:8000/api/v1/auth/organizations/members/
```

---

### `403 NOT_ORG_MEMBER`

**Cause:** The authenticated user is not a member of the organization specified in `X-Org-Slug`.

**Fix:** Add the user to the organization first via the admin or the invitation endpoint:
```bash
POST /api/v1/auth/organizations/invite/
{
  "email": "user@example.com",
  "role": "member"
}
```

---

## TOTP / 2FA

### QR code generated but TOTP codes always rejected

**Cause 1:** Server clock drift exceeds `TENXYTE_TOTP_VALID_WINDOW`.

**Fix:** Increase the tolerance window (accepts ±N × 30-second periods):
```python
TENXYTE_TOTP_VALID_WINDOW = 2  # default is 1
```

**Cause 2:** TOTP secret is encrypted but `FIELD_ENCRYPTION_KEY` changed since setup.

**Fix:** Ensure `FIELD_ENCRYPTION_KEY` has not changed. If it has, follow the [key rotation procedure](periodic_tasks.md#7-encryption-key-rotation-field_encryption_key).

---

### Backup codes not accepted

**Cause:** Each backup code is **single-use**. Once consumed it cannot be reused.

**Fix:** Regenerate backup codes:
```bash
POST /api/v1/auth/2fa/backup-codes/
```

---

## Social Authentication

### Google OAuth: `invalid_grant` or redirect loop

**Cause:** `TENXYTE_GOOGLE_CLIENT_ID` / `TENXYTE_GOOGLE_CLIENT_SECRET` are incorrect, or the redirect URI registered in Google Console does not match.

**Fix:**
1. Verify credentials in Google Cloud Console → APIs & Services → Credentials
2. Ensure the redirect URI matches exactly (including trailing slash):
   ```
   http://localhost:8000/api/v1/auth/social/google/callback/
   ```

---

## WebAuthn / Passkeys

### `InvalidStateError` during registration

**Cause:** The WebAuthn challenge has expired (default: 60 seconds) or was already consumed.

**Fix:** Re-initiate the registration flow:
```bash
POST /api/v1/auth/webauthn/register/begin/
```

---

## Database

### `OperationalError: no such table` for Tenxyte models

**Cause:** Migrations were not run after installing Tenxyte.

**Fix:**
```bash
python manage.py migrate
```

If the table still does not appear:
```bash
python manage.py showmigrations tenxyte
python manage.py migrate tenxyte
```

---

## Getting Further Help

1. Check the [Settings Reference](settings.md) — the setting you need may already exist
2. Review the [Security Guide](security.md) for security-related issues  
3. Check the [TESTING.md](TESTING.md) for test setup problems
4. Search open issues or ask on the community forum
