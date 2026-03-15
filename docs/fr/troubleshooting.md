# Guide de Dépannage

Problèmes courants et solutions lors de l'intégration de Tenxyte.

---

## Migration vers v0.9.3 (Réarchitecture du Core)

### `DeprecationWarning: Importing X from tenxyte.Y is deprecated`

**Symptôme :** Votre console affiche des avertissements lors du démarrage du serveur ou de l'exécution des tests.

**Cause :** Dans la v0.9.3, le projet a été restructuré selon une architecture Core et Adaptateurs. De nombreux services Django internes ont été refactorisés pour utiliser le Core agnostique au framework.

**Solution :** Mettez à jour vos imports.
Au lieu de :
```python
from tenxyte.services.auth_service import AuthService
```
Utilisez :
```python
from tenxyte.core.jwt_service import JWTService
```
*(Note : Les anciens imports continueront de fonctionner jusqu'à la v1.0.0).*

---

### Adaptateurs personnalisés non utilisés

**Symptôme :** Vous avez écrit un adaptateur personnalisé (ex: `CacheService`), mais le système continue d'utiliser le cache Django par défaut.

**Cause :** Les adaptateurs personnalisés doivent être passés explicitement aux services Core (ex: `JWTService`, `TOTPService`) qui les utilisent.

**Solution :** Suivez les étapes d'initialisation détaillées dans le [Guide des Adaptateurs Personnalisés](custom_adapters.md) pour vous assurer que vos instances d'adaptateurs personnalisés sont transmises aux services Core.

---

## Installation et Paramètres

### `tenxyte.setup()` n'a aucun effet

**Symptôme :** `INSTALLED_APPS`, `AUTH_USER_MODEL` ou `MIDDLEWARE` ne sont pas configurés automatiquement.

**Cause :** `tenxyte.setup()` lit vos paramètres existants (`INSTALLED_APPS`, `MIDDLEWARE`, etc.) puis les complète. Il doit être appelé **tout à la fin** de votre fichier `settings.py` (après que tous vos paramètres Django ont été définis), sinon il ne les verra pas.

**Solution :**
```python
# settings.py — Ajoutez ceci à la FIN du fichier (après INSTALLED_APPS, MIDDLEWARE, etc.)
import tenxyte
tenxyte.setup(globals())
```

Ne l'appelez pas à l'intérieur de blocs `if TYPE_CHECKING:` ou à l'intérieur de fonctions.

---

### `ImproperlyConfigured: TENXYTE_JWT_SECRET_KEY must be set in production`

**Cause :** Exécution avec `DEBUG=False` sans secret JWT dédié.

**Solution :**
```python
# settings.py
TENXYTE_JWT_SECRET_KEY = 'votre-secret-jwt-fort-et-dedie'  # Différent du SECRET_KEY de Django
```

Générer une clé sécurisée :
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

### Échec des migrations avec `table tenxyte_user already exists`

**Cause :** Une migration partielle précédente ou un conflit de `AUTH_USER_MODEL`.

**Solution :**
```bash
python manage.py migrate tenxyte --fake-initial
```

Si le problème persiste, vérifiez que `AUTH_USER_MODEL = 'tenxyte.User'` est défini **avant** d'exécuter la première migration.

---

## Authentification et JWT

### `401 TOKEN_EXPIRED` immédiatement après la connexion

**Symptôme :** Le jeton d'accès (access token) est accepté lors de la connexion mais rejeté à la requête suivante.

**Cause :** L'horloge du serveur est désynchronisée, ou `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME` est réglé sur une valeur trop basse.

**Solution :**
```python
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 900  # 15 minutes (en secondes)
```
Assurez-vous également que l'horloge du serveur est synchronisée (via NTP).

---

### `401 TOKEN_BLACKLISTED` après déconnexion

**Symptôme :** Le jeton est rejeté alors que l'utilisateur vient de se reconnecter.

**Cause :** L'ancien jeton a été mis sur liste noire mais le client continue de l'envoyer.

**Solution :** Assurez-vous que le client remplace les jetons stockés par la nouvelle paire `TokenPair` reçue lors de la réponse de reconnexion.

---

### `403 2FA_REQUIRED` — l'utilisateur ne peut pas se connecter

**Cause :** La 2FA est activée sur le compte mais le client n'envoie pas le `totp_code`.

**Solution :** Incluez le code TOTP dans le corps de la requête de connexion :
```json
{
  "email": "user@example.com",
  "password": "...",
  "totp_code": "123456"
}
```

Si l'utilisateur a perdu l'accès à son application d'authentification, il doit utiliser un code de secours.

---

## Limitation de Débit (Rate Limiting)

### Toutes les requêtes retournent `429` dans les tests

**Cause :** La limitation de débit est active et le lanceur de tests partage une clé de cache.

**Solution :** Désactivez le throttling pour les tests :
```python
# tests/settings.py
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}
```

Ou simulez-le (mock) par test :
```python
from unittest.mock import patch

with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
    response = client.post('/api/v1/auth/login/email/', data)
```

---

### `X-Forwarded-For` usurpé / mauvaise IP dans la limitation de débit

**Cause :** L'application est derrière un proxy mais `TENXYTE_TRUSTED_PROXIES` n'est pas configuré.

**Solution :**
```python
TENXYTE_TRUSTED_PROXIES = ['10.0.0.1']  # IP de votre proxy ou load balancer
```

Seules les IP de cette liste auront leur en-tête `X-Forwarded-For` considéré comme fiable.

---

## Multi-Tenant / Organisations

### `404 ORG_NOT_FOUND`

**Cause :** La valeur de l'en-tête `X-Org-Slug` ne correspond à aucune organisation existante.

**Solution :** Vérifiez la valeur du slug. Les slugs sont en minuscules et sécurisés pour les URL :
```bash
curl -H "X-Org-Slug: acme-corp" http://localhost:8000/api/v1/auth/organizations/members/
```

---

### `403 ORG_MEMBERSHIP_REQUIRED`

**Cause :** L'utilisateur authentifié n'est pas membre de l'organisation spécifiée dans `X-Org-Slug`.

**Solution :** Ajoutez d'abord l'utilisateur à l'organisation via l'interface d'administration ou le point de terminaison d'invitation :
```bash
POST /api/v1/auth/organizations/invite/
{
  "email": "user@example.com",
  "role": "member"
}
```

---

## TOTP / 2FA

### Code QR généré mais les codes TOTP sont toujours rejetés

**Cause 1 :** La dérive de l'horloge du serveur dépasse `TENXYTE_TOTP_VALID_WINDOW`.

**Solution :** Augmentez la fenêtre de tolérance (accepte ±N périodes de 30 secondes) :
```python
TENXYTE_TOTP_VALID_WINDOW = 2  # la valeur par défaut est 1
```

**Cause 2 :** Le secret TOTP est chiffré mais `FIELD_ENCRYPTION_KEY` a changé depuis la configuration.

**Solution :** Assurez-vous que `FIELD_ENCRYPTION_KEY` n'a pas changé. Si c'est le cas, suivez la [procédure de rotation des clés](periodic_tasks.md#7-encryption-key-rotation-field_encryption_key).

---

### Codes de secours non acceptés

**Cause :** Chaque code de secours est à **usage unique**. Une fois utilisé, il ne peut plus être réutilisé.

**Solution :** Régénérez les codes de secours :
```bash
POST /api/v1/auth/2fa/backup-codes/
```

---

## Authentification Sociale

### Google OAuth : `invalid_grant` ou boucle de redirection

**Cause :** `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` sont incorrects, ou l'URI de redirection enregistré dans la console Google ne correspond pas.

**Solution :**
1. Vérifiez les identifiants dans Google Cloud Console → API et Services → Identifiants
2. Assurez-vous que l'URI de redirection correspond exactement (y compris le slash final) :
   ```
   http://localhost:8000/api/v1/auth/social/google/callback/
   ```

---

## WebAuthn / Passkeys

### `InvalidStateError` pendant l'enregistrement

**Cause :** Le défi (challenge) WebAuthn a expiré (par défaut : 300 secondes) ou a déjà été consommé.

**Solution :** Relancez le flux d'enregistrement :
```bash
POST /api/v1/auth/webauthn/register/begin/
```

---

## Base de données

### `OperationalError: no such table` pour les modèles Tenxyte

**Cause :** Les migrations n'ont pas été exécutées après l'installation de Tenxyte.

**Solution :**
```bash
python manage.py migrate
```

Si la table n'apparaît toujours pas :
```bash
python manage.py showmigrations tenxyte
python manage.py migrate tenxyte
```

---

## Pour aller plus loin

1. Consultez la [Référence des Paramètres](settings.md) — le paramètre dont vous avez besoin existe peut-être déjà
2. Consultez le [Guide de Sécurité](security.md) pour les questions liées à la sécurité
3. Consultez [TESTING.md](TESTING.md) pour les problèmes de configuration des tests
4. Recherchez dans les tickets ouverts ou demandez sur le forum de la communauté
