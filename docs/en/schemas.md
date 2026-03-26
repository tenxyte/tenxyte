# Schemas Reference

This document describes the reusable schema components used throughout the Tenxyte API. These correspond to the `$ref` components in the OpenAPI specification (`openapi_schema.json`).

## Table of Contents

- [User](#user)
- [TokenPair](#tokenpair)
- [ErrorResponse](#errorresponse)
- [PaginatedResponse](#paginatedresponse)
- [Organization](#organization)
- [AuditLog](#auditlog)
- [Role](#role)
- [Permission](#permission)
- [Session](#session)
- [Device](#device)
- [LoginAttempt](#loginattempt)
- [BlacklistedToken](#blacklistedtoken)
- [DeviceInfo](#deviceinfo)

---

## User

Represents an authenticated Tenxyte user.

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "username": null,
  "phone": "+33612345678",
  "avatar": "https://cdn.example.com/avatars/user.jpg",
  "bio": null,
  "timezone": "Europe/Paris",
  "language": "fr",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_2fa_enabled": false,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-03-15T10:30:00Z",
  "last_login": "2026-03-01T12:00:00Z",
  "custom_fields": null,
  "preferences": {
    "email_notifications": true,
    "sms_notifications": false,
    "marketing_emails": false
  },
  "roles": ["admin"],
  "permissions": ["users.view", "users.manage"]
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique user identifier |
| `email` | string \| null | Primary login email |
| `username` | string \| null | Optional username |
| `phone` | string \| null | Formatted phone number (e.g. +33612345678) |
| `avatar` | string \| null | URL to the user's avatar image |
| `bio` | string \| null | Short biography |
| `timezone` | string \| null | User's preferred timezone |
| `language` | string \| null | ISO language code (e.g. 'en', 'fr') |
| `first_name` / `last_name` | string | Display name |
| `is_active` | boolean | Indicates if the account is active |
| `is_email_verified` | boolean | Indicates if the email was verified |
| `is_phone_verified` | boolean | Indicates if the phone number was verified |
| `is_2fa_enabled` | boolean | Indicates if TOTP two-factor is active |
| `created_at` | string (date-time) | Account creation timestamp |
| `updated_at` | string (date-time) \| null | Last update timestamp |
| `last_login` | string (date-time) \| null | Last login timestamp |
| `custom_fields` | object \| null | Extending metadata for custom user models |
| `preferences` | object | User notification preferences |
| `roles` | string[] | Flat list of assigned role codes |
| `permissions` | string[] | Flat list of permission codes (e.g., `["users.view", "users.manage"]`) |

---

## TokenPair

Issued on successful login or token refresh.

```json
{
  "access_token": "<JWT access token>",
  "refresh_token": "<JWT refresh token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop"
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | JWT string | Short-lived access token |
| `refresh_token` | JWT string | Long-lived refresh token |
| `token_type` | string | Token type (always "Bearer") |
| `expires_in` | integer | Access token expiration in seconds |
| `refresh_expires_in` | integer | Refresh token expiration in seconds |
| `device_summary` | string \| null | Description of the user's device (if `device_info` was sent) |

> **Cookie mode:** When `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, the `refresh_token` field is omitted from the JSON body. Instead, it is delivered as an `HttpOnly; Secure; SameSite` cookie. See [Security Guide](security.md#cookie-based-refresh-tokens) for details.

---

## ErrorResponse

Returned on all `4xx` and `5xx` responses.

```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {
    "field_name": ["List of errors for this field"]
  }
}
```

| Field | Type | Description |
|---|---|---|
| `error` | string | User-facing description |
| `code` | string | Machine-readable error identifier (see below) |
| `details` | object \| null | Dictionary containing field-level validation errors. Keys are field names, values are arrays of error strings. |

### Common Error Codes

| Code | HTTP Status | Meaning |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `ACCOUNT_LOCKED` | 401 | Too many failed login attempts |
| `2FA_REQUIRED` | 403 | Login requires a TOTP code |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `TOKEN_BLACKLISTED` | 401 | Token was revoked (logout) |
| `PERMISSION_DENIED` | 403 | Insufficient role/permission |
| `SESSION_LIMIT_EXCEEDED` | 403 | Too many concurrent sessions |
| `DEVICE_LIMIT_EXCEEDED` | 403 | Too many registered devices |
| `RATE_LIMITED` | 429 | Too many requests |
| `MISSING_REFRESH_TOKEN` | 400 | No refresh token in body or cookie |
| `INVALID_REDIRECT_URI` | 400 | redirect_uri not in application whitelist |
| `ADMIN_2FA_SETUP_REQUIRED` | 403 | Admin must enable 2FA before login |
| `INVALID_2FA_CODE` | 401 | Wrong TOTP or backup code |
| `PASSWORD_BREACHED` | 400 | Password found in HIBP breach database |
| `PASSWORD_REUSED` | 400 | Password matches a recent entry in history |
| `INVALID_PASSWORD` | 400 | Current password is incorrect (change flow) |
| `INVALID_OTP` | 400 | Wrong OTP verification code |
| `OTP_EXPIRED` | 400 | OTP code has expired |
| `RESET_FAILED` | 400 | Password reset failed |
| `ORG_NOT_FOUND` | 404 | X-Org-Slug header does not match |
| `NOT_ORG_MEMBER` | 403 | User is not a member of the provided org |

---

## PaginatedResponse

All list endpoints return a custom paginated wrapper (`TenxytePagination`):

```json
{
  "count": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "next": "http://localhost:8000/api/v1/auth/admin/users/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Field | Type | Description |
|---|---|---|
| `count` | integer | Total number of items across all pages |
| `page` | integer | Current page number |
| `page_size` | integer | Number of items per page |
| `total_pages` | integer | Total number of pages |
| `next` | string \| null | URL of the next page (null if last page) |
| `previous` | string \| null | URL of the previous page (null if first page) |
| `results` | array | Items on the current page |

---

## Organization

Represents a tenant organization.

```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Acme Corporation Workspace",
  "parent": null,
  "parent_name": null,
  "metadata": {},
  "is_active": true,
  "max_members": 0,
  "member_count": 12,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-02T00:00:00Z",
  "created_by_email": "admin@acmecorp.com",
  "user_role": "owner"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique organization identifier |
| `name` | string | Display name of the organization |
| `slug` | string | URL-safe identifier (used in `X-Org-Slug` header) |
| `description` | string \| null | Description of the organization |
| `parent` | integer \| null | Parent org ID for hierarchical tenants |
| `parent_name` | string \| null | Name of the parent organization |
| `metadata` | object | Custom key-value pairs |
| `is_active` | boolean | Indicates if the organization is active |
| `max_members` | integer | `0` = unlimited |
| `member_count` | integer | Current number of members |
| `created_at` | string (date-time) | Creation timestamp |
| `updated_at` | string (date-time) | Last update timestamp |
| `created_by_email` | string \| null | Email of the creator |
| `user_role` | string \| null | Current authenticated user's role code in this organization |

---

## AuditLog

Security event log entry.

```json
{
  "id": "uuid-string",
  "user": "uuid-string",
  "user_email": "admin@example.com",
  "action": "login",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "application": "uuid-string",
  "application_name": "Web Dashboard",
  "details": {},
  "created_at": "2026-03-04T03:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Log entry identifier |
| `user` | string (UUID) \| null | Associated user ID (if any) |
| `user_email` | string \| null | Email of the associated user |
| `action` | string | The security action performed (e.g., "login", "2fa_enabled") |
| `ip_address` | string \| null | IP address of the client |
| `user_agent` | string \| null | Device info or User-Agent string |
| `application` | string (UUID) \| null | Application ID used for the action |
| `application_name` | string \| null | Display name of the application |
| `details` | object \| null | Extra contextual data (was metadata) |
| `created_at` | string (date-time) | Timestamp of the event |

See [Security Guide](security.md#audit-logging) for the full list of `action` values.

---

## Role

```json
{
  "id": "uuid-string",
  "code": "admin",
  "name": "Administrator",
  "description": "Full access to all system features",
  "permissions": [
    {
      "id": "uuid-string",
      "code": "users.manage",
      "name": "Manage Users",
      "description": "Allows creating, editing, and deleting users",
      "parent": null,
      "children": [],
      "created_at": "2026-03-01T00:00:00Z"
    }
  ],
  "is_default": false,
  "created_at": "2026-03-01T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

See [RBAC Guide](rbac.md) for built-in roles and permission decorators.

---

## Permission

```json
{
  "id": "uuid-string",
  "code": "users.manage",
  "name": "Manage Users",
  "description": "Allows creating, editing, and deleting users",
  "parent": null,
  "children": [],
  "created_at": "2026-03-01T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique identifier |
| `code` | string | The permission code string |
| `name` | string | Human-readable name |
| `description` | string \| null | Detailed description |
| `parent` | object \| null | Parent permission (id, code) |
| `children` | array of objects | Child permissions (id, code, name) |
| `created_at` | string (date-time) | Creation timestamp |
| `updated_at` | string (date-time) | Last modification timestamp |

---

## Session

Represents an active user session.

```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "device_info": {},
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "is_current": true,
  "created_at": "2026-03-01T00:00:00Z",
  "last_activity": "2026-03-01T12:00:00Z",
  "expires_at": "2026-03-31T00:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique session identifier |
| `user_id` | string (UUID) | Associated user ID |
| `device_info` | object | Details parsed from DeviceInfo string |
| `ip_address` | string | Last IP address |
| `user_agent` | string | Browser / Client |
| `is_current` | boolean | Indicates if this is the session making the current API call |
| `created_at` | string (date-time) | Session creation time |
| `last_activity` | string (date-time) | Last seen time |
| `expires_at` | string (date-time) | Session expiration time |

---

## Device

Represents a tracked user device for contextual security.

```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "device_fingerprint": "hash-string",
  "device_name": "Windows 11 Desktop",
  "device_type": "desktop",
  "platform": "windows",
  "browser": "chrome",
  "is_trusted": true,
  "last_seen": "2026-03-01T12:00:00Z",
  "created_at": "2026-02-01T00:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Device record ID |
| `user_id` | string (UUID) | Associated user ID |
| `device_fingerprint` | string | Unique client fingerprint hash |
| `device_name` | string | Display name |
| `device_type` | string | E.g., desktop, mobile |
| `platform` | string | OS platform |
| `browser` | string | Browser identifier |
| `is_trusted` | boolean | True if marked trusted by the user (bypasses some 2FA checks) |
| `last_seen` | string (date-time) | Last login from this device |
| `created_at` | string (date-time) | First seen timestamp |

---

## LoginAttempt

Records of all login attempts for security auditing and blocking.

```json
{
  "id": "uuid-string",
  "identifier": "user@example.com",
  "ip_address": "203.0.113.42",
  "application": "uuid-string",
  "success": false,
  "failure_reason": "invalid_password",
  "created_at": "2026-03-01T12:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Attempt ID |
| `identifier` | string | Email or username used to login |
| `ip_address` | string | Client IP |
| `application` | string (UUID) \| null | Application used |
| `success` | boolean | True if successful |
| `failure_reason` | string \| null | Code detailing why it failed |
| `created_at` | string (date-time) | Timestamp |

---

## BlacklistedToken

Records of revoked JWT tokens.

```json
{
  "id": "uuid-string",
  "token_jti": "jwt-uuid-id",
  "user": "uuid-string",
  "user_email": "user@example.com",
  "blacklisted_at": "2026-03-01T12:00:00Z",
  "expires_at": "2026-03-01T14:00:00Z",
  "reason": "logout",
  "is_expired": true
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Record ID |
| `token_jti` | string | The 'jti' claim of the JWT |
| `user` | string (UUID) \| null | Associated user ID |
| `user_email` | string \| null | Email string |
| `blacklisted_at` | string (date-time) | When it was revoked |
| `expires_at` | string (date-time) | Natural token expiration time |
| `reason` | string | E.g., logout, security |
| `is_expired` | boolean | True if natural expiration time has passed |

---

## DeviceInfo

Structured fingerprint string sent by the client during login.

**Format (v1):**
```
v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Europe/Paris
```

| Key | Description |
|---|---|
| `v` | Format version (always `1`) |
| `os` | Operating system (`windows`, `android`, `ios`, `macos`, `linux`) |
| `osv` | OS version |
| `device` | `desktop`, `mobile`, `tablet`, `server`, `bot`, `api-client` |
| `arch` | CPU architecture (`x64`, `arm64`, `arm`, `x86`) |
| `app` | Application name |
| `appv` | Application version |
| `runtime` | Browser/runtime client (`chrome`, `firefox`, `safari`, `curl`, `postman`, etc.) |
| `rtv` | Runtime version |
| `tz` | Timezone (e.g. `Europe/Paris`) |

See [Security Guide](security.md#session--device-limits) for configuration details.
