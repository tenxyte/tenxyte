# @tenxyte/vue — Integration Guide

> Vue 3 composables for the Tenxyte SDK. Reactive state updates automatically when authentication state changes.

---

## Installation

```bash
npm install @tenxyte/core @tenxyte/vue
```

**Requirements:** Vue 3.3+, `@tenxyte/core` ^0.10.0.

---

## Setup

### 1. Install the plugin

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
    // cookieMode: true, // Enable if backend uses HttpOnly refresh tokens
});

const app = createApp(App);
app.use(tenxytePlugin, tx);
app.mount('#app');
```

### 2. Use composables in any component

```vue
<script setup lang="ts">
import { useAuth, useUser, useRbac, useOrganization } from '@tenxyte/vue';

const { isAuthenticated, loading, logout } = useAuth();
const { user } = useUser();
const { hasRole } = useRbac();
</script>

<template>
    <p v-if="loading">Loading...</p>

    <div v-else-if="isAuthenticated">
        <p>Welcome, {{ user?.email }}</p>
        <AdminPanel v-if="hasRole('admin')" />
        <button @click="logout">Sign out</button>
    </div>

    <LoginPage v-else />
</template>
```

---

## Composables

### `useAuth()`

Reactive authentication state and actions.

```ts
const {
    isAuthenticated, // Readonly<Ref<boolean>> — true if access token is valid
    loading,         // Readonly<Ref<boolean>> — true during initial load
    accessToken,     // Readonly<Ref<string | null>> — raw JWT token
    loginWithEmail,  // (data: { email, password, device_info?, totp_code? }) => Promise<void>
    loginWithPhone,  // (data: { phone_country_code, phone_number, password, device_info? }) => Promise<void>
    logout,          // () => Promise<void>
    register,        // (data) => Promise<void>
} = useAuth();
```

**Example — Login form:**

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
        error.value = err.error || 'Login failed';
    }
}
</script>

<template>
    <p v-if="loading">Loading...</p>
    <button v-else-if="isAuthenticated" @click="logout">Sign out</button>
    <form v-else @submit.prevent="handleLogin">
        <p v-if="error" style="color: red">{{ error }}</p>
        <input v-model="email" type="email" placeholder="Email" required />
        <input v-model="password" type="password" placeholder="Password" required />
        <button type="submit">Sign in</button>
    </form>
</template>
```

**Example — Registration:**

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
        <input v-model="form.password" type="password" placeholder="Password" required />
        <input v-model="form.first_name" placeholder="First name" />
        <input v-model="form.last_name" placeholder="Last name" />
        <button type="submit">Create account</button>
    </form>
</template>
```

---

### `useUser()`

Decoded JWT user and profile management.

```ts
const {
    user,          // Readonly<Ref<DecodedTenxyteToken | null>> — decoded JWT payload
    loading,       // Readonly<Ref<boolean>>
    getProfile,    // () => Promise<UserProfile> — full profile from API
    updateProfile, // (data) => Promise<unknown>
} = useUser();
```

**Example:**

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

**Example — Profile editing:**

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
        <input v-model="firstName" placeholder="First name" />
        <button @click="handleSave">Save</button>
    </div>
</template>
```

---

### `useOrganization()`

Multi-tenant context for organizations (B2B).

```ts
const {
    activeOrg,          // Readonly<Ref<string | null>> — active org slug
    switchOrganization, // (slug: string) => void
    clearOrganization,  // () => void
} = useOrganization();
```

**Example:**

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
        <option value="">No organization</option>
        <option v-for="org in orgs" :key="org.slug" :value="org.slug">
            {{ org.name }}
        </option>
    </select>
</template>
```

---

### `useRbac()`

Synchronous role and permission checks from the current JWT.

```ts
const {
    hasRole,       // (role: string) => boolean
    hasPermission, // (permission: string) => boolean
    hasAnyRole,    // (roles: string[]) => boolean
    hasAllRoles,   // (roles: string[]) => boolean
} = useRbac();
```

**Example — Component guard:**

```vue
<script setup lang="ts">
import { useRbac } from '@tenxyte/vue';
const { hasRole } = useRbac();
</script>

<template>
    <div v-if="hasRole('admin')">
        <h2>Administration panel</h2>
        <!-- admin content -->
    </div>
    <p v-else>Access denied. Admin role required.</p>
</template>
```

**Example — Conditional rendering:**

```vue
<script setup lang="ts">
import { useRbac } from '@tenxyte/vue';
const { hasPermission } = useRbac();
</script>

<template>
    <div>
        <button v-if="hasPermission('posts.create')">New post</button>
        <button v-if="hasPermission('posts.delete')">Delete</button>
    </div>
</template>
```

---

## Direct Client Access

For features not covered by composables (social login, 2FA, AIRS, etc.), access the `TenxyteClient` directly:

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
    <button @click="handleGoogleLogin">Sign in with Google</button>
</template>
```

### Direct access examples

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

## Error Handling

All SDK methods throw a `TenxyteError` on failure:

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
        <p v-if="error.retry_after">Retry in {{ error.retry_after }}s</p>
    </div>
</template>
```

Common error codes: `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`, `2FA_REQUIRED`, `RATE_LIMITED`, `MISSING_REFRESH_TOKEN`, `INVALID_REDIRECT_URI`.

---

## Cookie Mode

If the backend is configured with `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`:

```ts
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    headers: { 'X-Access-Key': '<key>' },
    cookieMode: true,
});
```

Composables work transparently — auto-refresh uses `HttpOnly` cookies instead of local storage. No component changes required.

See the [Core Guide — Cookie Mode](core.md#cookie-mode-httponly-refresh-token) for details.

---

## How It Works

The `tenxytePlugin` provides the `TenxyteClient` instance via Vue's dependency injection (`app.provide`). Each composable calls `useTenxyteClient()` internally to retrieve the client, then subscribes to SDK events (`token:stored`, `token:refreshed`, `session:expired`) via `onMounted`/`onUnmounted` lifecycle hooks. Reactive state is exposed as `readonly(ref(...))` so templates update automatically.

---

## Full Application Example

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
    <div v-if="loading" class="spinner">Loading...</div>

    <form v-else-if="!isAuthenticated" @submit.prevent="handleLogin">
        <input v-model="email" type="email" placeholder="Email" required />
        <input v-model="password" type="password" placeholder="Password" required />
        <button type="submit">Sign in</button>
    </form>

    <div v-else>
        <header>
            <span>Signed in as: {{ user?.email }}</span>
            <button @click="logout">Sign out</button>
        </header>
        <main>
            <h1>Dashboard</h1>
            <section v-if="hasRole('admin')">Admin area</section>
        </main>
    </div>
</template>
```

---

## See Also

- [JavaScript SDK Overview](index.md)
- [Core Guide](core.md) — Full API for all 10 modules
- [React Guide](react.md) — React equivalent
- [API Endpoints](../../endpoints.md)
- [Security Guide](../../security.md)
