# @tenxyte/core — Guide d'intégration

> SDK JavaScript/TypeScript framework-agnostic pour l'API Tenxyte. Fonctionne dans Node.js, les navigateurs, et tout runtime JS.

---

## Installation

```bash
npm install @tenxyte/core
# ou
yarn add @tenxyte/core
# ou
pnpm add @tenxyte/core
```

---

## Initialisation

```typescript
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
    storage: new LocalStorageAdapter(), // Persistance navigateur
    // cookieMode: true, // Activer si le backend utilise les refresh tokens HttpOnly
});
```

> **Important :** Ne jamais exposer `X-Access-Secret` dans les bundles frontend. Utiliser exclusivement côté serveur.

Voir la [référence de configuration](index.md#configuration-reference) pour toutes les options disponibles.

---

## Modules

Le `TenxyteClient` expose 10 modules métier :

| Module | Accès | Description |
|---|---|---|
| **Auth** | `tx.auth` | Login, register, logout, refresh, magic link, social OAuth2 |
| **Security** | `tx.security` | 2FA/TOTP, OTP, mots de passe, WebAuthn/Passkeys |
| **RBAC** | `tx.rbac` | Vérifications JWT synchrones + CRUD rôles & permissions |
| **User** | `tx.user` | Profil CRUD, avatar, opérations admin |
| **B2B** | `tx.b2b` | Organisations CRUD, membres, invitations, context switching |
| **AI** | `tx.ai` | Tokens agents, HITL, heartbeat, usage, traçabilité |
| **Applications** | `tx.applications` | Gestion des clients API, régénération de credentials |
| **Admin** | `tx.admin` | Logs d'audit, tentatives de login, tokens blacklistés/refresh |
| **GDPR** | `tx.gdpr` | Suppression de compte, export de données |
| **Dashboard** | `tx.dashboard` | Statistiques globales, auth, sécurité, GDPR, par org |

---

### Authentication (`tx.auth`)

#### Login email / téléphone

```typescript
// Login par email
const tokens = await tx.auth.loginWithEmail({
    email: 'user@example.com',
    password: 'password123',
    device_info: '',
    totp_code: '123456', // optionnel, pour 2FA
});

// Login par téléphone
const tokens = await tx.auth.loginWithPhone({
    phone_country_code: '+33',
    phone_number: '612345678',
    password: 'password123',
    device_info: '',
});
```

#### Inscription

```typescript
const result = await tx.auth.register({
    email: 'new@example.com',
    password: 'StrongP@ss1',
    first_name: 'Jane',
    last_name: 'Doe',
    login: true, // Retourne les JWT directement
});
```

#### Magic Link (sans mot de passe)

```typescript
await tx.auth.requestMagicLink({
    email: 'user@example.com',
    validation_url: 'https://myapp.com/verify',
});

// Après clic sur le lien, extraire le token de l'URL
const tokens = await tx.auth.verifyMagicLink(urlToken);
```

#### Social OAuth2 (avec PKCE)

```typescript
// Avec un id_token natif (ex: Apple Sign-In, Google One Tap)
const tokens = await tx.auth.loginWithSocial('google', {
    id_token: 'eyJhbGciOi...',
});

// Avec un authorization code + PKCE (RFC 7636)
const tokens = await tx.auth.loginWithSocial('google', {
    code: 'authorization_code',
    redirect_uri: 'https://myapp.com/callback',
    code_verifier: 'pkce_verifier_string',
});

// Callback OAuth2 (code exchange)
const tokens = await tx.auth.handleSocialCallback(
    'github',
    'authorization_code',
    'https://myapp.com/callback',
    'pkce_verifier', // optionnel
);
```

Providers supportés : `'google'`, `'github'`, `'microsoft'`, `'facebook'`.

#### Session

```typescript
// Logout (le paramètre est optionnel en cookie mode)
await tx.auth.logout('refresh_token_value');
await tx.auth.logout(); // cookie mode — le serveur lit le cookie HttpOnly

// Logout de toutes les sessions
await tx.auth.logoutAll();

// Refresh manuel (optionnel en cookie mode)
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

// Gestion des mots de passe
await tx.security.resetPasswordRequest({ email: 'user@example.com' });
await tx.security.resetPasswordConfirm({ token: '...', new_password: 'NewP@ss1' });
await tx.security.changePassword({ old_password: 'old', new_password: 'new' });

// WebAuthn / Passkeys (FIDO2)
await tx.security.registerWebAuthn('Mon Laptop');
const session = await tx.security.authenticateWebAuthn('user@example.com');
const creds = await tx.security.listWebAuthnCredentials();
await tx.security.deleteWebAuthnCredential(credentialId);
```

---

### RBAC (`tx.rbac`)

```typescript
// Vérifications synchrones depuis le JWT (aucun appel réseau)
tx.rbac.setToken(accessToken);
const isAdmin = tx.rbac.hasRole('admin');
const canEdit = tx.rbac.hasPermission('users.edit');
const hasAny = tx.rbac.hasAnyRole(['admin', 'manager']);
const hasAll = tx.rbac.hasAllRoles(['admin', 'superadmin']);

// Opérations CRUD (appels réseau)
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

// Opérations admin
const users = await tx.user.listUsers({ page: 1, page_size: 20 });
await tx.user.adminUpdateUser('user-id', { is_active: false });
await tx.user.banUser('user-id', 'spam');
```

---

### B2B Organizations (`tx.b2b`)

```typescript
// Context switching — injecte automatiquement le header X-Org-Slug
tx.b2b.switchOrganization('acme-corp');
tx.b2b.clearOrganization();

// CRUD
const orgs = await tx.b2b.listOrganizations();
const org = await tx.b2b.createOrganization({ name: 'Acme Corp', slug: 'acme-corp' });
await tx.b2b.updateOrganization('acme-corp', { name: 'Acme Corp Inc.' });
await tx.b2b.deleteOrganization('acme-corp');

// Membres & invitations
const members = await tx.b2b.listMembers('acme-corp');
await tx.b2b.addMember('acme-corp', { user_id: 'uid', role_code: 'member' });
await tx.b2b.inviteMember('acme-corp', { email: 'dev@example.com', role_code: 'admin' });
```

---

### AI Agent Security (`tx.ai`)

```typescript
// Cycle de vie des tokens agents
const agentData = await tx.ai.createAgentToken({
    agent_id: 'Invoice-Parser-Bot',
    permissions: ['invoices.read', 'invoices.create'],
    budget_limit_usd: 5.00,
    circuit_breaker: { max_requests: 100, window_seconds: 60 },
});

tx.ai.setAgentToken(agentData.token); // Bascule en mode AgentBearer
tx.ai.clearAgentToken();              // Retour en mode Bearer standard

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

// Traçabilité
tx.ai.setTraceId('trace-1234'); // Ajoute le header X-Prompt-Trace-ID
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
// Côté utilisateur
await tx.gdpr.requestAccountDeletion({ reason: 'No longer needed' });
await tx.gdpr.confirmAccountDeletion('confirmation-code');
await tx.gdpr.cancelAccountDeletion();
const data = await tx.gdpr.exportUserData();

// Côté admin
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

## Cookie Mode (Refresh Token HttpOnly)

Lorsque le backend est configuré avec `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, le refresh token n'est plus retourné dans le corps JSON — il est transmis via un cookie `HttpOnly; Secure; SameSite`.

Pour activer le support côté SDK :

```typescript
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

En cookie mode :
- `TokenPair.refresh_token` est absent de la réponse JSON
- Le SDK ajoute `credentials: 'include'` aux requêtes refresh/logout
- `tx.auth.logout()` et `tx.auth.refreshToken()` peuvent être appelés sans argument
- L'intercepteur auto-refresh fonctionne sans token stocké en storage

Voir le [Security Guide](../../security.md#cookie-based-refresh-tokens) pour la configuration backend.

---

## Événements SDK

| Événement | Payload | Quand |
|---|---|---|
| `session:expired` | `void` | Refresh token expiré/révoqué, session irrécupérable |
| `token:refreshed` | `{ accessToken: string }` | Access token silencieusement renouvelé |
| `token:stored` | `{ accessToken: string; refreshToken?: string }` | Tokens persistés après login/register/refresh |
| `agent:awaiting_approval` | `{ action: unknown }` | Action agent IA en attente de confirmation humaine |
| `error` | `{ error: unknown }` | Erreur SDK irrécupérable |

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

## Helpers de haut niveau

```typescript
// Vérifie si l'utilisateur est authentifié (vérification expiration JWT)
const isLoggedIn = await tx.isAuthenticated();

// Récupère le token d'accès brut
const token = await tx.getAccessToken();

// Décode le JWT payload (aucun appel réseau)
const user = await tx.getCurrentUser();

// Vérifie l'expiration du token
const expired = await tx.isTokenExpired();

// Snapshot complet de l'état SDK (pour les wrappers framework)
const state = await tx.getState();
// { isAuthenticated, user, accessToken, activeOrg, isAgentMode }
```

---

## Storage

Le SDK propose trois backends de stockage :

| Classe | Utilisation | Persistance |
|---|---|---|
| `MemoryStorage` | Node.js, SSR, tests | Non (perdu au restart) |
| `LocalStorageAdapter` | Navigateur SPA | Oui (`localStorage`) |
| `CookieStorage` | SSR / Hybrid | Oui (cookies) |

```typescript
import { LocalStorageAdapter, MemoryStorage } from '@tenxyte/core';

// Navigateur
const tx = new TenxyteClient({
    baseUrl: '...',
    storage: new LocalStorageAdapter(),
});

// Node.js / tests
const tx = new TenxyteClient({
    baseUrl: '...',
    storage: new MemoryStorage(), // défaut
});
```

---

## Voir aussi

- [JavaScript SDK Overview](index.md)
- [React Guide](react.md)
- [Vue Guide](vue.md)
- [API Endpoints](../../endpoints.md)
- [Schemas Reference](../../schemas.md)
- [Security Guide](../../security.md)
- [Settings Reference](../../settings.md)
