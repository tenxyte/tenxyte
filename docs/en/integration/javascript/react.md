# @tenxyte/react — Integration Guide

> React hooks for the Tenxyte SDK. Components automatically re-render when authentication state changes.

---

## Installation

```bash
npm install @tenxyte/core @tenxyte/react
```

**Requirements:** React 18+ or 19+, `@tenxyte/core` ^0.10.0.

---

## Setup

### 1. Create the client and wrap your application

```tsx
// main.tsx
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';
import { TenxyteProvider } from '@tenxyte/react';
import App from './App';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
    storage: new LocalStorageAdapter(),
    // cookieMode: true, // Enable if backend uses HttpOnly refresh tokens
});

function Root() {
    return (
        <TenxyteProvider client={tx}>
            <App />
        </TenxyteProvider>
    );
}
```

### 2. Use hooks in any component

```tsx
import { useAuth, useUser, useRbac, useOrganization } from '@tenxyte/react';

function Dashboard() {
    const { isAuthenticated, loading, logout } = useAuth();
    const { user } = useUser();
    const { hasRole } = useRbac();

    if (loading) return <p>Loading...</p>;
    if (!isAuthenticated) return <LoginPage />;

    return (
        <div>
            <p>Welcome, {user?.email}</p>
            {hasRole('admin') && <AdminPanel />}
            <button onClick={logout}>Sign out</button>
        </div>
    );
}
```

---

## Hooks

### `useAuth()`

Reactive authentication state and actions.

```tsx
const {
    isAuthenticated, // boolean — true if access token is valid and not expired
    loading,         // boolean — true during initial load from storage
    accessToken,     // string | null — raw JWT token
    loginWithEmail,  // (data: { email, password, device_info?, totp_code? }) => Promise<void>
    loginWithPhone,  // (data: { phone_country_code, phone_number, password, device_info? }) => Promise<void>
    logout,          // () => Promise<void>
    register,        // (data) => Promise<void>
} = useAuth();
```

**Example — Login form:**

```tsx
import { useState, FormEvent } from 'react';
import { useAuth } from '@tenxyte/react';

function LoginPage() {
    const { loginWithEmail } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        try {
            await loginWithEmail({ email, password });
        } catch (err: any) {
            setError(err.error || 'Login failed');
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                type="email"
                required
            />
            <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                type="password"
                required
            />
            <button type="submit">Sign in</button>
        </form>
    );
}
```

**Example — Registration:**

```tsx
function RegisterPage() {
    const { register } = useAuth();

    const handleRegister = async () => {
        await register({
            email: 'new@example.com',
            password: 'StrongP@ss1',
            first_name: 'Jane',
            last_name: 'Doe',
        });
    };

    return <button onClick={handleRegister}>Create account</button>;
}
```

---

### `useUser()`

Decoded JWT user and profile management.

```tsx
const {
    user,          // DecodedTenxyteToken | null — decoded JWT payload
    loading,       // boolean
    getProfile,    // () => Promise<UserProfile> — full profile from API
    updateProfile, // (data) => Promise<unknown>
} = useUser();
```

**Example:**

```tsx
import { useUser } from '@tenxyte/react';

function UserBadge() {
    const { user, loading } = useUser();
    if (loading || !user) return null;

    return (
        <div>
            <span>{user.first_name} {user.last_name}</span>
            <small>{user.email}</small>
        </div>
    );
}
```

**Example — Profile editing:**

```tsx
function ProfileEditor() {
    const { user, updateProfile, getProfile } = useUser();
    const [firstName, setFirstName] = useState(user?.first_name ?? '');

    const handleSave = async () => {
        await updateProfile({ first_name: firstName });
        await getProfile(); // Refresh data
    };

    return (
        <div>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <button onClick={handleSave}>Save</button>
        </div>
    );
}
```

---

### `useOrganization()`

Multi-tenant context for organizations (B2B).

```tsx
const {
    activeOrg,          // string | null — active org slug
    switchOrganization, // (slug: string) => void
    clearOrganization,  // () => void
} = useOrganization();
```

**Example:**

```tsx
import { useOrganization } from '@tenxyte/react';

function OrgSwitcher({ orgs }: { orgs: { slug: string; name: string }[] }) {
    const { activeOrg, switchOrganization, clearOrganization } = useOrganization();

    return (
        <select
            value={activeOrg ?? ''}
            onChange={(e) =>
                e.target.value ? switchOrganization(e.target.value) : clearOrganization()
            }
        >
            <option value="">No organization</option>
            {orgs.map((o) => (
                <option key={o.slug} value={o.slug}>{o.name}</option>
            ))}
        </select>
    );
}
```

---

### `useRbac()`

Synchronous role and permission checks from the current JWT.

```tsx
const {
    hasRole,       // (role: string) => boolean
    hasPermission, // (permission: string) => boolean
    hasAnyRole,    // (roles: string[]) => boolean
    hasAllRoles,   // (roles: string[]) => boolean
} = useRbac();
```

**Example — Route guard:**

```tsx
import { useRbac } from '@tenxyte/react';

function AdminPanel() {
    const { hasRole } = useRbac();

    if (!hasRole('admin')) {
        return <p>Access denied. Admin role required.</p>;
    }

    return <div>Administration panel</div>;
}
```

**Example — Conditional rendering:**

```tsx
function ActionButtons() {
    const { hasPermission } = useRbac();

    return (
        <div>
            {hasPermission('posts.create') && <button>New post</button>}
            {hasPermission('posts.delete') && <button>Delete</button>}
        </div>
    );
}
```

---

## Direct Client Access

For features not covered by hooks (social login, 2FA, AIRS, etc.), access the `TenxyteClient` directly:

```tsx
import { useTenxyteClient } from '@tenxyte/react';

function SocialLoginButtons() {
    const client = useTenxyteClient();

    const handleGoogleLogin = async () => {
        await client.auth.loginWithSocial('google', {
            id_token: 'google-jwt-token',
        });
    };

    const handleGitHubCallback = async (code: string, redirectUri: string, codeVerifier?: string) => {
        await client.auth.handleSocialCallback('github', code, redirectUri, codeVerifier);
    };

    return (
        <div>
            <button onClick={handleGoogleLogin}>Sign in with Google</button>
        </div>
    );
}
```

### Direct access examples

```tsx
const client = useTenxyteClient();

// 2FA
const status = await client.security.get2FAStatus();
await client.security.setup2FA();

// Magic Link
await client.auth.requestMagicLink({
    email: 'user@example.com',
    validation_url: 'https://myapp.com/verify',
});

// AIRS
const agents = await client.ai.listAgentTokens();

// GDPR
await client.gdpr.requestAccountDeletion({ reason: 'Test' });
```

---

## Error Handling

All SDK methods throw a `TenxyteError` on failure:

```tsx
import type { TenxyteError } from '@tenxyte/core';

function LoginForm() {
    const { loginWithEmail } = useAuth();
    const [error, setError] = useState<TenxyteError | null>(null);

    const handleLogin = async (email: string, password: string) => {
        try {
            setError(null);
            await loginWithEmail({ email, password });
        } catch (err) {
            setError(err as TenxyteError);
        }
    };

    return (
        <div>
            {error && (
                <div className="error">
                    <strong>{error.code}</strong>: {error.error}
                    {error.retry_after && <p>Retry in {error.retry_after}s</p>}
                </div>
            )}
            {/* form... */}
        </div>
    );
}
```

Common error codes: `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`, `2FA_REQUIRED`, `RATE_LIMITED`, `MISSING_REFRESH_TOKEN`, `INVALID_REDIRECT_URI`.

---

## Cookie Mode

If the backend is configured with `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`:

```tsx
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

Hooks work transparently — auto-refresh uses `HttpOnly` cookies instead of local storage. No component changes required.

See the [Core Guide — Cookie Mode](core.md#cookie-mode-httponly-refresh-token) for details.

---

## How It Works

`TenxyteProvider` places the `TenxyteClient` instance in React context. Each hook subscribes to SDK events (`token:stored`, `token:refreshed`, `session:expired`) and triggers a re-render when authentication state changes. All state updates are automatic — no manual invalidation needed.

---

## Full Application Example

```tsx
// App.tsx
import { useAuth, useUser, useRbac } from '@tenxyte/react';

export default function App() {
    const { isAuthenticated, loading, loginWithEmail, logout } = useAuth();
    const { user } = useUser();
    const { hasRole } = useRbac();

    if (loading) return <div className="spinner">Loading...</div>;

    if (!isAuthenticated) {
        return (
            <form onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                await loginWithEmail({
                    email: fd.get('email') as string,
                    password: fd.get('password') as string,
                });
            }}>
                <input name="email" type="email" placeholder="Email" required />
                <input name="password" type="password" placeholder="Password" required />
                <button type="submit">Sign in</button>
            </form>
        );
    }

    return (
        <div>
            <header>
                <span>Signed in as: {user?.email}</span>
                <button onClick={logout}>Sign out</button>
            </header>
            <main>
                <h1>Dashboard</h1>
                {hasRole('admin') && <section>Admin area</section>}
            </main>
        </div>
    );
}
```

---

## See Also

- [JavaScript SDK Overview](index.md)
- [Core Guide](core.md) — Full API for all 10 modules
- [Vue Guide](vue.md) — Vue 3 equivalent
- [API Endpoints](../../endpoints.md)
- [Security Guide](../../security.md)
