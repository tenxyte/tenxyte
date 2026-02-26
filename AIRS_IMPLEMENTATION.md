# Tenxyte AIRS — Plan d'Implémentation Complet

> **AI Responsibility & Security (AIRS)** — Module natif de gouvernance agentique pour le moteur Tenxyte.
> **Date de rédaction :** Février 2026
> **Basé sur :** reflexion.md, ia_research.md, ia_incidents.md, analyse du codebase existant.

---

## Vue d'ensemble

AIRS s'implémente en **3 phases progressives** au-dessus du socle Tenxyte existant (RBAC, Organizations, Audit Log, Middlewares). Chaque phase est **autonome et activable par un setting** — le développeur choisit son niveau de protection.

```
Socle Tenxyte (existant)
│
├── Phase 1 — Identity & Delegation     (AgentToken, RBAC double-passe)
│   ├── Phase 2 — Circuit Breaker       (Coupe-circuit, HITL, Dead Man's Switch)
│   │   └── Phase 3 — Guardrails      (PII Redaction, Cost Budget, Forensic Audit)
│   │
│   └── React SDK (useAgentControl, AIClearanceCenter)
```

---

## Phase 1 — Identity & Delegation

> **Objectif :** Permettre la création de tokens délégués pour les agents IA, avec validation RBAC en double passe.
> **Durée estimée :** 2–3 semaines
> **Setting d'activation :** `TENXYTE_AIRS_ENABLED = True`

### 1.1 — Modèle de données `AgentToken`

**Fichier à créer :** `src/tenxyte/models/agent.py`

```python
class AgentToken(models.Model):
    """
    Token de délégation pour un agent IA.
    L'agent agit AU NOM d'un utilisateur humain avec un sous-ensemble de ses permissions.
    """
    class Status(models.TextChoices):
        ACTIVE    = 'ACTIVE',    'Active'
        SUSPENDED = 'SUSPENDED', 'Suspendu (automatique)'
        REVOKED   = 'REVOKED',   'Révoqué (manuel)'
        EXPIRED   = 'EXPIRED',   'Expiré'

    class SuspendedReason(models.TextChoices):
        RATE_LIMIT        = 'RATE_LIMIT', 'Rate Limit dépassé'
        ANOMALY           = 'ANOMALY',    'Comportement anormal détecté'
        MANUAL            = 'MANUAL',     'Révocation manuelle'
        HEARTBEAT_MISSING = 'HEARTBEAT_MISSING', 'Heartbeat manquant'

    id = AutoFieldClass(primary_key=True)

    # --- Identité et délégation ---
    token        = models.CharField(max_length=128, unique=True, db_index=True)
    agent_id     = models.CharField(max_length=100)          # "claude-3", "my-copilot-v2"
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='agent_tokens'
    )
    application = models.ForeignKey(
        'tenxyte.Application', on_delete=models.CASCADE,
        related_name='agent_tokens'
    )
    organization = models.ForeignKey(
        'tenxyte.Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='agent_tokens'
    )
    granted_permissions = models.ManyToManyField(
        'tenxyte.Permission',
        related_name='agent_tokens',
        blank=True
    )

    # --- Cycle de vie ---
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    expires_at   = models.DateTimeField()
    revoked_at   = models.DateTimeField(null=True, blank=True)
    revoked_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='revoked_agent_tokens'
    )
    suspended_at     = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.CharField(max_length=30, choices=SuspendedReason.choices, null=True, blank=True)

    # --- Circuit Breaker (Phase 2) ---
    max_requests_per_minute = models.PositiveIntegerField(default=60)
    max_requests_total      = models.PositiveIntegerField(default=1000)
    current_request_count   = models.PositiveIntegerField(default=0)
    max_failed_requests     = models.PositiveIntegerField(default=10)
    current_failed_count    = models.PositiveIntegerField(default=0)

    # --- Dead Man's Switch (Phase 2) ---
    heartbeat_required_every = models.PositiveIntegerField(null=True, blank=True)  # secondes
    last_heartbeat_at        = models.DateTimeField(null=True, blank=True)

    # --- Budget (Phase 3) ---
    budget_limit_usd    = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    current_spend_usd   = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # --- Audit ---
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agent_tokens'
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['triggered_by', 'status']),
        ]


class AgentPendingAction(models.Model):
    """
    Action en attente d'une confirmation humaine (Human-in-the-Loop).
    Créée quand un endpoint @require_agent_clearance(human_in_the_loop_required=True)
    reçoit une requête d'un AgentToken.
    """
    id                    = AutoFieldClass(primary_key=True)
    agent_token           = models.ForeignKey(AgentToken, on_delete=models.CASCADE, related_name='pending_actions')
    permission_requested  = models.CharField(max_length=100)
    endpoint              = models.CharField(max_length=255)
    payload               = models.JSONField(default=dict)
    confirmation_token    = models.CharField(max_length=128, unique=True)
    expires_at            = models.DateTimeField()
    confirmed_at          = models.DateTimeField(null=True, blank=True)
    denied_at             = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agent_pending_actions'
```

---

### 1.2 — Service `AgentTokenService`

**Fichier à créer :** `src/tenxyte/services/agent_service.py`

**Méthodes à implémenter :**

```python
class AgentTokenService:
    def create(self, triggered_by, application, granted_permissions,
               expires_in=3600, agent_id='unknown', organization=None,
               circuit_breaker=None, dead_mans_switch=None,
               budget_limit_usd=None) -> AgentToken:
        """
        Crée un AgentToken après vérification que les permissions demandées
        sont un sous-ensemble strict des permissions de l'utilisateur.
        Lève PermissionDenied si l'agent tente de s'accorder plus de droits que l'humain.
        """

    def validate(self, raw_token) -> tuple[AgentToken | None, str | None]:
        """
        Valide un token. Retourne (agent_token, error_code).
        Vérifie: existence, statut ACTIVE, non-expiré, heartbeat valide.
        Met à jour last_used_at et current_request_count (atomique).
        """

    def validate_permission(self, agent_token, permission_code) -> bool:
        """
        Double passe de validation RBAC:
        1. L'AgentToken inclut-il cette permission dans son scope ?
        2. L'utilisateur déléguant a-t-il ENCORE cette permission en base ?
        → Les DEUX conditions doivent être vraies.
        """

    def revoke(self, agent_token, revoked_by=None, reason='') -> AgentToken:
        """Révocation définitive (irréversible). Synchrone, non-cacheable."""

    def suspend(self, agent_token, reason) -> AgentToken:
        """Suspension temporaire (automatique). Peut être levée."""

    def revoke_all_for_user(self, user) -> int:
        """Coupe-circuit nucléaire : révoque tous les tokens actifs d'un user."""

    def revoke_all_for_agent(self, agent_id, organization=None) -> int:
        """Révoque tous les tokens d'un agent_id (scope org optionnel)."""

    def send_heartbeat(self, agent_token) -> AgentToken:
        """Met à jour last_heartbeat_at. Maintient le token en vie."""

    def check_circuit_breaker(self, agent_token) -> tuple[bool, str | None]:
        """
        Vérifie les seuils du circuit breaker.
        Retourne (ok, suspend_reason_or_None).
        """

    def create_pending_action(self, agent_token, permission, endpoint, payload) -> AgentPendingAction:
        """Crée une action HITL en attente. Notifie l'utilisateur (signal)."""

    def confirm_pending_action(self, confirmation_token, confirmed_by) -> AgentPendingAction:
        """Confirme une action en attente. L'appelant re-exécute l'action."""

    def deny_pending_action(self, confirmation_token, denied_by) -> AgentPendingAction:
        """Refuse une action en attente."""
```

---

### 1.3 — Middleware `AgentTokenMiddleware`

**Fichier à modifier :** `src/tenxyte/middleware.py`

C'est la **4ème couche** de la pile middleware Tenxyte (après App Auth, JWT, Org).

```
MIDDLEWARE = [
    'tenxyte.middleware.CORSMiddleware',           # Couche 0
    'tenxyte.middleware.SecurityHeadersMiddleware', # Couche 0
    'tenxyte.middleware.ApplicationAuthMiddleware', # Couche 1 — X-Access-Key
    'tenxyte.middleware.JWTAuthMiddleware',          # Couche 2 — Bearer JWT
    'tenxyte.middleware.OrganizationContextMiddleware', # Couche 3 — X-Org-Slug
    'tenxyte.middleware.AgentTokenMiddleware',       # Couche 4 (AIRS) — AgentBearer
]
```

**Logique du middleware :**

```python
class AgentTokenMiddleware:
    """
    Couche 4 AIRS: Si l'Authorization header est 'AgentBearer <token>',
    valide l'AgentToken et l'attache à request.agent_token.
    Vérifie le circuit breaker à chaque requête.
    """
    def __call__(self, request):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('AgentBearer '):
            request.agent_token = None
            return self.get_response(request)

        raw_token = auth[12:]
        agent_token, error = AgentTokenService().validate(raw_token)

        if error:
            return JsonResponse({'error': error, 'code': f'AGENT_TOKEN_{error}'}, status=403)

        ok, suspend_reason = AgentTokenService().check_circuit_breaker(agent_token)
        if not ok:
            return JsonResponse({
                'error': 'Agent token suspended by circuit breaker',
                'code': 'AGENT_TOKEN_SUSPENDED',
                'reason': suspend_reason
            }, status=403)

        request.agent_token = agent_token
        request.user = agent_token.triggered_by  # L'agent agit "en tant que" l'humain
        return self.get_response(request)
```

---

### 1.4 — Décorateur `@require_agent_clearance`

**Fichier à modifier :** `src/tenxyte/decorators.py`

```python
def require_agent_clearance(
    permission_code: str = None,
    human_in_the_loop_required: bool = False,
    max_risk_score: int = 100
):
    """
    Décorateur pour les endpoints sensibles accessibles par les agents IA.

    Si la requête vient d'un AgentToken :
    - Vérifie que l'agent a la permission (double passe RBAC)
    - Si human_in_the_loop_required=True → retourne 202 + confirmation_token
    - Si le risk_score de l'agent > max_risk_score → refuse directement

    Si la requête vient d'un humain (JWT standard) → passe normalement.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            # Requête d'un agent IA
            if hasattr(request, 'agent_token') and request.agent_token:
                service = AgentTokenService()

                # Vérification de permission (double passe)
                if permission_code:
                    if not service.validate_permission(request.agent_token, permission_code):
                        return JsonResponse({
                            'error': f'Agent insufficient permissions: {permission_code}',
                            'code': 'AGENT_PERMISSION_DENIED'
                        }, status=403)

                # Human-in-the-loop obligatoire
                if human_in_the_loop_required:
                    pending = service.create_pending_action(
                        agent_token=request.agent_token,
                        permission=permission_code or 'unknown',
                        endpoint=request.path,
                        payload=request.data if hasattr(request, 'data') else {}
                    )
                    return JsonResponse({
                        'status': 'pending_confirmation',
                        'message': 'This action requires human approval.',
                        'confirmation_token': pending.confirmation_token,
                        'expires_at': pending.expires_at.isoformat()
                    }, status=202)

            return _call_view(view_func, view_instance, request, view_args, kwargs)
        return wrapper
    return decorator
```

---

### 1.5 — Endpoints REST AIRS

**Fichier à créer :** `src/tenxyte/views/agent_views.py`
**À ajouter dans :** `src/tenxyte/urls.py`

| Méthode | URL | Description |
|---|---|---|
| `POST` | `/ai/tokens/` | Créer un AgentToken (auth JWT requise) |
| `GET` | `/ai/tokens/` | Lister ses AgentTokens actifs |
| `GET` | `/ai/tokens/{id}/` | Détail d'un token |
| `POST` | `/ai/tokens/{id}/revoke/` | Révoquer un token |
| `POST` | `/ai/tokens/{id}/suspend/` | Suspendre un token |
| `POST` | `/ai/tokens/{id}/heartbeat/` | Envoyer un heartbeat |
| `POST` | `/ai/tokens/revoke-all/` | Coupe-circuit nucléaire (tous mes agents) |
| `GET` | `/ai/pending-actions/` | Lister ses actions en attente |
| `POST` | `/ai/pending-actions/{token}/confirm/` | Confirmer une action HITL |
| `POST` | `/ai/pending-actions/{token}/deny/` | Refuser une action HITL |

---

### 1.6 — Settings Phase 1

À ajouter dans `src/tenxyte/conf.py` :

```python
# AIRS — AI Responsibility & Security
TENXYTE_AIRS_ENABLED              = env.bool('TENXYTE_AIRS_ENABLED', default=False)
TENXYTE_AIRS_TOKEN_MAX_LIFETIME   = env.int('TENXYTE_AIRS_TOKEN_MAX_LIFETIME', default=86400)  # 24h max
TENXYTE_AIRS_DEFAULT_EXPIRY       = env.int('TENXYTE_AIRS_DEFAULT_EXPIRY', default=3600)       # 1h par défaut
TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = env.bool('...', default=True)  # empêche "toutes les perms"
```

---

### 1.7 — Migrations Phase 1

```
src/tenxyte/migrations/
  ├── 0001_initial.py          (existant)
  └── 0002_agent_tokens.py     (NOUVEAU — tables agent_tokens, agent_pending_actions)
```

---

## Phase 2 — Circuit Breaker & Human-in-the-Loop

> **Objectif :** Ajouter les mécanismes automatiques de coupe-circuit et la supervision humaine native.
> **Durée estimée :** 1–2 semaines (les champs DB sont déjà prévus en Phase 1)
> **Setting d'activation :** `TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED = True`

### 2.1 — Logique Circuit Breaker (Redis)

La méthode `check_circuit_breaker()` dans `AgentTokenService` doit utiliser Redis pour les compteurs "per-minute" (sliding window), la DB pour les compteurs totaux.

```python
# Seuils configurables par token (dans AgentToken.circuit_breaker JSONField)
# ou globalement dans conf.py :
TENXYTE_AIRS_DEFAULT_MAX_RPM       = 60     # requests/minute
TENXYTE_AIRS_DEFAULT_MAX_TOTAL     = 1000   # total requests
TENXYTE_AIRS_DEFAULT_MAX_FAILURES  = 10     # 403/404 consécutifs
```

**Suspension automatique :** quand un seuil est franchi, le token passe en `SUSPENDED` (pas `REVOKED`). Un admin/user peut le réactiver après investigation.

### 2.2 — Dead Man's Switch (Celery Task)

**Fichier à créer :** `src/tenxyte/tasks/agent_tasks.py`

```python
@shared_task
def check_agent_heartbeats():
    """
    Tâche Celery périodique (toutes les minutes via celery beat).
    Suspend les AgentTokens dont le heartbeat est absent depuis trop longtemps.
    """
    cutoff = timezone.now() - timedelta(seconds=MIN_HEARTBEAT_AGE)
    stale_tokens = AgentToken.objects.filter(
        status=AgentToken.Status.ACTIVE,
        heartbeat_required_every__isnull=False,
        last_heartbeat_at__lt=cutoff
    )
    for token in stale_tokens:
        AgentTokenService().suspend(token, reason=AgentToken.SuspendedReason.HEARTBEAT_MISSING)
```

**Scheduler Celery Beat :**
```python
CELERY_BEAT_SCHEDULE = {
    'check-agent-heartbeats': {
        'task': 'tenxyte.tasks.agent_tasks.check_agent_heartbeats',
        'schedule': 60.0,  # toutes les 60 secondes
    },
}
```

### 2.3 — Permissions Sensibles (Global HITL List)

```python
# conf.py — Actions qui nécessitent TOUJOURS une confirmation humaine
TENXYTE_AIRS_CONFIRMATION_REQUIRED = [
    'users.delete',
    'billing.modify',
    'org.delete',
    'data.export_bulk',
]
```

Le middleware AIRS vérifie cette liste avant même d'atteindre le décorateur. C'est un filet de sécurité global.

### 2.4 — Audit Log IA (Extension)

**Fichier à modifier :** `src/tenxyte/models/security.py` (AuditLog existant)

Migration à ajouter :
```python
# Dans AbstractAuditLog :
agent_token  = models.ForeignKey('tenxyte.AgentToken', null=True, blank=True, on_delete=models.SET_NULL)
on_behalf_of = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='audit_logs_agent')
```

Chaque action via `AgentToken` loggue automatiquement : `{ actor: "claude-3-agent", on_behalf_of: user_id, org: org_id }`.

---

## Phase 3 — Guardrails, PII Redaction & Cost Management

> **Objectif :** Protection des données et responsabilité financière des agents.
> **Durée estimée :** 2 semaines
> **Settings :** `TENXYTE_AIRS_REDACT_PII`, `TENXYTE_AIRS_BUDGET_TRACKING`

### 3.1 — PII Redaction Middleware

**Fichier à créer :** `src/tenxyte/middleware/pii_redaction.py`

```python
class PIIRedactionMiddleware:
    """
    Si la requête est authentifiée via AgentToken ET que TENXYTE_AIRS_REDACT_PII=True,
    intercepte la réponse JSON et masque les champs PII configurés.
    """

    PII_FIELDS = ['email', 'phone', 'ssn', 'date_of_birth', 'address',
                  'credit_card', 'password', 'totp_secret', 'backup_codes']

    def process_response(self, request, response):
        if not getattr(request, 'agent_token', None):
            return response
        if response.get('Content-Type', '').startswith('application/json'):
            data = json.loads(response.content)
            data = self._redact(data)
            response.content = json.dumps(data)
        return response

    def _redact(self, obj):
        """Redact PII fields recursively in JSON."""
        if isinstance(obj, dict):
            return {
                k: '***REDACTED***' if k in self.PII_FIELDS else self._redact(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._redact(item) for item in obj]
        return obj
```

### 3.2 — Budget Tracking (Ledger)

L'application qui utilise l'agent remonte ses coûts LLM via un endpoint dédié. Tenxyte est le **ledger centralisé**.

```python
# Endpoint : POST /ai/tokens/{id}/report-usage/
# Body: { "cost_usd": 0.0045, "prompt_tokens": 1200, "completion_tokens": 300 }
# Tenxyte incrémente current_spend_usd et suspend si budget_limit_usd est dépassé.

TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
```

Quand `current_spend_usd >= budget_limit_usd`, le token passe en `SUSPENDED` avec raison `BUDGET_EXCEEDED`.

### 3.3 — Forensic Audit & Prompt Provenance

Champ additionnel dans `AgentPendingAction` et `AuditLog` :

```python
# Dans AuditLog + AgentPendingAction :
prompt_trace_id = models.CharField(max_length=128, null=True, blank=True)
# Fourni par l'appelant (l'application IA) via le header X-Prompt-Trace-ID.
# Permet de lier une action dangereuse à l'identifiant du prompt LLM source.
```

---

## Phase 4 — SDK React `@tenxyte/react/ai-security`

> **Objectif :** Composants front-end pour la supervision et le consentement agent.
> **Durée estimée :** 2–3 semaines (dans le repo react-tenxyte)
> **Dépend de :** Phase 1 + 2 backend complètes

### 4.1 — Hooks

```tsx
// Création et contrôle des tokens
const { createAgentToken, revokeAgent, suspendAgent, agentTokens } = useAgentControl()

// Confirmation HITL — écoute le polling ou WebSocket
const { pendingActions, confirmAgentAction, denyAgentAction } = useAgentApprovals()

// Vérification des permissions d'un agent
const { canAgentDo } = useAgentPermissions(agentId)
```

### 4.2 — Composants

```tsx
// Dashboard de contrôle — liste les agents actifs avec boutons de suspension
<AgentControlPanel />

// Carte individuelle d'un agent
<AgentCard agent={token} onSuspend={...} onRevoke={...} />

// Modal de confirmation HITL
<AgentConfirmationModal action={pendingAction} onConfirm={...} onDeny={...} />

// Superposition globale — le composant s'intègre une fois dans le layout principal
// Il affiche les notifications HITL sans autre configuration
<AIClearanceCenter theme="dark" position="bottom-right" />
```

### 4.3 — Flux de consentement (User Flow)

```
Utilisateur → active un agent Copilot
  → createAgentToken({ agentId: 'copilot', permissions: ['docs.read','email.send'], expiresIn: 3600 })
  → token retourné au backend IA
  
Backend IA → appelle POST /api/bulk-delete-documents/ avec AgentBearer <token>
  → Tenxyte intercepte → @require_agent_clearance(human_in_the_loop_required=True)
  → Retourne 202 + confirmation_token

<AIClearanceCenter /> → reçoit la notification HITL
  → Affiche : "Copilot veut supprimer 47 documents — Confirmer ?"
  → Utilisateur clique "Confirmer"
  → POST /ai/pending-actions/{confirmation_token}/confirm/
  → Returned 200 — backend IA peut ré-exécuter l'action
```

---

## Priorités et Timeline

```
SEMAINE 1-2     SEMAINE 3-4         SEMAINE 5-6         SEMAINE 7-9
──────────────  ─────────────────   ─────────────────   ─────────────
AgentToken DB   AgentTokenService   PIIRedaction        React SDK
Migration       AgentMiddleware     BudgetTracking      AIClearanceCenter
               @require_clearance  ForensicAudit        useAgentControl
               REST Endpoints      Settings Phase 3     Intégration tests
               Tests Phase 1       Tests Phase 3
               Settings Phase 1
```

---

## Tests à écrire (TDD)

```
tests/unit/
  test_agent_service.py           # create, validate, revoke, suspend, double-passe RBAC
  test_agent_middleware.py        # AgentBearer, token expiré, token suspendu, double-passe
  test_agent_decorators.py        # @require_agent_clearance, HITL, permission denied
  test_agent_circuit_breaker.py   # Rate limit, anomaly, heartbeat missing
  test_pii_redaction.py           # Masquage des champs PII dans les réponses

tests/integration/
  test_agent_workflow.py          # Flux complet : création → action → révocation
  test_hitl_workflow.py           # Flux HITL : action → 202 → confirmation → ré-exec
```

---

## Mise à jour ROADMAP.md

Ce plan correspond à une **Phase 1.5** à insérer dans `ROADMAP.md` entre la Phase 1 (Parité Compétitive) et la Phase 2 (SaaS). Voici le résumé des tâches à cocher :

```
### 1.5 — Tenxyte AIRS (AI Responsibility & Security)

- [x] Model `AgentToken` + `AgentPendingAction` (migrations incluses)
- [x] `AgentTokenService` — create, validate, revoke, suspend, RBAC double-passe
- [x] `AgentTokenMiddleware` — couche 4 du middleware stack
- [x] `@require_agent_clearance` decorator
- [x] REST Endpoints AIRS (10 endpoints)
- [ ] Circuit Breaker (Redis sliding window)
- [ ] Dead Man's Switch (Celery task)
- [ ] TENXYTE_AIRS_CONFIRMATION_REQUIRED (liste globale HITL)
- [ ] Extension AuditLog (agent_token + on_behalf_of)
- [ ] PIIRedactionMiddleware
- [ ] Budget Tracking (Cost Ledger)
- [ ] Forensic Audit (X-Prompt-Trace-ID)
- [x] Settings AIRS dans conf.py
- [x] Tests unitaires (5 fichiers)
- [ ] Tests d'intégration (2 fichiers)
- [ ] React SDK: useAgentControl, useAgentApprovals, AIClearanceCenter
- [ ] Documentation docs/airs.md
```

---

## Conclusion

Tenxyte AIRS répond aux **4 failles les plus critiques** documentées dans les incidents IA récents (EchoLeak, Shadow Escape, Slack AI, GitHub MCP) :

| Incident | Vecteur | Solution AIRS |
|---|---|---|
| EchoLeak (MS Copilot) | Exfiltration de données via agent | PIIRedactionMiddleware + RBAC scope |
| Shadow Escape (ChatGPT/Gemini) | Agent hijacking silencieux | Circuit Breaker + Dead Man's Switch |
| GitHub MCP | Injection via repo issue | RBAC double-passe (scope agentique) |
| Slack AI Injection | Accès à données hors scope | Contrat de délégation + err 403 agent |
