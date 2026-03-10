import pytest
import json
from django.http import JsonResponse
from django.test import RequestFactory
from tenxyte.decorators import require_agent_clearance
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.models.base import get_user_model, get_application_model, get_permission_model

pytestmark = pytest.mark.django_db
User = get_user_model()
Application = get_application_model()
Permission = get_permission_model()

@pytest.fixture
def test_user():
    return User.objects.create_user(email="docs@example.com", password="password123")

@pytest.fixture
def test_app(test_user):
    return Application.create_application(name="Test App")[0]

@pytest.fixture
def permission():
    return Permission.objects.create(code="docs.delete", name="Delete Docs")

@require_agent_clearance(permission_code="docs.delete", human_in_the_loop_required=True)
def dummy_view_hitl(request):
    return JsonResponse({'status': 'deleted'})

@require_agent_clearance(permission_code="docs.delete")
def dummy_view_direct(request):
    return JsonResponse({'status': 'deleted'})

class TestRequireAgentClearanceDecorator:
    def test_direct_access_by_human(self, test_user):
        # A human with standard JWT will simply pass through
        request = RequestFactory().post('/api/docs/')
        request.user = test_user
        
        response = dummy_view_direct(request)
        assert response.status_code == 200

    def test_agent_with_insufficient_perms(self, test_user, test_app, permission):
        # User has the permission, but does NOT delegate it to the agent
        test_user.direct_permissions.add(permission)
        
        # We need a different permission to delegate so the token is created successfully
        from tenxyte.models.base import get_permission_model
        Permission = get_permission_model()
        read_perm = Permission.objects.create(code="docs.read", name="Read Docs")
        test_user.direct_permissions.add(read_perm)
        
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[read_perm])
        
        request = RequestFactory().post('/api/docs/')
        request.user = test_user
        request.agent_token = token
        
        response = dummy_view_direct(request)
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data['code'] == 'AGENT_PERMISSION_DENIED'

    def test_agent_with_sufficient_perms(self, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission])
        
        request = RequestFactory().post('/api/docs/')
        request.user = test_user
        request.agent_token = token
        
        response = dummy_view_direct(request)
        assert response.status_code == 200

    def test_agent_hitl_required(self, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission])
        
        request = RequestFactory().post('/api/docs/')
        request.user = test_user
        request.agent_token = token
        
        response = dummy_view_hitl(request)
        assert response.status_code == 202
        data = json.loads(response.content)
        assert data['status'] == 'pending_confirmation'
        assert 'confirmation_token' in data
        
        # Verify an action was created in DB
        assert AgentPendingAction.objects.filter(confirmation_token=data['confirmation_token']).exists()
