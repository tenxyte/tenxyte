# Gestion des comptes administrateurs

Les comptes administrateurs sont nécessaires pour gérer les utilisateurs, configurer le contrôle d'accès basé sur les rôles (RBAC), consulter les journaux d'audit et accéder au panneau d'administration Django intégré. Tenxyte propose deux niveaux distincts de comptes administratifs.

---

## Sommaire

- [Présentation](#présentation)
- [1. Superutilisateur Django](#1-superutilisateur-django)
  - [Création](#création)
  - [Capacités](#capacités)
- [2. Rôles d'administration RBAC](#2-rôles-dadministration-rbac)
  - [Création](#création-1)
  - [Capacités](#capacités-1)
- [Comparaison](#comparaison)

---

## Présentation

Dans Tenxyte, vous pouvez avoir un **Superutilisateur** complet (qui outrepasse toutes les vérifications de permissions) ou un **Administrateur RBAC** (un utilisateur standard auquel est assigné le rôle `admin` ou `super_admin`). Selon vos exigences de sécurité, vous pourriez n'accorder le statut de Superutilisateur qu'aux développeurs backend, tandis que le personnel de support reçoit le rôle `admin`.

---

## 1. Superutilisateur Django

Un Superutilisateur Django est essentiellement un compte "root" pour votre application. Cet utilisateur a `is_superuser=True` et `is_staff=True` dans la base de données.

### Création

Les superutilisateurs sont généralement créés via la ligne de commande. C'est presque toujours le tout premier compte que vous créez lors de la configuration initiale de Tenxyte.

```bash
python manage.py createsuperuser
```

Exemple d'invite :
```
Email address: admin@example.com
Password: 
Password (again): 
Superuser created successfully.
```

### Capacités

- **Outrepasse le RBAC :** `user.has_permission("any.permission")` renvoie toujours `True`.
- **Accès au panneau d'administration :** Peut se connecter à `http://localhost:8000/admin/` pour visualiser les tables brutes de la base de données.
- **Accès à l'API :** Possède un accès implicite à chaque point de terminaison de l'API automatiquement.

*Note : Vous n'avez pas besoin d'assigner des rôles RBAC à un Superutilisateur.*

---

## 2. Rôles d'administration RBAC

Un Administrateur RBAC est un utilisateur régulier qui a été assigné à un rôle puissant (ex: `admin` ou `super_admin`). Il n'a pas `is_superuser=True`.

### Création

Pour créer un Administrateur RBAC, l'utilisateur doit d'abord s'inscrire normalement. Ensuite, un Superutilisateur ou un Administrateur existant peut l'élever via l'API :

```bash
POST /api/v1/auth/users/<user_id>/roles/
Authorization: Bearer <superuser_token>

{
  "role_codes": ["super_admin"]
}
```

Alternativement, vous pouvez élever un utilisateur par programmation via le shell Django :

```python
# python manage.py shell
from tenxyte.models import get_user_model
User = get_user_model()

user = User.objects.get(email="manager@example.com")
user.assign_role("super_admin")
```

### Capacités

- **RBAC strict :** Ils n'ont que les permissions explicitement accordées à leur rôle.
- **Pas d'accès à l'administration Django :** Par défaut, ils ne peuvent pas accéder à `/admin/` à moins que vous ne définissiez également manuellement `is_staff=True` sur leur compte.
- **Plus sûr pour les équipes :** Idéal pour le support client, les RH ou les chefs de produit qui ont besoin d'un large accès à l'API sans accès direct à la base de données.

Consultez le [Guide RBAC](rbac.md) pour plus de détails sur les rôles et permissions intégrés.

---

## Comparaison

| Fonctionnalité | Superutilisateur Django | RBAC `super_admin` | RBAC `admin` |
|---|---|---|---|
| **Outrepasser les permissions** | ✅ Oui | ❌ Non (Dépend des perms assignées) | ❌ Non |
| **Accès Admin Django (`/admin/`)** | ✅ Oui | ❌ Non (nécessite `is_staff`) | ❌ Non |
| **Gérer utilisateurs & rôles (API)** | ✅ Oui | ✅ Oui | ✅ Oui |
| **Méthode de création** | CLI (`createsuperuser`) | API ou Shell | API ou Shell |
| **Idéal pour** | Développeurs, Administrateurs système | Responsables d'équipe | Personnel de support |

