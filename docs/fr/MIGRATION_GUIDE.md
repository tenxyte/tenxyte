# Guide de Migration

Ce guide vous aide à migrer des bibliothèques d'authentification Django courantes vers Tenxyte.

## Table des Matières

- [Migration de Tenxyte v0.9.x vers v0.9.3 (Réarchitecture du Cœur)](#migration-de-tenxyte-v09x-vers-v093-rearchitecture-du-coeur)
- [Migration depuis `djangorestframework-simplejwt`](#migration-depuis-djangorestframework-simplejwt)
  - [Correspondance des Paramètres](#correspondance-des-parametres)
  - [Classe d'Authentification](#classe-dauthentification)
  - [Migration des URLs](#migration-des-urls)
  - [Compatibilité du Format des Jetons](#compatibilite-du-format-des-jetons)
  - [Migration du Modèle Utilisateur](#migration-du-modele-utilisateur)
- [Migration depuis `dj-rest-auth`](#migration-depuis-dj-rest-auth)
  - [Correspondance des Points de Terminaison](#correspondance-des-points-de-terminaison)
  - [Changements de Format de Réponse](#changements-de-format-de-reponse)
- [Migration depuis une Implémentation d'Authentification Personnalisée](#migration-depuis-une-implementation-dauthentification-personnalisee)
  - [Étape 1 — Préserver les utilisateurs existants](#etape-1--preserver-les-utilisateurs-existants)
  - [Étape 2 — Migrer les rôles et permissions](#etape-2--migrer-les-roles-et-permissions)
  - [Étape 3 — Mettre à jour les en-têtes du frontend](#etape-3--mettre-a-jour-les-en-tetes-du-frontend)
- [Liste de Contrôle des Changements Majeurs](#liste-de-controle-des-changements-majeurs)
- [Besoin d'aide ?](#besoin-daide)

---

## Migration de Tenxyte v0.9.x vers v0.9.3 (Réarchitecture du Cœur)

Tenxyte v0.9.3 introduit un changement majeur d'architecture sous-jacente : la logique métier a été extraite dans un paquet `tenxyte.core` indépendant du framework. Cependant, pour les projets Django existants, cette mise à jour est conçue pour avoir **zéro changement majeur (breaking changes)**.

### Ce que vous devez savoir

1. **Aucun changement dans `settings.py`** : Tous vos paramètres `TENXYTE_*` actuels continueront de fonctionner exactement comme avant. Le nouvel Adaptateur Django lit `django.conf.settings` et les transmet automatiquement au Cœur.
2. **Aucun changement aux Modèles ou à la Base de données** : Le schéma de base de données de Tenxyte reste strictement identique. Vous n'avez **pas** besoin d'exécuter `makemigrations` ou `migrate` lors de la mise à jour.
3. **Aucun changement aux Points de Terminaison de l'API** : Toutes les URLs, les charges utiles de requête JSON et les réponses JSON restent exactement les mêmes.
4. **Aucun changement aux Jetons** : Les JWT, jetons de rafraîchissement (Refresh Tokens) et clés d'accès (Passkeys) existants continueront de fonctionner sans aucune interruption.

### Comment effectuer la mise à jour

Mettez simplement à jour le paquet via pip :

```bash
pip install tenxyte==0.9.3
```

*(Si vous utilisez des extras spécifiques comme Twilio ou SendGrid, vous souhaiterez peut-être passer à la nouvelle syntaxe hiérarchique des extras, bien que le `pip install tenxyte` par défaut continue d'installer la pile Django complète.)*

```bash
pip install "tenxyte[django,twilio]"
```

### Avertissements d'Obsolescence (Deprecation Warnings)

Bien que votre code continuera de fonctionner, certains imports internes profonds ont été déplacés structurellement. Par exemple, si vous importiez directement des Services au lieu d'utiliser les points de terminaison REST, vous pourriez voir des `DeprecationWarning`.

```python
# Ancien import (fonctionne toujours en v0.9.3 mais génère un DeprecationWarning)
from tenxyte.services.auth_service import AuthService

# Recommandé : utilisez les services tenxyte.core avec des adaptateurs à la place
from tenxyte.core.jwt_service import JWTService
```

Ces alias d'importation seront conservés jusqu'à la v1.0.0, vous laissant amplement le temps de mettre à jour vos surcharges personnalisées.

---

## Migration depuis `djangorestframework-simplejwt`

### Correspondance des Paramètres

| simplejwt | Tenxyte | Notes |
|---|---|---|
| `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']` | `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | En secondes (pas `timedelta`) |
| `SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']` | `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | En secondes |
| `SIMPLE_JWT['ROTATE_REFRESH_TOKENS']` | `TENXYTE_REFRESH_TOKEN_ROTATION` | Booléen |
| `SIMPLE_JWT['BLACKLIST_AFTER_ROTATION']` | `TENXYTE_TOKEN_BLACKLIST_ENABLED` | Booléen |
| `SIMPLE_JWT['SIGNING_KEY']` | `TENXYTE_JWT_SECRET_KEY` | Chaîne de caractères |
| `SIMPLE_JWT['AUTH_HEADER_TYPES']` | Toujours `Bearer` | Fixé dans Tenxyte |
| `SIMPLE_JWT['USER_ID_FIELD']` | Toujours `id` (Entier/Chaîne) | Fixé dans Tenxyte |

### Classe d'Authentification

```python
# Avant (simplejwt)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# Après (Tenxyte)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}
```

### Migration des URLs

```python
# Avant (simplejwt)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]

# Après (Tenxyte)
urlpatterns = [
    path('api/auth/', include('tenxyte.urls')),
    # Connexion : POST /api/auth/login/email/
    # Rafraîchissement : POST /api/auth/refresh/
]

> **Note** : L'URL exacte dépend de l'endroit où vous montez `tenxyte.urls` dans votre `urls.py`. Si vous avez configuré `path('api/v1/auth/', include('tenxyte.urls'))`, les points de terminaison seront préfixés par `/api/v1/auth/`.
```

### Compatibilité du Format des Jetons

Les jetons Tenxyte ne sont **pas compatibles** avec les jetons simplejwt. Tous les jetons existants deviendront invalides après la migration. Prévoyez :

1. Une fenêtre de maintenance ou une période de grâce où les deux systèmes fonctionnent en parallèle.
2. Une ré-authentification côté client après la fenêtre de migration.

### Migration du Modèle Utilisateur

Si votre modèle utilisateur personnalisé n'incluait que des champs que Tenxyte gère déjà (ex: `phone`, `first_name`, `last_name`), vous pouvez passer au modèle par défaut de Tenxyte :

```python
# Avant
from django.contrib.auth.models import AbstractUser

class MyUser(AbstractUser):
    phone = models.CharField(...)

# Après — L'utilisateur de Tenxyte inclut déjà le téléphone, la 2FA, etc.
# Défini dans settings.py :
AUTH_USER_MODEL = 'tenxyte.User'
```

Si votre modèle utilisateur personnalisé incluait des **champs spécifiques au projet** (ex: `company`, `avatar`), vous devez étendre l'`AbstractUser` de Tenxyte :

```python
# Après — Étendre l'AbstractUser de Tenxyte
from tenxyte.models import AbstractUser

class MyUser(AbstractUser):
    company = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'

# Défini dans settings.py :
TENXYTE_USER_MODEL = 'myapp.MyUser'
AUTH_USER_MODEL = 'myapp.MyUser'  # Défini également pour Django
```

Après avoir mis à jour vos modèles et paramètres, exécutez :
```bash
python manage.py makemigrations --empty myapp --name migrate_to_tenxyte_user
python manage.py migrate
```

---

## Migration depuis `dj-rest-auth`

### Correspondance des Points de Terminaison

| Point de terminaison dj-rest-auth | Équivalent Tenxyte (en supposant `path('api/v1/auth/', ...)` dans votre `urls.py`) |
|---|---|
| `POST /auth/login/` | `POST /api/v1/auth/login/email/` |
| `POST /auth/logout/` | `POST /api/v1/auth/logout/` |
| `POST /auth/registration/` | `POST /api/v1/auth/register/` |
| `POST /auth/password/change/` | `POST /api/v1/auth/password/change/` |
| `POST /auth/password/reset/` | `POST /api/v1/auth/password/reset/request/` |
| `POST /auth/password/reset/confirm/` | `POST /api/v1/auth/password/reset/confirm/` |
| `GET /auth/user/` | `GET /api/v1/auth/me/` |
| `PUT /auth/user/` | `PUT /api/v1/auth/me/` |

### Changements de Format de Réponse

dj-rest-auth renvoie les jetons à l'intérieur d'un champ `key` (Knox) ou `access`/`refresh` (adaptateur JWT). Tenxyte renvoie toujours une charge utile détaillée :

```json
{
  "access_token": "<jeton d'accès>",
  "refresh_token": "<jeton de rafraîchissement>",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 604800,
  "user": { ... },
  "requires_2fa": false,
  "session_id": "...",
  "device_id": "..."
}
```

Mettez à jour la gestion des jetons de votre frontend en conséquence (en vous concentrant sur les clés `access_token` et `refresh_token`).

---

## Migration depuis une Implémentation d'Authentification Personnalisée

### Étape 1 — Préserver les utilisateurs existants

Le modèle `User` de Tenxyte utilise des clés primaires standard (généralement des entiers) et stocke les mots de passe à l'aide de bcrypt avec un pré-hachage SHA-256. Les mots de passe existants hachés avec bcrypt provenant du hachoir PBKDF2 par défaut de Django **ne fonctionneront pas** directement.

Option A — Forcer la réinitialisation du mot de passe pour tous les utilisateurs :
```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.all().update(password='!')  # invalide tous les mots de passe
"
```
Ensuite, déclenchez un e-mail de réinitialisation de mot de passe en masse depuis votre panneau d'administration.

Option B — Implémenter un hachoir de migration unique qui accepte PBKDF2 lors de la première connexion et ré-hache avec bcrypt de manière transparente (recommandé pour les migrations sans temps d'arrêt).

### Étape 2 — Migrer les rôles et permissions

Si vous aviez des groupes/permissions personnalisés, mappez-les aux rôles RBAC de Tenxyte en utilisant la méthode `assign_role()` sur le modèle utilisateur :

```python
# commande de gestion ou script shell
from tenxyte.models import get_user_model, get_role_model

User = get_user_model()
Role = get_role_model()

# S'assurer que le rôle existe
Role.objects.get_or_create(code='admin', defaults={'name': 'Admin'})

# Assigner le rôle à un utilisateur
for user in User.objects.all():
    user.assign_role('admin')  # utilise le code du rôle, pas le nom
```

Consultez le [Guide RBAC](rbac.md) pour le modèle complet de rôles/permissions.

### Étape 3 — Mettre à jour les en-têtes du frontend

Tenxyte utilise `Authorization: Bearer <token>` pour JWT. Si vous utilisiez des cookies de session ou des en-têtes personnalisés, mettez à jour votre client HTTP frontend.

```http
Authorization: Bearer <access_token>
```

---

## Liste de Contrôle des Changements Majeurs

- [ ] `AUTH_USER_MODEL` remplacé par `tenxyte.User`
- [ ] Tous les jetons JWT existants sont invalidés
- [ ] Les hachages de mots de passe peuvent nécessiter une réinitialisation si vous migrez depuis PBKDF2
- [ ] Les URLs des points de terminaison ont changé (voir les tableaux de correspondance ci-dessus)
- [ ] Le format de réponse pour la connexion a changé (pas de champ `key`, utilisez les clés `access_token`/`refresh_token`)
- [ ] Les groupes/permissions personnalisés doivent être migrés vers les rôles RBAC de Tenxyte

---

## Besoin d'aide ?

- [Référence des Paramètres](settings.md) — toutes les options de configuration
- [Guide RBAC](rbac.md) — rôles et permissions
- [Guide de Sécurité](security.md) — renforcement de la sécurité après migration
- [Dépannage](troubleshooting.md) — erreurs courantes post-migration
