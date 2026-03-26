# JavaScript / TypeScript SDK Integration

> Official client SDK for integrating a Tenxyte-powered backend into any JavaScript or TypeScript application — Node.js, browsers, React, Vue, or vanilla JS.

---

## Packages

The Tenxyte JS SDK is a monorepo shipping three packages:

| Package | Description | Guide |
|---|---|---|
| [`@tenxyte/core`](https://www.npmjs.com/package/@tenxyte/core) | Framework-agnostic core SDK — works in Node.js, browsers, and any JS runtime | [Core Guide](core.md) |
| [`@tenxyte/react`](https://www.npmjs.com/package/@tenxyte/react) | React hooks with automatic re-renders on auth state changes | [React Guide](react.md) |
| [`@tenxyte/vue`](https://www.npmjs.com/package/@tenxyte/vue) | Vue 3 composables with reactive refs | [Vue Guide](vue.md) |

---

## Installation

```bash
# Core SDK only (Node.js, vanilla JS, any runtime)
npm install @tenxyte/core

# React bindings (requires React 18+ or 19+)
npm install @tenxyte/core @tenxyte/react

# Vue 3 bindings (requires Vue 3.3+)
npm install @tenxyte/core @tenxyte/vue
```

> **Requirements:** Node.js 18+ or any modern browser. TypeScript types are included — no separate `@types` package needed.

---

## Minimal Example

```typescript
import { TenxyteClient } from '@tenxyte/core';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
});

// Register
await tx.auth.register({
    email: 'user@example.com',
    password: 'SecureP@ss1!',
    first_name: 'John',
    last_name: 'Doe',
});

// Login
const tokens = await tx.auth.loginWithEmail({
    email: 'user@example.com',
    password: 'SecureP@ss1!',
    device_info: '',
});

// Authenticated request — Authorization header is injected automatically
const profile = await tx.user.getProfile();
```

Tokens are stored automatically, 401s trigger silent refresh, and `Authorization: Bearer <token>` is injected on every request.

---

## SDK Features at a Glance

- **Authentication** — Email/password, phone, magic link, social OAuth2 (with PKCE), registration
- **Cookie mode** — HttpOnly refresh token transport (`cookieMode: true`)
- **Security** — 2FA/TOTP, OTP, WebAuthn/Passkeys (FIDO2), password management
- **RBAC** — Synchronous JWT role/permission checks, CRUD operations
- **B2B** — Organization CRUD, members, invitations, context switching
- **AI Agent Security (AIRS)** — Agent tokens, Human-in-the-Loop, usage reporting
- **Applications** — API client management, credential regeneration
- **Admin** — Audit logs, login attempts, blacklisted/refresh tokens
- **GDPR** — Account deletion flows, data export
- **Dashboard** — Global, auth, security, GDPR, per-org statistics
- **Auto-refresh** — Silent 401 → refresh → retry interceptor
- **Retry** — Configurable exponential backoff for 429/5xx
- **Events** — `session:expired`, `token:refreshed`, `token:stored`, `agent:awaiting_approval`
- **TypeScript** — Full types generated from OpenAPI

---

## Configuration Reference

```typescript
const tx = new TenxyteClient({
    // Required
    baseUrl: 'https://api.my-service.com',

    // Optional — extra headers for every request
    headers: { 'X-Access-Key': 'pkg_abc123' },

    // Optional — token storage (default: MemoryStorage)
    storage: new LocalStorageAdapter(),

    // Optional — auto-refresh 401s silently (default: true)
    autoRefresh: true,

    // Optional — auto-inject device fingerprint (default: true)
    autoDeviceInfo: true,

    // Optional — request timeout in ms
    timeoutMs: 10_000,

    // Optional — retry config for 429/5xx
    retryConfig: { maxRetries: 3, baseDelayMs: 500 },

    // Optional — callback when session is unrecoverable
    onSessionExpired: () => router.push('/login'),

    // Optional — pluggable logger
    logger: console,
    logLevel: 'debug',

    // Optional — override auto-detected device info
    deviceInfoOverride: { app_name: 'MyApp', app_version: '2.0.0' },

    // Optional — cookie-based refresh token transport (default: false)
    // Enable when backend has TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True
    cookieMode: false,
});
```

| Option | Type | Default | Description |
|---|---|---|---|
| `baseUrl` | `string` | — | Base URL of the Tenxyte-powered API |
| `headers` | `Record<string, string>` | `{}` | Extra headers merged into every request |
| `storage` | `TenxyteStorage` | `MemoryStorage` | Token persistence backend |
| `autoRefresh` | `boolean` | `true` | Silent 401 → refresh → retry |
| `autoDeviceInfo` | `boolean` | `true` | Inject `device_info` into auth requests |
| `timeoutMs` | `number` | `undefined` | Global request timeout |
| `retryConfig` | `RetryConfig` | `undefined` | Exponential backoff for 429/5xx |
| `onSessionExpired` | `() => void` | `undefined` | Callback when session is unrecoverable |
| `logger` | `TenxyteLogger` | silent no-op | Logger implementation |
| `logLevel` | `LogLevel` | `'silent'` | `'silent'` \| `'error'` \| `'warn'` \| `'debug'` |
| `deviceInfoOverride` | `CustomDeviceInfo` | `undefined` | Override auto-detected device info |
| `cookieMode` | `boolean` | `false` | Use HttpOnly cookie refresh token transport |

---

## Error Handling

All SDK methods throw a `TenxyteError` on failure:

```typescript
import type { TenxyteError } from '@tenxyte/core';

try {
    await tx.auth.loginWithEmail({ email, password, device_info: '' });
} catch (err) {
    const e = err as TenxyteError;
    console.error(e.code);        // e.g. 'INVALID_CREDENTIALS', 'ACCOUNT_LOCKED'
    console.error(e.error);       // Human-readable message
    console.error(e.details);     // Per-field errors or free message
    console.error(e.retry_after); // Seconds to wait (on 429/423)
}
```

See [Schemas Reference](../../schemas.md) for the complete list of error codes.

---

## Next Steps

- [**Core Guide**](core.md) — Full `@tenxyte/core` API reference with all 10 modules
- [**React Guide**](react.md) — React hooks, `TenxyteProvider`, and full SPA examples
- [**Vue Guide**](vue.md) — Vue 3 composables, plugin setup, and full SPA examples
- [**API Endpoints**](../../endpoints.md) — Backend endpoint reference
- [**Security Guide**](../../security.md) — PKCE, cookie mode, JWT rotation, lockout
- [**Settings Reference**](../../settings.md) — All backend configuration options
