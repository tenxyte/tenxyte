![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Authentification Python indépendante du framework en quelques minutes — JWT, RBAC, 2FA, Liens Magiques, Passkeys, Connexion Sociale, Vérification de Fuites, Organisations (B2B), support multi-application.

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-4.2%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/tenxyte?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/tenxyte)

---

## Démarrage Rapide — 2 minutes pour votre premier appel API

### 1. Installation

```bash
pip install tenxyte
```

> **Prérequis :** Python 3.10+, Django 4.2+ ou FastAPI 0.135+

### 2. Configuration

```python
# settings.py — ajoutez tout en bas
import tenxyte
tenxyte.setup(globals())   # injecte automatiquement INSTALLED_APPS, AUTH_USER_MODEL, REST_FRAMEWORK, MIDDLEWARE
```

```python
# urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

### 3. Lancement

```bash
python manage.py tenxyte_quickstart   # migrate + seed rôles + création Application
python manage.py runserver
```

### 4. Premier appel API

```bash
# Inscription — utilisez les identifiants affichés par tenxyte_quickstart
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <votre-access-key>" -H "X-Access-Secret: <votre-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'

# Connexion
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <votre-access-key>" -H "X-Access-Secret: <votre-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'

# Requête authentifiée
curl http://localhost:8000/api/v1/auth/me/ \
  -H "X-Access-Key: <votre-access-key>" -H "X-Access-Secret: <votre-access-secret>" \
  -H "Authorization: Bearer <access_token>"
```

> ⚠️ En `DEBUG=True`, Tenxyte génère automatiquement une **clé secrète JWT éphémère** (invalidée au redémarrage) et applique des limites de sécurité relâchées. Les en-têtes `X-Access-Key` / `X-Access-Secret` sont **toujours requis** sauf si vous définissez explicitement `TENXYTE_APPLICATION_AUTH_ENABLED = False`.

> 💡 Incluez `"login": true` dans la requête d'inscription pour recevoir les tokens JWT directement dans la réponse.

C'est tout — vous avez un backend d'authentification complet en fonctionnement.

---

## AIRS — AI Responsibility & Security (AI-Ready Start)

Tenxyte n'authentifie pas seulement les humains — il rend votre backend **sûr à connecter à des agents IA**.

**Principe fondamental** : un agent IA n'agit jamais de sa propre autorité. Il emprunte les permissions d'un utilisateur via un `AgentToken` à portée limitée et durée de vie courte, et chaque action devient auditable, contrôlable et suspendable.

### Un flux "AI Ready" réel, de bout en bout

#### 1) Un utilisateur délègue un token limité à un agent

```http
POST /ai/tokens/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "agent_id": "finance-agent-v2",
  "expires_in": 3600,
  "permissions": ["read:reports", "write:invoices"],
  "organization": "acme-corp",
  "budget_limit_usd": 5.00,
  "circuit_breaker": {
    "max_requests_per_minute": 30,
    "max_requests_total": 500
  },
  "dead_mans_switch": {
    "heartbeat_required_every": 300
  }
}
```

**Réponse (201) :**

```json
{
  "id": 42,
  "token": "eKj3...raw_token...Xz9",
  "agent_id": "finance-agent-v2",
  "status": "ACTIVE",
  "expires_at": "2024-01-20T16:00:00Z"
}
```

> ⚠️ Le `token` brut est retourné **une seule fois** à la création — seul son hash SHA-256 est persisté. Stockez-le de manière sécurisée.

L'agent appelle ensuite vos APIs avec :

```http
Authorization: AgentBearer <raw_token>
```

#### 2) Chaque requête de l'agent est doublement vérifiée (scope Agent + RBAC Humain)

Tenxyte applique une **Double Validation RBAC** :

- **Vérification du scope agent** : la permission est-elle dans `granted_permissions` du token ?
- **Vérification humaine** : l'utilisateur délégant la possède-t-il encore ?

Si l'une échoue, la requête est rejetée (`403 Forbidden`).

#### 3) Les actions dangereuses peuvent exiger une validation humaine (HITL)

Les endpoints décorés avec `@require_agent_clearance(human_in_the_loop_required=True)` ne s'exécutent pas immédiatement lorsqu'ils sont appelés par un agent. Tenxyte crée un `AgentPendingAction` et retourne **`202 Accepted`** :

```json
{
  "status": "pending_confirmation",
  "message": "This action requires human approval.",
  "confirmation_token": "hitl_a1b2c3d4e5f6...",
  "expires_at": "2024-01-20T16:10:00Z"
}
```

L'humain confirme via :

```http
POST /ai/pending-actions/<confirmation_token>/confirm/
Authorization: Bearer <user_jwt>
```

L'agent relance ensuite l'appel original avec le token confirmé :

```http
X-Action-Confirmation: hitl_a1b2c3d4e5f6...
```

#### 4) Les agents incontrôlables sont stoppés automatiquement (Circuit Breaker + Dead Man's Switch)

Si l'agent dépasse les limites RPM/totales, atteint des seuils d'anomalie, rate le heartbeat ou épuise son budget, le token est automatiquement **SUSPENDU**.

```http
POST /ai/tokens/{id}/heartbeat/
Authorization: AgentBearer <raw_token>
```

#### 5) Le suivi de budget transforme les dépenses LLM en mécanisme d'application

Votre code signale les coûts ; Tenxyte les accumule et suspend le token quand la limite est atteinte.

```http
POST /ai/tokens/{id}/report-usage/
Authorization: AgentBearer <raw_token>
Content-Type: application/json

{
  "cost_usd": 0.042,
  "prompt_tokens": 1250,
  "completion_tokens": 450
}
```

#### 6) Audit forensique : tracez "quel prompt a causé quelle action"

Attachez `X-Prompt-Trace-ID` aux requêtes agent et Tenxyte le lie aux actions en attente et à la piste d'audit.

```http
X-Prompt-Trace-ID: trace_7f3a2b9c-...
```

> Vous voulez la référence complète (rédaction PII, paramètres, raisons de suspension, etc.) ? Consultez le **[Guide AIRS](airs.md)**.

---

## Organisations — Multi-Tenant B2B, Prêt à l'Emploi

Vous construisez un SaaS pour des entreprises ? Tenxyte embarque une hiérarchie multi-tenant complète avec RBAC par organisation, gestion des membres et flux d'invitation — aucune infrastructure supplémentaire nécessaire.

### Activation en une ligne

```python
TENXYTE_ORGANIZATIONS_ENABLED = True
```

### Modélisez n'importe quelle structure organisationnelle

```
Acme Corp (racine)
├── Ingénierie
│   ├── Équipe Backend
│   └── Équipe Frontend
└── Ventes
    └── EMEA
```

```http
POST /api/v1/auth/organizations/
Authorization: Bearer <token>
Content-Type: application/json

{ "name": "Ingénierie", "slug": "acme-engineering", "parent_id": 1 }
```

### Invitez des membres par email

```http
POST /api/v1/auth/organizations/invitations/
Authorization: Bearer <token>
X-Org-Slug: acme-corp
Content-Type: application/json

{ "email": "newmember@example.com", "role_code": "member", "expires_in_days": 7 }
```

Un email d'invitation est envoyé. L'utilisateur accepte en s'inscrivant ou en se connectant.

### Permissions par organisation dans les vues

```python
from tenxyte.decorators import require_jwt, require_org_context, require_org_permission

class OrgSettingsView(APIView):
    @require_jwt
    @require_org_context
    @require_org_permission('org.manage')
    def post(self, request):
        org = request.organization   # résolu depuis l'en-tête X-Org-Slug
        ...
```

### Héritage des rôles

Quand `TENXYTE_ORG_ROLE_INHERITANCE = True` (par défaut), les rôles se propagent vers le bas de la hiérarchie : un `admin` dans `Acme Corp` est automatiquement `admin` dans `Ingénierie`, `Équipe Backend`, etc.

> Référence complète : **[Guide des Organisations](organizations.md)**

---

## Shortcut Secure Mode — Sécurité Production en Une Ligne

Plutôt que de régler 115+ paramètres, choisissez un préréglage qui correspond à votre modèle de menace :

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'   # 'development' | 'medium' | 'robust'
```

| Paramètre | `development` | `medium` | `robust` |
|---|---|---|---|
| **Cible** | Prototypes, dev local | SaaS public, B2C | Fintech, santé, RGPD |
| Durée de vie access token | 1h | 15min | **5min** |
| Rotation du refresh token | ✗ | ✓ | ✓ |
| Tentatives de connexion max | 10 | 5 | **3** |
| Durée de verrouillage | 15min | 30min | **60min** |
| Historique des mots de passe | ✗ | 5 | **12** |
| Vérification fuites (HIBP) | ✗ | ✓ + blocage | ✓ + blocage |
| Journaux d'audit | ✗ | ✓ | ✓ |
| Limites d'appareils | ✗ | 5 | **2 (refus)** |
| En-têtes de sécurité | ✗ | ✓ | ✓ |
| Passkeys (WebAuthn) | ✗ | ✗ | **✓** |

Chaque paramètre reste individuellement modifiable — le préréglage est un point de départ, pas une cage :

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'robust'
TENXYTE_WEBAUTHN_ENABLED = False         # désactiver les passkeys
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 600  # 10min au lieu de 5min
```

> Référence complète : **[Guide des Paramètres](settings.md)**

---

## Passkeys (WebAuthn / FIDO2) — Sans Mot de Passe, Anti-Hameçonnage

Tenxyte embarque une stack WebAuthn/FIDO2 complète. Les utilisateurs s'inscrivent une fois avec Face ID, Touch ID ou une clé matérielle — puis s'authentifient sans jamais entrer de mot de passe.

### Activation

```python
TENXYTE_WEBAUTHN_ENABLED = True          # activé automatiquement avec le préréglage 'robust'
TENXYTE_WEBAUTHN_RP_ID = 'yourapp.com'
TENXYTE_WEBAUTHN_RP_NAME = 'Your App'
```

> Prérequis : `pip install tenxyte[webauthn]`

### 1) Enregistrer un passkey

```http
# Étape 1 — Obtenir le challenge navigateur
POST /api/v1/auth/webauthn/register/begin/
Authorization: Bearer <user_jwt>

# Étape 2 — Soumettre la clé navigateur
POST /api/v1/auth/webauthn/register/complete/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "challenge_id": 123,
  "credential": { ...réponse WebAuthn du navigateur... },
  "device_name": "MacBook Touch ID"
}
```

**Réponse (201) :**

```json
{
  "message": "Passkey registered successfully",
  "credential": {
    "id": "cred_abc123",
    "device_name": "MacBook Touch ID",
    "created_at": "2024-01-20T15:00:00Z"
  }
}
```

### 2) S'authentifier — sans mot de passe

```http
# Étape 1 — Obtenir le challenge navigateur
POST /api/v1/auth/webauthn/authenticate/begin/
Content-Type: application/json

{ "email": "user@example.com" }

# Étape 2 — Soumettre la clé navigateur
POST /api/v1/auth/webauthn/authenticate/complete/
Content-Type: application/json

{
  "challenge_id": 456,
  "credential": { ...réponse WebAuthn du navigateur... }
}
```

**Réponse (200) :**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": { "id": 42, "email": "user@example.com" },
  "message": "Authentication successful"
}
```

Supporte les **resident keys** — le passkey lui-même identifie l'utilisateur, aucun email nécessaire.

> Référence complète : **[Endpoints de l'API](endpoints.md)**

---

## Pourquoi Choisir Tenxyte ?

Tenxyte est le seul package d'authentification conçu pour **les humains et les agents IA**, tout en restant entièrement auto-hébergé, open-source et agnostique au framework — avec support Django complet aujourd'hui, FastAPI (partiel), et Java, Node.js et PHP en roadmap.

### Tableau Comparatif

| Fonctionnalité | **Tenxyte** | django-allauth | Clerk | Auth0 |
|---|:---:|:---:|:---:|:---:|
| **Type** | Package Python | Package Django | SaaS | SaaS |
| **Open source** | ✅ MIT | ✅ MIT | ❌ | ❌ |
| **Auto-hébergé / propriété des données** | ✅ | ✅ | ❌ | ❌ ¹ |
| **Support de frameworks** | ✅ Django (complet) · FastAPI (partiel) · Java, Node.js, PHP en cours | Django uniquement | SDK (JS en priorité) | SDK (20+ langages) |
| **JWT (accès + rafraîchissement)** | ✅ | ❌ ² | ✅ | ✅ |
| **Connexion sociale** | ✅ 4 providers | ✅ 50+ providers | ✅ 20+ providers | ✅ 30+ providers |
| **Liens Magiques** | ✅ | ✅ | ✅ | ✅ |
| **Passkeys / WebAuthn** | ✅ | ✅ | ✅ | ✅ |
| **2FA / TOTP + codes de secours** | ✅ | ✅ | ✅ | ✅ |
| **RBAC (rôles + permissions + décorateurs Python)** | ✅ complet | ❌ | ⚠️ par organisation | ⚠️ add-on |
| **Organisations / multi-tenant** | ✅ hiérarchique | ❌ | ✅ plat | ✅ |
| **Vérification fuites (HaveIBeenPwned)** | ✅ intégré | ❌ | ❌ | ✅ |
| **Verrouillage progressif** | ✅ | ⚠️ basique | ✅ | ✅ |
| **Journaux d'audit (API interrogeable)** | ✅ | ❌ | ⚠️ tableau de bord | ⚠️ flux de logs |
| **Préréglages Shortcut Secure Mode** | ✅ | ❌ | ❌ | ❌ |
| **Tokens agent IA (AIRS)** | ✅ | ❌ | ❌ | ⚠️ expérimental ³ |
| **Human-in-the-Loop (HITL)** | ✅ | ❌ | ❌ | ❌ |
| **Suivi budget LLM** | ✅ | ❌ | ❌ | ❌ |
| **Circuit Breaker + Dead Man's Switch** | ✅ | ❌ | ❌ | ❌ |
| **Trace forensique (X-Prompt-Trace-ID)** | ✅ | ❌ | ❌ | ❌ |
| **Gratuit / tarification** | ✅ illimité | ✅ illimité | ⚠️ 10k MAU | ⚠️ 7,5k MAU |

> ✅ = support natif · ⚠️ = partiel / limité · ❌ = non disponible

¹ Auth0 propose une option "Private Cloud" aux tarifs entreprise.  
² django-allauth utilise les sessions Django ; JWT nécessite un package séparé (ex. `djangorestframework-simplejwt`).  
³ Auth0 a annoncé des flux OAuth pour agents IA en 2025 (`auth0.com/ai`), sans suivi de budget, HITL ni circuit breaker.

### Quand choisir Tenxyte

- **Vous avez besoin d'une infrastructure IA-ready** — tokens agent à portée limitée, HITL, application du budget et circuit breakers sont intégrés, pas ajoutés en surcouche.
- **Vous possédez vos données** — utilisateurs, tokens, journaux d'audit et structures organisationnelles vivent dans votre propre base de données.
- **Vous construisez un SaaS sérieux** — organisations multi-tenant hiérarchiques, double validation RBAC et pistes d'audit forensiques dès le départ.
- **Vous voulez une ligne de config pour la sécurité en production** — `TENXYTE_SHORTCUT_SECURE_MODE = 'robust'` remplace une checklist d'audit de sécurité.
- **Vous avez besoin d'une couverture multi-framework** — intégration Django complète aujourd'hui, FastAPI (partiel) déjà supporté, avec Java (Spring Boot), Node.js (Express, Nest.js) et PHP (Laravel, Symfony) en roadmap.

---

## Fonctionnalités Clés

✨ **Authentification de Base**
- JWT avec tokens d'accès + rafraîchissement, rotation, liste noire
- Connexion par email / téléphone, Liens Magiques (sans mot de passe), Passkeys (WebAuthn/FIDO2)
- Connexion Sociale — Google, GitHub, Microsoft, Facebook
- Support multi-application (`X-Access-Key` / `X-Access-Secret`)

🔐 **Sécurité**
- 2FA (TOTP) — Google Authenticator, Authy
- OTP par email et SMS, vérification de fuites de mots de passe (HaveIBeenPwned, k-anonymity)
- Verrouillage de compte, limites de sessions & appareils, limitation de débit, CORS, en-têtes de sécurité
- Journaux d'audit

👥 **RBAC**
- Rôles hiérarchiques, permissions directes (par utilisateur et par rôle)
- 9 décorateurs + classes de permissions DRF

🏢 **Organisations (B2B)**
- Multi-tenant avec arborescence hiérarchique, rôles & adhésions par organisation

📱 **Communication**
- SMS : Twilio, NGH Corp, Console
- Email : Django (recommandé), SendGrid, Console

⚙️ **Shortcut Secure Mode**
- Préréglage de sécurité en une ligne : `TENXYTE_SHORTCUT_SECURE_MODE = 'medium'`
- Modes : `development` / `medium` / `robust` — tous individuellement modifiables

---

## Options d'Installation

```bash
pip install tenxyte              # Inclut l'adaptateur Django (rétrocompatible)
pip install tenxyte[core]        # Core uniquement — sans framework, à vous de choisir
pip install tenxyte[fastapi]     # Adaptateur FastAPI + Core

# Extras optionnels (fonctionnent avec n'importe quel adaptateur)
pip install tenxyte[twilio]      # SMS via Twilio
pip install tenxyte[sendgrid]    # Email via SendGrid
pip install tenxyte[mongodb]     # Support MongoDB
pip install tenxyte[postgres]    # PostgreSQL
pip install tenxyte[mysql]       # MySQL/MariaDB
pip install tenxyte[webauthn]    # Passkeys / FIDO2
pip install tenxyte[all]         # Tout inclus
```

---

## Configuration Production

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'votre-secret-long-aléatoire-dédié'   # REQUIS
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'                        # 'medium' | 'robust'
TENXYTE_APPLICATION_AUTH_ENABLED = True
```

- Configurez un backend de base de données résilient (PostgreSQL recommandé)
- Configurez un fournisseur d'email (ex. SendGrid)
- Activez TLS/HTTPS en frontal

---

## Aperçu des Endpoints

> Les routes requièrent les en-têtes `X-Access-Key` et `X-Access-Secret` par défaut. Pour désactiver cette vérification en développement, définissez `TENXYTE_APPLICATION_AUTH_ENABLED = False` (interdit en production).

| Catégorie | Endpoints Principaux |
|---|---|
| **Auth** | `register`, `login/email`, `login/phone`, `refresh`, `logout`, `logout/all` |
| **Social** | `social/google`, `social/github`, `social/microsoft`, `social/facebook` |
| **Lien Magique** | `magic-link/request`, `magic-link/verify` |
| **Passkeys** | `webauthn/register/begin+complete`, `webauthn/authenticate/begin+complete` |
| **OTP** | `otp/request`, `otp/verify/email`, `otp/verify/phone` |
| **Mot de Passe** | `password/reset/request`, `password/reset/confirm`, `password/change` |
| **2FA** | `2fa/setup`, `2fa/confirm`, `2fa/disable`, `2fa/backup-codes` |
| **Profil** | `me/`, `me/roles/` |
| **RBAC** | `roles/`, `permissions/`, `users/{id}/roles/`, `users/{id}/permissions/` |
| **Applications** | `applications/` (CRUD + régénération) |

Pour des exemples complets avec les corps de requête/réponse, voir [endpoints.md](endpoints.md).

### Documentation Interactive

Ajoutez ces routes à votre `urls.py` pour Swagger UI et ReDoc :

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns += [
    path(f'{api_prefix}/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{api_prefix}/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{api_prefix}/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

- [**Collection Postman**](../../tenxyte_api_collection.postman_collection.json) — Collection prête à l'emploi

---

## 📚 Documentation

### 📖 **Guides pour Développeurs**
- [**Démarrage Rapide**](quickstart.md) - Commencez en 2 minutes avec Django
- [**Démarrage Rapide FastAPI**](fastapi_quickstart.md) - Commencez avec FastAPI
- [**Référence des Paramètres**](settings.md) - Toutes les 115+ options de configuration
- [**Endpoints de l'API**](endpoints.md) - Référence complète des endpoints avec exemples
- [**Comptes Admin**](admin.md) - Gérer les Super-utilisateurs et les Admins RBAC
- [**Guide des Applications**](applications.md) - Gérer les clients API et les identifiants
- [**Guide RBAC**](rbac.md) - Rôles, permissions et décorateurs
- [**Guide de Sécurité**](security.md) - Fonctionnalités de sécurité et bonnes pratiques
- [**Guide des Organisations**](organizations.md) - Configuration B2B multi-tenant
- [**Guide AIRS**](airs.md) - Responsabilité et Sécurité de l'IA
- [**Guide de Migration**](MIGRATION_GUIDE.md) - Migration depuis dj-rest-auth, simplejwt

### 📦 **Intégration SDK (JavaScript / TypeScript)**
- [**Vue d'ensemble du SDK JavaScript**](integration/javascript/index.md) - Packages, installation, configuration, gestion des erreurs
- [**Guide @tenxyte/core**](integration/javascript/core.md) - SDK agnostique au framework — les 10 modules, mode cookie, PKCE, événements
- [**Guide @tenxyte/react**](integration/javascript/react.md) - Hooks React, TenxyteProvider, exemples SPA
- [**Guide @tenxyte/vue**](integration/javascript/vue.md) - Composables Vue 3, configuration du plugin, exemples SPA

### 🔧 **Documentation Technique**
- [**Guide d'Architecture**](architecture.md) - Architecture Core & Adapters (Hexagonale)
- [**Guide Async**](async_guide.md) - Modèles async/await et bonnes pratiques
- [**Service de Tâches**](task_service.md) - Traitement des tâches en arrière-plan
- [**Guide des Adaptateurs Personnalisés**](custom_adapters.md) - Création d'adaptateurs personnalisés
- [**Référence des Schémas**](schemas.md) - Composants de schéma réutilisables
- [**Guide de Test**](TESTING.md) - Stratégies de test et exemples
- [**Tâches Périodiques**](periodic_tasks.md) - Tâches de maintenance et de nettoyage planifiées
- [**Dépannage**](troubleshooting.md) - Problèmes courants et solutions
- [**Contribution**](CONTRIBUTING.md) - Comment contribuer à Tenxyte

---

## Architecture : Core & Adapters

Tenxyte est construit autour d'un **Core indépendant du framework** utilisant une architecture Ports et Adapters (Hexagonale).

- **Core** : Contient la logique pure Python d'authentification, JWT et RBAC (zéro dépendance framework).
- **Ports** : Définit des interfaces abstraites pour les opérations externes (ex. Repositories, EmailServices, CacheServices).
- **Adapters** : Implémentations concrètes adaptées aux frameworks (Django, FastAPI) ou aux bibliothèques.

Cette conception garantit que les déploiements Django existants fonctionnent avec **zéro changement cassant**, tout en ouvrant nativement le support des frameworks asynchrones modernes comme FastAPI.

En savoir plus dans notre **[Guide d'Architecture](architecture.md)** détaillé.

---

## Bases de Données Supportées

- ✅ **SQLite** — développement
- ✅ **PostgreSQL** — recommandé pour la production
- ✅ **MySQL/MariaDB**
- ✅ **MongoDB** — via `django-mongodb-backend` (voir [quickstart.md](quickstart.md#mongodb) pour la configuration)

---

## Personnalisation & Extension

Tenxyte expose des classes de base abstraites : `AbstractUser`, `AbstractRole`, `AbstractPermission`, `AbstractApplication`.

```python
# myapp/models.py
from tenxyte.models import AbstractUser

class CustomUser(AbstractUser):
    company = models.CharField(max_length=100, blank=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'
```

```python
# settings.py
TENXYTE_USER_MODEL = 'myapp.CustomUser'
AUTH_USER_MODEL = 'myapp.CustomUser'
```

Même principe pour `TENXYTE_ROLE_MODEL`, `TENXYTE_PERMISSION_MODEL`, `TENXYTE_APPLICATION_MODEL`. Héritez toujours du `Meta` parent et définissez un `db_table` personnalisé.

### Création d'Adaptateurs Framework Personnalisés

Comme Tenxyte est indépendant du framework, vous pouvez écrire vos propres adaptateurs de Base de données, Cache ou Email en utilisant les `Ports` du core. Consultez le **[Guide des Adaptateurs Personnalisés](custom_adapters.md)** pour des instructions détaillées sur l'extension du core.

---

## Référence de Configuration

Plus de 115 paramètres documentés dans [settings.md](settings.md).

Options utiles pour le développement :

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # désactive la vérification X-Access-Key
TENXYTE_RATE_LIMITING_ENABLED = False
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = False          # pour les tests uniquement
```

---

## Maintenance Périodique

Tenxyte nécessite des tâches périodiques (nettoyage des tokens, purge OTP, rotation des journaux d'audit) pour maintenir les performances et la sécurité. Consultez le [Guide des Tâches Périodiques](periodic_tasks.md) pour la configuration complète avec Celery Beat ou cron.

---

## Développement & Tests

```bash
git clone https://github.com/tenxyte/tenxyte.git
pip install -e ".[dev]"
pytest                               # 1553 tests, 100% de réussite
pytest --cov=tenxyte --cov-report=html
```

**Tests multi-BDD** (nécessite un serveur par backend) :

```bash
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_sqlite"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_pgsql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mysql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mongodb"
```

---

## Foire Aux Questions & Dépannage

**`MongoDB does not support AutoField/BigAutoField`**
→ Configurez `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` et ajoutez `MIGRATION_MODULES = {'contenttypes': None, 'auth': None}`. Voir [quickstart.md](quickstart.md#mongodb).

**`Model instances without primary key value are unhashable`**
→ Même correctif (`MIGRATION_MODULES`). Si le problème persiste, déconnectez les signaux `post_migrate` pour `create_permissions` et `create_contenttypes`.

**`ModuleNotFoundError: No module named 'rest_framework'`**
→ `pip install djangorestframework`

**401 Unauthorized / JWT ne fonctionne pas**
→ Assurez-vous que les trois en-têtes sont présents : `X-Access-Key`, `X-Access-Secret`, `Authorization: Bearer <token>`.

**`No module named 'corsheaders'`**
→ Tenxyte inclut un middleware CORS intégré (`tenxyte.middleware.CORSMiddleware`). Supprimez `corsheaders` de votre configuration.

Pour plus de solutions, voir [troubleshooting.md](troubleshooting.md).

---

## Contribution

Les contributions sont les bienvenues ! Quelques règles simples :

1. Ouvrez une issue avant une demande de fonctionnalité majeure.
2. Fork → branche `feature/xxx` → PR avec tests et changelog.
3. Respectez les conventions de commit et ajoutez des tests unitaires.

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour plus de détails.

## Licence

MIT — voir [LICENSE](../../LICENSE).

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Suivi des bugs](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

Voir [CHANGELOG.md](../../CHANGELOG.md) pour l'historique des versions.
