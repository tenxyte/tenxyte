import pytest
import json
from django.test import RequestFactory
from django.http import JsonResponse
from tenxyte.middleware import AgentTokenMiddleware
from tenxyte.models.security import AuditLog
from tenxyte.models.agent import AgentToken
from django.contrib.auth import get_user_model
from tenxyte.models import get_application_model

User = get_user_model()
Application = get_application_model()

@pytest.fixture
def agent_middleware():
    def get_response(request):
        # Mock successful view response
        return JsonResponse({'status': 'ok'}, status=200)
    return AgentTokenMiddleware(get_response)

@pytest.mark.django_db
def test_agent_middleware_captures_prompt_trace_id(agent_middleware, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AUDIT_LOGGING_ENABLED = True
    
    # Setup test token
    user = User.objects.create_user(email="forensic@test.com", password="password")
    app = Application.objects.create(name="TestApp")
    # R9: AgentToken.token stores a SHA-256 hash; raw value must be passed in the auth header
    raw_token = "test-trace-token-123"
    token = AgentToken.objects.create(
        token=AgentToken._hash_token(raw_token),  # store hash in DB
        agent_id="test-agent",
        triggered_by=user,
        application=app,
        expires_at="2099-12-31T23:59:59Z"
    )
    
    factory = RequestFactory()
    request = factory.post(
        '/api/test-action/',
        data=json.dumps({'action': 'delete'}),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'AgentBearer {raw_token}',  # raw value for lookup
        HTTP_X_PROMPT_TRACE_ID='trace_abc123'
    )
    
    # Mocking check_circuit_breaker since this is just testing the middleware
    # Actually, the middleware uses AgentTokenService directly, so it will hit DB
    # The token is created, it should pass basic validation if not expired.
    
    # Process request
    response = agent_middleware(request)
    
    assert response.status_code == 200
    
    # Check AuditLog
    log = AuditLog.objects.filter(agent_token=token).first()
    assert log is not None
    assert log.action == 'agent_action'
    assert log.prompt_trace_id == 'trace_abc123'
    assert log.on_behalf_of == user
    assert log.details['actor'] == 'test-agent'
