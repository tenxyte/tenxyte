# Schemas Reference

This document describes the reusable schema components used throughout the Tenxyte API. These correspond to the `$ref` components in the OpenAPI specification (`openapi_schema.json`).

---

## User

Represents an authenticated Tenxyte user.

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "phone": "+33612345678",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": true,
  "has_2fa": false,
  "date_joined": "2026-01-01T00:00:00Z",
  "last_login": "2026-03-01T12:00:00Z",
  "roles": ["member"],
  "organization_slug": "acme-corp"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique user identifier |
| `email` | string | Primary login email |
| `phone` | string \| null | E.164-formatted phone number |
| `first_name` / `last_name` | string | Display name |
| `is_verified` | boolean | Email or phone verified |
| `has_2fa` | boolean | TOTP two-factor enabled |
| `roles` | string[] | Active roles within current org context |

---

## TokenPair

Issued on successful login or token refresh.

```json
{
  "access": "<JWT access token>",
  "refresh": "<JWT refresh token>",
  "access_expires_at": "2026-03-04T04:00:00Z",
  "refresh_expires_at": "2026-03-11T03:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `access` | JWT string | Short-lived access token (default: 15 min) |
| `refresh` | JWT string | Long-lived refresh token (default: 7 days) |
| `access_expires_at` | ISO 8601 | Expiry timestamp for the access token |
| `refresh_expires_at` | ISO 8601 | Expiry timestamp for the refresh token |

---

## ErrorResponse

Returned on all `4xx` and `5xx` responses.

```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

| Field | Type | Description |
|---|---|---|
| `error` | string | User-facing description |
| `code` | string | Machine-readable error identifier (see below) |
| `details` | object \| null | Field-level validation errors or extra context |

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
| `ORG_NOT_FOUND` | 404 | X-Org-Slug header does not match |
| `NOT_ORG_MEMBER` | 403 | User is not a member of the provided org |

---

## PaginatedResponse

All list endpoints return a paginated wrapper:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/auth/admin/users/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Field | Type | Description |
|---|---|---|
| `count` | integer | Total number of items across all pages |
| `next` | string \| null | URL of the next page (null if last page) |
| `previous` | string \| null | URL of the previous page (null if first page) |
| `results` | array | Items on the current page |

---

## Organization

Represents a tenant organization.

```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "parent": null,
  "plan": "enterprise",
  "max_members": 0,
  "member_count": 12,
  "created_at": "2026-01-01T00:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `slug` | string | URL-safe identifier used in `X-Org-Slug` header |
| `parent` | UUID \| null | Parent org ID for hierarchical tenants |
| `max_members` | integer | `0` = unlimited |

---

## AuditLog

Security event log entry.

```json
{
  "id": "uuid",
  "user": "uuid",
  "action": "login",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "metadata": {},
  "created_at": "2026-03-04T03:00:00Z"
}
```

See [Security Guide](security.md#audit-logging) for the full list of `action` values.

---

## Role

```json
{
  "id": "uuid",
  "name": "admin",
  "permissions": ["can_manage_users", "can_view_audit_logs"]
}
```

See [RBAC Guide](rbac.md) for built-in roles and permission decorators.

---

## DeviceInfo

Structured fingerprint string sent by the client during login.

**Format (v1):**
```
v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122
```

| Key | Description |
|---|---|
| `v` | Format version (always `1`) |
| `os` | Operating system |
| `osv` | OS version |
| `device` | `desktop`, `mobile`, or `tablet` |
| `arch` | CPU architecture |
| `runtime` | Browser/runtime + version |

See [Security Guide](security.md#session--device-limits) for configuration details.
