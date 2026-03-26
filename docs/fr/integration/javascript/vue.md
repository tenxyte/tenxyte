# @tenxyte/vue — Guide d'intégration

> Composables Vue 3 pour le SDK Tenxyte. Mise à jour réactive automatique lorsque l'état d'authentification change.

---

## Installation

```bash
npm install @tenxyte/core @tenxyte/vue
```

**Prérequis :** Vue 3.3+, `@tenxyte/core` ^0.10.0.

---

## Mise en place

### 1. Installer le plugin

```ts
// main.ts
import { createApp } from 'vue';
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';
import { tenxytePlugin } from '@tenxyte/vue';
import App from './App.vue';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<your-access-key>' },
    storage: new LocalStorageAdapter(),
    // cookieMode: true, // Activer si le backend utilise les refresh tokens HttpOnly
});

const app = createApp(App);
app.use(tenxytePlugin, tx);
app.mount('#app');
```

### 2. Utiliser les composables dans n'importe quel composant

```vue
<script setup lang="ts">
import { useAuth, useUser, useRbac, useOrganization } from '@tenxyte/vue';

const { isAuthenticated, loading, logout } = useAuth();
const { user } = useUser();
const { hasRole } = useRbac();
</script>

<template>
    <p v-if="loading">Chargement...</p>

    <div v-else-if="isAuthenticated">
        <p>Bienvenue, {{ user?.email }}</p>
        <AdminPanel v-if="hasRole('admin')" />
        <button @click="logout">Déconnexion</button>
    </div>

    <LoginPage v-else />
</template>
```

---

## Composables

### `useAuth()`

État d'authentification réactif et actions.

```ts
const {
    isAuthenticated, // Readonly<Ref<boolean>> — true si le token d'accès est valide
    loading,         // Readonly<Ref<boolean>> — true pendant le chargement initial
    accessToken,     // Readonly<Ref<string | null>> — token JWT brut
    loginWithEmail,  // (data: { email, password, device_info?, totp_code? }) => Promise<void>
    loginWithPhone,  // (data: { phone_country_code, phone_number, password, device_info? }) => Promise<void>
    logout,          // () => Promise<void>
    register,        // (data) => Promise<void>
} = useAuth();
```

**Exemple — Formulaire de login :**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useAuth } from '@tenxyte/vue';

const { isAuthenticated, loginWithEmail, logout, loading } = useAuth();
const email = ref('');
const password = ref('');
const error = ref('');

async function handleLogin() {
    error.value = '';
    try {
        await loginWithEmail({ email: email.value, password: password.value });
    } catch (err: any) {
        error.value = err.error || 'Échec de la connexion';
    }
}
</script>

<template>
    <p v-if="loading">Chargement...</p>
    <button v-else-if="isAuthenticated" @click="logout">Déconnexion</button>
    <form v-else @submit.prevent="handleLogin">
        <p v-if="error" style="color: red">{{ error }}</p>
        <input v-model="email" type="email" placeholder="Email" required />
        <input v-model="password" type="password" placeholder="Mot de passe" required />
        <button type="submit">Se connecter</button>
    </form>
</template>
```

**Exemple — Inscription :**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useAuth } from '@tenxyte/vue';

const { register } = useAuth();
const form = ref({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
});

async function handleRegister() {
    await register(form.value);
}
</script>

<template>
    <form @submit.prevent="handleRegister">
        <input v-model="form.email" type="email" placeholder="Email" required />
        <input v-model="form.password" type="password" placeholder="Mot de passe" required />
        <input v-model="form.first_name" placeholder="Prénom" />
        <input v-model="form.last_name" placeholder="Nom" />
        <button type="submit">Créer un compte</button>
    </form>
</template>
```

---

### `useUser()`

Utilisateur JWT décodé et gestion du profil.

```ts
const {
    user,          // Readonly<Ref<DecodedTenxyteToken | null>> — payload JWT décodé
    loading,       // Readonly<Ref<boolean>>
    getProfile,    // () => Promise<UserProfile> — profil complet depuis l'API
    updateProfile, // (data) => Promise<unknown>
} = useUser();
```

**Exemple :**

```vue
<script setup lang="ts">
import { useUser } from '@tenxyte/vue';
const { user, loading } = useUser();
</script>

<template>
    <div v-if="!loading && user">
        <span>{{ user.first_name }} {{ user.last_name }}</span>
        <small>{{ user.email }}</small>
    </div>
</template>
```

**Exemple — Édition de profil :**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useUser } from '@tenxyte/vue';

const { user, updateProfile, getProfile } = useUser();
const firstName = ref(user.value?.first_name ?? '');

async function handleSave() {
    await updateProfile({ first_name: firstName.value });
    await getProfile();
}
</script>

<template>
    <div>
        <input v-model="firstName" placeholder="Prénom" />
        <button @click="handleSave">Sauvegarder</button>
    </div>
</template>
```

---

### `useOrganization()`

Contexte multi-tenant pour les organisations (B2B).

```ts
const {
    activeOrg,          // Readonly<Ref<string | null>> — slug de l'org active
    switchOrganization, // (slug: string) => void
    clearOrganization,  // () => void
} = useOrganization();
```

**Exemple :**

```vue
<script setup lang="ts">
import { useOrganization } from '@tenxyte/vue';

const props = defineProps<{ orgs: { slug: string; name: string }[] }>();
const { activeOrg, switchOrganization, clearOrganization } = useOrganization();

function handleChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    value ? switchOrganization(value) : clearOrganization();
}
</script>

<template>
    <select :value="activeOrg ?? ''" @change="handleChange">
        <option value="">Aucune organisation</option>
        <option v-for="org in orgs" :key="org.slug" :value="org.slug">
            {{ org.name }}
        </option>
    </select>
</template>
```

---

### `useRbac()`

Vérifications synchrones de rôles et permissions depuis le JWT courant.

```ts
const {
    hasRole,       // (role: string) => boolean
    hasPermission, // (permission: string) => boolean
    hasAnyRole,    // (roles: string[]) => boolean
    hasAllRoles,   // (roles: string[]) => boolean
} = useRbac();
```

**Exemple — Garde de composant :**

```vue
<script setup lang="ts">
import { useRbac } from '@tenxyte/vue';
const { hasRole } = useRbac();
</script>

<template>
    <div v-if="hasRole('admin')">
        <h2>Panneau d'administration</h2>
        <!-- contenu admin -->
    </div>
    <p v-else>Accès refusé. Rôle admin requis.</p>
</template>
```

**Exemple — Rendu conditionnel :**

```vue
<script setup lang="ts">
import { useRbac } from '@tenxyte/vue';
const { hasPermission } = useRbac();
</script>

<template>
    <div>
        <button v-if="hasPermission('posts.create')">Nouveau post</button>
        <button v-if="hasPermission('posts.delete')">Supprimer</button>
    </div>
</template>
```

---

## Accès direct au client

Pour les fonctionnalités non couvertes par les composables (social login, 2FA, AIRS, etc.), accédez directement au `TenxyteClient` :

```vue
<script setup lang="ts">
import { useTenxyteClient } from '@tenxyte/vue';

const client = useTenxyteClient();

async function handleGoogleLogin() {
    await client.auth.loginWithSocial('google', {
        id_token: 'google-jwt-token',
    });
}

async function handleGitHubCallback(code: string, redirectUri: string, codeVerifier?: string) {
    await client.auth.handleSocialCallback('github', code, redirectUri, codeVerifier);
}
</script>

<template>
    <button @click="handleGoogleLogin">Se connecter avec Google</button>
</template>
```

### Exemples d'accès direct

```ts
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

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useAuth } from '@tenxyte/vue';
import type { TenxyteError } from '@tenxyte/core';

const { loginWithEmail } = useAuth();
const error = ref<TenxyteError | null>(null);

async function handleLogin(email: string, password: string) {
    try {
        error.value = null;
        await loginWithEmail({ email, password });
    } catch (err) {
        error.value = err as TenxyteError;
    }
}
</script>

<template>
    <div v-if="error" class="error">
        <strong>{{ error.code }}</strong>: {{ error.error }}
        <p v-if="error.retry_after">Réessayer dans {{ error.retry_after }}s</p>
    </div>
</template>
```

Codes d'erreur courants : `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`, `2FA_REQUIRED`, `RATE_LIMITED`, `MISSING_REFRESH_TOKEN`, `INVALID_REDIRECT_URI`.

---

## Cookie Mode

Si le backend est configuré avec `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True` :

```ts
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

Les composables fonctionnent de manière transparente — l'auto-refresh utilise les cookies `HttpOnly` au lieu du storage local. Aucune modification de composant nécessaire.

Voir le [Core Guide — Cookie Mode](core.md#cookie-mode-refresh-token-httponly) pour plus de détails.

---

## Fonctionnement interne

Le `tenxytePlugin` fournit l'instance `TenxyteClient` via l'injection de dépendances de Vue (`app.provide`). Chaque composable appelle `useTenxyteClient()` en interne pour récupérer le client, puis s'abonne aux événements SDK (`token:stored`, `token:refreshed`, `session:expired`) via les hooks de cycle de vie `onMounted`/`onUnmounted`. L'état réactif est exposé en `readonly(ref(...))` pour que les templates se mettent à jour automatiquement.

---

## Application complète (exemple)

```vue
<!-- App.vue -->
<script setup lang="ts">
import { ref } from 'vue';
import { useAuth, useUser, useRbac } from '@tenxyte/vue';

const { isAuthenticated, loading, loginWithEmail, logout } = useAuth();
const { user } = useUser();
const { hasRole } = useRbac();

const email = ref('');
const password = ref('');

async function handleLogin() {
    await loginWithEmail({ email: email.value, password: password.value });
}
</script>

<template>
    <div v-if="loading" class="spinner">Chargement...</div>

    <form v-else-if="!isAuthenticated" @submit.prevent="handleLogin">
        <input v-model="email" type="email" placeholder="Email" required />
        <input v-model="password" type="password" placeholder="Mot de passe" required />
        <button type="submit">Connexion</button>
    </form>

    <div v-else>
        <header>
            <span>Connecté : {{ user?.email }}</span>
            <button @click="logout">Déconnexion</button>
        </header>
        <main>
            <h1>Tableau de bord</h1>
            <section v-if="hasRole('admin')">Zone Admin</section>
        </main>
    </div>
</template>
```

---

## Voir aussi

- [JavaScript SDK Overview](index.md)
- [Core Guide](core.md) — API complète des 10 modules
- [React Guide](react.md) — Équivalent pour React
- [API Endpoints](../../endpoints.md)
- [Security Guide](../../security.md)
