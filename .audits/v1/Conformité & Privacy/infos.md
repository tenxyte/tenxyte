# Tenxyte — Conformité & Privacy Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit en profondeur de la conformité réglementaire (RGPD/GDPR, CCPA, SOC2…)
> et des mécanismes de protection de la vie privée du package Tenxyte.
> **Date** : 2026-02-27
> **Version auditée** : `0.9.1.7`

---

## 1. Positionnement réglementaire

### Nature juridique du projet

Tenxyte est une **librairie open-source** (MIT) distribuée sur PyPI. Elle est
**intégrée** dans des applications Django tierces par des développeurs.

Ce positionnement implique une **double responsabilité** :
- **Tenxyte** (en tant qu'éditeur de la librairie) : conçoit les mécanismes
  techniques de conformité (outils RGPD, anonymisation, audit, PII redaction…)
- **L'intégrateur** (le développeur/éditeur qui déploie Tenxyte) : agit comme
  *responsable du traitement* (RGPD Art. 4) et est responsable de la mise en
  conformité complète de son produit

> **Point critique pour l'audit** : Tenxyte fournit des *mécanismes* mais ne
> peut pas imposer leur usage. L'auditeur devra distinguer ce que le package
> **permet** de faire et ce que les intégrateurs **font effectivement**.

### Référentiels réglementaires couverts

| Réglementation | Couverture | Détail |
|---------------|------------|--------|
| **RGPD (UE) 2016/679** | Partielle — outils fournis | Art.17 (effacement), Art.20 (portabilité), Art.25 (Privacy by Design) |
| **CCPA (Californie)** | Indirecte | Les mécanismes RGPD couvrent partiellement le CCPA |
| **NIST SP 800-63B** | Partielle | Politique de mots de passe, 2FA, breach check |
| **OWASP ASVS** | Partielle | Authentification, gestion des sessions, logs |
| **SOC 2 Type II** | Infrastructure de l'intégrateur | Tenxyte fournit des briques (AuditLog, RBAC) |

---

## 2. Cartographie des données personnelles traitées

### Données collectées directement

| Donnée | Champ DB | Catégorie RGPD | Obligatoire | Collectée si |
|--------|----------|----------------|-------------|--------------|
| Email | `users.email` | Ordinaire (identifiant) | Non (ou téléphone) | Inscription classique |
| Prénom | `users.first_name` | Ordinaire | Non | Inscription |
| Nom | `users.last_name` | Ordinaire | Non | Inscription |
| Numéro de téléphone | `users.phone_country_code` + `phone_number` | Ordinaire | Non (ou email) | Inscription avec téléphone |
| Mot de passe hashé (bcrypt) | `users.password` | Sécurité — non exploitable | Oui si méthode classique | Inscription classique |
| Secret TOTP | `users.totp_secret` | Sécurité — non divulgable | Non | Activation 2FA |
| Codes backup 2FA (hashés SHA-256) | `users.backup_codes` | Sécurité | Non | Activation 2FA |
| Adresse IP (tentatives login) | `login_attempts.ip_address` | Ordinaire (identifiant indirect) | Audit | Chaque tentative |
| Adresse IP (refresh tokens) | `refresh_tokens.ip_address` | Ordinaire | Audit | Chaque session |
| Adresse IP (audit logs) | `audit_logs.ip_address` | Ordinaire | Audit | Chaque action sensible |
| User-Agent (device) | `refresh_tokens.device_info` | Ordinaire (identifiant indirect) | Non | Si device fingerprinting activé |
| User-Agent (audit logs) | `audit_logs.user_agent` | Ordinaire | Audit | Chaque action sensible |
| Date de dernière connexion | `users.last_login` | Ordinaire | Audit | Chaque connexion |
| Date de création du compte | `users.created_at` | Administrative | Oui | Inscription |

### Données collectées via OAuth / Social Login

| Provider | Données importées | Stockage |
|----------|------------------|----------|
| **Google** | email, prénom, nom, `sub` (ID Google), `picture` (URL), `email_verified` | `social_accounts` + `users` |
| **GitHub** | email (primary+verified), prénom, nom, ID GitHub, `avatar_url` | `social_accounts` + `users` |
| **Microsoft** | email (`mail` ou `userPrincipalName`), prénom, nom, ID Microsoft | `social_accounts` + `users` |
| **Facebook** | email, prénom, nom, ID Facebook, `picture.url` | `social_accounts` + `users` |

> **Note** : les `avatar_url` (URLs d'images de profil) sont stockés dans
> `social_accounts` mais **jamais dans la table principale `users`**. Ce sont
> des URLs externes, pas des images stockées localement.

### Données des agents IA (AIRS)

| Donnée | Table | Durée de conservation | Risque privacy |
|--------|-------|---------------------|---------------|
| `prompt_trace_id` | `audit_logs`, `agent_pending_actions` | Jusqu'à nettoyage manuel | Traçabilité LLM → données potentiellement sensibles |
| `agent_id` | `agent_tokens`, `audit_logs` | Durée de vie du token | Identification de l'agent IA |
| Payload des actions en attente | `agent_pending_actions.payload` | Jusqu'à expiration | Peut contenir des données métier sensibles |

---

## 3. Analyse des bases légales du traitement (RGPD Art. 6)

> **Important** : Tenxyte ne définit pas les bases légales — c'est la
> responsabilité de l'intégrateur/responsable de traitement. L'auditeur
> doit vérifier que chaque traitement est justifié par l'intégrateur.

| Traitement | Base légale probable | Article RGPD |
|-----------|---------------------|--------------|
| Compte utilisateur (email/password) | Exécution du contrat | Art. 6.1.b |
| Logs d'audit de sécurité | Intérêt légitime (sécurité) | Art. 6.1.f |
| Logs de tentatives de login | Intérêt légitime (sécurité) | Art. 6.1.f |
| Device fingerprinting | Intérêt légitime (sécurité) ou Consentement | Art. 6.1.a/f |
| Liaison compte OAuth | Consentement explicite | Art. 6.1.a |
| Données TOTP (2FA) | Intérêt légitime (sécurité) | Art. 6.1.f |
| Données AIRS agents IA | Contrat + Intérêt légitime | Art. 6.1.b/f |
| Historique des mots de passe | Intérêt légitime (sécurité) | Art. 6.1.f |
| Export données utilisateur | Obligation légale (Art. 20) | Art. 6.1.c |

---

## 4. Mécanismes RGPD implémentés

### 4.1 Droit à l'effacement (Art. 17) — Workflow complet

**Fichiers :** `models/gdpr.py`, `views/account_deletion_views.py`, `services/account_deletion_service.py`

Le droit à l'effacement est implémenté via un workflow à **5 états** avec double
confirmation et période de grâce :

```
PENDING → CONFIRMATION_SENT → CONFIRMED → COMPLETED
                                    ↓
                               CANCELLED (possible jusqu'à la fin de la période de grâce)
```

**Étapes détaillées :**

| Étape | Action | Délai | Sécurité |
|-------|--------|-------|---------|
| 1. Demande | POST `/request-account-deletion/` | Immédiat | Mot de passe requis + OTP si 2FA activé |
| 2. Confirmation email | Email avec token `secrets.token_urlsafe(48)` | TTL 24h | Token à usage unique |
| 3. Confirmation | POST `/confirm-account-deletion/` + token | Via email | Token cryptographique CSPRNG |
| 4. Période de grâce | Compte désactivé mais données intactes | 30 jours | Annulation possible |
| 5. Suppression | `user.soft_delete()` exécuté | À l'expiration | Anonymisation complète |

**Ce qui est anonymisé lors du `soft_delete()` :**

```python
email         → "deleted_<id>@deleted.local"
first_name    → ""
last_name     → ""
phone_*       → null
google_id     → null
totp_secret   → null
backup_codes  → []
is_2fa_enabled → False
is_active, is_staff, is_superuser → False
is_deleted    → True
deleted_at    → datetime.now()
anonymization_token → secrets.token_urlsafe(48)  # Pour audit sans PII
```

**Ce qui est conservé après anonymization :**

- `AuditLog` entries (IP + action — sans lien nominal à l'utilisateur)
- `DeletedAt` timestamp (anonymisé avec token opaque)
- Entrées dans les tables M2M révolues (roles, permissions — références vers des
  IDs sans données nominatives)

> **Lacune identifiée** : les `audit_logs` conservent l'`ip_address` et
> éventuellement le `user_agent` même après suppression du compte. L'IP est une
> donnée pseudo-anonyme. L'intégrateur doit définir une politique de rétention
> de ces logs indépendamment de la suppression du compte.

### 4.2 Droit à la portabilité (Art. 20) — Export de données

**Endpoint :** `POST /export-user-data/` (mot de passe requis)

**Données exportées en JSON :**

```json
{
  "user_info": {
    "id", "email", "first_name", "last_name",
    "phone_country_code", "phone_number",
    "is_email_verified", "is_phone_verified",
    "is_2fa_enabled", "created_at", "last_login"
  },
  "roles": [{ "code", "name", "assigned_at" }],
  "permissions": [{ "code", "name", "granted_at" }],
  "applications": [{ "name", "created_at" }],
  "audit_logs": [{ "action", "ip_address", "created_at", "details" }],
  "export_metadata": { "exported_at", "export_reason", "user_id" }
}
```

> **Limitations à noter pour l'audit :**
> - Les `audit_logs` exportés contiennent les **propres IPs** de l'utilisateur
>   (données personnelles incluses dans l'export par cohérence, mais potentiellement
>   sensibles si un tiers demandait l'export)
> - L'export est limité aux **100 derniers** audit logs
> - Les connexions OAuth (`SocialAccount`) ne sont **pas incluses** dans l'export
> - Les `RefreshToken` (historique de sessions) ne sont **pas inclus**
> - L'export est tracé dans `AuditLog` avec l'action `data_exported`

### 4.3 Privacy by Design (Art. 25)

**Mesures techniques implémentées :**

| Principe | Implémentation |
|---------|----------------|
| Minimisation des données | Seuls email OU téléphone requis ; prénom/nom optionnels |
| Pseudonymisation | Soft delete avec `anonymization_token` |
| Chiffrement en transit | Dépend de l'intégrateur (HTTPS) — Tenxyte force HSTS si configuré |
| Chiffrement au repos | Responsabilité de l'intégrateur (DB, disques) |
| Accès minimal (RBAC) | Permissions granulaires, principe du moindre privilège |
| Isolation multi-tenant | ContextVar strict — aucune fuite de données cross-tenant |
| Redaction PII agents IA | `PIIRedactionMiddleware` masque 10 champs sensibles |

---

## 5. PIIRedactionMiddleware — Protection de la vie privée face aux agents IA

**Fichier :** `src/tenxyte/middleware.py`

### Champs masqués dans les réponses JSON aux agents IA

```python
PII_FIELDS = {
    'email', 'phone', 'ssn', 'date_of_birth', 'address',
    'credit_card', 'password', 'totp_secret', 'backup_codes'
}
# Remplacement : "***REDACTED***"
# Récursif : objets imbriqués et listes
```

### Conditions d'activation

- `TENXYTE_AIRS_REDACT_PII = True` **ET** la requête utilise `AgentBearer` token
- Actif uniquement sur les **réponses** (JSON) — pas sur les requêtes entrantes

### Limite critique à documenter pour l'audit

Le masquage est **côté transport (HTTP response)** uniquement. Un agent IA
avec un accès direct à la base de données (hors Tenxyte API) pourrait contourner
cette protection. L'auditeur doit vérifier que les agents n'ont pas d'accès DB
direct.

---

## 6. Audit Logging — Traçabilité des accès aux données

**Fichier :** `src/tenxyte/models/security.py` — `AuditLog`

### Données enregistrées par entrée d'audit

| Champ | Type | Contenu |
|-------|------|---------|
| `action` | CharField | Action (voir liste ci-dessous) |
| `user` | FK nullable | Utilisateur concerné (null pour actions système) |
| `ip_address` | GenericIPAddressField | IP du client |
| `user_agent` | CharField (max 500) | User-Agent navigateur/client |
| `application` | FK nullable | Application cliente |
| `details` | JSONField | Contexte spécifique (device, nb sessions, etc.) |
| `agent_token` | FK nullable | Agent IA ayant déclenché l'action |
| `on_behalf_of` | FK nullable | Humain délégant si action AIRS |
| `prompt_trace_id` | CharField | ID de traçabilité LLM (si AIRS) |
| `created_at` | DateTimeField | Timestamp |

### Actions auditées (exhaustif)

```
# Authentification
login, login_failed, logout, logout_all, token_refresh

# Mots de passe
password_change, password_reset_request, password_reset_complete

# 2FA
2fa_enabled, 2fa_disabled, 2fa_backup_used

# Compte
account_created, account_locked, email_verified,
phone_verified, new_device_detected

# RBAC
role_assigned, role_removed, permission_changed

# Applications
app_created, app_credentials_regenerated

# Sécurité
suspicious_activity, session_limit_exceeded, device_limit_exceeded

# AIRS (agents IA)
agent_action

# RGPD
data_exported, deletion_confirmation_email_failed,
deletion_completion_email_failed
```

### Politique de rétention des logs (lacune)

> **Point critique pour l'audit** : Tenxyte ne définit pas de politique de
> rétention automatique pour `AuditLog`. Les logs s'accumulent indéfiniment
> sauf suppression manuelle ou via tâche Celery custom de l'intégrateur.
> 
> Recommandation RGPD : définir une durée de conservation (ex: 90 jours pour
> les logs fonctionnels, 5 ans pour les logs de sécurité critiques), et
> implémenter un nettoyage automatique côté intégrateur.

---

## 7. Authentification OAuth — Données tiers et consentement

**Fichier :** `src/tenxyte/services/social_auth_service.py`

### Données reçues par provider OAuth

| Provider | API appelée | Données reçues |
|----------|-----------|----------------|
| **Google** | `googleapis.com/oauth2/v3/userinfo` | `sub`, `email`, `email_verified`, `given_name`, `family_name`, `picture` |
| **GitHub** | `api.github.com/user` + `/user/emails` | `id`, `email`, `name`, `avatar_url` |
| **Microsoft** | `graph.microsoft.com/v1.0/me` | `id`, `mail`/`userPrincipalName`, `givenName`, `surname` |
| **Facebook** | `graph.facebook.com/me?fields=id,email,first_name,last_name,picture` | `id`, `email`, `first_name`, `last_name`, `picture.url` |

### Logique de fusion de comptes (Account Merging)

Lorsqu'un utilisateur se connecte via OAuth avec un email déjà présent en base :

1. Recherche d'une `SocialConnection` existante (provider + `provider_user_id`)
2. Si trouvée → utilisateur existant (liaison déjà faite)
3. Si non trouvée → recherche par `email` (case-insensitive)
4. Si email trouvé → **fusion automatique** (liaison de l'OAuth au compte existant)
5. Si aucun → création d'un nouveau compte

> **Risque de privacy pour l'audit** : la **fusion automatique par email** peut
> lier sans confirmation explicite un compte OAuth externe à un compte existant.
> Si un attaquant contrôle un compte OAuth avec le même email qu'une victime,
> il pourrait accéder au compte de la victime.
> 
> La surface d'attaque est limitée car les providers vérifient l'email
> (`email_verified: true`), mais un email non vérifié chez GitHub (par exemple,
> si l'utilisateur a un email non public) pourrait poser problème.
> 
> **Recommandation** : activer uniquement les providers qui retournent
> `email_verified: true` ou implémenter une confirmation email lors du premier
> lien OAuth.

### Données stockées dans `social_accounts`

```
provider, provider_user_id, email, first_name, last_name, avatar_url
```

Ces données sont une **copie des données du provider au moment du login** —
elles ne se mettent pas à jour automatiquement et peuvent devenir obsolètes.

---

## 8. Gestion des sessions et device fingerprinting

### Device fingerprinting

**Fichier :** `src/tenxyte/device_info.py`

Le device fingerprinting collecte des informations depuis le `User-Agent` HTTP.
Ces informations sont :
- Stockées dans `refresh_tokens.device_info` (durée de vie du refresh token)
- Logguées dans `audit_logs.user_agent` (durée de vie du log)
- Utilisées pour détecter les nouveaux devices (`new_device_detected` audit)
- Utilisées pour enforcer les limites de devices (`DEVICE_LIMIT_ENABLED`)

> **Données collectées** : OS, navigateur, type d'appareil — **pas de cookies**,
> pas de fingerprinting actif (canvas, WebGL, etc.). C'est un fingerprinting
> passif basé uniquement sur le User-Agent HTTP.

### Limites de sessions

Configurable via `TENXYTE_SESSION_LIMIT_ENABLED` et `TENXYTE_DEFAULT_MAX_SESSIONS`.
L'action `revoke_oldest` révoque les sessions les plus anciennes → peut créer
une **déconnexion forcée sans notification** de l'utilisateur sur les appareils
les plus anciens.

---

## 9. Chiffrement et protection des données sensibles

### En transit

Tenxyte ne gère pas directement TLS/HTTPS — c'est la responsabilité de la
couche infrastructure (nginx, Gunicorn) de l'intégrateur. Tenxyte peut injecter
le header `Strict-Transport-Security` via `SecurityHeadersMiddleware` si configuré.

### Au repos

| Donnée | Protection | Méthode |
|--------|-----------|---------|
| Mot de passe | ✅ Hashé | bcrypt (irréversible) |
| Secret application | ✅ Hashé | bcrypt + base64 (irréversible) |
| Token OTP | ✅ Hashé | SHA-256 (irréversible, haute entropie) |
| Token magic link | ✅ Hashé | SHA-256 (irréversible) |
| Codes backup 2FA | ✅ Hashés | SHA-256 |
| Secret TOTP (`totp_secret`) | ❌ En clair | Nécessaire pour la vérification |
| Refresh token | ❌ En clair | Utilisé pour lookup DB |
| Agent token | ❌ En clair | Utilisé pour validation directe |
| IP addresses | ❌ En clair | Données opérationnelles |
| User-Agent | ❌ En clair | Données opérationnelles |
| Données OAuth (`avatar_url`, noms) | ❌ En clair | Données non sensibles |

> **Lacune notable** : `totp_secret`, `refresh_token`, `agent_token` et les
> adresses IP sont stockés en clair. Pour une conformité maximale, le chiffrement
> symétrique au repos des secrets TOTP (AES-256-GCM via une clé applicative)
> serait recommandé — mais n'est pas implémenté. C'est un choix d'architecture
> conscient (performance) que l'auditeur devra évaluer.

---

## 10. Politique de rétention des données

### Rétentions actuellement définies par Tenxyte

| Donnée | Durée de vie | Déclencheur de suppression |
|--------|-------------|---------------------------|
| `OTPCode` | 10–15 min (expiration) | Marqué `is_used=True`, non supprimé automatiquement |
| `MagicLinkToken` | 15 min (expiration) | Marqué `is_used=True` |
| `WebAuthnChallenge` | 5 min (expiration) | Marqué `is_used=True` |
| `AgentPendingAction` | 10 min (expiration) | Persist en DB jusqu'à nettoyage manuel |
| `AccountDeletionRequest` | 30 jours de grâce | Persist après `COMPLETED` |
| `BlacklistedToken` | Durée du JWT | Nettoyable via `cleanup_expired()` |
| `RefreshToken` | Configurable (default 7–30j) | Révocation manuelle ou rotation |
| `LoginAttempt` | Indéfini ⚠️ | Aucun nettoyage automatique |
| `AuditLog` | Indéfini ⚠️ | Aucun nettoyage automatique |
| `PasswordHistory` | Indéfini ⚠️ | Nettoyage lors d'un nouveau hash uniquement |

> **⚠️ Points critiques pour la conformité RGPD** :
> - `LoginAttempt`, `AuditLog`, `OTPCode` expiré, `AgentPendingAction` expiré,
>   `AccountDeletionRequest` complétée — **aucune suppression automatique**.
>   L'intégrateur doit mettre en place des tâches périodiques (Celery Beat, cron)
>   pour nettoyer ces données selon sa politique de rétention documentée.

---

## 11. Tiers recevant des données

### Services externes appelés par Tenxyte

| Service | Données envoyées | Conditions |
|---------|-----------------|------------|
| **HaveIBeenPwned API** | SHA-1 prefix (5 chars) du mot de passe | Si `BREACH_CHECK_ENABLED = True` |
| **Google OAuth API** | Code d'autorisation, `CLIENT_ID`, `CLIENT_SECRET` | Si connexion Google utilisée |
| **GitHub API** | Code d'autorisation, credentials | Si connexion GitHub utilisée |
| **Microsoft Graph API** | Code d'autorisation, credentials | Si connexion Microsoft utilisée |
| **Facebook Graph API** | `access_token` (token de l'utilisateur) | Si connexion Facebook utilisée |
| **Twilio (SMS)** | Numéro de téléphone, corps OTP | Si `TENXYTE_SMS_BACKEND = TwilioBackend` |
| **SendGrid (Email)** | Email de destination, corps | Si `TENXYTE_EMAIL_BACKEND = SendGridBackend` |

> **Note HIBP** : grâce au protocole k-anonymity, **le mot de passe en clair ou
> le hash complet ne quitte jamais le serveur**. Seuls 5 caractères hexadécimaux
> (20 bits) du SHA-1 sont transmis — confidentialité maximale.

> **Note Twilio/SendGrid** : ces providers de communication reçoivent des données
> personnelles (email, téléphone). L'intégrateur doit avoir un DPA (Data
> Processing Agreement) avec chacun.

---

## 12. Droits des personnes concernées — Couverture par les APIs

| Droit RGPD | Endpoint | Statut |
|-----------|---------|--------|
| Art. 15 — Droit d'accès | `GET /me/` + `POST /export-user-data/` | ✅ Partiellement implémenté |
| Art. 16 — Droit de rectification | `PUT/PATCH /me/` (si implémenté par l'intégrateur) | ⚠️ Dépend de l'intégrateur |
| Art. 17 — Droit à l'effacement | `POST /request-account-deletion/` | ✅ Implémenté (workflow 5 états) |
| Art. 18 — Droit à la limitation | Non implémenté (compte doit être actif ou deleted) | ❌ Non couvert |
| Art. 20 — Droit à la portabilité | `POST /export-user-data/` | ✅ Partiellement implémenté |
| Art. 21 — Droit d'opposition | Non implémenté | ❌ Responsabilité de l'intégrateur |
| Art. 22 — Décisions automatisées | AIRS circuit breaker (suspension auto) | ⚠️ À documenter dans PIA |

---

## 13. Analyse des risques privacy spécifiques

### Risque 1 — Fusion de comptes OAuth sans confirmation (Sévérité : Moyenne)

**Description** : un compte OAuth avec un email non vérifié ou un email correspondant
à un compte existant est automatiquement fusionné sans confirmation explicite de
l'utilisateur concerné.

**Mitigation existante** : les providers Google, Microsoft, Facebook marquent
`email_verified: true`. GitHub peut ne pas fournir d'email vérifié.

**Recommandation** : ajouter une option `TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL`
pour rejeter les logins OAuth sans email vérifié.

### Risque 2 — Logs d'audit non purgés (Sévérité : Moyenne-Haute)

**Description** : `AuditLog` et `LoginAttempt` s'accumulent indéfiniment avec
des données personnelles (IP, User-Agent). En l'absence de politique de rétention,
une base de données de plusieurs années peut constituer un profil comportemental
non conforme aux principes de minimisation RGPD.

**Recommandation** : fournir des tâches Celery prêtes à l'emploi pour la purge
des logs après N jours.

### Risque 3 — Prompt trace ID dans les logs AIRS (Sévérité : Faible-Moyenne)

**Description** : le `prompt_trace_id` stocké dans `AuditLog` peut permettre de
retrouver le contexte complet d'une interaction LLM dans les logs du système IA.
Si le prompt contient des données personnelles (nom, email mentionné dans une
requête), un croisement entre les logs Tenxyte et les logs LLM pourrait reconstituer
des PII.

**Recommandation** : documenter la politique de gestion du `prompt_trace_id` et
s'assurer qu'il ne contient que des identifiants opaques (UUID), pas de données en clair.

### Risque 4 — `totp_secret` non chiffré (Sévérité : Faible)

**Description** : le secret TOTP est stocké en clair en base. Si la DB est
compromise (dump SQL), l'attaquant peut reproduire le 2FA de chaque utilisateur.

**Mitigation** : l'accès à la DB nécessite des credentials séparés. Le 2FA
ajoute une couche de protection même si les credentials initiaux sont compromis.

**Recommandation** : chiffrement AES-256-GCM du `totp_secret` avec une clé
applicative distincte de la clé JWT.

### Risque 5 — Export de données limité (Sévérité : Faible)

**Description** : l'export RGPD (Art. 20) ne couvre pas toutes les données :
sessions (`RefreshToken`), connexions sociales (`SocialConnection`), demandes
de suppression passées, historique de mots de passe, tentatives de login.

**Recommandation** : étendre `export_user_data` pour couvrir toutes les tables
où l'utilisateur est référencé.

---

## 14. Points de configuration liés à la confidentialité

```python
# settings.py — variables de configuration privacy-relevant

# Breach check (HaveIBeenPwned)
TENXYTE_BREACH_CHECK_ENABLED = True         # Activer la vérification
TENXYTE_BREACH_CHECK_REJECT = True          # Rejeter les mots de passe fuités

# Masquage PII pour les agents IA
TENXYTE_AIRS_REDACT_PII = True             # Activer le masquage PII AIRS

# Audit logging
TENXYTE_AUDIT_LOGGING_ENABLED = True        # Activer les logs d'audit

# Mode sécurité (détermine plusieurs paramètres privacy)
TENXYTE_SHORTCUT_SECURE_MODE = 'robust'     # 'starter' | 'medium' | 'robust'

# Device fingerprinting
TENXYTE_DEVICE_LIMIT_ENABLED = True         # Active le tracking de devices

# Session limit
TENXYTE_SESSION_LIMIT_ENABLED = True        # Active le suivi des sessions

# Historique des mots de passe
TENXYTE_PASSWORD_HISTORY_ENABLED = True
TENXYTE_PASSWORD_HISTORY_COUNT = 5          # Nb de mots de passe mémorisés

# Magic Link
TENXYTE_MAGIC_LINK_ENABLED = False          # Désactivé dans 'robust' (vecteur email)

# Providers OAuth activés
TENXYTE_SOCIAL_PROVIDERS = ['google', 'github', 'microsoft', 'facebook']
```

---

## 15. Checklist de conformité pour l'auditeur

### Ce que Tenxyte implémente ✅

- [x] Droit à l'effacement avec workflow documenté et période de grâce
- [x] Droit à la portabilité (export JSON)
- [x] Anonymisation des PII lors de la suppression
- [x] Conservation des `AuditLog` même après suppression (obligation légale)
- [x] Privacy by Design : minimisation des données collectées
- [x] Chiffrement des mots de passe (bcrypt, irréversible)
- [x] k-anonymity pour la vérification HIBP
- [x] Masquage PII dans les réponses aux agents IA
- [x] Traçabilité complète des actions sensibles (AuditLog)
- [x] Isolation des données multi-tenant (RGPD Art. 25)
- [x] Contrôle d'accès RBAC granulaire

### Ce que Tenxyte ne couvre pas (responsabilité de l'intégrateur) ⚠️

- [ ] Politique de rétention des logs (pas de purge automatique)
- [ ] Registre des activités de traitement (RGPD Art. 30)
- [ ] Analyse d'impact (PIA/DPIA) — RGPD Art. 35
- [ ] Consentement granulaire (opt-in par finalité)
- [ ] Droit à la limitation du traitement (Art. 18)
- [ ] Droit d'opposition (Art. 21)
- [ ] Notification à l'autorité de contrôle (violation Art. 33)
- [ ] Notification aux personnes concernées (violation Art. 34)
- [ ] DPA avec Twilio, SendGrid, Google, GitHub, Microsoft, Facebook
- [ ] Politique de confidentialité (mentions légales)
- [ ] Chiffrement au repos des données non sensibles (IP, UA)
- [ ] Chiffrement du `totp_secret`
- [ ] Base de données conforme (RGPD recommande hébergement UE)
- [ ] Transferts internationaux de données (si usage cloud US)

---

## 16. Contenu des tokens JWT — Analyse Privacy

**Fichier :** `src/tenxyte/services/jwt_service.py`

### Payload d'un access token JWT Tenxyte

```json
{
  "type": "access",
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "app_id":  "7b3c2e1d-...",
  "iat": 1709035200,
  "exp": 1709036100
}
```

### Analyse : données personnelles superflues ?

| Claim JWT | Nature | Données personnelles ? | Justification |
|-----------|--------|----------------------|---------------|
| `type` | Technique | ❌ Non | Constante `"access"` |
| `jti` | Technique | ❌ Non | UUID aléatoire (lien à la blacklist) |
| `user_id` | Identifiant opaque | ⚠️ Pseudo-PII | UUID de l'utilisateur — pseudonyme, mais permet de retrouver le profil |
| `app_id` | Identifiant opaque | ⚠️ Pseudo-PII | UUID de l'application cliente |
| `iat` / `exp` | Technique | ❌ Non | Timestamps ISO |

> **Évaluation** : le payload JWT Tenxyte est **minimal** — aucune donnée
> nominale (email, nom, téléphone) n'y figure. Seuls des identifiants opaques
> (`user_id`, `app_id`) sont inclus, conformément au principe de minimisation.
>
> **Risque résiduel** : le JWT est encodé en base64 (non chiffré) — toute
> partie l'interceptant peut lire `user_id` et `app_id`. Bien que ces UUIDs
> soient des identifiants pseudo-anonymes, un réseau interne qui loggue les
> JWTs aurait accès à ces identifiants. La recommandation OWASP est de ne
> **jamais inclure de PII dans un JWT non chiffré**.

### Points à vérifier pour l'audit

- [ ] Des claims custom ont-ils été ajoutés par l'intégrateur (email, rôles, nom) ?
- [ ] Les logs d'accès (nginx, reverse proxy) capturent-ils le header `Authorization`
  contenant le JWT ? Si oui, les `user_id` sont dans les logs.
- [ ] Le JWT est-il transmis via URL query parameter dans certains cas
  (ex : magic links) ? → risque Referer header leak.

---

## 17. Droit à l'effacement — Invalidation des sessions actives

> Question directe : **le `soft_delete()` révoque-t-il les sessions actives ?**

### Analyse du code `AccountDeletionRequest.execute_deletion()`

```python
# models/gdpr.py — execute_deletion()
def execute_deletion(self, processed_by=None):
    if self.status != 'confirmed':
        return False

    success = self.user.soft_delete()   # ← seul appel

    if success:
        self.status = 'completed'
        ...
    return success
```

```python
# models/auth.py — User.soft_delete()
def soft_delete(self):
    self.email = f"deleted_{self.id}@deleted.local"
    self.first_name = ""
    # ... anonymisation des PII ...
    self.is_active = False              # ← compte désactivé
    self.is_deleted = True
    self.save()
    return True
    # ⚠️ Aucune révocation de RefreshToken ici
```

### Ce qui est invalidé lors de la suppression

| Ressource | Invalidée ? | Mécanisme |
|-----------|------------|-----------|
| **Accès via JWT actuel** | ✅ Oui (indirect) | `is_active = False` → `require_jwt` vérifie `user.is_active` → 401 |
| **Refresh tokens existants** | ❌ **NON** | Restent valides en DB (`is_revoked = False`) — mais impossibles à utiliser car `is_active = False` bloque la génération d'un nouveau JWT |
| **Agent tokens (AIRS)** | ❌ **NON** | Restent actifs en DB — mais bloqués par `is_active` check |
| **Sessions magic link** | ❌ **NON** | `MagicLinkToken` reste en DB |
| **Challenges WebAuthn** | ❌ **NON** | Restent en DB jusqu'à expiration |

### Évaluation de conformité RGPD

> **Conclusion** : le droit à l'effacement **invalide fonctionnellement** les
> sessions actives via `is_active = False` — un utilisateur supprimé ne peut
> plus s'authentifier ni utiliser un access token existant.
>
> Cependant, **les refresh tokens, agent tokens et magic links ne sont pas
> révoqués en DB**. En cas de réactivation accidentelle du compte (ex: bug,
> manipulation directe en DB), ces tokens seraient à nouveau utilisables.
>
> **Recommandation RGPD Art. 17** : la révocation explicite de tous les tokens
> actifs lors de la suppression (`RefreshToken.objects.filter(user=user).update(is_revoked=True)`)
> serait une meilleure pratique, même si l'effet pratique actuel est suffisant
> grâce au check `is_active`.

### Checklist supplémentaire pour l'audit

- [ ] Vérifier que le JWT access token existant est bien rejeté immédiatement
  après `soft_delete()` (pas de délai de propagation cache) ?
- [ ] Les refresh tokens orphelins sont-ils nettoyés par `tenxyte_cleanup` ?
  → Oui, via `expires_at < now` mais pas immédiatement à la suppression.
- [ ] Un compte supprimé peut-il être réactivé (`is_active = True` en DB) et
  récupérer l'accès via un refresh token non révoqué ?
