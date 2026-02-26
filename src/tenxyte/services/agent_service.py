import secrets
import string
from django.utils import timezone
from datetime import timedelta
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.conf import auth_settings
from django.core.exceptions import PermissionDenied


class AgentTokenService:
    def _generate_token(self) -> str:
        """Generate a random 48-character secure token."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
        
    def _generate_confirmation_token(self) -> str:
        return secrets.token_urlsafe(64)

    def create(self, triggered_by, application, granted_permissions,
               expires_in=None, agent_id='unknown', organization=None,
               circuit_breaker=None, dead_mans_switch=None,
               budget_limit_usd=None) -> AgentToken:
        """
        Crée un AgentToken après vérification que les permissions demandées
        sont un sous-ensemble strict des permissions de l'utilisateur.
        """
        # Ensure AIRS is enabled
        if not auth_settings.AIRS_ENABLED:
            raise ValueError("AIRS is disabled. Enable it by setting TENXYTE_AIRS_ENABLED = True")

        # Determine expiry
        if expires_in is None:
            expires_in = auth_settings.AIRS_DEFAULT_EXPIRY
        
        # Cap expiry to maximum lifetime
        if expires_in > auth_settings.AIRS_TOKEN_MAX_LIFETIME:
            expires_in = auth_settings.AIRS_TOKEN_MAX_LIFETIME

        # Verify permissions: Check if the user has all the requested permissions.
        # Check explicit permissions setting:
        if auth_settings.AIRS_REQUIRE_EXPLICIT_PERMISSIONS and not granted_permissions:
            raise PermissionDenied("Agent tokens must request explicit permissions.")

        for perm in granted_permissions:
            # We assume granted_permissions is a list of Permission objects or codes
            perm_code = perm.code if hasattr(perm, 'code') else perm
            
            # If the user doesn't have the permission, raise PermissionDenied
            # In an org context, we'd need to check both global or org permissions, 
            # but User.has_permission handles global.
            if organization:
                # First check org permission
                if not triggered_by.has_org_permission(organization, perm_code):
                    raise PermissionDenied(f"User does not have permission '{perm_code}' in the specified organization.")
            else:
                if not triggered_by.has_permission(perm_code):
                    raise PermissionDenied(f"User does not have permission '{perm_code}'.")

        # Circuit breaker settings mapping from dict if provided
        cb_kwargs = {}
        if circuit_breaker:
            if 'max_requests_per_minute' in circuit_breaker:
                cb_kwargs['max_requests_per_minute'] = circuit_breaker['max_requests_per_minute']
            if 'max_requests_total' in circuit_breaker:
                cb_kwargs['max_requests_total'] = circuit_breaker['max_requests_total']
            if 'max_failed_requests' in circuit_breaker:
                cb_kwargs['max_failed_requests'] = circuit_breaker['max_failed_requests']

        # DMS mapping
        dms_kwargs = {}
        if dead_mans_switch:
            if 'heartbeat_required_every' in dead_mans_switch:
                dms_kwargs['heartbeat_required_every'] = dead_mans_switch['heartbeat_required_every']
                dms_kwargs['last_heartbeat_at'] = timezone.now()

        # Create token object
        token = AgentToken.objects.create(
            token=self._generate_token(),
            agent_id=agent_id,
            triggered_by=triggered_by,
            application=application,
            organization=organization,
            expires_at=timezone.now() + timedelta(seconds=expires_in),
            budget_limit_usd=budget_limit_usd,
            **cb_kwargs,
            **dms_kwargs
        )

        # Set permissions
        # If granted_permissions holds models, just use set(). 
        # If it holds strings, fetch them first.
        if granted_permissions:
            from tenxyte.models.base import get_permission_model
            PermissionModel = get_permission_model()
            
            perms_to_add = []
            for perm in granted_permissions:
                if isinstance(perm, str):
                    perms_to_add.append(PermissionModel.objects.get(code=perm))
                else:
                    perms_to_add.append(perm)
                    
            token.granted_permissions.set(perms_to_add)

        return token

    def validate(self, raw_token) -> tuple[AgentToken | None, str | None]:
        """
        Valide un token. Retourne (agent_token, error_code).
        Vérifie: existence, statut ACTIVE, non-expiré, heartbeat valide.
        Met à jour last_used_at et current_request_count (atomique).
        """
        try:
            token = AgentToken.objects.get(token=raw_token)
        except AgentToken.DoesNotExist:
            return None, "NOT_FOUND"

        if token.status != AgentToken.Status.ACTIVE:
            return token, f"STATUS_{token.status}"

        # Check explicit expiry
        if token.expires_at < timezone.now():
            token.status = AgentToken.Status.EXPIRED
            token.save(update_fields=['status'])
            return token, "EXPIRED"

        # Check heartbeat if dead man's switch is active
        if token.heartbeat_required_every and token.last_heartbeat_at:
            max_age = timezone.now() - timedelta(seconds=token.heartbeat_required_every)
            if token.last_heartbeat_at < max_age:
                self.suspend(token, AgentToken.SuspendedReason.HEARTBEAT_MISSING)
                return token, "HEARTBEAT_MISSING"

        # Update last used
        token.last_used_at = timezone.now()
        # Increment request count using F object for atomicity
        from django.db.models import F
        token.current_request_count = F('current_request_count') + 1
        token.save(update_fields=['last_used_at', 'current_request_count'])
        
        # Refresh from db to get the actual value for F object
        token.refresh_from_db(fields=['current_request_count'])

        return token, None

    def validate_permission(self, agent_token, permission_code) -> bool:
        """
        Double passe de validation RBAC:
        1. L'AgentToken inclut-il cette permission dans son scope ?
        2. L'utilisateur déléguant a-t-il ENCORE cette permission en base ?
        """
        # Passe 1: Agent scope
        agent_has_perm = agent_token.granted_permissions.filter(code=permission_code).exists()
        
        # If explicit permissions aren't strictly required and the agent has no explicit permissions,
        # we treat it as requesting the user's full permissions scope.
        if not agent_has_perm:
            if auth_settings.AIRS_REQUIRE_EXPLICIT_PERMISSIONS:
                return False
            # If not requiring explicit, and list is empty, treat as all permissions delegated.
            if agent_token.granted_permissions.exists():
                return False

        # Passe 2: Humain (Utilisateur)
        user = agent_token.triggered_by
        
        # Check if the user still has this permission contextually. 
        if agent_token.organization:
            if not user.has_org_permission(agent_token.organization, permission_code):
                return False
        else:
            if not user.has_permission(permission_code):
                return False
                
        return True

    def revoke(self, agent_token, revoked_by=None, reason='') -> AgentToken:
        """Révocation définitive (irréversible)."""
        agent_token.status = AgentToken.Status.REVOKED
        agent_token.revoked_at = timezone.now()
        agent_token.revoked_by = revoked_by
        agent_token.suspended_reason = AgentToken.SuspendedReason.MANUAL if not reason else reason
        agent_token.save(update_fields=['status', 'revoked_at', 'revoked_by', 'suspended_reason'])
        return agent_token

    def suspend(self, agent_token, reason) -> AgentToken:
        """Suspension temporaire (automatique). Peut être levée."""
        agent_token.status = AgentToken.Status.SUSPENDED
        agent_token.suspended_at = timezone.now()
        agent_token.suspended_reason = reason
        agent_token.save(update_fields=['status', 'suspended_at', 'suspended_reason'])
        return agent_token

    def revoke_all_for_user(self, user) -> int:
        """Coupe-circuit nucléaire : révoque tous les tokens actifs d'un user."""
        updated_count = AgentToken.objects.filter(
            triggered_by=user,
            status=AgentToken.Status.ACTIVE
        ).update(
            status=AgentToken.Status.REVOKED,
            revoked_at=timezone.now(),
            revoked_by=user,
            suspended_reason=AgentToken.SuspendedReason.MANUAL
        )
        return updated_count

    def revoke_all_for_agent(self, agent_id, organization=None) -> int:
        """Révoque tous les tokens d'un agent_id (scope org optionnel)."""
        query = AgentToken.objects.filter(
            agent_id=agent_id,
            status=AgentToken.Status.ACTIVE
        )
        if organization:
            query = query.filter(organization=organization)
            
        updated_count = query.update(
            status=AgentToken.Status.REVOKED,
            revoked_at=timezone.now(),
            suspended_reason=AgentToken.SuspendedReason.MANUAL
        )
        return updated_count

    def send_heartbeat(self, agent_token) -> AgentToken:
        """Met à jour last_heartbeat_at. Maintient le token en vie."""
        agent_token.last_heartbeat_at = timezone.now()
        # In phase 2, if the token was suspended for missed heartbeat but recovers, 
        # it requires manual unsuspension for security, so we don't auto-activate it here.
        agent_token.save(update_fields=['last_heartbeat_at'])
        return agent_token

    def check_circuit_breaker(self, agent_token) -> tuple[bool, str | None]:
        """
        Vérifie les seuils du circuit breaker en DB et Cache.
        """
        if not auth_settings.AIRS_CIRCUIT_BREAKER_ENABLED:
            return True, None

        # Check max requests total
        if agent_token.max_requests_total and agent_token.current_request_count > agent_token.max_requests_total:
            self.suspend(agent_token, AgentToken.SuspendedReason.RATE_LIMIT)
            return False, "MAX_REQUESTS_TOTAL_EXCEEDED"
            
        # Check max failed requests
        if agent_token.max_failed_requests and agent_token.current_failed_count > agent_token.max_failed_requests:
            self.suspend(agent_token, AgentToken.SuspendedReason.ANOMALY)
            return False, "MAX_FAILED_REQUESTS_EXCEEDED"
            
        # Check budget limit
        if agent_token.budget_limit_usd and agent_token.current_spend_usd >= agent_token.budget_limit_usd:
            self.suspend(agent_token, AgentToken.SuspendedReason.BUDGET_EXCEEDED) # Note: BUDGET_EXCEEDED doesn't exist natively. ANOMALY can work or extending.
            return False, "BUDGET_EXCEEDED"

        # Rate limit per minute using cache
        if agent_token.max_requests_per_minute:
            from django.core.cache import cache
            cache_key = f"airs_rpm_{agent_token.token}"
            current_minute_requests = cache.get(cache_key, 0)
            
            if current_minute_requests >= agent_token.max_requests_per_minute:
                self.suspend(agent_token, AgentToken.SuspendedReason.RATE_LIMIT)
                return False, "RATE_LIMIT_EXCEEDED"
                
            if current_minute_requests == 0:
                cache.set(cache_key, 1, timeout=60)
            else:
                try:
                    cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, current_minute_requests + 1, timeout=60)
        
        return True, None

    def create_pending_action(self, agent_token, permission, endpoint, payload) -> AgentPendingAction:
        """Crée une action HITL en attente."""
        # By default actions expire in 10 minutes if unconfirmed.
        expires_at = timezone.now() + timedelta(minutes=10)
        
        return AgentPendingAction.objects.create(
            agent_token=agent_token,
            permission_requested=permission,
            endpoint=endpoint,
            payload=payload,
            confirmation_token=self._generate_confirmation_token(),
            expires_at=expires_at
        )

    def confirm_pending_action(self, confirmation_token, confirmed_by=None) -> AgentPendingAction | None:
        """Confirme une action en attente."""
        try:
            action = AgentPendingAction.objects.get(
                confirmation_token=confirmation_token,
                confirmed_at__isnull=True,
                denied_at__isnull=True
            )
        except AgentPendingAction.DoesNotExist:
            return None
            
        if action.expires_at < timezone.now():
            return None
            
        action.confirmed_at = timezone.now()
        action.save(update_fields=['confirmed_at'])
        return action

    def deny_pending_action(self, confirmation_token, denied_by=None) -> AgentPendingAction | None:
        """Refuse une action en attente."""
        try:
            action = AgentPendingAction.objects.get(
                confirmation_token=confirmation_token,
                confirmed_at__isnull=True,
                denied_at__isnull=True
            )
        except AgentPendingAction.DoesNotExist:
            return None
            
        if action.expires_at < timezone.now():
            return None
            
        action.denied_at = timezone.now()
        action.save(update_fields=['denied_at'])
        return action

    def report_usage(self, agent_token, cost_usd: float = 0.0, prompt_tokens: int = 0, completion_tokens: int = 0) -> bool:
        """
        Reports usage costs for an agent token and suspends it if budget is exceeded.
        Returns True if successful, False if budget exceeded.
        """
        from tenxyte.conf import auth_settings
        if not getattr(auth_settings, 'AIRS_BUDGET_TRACKING_ENABLED', False):
            return True
            
        if not agent_token.budget_limit_usd:
            return True
            
        from decimal import Decimal
        agent_token.current_spend_usd += Decimal(str(cost_usd))
        agent_token.save(update_fields=['current_spend_usd'])
        
        if agent_token.current_spend_usd >= agent_token.budget_limit_usd:
            self.suspend(agent_token, reason=AgentToken.SuspendedReason.BUDGET_EXCEEDED)
            return False
            
        return True
