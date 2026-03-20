# Guide de Sécurité

Tenxyte fournit plusieurs couches de sécurité prêtes à l'emploi.

## Table des Matières
- [Limitation de Débit (Rate Limiting)](#limitation-de-debit-rate-limiting)
- [Verrouillage de Compte](#verrouillage-de-compte)
- [Authentification à Deux Facteurs (2FA / TOTP)](#authentification-a-deux-facteurs-2fa--totp)
- [Sécurité des Jetons JWT](#securite-des-jetons-jwt)
- [Limites de Sessions et d'Appareils](#limites-de-sessions-et-dappareils)
- [Sécurité des Mots de Passe](#securite-des-mots-de-passe)
- [En-têtes de Sécurité](#en-tetes-de-securite)
- [CORS](#cors)
- [Journaux d'Audit (Audit Logging)](#journaux-daudit-audit-logging)
- [Vérification OTP](#verification-otp)
- [Checklist pour la Production](#checklist-pour-la-production)

---

## Limitation de Débit (Rate Limiting)

### Classes de Limitation Intégrées

Tenxyte est livré avec des classes de limitation préconfigurées pour les points de terminaison sensibles :

| Classe | Débit par Défaut | Appliqué à |
|---|---|---|
| `LoginThrottle` | 5/min | Points de terminaison de connexion |
| `LoginHourlyThrottle` | 20/heure | Points de terminaison de connexion |
| `RegisterThrottle` | 3/heure | Point de terminaison d'inscription |
| `RegisterDailyThrottle` | 10/jour | Point de terminaison d'inscription |
| `RefreshTokenThrottle` | 30/min | Rafraîchissement de jeton |
| `GoogleAuthThrottle` | 10/min | OAuth Google |
| `OTPRequestThrottle` | 5/heure | Demande d'OTP |
| `OTPVerifyThrottle` | 5/min | Vérification d'OTP |
| `PasswordResetThrottle` | 3/heure | Demande de réinitialisation de mot de passe |
| `PasswordResetDailyThrottle` | 10/jour | Demande de réinitialisation de mot de passe |
| `MagicLinkRequestThrottle` | 3/heure | Demande de lien magique |
| `MagicLinkVerifyThrottle` | 10/min | Vérification de lien magique |

### Limitation Personnalisée Basée sur l'URL

Appliquez des limites de débit à n'importe quelle URL sans écrire de classe personnalisée :

```python
# settings.py
TENXYTE_SIMPLE_THROTTLE_RULES = {
    '/api/v1/products/': '100/hour',
    '/api/v1/search/': '30/min',
    '/api/v1/upload/': '5/hour',
    '/api/v1/health/$': '1000/min',  # $ = correspondance exacte
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'tenxyte.throttles.SimpleThrottleRule',
    ],
}
```

### Désactiver la Limitation dans les Tests

```python
# Dans vos helpers de test
from unittest.mock import patch

with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
    response = client.post('/api/v1/auth/login/email/', data)
```

---

## Verrouillage de Compte

Après `TENXYTE_MAX_LOGIN_ATTEMPTS` (par défaut : 5) tentatives de connexion échouées dans un intervalle de `TENXYTE_RATE_LIMIT_WINDOW_MINUTES` (par défaut : 15 min), le compte est verrouillé pendant `TENXYTE_LOCKOUT_DURATION_MINUTES` (par défaut : 30 min).

```python
# settings.py
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = True
TENXYTE_MAX_LOGIN_ATTEMPTS = 5
TENXYTE_LOCKOUT_DURATION_MINUTES = 30
TENXYTE_RATE_LIMIT_WINDOW_MINUTES = 15
```

Les comptes verrouillés renvoient un `401` avec le code : `'ACCOUNT_LOCKED'`.

Déverrouillage par l'administrateur via l'API :
```bash
POST /api/v1/auth/admin/users/<id>/unlock/
```

---

## Authentification à Deux Facteurs (2FA / TOTP)

### Flux de Configuration

1. L'utilisateur appelle `POST /2fa/setup/` → reçoit un code QR + codes de secours.
2. L'utilisateur scanne le code QR avec Google Authenticator / Authy.
3. L'utilisateur appelle `POST /2fa/confirm/` avec le premier code TOTP → la 2FA est activée.

### Connexion avec 2FA

```bash
POST /api/v1/auth/login/email/
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "totp_code": "123456"
}
```

Si le `totp_code` est manquant alors que la 2FA est activée, la réponse est :
```json
{
  "error": "2FA code required",
  "code": "2FA_REQUIRED",
  "requires_2fa": true
}
```

### Codes de Secours

Générés lors de la configuration (`TENXYTE_BACKUP_CODES_COUNT`, par défaut : 10).
Chaque code est à usage unique. Régénérez-les avec `POST /2fa/backup-codes/`.

### Configuration

```python
TENXYTE_TOTP_ISSUER = 'MonApp'        # Nom affiché dans l'application d'authentification
TENXYTE_TOTP_VALID_WINDOW = 1        # Accepter ±1 période (tolérance de 30s)
TENXYTE_BACKUP_CODES_COUNT = 10
```

---

## Sécurité des Jetons JWT

### Mise sur Liste Noire (Blacklisting) des Jetons d'Accès

Lorsque `TENXYTE_TOKEN_BLACKLIST_ENABLED = True` (par défaut), les jetons d'accès sont mis sur liste noire lors de la déconnexion. Cela empêche la réutilisation du jeton même avant son expiration.

```python
TENXYTE_TOKEN_BLACKLIST_ENABLED = True
```

### Rotation des Jetons de Rafraîchissement

Lorsque `TENXYTE_REFRESH_TOKEN_ROTATION = True` (par défaut), chaque appel à `/refresh/` délivre un **nouveau** jeton de rafraîchissement et invalide l'ancien. Cela limite les dégâts en cas de vol d'un jeton de rafraîchissement.

```python
TENXYTE_REFRESH_TOKEN_ROTATION = True
```

### Jetons d'Accès à Courte Durée de Vie

Gardez les jetons d'accès à courte durée de vie et appuyez-vous sur les jetons de rafraîchissement pour la persistance de session. Par défaut, les jetons d'accès durent 1 heure, mais il est fortement recommandé de raccourcir cette durée en production :

```python
# Valeurs par défaut
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600    # 1 heure
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 604800 # 7 jours
```

*(Note : Le préréglage `standard` configure les jetons d'accès à 15 minutes).*

---

## Limites de Sessions et d'Appareils

### Limites de Sessions

Limitez le nombre de sessions simultanées qu'un utilisateur peut avoir en rejetant ou en remplaçant des connexions. Par défaut, Tenxyte limite les utilisateurs à 1 session :

```python
TENXYTE_SESSION_LIMIT_ENABLED = True
TENXYTE_DEFAULT_MAX_SESSIONS = 1 # Remplacé par le préréglage standard à 3
TENXYTE_DEFAULT_SESSION_LIMIT_ACTION = 'revoke_oldest'  # ou 'deny'
```

Actions :
- `'revoke_oldest'` — révoque la session la plus ancienne pour faire de la place.
- `'deny'` — rejette la nouvelle tentative de connexion.

Remplacement par utilisateur : définissez `user.max_sessions = 5` pour outrepasser la valeur par défaut pour cet utilisateur.

### Limites d'Appareils

Limitez le nombre d'appareils uniques qu'un utilisateur peut utiliser en suivant les origines structurées des appareils. Par défaut, Tenxyte limite les utilisateurs à 1 appareil :

```python
TENXYTE_DEVICE_LIMIT_ENABLED = True
TENXYTE_DEFAULT_MAX_DEVICES = 1 # Remplacé par le préréglage standard à 5, haute sécurité à 2
TENXYTE_DEVICE_LIMIT_ACTION = 'deny'  # ou 'revoke_oldest'
```

L'identification de l'appareil utilise le champ `device_info` envoyé par le client (chaîne d'empreinte structurée). Tenxyte utilise une correspondance intelligente — les différences de version mineures (ex: Chrome 122 vs 123) sont traitées comme le même appareil.

**Format d'information d'appareil (v1) :**
```
v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122
```

Construction à partir du User-Agent comme solution de repli :
```python
from tenxyte.device_info import build_device_info_from_user_agent
device_info = build_device_info_from_user_agent(request.META.get('HTTP_USER_AGENT', ''))
```

---

## Sécurité des Mots de Passe

### Politique de Mot de Passe

```python
TENXYTE_PASSWORD_MIN_LENGTH = 8
TENXYTE_PASSWORD_MAX_LENGTH = 128
TENXYTE_PASSWORD_REQUIRE_UPPERCASE = True
TENXYTE_PASSWORD_REQUIRE_LOWERCASE = True
TENXYTE_PASSWORD_REQUIRE_DIGIT = True
TENXYTE_PASSWORD_REQUIRE_SPECIAL = True
```

### Historique des Mots de Passe

Empêche les utilisateurs de réutiliser leurs mots de passe récents :

```python
TENXYTE_PASSWORD_HISTORY_ENABLED = True
TENXYTE_PASSWORD_HISTORY_COUNT = 5  # Vérifier par rapport aux 5 derniers mots de passe
```

### Vérifier la Force d'un Mot de Passe

```bash
POST /api/v1/auth/password/strength/
{ "password": "MonMotDePasse123!" }
```

---

## En-têtes de Sécurité

Ajoutez des en-têtes de sécurité à toutes les réponses. Par défaut, Tenxyte fournit un ensemble d'en-têtes très restrictif, mais ils sont désactivés (`False`) par défaut à moins que vous n'utilisiez un préréglage de sécurité ou que vous ne les activiez manuellement :

```python
TENXYTE_SECURITY_HEADERS_ENABLED = False # Définir sur True pour activer
TENXYTE_SECURITY_HEADERS = {
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

Ajoutez le middleware :
```python
MIDDLEWARE = [
    ...
    'tenxyte.middleware.SecurityHeadersMiddleware',
]
```

---

## CORS

```python
TENXYTE_CORS_ENABLED = True
TENXYTE_CORS_ALLOWED_ORIGINS = [
    'https://votreapp.com',
    'http://localhost:3000',
]
TENXYTE_CORS_ALLOW_CREDENTIALS = True
```

Ajoutez le middleware :
```python
MIDDLEWARE = [
    'tenxyte.middleware.CORSMiddleware',  # Doit être en premier
    ...
]
```

---

## Journaux d'Audit (Audit Logging)

Tous les événements relatifs à la sécurité sont automatiquement enregistrés dans le modèle `AuditLog` :

| Événement | Déclencheur |
|---|---|
| `login` | Connexion réussie |
| `login_failed` | Tentative de connexion échouée |
| `logout` | Déconnexion de l'utilisateur |
| `logout_all` | Déconnexion de tous les appareils |
| `token_refresh` | Jeton d'accès rafraîchi |
| `password_change` | Mot de passe changé |
| `password_reset_request` | Demande de réinitialisation de mot de passe |
| `password_reset_complete` | Réinitialisation de mot de passe terminée |
| `2fa_enabled` | 2FA activée |
| `2fa_disabled` | 2FA désactivée |
| `2fa_backup_used` | Code de secours 2FA utilisé |
| `account_created` | Compte créé |
| `account_locked` | Compte verrouillé après des échecs |
| `account_unlocked` | Compte déverrouillé |
| `email_verified` | E-mail vérifié |
| `phone_verified` | Téléphone vérifié |
| `role_assigned` | Rôle attribué |
| `role_removed` | Rôle retiré |
| `permission_changed`| Permission changée |
| `app_created` | Application créée |
| `app_credentials_regenerated` | Identifiants d'application régénérés |
| `account_deleted` | Compte supprimé |
| `suspicious_activity` | Activité suspecte détectée |
| `session_limit_exceeded` | Limite de sessions atteinte |
| `device_limit_exceeded` | Limite d'appareils atteinte |
| `new_device_detected` | Connexion depuis un appareil non reconnu |
| `agent_action` | Action d'agent exécutée |

Consulter les journaux d'audit :
```bash
GET /api/v1/auth/admin/audit-logs/?action=login_failed&date_from=2026-01-01
```

---

## Vérification OTP

La vérification de l'e-mail et du téléphone utilise des codes OTP limités dans le temps :

```python
TENXYTE_OTP_LENGTH = 6
TENXYTE_OTP_EMAIL_VALIDITY = 15   # minutes
TENXYTE_OTP_PHONE_VALIDITY = 10   # minutes
TENXYTE_OTP_MAX_ATTEMPTS = 5      # avant invalidation
```

---

## Checklist pour la Production

- [ ] Définissez `TENXYTE_JWT_SECRET_KEY` sur un secret fort et unique (différent de `SECRET_KEY`).
- [ ] Définissez `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` sur ≤ 900 secondes (15 min).
- [ ] Activez `TENXYTE_REFRESH_TOKEN_ROTATION = True`.
- [ ] Activez `TENXYTE_TOKEN_BLACKLIST_ENABLED = True`.
- [ ] Activez `TENXYTE_SECURITY_HEADERS_ENABLED = True`.
- [ ] Configurez `TENXYTE_CORS_ALLOWED_ORIGINS` (ne jamais utiliser `ALLOW_ALL_ORIGINS` en production).
- [ ] Définissez `TENXYTE_MAX_LOGIN_ATTEMPTS` sur une valeur raisonnable (5–10).
- [ ] Activez `TENXYTE_PASSWORD_HISTORY_ENABLED = True`.
- [ ] Utilisez HTTPS en production (requis pour `Strict-Transport-Security`).
- [ ] Effectuez une rotation régulière des secrets d'`Application`.
