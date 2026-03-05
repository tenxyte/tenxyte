# Schemas Reference

This document describes the reusable schema components used throughout the Tenxyte API. These correspond to the `$ref` components in the OpenAPI specification (`openapi_schema.json`).

---

## User

Represents an authenticated Tenxyte user.

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "first_name": "John",
  "last_name": "Doe",
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_2fa_enabled": false,
  "roles": ["admin"],
  "permissions": ["users.view", "users.manage"],
  "created_at": "2026-01-01T00:00:00Z",
  "last_login": "2026-03-01T12:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique user identifier |
| `email` | string \| null | Primary login email |
| `phone_country_code` | string \| null | Country code (e.g. +33) |
| `phone_number` | string \| null | Local phone number |
| `first_name` / `last_name` | string | Display name |
| `is_email_verified` | boolean | Indicates if the email was verified |
| `is_phone_verified` | boolean | Indicates if the phone number was verified |
| `is_2fa_enabled` | boolean | Indicates if TOTP two-factor is active |
| `roles` | string[] | Flat list of assigned role IDs |
| `permissions` | string[] | Flat list of assigned permissions (direct + from roles) |
| `created_at` | string (date-time) | Account creation timestamp |
| `last_login` | string (date-time) \| null | Last login timestamp |

---

## TokenPair

Issued on successful login or token refresh.

```json
{
  "access_token": "<JWT access token>",
  "refresh_token": "<JWT refresh token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "Windows 11 Desktop"
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | JWT string | Short-lived access token |
| `refresh_token` | JWT string | Long-lived refresh token |
| `token_type` | string | Token type (always "Bearer") |
| `expires_in` | integer | Access token expiration in seconds |
| `device_summary` | string \| null | Description of the user's device (if `device_info` was sent) |

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
