# Démarrage Rapide — Tenxyte en 2 minutes

## Table des Matières

- [Installation](#1-installation)
- [Configuration](#2-configuration-settingspy)
- [Initialisation](#3-initialisation)
- [Prêt !](#-pret)
- [Connexion et Utilisation du JWT](#4-connexion--utilisation-de-votre-jwt)
- [Production](#production)
- [Configuration Manuelle](#configuration-manuelle-alternative)
- [MongoDB](#mongodb)
- [Étapes Suivantes](#etapes-suivantes)

---

## 1. Installation

```bash
pip install tenxyte
```

## 2. Configuration du fichier `settings.py`

```python
# settings.py — Ajoutez ceci à la FIN du fichier (après INSTALLED_APPS, MIDDLEWARE, etc.)
import tenxyte
tenxyte.setup(globals())

# `tenxyte.setup(globals())` injecte automatiquement la configuration minimale requise :
# - Définit AUTH_USER_MODEL = 'tenxyte.User'
# - Ajoute 'rest_framework' et 'tenxyte' à INSTALLED_APPS
# - Configure DEFAULT_AUTHENTICATION_CLASSES et DEFAULT_SCHEMA_CLASS pour REST_FRAMEWORK
# - Ajoute 'tenxyte.middleware.ApplicationAuthMiddleware' à MIDDLEWARE
# Note : Cette fonction n'écrasera JAMAIS les paramètres que vous avez déjà explicitement définis.
```

### Comprendre `tenxyte.setup()` VS `tenxyte.setup(globals())`
Par défaut, l'appel à `tenxyte.setup()` tentera de trouver le module de paramètres Django et de modifier ses propriétés. Cependant, à l'intérieur de votre fichier `settings.py`, les variables standard que vous venez de définir (comme `INSTALLED_APPS` ou `MIDDLEWARE`) pourraient ne pas encore être totalement chargées dans le registre des modules.

Passer `globals()` indique à Tenxyte de modifier directement le dictionnaire local de variables dans votre `settings.py`. **C'est l'approche recommandée et la plus sûre**, car elle garantit strictement que vos dictionnaires `INSTALLED_APPS`, `MIDDLEWARE` et `REST_FRAMEWORK` sont complétés proprement sans risque de problèmes de résolution de module. Placez toujours cet appel tout en **bas** de votre fichier `settings.py`.

Ajoutez ensuite les URLs :

```python
# urls.py
from django.urls import path, include
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'{api_prefix}/auth/', include('tenxyte.urls')),
]
```

## 3. Initialisation

```bash
python manage.py tenxyte_quickstart
```

Cette commande unique exécute :
- `makemigrations` + `migrate`
- L'injection des rôles et des permissions (4 rôles, 47 permissions)
- La création d'une Application par défaut (identifiants affichés)

**Options :**

| Option | Description |
|---|---|
| `--no-seed` | Ignorer l'injection des rôles et des permissions |
| `--no-app` | Ignorer la création de l'Application par défaut |
| `--app-name "Mon App"` | Nom personnalisé pour l'Application par défaut |

## 4. Créer un Compte Administrateur

Certaines fonctionnalités et vues (comme le panneau d'administration Django ou la configuration RBAC) nécessitent un compte administrateur. Vous pouvez créer votre super-utilisateur initial à l'aide de la commande standard de Django :

```bash
python manage.py createsuperuser
```

Suivez les instructions pour définir votre e-mail et votre mot de passe. Ce compte est créé avec `is_staff=True` et `is_superuser=True`, vous accordant un accès complet à tous les points de terminaison, y compris l'interface intégrée `http://localhost:8000/admin/`.

## ✅ Prêt !

En mode `DEBUG=True` (zéro-config), le préréglage `development` est automatiquement activé :
- Pas besoin de `TENXYTE_JWT_SECRET_KEY` (clé éphémère auto-générée)
- Les identifiants d'Application (`X-Access-Key` / `X-Access-Secret`) sont **obligatoires** — utilisez les identifiants affichés par `tenxyte_quickstart`
- Limitation du débit, verrouillage et sécurité de base activés

> **Note :** Le secret d'accès (Access Secret) est haché avec bcrypt et n'est affiché **qu'une seule fois** lors de l'initialisation.
> En cas de perte, régénérez les identifiants via `POST /api/v1/auth/applications/{id}/regenerate/`.

```bash
# Enregistrez votre premier utilisateur — utilisez les identifiants de tenxyte_quickstart
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <votre-access-key>" \
  -H "X-Access-Secret: <votre-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

## 4. Connexion et Utilisation de votre JWT

```bash
# Connexion
curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <votre-access-key>" \
  -H "X-Access-Secret: <votre-access-secret>" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!"}'
```

Réponse :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "a1b2c3d4e5...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "1",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_2fa_enabled": false
  }
}
```

```bash
# Utilisez le jeton d'accès pour les requêtes authentifiées
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Access-Key: <votre-access-key>" \
  -H "X-Access-Secret: <votre-access-secret>"
```

---

## Production

En production (`DEBUG=False`), configurez explicitement :

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'votre-cle-secrete-jwt-dediee'  # OBLIGATOIRE
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # ou 'robust'
```

Tous les paramètres individuels restent modifiables :

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'
TENXYTE_MAX_LOGIN_ATTEMPTS = 3       # écrase le préréglage
TENXYTE_BREACH_CHECK_ENABLED = True  # écrase le préréglage
```

→ [Référence des Paramètres](settings.md) pour les plus de 115 options.

---

## Configuration Manuelle (Alternative)

Si vous préférez ne pas utiliser `tenxyte.setup()` :

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'tenxyte',
]

AUTH_USER_MODEL = 'tenxyte.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}

MIDDLEWARE = [
    ...,
    'tenxyte.middleware.ApplicationAuthMiddleware',
]
```

Ensuite, lancez :

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py tenxyte_seed
```

---

## MongoDB

Pour MongoDB, consultez la section [Configuration de MongoDB](#mongodb--required-configuration) dans le README.

---

## Étapes Suivantes

- [Référence des Paramètres](settings.md) — Plus de 115 options de configuration
- [Points de Terminaison de l'API](endpoints.md) — Référence complète avec exemples curl
- [Guide RBAC](rbac.md) — Rôles, permissions, décorateurs
- [Guide de Sécurité](security.md) — Limitation de débit, 2FA, empreinte numérique de l'appareil
- [Guide des Organisations](organizations.md) — Configuration multi-tenant B2B
