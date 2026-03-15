# Guide des Organisations — Configuration Multi-Tenant B2B

Tenxyte prend en charge les organisations hiérarchiques avec un RBAC étendu aux organisations, une gestion des membres et des invitations.

> **Fonctionnalité optionnelle** — désactivée par défaut pour la compatibilité ascendante.

---

## Table des Matières

- [Activer les Organisations](#activer-les-organisations)
- [Configuration](#configuration)
- [Concepts](#concepts)
  - [Organisation](#organisation)
  - [Rôle d'Organisation (OrganizationRole)](#role-dorganisation-organizationrole)
  - [Appartenance à une Organisation (OrganizationMembership)](#appartenance-a-une-organisation-organizationmembership)
- [Utilisation de l'API](#utilisation-de-lapi)
  - [Créer une Organisation](#creer-une-organisation)
  - [Créer une Sous-Organisation](#creer-une-sous-organisation)
  - [Lister Mes Organisations](#lister-mes-organisations)
  - [Obtenir les Détails d'une Organisation](#obtenir-les-details-dune-organisation)
  - [Obtenir l'Arborescence de l'Organisation](#obtenir-larborescence-de-lorganisation)
  - [Mettre à Jour une Organisation](#mettre-a-jour-une-organisation)
  - [Supprimer une Organisation](#supprimer-une-organisation)
- [Gestion des Membres](#gestion-des-membres)
  - [Lister les Membres](#lister-les-membres)
  - [Ajouter un Membre](#ajouter-un-membre)
  - [Mettre à Jour le Rôle d'un Membre](#mettre-a-jour-le-role-dun-membre)
  - [Supprimer un Membre](#supprimer-un-membre)
  - [Inviter un Membre par E-mail](#inviter-un-membre-par-e-mail)
- [Rôles d'Organisation](#roles-dorganisation)
- [Héritage des Rôles](#heritage-des-roles)
- [API Python](#api-python)
- [RBAC Étendu aux Orgs dans les Vues](#rbac-etendu-aux-orgs-dans-les-vues)
- [Modèle de Données](#modele-de-donnees)
- [Référence des Paramètres](#reference-des-parametres)

---

## Activer les Organisations

Pour activer la fonctionnalité des organisations, mettez à jour votre fichier `settings.py` :

```python
# settings.py
TENXYTE_ORGANIZATIONS_ENABLED = True

# Ajouter le middleware pour attacher le contexte de l'organisation aux requêtes
MIDDLEWARE += [
    'tenxyte.middleware.OrganizationContextMiddleware',
]
```

Ensuite, lancez les migrations pour préparer la base de données :
```bash
python manage.py migrate
```

---

## Configuration

```python
TENXYTE_ORGANIZATIONS_ENABLED = True
TENXYTE_ORG_ROLE_INHERITANCE = True   # Les rôles se propagent dans la hiérarchie
TENXYTE_ORG_MAX_DEPTH = 5             # Profondeur maximale de la hiérarchie
TENXYTE_ORG_MAX_MEMBERS = 0           # 0 = illimité
```

---

## Concepts

### Organisation

Une entité nommée qui regroupe des utilisateurs. Les organisations peuvent être imbriquées (parent → enfants).

```
Acme Corp (racine)
├── Ingénierie
│   ├── Équipe Backend
│   └── Équipe Frontend
└── Ventes
    └── EMEA
```

### Rôle d'Organisation (OrganizationRole)

Un rôle limité à une organisation (ex: `admin`, `member`, `viewer`). Différent des rôles RBAC globaux.

### Appartenance à une Organisation (OrganizationMembership)

Lie un utilisateur à une organisation avec un rôle spécifique.

---

## Utilisation de l'API

### Créer une Organisation

```bash
POST /api/v1/auth/organizations/
Authorization: Bearer <token>

{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Notre organisation principale"
}
```

**Réponse `201` :**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "parent": null,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### Créer une Sous-Organisation

```bash
POST /api/v1/auth/organizations/
{
  "name": "Ingénierie",
  "slug": "acme-engineering",
  "parent_id": 1
}
```

### Lister Mes Organisations

```bash
GET /api/v1/auth/organizations/list/
```

### Obtenir les Détails d'une Organisation

```bash
GET /api/v1/auth/organizations/detail/
X-Org-Slug: acme-corp
```

### Obtenir l'Arborescence de l'Organisation

```bash
GET /api/v1/auth/organizations/tree/
X-Org-Slug: acme-corp
```

**Réponse :**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "children": [
    {
      "id": 2,
      "name": "Ingénierie",
      "children": [
        { "id": 3, "name": "Équipe Backend", "children": [] },
        { "id": 4, "name": "Équipe Frontend", "children": [] }
      ]
    }
  ]
}
```

### Mettre à Jour une Organisation

```bash
PATCH /api/v1/auth/organizations/update/
X-Org-Slug: acme-corp

{
  "name": "Acme Corporation",
  "description": "Description mise à jour"
}
```

### Supprimer une Organisation

```bash
DELETE /api/v1/auth/organizations/delete/
X-Org-Slug: acme-corp
```

---

## Gestion des Membres

### Lister les Membres

```bash
GET /api/v1/auth/organizations/members/
X-Org-Slug: acme-corp
```

**Réponse :**
```json
[
  {
    "user_id": 42,
    "email": "alice@acme.com",
    "role": "admin",
    "joined_at": "2026-01-01T00:00:00Z"
  }
]
```

### Ajouter un Membre

```bash
POST /api/v1/auth/organizations/members/add/
X-Org-Slug: acme-corp

{
  "user_id": 42,
  "role_code": "member"
}
```

### Mettre à Jour le Rôle d'un Membre

```bash
PATCH /api/v1/auth/organizations/members/42/
X-Org-Slug: acme-corp

{
  "role_code": "admin"
}
```

### Supprimer un Membre

```bash
DELETE /api/v1/auth/organizations/members/42/remove/
X-Org-Slug: acme-corp
```

### Inviter un Membre par E-mail

```bash
POST /api/v1/auth/organizations/invitations/
X-Org-Slug: acme-corp

{
  "email": "newmember@example.com",
  "role_code": "member",
  "expires_in_days": 7
}
```

Un e-mail d'invitation est envoyé. L'utilisateur peut accepter en s'inscrivant ou en se connectant.

---

## Rôles d'Organisation

Lister les rôles disponibles étendus à l'organisation :

```bash
GET /api/v1/auth/org-roles/
```

Créer des rôles d'organisation par programmation :

```python
from tenxyte.models import OrganizationRole

role = OrganizationRole.objects.create(
    code="admin",
    name="Admin",
    description="Administrateur avec permissions de gestion",
    permissions=["org.members.invite", "org.members.manage"]
)
```

---

## Héritage des Rôles

Lorsque `TENXYTE_ORG_ROLE_INHERITANCE = True`, les rôles assignés à une organisation parente se propagent à toutes les organisations enfants.

Exemple :
- Alice est `admin` dans `Acme Corp`
- Elle a automatiquement les droits `admin` dans `Ingénierie`, `Équipe Backend`, etc.

Pour vérifier les permissions effectives dans une organisation spécifique :

```python
membership = OrganizationMembership.objects.get(user=alice, organization=backend_team)
# membership.role peut être hérité du parent
```

---

## API Python

```python
from tenxyte.services import OrganizationService

service = OrganizationService()

# Créer
success, org, error = service.create_organization(
    name="Acme Corp",
    slug="acme-corp",
    created_by=user
)

# Ajouter un membre
success, membership, error = service.add_member(
    organization=org,
    user_to_add=new_user,
    role_code="member",
    added_by=admin_user
)

# Obtenir l'arborescence
tree = service.get_organization_tree(org)

# Vérifier l'appartenance
is_member = service.is_member(user, org)
```

---

## RBAC Étendu aux Orgs dans les Vues

Utilisez `@require_org_permission` pour protéger les vues avec des permissions étendues à l'organisation :

```python
from tenxyte.decorators import require_jwt, require_org_context, require_org_permission

class OrgSettingsView(APIView):
    @require_jwt
    @require_org_context
    @require_org_permission('org.manage')
    def post(self, request):
        # request.organization est défini par le middleware
        org = request.organization
        ...
```

Le middleware résout l'organisation à partir de l'en-tête de requête `X-Org-Slug`.

---

## Modèle de Données

```
Organization
├── id
├── name
├── slug (unique)
├── description
├── parent (FK → self, nullable)
├── metadata (JSON)
├── is_active
├── max_members
├── created_at
├── updated_at
└── created_by (FK → User, nullable)

OrganizationRole
├── id
├── code (unique)
├── name
├── description
├── is_system
├── is_default
├── permissions (liste JSON)
├── created_at
└── updated_at

OrganizationMembership
├── id
├── user (FK → User)
├── organization (FK → Organization)
├── role (FK → OrganizationRole)
├── status
├── invited_by (FK → User, nullable)
├── invited_at (nullable)
├── created_at
└── updated_at

OrganizationInvitation
├── id
├── organization (FK → Organization)
├── email
├── role (FK → OrganizationRole)
├── token (unique)
├── invited_by (FK → User, nullable)
├── status
├── created_at
├── expires_at
└── accepted_at (nullable)
```

---

## Référence des Paramètres

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_ORGANIZATIONS_ENABLED` | `False` | Activer la fonctionnalité |
| `TENXYTE_ORG_ROLE_INHERITANCE` | `True` | Propager les rôles dans la hiérarchie |
| `TENXYTE_ORG_MAX_DEPTH` | `5` | Profondeur d'imbrication maximale |
| `TENXYTE_ORG_MAX_MEMBERS` | `0` | Membres max par org (0 = illimité) |
| `TENXYTE_CREATE_DEFAULT_ORGANIZATION`| `True` | Créer une organisation par défaut pour les nouveaux utilisateurs |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Modèle remplaçable |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Modèle remplaçable |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL` | `'tenxyte.OrganizationMembership'` | Modèle remplaçable |
