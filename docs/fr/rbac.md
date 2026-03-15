# Guide RBAC — Rôles, Permissions et Décorateurs

Tenxyte fournit un système de contrôle d'accès basé sur les rôles (RBAC) flexible avec :
- **Permissions** — capacités atomiques (ex: `posts.publish`, `users.ban`)
- **Rôles** — groupes de permissions nommés avec une hiérarchie optionnelle
- **Décorateurs** — protégez vos vues avec une seule ligne de code

## Table des Matières

- [Concepts](#concepts)
  - [Permissions](#permissions)
  - [Hiérarchie des Permissions](#hierarchie-des-permissions)
  - [Rôles](#roles)
  - [Ordre de Résolution des Permissions](#ordre-de-resolution-des-permissions)
- [Méthodes RBAC de l'Utilisateur](#methodes-rbac-de-lutilisateur)
- [Décorateurs](#decorateurs)
  - [`@require_permission`](#require_permission)
  - [`@require_any_permission`](#require_any_permission)
  - [`@require_all_permissions`](#require_all_permissions)
  - [`@require_role`](#require_role)
  - [`@require_any_role`](#require_any_role)
  - [`@require_all_roles`](#require_all_roles)
  - [`@require_jwt`](#require_jwt)
  - [`@require_verified_email`](#require_verified_email)
  - [`@require_verified_phone`](#require_verified_phone)
- [Combinaison de Décorateurs](#combinaison-de-decorateurs)
- [Points de Terminaison d'API pour la Gestion RBAC](#points-de-terminaison-dapi-pour-la-gestion-rbac)
  - [Permissions](#permissions-1)
  - [Rôles](#roles-1)
  - [Rôles et Permissions des Utilisateurs](#roles-et-permissions-des-utilisateurs)
- [RBAC Étendu aux Organisations](#rbac-etendu-aux-organisations)
- [Rôles par Défaut](#roles-par-defaut)
- [Codes de Permission Intégrés](#codes-de-permission-integres)
- [Injection (Seeding) et Personnalisation](#injection-seeding-et-personnalisation)
  - [Commande `tenxyte_seed`](#commande-tenxyte_seed)
  - [Modèles Interchangeables](#modeles-interchangeables)

---

## Concepts

### Permissions

Une permission est un code textuel comme `users.view`, `posts.publish`, `billing.manage`.

```python
from tenxyte.models import Permission

# Création
perm = Permission.objects.create(code="posts.publish", name="Publier des articles")

# Attribution directe à un utilisateur
user.direct_permissions.add(perm)

# Vérification
user.has_permission("posts.publish")  # True
```

### Hiérarchie des Permissions

Les permissions prennent en charge les relations parent/enfant. Posséder une permission parente accorde automatiquement toutes ses permissions enfants.

```python
from tenxyte.models import Permission

# Créer une permission parente
content = Permission.objects.create(code="content", name="Tout le contenu")

# Créer des enfants — posséder "content" accorde les deux automatiquement
Permission.objects.create(code="content.edit", name="Modifier le contenu", parent=content)
Permission.objects.create(code="content.publish", name="Publier le contenu", parent=content)

# Un utilisateur avec le parent a tous les enfants
user.direct_permissions.add(content)
user.has_permission("content.edit")     # True (hérité du parent)
user.has_permission("content.publish")  # True (hérité du parent)
```

### Rôles

Un rôle regroupe plusieurs permissions. Chaque rôle possède un identifiant `code` unique.

```python
from tenxyte.models import Role

# Créer un rôle (le code est requis et doit être unique)
editor = Role.objects.create(code="editor", name="Éditeur", description="Peut éditer le contenu")
editor.permissions.add(Permission.objects.get(code="posts.edit"))

# Créer un autre rôle
publisher = Role.objects.create(code="publisher", name="Éditeur en chef", description="Peut publier le contenu")
publisher.permissions.add(Permission.objects.get(code="posts.publish"))

# Attribuer à l'utilisateur
user.roles.add(editor)

# Vérification
user.has_permission("posts.edit")    # True (via le rôle d'éditeur)
user.has_permission("posts.publish") # False (seul le rôle publisher l'a)
```

### Ordre de Résolution des Permissions

Lors de la vérification de `user.has_permission("x")`, Tenxyte vérifie :
1. Les **permissions directes** de l'utilisateur et les permissions issues des **rôles** de l'utilisateur (vérifiées ensemble en une seule requête).
2. La **hiérarchie des permissions** — si la permission a des ancêtres (via `parent`), vérifie si une permission ancêtre est attribuée à l'utilisateur.

---

## Méthodes RBAC de l'Utilisateur

Le modèle `User` fournit ces méthodes intégrées pour le RBAC :

### Méthodes de Permission

```python
# Vérification d'une seule permission (inclut rôles, direct et hiérarchie)
user.has_permission("posts.publish")             # bool

# Vérifications de plusieurs permissions
user.has_any_permission(["posts.edit", "posts.publish"])   # True si au moins une
user.has_all_permissions(["posts.edit", "posts.publish"])  # True si toutes

# Lister toutes les permissions effectives (rôles + direct + hiérarchie)
user.get_all_permissions()  # ['posts.edit', 'posts.publish', ...]
```

### Méthodes de Rôle

```python
# Vérifier les rôles
user.has_role("admin")                           # bool
user.has_any_role(["admin", "editor"])            # True si au moins un
user.has_all_roles(["admin", "editor"])           # True si tous

# Attribuer / retirer des rôles
user.assign_role("editor")    # True si attribué, False si rôle non trouvé
user.remove_role("editor")    # True si retiré, False si rôle non trouvé

# Lister tous les codes de rôles
user.get_all_roles()          # ['editor', 'viewer']

# Attribuer le rôle par défaut (celui avec is_default=True)
user.assign_default_role()
```

---

## Décorateurs

### `@require_permission`

Protège une méthode de vue — retourne un `403` si l'utilisateur n'a pas la permission.

```python
from tenxyte.decorators import require_permission

class PostPublishView(APIView):
    @require_permission('posts.publish')
    def post(self, request):
        ...
```

### `@require_any_permission`

Autorise l'accès si l'utilisateur possède **au moins une** des permissions listées.

```python
from tenxyte.decorators import require_any_permission

class ContentView(APIView):
    @require_any_permission(['posts.edit', 'posts.publish'])
    def get(self, request):
        ...
```

### `@require_all_permissions`

Autorise l'accès uniquement si l'utilisateur possède **toutes** les permissions listées.

```python
from tenxyte.decorators import require_all_permissions

class AdminView(APIView):
    @require_all_permissions(['users.view', 'users.manage'])
    def get(self, request):
        ...
```

### `@require_role`

Autorise l'accès uniquement si l'utilisateur possède un rôle spécifique (via son **code**, pas son nom).

```python
from tenxyte.decorators import require_role

class EditorView(APIView):
    @require_role('editor')
    def post(self, request):
        ...
```

### `@require_any_role`

Autorise l'accès si l'utilisateur possède **au moins un** des rôles listés.

```python
from tenxyte.decorators import require_any_role

class StaffView(APIView):
    @require_any_role(['admin', 'editor'])
    def get(self, request):
        ...
```

### `@require_all_roles`

Autorise l'accès uniquement si l'utilisateur possède **tous** les rôles listés.

```python
from tenxyte.decorators import require_all_roles

class SuperStaffView(APIView):
    @require_all_roles(['admin', 'editor'])
    def get(self, request):
        ...
```

### `@require_jwt`

Nécessite un jeton d'accès JWT valide. Retourne un `401` s'il est manquant ou invalide.

```python
from tenxyte.decorators import require_jwt

class ProtectedView(APIView):
    @require_jwt
    def get(self, request):
        # request.user est défini
        ...
```

### `@require_verified_email`

Nécessite que l'e-mail de l'utilisateur soit vérifié.

```python
from tenxyte.decorators import require_verified_email

class SensitiveView(APIView):
    @require_verified_email
    def post(self, request):
        ...
```

### `@require_verified_phone`

Nécessite que le numéro de téléphone de l'utilisateur soit vérifié. Inclut la validation JWT.

```python
from tenxyte.decorators import require_verified_phone

class PhoneRequiredView(APIView):
    @require_verified_phone
    def post(self, request):
        ...
```

---

## Combinaison de Décorateurs

Les décorateurs peuvent être empilés — ils sont appliqués de bas en haut :

```python
class AdminOnlyView(APIView):
    @require_permission('admin.access')
    @require_verified_email
    def get(self, request):
        ...
```

> **Note :** `@require_permission`, `@require_any_permission`, `@require_all_permissions`, `@require_role` et `@require_verified_email` incluent tous la validation JWT en interne — il n'est pas nécessaire d'ajouter `@require_jwt` explicitement lors de leur utilisation.

---

## Points de Terminaison d'API pour la Gestion RBAC

### Permissions

```bash
# Lister toutes les permissions
GET /api/v1/auth/permissions/

# Créer une permission
POST /api/v1/auth/permissions/
{ "code": "posts.publish", "name": "Publier des articles" }

# Obtenir / Mettre à jour / Supprimer
GET    /api/v1/auth/permissions/<id>/
PUT    /api/v1/auth/permissions/<id>/
DELETE /api/v1/auth/permissions/<id>/
```

### Rôles

```bash
# Lister tous les rôles
GET /api/v1/auth/roles/

# Créer un rôle
POST /api/v1/auth/roles/
{ "code": "editor", "name": "Éditeur", "description": "..." }

# Obtenir / Mettre à jour / Supprimer
GET    /api/v1/auth/roles/<id>/
PUT    /api/v1/auth/roles/<id>/
DELETE /api/v1/auth/roles/<id>/

# Gérer les permissions d'un rôle
GET  /api/v1/auth/roles/<id>/permissions/
POST /api/v1/auth/roles/<id>/permissions/
{ "permission_codes": ["posts.publish", "posts.edit"] }
```

### Rôles et Permissions des Utilisateurs

```bash
# Attribuer/retirer des rôles
GET    /api/v1/auth/users/<id>/roles/
POST   /api/v1/auth/users/<id>/roles/
DELETE /api/v1/auth/users/<id>/roles/

# Attribuer/retirer des permissions directes
GET    /api/v1/auth/users/<id>/permissions/
POST   /api/v1/auth/users/<id>/permissions/
DELETE /api/v1/auth/users/<id>/permissions/
```

---

## Attribution des Rôles Admin et Super-utilisateurs

Il existe deux manières principales d'accorder des privilèges administratifs dans Tenxyte :

### 1. Super-utilisateur Django (`is_superuser=True`)
Un super-utilisateur contourne automatiquement toutes les vérifications de permissions RBAC. Il a également accès à l'interface d'administration Django (`/admin/`).
Typiquement, vous créez votre premier super-utilisateur via la ligne de commande :

```bash
python manage.py createsuperuser
```

*Note : Les super-utilisateurs n'ont pas besoin de se voir attribuer explicitement les rôles RBAC `admin` ou `super_admin`.*

### 2. Rôles Admin RBAC (`super_admin` ou `admin`)
Ce sont des utilisateurs standards auxquels est attribué un rôle contenant des permissions de haut niveau. Ils n'ont pas accès au panneau d'administration Django (sauf si `is_staff=True`), mais ils ont des capacités administratives via l'API.

Pour attribuer un rôle Admin à un utilisateur existant via l'API :

```bash
POST /api/v1/auth/users/<user_id>/roles/
Authorization: Bearer <superuser_token>

{
  "role_codes": ["super_admin"]
}
```

Ou via le shell Python de Django :
```python
user = User.objects.get(email="manager@example.com")
user.assign_role("admin")
```

---

## RBAC Étendu aux Organisations

Lorsque `TENXYTE_ORGANIZATIONS_ENABLED = True`, les rôles peuvent être limités à une organisation :

```python
# Un utilisateur peut être "Admin" dans l'Organisation A mais "Viewer" dans l'Organisation B
membership = OrganizationMembership.objects.get(user=user, organization=org_a)
membership.role  # OrganizationRole limité à org_a
```

Utilisez `@require_org_permission` pour vérifier les permissions limitées à l'organisation :

```python
from tenxyte.decorators import require_org_permission

class OrgAdminView(APIView):
    @require_org_permission('org.manage')
    def post(self, request):
        # request.organization est défini par le middleware
        ...
```

Consultez [organizations.md](organizations.md) pour le guide complet sur les Organisations.

---

## Rôles par Défaut

Tenxyte injecte 4 rôles par défaut via `tenxyte_seed` :

| Code | Nom | Par défaut | Permissions |
|---|---|---|---|
| `viewer` | Lecteur | ✅ | `content.view` |
| `editor` | Éditeur | — | `content.view`, `content.create`, `content.edit` |
| `admin` | Administrateur | — | Contenu + Utilisateurs + Vue Rôles + Vue Permissions |
| `super_admin` | Super Administrateur | — | **Toutes les permissions** |

> **Note :** Le rôle `viewer` est le rôle par défaut (`is_default=True`) — il est automatiquement attribué aux nouveaux utilisateurs lors de l'appel à `user.assign_default_role()`.

---

## Codes de Permission Intégrés

Tenxyte injecte 41 permissions via `tenxyte_seed`. Les permissions parentes (en gras) accordent tous leurs enfants via la hiérarchie.

### Utilisateurs

| Code | Description |
|---|---|
| **`users`** | Toutes les permissions utilisateur (parent) |
| `users.view` | Voir la liste et les détails des utilisateurs |
| `users.create` | Créer de nouveaux utilisateurs |
| `users.edit` | Modifier les informations des utilisateurs |
| `users.delete` | Supprimer des utilisateurs |
| `users.ban` | Bannir/débannir des utilisateurs |
| `users.lock` | Verrouiller/déverrouiller des comptes utilisateurs |
| **`users.roles`** | Toutes les permissions liées aux rôles utilisateurs (parent) |
| `users.roles.view` | Voir les rôles des utilisateurs |
| `users.roles.assign` | Attribuer des rôles aux utilisateurs |
| `users.roles.remove` | Retirer des rôles aux utilisateurs |
| **`users.permissions`** | Toutes les permissions liées à la gestion directe des permissions (parent) |
| `users.permissions.view` | Voir les permissions directes des utilisateurs |
| `users.permissions.assign` | Attribuer des permissions directes aux utilisateurs |
| `users.permissions.remove` | Retirer des permissions directes aux utilisateurs |

### Rôles et Permissions

| Code | Description |
|---|---|
| **`roles`** | Toutes les permissions sur les rôles (parent) |
| `roles.view` | Voir la liste et les détails des rôles |
| `roles.create` | Créer de nouveaux rôles |
| `roles.update` | Mettre à jour les informations des rôles |
| `roles.delete` | Supprimer des rôles |
| `roles.manage_permissions` | Attribuer/retirer des permissions aux rôles |
| **`permissions`** | Toutes les permissions sur les permissions (parent) |
| `permissions.view` | Voir la liste des permissions |
| `permissions.create` | Créer de nouvelles permissions |
| `permissions.update` | Mettre à jour les informations des permissions |
| `permissions.delete` | Supprimer des permissions |

### Applications

| Code | Description |
|---|---|
| **`applications`** | Toutes les permissions sur les applications (parent) |
| `applications.view` | Voir la liste et les détails des applications |
| `applications.create` | Créer de nouvelles applications |
| `applications.update` | Modifier les informations d'une application |
| `applications.delete` | Supprimer des applications |
| `applications.regenerate` | Régénérer les identifiants d'une application |

### Contenu (générique)

| Code | Description |
|---|---|
| **`content`** | Toutes les permissions sur le contenu (parent) |
| `content.view` | Voir le contenu |
| `content.create` | Créer du contenu |
| `content.edit` | Modifier le contenu |
| `content.delete` | Supprimer du contenu |
| `content.publish` | Publier du contenu |

### Système et Sécurité

| Code | Description |
|---|---|
| **`system`** | Toutes les permissions système (parent) |
| `system.admin` | Accès complet à l'administration système |
| `system.settings` | Gérer les paramètres système |
| `system.logs` | Voir les journaux système |
| `system.audit` | Voir la trace d'audit |
| `dashboard.view` | Accéder aux statistiques du tableau de bord |
| `security.view` | Voir les journaux d'audit, tentatives de connexion, jetons |
| `gdpr.admin` | Voir les demandes de suppression |
| `gdpr.process` | Traiter les demandes de suppression |

---

## Injection (Seeding) et Personnalisation

### Commande `tenxyte_seed`

Injecter les permissions et rôles par défaut dans la base de données :

```bash
# Injecter tous les réglages par défaut
python manage.py tenxyte_seed

# Options
python manage.py tenxyte_seed --no-permissions   # Ignorer les permissions
python manage.py tenxyte_seed --no-roles          # Ignorer les rôles
python manage.py tenxyte_seed --force              # Supprimer et tout recréer
```

Cette commande est idempotente — l'exécuter plusieurs fois ne créera pas de doublons.

### Modèles Interchangeables

Tous les modèles RBAC peuvent être remplacés par des implémentations personnalisées :

```python
# settings.py
TENXYTE_PERMISSION_MODEL = 'myapp.CustomPermission'  # étend AbstractPermission
TENXYTE_ROLE_MODEL = 'myapp.CustomRole'              # étend AbstractRole
TENXYTE_USER_MODEL = 'myapp.CustomUser'              # étend AbstractUser
```

Exemple de modèle de permission personnalisé :

```python
from tenxyte.models import AbstractPermission

class CustomPermission(AbstractPermission):
    category = models.CharField(max_length=50)
    is_system = models.BooleanField(default=False)

    class Meta(AbstractPermission.Meta):
        db_table = 'custom_permissions'
```
