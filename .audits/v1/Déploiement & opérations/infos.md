# Tenxyte — Déploiement & Opérations Audit Brief

> **Objectif** : fournir toutes les informations nécessaires pour conduire un
> audit en profondeur du déploiement et des opérations de Tenxyte : gestion des
> secrets d'infrastructure, exposition dans les artefacts de déploiement, et
> procédures de réponse à incident.
> **Date** : 2026-02-27 | **Version** : `0.9.1.7`

---

## PARTIE A — Gestion des secrets d'infrastructure

---

### A1. Inventaire complet des secrets requis

| Secret | Variable d'environnement / setting | Criticité | Rotation recommandée |
|--------|-----------------------------------|-----------|---------------------|
| Clé JWT | `TENXYTE_JWT_SECRET_KEY` (fallback `SECRET_KEY`) | 🔴 Critique | Trimestrielle + immédiate si compromise |
| Clé Django (`SECRET_KEY`) | `SECRET_KEY` | 🔴 Critique | Trimestrielle |
| Secret TOTP (par utilisateur) | En DB `users.totp_secret` (en clair) | 🔴 Critique | Sur compromission DB |
| Secrets applicatifs (`X-Access-Secret`) | En DB `applications` (hashé bcrypt) | 🔴 Critique | Sur compromission + via `/applications/<id>/regenerate/` |
| Refresh tokens actifs | En DB `refresh_tokens` (en clair) | 🔴 Critique | Sur compromission DB |
| `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `GITHUB_CLIENT_ID` + `GITHUB_CLIENT_SECRET` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `MICROSOFT_CLIENT_ID` + `MICROSOFT_CLIENT_SECRET` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `FACEBOOK_APP_ID` + `FACEBOOK_APP_SECRET` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `SENDGRID_API_KEY` | settings Django | 🟡 Haute | Annuelle + si exposé |
| `NGH_API_KEY` + `NGH_API_SECRET` | settings Django | 🟡 Haute | Si NGH backend activé |

### A2. Comment Tenxyte charge ses secrets

**Fichier :** `src/tenxyte/conf.py` (887 lignes)

```python
# Ordre de résolution dans conf.py :
# 1. settings.py du projet (TENXYTE_<NOM> explicite)
# 2. Preset TENXYTE_SHORTCUT_SECURE_MODE (starter/medium/robust)
# 3. Valeur par défaut de conf.py

# Exemple : JWT_SECRET_KEY
JWT_SECRET_KEY = getattr(settings, 'TENXYTE_JWT_SECRET_KEY',
                    getattr(settings, 'SECRET_KEY', 'UNSAFE_DEFAULT'))
```

**Points critiques :**

- `TENXYTE_JWT_SECRET_KEY` est **optionnel** — si non défini, Tenxyte utilise
  `SECRET_KEY` Django. Ces deux clés partagées signifient qu'une compromission
  de `SECRET_KEY` compromet simultanément les cookies de session Django ET tous
  les tokens JWT. **Elles devraient être des valeurs distinctes.**

- Si ni `TENXYTE_JWT_SECRET_KEY` ni `SECRET_KEY` ne sont définis correctement,
  Tenxyte utilise la chaîne littérale `'UNSAFE_DEFAULT'` — un token JWT forgé
  avec cette clé serait accepté.

- Les secrets **OAuth** (`GOOGLE_CLIENT_SECRET`, etc.) sont intentionnellement
  **exclus des presets** (`SECURE_MODE_PRESETS`) et doivent être fournis
  manuellement — bonne conception, mais aucun mécanisme ne les force.

### A3. Surface d'exposition des secrets dans les artefacts de déploiement

#### A3.1 — Fichiers de configuration

| Artefact | Statut | Risque |
|----------|--------|--------|
| `.env` / `.env.production` | ❌ **Absent du repo** (vérifié) | N/A si jamais commité |
| `tests/settings.py` | ✅ Présent mais contient uniquement `'test-secret-key-for-testing-only'` | Faible (clé de test explicite) |
| `pyproject.toml` | ✅ Présent — aucune valeur sensible | Sûr |
| `.gitignore` | À vérifier — est-ce que `.env` et `*.secret` sont inclus ? | Critique |

> **Vecteurs à scanner avec truffleHog / git-secrets :**
> ```bash
> trufflehog git file://./tenxyte --since-commit HEAD --only-verified
> git-secrets --scan-history
> gitleaks detect --source . --verbose
> ```

#### A3.2 — Images Docker

**Aucun Dockerfile** n'a été identifié dans le repository Tenxyte.
Tenxyte est un **package PyPI** — pas une application Docker.

Cependant, l'**intégrateur** qui déploie Tenxyte dans son projet Django doit
vérifier les risques suivants dans ses propres images Docker :

| Risque Docker | Description | Vérification |
|--------------|-------------|-------------|
| `ARG SECRET_KEY=...` dans Dockerfile | Les `ARG` sont conservés dans l'historique des layers | `docker history <image> --no-trunc` |
| `.env` copié dans l'image | `COPY . .` sans `.dockerignore` adéquat | `docker run --rm <image> cat .env` |
| `ENV` avec valeurs en dur | Variables d'environnement visibles dans la config de l'image | `docker inspect <image>` |
| `settings.py` avec secrets hardcodés | Commité dans le repo puis copié dans l'image | `git log -p -- settings.py` |

#### A3.3 — Logs de déploiement

Tenxyte utilise le logging Django standard. Les risques identifiés :

```python
# services/*.py — pattern standard dans le codebase
except SomeException as e:
    logger.error(f"Error: {e}")  # ⚠️ str(e) peut contenir des infos sensibles
```

| Source de leak potentiel dans les logs | Risque |
|---------------------------------------|--------|
| `logger.error(str(e))` dans les services | Messages d'exception pouvant contenir des paths, noms de tables, données partielles |
| Django `DEBUG = True` en prod | Affiche le traceback complet + variables locales dans les réponses HTTP |
| `OrganizationContextMiddleware` : `'message': str(e)` dans la réponse 500 | Expose le message d'exception dans la réponse API |
| `AuditLog.details` (JSONField) | Si des PII sont logguées par erreur dans ce champ JSON libre |
| `X-Prompt-Trace-ID` header → `audit_logs.prompt_trace_id` | Identifiants de traces LLM dans les logs |

**Recommandations :**
```python
# Au lieu de : logger.error(f"Error: {e}")
logger.error("Error processing request", exc_info=True, extra={'context': 'service_name'})
# Ne jamais retourner str(e) directement dans les réponses API
```

#### A3.4 — Historique Git

Points à vérifier sur l'historique Git du **projet qui intègre Tenxyte** :

```bash
# Scanner tout l'historique Git pour des secrets
trufflehog git file://. --since-commit $(git rev-list --max-parents=0 HEAD)

# Patterns spécifiques à Tenxyte
git log --all -p | grep -E 'SECRET_KEY|JWT_SECRET|CLIENT_SECRET|API_KEY|AUTH_TOKEN'

# Vérifier les fichiers supprimés (un .env supprimé reste dans l'historique)
git log --diff-filter=D --name-only --pretty=format: | grep -E '\.env|\.secret|secrets'
```

---

## PARTIE B — Procédures opérationnelles existantes

---

### B1. Commandes de maintenance intégrées

**Fichier :** `src/tenxyte/management/commands/tenxyte_cleanup.py`

Tenxyte fournit une **commande de maintenance Django** native :

```bash
python manage.py tenxyte_cleanup [options]

Options:
  --login-attempts-days N   Supprimer les LoginAttempt > N jours (défaut: 90)
  --audit-log-days N        Supprimer les AuditLog > N jours (défaut: 365, 0=garder tout)
  --dry-run                 Simule sans supprimer (preview)
```

**Ce que la commande nettoie :**

| Table | Critère de suppression |
|-------|----------------------|
| `blacklisted_tokens` | `expires_at < now` (token expiré) |
| `otp_codes` | `expires_at < now` (OTP expiré) |
| `refresh_tokens` | `is_revoked=True` OU `expires_at < now` |
| `login_attempts` | `created_at < now - N jours` (défaut 90j) |
| `audit_logs` | `created_at < now - N jours` (défaut 365j) |

**Ce que la commande ne nettoie PAS :**
- `agent_pending_actions` (expirées)
- `webauthn_challenges` (expirées)
- `magic_link_tokens` (utilisés/expirés)
- `account_deletion_requests` (complétées)
- `social_accounts` (orphelins)

### B2. Tâches périodiques (Tasks)

**Fichier :** `src/tenxyte/tasks/agent_tasks.py`

Seule une tâche Celery est fournie nativement :

```python
@shared_task
def check_agent_heartbeats():
    """
    Toutes les minutes — suspend les AgentTokens dont le heartbeat est absent.
    Intégration Celery optionnelle (fallback: fonction appelable directement).
    """
```

> **⚠️ Lacune opérationnelle** : Celery est **optionnel** (import avec fallback).
> Si l'intégrateur n'intègre pas Celery Beat, les heartbeat AIRS ne sont jamais
> vérifiés automatiquement, rendant le Dead Man's Switch inopérant.

### B3. Opérations manuelles disponibles via API

Ces opérations sont disponibles immédiatement pour une réponse à incident :

| Action | Endpoint | Auth requise | Effet |
|--------|---------|-------------|-------|
| Révoquer refresh token spécifique | `DELETE /admin/refresh-tokens/<id>/revoke/` | JWT + is_staff | Invalide une session |
| Purger les tokens blacklistés expirés | `POST /admin/blacklisted-tokens/cleanup/` | JWT + is_staff | Maintenance DB |
| Bannir un utilisateur | `POST /admin/users/<id>/ban/` | JWT + is_staff | Bloque toute auth |
| Verrouiller un utilisateur | `POST /admin/users/<id>/lock/` | JWT + is_staff | Verrouillage temporaire |
| Régénérer le secret d'une application | `POST /applications/<id>/regenerate/` | JWT + is_staff | Invalide acc_secret courant |
| Révoquer tous les tokens d'un agent | `POST /ai/tokens/revoke-all/` | JWT + is_staff | Désactive tous les agents |
| Déconnexion globale (par utilisateur) | `POST /logout/all/` | JWT (utilisateur) | Révoque tous ses refresh tokens |

---

## PARTIE C — Procédures de réponse à incident

> **Statut actuel** : Tenxyte **ne fournit pas** de runbook de réponse à incident.
> Cette section documente ce qui existe techniquement et ce qui manque.

---

### C1. Scénario : Clé JWT compromise (`TENXYTE_JWT_SECRET_KEY`)

**Impact :** Un attaquant peut forger des tokens JWT valides pour **n'importe quel
utilisateur**, y compris les administrateurs. Tous les tokens actuellement émis
sont potentiellement forgés.

**Procédure de rotation urgente :**

```
1. IMMÉDIAT — Changer la valeur de TENXYTE_JWT_SECRET_KEY
   → Tous les tokens existants deviennent instantanément invalides
   → Tous les utilisateurs sont déconnectés

2. DANS LES 5 MINUTES — Redéployer l'application avec la nouvelle clé
   → S'assurer qu'aucun worker ancien ne tourne encore avec l'ancienne clé

3. DANS L'HEURE — Invalider tous les refresh tokens en DB
   → UPDATE refresh_tokens SET is_revoked = TRUE WHERE is_revoked = FALSE;
   → Ou via API: /admin/refresh-tokens/ (revoke manuellement ou endpoint bulk non implémenté)

4. DANS LES 24H — Notifier les utilisateurs
   → "Votre session a été invalidée pour des raisons de sécurité"
   → Demander re-login

5. DANS LES 48H — Analyser les logs d'audit
   → Chercher des connexions suspectes avec action='login' à des heures inhabituelles
   → Identifier les comptes potentiellement compromis
```

**Lacune identifiée :** Il n'existe pas d'endpoint API pour **révoquer en masse**
tous les refresh tokens. En cas d'urgence :

```python
# Commande Django directe en base
python manage.py shell -c "
from tenxyte.models import RefreshToken
count = RefreshToken.objects.filter(is_revoked=False).update(is_revoked=True)
print(f'Revoked {count} refresh tokens')
"
```

### C2. Scénario : Base de données compromise

**Impact :** Accès à tous les refresh tokens (en clair), TOTP secrets (en clair),
données personnelles, historique des sessions.

**Procédure :**

```
1. IMMÉDIAT — Couper l'accès réseau à la DB (firewall/security group)
2. IMMÉDIAT — Changer les credentials DB
3. DANS LES 5 MINUTES — Changer TENXYTE_JWT_SECRET_KEY + SECRET_KEY Django
   → Invalide tous les tokens JWT
4. DANS L'HEURE — Tous les utilisateurs doivent re-créer leur TOTP (clés exposées)
   → Désactiver le 2FA TOTP pour tous : UPDATE users SET is_2fa_enabled = FALSE;
   → Régénérer les secrets TOTP à la prochaine connexion de chaque utilisateur
5. DANS L'HEURE — Informer les utilisateurs que leurs secrets 2FA sont compromis
6. DANS LES 48H — Faire appel à un expert forensique
7. SELON RGPD — Notifier l'autorité de contrôle dans les 72h (Art. 33)
```

### C3. Scénario : Credentials d'une application client exposés (X-Access-Secret)

**Impact :** L'application cliente peut être usurpée — tous ses endpoints sont
accessibles par l'attaquant.

**Procédure :**

```
1. Via API — Régénérer immédiatement les credentials de l'application
   POST /applications/<app_id>/regenerate/

2. L'ancien access_secret est immédiatement invalide
3. Le nouveau secret est transmis de manière sécurisée à l'équipe cliente
4. Vérifier dans AuditLog les actions effectuées depuis l'application
   → Chercher user_agent et IP inhabituels dans la période de compromission
```

### C4. Scénario : Agent IA compromis ou malveillant

**Impact :** Un agent IA avec des permissions étendues peut effectuer des actions
non autorisées sur le système.

**Procédure (actions disponibles dans Tenxyte) :**

```
1. IMMÉDIAT — Révoquer le token agent spécifique
   POST /ai/tokens/<pk>/revoke/

2. OU révoquer TOUS les agents de l'utilisateur
   POST /ai/tokens/revoke-all/

3. Vérifier AuditLog avec action='agent_action' pour l'agent_id concerné
   → Identifier toutes les actions effectuées
   → Vérifier les AgentPendingAction (actions en attente de confirmation)

4. Si HITL non confirmées → les deny manuellement
   POST /ai/pending-actions/<token>/deny/

5. Analyser prompt_trace_id dans AuditLog pour retrouver la chaîne LLM
```

### C5. Scénario : Fuite de tokens de réinitialisation de mot de passe

**Impact :** Un attaquant peut réinitialiser le mot de passe d'un utilisateur
via un token OTP volé (6 chiffres, valide ~15 min).

**Procédure :**

```
1. Le code OTP est invalide après 15 minutes — risque limité dans le temps
2. Si compromission confirmée : invalider manuellement
   → UPDATE otp_codes SET is_used = TRUE WHERE user_id = <id> AND is_used = FALSE;
3. Vérifier si le reset a été utilisé (AuditLog action='password_reset_complete')
4. Si utilisé → l'utilisateur doit être contacté et son compte sécurisé
```

---

## PARTIE D — Ce qui manque dans Tenxyte pour les opérations

### D1. Fonctionnalités manquantes critiques pour la production

| Fonctionnalité manquante | Impact opérationnel | Workaround actuel |
|--------------------------|--------------------|--------------------|
| **Révocation mass refresh tokens** (endpoint API) | Impossible de déconnecter tous les users via API en situation d'urgence | `python manage.py shell` ou SQL direct |
| **Runbook de réponse à incident** | L'équipe ops ne sait pas quoi faire en cas de compromission | Ce document |
| **Alerting temps réel** (webhook, SIEM) | Les incidents ne sont pas détectés en temps réel | Polling manuel des AuditLogs |
| **Rotation automatique des clés** | Les clés JWT vieillissent sans rotation | Rotation manuelle |
| **Désactivation mass 2FA** en cas de compromission TOTP | Impossible via API | SQL direct |
| **Health check endpoint** documenté | Monitoring de disponibilité | `/health/` (non documenté dans le package) |
| **Tâche de cleanup** des AgentPendingAction expirées | Accumulation en DB | `python manage.py shell` ou SQL direct |

### D2. Recommandations pour rendre Tenxyte production-ready

#### Secrets management

```python
# Pattern recommandé : charger les secrets depuis un vault externe
# Au lieu de settings.py en clair

# Option 1 : Variables d'environnement (minimum)
TENXYTE_JWT_SECRET_KEY = os.environ['TENXYTE_JWT_SECRET_KEY']

# Option 2 : AWS Secrets Manager
import boto3
client = boto3.client('secretsmanager')
TENXYTE_JWT_SECRET_KEY = client.get_secret_value(SecretId='tenxyte/jwt')['SecretString']

# Option 3 : HashiCorp Vault
import hvac
vault_client = hvac.Client()
TENXYTE_JWT_SECRET_KEY = vault_client.secrets.kv.read_secret_version(path='tenxyte/jwt')['data']['value']
```

#### Monitoring des incidents

```python
# Intégrer un webhook sur les AuditLog créés avec des actions critiques
# (non implémenté nativement — à faire côté intégrateur via signals Django)

from django.db.models.signals import post_save
from django.dispatch import receiver
from tenxyte.models import AuditLog

CRITICAL_ACTIONS = {'suspicious_activity', 'user_banned', 'deletion_request'}

@receiver(post_save, sender=AuditLog)
def alert_on_critical_action(sender, instance, created, **kwargs):
    if created and instance.action in CRITICAL_ACTIONS:
        # Envoyer vers PagerDuty, Slack, SIEM...
        send_alert(instance)
```

#### Rotation de clé JWT sans interruption (zero-downtime)

```
Problème : changer TENXYTE_JWT_SECRET_KEY invalide tous les tokens actuels.
Solution (non implémentée dans Tenxyte) :

1. Ajouter TENXYTE_JWT_OLD_SECRET_KEY = <ancienne clé>
2. decode_token() essaie d'abord la nouvelle clé, puis l'ancienne
3. Après expiration des anciens tokens (JWT_ACCESS_TOKEN_LIFETIME), supprimer l'ancienne clé
4. Désactiver TENXYTE_JWT_OLD_SECRET_KEY

→ À implémenter dans JWTService.decode_token() ou via un token versioning (claims 'v')
```

---

## PARTIE E — Checklist de l'auditeur

### Secrets d'infrastructure

- [ ] `TENXYTE_JWT_SECRET_KEY` est-il distinct de `SECRET_KEY` Django ?
- [ ] Les secrets sont-ils chargés depuis des variables d'environnement (pas hardcodés) ?
- [ ] Les secrets sont-ils gérés via un vault (AWS SM, HashiCorp, GCP SM) ?
- [ ] `.env` est-il dans `.gitignore` ET absent de l'historique Git (`git log --all -- .env`) ?
- [ ] L'historique Git ne contient-il aucun secret (`trufflehog`, `gitleaks`) ?
- [ ] Les images Docker ne contiennent-elles pas de secrets dans les layers ou ENV ?
- [ ] Les logs de déploiement (CI/CD) ne contiennent-ils pas de valeurs de secrets ?
- [ ] La clé JWT et les secrets OAuth ont-ils une politique de rotation définie ?

### Procédures opérationnelles

- [ ] Existe-t-il un runbook documenté pour la rotation d'urgence des clés JWT ?
- [ ] L'équipe sait-elle comment révoquer en masse tous les refresh tokens en cas d'incident ?
- [ ] L'équipe sait-elle comment désactiver rapidement le 2FA TOTP si les secrets sont exposés ?
- [ ] Les procédures RGPD Art. 33 (notification sous 72h) sont-elles documentées ?
- [ ] Une notification utilisateur est-elle prévue en cas de compromission ?
- [ ] `python manage.py tenxyte_cleanup` est-il planifié (cron/Celery Beat) ?
- [ ] `check_agent_heartbeats` Celery task est-il déclenché périodiquement ?

### Monitoring et alerting

- [ ] Des alertes temps réel existent-elles sur les actions `suspicious_activity` dans AuditLog ?
- [ ] Les AuditLogs sont-ils exportés vers un SIEM (Splunk, Datadog, CloudWatch Logs) ?
- [ ] La commande `tenxyte_cleanup` est-elle planifiée avec des paramètres de rétention adéquats ?
- [ ] L'API health check est-elle monitorée (Pingdom, UptimeRobot, etc.) ?
- [ ] Des alertes de dépassement de budget/circuit breaker AIRS sont-elles configurées ?

### Configuration production

- [ ] `DEBUG = False` en production Django ?
- [ ] `ALLOWED_HOSTS` est-il restreint aux domaines légitimes ?
- [ ] `TENXYTE_SHORTCUT_SECURE_MODE = 'robust'` ou configuration manuelle équivalente ?
- [ ] `TENXYTE_CORS_ALLOW_ALL_ORIGINS = False` ?
- [ ] `TENXYTE_AUDIT_LOGGING_ENABLED = True` ?
- [ ] `TENXYTE_BREACH_CHECK_ENABLED = True` et `TENXYTE_BREACH_CHECK_REJECT = True` ?
