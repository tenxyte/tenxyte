# Guide des Applications — Gestion des clients API

Tenxyte propose un modèle `Application` intégré pour gérer plusieurs clients API (tels que des applications Web, des applications mobiles, des scripts de test ou des intégrations B2B). Chaque application reçoit sa propre `access_key` et `access_secret`, qui sont nécessaires pour authentifier les requêtes API.

---

## Sommaire

- [Présentation](#présentation)
- [Fonctionnement](#fonctionnement)
- [Configuration](#configuration)
- [Utilisation de l'API](#utilisation-de-lapi)
  - [Créer une application](#créer-une-application)
  - [Lister les applications](#lister-les-applications)
  - [Obtenir les détails d'une application](#obtenir-les-détails-dune-application)
  - [Mettre à jour une application](#mettre-à-jour-une-application)
  - [Régénérer les identifiants](#régénérer-les-identifiants)
  - [Supprimer une application](#supprimer-une-application)
- [Notes de sécurité](#notes-de-sécurité)
- [API Python](#api-python)
- [Modèle de données](#modèle-de-données)

---

## Présentation

Dans les systèmes modernes, un backend dessert généralement plusieurs clients. Au lieu d'utiliser une seule clé API globale ou de coder en dur les identifiants, Tenxyte vous permet de générer des clés distinctes pour chaque client.

Par exemple, vous pourriez avoir :
- Application `Web Frontend`
- Application `iOS Mobile`
- Application `Partner X Integration`

En transmettant les en-têtes HTTP `X-Access-Key` et `X-Access-Secret`, Tenxyte identifie l'application cliente effectuant la requête.

---

## Fonctionnement

1. **Création** : Un administrateur crée une Application via l'API (ou via le code Python).
2. **Affichage des identifiants** : Le système génère une `access_key` (publique) et un `access_secret` (privé). L' `access_secret` brut n'est renvoyé **qu'une seule fois**, puis est haché de manière sécurisée (bcrypt + base64) dans la base de données.
3. **Utilisation** : Chaque requête vers les points de terminaison d'authentification protégés de Tenxyte doit inclure les en-têtes `X-Access-Key` et `X-Access-Secret` afin que le système puisse vérifier l'identité de l'application.
4. **Révocation** : Si un secret est divulgué, les administrateurs peuvent régénérer les identifiants pour cette application spécifique ou désactiver complètement l'application.

---

## Configuration

Le modèle d'Application par défaut peut être personnalisé. Si vous devez ajouter des champs (comme des limites de débit, un propriétaire, etc.), vous pouvez étendre `AbstractApplication`.

```python
# Créer un modèle personnalisé
from tenxyte.models import AbstractApplication
from django.db import models

class CustomApplication(AbstractApplication):
    owner = models.ForeignKey('users.User', on_delete=models.CASCADE)
    api_rate_limit = models.IntegerField(default=1000)

    class Meta(AbstractApplication.Meta):
        db_table = 'custom_applications'
```

Et mettez à jour votre fichier `settings.py` :
```python
TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
```

---

## Utilisation de l'API

Tous les points de terminaison se situent sous `/api/v1/auth/applications/` et nécessitent les permissions RBAC appropriées (`applications.view`, `applications.create`, `applications.update`, `applications.delete`, `applications.regenerate`) ainsi qu'un JWT valide.

### Créer une application

Crée un nouveau client et renvoie le secret.

```bash
POST /api/v1/auth/applications/
Authorization: Bearer <token>

{
  "name": "Mobile iOS App",
  "description": "Application iOS principale pour les utilisateurs finaux",
  "redirect_uris": ["myapp://callback", "https://app.example.com/auth"]
}
```

**Réponse `201` :**
```json
{
  "message": "Application created successfully",
  "application": {
    "id": 1,
    "name": "Mobile iOS App",
    "description": "Application iOS principale pour les utilisateurs finaux",
    "access_key": "c4ca4238a0b923820dcc509a6f75849b...",
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "credentials": {
    "access_key": "c4ca4238a0b923820dcc509a6f75849b...",
    "access_secret": "8b1a9953c4611296a827abf8c47804d7..."
  },
  "warning": "Enregistrez l'access_secret maintenant ! Il ne sera plus jamais affiché."
}
```

### Lister les applications

Renvoie une liste paginée de toutes les applications.

```bash
GET /api/v1/auth/applications/
Authorization: Bearer <token>
```

Accepte des paramètres de requête tels que `?search=mobile`, `?is_active=true`, `?ordering=name`.

### Obtenir les détails d'une application

Récupère les détails d'une application. Le secret n'est jamais renvoyé.

```bash
GET /api/v1/auth/applications/1/
Authorization: Bearer <token>
```

### Mettre à jour une application

Met à jour le nom ou la description d'une application.

```bash
PUT /api/v1/auth/applications/1/
Authorization: Bearer <token>

{
  "name": "Mobile iOS App v2",
  "description": "Application iOS mise à jour",
  "is_active": true
}
```

Alternativement, utilisez `PATCH` pour basculer rapidement le statut actif :
```bash
PATCH /api/v1/auth/applications/1/
Authorization: Bearer <token>

{
  "is_active": false
}
```

### Régénérer les identifiants

Si un secret est compromis ou perdu, vous pouvez invalider les anciens identifiants et en créer de nouveaux. Cela nécessite une confirmation explicite par chaîne de caractères (`"REGENERATE"`).

```bash
POST /api/v1/auth/applications/1/regenerate/
Authorization: Bearer <token>

{
     "confirmation": "REGENERATE"
}
```

**Réponse `200` :**
```json
{
  "message": "Credentials regenerated successfully",
  "application": { /* ... */ },
  "credentials": {
    "access_key": "new_key...",
    "access_secret": "new_secret..."
  },
  "warning": "Enregistrez l'access_secret maintenant ! Il ne sera plus jamais affiché.",
  "old_credentials_invalidated": true
}
```

### Supprimer une application

Supprime définitivement l'application et révoque complètement son accès.

```bash
DELETE /api/v1/auth/applications/1/
Authorization: Bearer <token>
```

---

## Notes de sécurité

1. **Hachage** : Tout comme les mots de passe, les secrets d'application sont hachés de manière sécurisée avec `bcrypt` et stockés en base64. Ils ne peuvent pas être récupérés en lisant la base de données.
2. **Affichage unique** : L' `access_secret` n'est renvoyé qu'une seule fois lorsque le point de terminaison `POST` ou `regenerate` est appelé. Après cela, il est inaccessible.
3. **Désactivation** : Avant de supprimer complètement une application, envisagez de la désactiver (`PATCH is_active: false`) pour interrompre temporairement son accès sans perdre son historique et ses statistiques.

---

## API Python

Vous pouvez interagir par programmation avec le modèle `Application` dans votre code Python :

```python
from tenxyte.models import get_application_model

Application = get_application_model()

# 1. Créer une application
app, raw_secret = Application.create_application(
    name="Test Script API", 
    description="Pour des tests internes"
)
print(f"Clé : {app.access_key}")
print(f"Secret : {raw_secret}")

# 2. Vérifier le secret
is_valid = app.verify_secret(raw_secret) # Renvoie True ou False

# 3. Régénérer les identifiants
new_credentials = app.regenerate_credentials()
print(new_credentials["access_key"])
print(new_credentials["access_secret"])
```

---

## Modèle de données

```
Application (AbstractApplication)
├── id  (Clé primaire)
├── name (chaîne)
├── description (texte)
├── access_key (chaîne, unique, indexée)
├── access_secret (chaîne, hachée)
├── is_active (booléen, par défaut : true)
├── redirect_uris (tableau JSON, par défaut : [])
├── created_at (datetime)
└── updated_at (datetime)
```

> **Note :** Lorsque `redirect_uris` est vide, toutes les URI de redirection sont autorisées (rétrocompatible). Lorsqu'il est renseigné, seules les correspondances exactes sont acceptées lors des flux OAuth. Voir le [Guide de Sécurité](security.md) pour plus de détails.
