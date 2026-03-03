# Quickstart — Tenxyte en 2 minutes

## 1. Install

```bash
pip install tenxyte
```

## 2. Configure `settings.py`

```python
# settings.py — ajoutez ces 2 lignes
import tenxyte
tenxyte.setup()  # auto-configure INSTALLED_APPS, AUTH_USER_MODEL, REST_FRAMEWORK, MIDDLEWARE
```

Puis ajoutez les URLs :

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('tenxyte.urls')),
]
```

## 3. Bootstrap

```bash
python manage.py tenxyte_quickstart
```

Cette commande unique exécute :
- `makemigrations` + `migrate`
- Seed des rôles et permissions (4 rôles, 41 permissions)
- Création d'une Application par défaut (credentials affichés)

## ✅ Prêt !

En mode `DEBUG=True` (zero-config), le preset `development` s'active automatiquement :
- Pas besoin de `TENXYTE_JWT_SECRET_KEY` (clé éphémère auto-générée)
- Pas besoin d'Application credentials (X-Access-Key désactivé)
- Rate limiting, lockout, et sécurité de base activés

```bash
# Votre première requête — aucun header spécial requis en dev !
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss1!", "first_name": "John", "last_name": "Doe"}'
```

---

## Production

En production (`DEBUG=False`), configurez explicitement :

```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'your-dedicated-jwt-secret-key'  # OBLIGATOIRE
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # ou 'robust'

# Si Application auth est nécessaire (recommandé) :
# TENXYTE_APPLICATION_AUTH_ENABLED = True  # déjà True par défaut hors dev preset
```

Tous les settings individuels restent overridables :

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'
TENXYTE_MAX_LOGIN_ATTEMPTS = 3       # override le preset
TENXYTE_BREACH_CHECK_ENABLED = True  # override le preset
```

→ [Settings Reference](settings.md) pour les 150+ options.

---

## Configuration manuelle (alternative)

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

Puis exécutez :

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py tenxyte_seed
```

---

## MongoDB

Pour MongoDB, voir la [configuration MongoDB](#mongodb--required-configuration) dans le README.

---

## Next Steps

- [Settings Reference](settings.md) — 150+ options de configuration
- [API Endpoints](endpoints.md) — Référence complète avec exemples curl
- [RBAC Guide](rbac.md) — Rôles, permissions, décorateurs
- [Security Guide](security.md) — Rate limiting, 2FA, device fingerprinting
- [Organizations Guide](organizations.md) — Config multi-tenant B2B
