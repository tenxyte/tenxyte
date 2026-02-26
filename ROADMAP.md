# Roadmap Tenxyte — Plan d'Action Complet

> **Dernière mise à jour :** 20 Février 2026  
> **Objectif :** Amener le moteur Tenxyte à un état complet, compétitif, et prêt pour un lancement SaaS.  
> **Principe :** Le code Open Source est identique au moteur Cloud. Aucune fonctionnalité du moteur n'est bridée.

---

## État Actuel du Moteur

| Composant | État |
|---|---|
| Auth Email/Password/Phone | ✅ Prod-ready |
| Google OAuth | ✅ Prod-ready |
| JWT + Rotation + Blacklist | ✅ Prod-ready |
| 2FA/TOTP + Backup Codes | ✅ Prod-ready |
| RBAC Global (8 décorateurs) | ✅ Prod-ready |
| Hiérarchie de Rôles | ✅ Prod-ready |
| Organizations B2B + RBAC Org-Scoped | ✅ Prod-ready |
| RGPD (Suppression/Export/Annulation) | ✅ Prod-ready |
| Rate Limiting (8 classes + custom) | ✅ Prod-ready |
| Device Fingerprinting | ✅ v1 |
| Middlewares (CORS, Security Headers, App Auth) | ✅ Prod-ready |
| M2M / API Keys (Application model) | ✅ Prod-ready |
| Audit Logs + Login Attempts | ✅ Prod-ready |
| 150+ settings configurables | ✅ Prod-ready |
| Tests (coverage 79.73%, 700 tests) | ✅ Solide |
| Documentation | ✅ 6 guides (quickstart, settings, endpoints, rbac, security, organizations) |
| Passwordless / Magic Links | ❌ Absent |
| Social Login multi-provider | ❌ Partiel (Google seulement) |
| Passkeys / WebAuthn | ❌ Absent |
| SDK JavaScript | ❌ Absent |
| Webhooks | ❌ Absent |
| Dashboard Admin SaaS | ❌ Absent |
| SSO SAML/OIDC | ❌ Absent |

---

## Phase 0 — Finition du Moteur Existant *(Priorité immédiate)*

> **Objectif :** Rendre le moteur actuel irréprochable avant d'ajouter de nouvelles fonctionnalités.  
> **Durée estimée :** 2–3 semaines

### 0.1 — Couverture de tests ✅ COMPLÉTÉ

| Fichier | Coverage avant | Coverage après | Statut |
|---|---|---|---|
| `services/auth_service.py` | 51% | 74% | ✅ |
| `views/auth_views.py` | 37% | 98% | ✅ |
| `views/otp_views.py` | 43% | 100% | ✅ |
| `views/twofa_views.py` | 46% | 100% | ✅ |
| `views/user_views.py` | 41% | 97% | ✅ |
| `views/dashboard_views.py` | 0% | 100% | ✅ |
| `services/stats_service.py` | 0% | 86% | ✅ |
| **TOTAL** | ~51% | **79.73%** | ✅ |

**700 tests passent. Fichiers créés :**
- `tests/unit/test_auth_views.py` ✅
- `tests/unit/test_otp_views.py` ✅
- `tests/unit/test_twofa_views.py` ✅
- `tests/unit/test_user_views.py` ✅
- `tests/unit/test_auth_service_extended.py` ✅
- `tests/unit/test_dashboard_views.py` ✅

### 0.2 — Correction des bugs connus ✅ COMPLÉTÉ

- [x] `views/auth_views.py` — Google OAuth errors handled (invalid token → 401, disabled account → 401)
- [x] `services/auth_service.py` — `logout_all_devices` révoque tous les tokens + blacklist access token
- [x] `models/` — MySQL migrations: max_length=191 pour tous les champs indexés
- [x] `conf.py` — Tous les settings ont des valeurs par défaut sensées
- [x] `models/auth.py` — UserManager hérite de BaseUserManager (get_by_natural_key)

### 0.3 — Documentation du package ✅ COMPLÉTÉ

- [x] `README.md` — Installation, quickstart, badges coverage/tests, liens docs
- [x] `docs/quickstart.md` — Guide d'intégration en 5 minutes
- [x] `docs/settings.md` — Référence complète des 150+ settings
- [x] `docs/endpoints.md` — Référence API (tous les endpoints avec exemples curl)
- [x] `docs/organizations.md` — Guide Organizations B2B
- [x] `docs/rbac.md` — Guide RBAC + 8 décorateurs
- [x] `docs/security.md` — Guide sécurité (rate limiting, 2FA, device fingerprinting, JWT hardening)
- [x] `CHANGELOG.md` — Historique des versions

### 0.4 — Packaging PyPI ✅ COMPLÉTÉ

- [x] `pyproject.toml` — version, dépendances, classifiers, keywords mis à jour
- [x] Migrations incluses dans le package (`recursive-include src/tenxyte/migrations`)
- [x] Templates email inclus dans `MANIFEST.in`
- [x] Docs incluses dans `MANIFEST.in` (`recursive-include docs *.md`)
- [x] `.github/workflows/ci.yml` — lint + tests matrix (Python 3.10/3.11/3.12 × Django 5.0/5.1)
- [x] `.github/workflows/publish.yml` — publish to PyPI on git tag `v*`
- [x] Badge coverage + tests dans le README

---

## Phase 1 — Parité Compétitive *(Fonctionnalités manquantes critiques)*

> **Objectif :** Combler les gaps bloquants pour être compétitif face à Auth0/Clerk.  
> **Durée estimée :** 6–8 semaines

### 1.1 — Passwordless / Magic Links

**Pourquoi :** Tendance forte en 2026. Clerk, Auth0, Stytch, Supabase l'ont tous.

**Implémentation dans le moteur :**
- [ ] Nouveau model `MagicLinkToken` (token, user, expires_at, used_at, ip_address)
- [ ] `MagicLinkService` — génération, validation, expiration
- [ ] Endpoint `POST /auth/magic-link/request/` — envoie le lien par email
- [ ] Endpoint `GET /auth/magic-link/verify/?token=xxx` — valide et retourne JWT
- [ ] Email template `emails/magic_link.html`
- [ ] Setting `TENXYTE_MAGIC_LINK_EXPIRY_MINUTES` (défaut: 15)
- [ ] Setting `TENXYTE_MAGIC_LINK_ENABLED` (défaut: False)
- [ ] Tests unitaires complets

### 1.2 — Social Login Multi-Provider

**Pourquoi :** GitHub, Facebook, Apple, Microsoft = couverture minimale attendue.

**Implémentation :**
- [ ] Refactoriser `GoogleAuthService` en `AbstractOAuthProvider` (base commune)
- [ ] `GitHubAuthService` — OAuth2 GitHub (code → access_token → user info)
- [ ] `MicrosoftAuthService` — OAuth2 Microsoft/Azure AD
- [ ] `FacebookAuthService` — OAuth2 Facebook
- [ ] `AppleAuthService` — Sign in with Apple (JWT-based, plus complexe)
- [ ] Endpoint générique `POST /auth/social/<provider>/` (remplace `POST /auth/google/`)
- [ ] Model `SocialConnection` — lie un user à plusieurs providers
- [ ] Settings `TENXYTE_SOCIAL_PROVIDERS` — liste des providers activés
- [ ] Tests pour chaque provider (mocks)

### 1.3 — Passkeys / WebAuthn (FIDO2)

**Pourquoi :** Standard de l'industrie en 2026. Google, Apple, Microsoft poussent les Passkeys.

**Implémentation :**
- [ ] Dépendance : `py_webauthn` (library Python FIDO2)
- [ ] Model `WebAuthnCredential` (credential_id, public_key, user, device_name, created_at, last_used_at)
- [ ] `WebAuthnService` — registration challenge, registration verification, authentication challenge, authentication verification
- [ ] Endpoint `POST /auth/webauthn/register/begin/` — génère le challenge d'enregistrement
- [ ] Endpoint `POST /auth/webauthn/register/complete/` — valide et sauvegarde la credential
- [ ] Endpoint `POST /auth/webauthn/authenticate/begin/` — génère le challenge d'auth
- [ ] Endpoint `POST /auth/webauthn/authenticate/complete/` — valide et retourne JWT
- [ ] Endpoint `GET /auth/webauthn/credentials/` — liste les passkeys de l'utilisateur
- [ ] Endpoint `DELETE /auth/webauthn/credentials/<id>/` — supprime une passkey
- [ ] Setting `TENXYTE_WEBAUTHN_ENABLED` (défaut: False)
- [ ] Setting `TENXYTE_WEBAUTHN_RP_ID` — Relying Party ID (ex: `yourapp.com`)
- [ ] Setting `TENXYTE_WEBAUTHN_RP_NAME` — Nom affiché dans le prompt Passkey
- [ ] Tests unitaires (mocks WebAuthn)

### 1.4 — SDK JavaScript

**Pourquoi :** Impossible de vendre un SaaS sans `npm install @tenxyte/js`.

**Structure du SDK (repo séparé `tenxyte-js`) :**
```
packages/
  @tenxyte/core/        — Client HTTP vanilla (fetch), gestion tokens, refresh auto
  @tenxyte/react/       — Hooks React : useAuth(), useUser(), useOrganization()
  @tenxyte/vue/         — Composables Vue 3 : useAuth(), useUser()
```

**Fonctionnalités `@tenxyte/core` :**
- [ ] `TenxyteClient` — init avec `` + `appKey`
- [ ] `auth.loginWithEmail(email, password)` → tokens
- [ ] `auth.loginWithPhone(phone, password)` → tokens
- [ ] `auth.loginWithGoogle(idToken)` → tokens
- [ ] `auth.loginWithMagicLink(token)` → tokens
- [ ] `auth.logout()` — révoque + nettoie storage
- [ ] `auth.refreshToken()` — refresh automatique
- [ ] `auth.getUser()` — profil courant
- [ ] `auth.on('tokenRefreshed', cb)` — événements
- [ ] Intercepteur automatique pour ajouter `Authorization: Bearer` aux requêtes
- [ ] Gestion du storage (localStorage / sessionStorage / memory)

**Fonctionnalités `@tenxyte/react` :**
- [ ] `<TenxyteProvider>` — Context provider
- [ ] `useAuth()` — `{ user, isLoading, isAuthenticated, login, logout }`
- [ ] `useUser()` — `{ user, updateUser }`
- [ ] `useOrganization()` — `{ organization, members, roles }`
- [ ] `<ProtectedRoute>` — HOC de protection de route
- [ ] `usePermission(perm)` — vérifie une permission

### 1.5 — Breach Password Check

**Pourquoi :** Sécurité de base. Auth0 et Keycloak l'ont nativement. Implémentation simple.

**Implémentation :**
- [ ] `BreachCheckService` — appel HaveIBeenPwned API (k-anonymity, SHA1 prefix)
- [ ] Intégration dans `RegisterView` et `ChangePasswordView`
- [ ] Setting `TENXYTE_BREACH_CHECK_ENABLED` (défaut: False)
- [ ] Setting `TENXYTE_BREACH_CHECK_REJECT` — rejeter ou seulement avertir
- [ ] Tests (mock de l'API HIBP)

---

## Phase 2 — Construction du Cloud SaaS

> **Objectif :** Créer la couche SaaS au-dessus du moteur.  
> **Durée estimée :** 3–4 mois  
> **Stack :** Django (backend) + React/Next.js (dashboard) + PostgreSQL + Redis

### 2.1 — Tenant Management Layer

**Architecture :** `TenxyteAccount → Project (tenant) → Application (plateforme)`

- [ ] Model `TenxyteAccount` — le compte développeur (email, plan, billing)
- [ ] Model `Project` — le vrai tenant (slug, name, account, settings_override)
- [ ] Isolation par `Project` — chaque Project a ses propres Users/Roles/Perms/Orgs
- [ ] `ProjectMiddleware` — résout le tenant depuis l'API Key (`X-Access-Key`)
- [ ] Admin API — CRUD Projects, Applications, gestion des limites de plan
- [ ] Système de quotas — MAU, nb projets, nb apps, nb orgs, nb webhooks

### 2.2 — Système de Webhooks

**Pourquoi :** Essentiel pour l'intégration SaaS. Tous les concurrents l'ont.

**Événements à supporter :**
```
user.created          user.updated          user.deleted
user.logged_in        user.logged_out       user.locked
user.password_changed user.2fa_enabled      user.2fa_disabled
org.created           org.member_invited    org.member_joined
org.member_removed    org.role_changed
session.created       session.revoked
```

**Implémentation :**
- [ ] Model `WebhookEndpoint` (url, events, secret, active, project)
- [ ] Model `WebhookDelivery` (endpoint, event, payload, status_code, attempts, next_retry)
- [ ] `WebhookService` — dispatch, signature HMAC-SHA256, retry exponentiel (3 tentatives)
- [ ] Celery task `deliver_webhook` — envoi asynchrone
- [ ] Endpoint `POST /admin/webhooks/` — créer un endpoint
- [ ] Endpoint `GET /admin/webhooks/<id>/deliveries/` — historique des livraisons
- [ ] Endpoint `POST /admin/webhooks/<id>/test/` — tester un endpoint
- [ ] Setting `TENXYTE_WEBHOOKS_ENABLED`

### 2.3 — Dashboard Admin SaaS (React/Next.js)

**Repo séparé `tenxyte-dashboard`**

**Pages à implémenter :**
- [ ] **Auth** — Login/Register pour le compte développeur
- [ ] **Overview** — Métriques clés (MAU, logins/jour, erreurs)
- [ ] **Users** — Liste, recherche, détail, ban, unlock, impersonate
- [ ] **Roles & Permissions** — CRUD visuel du RBAC
- [ ] **Organizations** — Arbre hiérarchique, membres, rôles org-scoped
- [ ] **Audit Logs** — Timeline filtrée par user/action/date
- [ ] **Sessions** — Sessions actives, révocation par device
- [ ] **Applications** — CRUD API Keys, régénération
- [ ] **Webhooks** — CRUD endpoints, historique des livraisons
- [ ] **Settings** — Configuration du projet (JWT lifetime, password policy, etc.)
- [ ] **Billing** — Plan actuel, usage, upgrade

### 2.4 — Hosted Login Page

**Pourquoi :** Valeur ajoutée clé du SaaS. Permet au dev de ne pas coder de page de login.

- [ ] Page de login hébergée sur `auth.tenxyte.io/<project-slug>/login`
- [ ] Personnalisable via CSS Variables (logo, couleurs, fond)
- [ ] Support des providers activés (Email, Google, GitHub, Magic Link, Passkey)
- [ ] Redirect vers `redirect_uri` après login avec code d'autorisation
- [ ] Setting `TENXYTE_HOSTED_LOGIN_ENABLED`

### 2.5 — Python Auth Hooks

**Pourquoi :** Unique sur le marché. Auth0 a des Actions JS, Tenxyte aura des Hooks Python.

```python
# tenxyte_hooks.py
@tenxyte.on("pre_login")
def enforce_geo_mfa(user, request, context):
    if context.country != user.usual_country:
        return tenxyte.require_mfa(method="totp")
    return tenxyte.allow()

@tenxyte.on("post_register")
def auto_assign_role(user, request, context):
    if user.email.endswith("@company.com"):
        return tenxyte.assign_role(user, "employee")
```

**Implémentation :**
- [ ] `HookRegistry` — registre des hooks par événement
- [ ] `@tenxyte.on(event)` — décorateur d'enregistrement
- [ ] `HookContext` — objet contexte passé aux hooks (request, user, result)
- [ ] `HookResult` — `allow()`, `deny(reason)`, `require_mfa()`, `assign_role()`
- [ ] Intégration dans `AuthService` aux points clés (pre/post login, register, logout)
- [ ] Setting `TENXYTE_HOOKS_MODULE` — chemin vers le fichier de hooks
- [ ] Documentation + exemples

### 2.6 — Web Components Universels

**Pourquoi :** Pas de lock-in framework (contrairement à Clerk qui est React-only).

```html
<tenxyte-login theme="dark" providers="google,github"></tenxyte-login>
<tenxyte-user-button></tenxyte-user-button>
<tenxyte-org-switcher></tenxyte-org-switcher>
```

**Implémentation (repo `tenxyte-elements`) :**
- [ ] `<tenxyte-login>` — formulaire de login complet
- [ ] `<tenxyte-register>` — formulaire d'inscription
- [ ] `<tenxyte-user-button>` — avatar + menu utilisateur
- [ ] `<tenxyte-org-switcher>` — sélecteur d'organisation
- [ ] Thème CSS Variables (dark/light + custom)
- [ ] Build en Web Components natifs (Lit ou Stencil)
- [ ] Compatible React, Vue, Svelte, Angular, HTML pur

---

## Phase 3 — Enterprise & Différenciation

> **Objectif :** Signer des gros contrats, se différencier radicalement.  
> **Durée estimée :** 4–6 mois

### 3.1 — SSO Enterprise (SAML 2.0 / OIDC)

**Pourquoi :** Indispensable pour vendre à des entreprises >500 employés.

**Implémentation :**
- [ ] Dépendance : `python3-saml` ou `pysaml2`
- [ ] Model `SSOConnection` (organization, provider_type, metadata_url, entity_id, ...)
- [ ] `SAMLService` — SP-initiated SSO, IdP-initiated SSO, SLO (Single Logout)
- [ ] `OIDCService` — Authorization Code Flow, token validation, userinfo
- [ ] Endpoint `GET /auth/sso/<org-slug>/login/` — initie le flow SSO
- [ ] Endpoint `POST /auth/sso/<org-slug>/callback/` — callback SAML/OIDC
- [ ] Admin endpoint — configuration de la connexion SSO par org
- [ ] Support : Okta, Azure AD, Google Workspace, Ping Identity
- [ ] Setting `TENXYTE_SSO_ENABLED`
- [ ] Tests (mocks SAML/OIDC)

### 3.2 — SCIM / Directory Sync

**Pourquoi :** Auto-provisioning des membres par organisation via Active Directory.

**Implémentation :**
- [ ] Endpoints SCIM 2.0 : `GET/POST /scim/v2/Users`, `GET/PUT/DELETE /scim/v2/Users/<id>`
- [ ] Endpoints SCIM 2.0 : `GET/POST /scim/v2/Groups`, `GET/PUT/DELETE /scim/v2/Groups/<id>`
- [ ] Mapping SCIM Group → Organization + Membership
- [ ] Token d'authentification SCIM par organization
- [ ] Sync bidirectionnelle (provisioning + deprovisioning)
- [ ] Setting `TENXYTE_SCIM_ENABLED`

### 3.3 — Active Defense (Sécurité Offensive)

**Pourquoi :** Aucun concurrent ne propose ce niveau de défense dans sa version gratuite.

| Fonctionnalité | Description |
|---|---|
| **Honeypot Accounts** | Faux comptes admin — si accédés, bannissent l'IP et alertent |
| **Credential Stuffing Detection** | Patterns de login en masse (même IP, user-agents rotatifs, timing) |
| **IP Reputation Network** | IPs malveillantes partagées anonymement entre instances |
| **Behavioral Biometrics** | Vitesse de frappe/navigation pour détecter bots sans CAPTCHA |

**Implémentation :**
- [ ] Model `HoneypotAccount` — comptes pièges configurables
- [ ] `CredentialStuffingDetector` — analyse des patterns de login (Redis sliding window)
- [ ] `IPReputationService` — lookup local + API externe optionnelle
- [ ] `BehavioralAnalyzer` — score de confiance basé sur les événements JS
- [ ] Setting `TENXYTE_ACTIVE_DEFENSE_ENABLED`
- [ ] Setting `TENXYTE_HONEYPOT_ACCOUNTS` — liste des emails pièges

### 3.4 — Shadow Audit (RBAC Intelligence)

**Pourquoi :** Répond aux exigences SOC2. Aucun concurrent ne propose ça.

- [ ] Tracking passif des permissions effectivement invoquées (via les décorateurs)
- [ ] Model `PermissionUsage` (user, permission, last_used_at, use_count)
- [ ] Rapport `GET /admin/rbac/unused-permissions/` — permissions jamais utilisées
- [ ] Rapport `GET /admin/rbac/users/<id>/permission-usage/` — usage par user
- [ ] Recommandations automatiques de nettoyage (Least Privilege)
- [ ] Setting `TENXYTE_SHADOW_AUDIT_ENABLED`

### 3.5 — Audit Log Streaming (SIEM)

**Pourquoi :** Requis pour les clients Enterprise avec Splunk/Datadog.

- [ ] Connecteur Splunk (HTTP Event Collector)
- [ ] Connecteur Datadog (Logs API)
- [ ] Connecteur générique webhook (JSON)
- [ ] Export CSV/JSON des audit logs
- [ ] Setting `TENXYTE_AUDIT_STREAM_BACKEND` — `splunk`, `datadog`, `webhook`

### 3.6 — Zero-Knowledge Auth

**Pourquoi :** Argument décisif pour Finance, Santé, Gouvernement. Aucun concurrent.

- [ ] Chiffrement des métadonnées utilisateur avec clé client-side (AES-256-GCM)
- [ ] Tenxyte stocke des blobs chiffrés, pas de données en clair
- [ ] SDK JS gère le chiffrement/déchiffrement côté client
- [ ] Setting `TENXYTE_ZERO_KNOWLEDGE_ENABLED`
- [ ] Documentation + guide de migration

---

## Phase 4 — Lancement & Croissance

> **Objectif :** Acquérir les premiers utilisateurs et générer du revenu.

### 4.1 — Site Web Marketing

- [ ] Landing page `tenxyte.io` — Hero, features, pricing, comparaison concurrents
- [ ] Page documentation `docs.tenxyte.io` (Docusaurus ou Mintlify)
- [ ] Blog technique — articles SEO sur auth, sécurité, Django
- [ ] Page pricing — Free / Premium / Enterprise

### 4.2 — Communauté & Adoption

- [ ] GitHub — README irréprochable, contributing guide, issue templates
- [ ] Discord — serveur communautaire
- [ ] Product Hunt — lancement coordonné
- [ ] Hacker News — Show HN post
- [ ] Articles sur Dev.to, Medium, Hashnode

### 4.3 — Intégrations Ecosystem

- [ ] Template Django starter avec Tenxyte pré-configuré
- [ ] Template FastAPI (via ASGI adapter)
- [ ] Intégration Cookiecutter Django
- [ ] Plugin pytest `pytest-tenxyte` — fixtures prêtes à l'emploi

---

## Récapitulatif des Priorités

```
MAINTENANT          COURT TERME (1-3 mois)    MOYEN TERME (3-6 mois)    LONG TERME (6-12 mois)
─────────────────   ──────────────────────    ──────────────────────    ──────────────────────
Phase 0             Phase 1                   Phase 2                   Phase 3 + 4
Tests 90%+          Magic Links               Tenant Layer              SSO SAML/OIDC
Bug fixes           Social Login Multi        Webhooks                  SCIM
Documentation       Passkeys/WebAuthn         Dashboard SaaS            Active Defense
PyPI packaging      SDK JavaScript            Hosted Login              Shadow Audit
                    Breach Check              Python Hooks              Zero-Knowledge
                                              Web Components            SIEM Streaming
```

---

## Métriques de Succès par Phase

| Phase | Métrique clé | Cible |
|---|---|---|
| Phase 0 | Coverage tests | ≥ 90% |
| Phase 0 | Documentation | README + 5 guides |
| Phase 1 | Providers auth | ≥ 5 (Email, Phone, Google, GitHub, Magic Link, Passkey) |
| Phase 1 | SDK npm downloads | 100+ /semaine |
| Phase 2 | Dashboard | 100% des features moteur accessibles |
| Phase 2 | Webhooks | 100% des events couverts |
| Phase 3 | Clients Enterprise | 3+ contrats signés |
| Phase 4 | GitHub Stars | 1000+ |
| Phase 4 | MAU (Cloud) | 10,000+ |

---

## Stack Technique Recommandée

| Couche | Technologie | Justification |
|---|---|---|
| **Moteur** | Django + DRF | Déjà en place, Python-first |
| **Queue** | Celery + Redis | Webhooks, emails async |
| **Cache** | Redis | Rate limiting, sessions, tokens |
| **DB** | PostgreSQL | Production-grade, JSON fields |
| **Dashboard** | Next.js 14 + TailwindCSS + shadcn/ui | DX moderne, SSR |
| **SDK JS** | TypeScript vanilla + React adapter | Pas de lock-in |
| **Web Components** | Lit (Google) | Standard W3C, framework-agnostic |
| **CI/CD** | GitHub Actions | Tests, lint, publish, deploy |
| **Docs** | Mintlify ou Docusaurus | Beau, rapide, MDX |
| **Monitoring** | Sentry + Prometheus | Erreurs + métriques |
