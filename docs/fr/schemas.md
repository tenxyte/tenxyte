# Référence des Schémas

Ce document décrit les composants de schéma réutilisables utilisés dans l'API Tenxyte. Ceux-ci correspondent aux composants `$ref` de la spécification OpenAPI (`openapi_schema.json`).

## Table des Matières

- [Utilisateur (User)](#user)
- [Paire de Jetons (TokenPair)](#tokenpair)
- [Réponse d'Erreur (ErrorResponse)](#errorresponse)
- [Réponse Paginée (PaginatedResponse)](#paginatedresponse)
- [Organisation](#organization)
- [Journal d'Audit (AuditLog)](#auditlog)
- [Rôle](#role)
- [Informations sur l'Appareil (DeviceInfo)](#deviceinfo)

---

## User (Utilisateur)

Représente un utilisateur Tenxyte authentifié.

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "phone_country_code": "+33",
  "phone_number": "612345678",
  "first_name": "John",
  "last_name": "Doe",
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_2fa_enabled": false,
  "roles": ["admin"],
  "permissions": ["users.view", "users.manage"],
  "created_at": "2026-01-01T00:00:00Z",
  "last_login": "2026-03-01T12:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant unique de l'utilisateur |
| `email` | string \| null | E-mail de connexion principal |
| `phone_country_code` | string \| null | Code pays (ex: +33) |
| `phone_number` | string \| null | Numéro de téléphone local |
| `first_name` / `last_name` | string | Nom d'affichage |
| `is_email_verified` | boolean | Indique si l'e-mail a été vérifié |
| `is_phone_verified` | boolean | Indique si le numéro de téléphone a été vérifié |
| `is_2fa_enabled` | boolean | Indique si l'authentification à deux facteurs TOTP est active |
| `roles` | string[] | Liste plate des identifiants de rôles attribués |
| `permissions` | string[] | Liste plate des permissions attribuées (directes + via les rôles) |
| `created_at` | string (date-time) | Horodatage de création du compte |
| `last_login` | string (date-time) \| null | Horodatage de la dernière connexion |

---

## TokenPair (Paire de Jetons)

Délivré lors d'une connexion réussie ou d'un rafraîchissement de jeton.

```json
{
  "access_token": "<JWT access token>",
  "refresh_token": "<JWT refresh token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "device_summary": "Windows 11 Desktop"
}
```

| Champ | Type | Description |
|---|---|---|
| `access_token` | chaîne JWT | Jeton d'accès à courte durée de vie |
| `refresh_token` | chaîne JWT | Jeton de rafraîchissement à longue durée de vie |
| `token_type` | string | Type de jeton (toujours "Bearer") |
| `expires_in` | integer | Expiration du jeton d'accès en secondes |
| `device_summary` | string \| null | Description de l'appareil de l'utilisateur (si `device_info` a été envoyé) |

---

## ErrorResponse (Réponse d'Erreur)

Renvoyée pour toutes les réponses `4xx` et `5xx`.

```json
{
  "error": "Message compréhensible par l'humain",
  "code": "CODE_COMPREHENSIBLE_PAR_LA_MACHINE",
  "details": {}
}
```

| Champ | Type | Description |
|---|---|---|
| `error` | string | Description destinée à l'utilisateur |
| `code` | string | Identifiant d'erreur lisible par la machine (voir ci-dessous) |
| `details` | object \| null | Erreurs de validation au niveau des champs ou contexte supplémentaire |

### Codes d'Erreur Courants

| Code | Statut HTTP | Signification |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | E-mail ou mot de passe incorrect |
| `ACCOUNT_LOCKED` | 401 | Trop de tentatives de connexion échouées |
| `2FA_REQUIRED` | 403 | La connexion nécessite un code TOTP |
| `TOKEN_EXPIRED` | 401 | Le jeton d'accès a expiré |
| `TOKEN_BLACKLISTED` | 401 | Le jeton a été révoqué (déconnexion) |
| `PERMISSION_DENIED` | 403 | Rôle ou permission insuffisant |
| `SESSION_LIMIT_EXCEEDED` | 403 | Trop de sessions simultanées |
| `DEVICE_LIMIT_EXCEEDED` | 403 | Trop d'appareils enregistrés |
| `RATE_LIMITED` | 429 | Trop de requêtes |
| `ORG_NOT_FOUND` | 404 | L'en-tête X-Org-Slug ne correspond à rien |
| `NOT_ORG_MEMBER` | 403 | L'utilisateur n'est pas membre de l'organisation fournie |

---

## PaginatedResponse (Réponse Paginée)

Tous les points de terminaison de liste renvoient un wrapper de pagination personnalisé (`TenxytePagination`) :

```json
{
  "count": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "next": "http://localhost:8000/api/v1/auth/admin/users/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Champ | Type | Description |
|---|---|---|
| `count` | integer | Nombre total d'éléments sur toutes les pages |
| `page` | integer | Numéro de la page actuelle |
| `page_size` | integer | Nombre d'éléments par page |
| `total_pages` | integer | Nombre total de pages |
| `next` | string \| null | URL de la page suivante (null si dernière page) |
| `previous` | string \| null | URL de la page précédente (null si première page) |
| `results` | array | Éléments de la page actuelle |

---

## Organization (Organisation)

Représente une organisation locataire (tenant).

```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Espace de travail Acme Corporation",
  "parent": null,
  "parent_name": null,
  "metadata": {},
  "is_active": true,
  "max_members": 0,
  "member_count": 12,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-02T00:00:00Z",
  "created_by_email": "admin@acmecorp.com",
  "user_role": "owner"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | integer | Identifiant unique de l'organisation |
| `name` | string | Nom d'affichage de l'organisation |
| `slug` | string | Identifiant sûr pour les URL (utilisé dans l'en-tête `X-Org-Slug`) |
| `description` | string \| null | Description de l'organisation |
| `parent` | integer \| null | ID de l'organisation parente pour les locataires hiérarchiques |
| `parent_name` | string \| null | Nom de l'organisation parente |
| `metadata` | object | Paires clé-valeur personnalisées |
| `is_active` | boolean | Indique si l'organisation est active |
| `max_members` | integer | `0` = illimité |
| `member_count` | integer | Nombre actuel de membres |
| `created_at` | string (date-time) | Horodatage de création |
| `updated_at` | string (date-time) | Horodatage de la dernière mise à jour |
| `created_by_email` | string \| null | E-mail du créateur |
| `user_role` | string \| null | Code du rôle de l'utilisateur actuellement authentifié dans cette organisation |

---

## AuditLog (Journal d'Audit)

Entrée du journal des événements de sécurité.

```json
{
  "id": "uuid-string",
  "user": "uuid-string",
  "user_email": "admin@example.com",
  "action": "login",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "application": "uuid-string",
  "application_name": "Tableau de Bord Web",
  "details": {},
  "created_at": "2026-03-04T03:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant de l'entrée du journal |
| `user` | string (UUID) \| null | ID de l'utilisateur associé (le cas échéant) |
| `user_email` | string \| null | E-mail de l'utilisateur associé |
| `action` | string | L'action de sécurité effectuée (ex: "login", "2fa_enabled") |
| `ip_address` | string \| null | Adresse IP du client |
| `user_agent` | string \| null | Informations sur l'appareil ou chaîne User-Agent |
| `application` | string (UUID) \| null | ID de l'application utilisée pour l'action |
| `application_name` | string \| null | Nom d'affichage de l'application |
| `details` | object \| null | Données contextuelles supplémentaires (anciennement metadata) |
| `created_at` | string (date-time) | Horodatage de l'événement |

Consultez le [Guide de Sécurité](security.md#audit-logging) pour la liste complète des valeurs d'action (`action`).

---

## Role (Rôle)

```json
{
  "id": "uuid-string",
  "code": "admin",
  "name": "Administrateur",
  "description": "Accès complet à toutes les fonctionnalités du système",
  "permissions": [
    {
      "id": "uuid-string",
      "code": "users.manage",
      "name": "Gérer les utilisateurs"
    }
  ],
  "is_default": false,
  "created_at": "2026-03-01T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

Consultez le [Guide RBAC](rbac.md) pour les rôles intégrés et les décorateurs de permission.

---

## DeviceInfo (Informations sur l'Appareil)

Chaîne d'empreinte structurée envoyée par le client lors de la connexion.

**Format (v1) :**
```
v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Europe/Paris
```

| Clé | Description |
|---|---|
| `v` | Version du format (toujours `1`) |
| `os` | Système d'exploitation (`windows`, `android`, `ios`, `macos`, `linux`) |
| `osv` | Version de l'OS |
| `device` | `desktop`, `mobile`, `tablet`, `server`, `bot`, `api-client` |
| `arch` | Architecture du processeur (`x64`, `arm64`, `arm`, `x86`) |
| `app` | Nom de l'application |
| `appv` | Version de l'application |
| `runtime` | Navigateur/client d'exécution (`chrome`, `firefox`, `safari`, `curl`, `postman`, etc.) |
| `rtv` | Version de l'environnement d'exécution |
| `tz` | Fuseau horaire (ex: `Europe/Paris`) |

Consultez le [Guide de Sécurité](security.md#session--device-limits) pour les détails de configuration.
