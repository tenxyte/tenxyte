# @tenxyte/core — Integration Guide

> Framework-agnostic JavaScript/TypeScript SDK for the Tenxyte API. Works in Node.js, browsers, and any JS runtime.

---

## Installation

```bash
npm install @tenxyte/core
# or
yarn add @tenxyte/core
# or
pnpm add @tenxyte/core
```

---

## Initialization

```typescript
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
    storage: new LocalStorageAdapter(), // Browser persistence
    // cookieMode: true, // Enable if backend uses HttpOnly refresh tokens
});
```

> **Important:** Never expose `X-Access-Secret` in frontend bundles. Use it server-side only.

See the [configuration reference](index.md#configuration-reference) for all available options.

---

## Modules

The `TenxyteClient` exposes 10 business modules:

| Module | Access | Description |
|---|---|---|
| **Auth** | `tx.auth` | Login, register, logout, refresh, magic link, social OAuth2 |
| **Security** | `tx.security` | 2FA/TOTP, OTP, passwords, WebAuthn/Passkeys |
| **RBAC** | `tx.rbac` | Synchronous JWT checks + roles & permissions CRUD |
| **User** | `tx.user` | Profile CRUD, avatar, admin operations |
| **B2B** | `tx.b2b` | Organizations CRUD, members, invitations, context switching |
| **AI** | `tx.ai` | Agent tokens, HITL, heartbeat, usage, traceability |
| **Applications** | `tx.applications` | API client management, credential regeneration |
| **Admin** | `tx.admin` | Audit logs, login attempts, blacklisted/refresh tokens |
| **GDPR** | `tx.gdpr` | Account deletion, data export |
| **Dashboard** | `tx.dashboard` | Global stats, auth, security, GDPR, per-org |

---

### Authentication (`tx.auth`)

#### Email / Phone Login

```typescript
// Login with email
const tokens = await tx.auth.loginWithEmail({
    email: 'user@example.com',
    password: 'password123',
    device_info: '',
    totp_code: '123456', // optional, for 2FA
});

// Login with phone
const tokens = await tx.auth.loginWithPhone({
    phone_country_code: '+1',
    phone_number: '5551234567',
    password: 'password123',
    device_info: '',
});
```

#### Registration

```typescript
const result = await tx.auth.register({
    email: 'new@example.com',
    password: 'StrongP@ss1',
    first_name: 'Jane',
    last_name: 'Doe',
    login: true, // Returns JWT tokens immediately
});
```

#### Magic Link (Passwordless)

```typescript
await tx.auth.requestMagicLink({
    email: 'user@example.com',
    validation_url: 'https://myapp.com/verify',
});

// After clicking the link, extract the token from the URL
const tokens = await tx.auth.verifyMagicLink(urlToken);
```

#### Social OAuth2 (with PKCE)

```typescript
// With a native id_token (e.g. Apple Sign-In, Google One Tap)
const tokens = await tx.auth.loginWithSocial('google', {
    id_token: 'eyJhbGciOi...',
});

// With an authorization code + PKCE (RFC 7636)
const tokens = await tx.auth.loginWithSocial('google', {
    code: 'authorization_code',
    redirect_uri: 'https://myapp.com/callback',
    code_verifier: 'pkce_verifier_string',
});

// OAuth2 callback (code exchange)
const tokens = await tx.auth.handleSocialCallback(
    'github',
    'authorization_code',
    'https://myapp.com/callback',
    'pkce_verifier', // optional
);
```

Supported providers: `'google'`, `'github'`, `'microsoft'`, `'facebook'`.

#### Session

```typescript
// Logout (parameter is optional in cookie mode)
await tx.auth.logout('refresh_token_value');
await tx.auth.logout(); // cookie mode — server reads the HttpOnly cookie

// Logout from all sessions
await tx.auth.logoutAll();

// Manual refresh (optional in cookie mode)
const newTokens = await tx.auth.refreshToken('refresh_token_value');
const newTokens = await tx.auth.refreshToken(); // cookie mode
```

---

### Security (`tx.security`)

```typescript
// 2FA (TOTP)
const status = await tx.security.get2FAStatus();
const { secret, qr_code_url, backup_codes } = await tx.security.setup2FA();
await tx.security.confirm2FA('123456');
await tx.security.disable2FA('123456');

// OTP
await tx.security.requestOtp({ delivery_method: 'email', purpose: 'login' });
const result = await tx.security.verifyOtp({ otp: '123456', purpose: 'login' });

// Password management
await tx.security.resetPasswordRequest({ email: 'user@example.com' });
await tx.security.resetPasswordConfirm({ token: '...', new_password: 'NewP@ss1' });
await tx.security.changePassword({ old_password: 'old', new_password: 'new' });

// WebAuthn / Passkeys (FIDO2)
await tx.security.registerWebAuthn('My Laptop');
const session = await tx.security.authenticateWebAuthn('user@example.com');
const creds = await tx.security.listWebAuthnCredentials();
await tx.security.deleteWebAuthnCredential(credentialId);
```

---

### RBAC (`tx.rbac`)

```typescript
// Synchronous checks from JWT (no network call)
tx.rbac.setToken(accessToken);
const isAdmin = tx.rbac.hasRole('admin');
const canEdit = tx.rbac.hasPermission('users.edit');
const hasAny = tx.rbac.hasAnyRole(['admin', 'manager']);
const hasAll = tx.rbac.hasAllRoles(['admin', 'superadmin']);

// CRUD operations (network calls)
const roles = await tx.rbac.listRoles();
await tx.rbac.createRole({ code: 'editor', name: 'Editor' });
await tx.rbac.assignRoleToUser('user-id', 'editor');
await tx.rbac.removeRoleFromUser('user-id', 'editor');

const permissions = await tx.rbac.listPermissions();
await tx.rbac.assignPermissionsToUser('user-id', ['posts.create', 'posts.edit']);
await tx.rbac.removePermissionsFromUser('user-id', ['posts.create']);
```

---

### User Management (`tx.user`)

```typescript
const profile = await tx.user.getProfile();
await tx.user.updateProfile({ first_name: 'Updated' });
await tx.user.uploadAvatar(fileFormData);
await tx.user.deleteAccount('my-password');

// Admin operations
const users = await tx.user.listUsers({ page: 1, page_size: 20 });
await tx.user.adminUpdateUser('user-id', { is_active: false });
await tx.user.banUser('user-id', 'spam');
```

---

### B2B Organizations (`tx.b2b`)

```typescript
// Context switching — automatically injects the X-Org-Slug header
tx.b2b.switchOrganization('acme-corp');
tx.b2b.clearOrganization();

// CRUD
const orgs = await tx.b2b.listOrganizations();
const org = await tx.b2b.createOrganization({ name: 'Acme Corp', slug: 'acme-corp' });
await tx.b2b.updateOrganization('acme-corp', { name: 'Acme Corp Inc.' });
await tx.b2b.deleteOrganization('acme-corp');

// Members & invitations
const members = await tx.b2b.listMembers('acme-corp');
await tx.b2b.addMember('acme-corp', { user_id: 'uid', role_code: 'member' });
await tx.b2b.inviteMember('acme-corp', { email: 'dev@example.com', role_code: 'admin' });
```

---

### AI Agent Security (`tx.ai`)

```typescript
// Agent token lifecycle
const agentData = await tx.ai.createAgentToken({
    agent_id: 'Invoice-Parser-Bot',
    permissions: ['invoices.read', 'invoices.create'],
    budget_limit_usd: 5.00,
    circuit_breaker: { max_requests: 100, window_seconds: 60 },
});

tx.ai.setAgentToken(agentData.token); // Switch to AgentBearer mode
tx.ai.clearAgentToken();              // Return to standard Bearer mode

// Human-in-the-Loop
const pending = await tx.ai.listPendingActions();
await tx.ai.confirmPendingAction('confirmation-token');
await tx.ai.denyPendingAction('confirmation-token');

// Monitoring
await tx.ai.sendHeartbeat('token-id');
await tx.ai.reportUsage('token-id', {
    cost_usd: 0.015,
    prompt_tokens: 1540,
    completion_tokens: 420,
});

// Traceability
tx.ai.setTraceId('trace-1234'); // Adds the X-Prompt-Trace-ID header
tx.ai.clearTraceId();
```

---

### Applications (`tx.applications`)

```typescript
const apps = await tx.applications.listApplications();
const app = await tx.applications.createApplication({
    name: 'My API Client',
    description: 'Backend service',
});
await tx.applications.updateApplication('app-id', { name: 'Renamed' });
await tx.applications.deleteApplication('app-id');
const newCreds = await tx.applications.regenerateCredentials('app-id');
```

---

### Admin (`tx.admin`)

```typescript
const logs = await tx.admin.listAuditLogs({ page: 1 });
const attempts = await tx.admin.listLoginAttempts({ user_id: 'uid' });
const blacklisted = await tx.admin.listBlacklistedTokens();
await tx.admin.cleanupBlacklistedTokens();
const refreshTokens = await tx.admin.listRefreshTokens({ user_id: 'uid' });
await tx.admin.revokeRefreshToken('token-id');
```

---

### GDPR (`tx.gdpr`)

```typescript
// User-side
await tx.gdpr.requestAccountDeletion({ reason: 'No longer needed' });
await tx.gdpr.confirmAccountDeletion('confirmation-code');
await tx.gdpr.cancelAccountDeletion();
const data = await tx.gdpr.exportUserData();

// Admin-side
const requests = await tx.gdpr.listDeletionRequests({ status: 'pending' });
await tx.gdpr.processDeletionRequest('request-id', { action: 'approve' });
```

---

### Dashboard (`tx.dashboard`)

```typescript
const global = await tx.dashboard.getStats({ period: 'last_30_days' });
const auth = await tx.dashboard.getAuthStats();
const security = await tx.dashboard.getSecurityStats();
const gdpr = await tx.dashboard.getGdprStats();
const orgStats = await tx.dashboard.getOrganizationStats('acme-corp');
```

---

## Cookie Mode (HttpOnly Refresh Token)

When the backend is configured with `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, the refresh token is no longer returned in the JSON body — it is sent via an `HttpOnly; Secure; SameSite` cookie.

To enable SDK-side support:

```typescript
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

In cookie mode:
- `TokenPair.refresh_token` is absent from the JSON response
- The SDK adds `credentials: 'include'` to refresh/logout requests
- `tx.auth.logout()` and `tx.auth.refreshToken()` can be called without arguments
- The auto-refresh interceptor works without a token stored in storage

See the [Security Guide](../../security.md#cookie-based-refresh-tokens) for backend configuration.

---

## SDK Events

| Event | Payload | When |
|---|---|---|
| `session:expired` | `void` | Refresh token expired/revoked, session unrecoverable |
| `token:refreshed` | `{ accessToken: string }` | Access token silently renewed |
| `token:stored` | `{ accessToken: string; refreshToken?: string }` | Tokens persisted after login/register/refresh |
| `agent:awaiting_approval` | `{ action: unknown }` | AI agent action awaiting human confirmation |
| `error` | `{ error: unknown }` | Unrecoverable SDK error |

```typescript
tx.on('session:expired', () => {
    router.push('/login');
});

tx.on('token:refreshed', ({ accessToken }) => {
    console.log('Token refreshed silently');
});

tx.on('agent:awaiting_approval', ({ action }) => {
    showApprovalDialog(action);
});
```

---

## High-Level Helpers

```typescript
// Check if the user is authenticated (JWT expiry check)
const isLoggedIn = await tx.isAuthenticated();

// Get the raw access token
const token = await tx.getAccessToken();

// Decode the JWT payload (no network call)
const user = await tx.getCurrentUser();

// Check token expiry
const expired = await tx.isTokenExpired();

// Full SDK state snapshot (for framework wrappers)
const state = await tx.getState();
// { isAuthenticated, user, accessToken, activeOrg, isAgentMode }
```

---

## Storage

The SDK provides three storage backends:

| Class | Usage | Persistence |
|---|---|---|
| `MemoryStorage` | Node.js, SSR, tests | No (lost on restart) |
| `LocalStorageAdapter` | Browser SPA | Yes (`localStorage`) |
| `CookieStorage` | SSR / Hybrid | Yes (cookies) |

```typescript
import { LocalStorageAdapter, MemoryStorage } from '@tenxyte/core';

// Browser
const tx = new TenxyteClient({
    baseUrl: '...',
    storage: new LocalStorageAdapter(),
});

// Node.js / tests
const tx = new TenxyteClient({
    baseUrl: '...',
    storage: new MemoryStorage(), // default
});
```

---

## See Also

- [JavaScript SDK Overview](index.md)
- [React Guide](react.md)
- [Vue Guide](vue.md)
- [API Endpoints](../../endpoints.md)
- [Schemas Reference](../../schemas.md)
- [Security Guide](../../security.md)
- [Settings Reference](../../settings.md)
