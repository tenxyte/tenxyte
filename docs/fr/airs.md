# Tenxyte AIRS (Responsabilité et Sécurité de l'IA)

## Sommaire

- [Présentation](#présentation)
- [1. Parité Agentique de Base — AgentToken](#1-parité-agentique-de-base--agenttoken)
- [2. Disjoncteur et Limitation de Débit](#2-disjoncteur-et-limitation-de-débit)
- [3. Intervention Humaine (Human in the Loop - HITL)](#3-intervention-humaine-human-in-the-loop---hitl)
- [4. Garde-fous : Caviardage des PII et Suivi Budgétaire](#4-garde-fous--caviardage-des-pii-et-suivi-budgétaire)
- [5. Audit Forensique](#5-audit-forensique)
- [Référence de Configuration](#référence-de-configuration)

---

## Présentation

Tenxyte AIRS est une suite complète de mesures de responsabilité, de sécurité et de protection pour les agents IA intégrés. Elle répond aux défis majeurs posés par les LLM et les modèles agentiques dans les environnements de production (ex : EchoLeak, Shadow Escape, dépenses incontrôlées).

**Principe fondamental** : Un agent IA n'agit jamais sous sa propre autorité. Il emprunte l'identité et les permissions d'un utilisateur humain via un jeton délimité et limité dans le temps (`AgentToken`), et chaque action qu'il entreprend est auditable, contrôlable et suspendable.

---

## 1. Parité Agentique de Base — AgentToken

Un `AgentToken` est le jeton d'identité délivré à un agent IA. Il permet une **délégation sécurisée** : l'agent agit au nom d'un utilisateur humain, avec un sous-ensemble strict de ses permissions, sans jamais manipuler les identifiants de l'utilisateur.

### Création (API)

```http
POST /ai/tokens/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "agent_id": "finance-agent-v2",
  "expires_in": 3600,
  "permissions": ["read:reports", "write:invoices"],
  "organization": "acme-corp",
  "budget_limit_usd": 5.00,
  "circuit_breaker": {
    "max_requests_per_minute": 30,
    "max_requests_total": 500
  },
  "dead_mans_switch": {
    "heartbeat_required_every": 300
  }
}
```

**Réponse (201) :**
```json
{
  "id": 42,
  "token": "eKj3...raw_token...Xz9",
  "agent_id": "finance-agent-v2",
  "status": "ACTIVE",
  "expires_at": "2024-01-20T16:00:00Z"
}
```

> ⚠️ La valeur brute du `token` n'est renvoyée **qu'une seule fois** lors de la création. Stockez-la de manière sécurisée — seul son hachage SHA-256 est conservé dans la base de données.

L'agent utilise ensuite `AgentBearer <token>` dans l'en-tête `Authorization` pour toutes les requêtes suivantes.

### Double Validation RBAC

Chaque requête effectuée avec un `AgentToken` passe par deux vérifications de permissions :

1. **Vérification du périmètre de l'agent** : L' `AgentToken` inclut-il la permission requise dans ses `granted_permissions` ?
2. **Vérification humaine** : L'utilisateur délégant détient-il *toujours* cette permission dans la base de données (ou au sein de l'organisation) ?

Si l'une des vérifications échoue, la requête est rejetée avec une erreur `403 Forbidden`.

### Cycle de vie du jeton

| Statut | Description |
|---|---|
| `ACTIVE` | Le jeton est valide et peut être utilisé |
| `SUSPENDED` | Désactivé automatiquement (disjoncteur, budget, battement de cœur) |
| `REVOKED` | Révoqué manuellement — permanent, irréversible |
| `EXPIRED` | Durée de vie dépassée (`expires_at`) |

---

## 2. Disjoncteur et Limitation de Débit (Circuit Breaker)

Le disjoncteur est un pare-feu autonome qui protège contre les comportements incontrôlés des agents : boucles infinies, pics d'exfiltration de données ou cascades d'échecs inattendues.

### Seuils configurables (par jeton)

| Champ | Par défaut | Description |
|---|---|---|
| `max_requests_per_minute` | 60 | Limite de requêtes par minute (RPM) via le cache |
| `max_requests_total` | 1000 | Plafond absolu de requêtes pour la durée de vie du jeton |
| `max_failed_requests` | 10 | Nombre max d'erreurs consécutives avant suspension |

Si un seuil est dépassé, le jeton passe automatiquement au statut `SUSPENDED` avec la raison appropriée :

| Raison | Déclencheur |
|---|---|
| `RATE_LIMIT` | RPM ou total de requêtes dépassé |
| `ANOMALY` | Nombre max d'échecs consécutifs dépassé |
| `HEARTBEAT_MISSING` | Expiration de la sécurité "Dead Man's Switch" |
| `BUDGET_EXCEEDED` | Le coût LLM a dépassé la limite budgétaire |
| `MANUAL` | Suspendu manuellement par l'utilisateur délégant |

### Dead Man's Switch (Sécurité d'absence)

Si `heartbeat_required_every` (en secondes) est défini, l'agent doit appeler périodiquement :

```http
POST /ai/tokens/{id}/heartbeat/
Authorization: AgentBearer <raw_token>
```

Si aucun battement de cœur n'est reçu dans l'intervalle configuré, le jeton est automatiquement suspendu avec `HEARTBEAT_MISSING`. Cela garantit que si le conteneur d'orchestration plante ou est corrompu, l'agent perd automatiquement son accès.

### Interrupteur d'urgence (Kill Switch)

Pour révoquer immédiatement **tous** les jetons actifs d'un utilisateur (option radicale) :

```http
POST /ai/tokens/revoke-all/
Authorization: Bearer <user_jwt>
```

---

## 3. Intervention Humaine (Human in the Loop - HITL)

Certaines actions sont trop sensibles pour qu'un agent IA les exécute de manière autonome. Le HITL garantit qu'un humain doit explicitement les approuver avant leur exécution.

### Fonctionnement

Les points de terminaison décorés avec `@require_agent_clearance(human_in_the_loop_required=True)` se comportent différemment lorsqu'ils sont appelés par un agent :

1. L'agent appelle le point de terminaison normalement.
2. Au lieu de s'exécuter, Tenxyte crée une action en attente (`AgentPendingAction`) et renvoie **`202 Accepted`** (pas `200`).
3. L'humain est notifié (email, webhook, etc.) avec un `confirmation_token`.
4. L'humain confirme ou refuse via l'API.
5. L'agent peut interroger (poll) ou être notifié pour réessayer.

### Actions HITL globales

Configurez les actions qui nécessitent **toujours** une approbation humaine dans le fichier `settings.py` :

```python
TENXYTE_AIRS_CONFIRMATION_REQUIRED = [
    "users.delete",
    "billing.refund",
    "data.export_all",
]
```

### Points de terminaison de confirmation/refus

```http
# L'humain approuve
POST /ai/pending-actions/<confirmation_token>/confirm/
Authorization: Bearer <user_jwt>

# L'humain refuse
POST /ai/pending-actions/<confirmation_token>/deny/
Authorization: Bearer <user_jwt>
```

Les actions en attente de l'agent peuvent également être listées :

```http
GET /ai/pending-actions/
Authorization: Bearer <user_jwt>
```

---

## 4. Garde-fous : Caviardage des PII et Suivi Budgétaire

### Caviardage des PII (Informations Personnelles Identifiables)

Lorsque `TENXYTE_AIRS_REDACT_PII = True`, un middleware intercepte toutes les réponses JSON envoyées à un demandeur `AgentBearer` et anonymise automatiquement les champs sensibles (emails, numéros de téléphone, IBAN, etc.) en les remplaçant par `***REDACTED***`.

Cela empêche les LLM d'ingérer ou de mémoriser des informations personnelles identifiables provenant de votre backend.

---

### Suivi Budgétaire

Le suivi budgétaire vous permet de plafonner l'impact financier qu'un agent peut avoir via des appels d'API LLM (OpenAI, Anthropic, Google, etc.).

> **Important** : Tenxyte ne connaît **pas** les tarifs des LLM. Il est agnostique vis-à-vis du modèle. Votre code est responsable de la conversion du nombre de jetons en un coût USD et de son signalement. Tenxyte ne fait qu'accumuler le `cost_usd` signalé et suspend l'agent lorsque la limite est atteinte.

#### Activer dans les paramètres

```python
TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
```

#### Créer un jeton avec un plafond budgétaire

```python
from tenxyte.services.agent_service import AgentTokenService

service = AgentTokenService()
token = service.create(
    triggered_by=user,
    application=app,
    granted_permissions=[],
    budget_limit_usd=1.00,  # 1.00 $ maximum
)
```

#### Calculer le coût dans votre wrapper LLM

Vous êtes responsable du maintien d'une table de tarification et du calcul des coûts :

```python
# Exemple de table de tarification (à mettre à jour selon les tarifs des fournisseurs)
MODEL_PRICING = {
    "claude-sonnet-4-5":    {"input": 3.00,  "output": 15.00},  # par million de jetons
    "gemini-1.5-pro":       {"input": 3.50,  "output": 10.50},
    "gpt-4o":               {"input": 5.00,  "output": 15.00},
}

def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (
        (prompt_tokens    / 1_000_000) * pricing["input"] +
        (completion_tokens / 1_000_000) * pricing["output"]
    )
```

#### Signaler l'utilisation après chaque appel LLM

**Via le service Python :**
```python
# Après avoir appelé votre LLM (Anthropic, Google, OpenAI, etc.)
prompt_tokens     = response.usage.input_tokens    # depuis la réponse du fournisseur
completion_tokens = response.usage.output_tokens

cost = calculate_cost_usd("claude-sonnet-4-5", prompt_tokens, completion_tokens)

success = service.report_usage(token, cost_usd=cost)

if not success:
    # Budget dépassé → le jeton est désormais SUSPENDED
    # L'agent recevra des erreurs 401/403 lors des requêtes suivantes
    raise Exception("Budget de l'agent épuisé")
```

**Via l'API REST (depuis l'agent lui-même) :**
```http
POST /ai/tokens/{id}/report-usage/
Authorization: AgentBearer <raw_token>
Content-Type: application/json

{
  "cost_usd": 0.042,
  "prompt_tokens": 1250,
  "completion_tokens": 450
}
```

**Réponse lorsque le budget est dépassé (403) :**
```json
{
  "error": "Budget exceeded",
  "status": "suspended"
}
```

#### Ce qui se passe en interne

```
report_usage(cost_usd=0.60, budget_limit=0.50)
    ↓
current_spend_usd += 0.60   →  0.60
current_spend_usd (0.60) >= budget_limit (0.50)
    ↓
token.status      = SUSPENDED
token.suspended_reason = BUDGET_EXCEEDED
    ↓
return False  (toutes les requêtes futures avec ce jeton → 403)
```

---

## 5. Audit Forensique

Chaque requête d'agent peut porter un en-tête `X-Prompt-Trace-ID`. Cet ID est :

- Stocké dans `AgentPendingAction.prompt_trace_id`
- Lié dans l' `AuditLog` (Journal d'audit)

Cela permet une traçabilité précise : *"quel prompt utilisateur a déclenché quelle action backend"*, facilitant les enquêtes après incident et les rapports de conformité.

```http
POST /ai/tokens/{id}/some-action/
Authorization: AgentBearer <raw_token>
X-Prompt-Trace-ID: trace_7f3a2b9c-...
```

---

## Référence de Configuration

Tous les paramètres sont définis dans `settings.py`. Les valeurs par défaut sont gérées via `src/tenxyte/conf/airs.py`.

| Paramètre | Par défaut | Description |
|---|---|---|
| `TENXYTE_AIRS_ENABLED` | `True` | Interrupteur principal pour AIRS |
| `TENXYTE_AIRS_TOKEN_MAX_LIFETIME` | `86400` | Durée de vie maximale du jeton (secondes) |
| `TENXYTE_AIRS_DEFAULT_EXPIRY` | `3600` | Expiration par défaut du jeton si non spécifiée (secondes) |
| `TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS` | `True` | Les jetons doivent déclarer des permissions explicites |
| `TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED` | `True` | Activer/désactiver le disjoncteur |
| `TENXYTE_AIRS_DEFAULT_MAX_RPM` | `60` | RPM max par défaut |
| `TENXYTE_AIRS_DEFAULT_MAX_TOTAL` | `1000` | Plafond total de requêtes par défaut |
| `TENXYTE_AIRS_DEFAULT_MAX_FAILURES` | `10` | Max d'échecs par défaut avant suspension |
| `TENXYTE_AIRS_CONFIRMATION_REQUIRED` | `[]` | Liste des codes de permission nécessitant toujours un HITL |
| `TENXYTE_AIRS_REDACT_PII` | `False` | Activer le caviardage des PII pour les réponses aux agents |
| `TENXYTE_AIRS_BUDGET_TRACKING_ENABLED` | `False` | Activer le suivi budgétaire LLM |
