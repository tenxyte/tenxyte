# Blocs UI (`@tenxyte/registry` — shadcn)

> Blocs prêts à l'emploi pour l'authentification, la 2FA, les passkeys, les organisations et la file d'approbation AIRS pour **React** et **Vue 3** — distribués comme du code source que vous possédez et restylez via la CLI `shadcn`.

---

## Architecture

L'intégration UI de Tenxyte repose sur trois couches strictement séparées (zéro logique métier dupliquée) :

1. **Flows (`@tenxyte/core >= 0.10.0`)** — 12 machines à états agnostiques (`SignInFlow`, `SignUpFlow`, `LoginOtpFlow`, `TwoFactorSetupFlow`, `PasskeyAuthFlow`, `HitlApprovalFlow`, …) portant les appels réseau, le parsing d'erreurs du contrat et les transitions.
2. **Bindings framework (`@tenxyte/react >= 0.6.0` / `@tenxyte/vue >= 0.6.0`)** — hooks React (`useSignInFlow`, `useSignUpFlow`, …) et composables Vue 3 à parité d'API vérifiée statiquement, avec restauration automatique du focus après les états occupés.
3. **Registry UI (`@tenxyte/registry`)** — blocs shadcn copier-coller bâtis sur **Base UI** (React) et **Reka UI** (Vue) avec des tokens CSS Tailwind v4 isolés (`--tx-*`). Les blocs n'effectuent jamais d'appel réseau direct ; ils rendent uniquement l'état d'un Flow.

---

## Installation

**Prérequis :** un projet Vite (ou équivalent) avec Tailwind CSS v4 (`@tailwindcss/vite`) et un alias `@/` → `src/` déclaré dans `tsconfig` et dans la config du bundler (exigé par `shadcn init` / `shadcn-vue init`).

### 1. Déclarer le namespace `@tenxyte` dans `components.json`

```json
{
  "registries": {
    "@tenxyte": "https://<votre-domaine-registry>/r/{name}.json"
  }
}
```

### 2. Installer un bloc via la CLI shadcn

Les blocs dépendants (ex. `otp-input` pour `sign-in`), les tokens de thème et les paquets `@tenxyte/core` + `@tenxyte/react` (ou `@tenxyte/vue`) sont installés automatiquement :

```bash
# React (Base UI)
npx shadcn@latest add @tenxyte/sign-in

# Vue 3 (Reka UI)
npx shadcn-vue@latest add @tenxyte/sign-in-vue
```

### 3. Importer les tokens de thème une seule fois

Dans votre fichier CSS d'entrée, juste après `@import "tailwindcss";` :

```css
@import "tailwindcss";
@import "./styles/tenxyte-theme.css";
```

---

## Thème et mode clair

Les tokens Tenxyte sont **sombres par défaut** et préfixés `--tx-*` (`--tx-primary`, `--tx-bg`, `--tx-fg`, `--tx-radius`, …) afin de ne jamais entrer en collision avec les variables shadcn (`--primary`, `--radius`) ni avec les styles du projet hôte.

* **Page claire :** ajoutez `data-theme="light"` sur `<html>`.
* **Personnalisation :** surchargez librement les variables `--tx-*` dans votre CSS :

```css
:root {
  --tx-primary: oklch(0.65 0.2 30);
  --tx-radius: 0;
}
```

---

## Catalogue des blocs (12 parcours + 1 primitive partagée)

Chaque bloc React dispose de son équivalent Vue 3 avec le suffixe `-vue` :

| Bloc React | Bloc Vue | Flow `@tenxyte/core` sous-jacent |
|---|---|---|
| `otp-input` | `otp-input-vue` | Primitive partagée de saisie OTP |
| `sign-in` | `sign-in-vue` | `SignInFlow` — connexion email/mot de passe + 2FA |
| `sign-up` | `sign-up-vue` | `SignUpFlow` — inscription + force du mot de passe |
| `login-otp` | `login-otp-vue` | `LoginOtpFlow` — connexion passwordless par SMS |
| `magic-link` | `magic-link-vue` | `MagicLinkFlow` — connexion passwordless par e-mail |
| `otp-verify` | `otp-verify-vue` | `OtpVerifyFlow` — vérification email/téléphone |
| `password-reset` | `password-reset-vue` | `PasswordResetFlow` — réinitialisation de mot de passe |
| `forced-password-change` | `forced-password-change-vue` | `ForcedPasswordChangeFlow` — barrière `must_change_password` |
| `two-factor-setup` | `two-factor-setup-vue` | `TwoFactorSetupFlow` — configuration TOTP & codes de secours |
| `passkey-button` | `passkey-button-vue` | `PasskeyRegisterFlow` + `PasskeyAuthFlow` (WebAuthn) |
| `org-switcher` | `org-switcher-vue` | `OrgSwitcherFlow` — sélecteur d'organisation B2B |
| `hitl-queue` | `hitl-queue-vue` | `HitlApprovalFlow` — file d'approbation AIRS (HITL) |

---

## Auto-héberger le registry

Les sources se trouvent dans `packages/registry/` du monorepo [`tenxyte-js`](https://github.com/tenxyte/tenxyte-js) :

```bash
pnpm --filter @tenxyte/registry build:registry   # génère r/*.json depuis registry.json
```

Servez ensuite le dossier `packages/registry/r/*.json` sur n'importe quel hébergeur statique (Vercel, Cloudflare Pages, GitHub Pages, S3/CloudFront) et pointez l'URL `@tenxyte` de `components.json` dessus.
