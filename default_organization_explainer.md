# L'Organisation par Défaut ("Personal Workspace")

Dans la quasi-totalité des SaaS B2B modernes (Notion, Slack, Vercel, Github), la création automatique d'une "Organisation par défaut" à l'inscription est le standard de conception.

## Pourquoi ce fonctionnement ?

### 1. Simplification de l'Expérience Utilisateur (Onboarding)
Si un utilisateur s'inscrit, qu'il arrive sur un dashboard vide et que le système lui affiche : *"Erreur : Vous devez d'abord créer ou rejoindre une organisation pour utiliser l'application"*, cela crée une **friction massive**.
L'utilisateur veut tester le produit tout de suite. En créant automatiquement une organisation (ex: "Workspace de Jean"), il peut immédiatement créer des documents, inviter des collègues, etc.

### 2. Cohérence du Modèle de Données (Hard Multi-Tenancy)
C'est le point technique le plus crucial ! Si vous mettez en place un filtrage strict par `TenantModel` (Option 1), **aboslument toutes** les données métier de votre application devront être rattachées à une organisation.
- Un document *doit* avoir un `organization_id`.
- Un projet *doit* avoir un `organization_id`.

**Le problème sans organisation par défaut :**
Si l'utilisateur n'a pas d'organisation, il se retrouve dans un état "limbo" ("hors-contexte"). Le framework lui interdirait de créer la moindre donnée métier puisqu'il n'aurait pas de `current_org` active dans son `contextvars`.

### 3. La transition "Individu -> Équipe"
Un utilisateur commence toujours seul. Son "Workspace Personnel" est son espace de test. Demain, s'il aime le produit, il lui suffira d'aller dans "Paramètres", de renommer "Workspace de Jean" en "Acme Corp", et d'inviter ses collègues. Le modèle de données n'aura pas bougé d'un iota.

---

## Faut-il faire de même pour Tenxyte ?

**Oui, c'est indispensable si vous activez les organisations (`TENXYTE_ORGANIZATIONS_ENABLED = True`).**

### Comment cela se traduit dans Tenxyte ?

Dans votre logique de création de compte (par exemple dans le serializer de Signup ou le service d'authentification) :

1. L'utilisateur "Jean Dupont" (jean@example.com) s'inscrit.
2. Le système crée le User `Jean`.
3.  **Action automatique** : Le système appelle [OrganizationService().create_organization()](file:///c:/Users/bobop/Documents/own/tenxyte/src/tenxyte/services/organization_service.py#28-653) :
    - `name` = "Personal Workspace" (ou "Workspace de Jean")
    - `slug` = `jean-workspace-1234`
    - `created_by` = Jean
4. Le service va automatiquement assigner le rôle [owner](file:///c:/Users/bobop/Documents/own/tenxyte/src/tenxyte/decorators.py#559-570) à Jean pour cette organisation.
5. Lorsque la configuration du Front-End (Tenxyte React SDK) s'initialise, il verra que Jean appartient à une seule organisation. Il sélectionnera automatiquement ce `slug` et l'enverra dans tous les headers `X-Org-Slug`.

### Et quand un utilisateur est "uniquement" invité ?
Si Jean invite "Marie" depuis son organisation "Workspace de Jean" :
- Marie clique sur le lien d'invitation.
- Elle crée son compte.
- **Là, vous avez le choix métier** :
  1. Soit vous lui créez quand même son propre "Workspace de Marie" par défaut, ET elle rejoint le "Workspace de Jean". (C'est ce que fait Notion).
  2. Soit, comme elle vient d'une invitation, elle rejoint uniquement le "Workspace de Jean" et vous lui épargnez la création de son espace perso. (C'est ce que fait Slack).

Dans tous les cas, une fois connectée, l'utilisateur d'un système Hard Multi-Tenant **doit toujours avoir au moins un contexte d'organisation actif** pour interagir avec le cœur de l'application.
