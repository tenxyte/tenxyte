# Rapport Stratégique : Distribution Tenxyte — Open Source vs Cloud SaaS

> **Dernière mise à jour :** 19 Février 2026  
> **Basé sur :** Audit complet du code source (`src/tenxyte/`) + Analyse stratégique Organizations

---

## Philosophie du Modèle

| | Free (Open Source) | Premium (SaaS) | Enterprise (SaaS +) |
|---|---|---|---|
| **Ce que c'est** | Le moteur complet | Le moteur + un chauffeur | Le moteur + un chauffeur + un mécanicien dédié |
| **Cible** | Développeurs, projets souverains | Startups & PME | Fintech, Santé, Gouvernement |
| **Format** | `pip install tenxyte` | API REST Cloud + Dashboard | Instance dédiée + SLA |

> **Principe clé :** Le code Open Source est **identique** au moteur qui tourne en Cloud. Aucune fonctionnalité du "moteur" n'est bridée. La différence est uniquement dans le **service autour**.

---

## 1. Plan Free — Open Source / Self-Hosted

### Description
Le package Python `tenxyte` est une **application Django réutilisable** que tout développeur peut installer et intégrer dans son projet. Il a accès à 100% du code source et des fonctionnalités.

### Inventaire Complet des Fonctionnalités (Code Actuel)

#### 🔐 Authentification (7 endpoints)
- Inscription par email/téléphone (`RegisterView`)
- Login Email + Password (`LoginEmailView`)
- Login Téléphone + Password (`LoginPhoneView`)
- Google OAuth (id_token, access_token, authorization code) (`GoogleAuthView`)
- Rafraîchissement JWT avec rotation optionnelle (`RefreshTokenView`)
- Déconnexion unitaire (`LogoutView` — révoque refresh + blacklist access)
- Déconnexion de tous les appareils (`LogoutAllView`)

#### 🛡️ Sécurité Avancée
- **2FA/TOTP :** Activation, confirmation, désactivation, codes de secours regénérables (5 endpoints)
- **Mot de passe :** Réinitialisation via OTP, changement, vérification de force, exigences de complexité (5 endpoints)
- **Historique de mots de passe** (`PasswordHistory` model) — empêche la réutilisation
- **Verrouillage de compte** configurable (tentatives + durée via `settings.py`)
- **Alerte nouveau device** — email automatique si login depuis un appareil inconnu
- **Device Fingerprinting** (`device_info.py`) — parsing User-Agent + format structuré v1

#### 🔑 RBAC Complet (7 endpoints)
- CRUD Permissions (`PermissionListView`, `PermissionDetailView`)
- CRUD Rôles + assign permissions aux rôles (`RoleListView`, `RoleDetailView`, `RolePermissionsView`)
- Assign/Remove rôles et permissions directes par utilisateur (`UserRolesView`, `UserDirectPermissionsView`)
- **Hiérarchie de rôles** avec héritage de permissions
- **8 Décorateurs prêts à l'emploi :** `@require_role`, `@require_any_role`, `@require_all_roles`, `@require_permission`, `@require_any_permission`, `@require_all_permissions`, `@require_verified_email`, `@require_verified_phone`

#### 🏢 Organizations B2B (activable via `TENXYTE_ORGANIZATIONS_ENABLED = True`)
- **Hiérarchie Parent/Enfant** — Organisations avec sous-organisations (profondeur configurable)
- **Membres** — Users appartiennent à 1 ou plusieurs Organizations avec rôles org-scoped
- **RBAC Org-Scoped** — Rôles et permissions par organisation (séparés du RBAC global)
- **Décorateurs org-scoped** : `@require_org_membership`, `@require_org_role`, `@require_org_permission`, `@require_org_owner`
- **OrganizationContextMiddleware** — Header `X-Org-Slug` pour contextualiser les requêtes
- **Invitations** — Workflow d'invitation par email avec accept/decline/expire
- **Héritage de rôles** — Admin d'un parent = admin des enfants (configurable)
- **Modèles Abstract/Swappable** — `AbstractOrganization`, `AbstractOrganizationRole`, `AbstractOrganizationMembership`

#### 📱 OTP / Vérification (3 endpoints)
- Demande d'OTP Email ou SMS (`RequestOTPView`)
- Vérification Email (`VerifyEmailOTPView`)
- Vérification Téléphone (`VerifyPhoneOTPView`)

#### 📱 API Applications / Identification Plateforme (3 endpoints)
- CRUD Applications (`ApplicationListView`, `ApplicationDetailView`)
- Régénération de credentials (`ApplicationRegenerateView`)
- Authentification par `X-Access-Key` / `X-Access-Secret` (Middleware)

> **Note :** `Application` identifie la **plateforme** (Web, Mobile, Desktop) d'un même projet. Les Users, Rôles et Permissions sont **partagés** entre les Applications d'un même projet. Ce N'EST PAS un tenant multi-projet.

#### 🛡️ Middlewares (4 + 1 optionnel)
- `ApplicationAuthMiddleware` — Authentification app (1ère couche)
- `JWTAuthMiddleware` — Validation JWT (2ème couche)
- `OrganizationContextMiddleware` — Contexte org optionnel (3ème couche, si Organizations activé)
- `CORSMiddleware` — Gestion CORS intégrée et configurable
- `SecurityHeadersMiddleware` — Headers de sécurité (X-Frame-Options, HSTS, etc.)

#### ⚡ Protection / Rate Limiting (8 throttle classes)
- Login, Login Horaire, Register, Register Daily
- Password Reset, Password Reset Daily
- OTP Request, OTP Verify
- Google Auth
- **+ Décorateur custom** `@rate_limit(max_requests=10, window_seconds=60)`
- **+ SimpleThrottleRule** — Rate limiter par URL configurable en `settings.py`

#### 🔏 RGPD / Suppression de Compte (5 endpoints)
- Demande de suppression (`request_account_deletion`)
- Confirmation par token email (`confirm_account_deletion`)
- Annulation de suppression (`cancel_account_deletion`)
- Statut des demandes (`account_deletion_status`)
- **Export de données utilisateur** (`export_user_data`) — Portabilité RGPD complète

#### 📊 Audit / Profil (2 endpoints)
- Profil utilisateur (`MeView` — GET & PATCH)
- Rôles et permissions de l'utilisateur connecté (`MyRolesView`)

#### ⚙️ Configuration Centralisée (`conf.py`)
- **150+ paramètres** configurables via `settings.py`
- JWT (lifetime, algorithme, secret), 2FA, SMS/Email backends, password policies, rate limiting, CORS, Security Headers, Session/Device limits

### Responsabilités du Développeur (Self-Hosted)
| Élément | Détail |
|---|---|
| Base de Données | PostgreSQL/MySQL — à configurer et maintenir |
| Email Gateway | SMTP, SendGrid, ou Amazon SES — vos propres clés |
| SMS Gateway | Twilio, Vonage — vos propres clés |
| Serveur | Hébergement, SSL, mises à jour de sécurité |
| Mises à jour | `pip install --upgrade tenxyte` — manuelles |

### Support
- GitHub Issues
- Documentation publique
- Communauté Discord (à venir)

---

## 2. Plan Premium — SaaS Cloud Managed

### Description
Tenxyte **hébergé et géré par nos soins**. Le développeur consomme une API REST sécurisée et gère ses utilisateurs via un Dashboard Web. Il n'a **rien à installer** ni à maintenir.

### Architecture Cloud : Compte → Projet → Application

> **Clarification importante :** Dans le moteur Tenxyte, `Application` identifie la **plateforme** (Web, Mobile, Desktop) d'un même projet — pas un tenant. En mode Cloud, le vrai **tenant** est le `Project`.

```
TenxyteAccount (le dev qui paie)
│
├── Project "GestionPro"  ◄── LE VRAI TENANT (isolation)
│   ├── Application "GestionPro Web"     (API Key: txk_abc...)
│   ├── Application "GestionPro Desktop" (API Key: txk_def...)
│   ├── Application "GestionPro Mobile"  (API Key: txk_ghi...)
│   ├── Users (partagés entre les 3 apps)
│   ├── Roles (partagés)
│   ├── Permissions (partagées)
│   └── Organizations (si activé, partagées entre les apps)
│
├── Project "MonSiteEcommerce"  ◄── AUTRE TENANT
│   ├── Application "Ecommerce Web"
│   ├── Application "Ecommerce Mobile"
│   └── Users/Roles/Permissions (ISOLÉS de GestionPro)
│
└── Limites selon Plan (nb projets, MAU/projet, etc.)
```

### Ce que le Développeur Reçoit (Valeur Ajoutée vs Free)

| Composant | Détail |
|---|---|
| **API REST Identique** | Même moteur que la librairie, hébergé sur notre infra |
| **Dashboard Admin** | Interface graphique pour gérer Users, Rôles, Permissions, Organizations, Sessions, Logs |
| **Email/SMS Inclus** | Quotas d'emails transactionnels et SMS inclus (ex: 10K emails/mois) |
| **Webhooks** | Notifications en temps réel : `user.created`, `user.logged_in`, `org.member.invited`, etc. |
| **Zéro Maintenance** | DB managée, backups auto, mises à jour de sécurité sans interruption |
| **Tenant Isolation** | Chaque **Project** a ses propres users/rôles/permissions/orgs isolés |
| **Monitoring** | Alertes en cas d'attaque brute-force, pics de connexions, etc. |

### Fonctionnalités Activées
- Toutes les fonctionnalités du Plan Free (moteur complet, Organizations incluses)
- **Hosted Login Page** — Page de login hébergée, personnalisable (Logo, Couleurs)
- **SDK JavaScript** — `useAuth()` pour React/Next/Vue
- **Organizations Dashboard** — Gestion visuelle des orgs, membres, rôles org-scoped
- Historique des logs d'audit — **rétention 90 jours**
- Rate Limiting dynamique — ajustable depuis le Dashboard
- Limites de sessions/devices configurables visuellement

### Limites de Plan
| Ressource | Limite |
|---|---|
| MAU (Monthly Active Users) | Jusqu'à 10,000 |
| Projects | 3 |
| Applications par Project | 5 |
| Membres par Organization | 50 |
| Profondeur hiérarchie Org | 2 niveaux |
| Rôles personnalisés | 20 |
| Webhooks | 5 |
| Email/mois | 10,000 |

### Prix
Forfaitaire ou au MAU, selon la stratégie commerciale.

---

## 3. Plan Enterprise — Cloud Scale & Compliance

### Description
Version Cloud avec **engagement contractuel**, infrastructure dédiée, et fonctionnalités de conformité avancées pour les organisations régulées.

### Ce que le Client Reçoit (en plus du Premium)

| Composant | Détail |
|---|---|
| **SLA** | 99.9% uptime garanti contractuellement |
| **SSO Corporatif** | SAML 2.0, OpenID Connect, intégration Active Directory / Okta |
| **SSO par Organization** | Chaque org peut avoir son propre provider SSO SAML/OIDC |
| **SCIM / Directory Sync** | Auto-provisioning des membres par org via Active Directory |
| **Data Residency** | Choix de la région de stockage (EU / US / Afrique) |
| **Instance Dédiée** | Isolation complète (base de données et compute dédiés) |
| **IP Dédiées** | Pour les règles de pare-feu strictes |
| **Audit Légal** | Archivage des logs sur 1 an+, exports conformité (GDPR, SOC2) |
| **Custom Email Sender** | Envoi depuis le domaine du client (ex: `noreply@client.com`) |
| **Pentests** | Tests de pénétration réguliers sur l'instance |

### Limites de Plan
| Ressource | Limite |
|---|---|
| MAU | Illimité (négocié) |
| Projects | Illimité |
| Applications (API Keys) | Illimité |
| Membres par Organization | Illimité |
| Profondeur hiérarchie Org | 5 niveaux |
| Rôles personnalisés | Illimité |
| Webhooks | Illimité |
| Email/mois | Illimité / Custom SMTP |
| Rétention Audit Logs | 1 an+ |

### Support
- Ingénieur dédié
- Onboarding assisté
- Canal Slack/Teams privé
- Réponse prioritaire (<4h)

---

## Matrice de Comparaison (pour le Site Web)

| Caractéristique | 🆓 Free | ⭐ Premium | 🏢 Enterprise |
| :--- | :---: | :---: | :---: |
| **Type** | Librairie Python | API Cloud | API Cloud Dédiée |
| **Hébergement** | Votre Serveur | Cloud Tenxyte | Cloud Tenxyte / VPC |
| **Code Source** | ✅ Complet | ❌ API Only | ❌ API Only |
| **Auth Email/Password** | ✅ | ✅ | ✅ |
| **Auth Téléphone** | ✅ | ✅ | ✅ |
| **Google OAuth** | ✅ | ✅ | ✅ |
| **2FA (TOTP)** | ✅ | ✅ | ✅ |
| **RBAC Global** | ✅ | ✅ | ✅ |
| **Organizations B2B** | ✅ (setting ON) | ✅ Dashboard | ✅ Dashboard avancé |
| **RBAC Org-Scoped** | ✅ (setting ON) | ✅ Dashboard | ✅ |
| **Membres/Org** | Illimité | 50 | Illimité |
| **Hiérarchie Org** | Configurable | 2 niveaux | 5 niveaux |
| **RGPD (Suppression/Export)** | ✅ | ✅ | ✅ |
| **Rate Limiting** | ✅ | ✅ Dashboard | ✅ Dashboard |
| **Device Fingerprinting** | ✅ | ✅ | ✅ |
| **Audit Logs** | Dans votre DB | 90 jours | 1 an+ / SIEM |
| **Dashboard Admin** | Django Admin | ✅ **Dashboard Tenxyte** | ✅ Avancé |
| **Email/SMS** | Vos clés API | ✅ **Inclus** | ✅ Illimité |
| **Webhooks** | ❌ (DIY) | ✅ 5 | ✅ Illimité |
| **Hosted Login Page** | ❌ | ✅ | ✅ Custom Domain |
| **SDK JS/React** | ❌ | ✅ | ✅ |
| **SSO (SAML/OIDC)** | ❌ | ❌ | ✅ |
| **SSO par Organization** | ❌ | ❌ | ✅ |
| **SCIM / Directory Sync** | ❌ | ❌ | ✅ |
| **Data Residency** | N/A | ❌ | ✅ |
| **SLA** | ❌ | ❌ | ✅ 99.9% |
| **Support** | GitHub | Email | Ingénieur dédié |
| **Maintenance DB** | Manuelle | ✅ Auto | ✅ Auto + Isolation |

---

## Architecture Technique — Actions Concrètes

### 1. Le Package `tenxyte` (src actuel) — Produit d'Appel
C'est le moteur. Il doit être **irréprochable**, bien documenté, et facile à installer.

**Ce qui existe déjà (36+ endpoints, prêts) :**
- Auth complète (Email, Phone, Google, JWT, Refresh rotation)
- RBAC granulaire avec décorateurs
- 2FA/TOTP avec backup codes
- Rate limiting avancé (8 throttle classes + custom decorator)
- RGPD complet (suppression, annulation, export)
- Device fingerprinting
- 4 middlewares de sécurité + 1 optionnel (Organizations)
- 150+ settings configurables

**À intégrer dans le moteur (planifié) :**
- Organizations B2B (modèles, endpoints, décorateurs org-scoped)
- Activable via `TENXYTE_ORGANIZATIONS_ENABLED = True`

### 2. La Super-App Tenxyte Cloud (à construire)
Une application **Django + React** qui consomme en interne le package `tenxyte` et ajoute :

```
┌─────────────────────────────────────────────────────────┐
│                 TENXYTE CLOUD PLATFORM                    │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ Dashboard  │  │  Webhooks  │  │  Billing   │         │
│  │  (React)   │  │  Engine    │  │  Engine    │         │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
│        │               │               │                │
│  ┌─────┴───────────────┴───────────────┴──────────────┐ │
│  │          TENANT MANAGEMENT LAYER                    │ │
│  │   TenxyteAccount → Project (tenant) → Application  │ │
│  │   (Application = plateforme Web/Mobile/Desktop)     │ │
│  └─────────────────┬──────────────────────────────────┘ │
│                    │                                    │
│  ┌─────────────────┴──────────────────────────────────┐ │
│  │         📦  PACKAGE TENXYTE (src)                  │ │
│  │   (Le même code que la version Open Source)        │ │
│  │   Auth + RBAC + 2FA + RGPD + Organizations B2B    │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

> **Note :** Le `Project` est le **vrai tenant** dans le Cloud. Il regroupe les Applications (Web/Mobile/Desktop), les Users, les Rôles, les Permissions et les Organizations. Le modèle `Application` existant garde son rôle d'identification de plateforme.

### 3. Priorités de Développement
1. **Organizations B2B** — Intégration dans le moteur (modèles, endpoints, décorateurs)
2. **Documentation du package** — README, guides d'intégration, exemples
3. **SDK JavaScript** (vanilla + React hooks)
4. **Dashboard Admin** (React) pour le SaaS — incluant gestion des Orgs
5. **Système de Webhooks** côté serveur (incluant `org.*` events)
6. **Hosted Login Page** (page hébergée personnalisable)
7. **SSO SAML/OIDC** pour le plan Enterprise (org-scoped)
8. **SCIM / Directory Sync** par Organization (Enterprise)
