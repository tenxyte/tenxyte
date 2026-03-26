# @tenxyte/react — Guide d'intégration

> Hooks React pour le SDK Tenxyte. Re-render automatique des composants lorsque l'état d'authentification change.

---

## Installation

```bash
npm install @tenxyte/core @tenxyte/react
```

**Prérequis :** React 18+ ou 19+, `@tenxyte/core` ^0.10.0.

---

## Mise en place

### 1. Créer le client et wrapper l'application

```tsx
// main.tsx
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';
import { TenxyteProvider } from '@tenxyte/react';
import App from './App';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
    storage: new LocalStorageAdapter(),
    // cookieMode: true, // Activer si le backend utilise les refresh tokens HttpOnly
});

function Root() {
    return (
        <TenxyteProvider client={tx}>
            <App />
        </TenxyteProvider>
    );
}
```

### 2. Utiliser les hooks dans n'importe quel composant

```tsx
import { useAuth, useUser, useRbac, useOrganization } from '@tenxyte/react';

function Dashboard() {
    const { isAuthenticated, loading, logout } = useAuth();
    const { user } = useUser();
    const { hasRole } = useRbac();

    if (loading) return <p>Chargement...</p>;
    if (!isAuthenticated) return <LoginPage />;

    return (
        <div>
            <p>Bienvenue, {user?.email}</p>
            {hasRole('admin') && <AdminPanel />}
            <button onClick={logout}>Déconnexion</button>
        </div>
    );
}
```

---

## Hooks

### `useAuth()`

État d'authentification réactif et actions.

```tsx
const {
    isAuthenticated, // boolean — true si le token d'accès est valide et non expiré
    loading,         // boolean — true pendant le chargement initial depuis le storage
    accessToken,     // string | null — token JWT brut
    loginWithEmail,  // (data: { email, password, device_info?, totp_code? }) => Promise<void>
    loginWithPhone,  // (data: { phone_country_code, phone_number, password, device_info? }) => Promise<void>
    logout,          // () => Promise<void>
    register,        // (data) => Promise<void>
} = useAuth();
```

**Exemple — Formulaire de login :**

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
            setError(err.error || 'Échec de la connexion');
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
                placeholder="Mot de passe"
                type="password"
                required
            />
            <button type="submit">Se connecter</button>
        </form>
    );
}
```

**Exemple — Inscription :**

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

    return <button onClick={handleRegister}>Créer un compte</button>;
}
```

---

### `useUser()`

Utilisateur JWT décodé et gestion du profil.

```tsx
const {
    user,          // DecodedTenxyteToken | null — payload JWT décodé
    loading,       // boolean
    getProfile,    // () => Promise<UserProfile> — profil complet depuis l'API
    updateProfile, // (data) => Promise<unknown>
} = useUser();
```

**Exemple :**

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

**Exemple — Édition de profil :**

```tsx
function ProfileEditor() {
    const { user, updateProfile, getProfile } = useUser();
    const [firstName, setFirstName] = useState(user?.first_name ?? '');

    const handleSave = async () => {
        await updateProfile({ first_name: firstName });
        await getProfile(); // Rafraîchir les données
    };

    return (
        <div>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <button onClick={handleSave}>Sauvegarder</button>
        </div>
    );
}
```

---

### `useOrganization()`

Contexte multi-tenant pour les organisations (B2B).

```tsx
const {
    activeOrg,          // string | null — slug de l'org active
    switchOrganization, // (slug: string) => void
    clearOrganization,  // () => void
} = useOrganization();
```

**Exemple :**

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
            <option value="">Aucune organisation</option>
            {orgs.map((o) => (
                <option key={o.slug} value={o.slug}>{o.name}</option>
            ))}
        </select>
    );
}
```

---

### `useRbac()`

Vérifications synchrones de rôles et permissions depuis le JWT courant.

```tsx
const {
    hasRole,       // (role: string) => boolean
    hasPermission, // (permission: string) => boolean
    hasAnyRole,    // (roles: string[]) => boolean
    hasAllRoles,   // (roles: string[]) => boolean
} = useRbac();
```

**Exemple — Garde de route :**

```tsx
import { useRbac } from '@tenxyte/react';

function AdminPanel() {
    const { hasRole } = useRbac();

    if (!hasRole('admin')) {
        return <p>Accès refusé. Rôle admin requis.</p>;
    }

    return <div>Panneau d'administration</div>;
}
```

**Exemple — Rendu conditionnel :**

```tsx
function ActionButtons() {
    const { hasPermission } = useRbac();

    return (
        <div>
            {hasPermission('posts.create') && <button>Nouveau post</button>}
            {hasPermission('posts.delete') && <button>Supprimer</button>}
        </div>
    );
}
```

---

## Accès direct au client

Pour les fonctionnalités non couvertes par les hooks (social login, 2FA, AIRS, etc.), accédez directement au `TenxyteClient` :

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
            <button onClick={handleGoogleLogin}>Se connecter avec Google</button>
        </div>
    );
}
```

### Exemples d'accès direct

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

## Gestion des erreurs

Toutes les méthodes du SDK lèvent un `TenxyteError` en cas d'échec :

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
                    {error.retry_after && <p>Réessayer dans {error.retry_after}s</p>}
                </div>
            )}
            {/* formulaire... */}
        </div>
    );
}
```

Codes d'erreur courants : `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`, `2FA_REQUIRED`, `RATE_LIMITED`, `MISSING_REFRESH_TOKEN`, `INVALID_REDIRECT_URI`.

---

## Cookie Mode

Si le backend est configuré avec `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True` :

```tsx
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

Les hooks fonctionnent de manière transparente — l'auto-refresh utilise les cookies `HttpOnly` au lieu du storage local. Aucune modification de composant nécessaire.

Voir le [Core Guide — Cookie Mode](core.md#cookie-mode-refresh-token-httponly) pour plus de détails.

---

## Fonctionnement interne

`TenxyteProvider` place l'instance `TenxyteClient` dans le contexte React. Chaque hook s'abonne aux événements SDK (`token:stored`, `token:refreshed`, `session:expired`) et déclenche un re-render lorsque l'état d'authentification change. Toutes les mises à jour d'état sont automatiques — aucune invalidation manuelle nécessaire.

---

## Application complète (exemple)

```tsx
// App.tsx
import { useAuth, useUser, useRbac } from '@tenxyte/react';

export default function App() {
    const { isAuthenticated, loading, loginWithEmail, logout } = useAuth();
    const { user } = useUser();
    const { hasRole } = useRbac();

    if (loading) return <div className="spinner">Chargement...</div>;

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
                <input name="password" type="password" placeholder="Mot de passe" required />
                <button type="submit">Connexion</button>
            </form>
        );
    }

    return (
        <div>
            <header>
                <span>Connecté : {user?.email}</span>
                <button onClick={logout}>Déconnexion</button>
            </header>
            <main>
                <h1>Tableau de bord</h1>
                {hasRole('admin') && <section>Zone Admin</section>}
            </main>
        </div>
    );
}
```

---

## Voir aussi

- [JavaScript SDK Overview](index.md)
- [Core Guide](core.md) — API complète des 10 modules
- [Vue Guide](vue.md) — Équivalent pour Vue 3
- [API Endpoints](../../endpoints.md)
- [Security Guide](../../security.md)
