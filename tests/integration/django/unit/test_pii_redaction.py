import pytest
import json
from django.http import JsonResponse
from tenxyte.middleware import PIIRedactionMiddleware
from tenxyte.models.agent import AgentToken
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

class MockToken:
    def __init__(self, agent_id='test-agent'):
        self.agent_id = agent_id

@pytest.fixture
def pii_middleware():
    def get_response(request):
        # A mock view that returns a JSON response with PII
        data = {
            'user': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '+1234567890',
                'address': '123 Main St, City, Country',
                'public_profile': 'https://example.com/johndoe',
                'nested': {
                    'ssn': '123-45-6789'
                }
            },
            'status': 'success',
            'list_data': [
                {'credit_card': '4111-1111-1111-1111'},
                {'id': 1}
            ]
        }
        return JsonResponse(data)
    
    return PIIRedactionMiddleware(get_response)

@pytest.fixture
def factory():
    return RequestFactory()

def test_pii_redaction_disabled(pii_middleware, factory, settings):
    # Ensure it's disabled
    settings.TENXYTE_AIRS_REDACT_PII = False
    
    request = factory.get('/')
    request.agent_token = MockToken()
    
    response = pii_middleware(request)
    data = json.loads(response.content)
    
    # Should not be redacted
    assert data['user']['email'] == 'john.doe@example.com'
    assert data['user']['phone'] == '+1234567890'

def test_pii_redaction_enabled_but_no_agent(pii_middleware, factory, settings):
    settings.TENXYTE_AIRS_REDACT_PII = True
    
    request = factory.get('/')
    # No request.agent_token
    
    response = pii_middleware(request)
    data = json.loads(response.content)
    
    # Should not be redacted
    assert data['user']['email'] == 'john.doe@example.com'

def test_pii_redaction_success(pii_middleware, factory, settings):
    settings.TENXYTE_AIRS_REDACT_PII = True
    
    request = factory.get('/')
    request.agent_token = MockToken()
    
    response = pii_middleware(request)
    data = json.loads(response.content)
    
    # Should be redacted
    assert data['user']['email'] == '***REDACTED***'
    assert data['user']['phone'] == '***REDACTED***'
    assert data['user']['address'] == '***REDACTED***'
    assert data['user']['nested']['ssn'] == '***REDACTED***'
    assert data['list_data'][0]['credit_card'] == '***REDACTED***'
    
    # Non-PII fields should be intact
    assert data['user']['name'] == 'John Doe'
    assert data['user']['public_profile'] == 'https://example.com/johndoe'
    assert data['status'] == 'success'
    assert data['list_data'][1]['id'] == 1
