import pytest
import json
from django.urls import reverse
from rest_framework.test import APIClient
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.models.base import get_permission_model
from django.urls import path
from django.http import JsonResponse
from tenxyte.decorators import require_agent_clearance

Permission = get_permission_model()

@require_agent_clearance(permission_code="critical.delete", human_in_the_loop_required=True)
def dummy_critical_view(request):
    return JsonResponse({'status': 'boom deleted'})

from tenxyte.urls import urlpatterns
urlpatterns.append(path('api/test-critical-delete/', dummy_critical_view, name='test_critical_delete'))

@pytest.fixture
def permission():
    return Permission.objects.create(code="critical.delete", name="Critical Delete")

@pytest.mark.django_db
def test_hitl_workflow(authenticated_client, user, application, permission, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = True
    
    user.direct_permissions.add(permission)
    
    from tenxyte.services.agent_service import AgentTokenService
    service = AgentTokenService()
    token = service.create(triggered_by=user, application=application, granted_permissions=[permission])
    
    # 1. Agent calls the critical endpoint
    from django.test import RequestFactory
    from tenxyte.middleware import AgentTokenMiddleware
    
    def get_response_mock(r):
        return dummy_critical_view(r)
        
    middleware = AgentTokenMiddleware(get_response_mock)
    
    request = RequestFactory().post('/api/test-critical-delete/', data=json.dumps({'target': 42}), content_type='application/json')
    request.META['HTTP_AUTHORIZATION'] = f'AgentBearer {token.token}'
    
    response = middleware(request)
    
    # 2. Should intercept and return 202
    assert response.status_code == 202
    data = json.loads(response.content)
    assert data['status'] == 'pending_confirmation'
    confirmation_token = data['confirmation_token']
    
    assert AgentPendingAction.objects.filter(confirmation_token=confirmation_token).exists()
    
    # 3. User verifies actions and confirms
    list_url = reverse('authentication:agent_pending_action_list')
    list_response = authenticated_client.get(list_url)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]['confirmation_token'] == confirmation_token
    
    confirm_url = reverse('authentication:agent_pending_action_confirm', kwargs={'token': confirmation_token})
    confirm_response = authenticated_client.post(confirm_url, format='json')
    assert confirm_response.status_code == 200
    assert confirm_response.json()['status'] == 'confirmed'
    
    # 4. Agent attempts again, should succeed
    request.META['HTTP_X_ACTION_CONFIRMATION'] = confirmation_token
    response_retry = middleware(request)
    assert response_retry.status_code == 200
    assert json.loads(response_retry.content)['status'] == 'boom deleted'
