import pytest
from django.utils import timezone
from datetime import timedelta
from tenxyte.models.agent import AgentToken
from tenxyte.models.base import get_user_model, get_application_model
from tenxyte.tasks.agent_tasks import check_agent_heartbeats

pytestmark = pytest.mark.django_db
User = get_user_model()
Application = get_application_model()

@pytest.fixture
def test_user():
    return User.objects.create_user(email="taskuser@example.com", password="password123")

@pytest.fixture
def test_app():
    return Application.create_application(name="Task App")[0]

class TestAgentTasks:
    def test_check_agent_heartbeats_no_stale_tokens(self, test_user, test_app):
        token = AgentToken.objects.create(
            token="token1", agent_id="a1", triggered_by=test_user, application=test_app,
            expires_at=timezone.now() + timedelta(days=1),
            heartbeat_required_every=60,
            last_heartbeat_at=timezone.now()
        )
        count = check_agent_heartbeats()
        assert count == 0
        token.refresh_from_db()
        assert token.status == AgentToken.Status.ACTIVE

    def test_check_agent_heartbeats_stale_token_suspend(self, test_user, test_app):
        token = AgentToken.objects.create(
            token="token2", agent_id="a2", triggered_by=test_user, application=test_app,
            expires_at=timezone.now() + timedelta(days=1),
            heartbeat_required_every=60,
            last_heartbeat_at=timezone.now() - timedelta(seconds=65)
        )
        count = check_agent_heartbeats()
        assert count == 1
        token.refresh_from_db()
        assert token.status == AgentToken.Status.SUSPENDED
        assert token.suspended_reason == AgentToken.SuspendedReason.HEARTBEAT_MISSING
        
    def test_check_agent_heartbeats_never_sent_heartbeat(self, test_user, test_app):
        token = AgentToken.objects.create(
            token="token3", agent_id="a3", triggered_by=test_user, application=test_app,
            expires_at=timezone.now() + timedelta(days=1),
            heartbeat_required_every=60,
            last_heartbeat_at=None
        )
        AgentToken.objects.filter(id=token.id).update(created_at=timezone.now() - timedelta(seconds=65))
        
        count = check_agent_heartbeats()
        assert count == 1
        token.refresh_from_db()
        assert token.status == AgentToken.Status.SUSPENDED
