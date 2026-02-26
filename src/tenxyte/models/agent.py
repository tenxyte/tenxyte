from django.db import models
from django.conf import settings
from tenxyte.models.base import AutoFieldClass

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
        BUDGET_EXCEEDED   = 'BUDGET_EXCEEDED', 'Budget dépassé'

    id = AutoFieldClass(primary_key=True)

    # --- Identité et délégation ---
    token        = models.CharField(max_length=128, unique=True, db_index=True)
    agent_id     = models.CharField(max_length=100)          # "claude-3.5-sonnet", "my-copilot-v2"
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

    def __str__(self):
        return f"AgentToken {self.agent_id} by {self.triggered_by_id} ({self.status})"


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
    confirmation_token    = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at            = models.DateTimeField()
    confirmed_at          = models.DateTimeField(null=True, blank=True)
    denied_at             = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    
    # --- Forensic Audit (Phase 3) ---
    prompt_trace_id       = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = 'agent_pending_actions'

    def __str__(self):
        return f"PendingAction {self.endpoint} for {self.agent_token_id}"
