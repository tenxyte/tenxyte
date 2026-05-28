# Intégration SDK JavaScript / TypeScript

> SDK client officiel pour intégrer un backend Tenxyte dans n'importe quelle application JavaScript ou TypeScript — Node.js, navigateurs, React, Vue, ou vanilla JS.

---

## Packages

Le SDK JS Tenxyte est un monorepo livrant trois packages :

| Package | Description | Guide |
|---|---|---|
| [`@tenxyte/core`](https://www.npmjs.com/package/@tenxyte/core) | SDK core agnostique au framework — fonctionne dans Node.js, les navigateurs et tout runtime JS | [Guide Core](core.md) |
| [`@tenxyte/react`](https://www.npmjs.com/package/@tenxyte/react) | Hooks React avec re-render automatique lors des changements d'état d'authentification | [Guide React](react.md) |
| [`@tenxyte/vue`](https://www.npmjs.com/package/@tenxyte/vue) | Composables Vue 3 avec refs réactives | [Guide Vue](vue.md) |

---

## Installation

```bash
# SDK Core uniquement (Node.js, vanilla JS, tout runtime)
npm install @tenxyte/core

# Bindings React (nécessite React 18+ ou 19+)
npm install @tenxyte/core @tenxyte/react

# Bindings Vue 3 (nécessite Vue 3.3+)
npm install @tenxyte/core @tenxyte/vue
```

> **Prérequis :** Node.js 18+ ou tout navigateur moderne. Les types TypeScript sont inclus — aucun package `@types` séparé n'est nécessaire.

---

## Exemple minimal

```typescript
import { TenxyteClient, LocalStorageAdapter } from '@tenxyte/core';

const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    accessKey: 'pkg_abc123',            // ✅ frontend et backend
    storage: new LocalStorageAdapter(),  // Persistance navigateur
});

// Inscription
await tx.auth.register({
    email: 'user@example.com',
    password: 'SecureP@ss1!',
    first_name: 'John',
    last_name: 'Doe',
});

// Connexion
const tokens = await tx.auth.loginWithEmail({
    email: 'user@example.com',
    password: 'SecureP@ss1!',
    device_info: '',
});

// Requête authentifiée — le header Authorization est injecté automatiquement
const profile = await tx.user.getProfile();
```

Les tokens sont stockés automatiquement, les 401 déclenchent un refresh silencieux, et `Authorization: Bearer <token>` est injecté dans chaque requête.

---

## Authentification applicative (Dual-Mode)

Tenxyte supporte deux modes d'authentification applicative :

| Mode | Configuration SDK | Cas d'usage |
|------|------------------|-------------|
| **Frontend** (navigateur) | `accessKey` uniquement | SPA, apps web — l'`Origin` est validée côté serveur contre `allowed_origins` |
| **Backend** (serveur → serveur) | `accessKey` + `accessSecret` | Cron jobs, webhooks, scripts admin |

```typescript
// Frontend (navigateur) — seule la clé publique est nécessaire
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    accessKey: 'pkg_abc123',
    storage: new LocalStorageAdapter(),
});

// Backend (Node.js) — clé + secret
const tx = new TenxyteClient({
    baseUrl: 'https://api.my-backend.com',
    accessKey: 'pkg_abc123',
    accessSecret: process.env.TENXYTE_SECRET,
});
```

> **Guardrail navigateur :** Si `accessSecret` est fourni dans un environnement navigateur (`typeof window !== 'undefined'`), le SDK émet un `console.warn` au démarrage :
> ```
> [Tenxyte] ⚠️  `accessSecret` detected in a browser environment. ...
> ```

---

## Fonctionnalités du SDK en un coup d'œil

- **Authentification** — Email/mot de passe, téléphone, magic link, social OAuth2 (avec PKCE), inscription
- **Cookie mode** — Transport du refresh token via HttpOnly cookie (`cookieMode: true`)
- **Sécurité** — 2FA/TOTP, OTP, WebAuthn/Passkeys (FIDO2), gestion des mots de passe
- **RBAC** — Vérifications synchrones des rôles/permissions JWT, opérations CRUD
- **B2B** — CRUD organisations, membres, invitations, context switching
- **Sécurité Agent IA (AIRS)** — Tokens agents, Human-in-the-Loop, rapports d'utilisation
- **Applications** — Gestion des clients API, régénération de credentials
- **Admin** — Logs d'audit, tentatives de login, tokens blacklistés/refresh
- **GDPR** — Flux de suppression de compte, export de données
- **Dashboard** — Statistiques globales, auth, sécurité, GDPR, par organisation
- **Auto-refresh** — Intercepteur silencieux 401 → refresh → retry
- **Retry** — Backoff exponentiel configurable pour les erreurs 429/5xx
- **Événements** — `session:expired`, `token:refreshed`, `token:stored`, `agent:awaiting_approval`
- **TypeScript** — Types complets générés depuis OpenAPI

---

## Référence de configuration

```typescript
const tx = new TenxyteClient({
    // Requis
    baseUrl: 'https://api.my-service.com',

    // Authentification applicative (recommandé)
    accessKey: 'pkg_abc123',                      // ✅ frontend et backend
    accessSecret: process.env.TENXYTE_SECRET,      // ⚠️  backend uniquement

    // Optionnel — headers supplémentaires pour chaque requête
    // (rétrocompatible, accessKey/accessSecret sont préférés)
    headers: {},

    // Optionnel — stockage des tokens (défaut : MemoryStorage)
    storage: new LocalStorageAdapter(),

    // Optionnel — refresh silencieux des 401 (défaut : true)
    autoRefresh: true,

    // Optionnel — injection automatique du fingerprint appareil (défaut : true)
    autoDeviceInfo: true,

    // Optionnel — timeout des requêtes en ms
    timeoutMs: 10_000,

    // Optionnel — configuration retry pour les erreurs 429/5xx
    retryConfig: { maxRetries: 3, baseDelayMs: 500 },

    // Optionnel — callback lorsque la session est irrécupérable
    onSessionExpired: () => router.push('/login'),

    // Optionnel — logger externe
    logger: console,
    logLevel: 'debug',

    // Optionnel — override du device info auto-détecté
    deviceInfoOverride: { app_name: 'MyApp', app_version: '2.0.0' },

    // Optionnel — transport du refresh token via cookie HttpOnly (défaut : false)
    // Activer lorsque le backend a TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True
    cookieMode: false,
});
```

| Option | Type | Défaut | Description |
|---|---|---|---|
| `baseUrl` | `string` | — | URL de base de l'API Tenxyte |
| `accessKey` | `string` | `undefined` | Clé publique de l'application — injecte `X-Access-Key` |
| `accessSecret` | `string` | `undefined` | Secret privé (backend uniquement) — injecte `X-Access-Secret` |
| `headers` | `Record<string, string>` | `{}` | Headers supplémentaires fusionnés dans chaque requête |
| `storage` | `TenxyteStorage` | `MemoryStorage` | Backend de persistance des tokens |
| `autoRefresh` | `boolean` | `true` | Refresh silencieux 401 → refresh → retry |
| `autoDeviceInfo` | `boolean` | `true` | Injection de `device_info` dans les requêtes auth |
| `timeoutMs` | `number` | `undefined` | Timeout global des requêtes |
| `retryConfig` | `RetryConfig` | `undefined` | Backoff exponentiel pour les erreurs 429/5xx |
| `onSessionExpired` | `() => void` | `undefined` | Callback lorsque la session est irrécupérable |
| `logger` | `TenxyteLogger` | no-op silencieux | Implémentation du logger |
| `logLevel` | `LogLevel` | `'silent'` | `'silent'` \| `'error'` \| `'warn'` \| `'debug'` |
| `deviceInfoOverride` | `CustomDeviceInfo` | `undefined` | Override du device info auto-détecté |
| `cookieMode` | `boolean` | `false` | Transport du refresh token via cookie HttpOnly |

> **Migration :** `headers: { 'X-Access-Key': '...' }` reste fonctionnel. `accessKey`/`accessSecret` sont simplement fusionnés dans `headers` par `resolveConfig()` avant de passer au client HTTP.

---

## Gestion des erreurs

Toutes les méthodes du SDK lèvent un `TenxyteError` en cas d'échec :

```typescript
import type { TenxyteError } from '@tenxyte/core';

try {
    await tx.auth.loginWithEmail({ email, password, device_info: '' });
} catch (err) {
    const e = err as TenxyteError;
    console.error(e.code);        // ex : 'INVALID_CREDENTIALS', 'ACCOUNT_LOCKED'
    console.error(e.error);       // Message lisible par un humain
    console.error(e.details);     // Erreurs par champ ou message libre
    console.error(e.retry_after); // Secondes à attendre (pour les erreurs 429/423)
}
```

Codes d'erreur courants : `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`, `2FA_REQUIRED`, `RATE_LIMITED`, `MISSING_REFRESH_TOKEN`, `INVALID_REDIRECT_URI`, `APP_AUTH_REQUIRED`, `APP_AUTH_ORIGIN_REQUIRED`, `APP_AUTH_ORIGIN_DENIED`.

| Code | Signification |
|------|---------------|
| `APP_AUTH_REQUIRED` | Aucun header d'auth applicative fourni (`X-Access-Key` manquant) |
| `APP_AUTH_ORIGIN_REQUIRED` | Clé seule fournie mais header `Origin` manquant |
| `APP_AUTH_ORIGIN_DENIED` | `Origin` non présente dans `allowed_origins` de l'application |

Voir la [Référence des Schémas](../../schemas.md) pour la liste complète des codes d'erreur.

---

## Prochaines étapes

- [**Guide Core**](core.md) — Référence complète de l'API `@tenxyte/core` avec les 10 modules
- [**Guide React**](react.md) — Hooks React, `TenxyteProvider`, et exemples SPA complets
- [**Guide Vue**](vue.md) — Composables Vue 3, configuration du plugin, et exemples SPA complets
- [**Endpoints API**](../../endpoints.md) — Référence des endpoints backend
- [**Guide de Sécurité**](../../security.md) — PKCE, cookie mode, rotation JWT, verrouillage
- [**Référence des Paramètres**](../../settings.md) — Toutes les options de configuration backend
