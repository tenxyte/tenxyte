# Plan Logique : Intégration des Organizations dans Tenxyte

> **Dernière mise à jour :** 19 Février 2026
> **Correction :** `Application` = plateforme (Web/Mobile/Desktop), PAS un tenant. Organizations globales (comme Users). Isolation par `Project` uniquement côté Cloud.

## Le Problème

Tenxyte a aujourd'hui une architecture en deux couches :

```
Requête HTTP
  │
  ├─ Couche 1 : ApplicationAuthMiddleware  (X-Access-Key / X-Access-Secret)
  │   └── request.application = Application (identifie la PLATEFORME : Web/Mobile/Desktop)
  │
  ├─ Couche 2 : require_jwt decorator  (Bearer token)
  │   └── request.user = User
  │   └── Vérifie : token.app_id == request.application.id
  │
  └─ Couche 3 : RBAC decorators  (@require_role, @require_permission)
      └── Vérifie : user.roles / user.permissions (GLOBALES)
```

**Clarification :** `Application` ne représente PAS un tenant/projet. C'est une identification de **plateforme** (Web, Mobile, Desktop). Les Users, Rôles et Permissions sont **partagés** entre toutes les Applications d'un même déploiement.

**Le problème :** les rôles/permissions sont **globaux** par utilisateur. Un user est « admin » partout ou nulle part. Il n'y a aucun concept de « cet user est admin dans l'org Acme, mais simple member dans l'org Beta ».

## Architecture Proposée

### Principe Fondamental : « Org comme Contexte, pas comme Remplacement »

> L'Organization ne remplace NI l'Application, NI le User. C'est une **couche de contexte** qui se superpose.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHAÎNE DE SÉCURITÉ                             │
│                                                                   │
│  ┌──────────────┐    ┌──────────┐    ┌──────────────────────┐    │
│  │ Application  │ →  │   User   │ →  │   Organization       │    │
│  │ (M2M Keys)   │    │  (JWT)   │    │   (Contexte)         │    │
│  │              │    │          │    │                      │    │
│  │ QUI appelle? │    │ QUI est  │    │ DANS QUEL contexte   │    │
│  │              │    │ connecté?│    │ agit-il?             │    │
│  └──────────────┘    └──────────┘    └──────────────────────┘    │
│       Couche 1           Couche 2          Couche 3 (NOUVEAU)    │
│                                                                   │
│  Existing RBAC (global) reste INTACT.                            │
│  Org RBAC s'ajoute EN PLUS pour les endpoints org-scoped.        │
│                                                                   │
│  Activable via : TENXYTE_ORGANIZATIONS_ENABLED = True            │
└─────────────────────────────────────────────────────────────────┘
```

### Les 3 Règles d'Or

1. **Rétro-compatible à 100%** — Tous les endpoints existants continuent de fonctionner sans aucun changement. Les rôles/permissions globaux restent intacts.
2. **Opt-in** — Activé via `TENXYTE_ORGANIZATIONS_ENABLED = True` (désactivé par défaut). Pas de migration, pas d'endpoint, pas de middleware si désactivé.
3. **Swappable** — Comme `AbstractUser`, les models Organization seront extensibles via `TENXYTE_ORGANIZATION_MODEL`.
4. **Scoping global** — Les Organizations sont globales (comme Users). L'isolation par projet (Cloud) est gérée par le modèle `Project`, pas par le package.

---

## Nouveaux Modèles

### 1. `AbstractOrganization` — L'entité mère

```python
class AbstractOrganization(models.Model):
    """
    Organization with optional parent/child hierarchy.
    
    Hierarchy example:
        Acme Corp (root)
        ├── Acme France (child)
        │   ├── Acme Paris (grandchild)
        │   └── Acme Lyon
        └── Acme USA (child)
    """
    id = AutoFieldClass(primary_key=True)
    
    # Identité
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    # Hiérarchie parent/enfant
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.CASCADE,  # Supprimer parent = supprimer enfants
        related_name='children'
    )
    
    # PAS de FK vers Application !
    # Application = plateforme (Web/Mobile/Desktop), pas un tenant.
    # Les Organizations sont globales dans un déploiement (comme les Users).
    # En Cloud, l'isolation par projet sera dans le modèle Project.
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(default=0)  # 0 = illimité
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, related_name='created_organizations'
    )
    
    class Meta:
        abstract = True
        ordering = ['name']
```

> [!IMPORTANT]
> **Pas de FK `application`** — Les Organizations sont **globales** (comme Users). `Application` = plateforme (Web/Mobile/Desktop). En Cloud, l'isolation par projet est dans le modèle `Project` (Tenant Management Layer).

#### Méthodes de hiérarchie

```python
def get_ancestors(self, include_self=False):
    """Remonte jusqu'à la racine."""
    
def get_descendants(self, include_self=False):
    """Descend dans tous les enfants (récursif)."""
    
def get_root(self):
    """Retourne l'organisation racine."""
    
@property
def depth(self):
    """Profondeur dans l'arbre (root=0)."""
    
@property
def is_root(self):
    """True si pas de parent."""
```

### 2. `AbstractOrganizationRole` — Rôles DANS une org

```python
class AbstractOrganizationRole(models.Model):
    """
    Rôles spécifiques aux Organizations (différents des rôles globaux).
    
    Exemples de rôles org :
      - owner   : Propriétaire, peut supprimer l'org
      - admin   : Admin, peut gérer les membres
      - member  : Membre, accès de base
      - billing : Accès facturation uniquement
      - viewer  : Lecture seule
    """
    id = AutoFieldClass(primary_key=True)
    
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Portée du rôle
    is_system = models.BooleanField(default=False)  # owner, admin, member
    is_default = models.BooleanField(default=False)  # Assigné auto aux nouveaux membres
    
    # Permissions org-level (codes de permissions)
    permissions = models.JSONField(default=list, blank=True)
    # Ex: ["org.members.invite", "org.settings.read", "org.billing.manage"]
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
        ordering = ['name']
```

> [!NOTE]
> **Pourquoi un model séparé de `Role` ?** Les rôles globaux (`Role`) = ce que l'user peut faire sur la PLATEFORME. Les rôles org (`OrganizationRole`) = ce que l'user peut faire DANS une org. Un user peut être `admin` global ET `viewer` dans une org spécifique.

### 3. `AbstractOrganizationMembership` — La table pivot

```python
class AbstractOrganizationMembership(models.Model):
    """
    Membership = la relation User ↔ Organization + son rôle dans cette org.
    
    C'est la TABLE CLÉ de tout le système. Elle répond à :
    - "Est-ce que User X est dans l'Org Y ?"
    - "Quel est son rôle dans l'Org Y ?"
    - "Qui a invité User X ?"
    """
    id = AutoFieldClass(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    organization = models.ForeignKey(
        'tenxyte.Organization',
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.ForeignKey(
        'tenxyte.OrganizationRole',
        on_delete=models.PROTECT,  # PROTECT : on ne peut pas supprimer un rôle tant qu'il est assigné
        related_name='memberships'
    )
    
    # Invitation workflow
    STATUS_CHOICES = [
        ('pending', 'Invitation Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_invitations'
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        unique_together = [('user', 'organization')]  # Un user = un membership par org
        ordering = ['-created_at']
```

### 4. `OrganizationInvitation` — Invitations

```python
class AbstractOrganizationInvitation(models.Model):
    """
    Invitations à rejoindre une org (par email ou lien).
    """
    id = AutoFieldClass(primary_key=True)
    
    organization = models.ForeignKey('tenxyte.Organization', on_delete=models.CASCADE)
    email = models.EmailField()  # Email du destinataire
    role = models.ForeignKey('tenxyte.OrganizationRole', on_delete=models.CASCADE)
    
    token = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, default='pending')
    expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
```

---

## Comment le Contexte Org Circule dans une Requête

### Option choisie : **Header `X-Org-Slug`** + claim JWT optionnel

```
Requête HTTP
│
│  Headers:
│    X-Access-Key: "app_key_xxx"        ← Couche 1 (identifie la plateforme)
│    X-Access-Secret: "app_secret_xxx"
│    Authorization: "Bearer eyJ..."     ← Couche 2 (existante)
│    X-Org-Slug: "acme-france"          ← Couche 3 (NOUVEAU, optionnel)
│
│  OU dans le JWT (claim optionnel):
│    { ..., "org_id": "abc123", "org_role": "admin" }
```

### Nouveau Middleware : `OrganizationContextMiddleware`

```python
class OrganizationContextMiddleware:
    """
    Middleware optionnel (Couche 3).
    Actif uniquement si TENXYTE_ORGANIZATIONS_ENABLED = True.
    
    Si le header X-Org-Slug est présent :
      1. Vérifie que l'org existe et est active
      2. NE vérifie PAS le membership (ça c'est le job des décorateurs)
      3. Attache request.organization = Organization
    
    Si pas de header : request.organization = None (pas d'erreur)
    """
    def __call__(self, request):
        if not org_settings.ORGANIZATIONS_ENABLED:
            request.organization = None
            return self.get_response(request)
        
        org_slug = request.headers.get('X-Org-Slug')
        
        if org_slug:
            try:
                org = Organization.objects.get(
                    slug=org_slug,
                    is_active=True
                )
                request.organization = org
            except Organization.DoesNotExist:
                return JsonResponse({
                    'error': 'Organization not found',
                    'code': 'ORG_NOT_FOUND'
                }, status=404)
        else:
            request.organization = None
        
        return self.get_response(request)
```

> [!IMPORTANT]
> **Scoping global** — Les Organizations sont globales (comme Users). En self-hosted, toutes les orgs sont dans la même DB. En Cloud, l'isolation par projet est gérée par le modèle `Project` dans le Tenant Management Layer.

---

## Nouveaux Décorateurs (Org-Scoped)

```python
def require_org_membership(view_func):
    """
    Exige que l'user soit membre de request.organization.
    Attache request.org_membership = Membership
    
    Usage:
        @require_jwt
        @require_org_membership
        def my_view(request): ...
    """

def require_org_role(role_code: str):
    """
    Exige un rôle spécifique dans l'org courante.
    
    Usage:
        @require_jwt
        @require_org_role('admin')
        def manage_members(request): ...
    """

def require_org_permission(permission_code: str):
    """
    Exige une permission org-level.
    
    Usage:
        @require_jwt
        @require_org_permission('org.members.invite')
        def invite_member(request): ...
    """

def require_org_owner(view_func):
    """
    Raccourci pour require_org_role('owner').
    """
```

### Chaîne complète d'un endpoint org-scoped

```
@require_jwt                    # 1. User authentifié (existant)
@require_org_membership         # 2. User est membre de l'org (NOUVEAU)
@require_org_role('admin')      # 3. User a le rôle admin dans l'org (NOUVEAU)
def invite_member(request):
    # request.application   ← App (couche 1)
    # request.user          ← User (couche 2)
    # request.organization  ← Org (couche 3)
    # request.org_membership ← Membership du user dans cette org
    pass
```

---

## Ce qui NE Change PAS (Rétro-compatibilité)

| Composant | Impact |
|---|---|
| `ApplicationAuthMiddleware` | ❌ Aucun changement |
| `JWTAuthMiddleware` | ❌ Aucun changement |
| `require_jwt` | ❌ Aucun changement |
| `require_role('admin')` | ❌ Continue de vérifier les rôles GLOBAUX |
| `require_permission('users.create')` | ❌ Continue de vérifier les permissions GLOBALES |
| JWT payload (`user_id`, `app_id`) | ❌ Aucun changement structurel (claim `org_id` optionnel) |
| `User.roles` / `User.permissions` | ❌ Restent les rôles/permissions GLOBAUX |
| Tous les 36 endpoints existants | ❌ Aucun changement |

---

## Héritage de rôles dans la hiérarchie Parent/Enfant

### Règle : « Les rôles se propagent vers le bas, JAMAIS vers le haut »

```
Acme Corp (root)          ← User est "admin" ici
├── Acme France            ← User est AUSSI "admin" ici (hérité)
│   ├── Acme Paris         ← User est AUSSI "admin" ici (hérité)
│   └── Acme Lyon          ← User est AUSSI "admin" ici (hérité)
└── Acme USA               ← User est AUSSI "admin" ici (hérité)
```

**Mais :**

```
Acme Corp (root)           ← User n'a PAS de rôle ici
├── Acme France            ← User est "admin" ici
│   ├── Acme Paris         ← User est "admin" ici (hérité de France)
│   └── Acme Lyon          ← User est "admin" ici (hérité de France)
└── Acme USA               ← User n'a PAS de rôle ici
```

### Configurable via settings

```python
# settings.py
TENXYTE_ORGANIZATIONS_ENABLED = True   # False par défaut — active tout le module Org
TENXYTE_ORG_ROLE_INHERITANCE = True     # True par défaut — rôles hérités vers le bas
TENXYTE_ORG_MAX_DEPTH = 5              # Profondeur max de hiérarchie
TENXYTE_ORG_MAX_MEMBERS = 0            # 0 = illimité
```

---

## Nouvelles Méthodes sur `AbstractUser`

```python
# Sur le model User (ajoutées sans casser l'existant)

def get_organizations(self):
    """Retourne toutes les orgs dont l'user est membre actif."""
    
def get_org_membership(self, organization):
    """Retourne le Membership dans une org spécifique."""
    
def get_org_role(self, organization):
    """Retourne le rôle de l'user dans une org."""
    
def has_org_role(self, organization, role_code):
    """Vérifie un rôle dans une org (avec héritage si activé)."""
    
def has_org_permission(self, organization, permission_code):
    """Vérifie une permission dans une org."""
    
def is_org_member(self, organization):
    """Vérifie si l'user est membre actif d'une org."""
```

---

## Nouveaux Endpoints API

```
# Organizations CRUD
POST   /api/v1/auth/organizations/                           ← Créer une org
GET    /api/v1/auth/organizations/                           ← Lister mes orgs
GET    /api/v1/auth/organizations/{slug}/                    ← Détails d'une org
PATCH  /api/v1/auth/organizations/{slug}/                    ← Modifier une org
DELETE /api/v1/auth/organizations/{slug}/                    ← Supprimer une org

# Sub-organizations (hiérarchie)
POST   /api/v1/auth/organizations/{slug}/children/           ← Créer une sous-org
GET    /api/v1/auth/organizations/{slug}/children/           ← Lister les sous-orgs
GET    /api/v1/auth/organizations/{slug}/tree/               ← Arbre complet

# Members
GET    /api/v1/auth/organizations/{slug}/members/            ← Lister les membres
POST   /api/v1/auth/organizations/{slug}/members/            ← Ajouter un membre
PATCH  /api/v1/auth/organizations/{slug}/members/{user_id}/  ← Modifier le rôle
DELETE /api/v1/auth/organizations/{slug}/members/{user_id}/  ← Retirer un membre

# Invitations
POST   /api/v1/auth/organizations/{slug}/invitations/        ← Inviter par email
GET    /api/v1/auth/organizations/{slug}/invitations/        ← Lister les invitations
POST   /api/v1/auth/invitations/{token}/accept/              ← Accepter une invitation
POST   /api/v1/auth/invitations/{token}/decline/             ← Décliner une invitation

# Organization Roles
GET    /api/v1/auth/org-roles/                               ← Lister les rôles org disponibles
```

---

## Schéma Relationnel Final

```mermaid
erDiagram
    Application ||--o{ Organization : "coexists (Cloud: via Project)"
    Organization ||--o{ Organization : "parent-children"
    Organization ||--o{ OrganizationMembership : "has members"
    User ||--o{ OrganizationMembership : "belongs to orgs"
    OrganizationRole ||--o{ OrganizationMembership : "defines access"
    Organization ||--o{ OrganizationInvitation : "has invitations"
    OrganizationRole ||--o{ OrganizationInvitation : "target role"
    User ||--o{ OrganizationInvitation : "invited by"
    
    Application {
        id PK
        access_key UK
        access_secret string
        is_active bool
    }
    
    User {
        id PK
        email UK
        roles M2M_Role
        direct_permissions M2M_Permission
    }
    
    Organization {
        id PK
        name string
        slug UK
        parent_id FK_self
        is_active bool
        max_members int
        metadata JSON
        created_by FK_User
    }
    
    OrganizationRole {
        id PK
        code string
        name string
        is_system bool
        is_default bool
        permissions JSON
    }
    
    OrganizationMembership {
        id PK
        user_id FK_User
        organization_id FK_Organization
        role_id FK_OrganizationRole
        status enum
        invited_by FK_User
    }
    
    OrganizationInvitation {
        id PK
        organization_id FK_Organization
        email string
        role_id FK_OrganizationRole
        token UK
        status enum
        invited_by FK_User
        expires_at datetime
    }
```

---

## Plan de Fichiers à Créer/Modifier

### Fichiers NOUVEAUX

| Fichier | Contenu |
|:---|:---|
| `src/tenxyte/models/organization.py` | `AbstractOrganization`, `Organization`, `AbstractOrganizationRole`, `OrganizationRole`, `AbstractOrganizationMembership`, `OrganizationMembership`, `AbstractOrganizationInvitation`, `OrganizationInvitation` — **sans FK vers Application** |
| `src/tenxyte/services/organization_service.py` | `OrganizationService` — CRUD, members, invitations, hierarchy |
| `src/tenxyte/views/organization_views.py` | Views pour les endpoints org (conditionnelles à `TENXYTE_ORGANIZATIONS_ENABLED`) |
| `src/tenxyte/serializers/organization_serializers.py` | Serializers pour les models org |

### Fichiers MODIFIÉS (additions seulement)

| Fichier | Modification |
|:---|:---|
| `src/tenxyte/models.py` | Import + re-export des models org (rétro-compatible) |
| `src/tenxyte/middleware.py` | Ajout `OrganizationContextMiddleware` (conditionnel à `TENXYTE_ORGANIZATIONS_ENABLED`) |
| `src/tenxyte/decorators.py` | Ajout `require_org_membership`, `require_org_role`, `require_org_permission`, `require_org_owner` |
| `src/tenxyte/urls.py` | Ajout des routes org (conditionnelles à `TENXYTE_ORGANIZATIONS_ENABLED`) |
| `src/tenxyte/conf.py` | Ajout des settings : `TENXYTE_ORGANIZATIONS_ENABLED` (False), `TENXYTE_ORG_ROLE_INHERITANCE`, `TENXYTE_ORG_MAX_DEPTH`, `TENXYTE_ORG_MAX_MEMBERS` |

### Fichiers INCHANGÉS

Tout le reste — aucun fichier existant n'est modifié de façon breaking.

> [!NOTE]
> **Isolation Cloud :** En mode Cloud, le modèle `Project` (dans la super-app) ajoutera la FK `project` aux Organizations pour l'isolation par projet. Le package moteur reste agnostique du concept de Project.

---

## Verification Plan

> [!IMPORTANT]
> **Pas de tests existants dans le repo** qui couvrent les Organizations (la feature n'existe pas encore). Il n'y a pas de suite de tests unitaires structurée dans `src/tenxyte/tests/`. Les tests seront créés from scratch.

### Tests à créer

1. **Tests unitaires models** — Hiérarchie parent/enfant, méthodes `get_ancestors()`, `get_descendants()`, `depth`, membership unique constraint
2. **Tests unitaires decorators** — `require_org_membership`, `require_org_role` avec mocks de request
3. **Tests intégration middleware** — `OrganizationContextMiddleware` avec isolation Application
4. **Tests intégration endpoints** — CRUD org, members, invitations via `APIClient`

### Comment les lancer

Le user devra valider la méthode de test préférée (Django TestCase avec un projet de test, ou pytest avec fixtures). On définira ça lors de l'implémentation.

---

## Décisions Architecturales (Validées)

> [!NOTE]
> **OrganizationRole séparé de Role** — Un user a **deux systèmes de rôles** : global (existant, inchangé) et org-scoped (nouveau). Évite de polluer le RBAC existant.

> [!NOTE]
> **Héritage de rôles activé par défaut** — Admin de "Acme Corp" = admin de "Acme France". Configurable via `TENXYTE_ORG_ROLE_INHERITANCE = False`.

> [!NOTE]
> **Pas de FK Application** — Organizations globales (comme Users). `Application` = plateforme. Isolation Cloud via `Project`.

> [!NOTE]
> **Opt-in par setting** — `TENXYTE_ORGANIZATIONS_ENABLED = False` par défaut. Désactivé = aucune migration, endpoint, ou middleware org.
