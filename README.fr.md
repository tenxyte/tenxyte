[Read this documentation in English](README.md)

![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Authentification Python agnostique au framework en quelques minutes — JWT, RBAC, 2FA, Liens Magiques, Passkeys, Connexion Sociale, Vérification des fuites de mots de passe, Organisations (B2B), support multi-application.

[![Version PyPI](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Versions Python](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Versions Django](https://img.shields.io/badge/django-6.0%2B-blue.svg)](https://www.djangoproject.com/)
[![Licence : MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Couverture](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte)

---

## Table des Matières

- [Fonctionnalités Clés](#fonctionnalites-cles)
- [Prérequis](#prerequis)
- [Installation](#installation)
- [Démarrage Rapide (Dev vs Prod)](#demarrage-rapide--developpement)
- [Exemples de Requêtes et Réponses](#exemples-de-requetes-et-reponses)
- [Points de Terminaison et Documentation](#points-de-terminaison-et-documentation)
- [Structure de la Documentation](#-structure-de-la-documentation)
- [Architecture : Core et Adaptateurs](#architecture--core-et-adaptateurs)
- [Bases de Données Supportées](#bases-de-donnees-supportees)
- [Maintenance Périodique](#maintenance-periodique)
- [Personnalisation et Extension](#personnalisation-et-extension)
- [Développement et Tests](#developpement-et-tests)
- [Dépannage](#questions-frequemment-posees--depannage)
- [Standards de Documentation](#-standards-de-documentation)
- [Contribution](#contribution)
- [Licence et Support](#licence)

---

## Fonctionnalités Clés

✨ **Authentification Core**
- JWT avec jetons d'accès + rafraîchissement, rotation, liste noire
- Connexion par e-mail / téléphone, Liens Magiques (sans mot de passe), Passkeys (WebAuthn/FIDO2)
- Connexion Sociale — Google, GitHub, Microsoft, Facebook
- Support multi-application (`X-Access-Key` / `X-Access-Secret`)

🔐 **Sécurité**
- 2FA (TOTP) — Google Authenticator, Authy
- OTP par e-mail et SMS, vérification des fuites de mots de passe (HaveIBeenPwned, k-anonymat)
- Verrouillage de compte, limites de sessions et d'appareils, limitation de débit (rate limiting), CORS, en-têtes de sécurité
- Journaux d'audit (Audit logging)

👥 **RBAC**
- Rôles hiérarchiques, permissions directes (par utilisateur et par rôle)
- 8 décorateurs + classes de permission DRF

🏢 **Organisations (B2B)**
- Multi-tenant avec arbre hiérarchique, rôles et adhésions par organisation

📱 **Communication**
- SMS : Twilio, NGH Corp, Console
- E-mail : Django (recommandé), SendGrid, Console

⚙️ **Mode de Sécurité Raccourci (Shortcut Secure Mode)**
- Préréglage de sécurité en une ligne : `TENXYTE_SHORTCUT_SECURE_MODE = 'medium'`
- Modes : `development` / `medium` / `robust` — tous surchargeables individuellement

---

## Prérequis

- Python 3.10+ (3.11+ recommandé)
- `pip` et un environnement virtuel
- **Django 6.0+** (pour l'adaptateur Django) ou **FastAPI 0.135+** (pour l'adaptateur FastAPI)
- Base de données (PostgreSQL recommandé pour la production)

## Installation

```bash
pip install tenxyte              # Inclut l'adaptateur Django (rétrocompatible)
pip install tenxyte[core]        # Core uniquement — sans framework, apportez le vôtre
pip install tenxyte[fastapi]     # Adaptateur FastAPI + Core

# Extras optionnels (fonctionnent avec n'importe quel adaptateur)
pip install tenxyte[twilio]      # SMS via Twilio
pip install tenxyte[sendgrid]    # E-mail via SendGrid
pip install tenxyte[mongodb]     # Support MongoDB
pip install tenxyte[postgres]    # PostgreSQL
pip install tenxyte[mysql]       # MySQL/MariaDB
pip install tenxyte[webauthn]    # Passkeys / FIDO2
pip install tenxyte[all]         # Tout inclus
```

## Démarrage Rapide — Développement

### 1. Installer

```bash
pip install tenxyte
```

### 2. Configurer (`settings.py` + `urls.py`)

```python
# settings.py — Ajoutez ceci à la FIN du fichier (après INSTALLED_APPS, MIDDLEWARE, etc.)
import tenxyte
tenxyte.setup(globals())

# `tenxyte.setup(globals())` injecte automatiquement la configuration minimale requise :
# - Définit AUTH_USER_MODEL = 'tenxyte.User'
# - Ajoute 'rest_framework' et 'tenxyte' à INSTALLED_APPS
# - Configure DEFAULT_AUTHENTICATION_CLASSES et DEFAULT_SCHEMA_CLASS pour REST_FRAMEWORK
# - Ajoute 'tenxyte.middleware.ApplicationAuthMiddleware' à MIDDLEWARE
# Note : Il n'écrasera JAMAIS les paramètres que vous avez déjà explicitement définis.
```

### Comprendre `tenxyte.setup()` VS `tenxyte.setup(globals())`
Passer `globals()` indique à Tenxyte de modifier directement le dictionnaire local de variables dans votre `settings.py`. **C'est l'approche recommandée et la plus sûre**, car elle garantit strictement que vos dictionnaires `INSTALLED_APPS`, `MIDDLEWARE` et `REST_FRAMEWORK` sont proprement complétés sans risquer de problèmes de résolution de modules. Placez-le toujours tout en **bas** de votre `settings.py`.

```python
# urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

### 3. Initialiser (Bootstrap)

```bash
python manage.py tenxyte_quickstart
# → makemigrations + migrate + seed roles/permissions + create Application
python manage.py runserver
```

> ⚠️ En `DEBUG=True`, Tenxyte active un comportement "zéro configuration" : JWT éphémère, `X-Access-Key` désactivé, limites assouplies.

```bash
# Première requête — aucun en-tête spécial requis en dev !
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

### Démarrage Rapide — Production

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'votre-secret-long-et-aleatoire-dedie'   # REQUIS
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'                        # 'medium' | 'robust'
TENXYTE_APPLICATION_AUTH_ENABLED = True
```

- Configurez un backend de base de données résilient (PostgreSQL recommandé)
- Configurez un fournisseur d'e-mail (ex: SendGrid)
- Activez TLS/HTTPS en amont

---

## Exemples de Requêtes et Réponses

> En production, les routes nécessitent les en-têtes `X-Access-Key` et `X-Access-Secret`. En `DEBUG=True` (mode dev), ils ne sont pas requis.

### S'enregistrer (Register)

**Requête :**

```http
POST /api/v1/auth/register/
Content-Type: application/json
X-Access-Key: <app_key>
X-Access-Secret: <app_secret>

{
  "email": "user@example.com",
  "password": "SecureP@ss1!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Réponse (201 Created) :**

```json
{
  "message": "Registration successful",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "phone_country_code": null,
    "phone_number": null,
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false,
    "roles": [],
    "permissions": [],
    "created_at": "2026-03-03T22:00:00Z",
    "last_login": null
  },
  "verification_required": {
    "email": true,
    "phone": false
  }
}
```

> 💡 Pour connecter l'utilisateur immédiatement après l'enregistrement, incluez `"login": true` dans la requête — les jetons JWT seront alors inclus dans la réponse (`access_token`, `refresh_token`, `token_type`, `expires_in`).

### Connexion (e-mail)

**Requête :**

```http
POST /api/v1/auth/login/email/
Content-Type: application/json
X-Access-Key: <app_key>
X-Access-Secret: <app_secret>

{
  "email": "user@example.com",
  "password": "SecureP@ss1!"
}
```

**Réponse (200 OK) :**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "desktop/windows",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "phone": "",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "is_2fa_enabled": false
  }
}
```

> Si la 2FA est activée sur le compte, ajoutez `"totp_code": "123456"` à la requête.

### curl — Résumé rapide

```bash
# S'enregistrer
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'

# Se connecter
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'

# Requête authentifiée
curl http://localhost:8000/api/v1/auth/me/ \
  -H "X-Access-Key: key" -H "X-Access-Secret: secret" \
  -H "Authorization: Bearer <access_token>"
```

Pour des exemples plus complets avec réponses, voir : [docs/fr/endpoints.md](docs/fr/endpoints.md)

---

## Points de Terminaison et Documentation

### Documentation Interactive

Pour activer les points de terminaison de documentation interactive (Swagger UI, ReDoc et Schéma OpenAPI), assurez-vous qu'ils sont inclus dans votre routage, normalement fait dans votre `urls.py` principal :

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns = [
    # ... vos autres urls
    path(f'{api_prefix}/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{api_prefix}/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{api_prefix}/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

Une fois configuré, démarrez votre serveur :

```bash
python manage.py runserver

# Swagger UI : http://localhost:8000/api/v1/docs/
# ReDoc :      http://localhost:8000/api/v1/docs/redoc/
# Schéma :     http://localhost:8000/api/v1/docs/schema/
```

- [**Site Statique**](docs_site/index.html) — Documentation complète
- [**Collection Postman**](tenxyte_api_collection.postman_collection.json) — Collection prête à l'emploi
- [**Référence des Points de Terminaison**](docs/fr/endpoints.md) — Tous les points de terminaison avec exemples curl

### Aperçu des Points de Terminaison

| Catégorie | Points de terminaison clés |
|---|---|
| **Auth** | `register`, `login/email`, `login/phone`, `refresh`, `logout`, `logout/all` |
| **Social** | `social/google`, `social/github`, `social/microsoft`, `social/facebook` |
| **Magic Link** | `magic-link/request`, `magic-link/verify` |
| **Passkeys** | `webauthn/register/begin+complete`, `webauthn/authenticate/begin+complete` |
| **OTP** | `otp/request`, `otp/verify/email`, `otp/verify/phone` |
| **Mot de passe** | `password/reset/request`, `password/reset/confirm`, `password/change` |
| **2FA** | `2fa/setup`, `2fa/confirm`, `2fa/disable`, `2fa/backup-codes` |
| **Profil** | `me/`, `me/roles/` |
| **RBAC** | `roles/`, `permissions/`, `users/{id}/roles/`, `users/{id}/permissions/` |
| **Applications** | `applications/` (CRUD + régénération) |

---

## 📚 Structure de la Documentation

### 📖 **Guides Développeur**
- [**Démarrage Rapide**](docs/fr/quickstart.md) - Commencez en 2 minutes avec Django
- [**Démarrage Rapide FastAPI**](docs/en/fastapi_quickstart.md) - Commencez avec FastAPI (en anglais)
- [**Référence des Paramètres**](docs/fr/settings.md) - Plus de 95 options de configuration
- [**Points de Terminaison API**](docs/fr/endpoints.md) - Référence complète avec exemples
- [**Comptes Administrateurs**](docs/fr/admin.md) - Gérer les Superutilisateurs et Admins RBAC
- [**Guide des Applications**](docs/fr/applications.md) - Gérer les clients API et identifiants
- [**Guide RBAC**](docs/fr/rbac.md) - Rôles, permissions et décorateurs
- [**Guide de Sécurité**](docs/fr/security.md) - Fonctionnalités et bonnes pratiques
- [**Guide des Organisations**](docs/fr/organizations.md) - Configuration B2B multi-tenant
- [**Guide AIRS**](docs/fr/airs.md) - Responsabilité et Sécurité de l'IA
- [**Guide de Migration**](docs/fr/MIGRATION_GUIDE.md) - Migration depuis dj-rest-auth, simplejwt

### 🔧 **Documentation Technique**
- [**Guide d'Architecture**](docs/fr/architecture.md) - Architecture Core & Adaptateurs (Hexagonale)
- [**Guide Async**](docs/en/async_guide.md) - Patterns async/await et bonnes pratiques (en anglais)
- [**Service de Tâches**](docs/fr/task_service.md) - Traitement des tâches en arrière-plan
- [**Guide des Adaptateurs Personnalisés**](docs/fr/custom_adapters.md) - Créer des adaptateurs personnalisés
- [**Référence des Schémas**](docs/fr/schemas.md) - Composants de schémas réutilisables
- [**Guide de Test**](docs/fr/TESTING.md) - Stratégies de test et exemples
- [**Tâches Périodiques**](docs/fr/periodic_tasks.md) - Maintenance planifiée et tâches de nettoyage
- [**Dépannage**](docs/fr/troubleshooting.md) - Problèmes courants et solutions
- [**Contribution**](docs/fr/CONTRIBUTING.md) - Comment contribuer à Tenxyte

---

## 📊 Métriques de Qualité de la Documentation

| Métrique | Valeur | Statut |
|--------|-------|--------|
| Couverture API | 100% | ✅ Complète |
| Score de Qualité | 100/100 | ✅ Parfait |
| Réduction taille Schéma | 3% | ✅ Optimisé |
| Nombre d'Exemples | 280+ | ✅ Exhaustif |
| Couverture Codes Erreur | 100% | ✅ Complète |
| Documentation Multi-tenant | 100% | ✅ Complète |

---

## 🛠️ Scripts de Documentation

### Outils de Validation
```bash
# Valider la spécification OpenAPI
python scripts/validate_openapi_spec.py

# Vérifier la couverture de la documentation
python scripts/validate_documentation.py

# Optimiser les performances des schémas
python scripts/optimize_schemas.py
```

### Outils de Génération
```bash
# Générer la collection Postman
python scripts/generate_postman_collection.py

# Générer le site de documentation statique
python scripts/generate_docs_site.py
```

Voir la [Documentation des Scripts](https://github.com/tenxyte/tenxyte/blob/main/scripts/README.md) pour le guide d'utilisation complet.

---

## Architecture : Core et Adaptateurs

Tenxyte est construit autour d'un **Core agnostique au framework** utilisant une architecture Ports et Adaptateurs (Hexagonale).

- **Core** : Contient la logique pure Python d'authentification, JWT et RBAC (zéro dépendance au framework).
- **Ports** : Définit les interfaces abstraites pour les opérations externes (ex: Repositories, EmailServices, CacheServices).
- **Adaptateurs** : Implémentations concrètes adaptées aux frameworks (Django, FastAPI) ou aux bibliothèques.

Cette conception garantit que les déploiements Django existants fonctionnent avec **zéro changement cassant**, tout en ouvrant nativement le support pour les frameworks asynchrones modernes comme FastAPI.

En savoir plus dans notre **[Guide d'Architecture](docs/fr/architecture.md)** détaillé.

---

## Bases de Données Supportées

- ✅ **SQLite** — développement
- ✅ **PostgreSQL** — recommandé pour la production
- ✅ **MySQL/MariaDB**
- ✅ **MongoDB** — via `django-mongodb-backend`

### MongoDB — Configuration Requise

```bash
pip install tenxyte[mongodb]
```

```python
# settings.py
AUTH_USER_MODEL = 'tenxyte.User'
DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'NAME': 'tenxyte_db',
        'HOST': 'localhost',
        'PORT': 27017,
    }
}

# Désactiver les migrations natives (les PK entiers sont incompatibles avec ObjectId)
MIGRATION_MODULES = {
    'contenttypes': None,
    'auth': None,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'tenxyte.middleware.CORSMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ❌ Retirer : 'django.contrib.auth.middleware.AuthenticationMiddleware'
    'django.contrib.messages.middleware.MessageMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]
```

#### MongoDB — Support Django Admin

Pour utiliser Django Admin avec MongoDB, remplacez les entrées admin/auth/contenttypes par défaut par des configurations personnalisées qui définissent `ObjectIdAutoField`.

**Étape 1 — `apps.py` de votre application principale :**

```python
from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig

class MongoAdminConfig(AdminConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
```

**Étape 2 — `INSTALLED_APPS` :**

```python
INSTALLED_APPS = [
    # Remplacez les trois valeurs par défaut de Django par vos versions MongoDB :
    'config.apps.MongoAdminConfig',       # remplace 'django.contrib.admin'
    'config.apps.MongoAuthConfig',        # remplace 'django.contrib.auth'
    'config.apps.MongoContentTypesConfig', # remplace 'django.contrib.contenttypes'

    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'tenxyte',
]
```

> Remplacez `config` par le nom de votre application Django principale. Ensuite, exécutez `python manage.py makemigrations && python manage.py migrate` — Django Admin fonctionnera correctement avec MongoDB.

---

## Maintenance Périodique

Tenxyte nécessite quelques tâches périodiques pour maintenir les performances et la sécurité. Configurez **Celery Beat** ou un job *cron* standard :

1. **Nettoyage des jetons** (Quotidien à 3h du matin)
   Supprimer les jetons JWT sur liste noire et les jetons de rafraîchissement/agent expirés :
   ```python
   from tenxyte.models import BlacklistedToken, RefreshToken, AgentToken
   BlacklistedToken.cleanup_expired()
   # Ajoutez une logique similaire pour les jetons Refresh/Agent basée sur expires_at
   ```

2. **Purge OTP et WebAuthn** (Toutes les 15 minutes)
   Effacer les codes OTP expirés et les défis WebAuthn inutilisés :
   ```python
   from tenxyte.models import OTPCode, WebAuthnChallenge
   OTPCode.cleanup_expired()
   WebAuthnChallenge.cleanup_expired()
   ```

3. **Rotation des journaux d'audit** (Mensuel)
   Pour se conformer au RGPD, archivez ou supprimez les anciens journaux :
   ```python
   from django.utils import timezone
   from datetime import timedelta
   from tenxyte.models import AuditLog
   
   cutoff = timezone.now() - timedelta(days=90)
   AuditLog.objects.filter(timestamp__lt=cutoff).delete()
   ```

---

## Personnalisation et Extension

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

Même pattern pour `TENXYTE_ROLE_MODEL`, `TENXYTE_PERMISSION_MODEL`, `TENXYTE_APPLICATION_MODEL`. Héritez toujours du `Meta` parent et définissez un `db_table` personnalisé.

### Création d'Adaptateurs de Framework Personnalisés

Puisque Tenxyte est agnostique au framework, vous pouvez écrire vos propres adaptateurs de base de données, de cache ou d'e-mail en utilisant les `Ports` du core. Voir le **[Guide des Adaptateurs Personnalisés](docs/fr/custom_adapters.md)** pour des instructions détaillées sur l'extension du core.

---

## Référence de Configuration

Plus de 115 paramètres documentés dans [docs/fr/settings.md](docs/fr/settings.md).

Options utiles pour le développement :

```python
TENXYTE_APPLICATION_AUTH_ENABLED = False  # désactive la vérification X-Access-Key
TENXYTE_RATE_LIMITING_ENABLED = False
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = False          # test uniquement
```

---

## Développement et Tests

```bash
git clone https://github.com/tenxyte/tenxyte.git
pip install -e ".[dev]"
pytest                               # 1553 tests, taux de réussite de 100%
pytest --cov=tenxyte --cov-report=html
```

**Tests Multi-DB** (nécessite un serveur en cours d'exécution par backend) :

```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mysql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

---

## Questions Fréquemment Posées et Dépannage

**`MongoDB ne supporte pas AutoField/BigAutoField`**
→ Configurez `DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'` et ajoutez `MIGRATION_MODULES = {'contenttypes': None, 'auth': None}`. Pour Django Admin, utilisez les configs d'applications personnalisées décrites dans la [section Admin MongoDB](#mongodb--support-django-admin).

**`Model instances without primary key value are unhashable`**
→ Même correctif (`MIGRATION_MODULES`). Si cela persiste, déconnectez les signaux `post_migrate` pour `create_permissions` et `create_contenttypes`.

**`ModuleNotFoundError: No module named 'rest_framework'`**
→ `pip install djangorestframework`

**401 Unauthorized / JWT ne fonctionne pas**
→ Assurez-vous que les trois en-têtes sont présents : `X-Access-Key`, `X-Access-Secret`, `Authorization: Bearer <token>`.

**`No module named 'corsheaders'`**
→ Tenxyte inclut un middleware CORS intégré (`tenxyte.middleware.CORSMiddleware`). Retirez `corsheaders` de votre configuration.

---

## 🎯 Standards de Documentation

### Exigences de Qualité
- ✅ **Couverture à 100%** - Tous les points de terminaison documentés
- ✅ **Exemples Fonctionnels** - Tous les exemples testés et opérationnels
- ✅ **Gestion des Erreurs** - Documentation complète des erreurs
- ✅ **Support Multi-tenant** - Documentation B2B complète
- ✅ **Sécurité** - Confidentialité et sécurité documentées

### Standards de Maintenance
- 🔄 **Mises à jour Régulières** - Garder la documentation synchronisée
- 🧪 **Tests Automatisés** - Validation continue
- 📊 **Suivi Qualité** - Suivi des métriques et améliorations
- 🔧 **Mises à jour des Outils** - Maintenir les outils de validation et génération
- 📚 **Retours Utilisateurs** - Intégrer les retours des développeurs

---

## Contribution

Les contributions sont les bienvenues ! Quelques règles simples :

1. Ouvrez un ticket avant toute demande de fonctionnalité majeure.
2. Fork → branche `feature/xxx` → PR avec tests et changelog.
3. Respectez les conventions de commit et ajoutez des tests unitaires.

Voir [docs/fr/CONTRIBUTING.md](docs/fr/CONTRIBUTING.md) pour plus de détails.

## Licence

MIT — voir [LICENSE](LICENSE).

## Support

- 📖 [Documentation](https://tenxyte.readthedocs.io)
- 🐛 [Traqueur de tickets](https://github.com/tenxyte/tenxyte/issues)
- 💬 [Discussions](https://github.com/tenxyte/tenxyte/discussions)

## Changelog

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique des versions.
