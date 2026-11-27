# UI Blocks (`@tenxyte/registry` — shadcn)

> Ready-to-use authentication, 2FA, passkey, organization, and AIRS approval UI blocks for **React** and **Vue 3** — distributed as source code you own and restyle via the `shadcn` CLI.

---

## Architecture

Tenxyte splits UI integration into three strictly layered pieces (zero duplicated business logic):

1. **Flows (`@tenxyte/core >= 0.10.0`)** — 12 framework-agnostic state machines (`SignInFlow`, `SignUpFlow`, `LoginOtpFlow`, `TwoFactorSetupFlow`, `PasskeyAuthFlow`, `HitlApprovalFlow`, …) that own all network calls, wire-contract error parsing, and state transitions.
2. **Framework bindings (`@tenxyte/react >= 0.6.0` / `@tenxyte/vue >= 0.6.0`)** — reactive hooks (`useSignInFlow`, `useSignUpFlow`, …) and Vue 3 composables with static API parity and automatic focus restoration after busy states.
3. **UI Registry (`@tenxyte/registry`)** — copy-paste shadcn blocks built on **Base UI** (React) and **Reka UI** (Vue) with isolated `--tx-*` Tailwind v4 CSS tokens. Blocks never perform direct HTTP calls; they only render a Flow's state.

---

## Installation

**Prerequisites:** a Vite (or compatible) project with Tailwind CSS v4 (`@tailwindcss/vite`) and an `@/` → `src/` path alias configured in both `tsconfig` and your bundler (required by `shadcn init` / `shadcn-vue init`).

### 1. Register the `@tenxyte` namespace in `components.json`

```json
{
  "registries": {
    "@tenxyte": "https://<your-registry-host>/r/{name}.json"
  }
}
```

### 2. Install blocks via the shadcn CLI

Dependent blocks (such as `otp-input` for `sign-in`), theme tokens, and the required `@tenxyte/core` + `@tenxyte/react` (or `@tenxyte/vue`) packages are installed automatically:

```bash
# React (Base UI)
npx shadcn@latest add @tenxyte/sign-in

# Vue 3 (Reka UI)
npx shadcn-vue@latest add @tenxyte/sign-in-vue
```

### 3. Import the theme tokens once

In your main CSS entrypoint, right after `@import "tailwindcss";`:

```css
@import "tailwindcss";
@import "./styles/tenxyte-theme.css";
```

---

## Theming & Light Mode

The Tenxyte theme tokens are **dark by default** and prefixed with `--tx-*` (`--tx-primary`, `--tx-bg`, `--tx-fg`, `--tx-radius`, …) so they never collide with shadcn's own `--primary` / `--radius` variables or host styles.

* **Light pages:** set `data-theme="light"` on `<html>`.
* **Customizing:** override any `--tx-*` custom property in your own stylesheet:

```css
:root {
  --tx-primary: oklch(0.65 0.2 30);
  --tx-radius: 0;
}
```

---

## Block Catalogue (12 Flows + 1 Shared Primitive)

Each React block has a Vue 3 counterpart with the `-vue` suffix:

| React Block | Vue Block | Underlying `@tenxyte/core` Flow |
|---|---|---|
| `otp-input` | `otp-input-vue` | Shared single-field OTP input primitive |
| `sign-in` | `sign-in-vue` | `SignInFlow` — email/password sign-in + 2FA challenge |
| `sign-up` | `sign-up-vue` | `SignUpFlow` — registration + live password strength |
| `login-otp` | `login-otp-vue` | `LoginOtpFlow` — passwordless SMS OTP login |
| `magic-link` | `magic-link-vue` | `MagicLinkFlow` — passwordless email magic link |
| `otp-verify` | `otp-verify-vue` | `OtpVerifyFlow` — email/phone verification |
| `password-reset` | `password-reset-vue` | `PasswordResetFlow` — forgot / reset password |
| `forced-password-change` | `forced-password-change-vue` | `ForcedPasswordChangeFlow` — `must_change_password` gate |
| `two-factor-setup` | `two-factor-setup-vue` | `TwoFactorSetupFlow` — TOTP QR setup & backup codes |
| `passkey-button` | `passkey-button-vue` | `PasskeyRegisterFlow` + `PasskeyAuthFlow` (WebAuthn) |
| `org-switcher` | `org-switcher-vue` | `OrgSwitcherFlow` — B2B organization context switcher |
| `hitl-queue` | `hitl-queue-vue` | `HitlApprovalFlow` — AIRS Human-in-the-Loop approval queue |

---

## Self-Hosting the Registry

The source lives in `packages/registry/` of the [`tenxyte-js`](https://github.com/tenxyte/tenxyte-js) monorepo:

```bash
pnpm --filter @tenxyte/registry build:registry   # generates r/*.json from registry.json
```

Serve the generated `packages/registry/r/*.json` directory on any static host (Vercel, Cloudflare Pages, GitHub Pages, S3/CloudFront) and point your `components.json` `@tenxyte` URL to it.
