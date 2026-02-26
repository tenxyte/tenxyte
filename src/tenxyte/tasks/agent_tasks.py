import logging
from django.utils import timezone
from datetime import timedelta

# Try to import celery shared_task, if Celery is not installed, provide a mock
try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func

from tenxyte.models.agent import AgentToken
from tenxyte.services.agent_service import AgentTokenService

logger = logging.getLogger(__name__)

@shared_task
def check_agent_heartbeats():
    """
    Tâche Celery périodique (toutes les minutes via celery beat).
    Suspend les AgentTokens dont le heartbeat est absent depuis trop longtemps.
    """
    service = AgentTokenService()
    now = timezone.now()
    
    stale_tokens = AgentToken.objects.filter(
        status=AgentToken.Status.ACTIVE,
        heartbeat_required_every__isnull=False
    )
    
    suspended_count = 0
    for token in stale_tokens:
        if not token.last_heartbeat_at:
            # If no heartbeat ever sent, use created_at
            age = now - token.created_at
        else:
            age = now - token.last_heartbeat_at
            
        if age > timedelta(seconds=token.heartbeat_required_every):
            service.suspend(token, reason=AgentToken.SuspendedReason.HEARTBEAT_MISSING)
            suspended_count += 1
            
    if suspended_count > 0:
        logger.warning(f"Suspended {suspended_count} AgentTokens due to missing heartbeats.")
        
    return suspended_count
