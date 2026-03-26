# Référence des Schémas

Ce document décrit les composants de schéma réutilisables utilisés dans l'API Tenxyte. Ceux-ci correspondent aux composants `$ref` de la spécification OpenAPI (`openapi_schema.json`).

## Table des matières

- [Utilisateur](#utilisateur)
- [TokenPair](#tokenpair)
- [Réponse d'Erreur](#réponse-derreur)
- [Réponse Paginée](#réponse-paginée)
- [Organisation](#organisation)
- [Journal d'Audit](#journal-daudit)
- [Rôle](#rôle)
- [Permission](#permission)
- [Session](#session)
- [Appareil](#appareil)
- [Tentative de Connexion](#tentative-de-connexion)
- [Jeton sur Liste Noire](#jeton-sur-liste-noire)
- [Informations sur l'Appareil](#informations-sur-lappareil)

---

## Utilisateur

Représente un utilisateur Tenxyte authentifié.

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "username": null,
  "phone": "+33612345678",
  "avatar": "https://cdn.example.com/avatars/user.jpg",
  "bio": null,
  "timezone": "Europe/Paris",
  "language": "fr",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_2fa_enabled": false,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-03-15T10:30:00Z",
  "last_login": "2026-03-01T12:00:00Z",
  "custom_fields": null,
  "preferences": {
    "email_notifications": true,
    "sms_notifications": false,
    "marketing_emails": false
  },
  "roles": ["admin"],
  "permissions": ["users.view", "users.manage"]
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant unique de l'utilisateur |
| `email` | string \| null | Email de connexion principal |
| `username` | string \| null | Nom d'utilisateur optionnel |
| `phone` | string \| null | Numéro de téléphone formaté (ex: +33612345678) |
| `avatar` | string \| null | URL de l'image de l'avatar de l'utilisateur |
| `bio` | string \| null | Courte biographie |
| `timezone` | string \| null | Fuseau horaire préféré de l'utilisateur |
| `language` | string \| null | Code langue ISO (ex: 'en', 'fr') |
| `first_name` / `last_name` | string | Nom à afficher |
| `is_active` | boolean | Indique si le compte est actif |
| `is_email_verified` | boolean | Indique si l'email a été vérifié |
| `is_phone_verified` | boolean | Indique si le numéro de téléphone a été vérifié |
| `is_2fa_enabled` | boolean | Indique si l'authentification à deux facteurs TOTP est active |
| `created_at` | string (date-time) | Horodatage de la création du compte |
| `updated_at` | string (date-time) \| null | Horodatage de la dernière mise à jour |
| `last_login` | string (date-time) \| null | Horodatage de la dernière connexion |
| `custom_fields` | object \| null | Métadonnées d'extension pour les modèles d'utilisateurs personnalisés |
| `preferences` | object | Préférences de notification de l'utilisateur |
| `roles` | string[] | Liste plate des codes de rôles assignés |
| `permissions` | string[] | Liste plate des codes de permissions (ex: `["users.view", "users.manage"]`) |

---

## TokenPair

Délivré lors d'une connexion réussie ou d'un rafraîchissement de jeton.

```json
{
  "access_token": "<JWT access token>",
  "refresh_token": "<JWT refresh token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_expires_in": 86400,
  "device_summary": "Windows 11 Desktop"
}
```

| Champ | Type | Description |
|---|---|---|
| `access_token` | JWT string | Jeton d'accès à courte durée de vie |
| `refresh_token` | JWT string | Jeton de rafraîchissement à longue durée de vie |
| `token_type` | string | Type de jeton (toujours "Bearer") |
| `expires_in` | integer | Expiration du jeton d'accès en secondes |
| `refresh_expires_in` | integer | Expiration du jeton de rafraîchissement en secondes |
| `device_summary` | string \| null | Description de l'appareil de l'utilisateur (si `device_info` a été envoyé) |

> **Mode cookie :** Lorsque `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED=True`, le champ `refresh_token` est omis du corps JSON. Il est transmis via un cookie `HttpOnly; Secure; SameSite`. Voir le [Guide de Sécurité](security.md#cookie-based-refresh-tokens) pour plus de détails.

---

## Réponse d'Erreur

Renvoyée pour toutes les réponses `4xx` et `5xx`.

```json
{
  "error": "Message lisible par l'homme",
  "code": "CODE_LISIBLE_PAR_MACHINE",
  "details": {
    "field_name": ["Liste des erreurs pour ce champ"]
  }
}
```

| Champ | Type | Description |
|---|---|---|
| `error` | string | Description destinée à l'utilisateur |
| `code` | string | Identifiant d'erreur lisible par machine (voir ci-dessous) |
| `details` | object \| null | Dictionnaire contenant les erreurs de validation au niveau des champs. Les clés sont les noms des champs, les valeurs sont des tableaux de chaînes d'erreurs. |

### Codes d'Erreurs Courants

| Code | Statut HTTP | Signification |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Mauvais email/mot de passe |
| `ACCOUNT_LOCKED` | 401 | Trop de tentatives de connexion échouées |
| `2FA_REQUIRED` | 403 | La connexion nécessite un code TOTP |
| `TOKEN_EXPIRED` | 401 | Le jeton d'accès a expiré |
| `TOKEN_BLACKLISTED` | 401 | Le jeton a été révoqué (déconnexion) |
| `PERMISSION_DENIED` | 403 | Rôle/permission insuffisant |
| `SESSION_LIMIT_EXCEEDED` | 403 | Trop de sessions simultanées |
| `DEVICE_LIMIT_EXCEEDED` | 403 | Trop d'appareils enregistrés |
| `RATE_LIMITED` | 429 | Trop de requêtes |
| `MISSING_REFRESH_TOKEN` | 400 | Pas de jeton de rafraîchissement dans le corps ou le cookie |
| `INVALID_REDIRECT_URI` | 400 | redirect_uri non autorisé dans la liste blanche de l'application |
| `ADMIN_2FA_SETUP_REQUIRED` | 403 | L'administrateur doit activer la 2FA avant de se connecter |
| `INVALID_2FA_CODE` | 401 | Code TOTP ou code de secours invalide |
| `PASSWORD_BREACHED` | 400 | Mot de passe trouvé dans la base de données HIBP |
| `PASSWORD_REUSED` | 400 | Mot de passe identique à une entrée récente de l'historique |
| `INVALID_PASSWORD` | 400 | Mot de passe actuel incorrect (flux de changement) |
| `INVALID_OTP` | 400 | Code OTP de vérification incorrect |
| `OTP_EXPIRED` | 400 | Le code OTP a expiré |
| `RESET_FAILED` | 400 | Échec de la réinitialisation du mot de passe |
| `ORG_NOT_FOUND` | 404 | L'en-tête X-Org-Slug ne correspond pas |
| `NOT_ORG_MEMBER` | 403 | L'utilisateur n'est pas membre de l'organisation fournie |

---

## Réponse Paginée

Tous les points de terminaison de liste renvoient une enveloppe paginée personnalisée (`TenxytePagination`) :

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

## Organisation

Représente une organisation locataire (tenant).

```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Acme Corporation Workspace",
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
| `slug` | string | Identifiant sécurisé pour les URL (utilisé dans l'en-tête `X-Org-Slug`) |
| `description` | string \| null | Description de l'organisation |
| `parent` | integer \| null | ID de l'organisation parente pour les locataires hiérarchiques |
| `parent_name` | string \| null | Nom de l'organisation parente |
| `metadata` | object | Paires clé-valeur personnalisées |
| `is_active` | boolean | Indique si l'organisation est active |
| `max_members` | integer | `0` = illimité |
| `member_count` | integer | Nombre actuel de membres |
| `created_at` | string (date-time) | Horodatage de la création |
| `updated_at` | string (date-time) | Horodatage de la dernière mise à jour |
| `created_by_email` | string \| null | Email du créateur |
| `user_role` | string \| null | Code du rôle de l'utilisateur authentifié actuel dans cette organisation |

---

## Journal d'Audit

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
  "application_name": "Web Dashboard",
  "details": {},
  "created_at": "2026-03-04T03:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant de l'entrée du journal |
| `user` | string (UUID) \| null | ID utilisateur associé (le cas échéant) |
| `user_email` | string \| null | Email de l'utilisateur associé |
| `action` | string | L'action de sécurité effectuée (ex: "login", "2fa_enabled") |
| `ip_address` | string \| null | Adresse IP du client |
| `user_agent` | string \| null | Infos sur l'appareil ou chaîne User-Agent |
| `application` | string (UUID) \| null | ID de l'application utilisée pour l'action |
| `application_name` | string \| null | Nom d'affichage de l'application |
| `details` | object \| null | Données contextuelles supplémentaires (anciennement metadata) |
| `created_at` | string (date-time) | Horodatage de l'événement |

Voir le [Guide de Sécurité](security.md#audit-logging) pour la liste complète des valeurs `action`.

---

## Rôle

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
      "name": "Gérer les Utilisateurs",
      "description": "Permet de créer, modifier et supprimer des utilisateurs",
      "parent": null,
      "children": [],
      "created_at": "2026-03-01T00:00:00Z"
    }
  ],
  "is_default": false,
  "created_at": "2026-03-01T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

Voir le [Guide RBAC](rbac.md) pour les rôles intégrés et les décorateurs de permission.

---

## Permission

```json
{
  "id": "uuid-string",
  "code": "users.manage",
  "name": "Gérer les Utilisateurs",
  "description": "Permet de créer, modifier et supprimer des utilisateurs",
  "parent": null,
  "children": [],
  "created_at": "2026-03-01T00:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant unique |
| `code` | string | La chaîne de code de permission |
| `name` | string | Nom lisible par l'homme |
| `description` | string \| null | Description détaillée |
| `parent` | object \| null | Permission parente (id, code) |
| `children` | array of objects | Permissions enfants (id, code, name) |
| `created_at` | string (date-time) | Horodatage de la création |

---

## Session

Représente une session utilisateur active.

```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "device_info": {},
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "is_current": true,
  "created_at": "2026-03-01T00:00:00Z",
  "last_activity": "2026-03-01T12:00:00Z",
  "expires_at": "2026-03-31T00:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | Identifiant unique de session |
| `user_id` | string (UUID) | ID utilisateur associé |
| `device_info` | object | Détails analysés à partir de la chaîne DeviceInfo |
| `ip_address` | string | Dernière adresse IP |
| `user_agent` | string | Navigateur / Client |
| `is_current` | boolean | Indique s'il s'agit de la session effectuant l'appel API actuel |
| `created_at` | string (date-time) | Heure de création de la session |
| `last_activity` | string (date-time) | Heure de la dernière activité |
| `expires_at` | string (date-time) | Heure d'expiration de la session |

---

## Appareil

Représente un appareil utilisateur suivi pour la sécurité contextuelle.

```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "device_fingerprint": "hash-string",
  "device_name": "Windows 11 Desktop",
  "device_type": "desktop",
  "platform": "windows",
  "browser": "chrome",
  "is_trusted": true,
  "last_seen": "2026-03-01T12:00:00Z",
  "created_at": "2026-02-01T00:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | ID de l'enregistrement de l'appareil |
| `user_id` | string (UUID) | ID utilisateur associé |
| `device_fingerprint` | string | Empreinte numérique unique du client (hash) |
| `device_name` | string | Nom d'affichage |
| `device_type` | string | Ex: desktop, mobile |
| `platform` | string | Plateforme du système d'exploitation |
| `browser` | string | Identifiant du navigateur |
| `is_trusted` | boolean | Vrai si marqué comme de confiance par l'utilisateur (contourne certains contrôles 2FA) |
| `last_seen` | string (date-time) | Dernière connexion depuis cet appareil |
| `created_at` | string (date-time) | Horodatage de la première apparition |

---

## Tentative de Connexion

Enregistrements de toutes les tentatives de connexion pour l'audit de sécurité et le blocage.

```json
{
  "id": "uuid-string",
  "identifier": "user@example.com",
  "ip_address": "203.0.113.42",
  "application": "uuid-string",
  "success": false,
  "failure_reason": "invalid_password",
  "created_at": "2026-03-01T12:00:00Z"
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | ID de la tentative |
| `identifier` | string | Email ou nom d'utilisateur utilisé pour la connexion |
| `ip_address` | string | IP du client |
| `application` | string (UUID) \| null | Application utilisée |
| `success` | boolean | Vrai si réussi |
| `failure_reason` | string \| null | Code détaillant pourquoi la tentative a échoué |
| `created_at` | string (date-time) | Horodatage |

---

## Jeton sur Liste Noire

Enregistrements des jetons JWT révoqués.

```json
{
  "id": "uuid-string",
  "token_jti": "jwt-uuid-id",
  "user": "uuid-string",
  "user_email": "user@example.com",
  "blacklisted_at": "2026-03-01T12:00:00Z",
  "expires_at": "2026-03-01T14:00:00Z",
  "reason": "logout",
  "is_expired": true
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | string (UUID) | ID de l'enregistrement |
| `token_jti` | string | La réclamation 'jti' du JWT |
| `user` | string (UUID) \| null | ID utilisateur associé |
| `user_email` | string \| null | Chaîne d'email |
| `blacklisted_at` | string (date-time) | Quand il a été révoqué |
| `expires_at` | string (date-time) | Heure d'expiration naturelle du jeton |
| `reason` | string | Ex: logout, security |
| `is_expired` | boolean | Vrai si l'heure d'expiration naturelle est dépassée |

---

## Informations sur l'Appareil

Chaîne d'empreinte numérique structurelle envoyée par le client lors de la connexion.

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
| `arch` | Architecture CPU (`x64`, `arm64`, `arm`, `x86`) |
| `app` | Nom de l'application |
| `appv` | Version de l'application |
| `runtime` | Navigateur/client d'exécution (`chrome`, `firefox`, `safari`, `curl`, `postman`, etc.) |
| `rtv` | Version du runtime |
| `tz` | Fuseau horaire (ex: `Europe/Paris`) |

Voir le [Guide de Sécurité](security.md#session--device-limits) pour les détails de configuration.
