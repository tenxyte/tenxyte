import pytest
from django.utils import timezone
from tenxyte.models.agent import AgentToken
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.models import get_application_model, get_user_model
from django.core.exceptions import PermissionDenied

User = get_user_model()
Application = get_application_model()

@pytest.fixture
def user_app(db):
    user = User.objects.create_user(email="budget@test.com", password="password")
    app = Application.objects.create(name="TestApp")
    return user, app

@pytest.fixture
def agent_service():
    return AgentTokenService()

@pytest.mark.django_db
def test_report_usage_success(agent_service, user_app, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = False
    
    user, app = user_app
    token = agent_service.create(
        triggered_by=user,
        application=app,
        granted_permissions=[],
        budget_limit_usd=1.00 # $1 limit
    )
    
    # Report 10 cents
    success = agent_service.report_usage(token, cost_usd=0.10)
    
    assert success is True
    token.refresh_from_db()
    assert float(token.current_spend_usd) == 0.10
    assert token.status == AgentToken.Status.ACTIVE

@pytest.mark.django_db
def test_report_usage_exceeds_budget(agent_service, user_app, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = False
    
    user, app = user_app
    token = agent_service.create(
        triggered_by=user,
        application=app,
        granted_permissions=[],
        budget_limit_usd=0.50 # 50 cents limit
    )
    
    # Report 60 cents
    success = agent_service.report_usage(token, cost_usd=0.60)
    
    assert success is False
    token.refresh_from_db()
    assert float(token.current_spend_usd) == 0.60
    assert token.status == AgentToken.Status.SUSPENDED
    assert token.suspended_reason == AgentToken.SuspendedReason.BUDGET_EXCEEDED

@pytest.mark.django_db
def test_report_usage_disabled(agent_service, user_app, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = False
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = False
    
    user, app = user_app
    token = agent_service.create(
        triggered_by=user,
        application=app,
        granted_permissions=[],
        budget_limit_usd=1.00
    )
    
    success = agent_service.report_usage(token, cost_usd=2.00)
    
    assert success is True
    token.refresh_from_db()
    assert float(token.current_spend_usd) == 0.00 # Not recorded
    assert token.status == AgentToken.Status.ACTIVE

@pytest.mark.django_db
def test_report_usage_no_limit(agent_service, user_app, settings):
    settings.TENXYTE_AIRS_ENABLED = True
    settings.TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
    settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = False
    
    user, app = user_app
    token = agent_service.create(
        triggered_by=user,
        application=app,
        granted_permissions=[],
        budget_limit_usd=None # Unlimited
    )
    
    success = agent_service.report_usage(token, cost_usd=100.00)
    
    assert success is True
    token.refresh_from_db()
    assert float(token.current_spend_usd) == 0.00 # Not recorded if no limit set by design in this implementation
    assert token.status == AgentToken.Status.ACTIVE
