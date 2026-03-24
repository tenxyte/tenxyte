![# TENXYTE • AI-Ready Backend Framework](https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/baniere_github.jpg)

# Tenxyte Auth

> Authentification Python indépendante du framework en quelques minutes — JWT, RBAC, 2FA, Liens Magiques, Passkeys, Connexion Sociale, Vérification de Fuites, Organisations (B2B), support multi-application.

[![PyPI version](https://badge.fury.io/py/tenxyte.svg)](https://badge.fury.io/py/tenxyte)
[![Python versions](https://img.shields.io/pypi/pyversions/tenxyte.svg)](https://pypi.org/project/tenxyte/)
[![Django versions](https://img.shields.io/badge/django-6.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://codecov.io/gh/tenxyte/tenxyte/graph/badge.svg)](https://codecov.io/gh/tenxyte/tenxyte)
[![Tests](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml/badge.svg)](https://github.com/tenxyte/tenxyte/actions/workflows/ci.yml)

---

## Démarrage Rapide — 2 minutes pour votre premier appel API

### 1. Installation

```bash
pip install tenxyte
```

> **Prérequis :** Python 3.10+, Django 6.0+ ou FastAPI 0.135+

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
- 8 décorateurs + classes de permissions DRF

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
- [**Référence des Paramètres**](settings.md) - Toutes les 95+ options de configuration
- [**Endpoints de l'API**](endpoints.md) - Référence complète des endpoints avec exemples
- [**Comptes Admin**](admin.md) - Gérer les Super-utilisateurs et les Admins RBAC
- [**Guide des Applications**](applications.md) - Gérer les clients API et les identifiants
- [**Guide RBAC**](rbac.md) - Rôles, permissions et décorateurs
- [**Guide de Sécurité**](security.md) - Fonctionnalités de sécurité et bonnes pratiques
- [**Guide des Organisations**](organizations.md) - Configuration B2B multi-tenant
- [**Guide AIRS**](airs.md) - Responsabilité et Sécurité de l'IA
- [**Guide de Migration**](MIGRATION_GUIDE.md) - Migration depuis dj-rest-auth, simplejwt

### 🔧 **Documentation Technique**
- [**Guide d'Architecture**](architecture.md) - Architecture Core & Adapters (Hexagonale)
- [**Guide Async**](async_guide.md) - Modèles async/await et bonnes pratiques
- [**Service de Tâches**](task_service.md) - Traitement des tâches en arrière-plan
- [**Guide des Adaptateurs Personnalisés**](custom_adapters.md) - Création d'adaptateurs personnalisés
- [**Référence des Schémas**](schemas.md) - Composants de schéma réutilisables
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
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mysql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
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
