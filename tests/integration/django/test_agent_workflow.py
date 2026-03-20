import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from tenxyte.models.base import get_permission_model

Permission = get_permission_model()

@pytest.fixture
def permission():
    return Permission.objects.create(code="data.read", name="Read Data")

@pytest.mark.django_db
def test_full_agent_workflow(authenticated_client, user, application, permission, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = True
    
    user.direct_permissions.add(permission)
    
    # 1. Create Agent Token via REST API
    create_response = authenticated_client.post(reverse('authentication:agent_token_list_create'), {
        'permissions': ['data.read'],
        'expires_in': 3600,
        'application_id': application.id,
        'agent_id': 'integration-agent-v1'
    }, format='json')
    
    assert create_response.status_code == 201, create_response.content
    agent_data = create_response.json()
    assert 'token' in agent_data
    raw_agent_token = agent_data['token']
    token_id = agent_data['id']
    
    # 2. Simulate an Agent accessing a protected View
    agent_client = APIClient()
    agent_client.credentials(
        HTTP_AUTHORIZATION=f'AgentBearer {raw_agent_token}',
        HTTP_X_ACCESS_KEY=application.access_key,
        HTTP_X_ACCESS_SECRET=application._plain_secret
    )
    
    heartbeat_url = reverse('authentication:agent_token_heartbeat', kwargs={'pk': token_id})
    heartbeat_response = agent_client.post(heartbeat_url)
    assert heartbeat_response.status_code == 200, heartbeat_response.content
    
    # 3. Suspend User Token (as Admin/User)
    suspend_url = reverse('authentication:agent_token_suspend', kwargs={'pk': token_id})
    suspend_response = authenticated_client.post(suspend_url, {'reason': 'rate_limit'}, format='json') 
    assert suspend_response.status_code == 200
    
    # 4. Agent tries to use heartbeat again, should fail.
    heartbeat_rejected = agent_client.post(heartbeat_url)
    assert heartbeat_rejected.status_code in [401, 403]
    assert 'Unauthorized or token mismatch' in heartbeat_rejected.json().get('error', '')
    
    # 5. Revoke Token completely
    revoke_url = reverse('authentication:agent_token_revoke', kwargs={'pk': token_id})
    revoke_response = authenticated_client.post(revoke_url, format='json')
    assert revoke_response.status_code == 200
    
    # 6. Agent tries again, should fail (revoked)
    heartbeat_revoked = agent_client.post(heartbeat_url)
    assert heartbeat_revoked.status_code in [401, 403]
    assert 'Unauthorized or token mismatch' in heartbeat_revoked.json().get('error', '')
