from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.models.base import get_application_model
from django.utils import timezone
from tenxyte.conf import auth_settings
from django.core.exceptions import PermissionDenied


class AgentTokenListCreateView(APIView):
    """
    GET /ai/tokens/
    POST /ai/tokens/
    Liste les AgentTokens actifs ou en crée un nouveau.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tokens = AgentToken.objects.filter(triggered_by=request.user).order_by('-created_at')
        result = []
        for t in tokens:
            result.append({
                'id': t.id,
                'agent_id': t.agent_id,
                'status': t.status,
                'expires_at': t.expires_at.isoformat(),
                'created_at': t.created_at.isoformat(),
                'organization': t.organization.slug if t.organization else None,
                'current_request_count': t.current_request_count,
            })
        return JsonResponse(result, safe=False)

    def post(self, request):
        if not getattr(auth_settings, 'AIRS_ENABLED', True):
            return JsonResponse({'error': 'AIRS is disabled'}, status=400)
            
        data = request.data
        agent_id = data.get('agent_id', 'unknown')
        expires_in = data.get('expires_in')
        permissions_requested = data.get('permissions', [])
        organization_slug = data.get('organization')
        budget_limit_usd = data.get('budget_limit_usd')

        # Requires application
        if not hasattr(request, 'application') or not request.application:
            Application = get_application_model()
            app = Application.objects.filter(is_active=True).first()
            if not app:
                return JsonResponse({'error': 'Application context required'}, status=400)
            application = app
        else:
            application = request.application
            
        organization = None
        if organization_slug:
            try:
                from tenxyte.models.base import get_organization_model
                Organization = get_organization_model()
                organization = Organization.objects.get(slug=organization_slug, is_active=True)
            except Exception:
                return JsonResponse({'error': 'Organization not found'}, status=404)

        service = AgentTokenService()
        
        try:
            token = service.create(
                triggered_by=request.user,
                application=application,
                granted_permissions=permissions_requested,
                expires_in=expires_in,
                agent_id=agent_id,
                organization=organization,
                circuit_breaker=data.get('circuit_breaker'),
                dead_mans_switch=data.get('dead_mans_switch'),
                budget_limit_usd=budget_limit_usd,
            )
        except PermissionDenied as e:
            return JsonResponse({'error': str(e), 'code': 'PERMISSION_DENIED'}, status=403)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

        return JsonResponse({
            'id': token.id,
            'token': token.token,
            'agent_id': token.agent_id,
            'status': token.status,
            'expires_at': token.expires_at.isoformat(),
        }, status=201)


class AgentTokenDetailView(APIView):
    """
    GET /ai/tokens/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        return JsonResponse({
            'id': t.id,
            'agent_id': t.agent_id,
            'status': t.status,
            'expires_at': t.expires_at.isoformat(),
            'created_at': t.created_at.isoformat(),
            'organization': t.organization.slug if t.organization else None,
            'current_request_count': t.current_request_count,
        })


class AgentTokenRevokeView(APIView):
    """
    POST /ai/tokens/{id}/revoke/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        AgentTokenService().revoke(t, revoked_by=request.user)
        return JsonResponse({'status': 'revoked'})


class AgentTokenSuspendView(APIView):
    """
    POST /ai/tokens/{id}/suspend/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        AgentTokenService().suspend(t, reason=AgentToken.SuspendedReason.MANUAL)
        return JsonResponse({'status': 'suspended'})


class AgentTokenHeartbeatView(APIView):
    """
    POST /ai/tokens/{id}/heartbeat/
    Called by the agent itself using the token.
    """
    def post(self, request, pk):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('AgentBearer '):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        raw_token = auth[12:]
        service = AgentTokenService()
        token, error = service.validate(raw_token)
        
        if error or str(token.id) != str(pk):
            return JsonResponse({'error': 'Unauthorized or token mismatch'}, status=403)
            
        service.send_heartbeat(token)
        return JsonResponse({'status': 'ok'})


class AgentTokenRevokeAllView(APIView):
    """
    POST /ai/tokens/revoke-all/
    Coupe-circuit nucléaire.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = AgentTokenService().revoke_all_for_user(request.user)
        return JsonResponse({'status': 'revoked', 'count': count})


class AgentPendingActionListView(APIView):
    """
    GET /ai/pending-actions/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        actions = AgentPendingAction.objects.filter(
            agent_token__triggered_by=request.user,
            confirmed_at__isnull=True,
            denied_at__isnull=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')
        
        result = []
        for a in actions:
            result.append({
                'id': a.id,
                'agent_id': a.agent_token.agent_id,
                'permission': a.permission_requested,
                'endpoint': a.endpoint,
                'payload': a.payload,
                'confirmation_token': a.confirmation_token,
                'expires_at': a.expires_at.isoformat(),
                'created_at': a.created_at.isoformat(),
            })
        return JsonResponse(result, safe=False)


class AgentPendingActionConfirmView(APIView):
    """
    POST /ai/pending-actions/{token}/confirm/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        service = AgentTokenService()
        action = service.confirm_pending_action(token, confirmed_by=request.user)
        if not action or action.agent_token.triggered_by != request.user:
            return JsonResponse({'error': 'Invalid or expired token'}, status=400)
            
        return JsonResponse({'status': 'confirmed'})


class AgentPendingActionDenyView(APIView):
    """
    POST /ai/pending-actions/{token}/deny/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        service = AgentTokenService()
        action = service.deny_pending_action(token, denied_by=request.user)
        if not action or action.agent_token.triggered_by != request.user:
            return JsonResponse({'error': 'Invalid or expired token'}, status=400)
            
        return JsonResponse({'status': 'denied'})
