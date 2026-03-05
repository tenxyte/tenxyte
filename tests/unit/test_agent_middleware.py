import pytest
from unittest.mock import Mock
from django.http import JsonResponse
from django.test import RequestFactory
from tenxyte.middleware import AgentTokenMiddleware
from tenxyte.models.agent import AgentToken
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.models.base import get_user_model, get_application_model

pytestmark = pytest.mark.django_db

User = get_user_model()
Application = get_application_model()

@pytest.fixture
def mock_get_response():
    def get_response(request):
        return JsonResponse({'status': 'ok'})
    return get_response

@pytest.fixture
def middleware(mock_get_response):
    return AgentTokenMiddleware(mock_get_response)

@pytest.fixture
def test_user():
    return User.objects.create_user(email="agentmanager@example.com", password="password123")

@pytest.fixture
def permission():
    from tenxyte.models.base import get_permission_model
    Permission = get_permission_model()
    return Permission.objects.create(code="docs.read", name="Read")

@pytest.fixture
def test_app(test_user):
    return Application.create_application(name="Test App")[0]

class TestAgentTokenMiddleware:
    def test_no_auth_header(self, middleware):
        request = RequestFactory().get('/')
        response = middleware(request)
        assert getattr(request, 'agent_token', None) is None
        assert response.status_code == 200

    def test_invalid_bearer_prefix(self, middleware):
        request = RequestFactory().get('/', HTTP_AUTHORIZATION='Bearer 1234')
        response = middleware(request)
        assert getattr(request, 'agent_token', None) is None
        assert response.status_code == 200

    def test_valid_token(self, middleware, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission])
        
        # R9: token.token is SHA-256 hash in DB; token.raw_token is the cleartext value for auth
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'AgentBearer {token.raw_token}')
        response = middleware(request)
        
        assert response.status_code == 200
        assert request.agent_token.id == token.id
        assert request.user.id == test_user.id
        assert request.user_id == test_user.id

    def test_invalid_token(self, middleware):
        request = RequestFactory().get('/', HTTP_AUTHORIZATION='AgentBearer invalid_token')
        response = middleware(request)
        
        assert response.status_code == 403
        import json
        data = json.loads(response.content)
        assert data['code'] == 'AGENT_TOKEN_NOT_FOUND'

    def test_suspended_by_circuit_breaker(self, middleware, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission], circuit_breaker={'max_requests_total': 1})
        
        token.current_request_count = 2
        token.save()
        
        # R9: token.token is SHA-256 hash in DB; token.raw_token is the cleartext value for auth
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'AgentBearer {token.raw_token}')
        response = middleware(request)
        
        assert response.status_code == 403
        import json
        data = json.loads(response.content)
        assert data['code'] == 'AGENT_TOKEN_SUSPENDED'
        assert data['reason'] == 'MAX_REQUESTS_TOTAL_EXCEEDED'
