# Référence des Paramètres

**Table des Matières**
- [Priorité des Paramètres](#priorite-des-parametres)
- [Mode de Sécurité Raccourci (Shortcut Secure Mode)](#shortcut-secure-mode) (1)
- [Paramètres Essentiels (Core)](#core-settings) (6)
- [JWT](#jwt) (9)
- [Authentification à Deux Facteurs (TOTP)](#two-factor-authentication-totp) (3)
- [OTP (Vérification E-mail / SMS)](#otp-email--sms-verification) (4)
- [Politique de Mot de Passe](#password-policy) (9)
- [Limitation de Débit et Verrouillage de Compte](#rate-limiting--account-lockout) (5)
- [Limites de Sessions et d'Appareils](#session--device-limits) (6)
- [Multi-Application](#multi-application) (3)
- [CORS](#cors) (8)
- [En-têtes de Sécurité](#security-headers) (2)
- [Connexion Sociale (OAuth2)](#social-login-oauth2) (11)
- [WebAuthn / Passkeys (FIDO2)](#webauthn--passkeys-fido2) (4)
- [Vérification des Mots de Passe Compromis (HaveIBeenPwned)](#breach-password-check-haveibeenpwned) (2)
- [Lien Magique (Magic Link / Sans Mot de Passe)](#magic-link-passwordless) (3)
- [Backends SMS](#sms-backends) (9)
- [Backends E-mail](#email-backends) (3)
- [Journaux d'Audit](#audit-logging) (4)
- [Organisations (B2B)](#organizations-b2b) (8)
- [Modèles Interchangeables (Swappable Models)](#swappable-models) (4)

Tous les paramètres de Tenxyte sont préfixés par `TENXYTE_` et possèdent des valeurs par défaut raisonnables.
Surchargez-les dans le fichier `settings.py` de votre projet Django. Le `DjangoSettingsProvider` de l'adaptateur Django lit automatiquement ces valeurs et les transmet au Core agnostique — aucune configuration supplémentaire n'est requise.

---

## Priorité des Paramètres

`TENXYTE_SHORTCUT_SECURE_MODE` applique une combinaison prédéfinie de paramètres de sécurité en une seule ligne. Les paramètres individuels ont toujours la priorité sur le préréglage.

**Ordre de priorité :** `TENXYTE_*` explicite dans `settings.py` > préréglage > valeur par défaut

```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # 'development' | 'medium' | 'robust'
```

| Mode | Cas d'utilisation visé |
|---|---|
| `development` | Prototypes, développement local, outils internes |
| `medium` | SaaS public, applications B2C, startups |
| `robust` | Fintech, santé, B2B, strictement conforme au RGPD |

### Valeurs des préréglages

| Paramètre | `development` | `medium` | `robust` |
|---|---|---|---|
| `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | `3600` (1h) | `900` (15min) | `300` (5min) |
| `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | `2592000` (30j) | `604800` (7j) | `86400` (1j) |
| `TENXYTE_REFRESH_TOKEN_ROTATION` | `False` | `True` | `True` |
| `TENXYTE_MAX_LOGIN_ATTEMPTS` | `10` | `5` | `3` |
| `TENXYTE_LOCKOUT_DURATION_MINUTES` | `15` | `30` | `60` |
| `TENXYTE_PASSWORD_HISTORY_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_PASSWORD_HISTORY_COUNT` | `0` | `5` | `12` |
| `TENXYTE_BREACH_CHECK_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_BREACH_CHECK_REJECT` | `False` | `True` | `True` |
| `TENXYTE_MAGIC_LINK_ENABLED` | `False` | `True` | `False` |
| `TENXYTE_WEBAUTHN_ENABLED` | `False` | `False` | `True` |
| `TENXYTE_AUDIT_LOGGING_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEVICE_LIMIT_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEFAULT_MAX_DEVICES` | — | `5` | `2` |
| `TENXYTE_DEVICE_LIMIT_ACTION` | — | — | `'deny'` |
| `TENXYTE_SESSION_LIMIT_ENABLED` | `False` | `True` | `True` |
| `TENXYTE_DEFAULT_MAX_SESSIONS` | — | — | `1` |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS` | `False` | `False` | `False` |
| `TENXYTE_SECURITY_HEADERS_ENABLED` | `False` | `True` | `True` |

> Les paramètres marqués `—` ne sont pas définis par le préréglage et reprennent leurs valeurs par défaut individuelles.

Vous pouvez surcharger n'importe quelle valeur de préréglage individuellement :
```python
TENXYTE_SHORTCUT_SECURE_MODE = 'robust'
TENXYTE_WEBAUTHN_ENABLED = False  # désactiver les passkeys malgré le mode robust
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 600  # 10min au lieu de 5min
```

---

## Paramètres Essentiels (Core Settings)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_BASE_URL` | `'http://127.0.0.1:8000'` | URL de base de l'API. |
| `TENXYTE_API_VERSION` | `1` | Numéro de version de l'API. |
| `TENXYTE_API_PREFIX` | `'/api/v1'` | Préfixe matériel global de l'API. |
| `TENXYTE_TRUSTED_PROXIES` | `[]` | Liste des IP/CIDR de serveurs mandataires de confiance pour la validation `X-Forwarded-For`. |
| `TENXYTE_NUM_PROXIES` | `0` | Nombre de proxys amont de confiance (ex: Cloudflare + Nginx = 2). |
| `TENXYTE_VERBOSE_ERRORS` | `False` | Affiche les détails complets des erreurs (ex: rôle exact manquant). Désactivez en production. |

---

## JWT

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_JWT_SECRET_KEY` | `None` (Requis) | Clé secrète dédiée à la signature des JWT. Doit être définie explicitement en production. En mode `DEBUG`, une clé éphémère est auto-générée. |
| `TENXYTE_JWT_ALGORITHM` | `'HS256'` | Algorithme de signature JWT. |
| `TENXYTE_JWT_PRIVATE_KEY` | `None` | Clé privée RSA/ECDSA pour la signature JWT (requise pour les algorithmes RS/PS/ES). |
| `TENXYTE_JWT_PUBLIC_KEY` | `None` | Clé publique RSA/ECDSA pour la vérification JWT (requise pour les algorithmes RS/PS/ES). |
| `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` | `3600` | Durée de vie du jeton d'accès en secondes (1 heure). |
| `TENXYTE_JWT_REFRESH_TOKEN_LIFETIME` | `604800` | Durée de vie du jeton de rafraîchissement en secondes (7 jours). |
| `TENXYTE_JWT_AUTH_ENABLED` | `True` | Active/désactive l'authentification JWT. |
| `TENXYTE_TOKEN_BLACKLIST_ENABLED` | `True` | Met les jetons d'accès sur liste noire lors de la déconnexion. |
| `TENXYTE_REFRESH_TOKEN_ROTATION` | `True` | Délivre un nouveau jeton de rafraîchissement à chaque rafraîchissement (invalide l'ancien). |

---

## Authentification à Deux Facteurs (TOTP)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_TOTP_ISSUER` | `'MyApp'` | Nom de l'émetteur affiché dans les applications d'authentification (Google Authenticator, Authy). |
| `TENXYTE_TOTP_VALID_WINDOW` | `1` | Nombre de périodes de 30s acceptées avant/après l'heure actuelle. |
| `TENXYTE_BACKUP_CODES_COUNT` | `10` | Nombre de codes de secours générés lors de la configuration 2FA. |

---

## OTP (Vérification E-mail / SMS)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_OTP_LENGTH` | `6` | Longueur des codes OTP. |
| `TENXYTE_OTP_EMAIL_VALIDITY` | `15` | Validité de l'OTP par e-mail en minutes. |
| `TENXYTE_OTP_PHONE_VALIDITY` | `10` | Validité de l'OTP par SMS en minutes. |
| `TENXYTE_OTP_MAX_ATTEMPTS` | `5` | Nombre maximal de tentatives OTP échouées avant invalidation. |

---

## Politique de Mot de Passe

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_PASSWORD_MIN_LENGTH` | `8` | Longueur minimale du mot de passe. |
| `TENXYTE_PASSWORD_MAX_LENGTH` | `128` | Longueur maximale du mot de passe. |
| `TENXYTE_BCRYPT_ROUNDS` | `12` | Facteur de travail pour le hachage bcrypt. |
| `TENXYTE_PASSWORD_REQUIRE_UPPERCASE` | `True` | Exige au moins une lettre majuscule. |
| `TENXYTE_PASSWORD_REQUIRE_LOWERCASE` | `True` | Exige au moins une lettre minuscule. |
| `TENXYTE_PASSWORD_REQUIRE_DIGIT` | `True` | Exige au moins un chiffre. |
| `TENXYTE_PASSWORD_REQUIRE_SPECIAL` | `True` | Exige au moins un caractère spécial. |
| `TENXYTE_PASSWORD_HISTORY_ENABLED` | `True` | Empêche la réutilisation des mots de passe récents. |
| `TENXYTE_PASSWORD_HISTORY_COUNT` | `5` | Nombre de mots de passe précédents à vérifier. |

---

## Limitation de Débit et Verrouillage de Compte

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_RATE_LIMITING_ENABLED` | `True` | Active la limitation de débit sur les points de terminaison sensibles. |
| `TENXYTE_MAX_LOGIN_ATTEMPTS` | `5` | Tentatives échouées avant le verrouillage du compte. |
| `TENXYTE_LOCKOUT_DURATION_MINUTES` | `30` | Durée du verrouillage du compte en minutes. |
| `TENXYTE_RATE_LIMIT_WINDOW_MINUTES` | `15` | Fenêtre temporelle pour le comptage des tentatives de connexion. |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED` | `True` | Active/désactive le verrouillage du compte après échecs. |

### Règles de Limitation Personnalisées

Appliquez des limites de débit à n'importe quelle URL sans créer de classe de limitation personnalisée :

```python
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/products/': '100/hour',
    '/api/v1/search/': '30/min',
    '/api/v1/upload/': '5/hour',
    '/api/v1/health/$': '1000/min',  # avec $ = correspondance exacte
}
```

Nécessite l'ajout à la configuration DRF :
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'tenxyte.throttles.SimpleThrottleRule',
    ],
}
```

---

## Limites de Sessions et d'Appareils

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_SESSION_LIMIT_ENABLED` | `True` | Active les limites de sessions simultanées. |
| `TENXYTE_DEFAULT_MAX_SESSIONS` | `1` | Nombre maximal de sessions simultanées par utilisateur. |
| `TENXYTE_DEFAULT_SESSION_LIMIT_ACTION` | `'revoke_oldest'` | Action lorsque la limite est dépassée : `'deny'` ou `'revoke_oldest'`. |
| `TENXYTE_DEVICE_LIMIT_ENABLED` | `True` | Active les limites d'appareils uniques. |
| `TENXYTE_DEFAULT_MAX_DEVICES` | `1` | Nombre maximal d'appareils uniques par utilisateur. |
| `TENXYTE_DEVICE_LIMIT_ACTION` | `'deny'` | Action lorsque la limite d'appareils est dépassée : `'deny'` ou `'revoke_oldest'`. |

Surcharges par utilisateur : définissez `user.max_sessions` ou `user.max_devices` pour outrepasser la valeur par défaut.

---

## Multi-Application

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_APPLICATION_AUTH_ENABLED` | `True` | Requiert les en-têtes `X-Access-Key` / `X-Access-Secret`. |
| `TENXYTE_EXEMPT_PATHS` | `['/admin/', '/api/v1/health/', '/api/v1/docs/']` | Chemins exemptés de l'authentification d'application (correspondance de préfixe). |
| `TENXYTE_EXACT_EXEMPT_PATHS` | `['/api/v1/']` | Chemins exemptés de l'authentification d'application (correspondance exacte). |

---

## CORS

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_CORS_ENABLED` | `True` | Active le middleware CORS intégré. |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS` | `False` | Autorise toutes les origines (dangereux en production). |
| `TENXYTE_CORS_ALLOWED_ORIGINS` | `[]` | Liste des origines autorisées. |
| `TENXYTE_CORS_ALLOW_CREDENTIALS` | `True` | Autorise les identifiants (cookies, Authorization). |
| `TENXYTE_CORS_ALLOWED_METHODS` | `['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']` | Méthodes HTTP autorisées. |
| `TENXYTE_CORS_ALLOWED_HEADERS` | Voir ci-dessous | En-têtes de requête autorisés. |
| `TENXYTE_CORS_EXPOSE_HEADERS` | `[]` | En-têtes exposés au client. |
| `TENXYTE_CORS_MAX_AGE` | `86400` | Durée du cache de pré-vérification (preflight) en secondes. |

En-têtes autorisés par défaut : `Accept`, `Accept-Language`, `Content-Type`, `Authorization`, `X-Access-Key`, `X-Access-Secret`, `X-Requested-With`.

---

## En-têtes de Sécurité

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_SECURITY_HEADERS_ENABLED` | `False` | Ajoute des en-têtes de sécurité à toutes les réponses. |
| `TENXYTE_SECURITY_HEADERS` | Voir ci-dessous | Dictionnaire nom d'en-tête → valeur. |

En-têtes par défaut :
```python
{
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
}
```

---

## Connexion Sociale (OAuth2)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_SOCIAL_PROVIDERS` | `['google', 'github', 'microsoft', 'facebook']` | Fournisseurs OAuth2 activés. |
| `TENXYTE_SOCIAL_AUTO_MERGE_ACCOUNTS` | `False` | Fusionne automatiquement la connexion sociale avec un compte e-mail existant. |
| `TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL` | `True` | Rejette la connexion sociale si l'e-mail n'est pas vérifié par le fournisseur. |
| `GOOGLE_CLIENT_ID` | `''` | Identifiant client Google OAuth. |
| `GOOGLE_CLIENT_SECRET` | `''` | Secret client Google OAuth. |
| `GITHUB_CLIENT_ID` | `''` | Identifiant client GitHub OAuth App. |
| `GITHUB_CLIENT_SECRET` | `''` | Secret client GitHub OAuth App. |
| `MICROSOFT_CLIENT_ID` | `''` | Application (client) ID de Microsoft Azure AD. |
| `MICROSOFT_CLIENT_SECRET` | `''` | Secret client Microsoft Azure AD. |
| `FACEBOOK_APP_ID` | `''` | Identifiant d'application Facebook. |
| `FACEBOOK_APP_SECRET` | `''` | Secret d'application Facebook. |

Point de terminaison : `POST /api/v1/auth/social/<provider>/` — où `<provider>` est `google`, `github`, `microsoft` ou `facebook`.

---

## WebAuthn / Passkeys (FIDO2)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_WEBAUTHN_ENABLED` | `False` | Active l'authentification sans mot de passe via Passkeys. |
| `TENXYTE_WEBAUTHN_RP_ID` | `'localhost'` | ID de la partie fiduciante — doit correspondre à votre domaine (ex : `'yourapp.com'`). |
| `TENXYTE_WEBAUTHN_RP_NAME` | `'Tenxyte'` | Nom affiché dans l'invite Passkey du navigateur. |
| `TENXYTE_WEBAUTHN_CHALLENGE_EXPIRY_SECONDS` | `300` | Validité du défi WebAuthn en secondes. |

Nécessite : `pip install py-webauthn`

---

## Vérification des Mots de Passe Compromis (HaveIBeenPwned)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_BREACH_CHECK_ENABLED` | `False` | Vérifie les mots de passe par rapport à l'API HIBP Pwned Passwords. |
| `TENXYTE_BREACH_CHECK_REJECT` | `True` | Si `True`, rejette les mots de passe compromis (HTTP 400). Si `False`, avertit uniquement dans les journaux. |

Utilise l'anonymisation k — seuls les 5 premiers caractères du hachage SHA-1 sont envoyés à l'API.

---

## Lien Magique (Magic Link / Sans Mot de Passe)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_MAGIC_LINK_ENABLED` | `False` | Active la connexion sans mot de passe via des liens magiques par e-mail. |
| `TENXYTE_MAGIC_LINK_EXPIRY_MINUTES` | `15` | Validité du lien magique en minutes. |
| `TENXYTE_MAGIC_LINK_BASE_URL` | `'https://yourapp.com'` | URL de base utilisée pour construire le lien de vérification envoyé par e-mail. |

---

## Backends SMS

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_SMS_BACKEND` | `'tenxyte.backends.sms.ConsoleBackend'` | Classe du backend SMS. |
| `TENXYTE_SMS_ENABLED` | `False` | Active l'envoi réel de SMS. |
| `TENXYTE_SMS_DEBUG` | `True` | Enregistre les SMS dans les journaux au lieu de les envoyer. |
| `TWILIO_ACCOUNT_SID` | `''` | SID du compte Twilio (si utilisation du backend Twilio). |
| `TWILIO_AUTH_TOKEN` | `''` | Jeton d'authentification Twilio. |
| `TWILIO_PHONE_NUMBER` | `''` | Numéro de téléphone expéditeur Twilio. |
| `NGH_API_KEY` | `''` | Clé API NGH Corp (si utilisation du backend NGH). |
| `NGH_API_SECRET` | `''` | Secret API NGH Corp. |
| `NGH_SENDER_ID` | `''` | Identifiant d'expéditeur NGH Corp. |

Backends SMS disponibles :
- `tenxyte.backends.sms.ConsoleBackend` — affiche dans la console (développement)
- `tenxyte.backends.sms.TwilioBackend` — envoie via Twilio
- `tenxyte.backends.sms.NGHBackend` — envoie via NGH Corp

---

## Backends E-mail

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_EMAIL_BACKEND` | `'tenxyte.backends.email.DjangoBackend'` | Classe du backend e-mail. |
| `SENDGRID_API_KEY` | `''` | Clé API SendGrid (si utilisation du backend SendGrid). |
| `SENDGRID_FROM_EMAIL` | `'noreply@example.com'` | E-mail expéditeur SendGrid. |

Backends e-mail disponibles :
- `tenxyte.backends.email.DjangoBackend` — utilise le `EMAIL_BACKEND` de Django (recommandé)
- `tenxyte.backends.email.ConsoleBackend` — affiche dans la console (développement)
- `tenxyte.backends.email.SendGridBackend` — envoie via SendGrid (hérité ; préférez `django-anymail`)

---

## Journaux d'Audit

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_AUDIT_LOGGING_ENABLED` | `True` | Active l'enregistrement des journaux d'audit. |
| `TENXYTE_AUDIT_LOG_RETENTION_DAYS` | `90` | Jours de conservation avant la purge automatique (0 = infini). |
| `TENXYTE_PURGE_IP_ON_DELETION` | `False` | Purge l'IP des journaux lorsqu'un compte est supprimé. |
| `TENXYTE_AGENT_ACTION_RETENTION_DAYS` | `7` | Jours de conservation pour les actions d'Agent en attente (HITL). |

---

## Organisations (B2B)

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_ORGANIZATIONS_ENABLED` | `False` | Active la fonctionnalité Organisations (optionnel). |
| `TENXYTE_CREATE_DEFAULT_ORGANIZATION` | `True` | Crée une organisation par défaut pour les nouveaux utilisateurs. |
| `TENXYTE_ORG_ROLE_INHERITANCE` | `True` | Les rôles se propagent dans la hiérarchie de l'organisation. |
| `TENXYTE_ORG_MAX_DEPTH` | `5` | Profondeur maximale de la hiérarchie des organisations. |
| `TENXYTE_ORG_MAX_MEMBERS` | `0` | Nombre maximal de membres par organisation (0 = illimité). |
| `TENXYTE_ORGANIZATION_MODEL` | `'tenxyte.Organization'` | Modèle Organization interchangeable. |
| `TENXYTE_ORGANIZATION_ROLE_MODEL` | `'tenxyte.OrganizationRole'` | Modèle OrganizationRole interchangeable. |
| `TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL` | `'tenxyte.OrganizationMembership'` | Modèle OrganizationMembership interchangeable. |

---

## Modèles Interchangeables (Swappable Models)

Remplacez n'importe quel modèle core par le vôtre en pointant vers une classe personnalisée qui étend la base `Abstract*` correspondante.

| Paramètre | Défaut | Description |
|---|---|---|
| `TENXYTE_USER_MODEL` | `'tenxyte.User'` | Modèle User interchangeable. Définissez également `AUTH_USER_MODEL` de Django. |
| `TENXYTE_APPLICATION_MODEL` | `'tenxyte.Application'` | Modèle Application interchangeable (authentification multi-app). |
| `TENXYTE_ROLE_MODEL` | `'tenxyte.Role'` | Modèle Role interchangeable (RBAC). |
| `TENXYTE_PERMISSION_MODEL` | `'tenxyte.Permission'` | Modèle Permission interchangeable (RBAC). |

Exemple — modèle User personnalisé :

```python
# myapp/models.py
from tenxyte.models import AbstractUser

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True)

    class Meta(AbstractUser.Meta):
        db_table = 'custom_users'

# settings.py
TENXYTE_USER_MODEL = 'myapp.CustomUser'
AUTH_USER_MODEL = 'myapp.CustomUser'  # requis par Django
```

Exemple — modèle Application personnalisé :

```python
# myapp/models.py
from tenxyte.models import AbstractApplication

class CustomApplication(AbstractApplication):
    webhook_url = models.URLField(blank=True)

    class Meta(AbstractApplication.Meta):
        db_table = 'custom_applications'

# settings.py
TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
```
