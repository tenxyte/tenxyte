import pytest
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.models.base import get_user_model, get_application_model, get_permission_model
from tenxyte.services.agent_service import AgentTokenService

pytestmark = pytest.mark.django_db

User = get_user_model()
Application = get_application_model()
Permission = get_permission_model()

@pytest.fixture
def test_user():
    user = User.objects.create_user(email="agentmanager@example.com", password="password123")
    return user

@pytest.fixture
def test_app():
    return Application.create_application(name="Test App")[0]

@pytest.fixture
def permissions():
    p1 = Permission.objects.create(code="docs.read", name="Read Docs")
    p2 = Permission.objects.create(code="docs.write", name="Write Docs")
    return [p1, p2]

class TestAgentTokenService:
    def test_create_token_success(self, test_user, test_app, permissions):
        # Give user permission
        test_user.direct_permissions.add(permissions[0])

        service = AgentTokenService()
        token = service.create(
            triggered_by=test_user,
            application=test_app,
            granted_permissions=[permissions[0]],
            agent_id="test-agent",
            circuit_breaker={"max_requests_per_minute": 100},
            dead_mans_switch={"heartbeat_required_every": 300},
            budget_limit_usd=10.0
        )

        assert token.id is not None
        assert token.token is not None
        assert token.agent_id == "test-agent"
        assert token.status == AgentToken.Status.ACTIVE
        assert token.max_requests_per_minute == 100
        assert token.heartbeat_required_every == 300
        assert token.budget_limit_usd == 10.0
        assert token.granted_permissions.filter(code="docs.read").exists()

    def test_create_token_insufficient_permissions(self, test_user, test_app, permissions):
        # User has docs.read, but agent requests docs.write
        test_user.direct_permissions.add(permissions[0])

        service = AgentTokenService()
        with pytest.raises(PermissionDenied):
            service.create(
                triggered_by=test_user,
                application=test_app,
                granted_permissions=[permissions[1]],  # User doesn't have this
                agent_id="test-agent"
            )

    def test_validate_token_success(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]])

        validated_token, error = service.validate(token.token)
        assert error is None
        assert validated_token.id == token.id
        assert validated_token.current_request_count == 1

    def test_validate_token_not_found(self):
        service = AgentTokenService()
        token, error = service.validate("invalid_token")
        assert token is None
        assert error == "NOT_FOUND"

    def test_validate_token_expired(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]], expires_in=-10)

        validated_token, error = service.validate(token.token)
        assert error == "EXPIRED"
        validated_token.refresh_from_db()
        assert validated_token.status == AgentToken.Status.EXPIRED

    def test_validate_token_missing_heartbeat(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]], dead_mans_switch={"heartbeat_required_every": 60})
        
        # Simulate time passing (e.g. 100 seconds ago)
        token.last_heartbeat_at = timezone.now() - timedelta(seconds=100)
        token.save()

        validated_token, error = service.validate(token.token)
        assert error == "HEARTBEAT_MISSING"
        validated_token.refresh_from_db()
        assert validated_token.status == AgentToken.Status.SUSPENDED

    def test_revoke_token(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]])

        revoked = service.revoke(token, revoked_by=test_user, reason="compromised")
        assert revoked.status == AgentToken.Status.REVOKED
        assert revoked.revoked_by == test_user
        assert revoked.suspended_reason == "compromised"

    def test_suspend_token(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]])

        suspended = service.suspend(token, AgentToken.SuspendedReason.ANOMALY)
        assert suspended.status == AgentToken.Status.SUSPENDED
        assert suspended.suspended_reason == AgentToken.SuspendedReason.ANOMALY

    def test_circuit_breaker(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]], circuit_breaker={'max_requests_total': 5, 'max_failed_requests': 3})

        token.current_request_count = 6
        token.save()
        ok, reason = service.check_circuit_breaker(token)
        assert not ok
        assert reason == "MAX_REQUESTS_TOTAL_EXCEEDED"
        
        token.current_request_count = 1
        token.current_failed_count = 4
        token.status = AgentToken.Status.ACTIVE
        token.save()
        ok, reason = service.check_circuit_breaker(token)
        assert not ok
        assert reason == "MAX_FAILED_REQUESTS_EXCEEDED"

    def test_pending_action_workflow(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]])

        action = service.create_pending_action(token, permission="docs.delete", endpoint="/api/docs/", payload={"id": 1})
        assert action.confirmation_token is not None
        assert action.expires_at > timezone.now()

        confirmed = service.confirm_pending_action(action.confirmation_token, confirmed_by=test_user)
        assert confirmed is not None
        assert confirmed.confirmed_at is not None

        # Trying to deny a confirmed action should fail
        denied = service.deny_pending_action(action.confirmation_token, denied_by=test_user)
        assert denied is None

    def test_airs_disabled(self, test_user, test_app, permissions):
        from unittest import mock
        with mock.patch('tenxyte.services.agent_service.auth_settings') as mock_settings:
            mock_settings.AIRS_ENABLED = False
            service = AgentTokenService()
            with pytest.raises(ValueError, match="AIRS is disabled"):
                service.create(test_user, test_app, [permissions[0]])

    def test_expires_in_capped_and_explicit_perms(self, test_user, test_app, permissions):
        from unittest import mock
        with mock.patch('tenxyte.services.agent_service.auth_settings') as mock_settings:
            mock_settings.AIRS_ENABLED = True
            mock_settings.AIRS_REQUIRE_EXPLICIT_PERMISSIONS = True
            mock_settings.AIRS_TOKEN_MAX_LIFETIME = 3600
            mock_settings.AIRS_DEFAULT_EXPIRY = 3600
            test_user.direct_permissions.add(permissions[0])
            
            service = AgentTokenService()
            with pytest.raises(PermissionDenied, match="Agent tokens must request explicit permissions."):
                service.create(test_user, test_app, [])
                
            token = service.create(test_user, test_app, [permissions[0]], expires_in=7200)
            assert (token.expires_at - token.created_at).total_seconds() <= 3605

    def test_org_permission_denied(self, test_user, test_app, permissions):
        from unittest import mock
        from tenxyte.models.base import get_organization_model
        Organization = get_organization_model()
        org = Organization.objects.create(name="Test Org", slug="test-org")
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        
        with mock.patch.object(User, 'has_org_permission', return_value=False):
            with pytest.raises(PermissionDenied, match="User does not have permission .* in the specified organization."):
                service.create(test_user, test_app, [permissions[0]], organization=org)
                
            token = AgentToken.objects.create(
                token=service._generate_token(), agent_id="test", triggered_by=test_user, 
                application=test_app, organization=org, expires_at=timezone.now() + timedelta(days=1)
            )
            token.granted_permissions.add(permissions[0])
            assert service.validate_permission(token, permissions[0].code) is False

    def test_validate_inactive_token(self, test_user, test_app):
        service = AgentTokenService()
        token = AgentToken.objects.create(
            token="inactive_token", agent_id="test", triggered_by=test_user,
            application=test_app, expires_at=timezone.now() + timedelta(days=1),
            status=AgentToken.Status.REVOKED
        )
        validated_token, error = service.validate(token.token)
        assert error == "STATUS_REVOKED"

    def test_validate_permission_no_explicit_settings(self, test_user, test_app, permissions):
        from unittest import mock
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = AgentToken.objects.create(
            token="testtoken", agent_id="test", triggered_by=test_user,
            application=test_app, expires_at=timezone.now() + timedelta(days=1)
        )
        token.granted_permissions.add(permissions[1])  # Token has perm 1 but asking for perm 0
        
        with mock.patch('tenxyte.services.agent_service.auth_settings') as mock_settings:
            mock_settings.AIRS_REQUIRE_EXPLICIT_PERMISSIONS = False
            assert service.validate_permission(token, permissions[0].code) is False

    def test_validate_permission_user_lost_perm(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(test_user, test_app, [permissions[0]])
        
        test_user.direct_permissions.remove(permissions[0])
        # Force refresh perms somehow or mock since it relies on django auth
        from unittest import mock
        with mock.patch.object(User, 'has_permission', return_value=False):
            assert service.validate_permission(token, permissions[0].code) is False

    def test_revoke_all_for_agent(self, test_user, test_app, permissions):
        from unittest import mock
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token1 = service.create(test_user, test_app, [permissions[0]], agent_id="agent-x")
        
        from tenxyte.models.base import get_organization_model
        Organization = get_organization_model()
        org = Organization.objects.create(name="Org2", slug="org2")
        with mock.patch.object(User, 'has_org_permission', return_value=True):
            token2 = service.create(test_user, test_app, [permissions[0]], agent_id="agent-x", organization=org)
        
        assert service.revoke_all_for_agent("agent-x", organization=org) == 1
        
        token2.refresh_from_db()
        assert token2.status == AgentToken.Status.REVOKED
        
        token1.refresh_from_db()
        assert token1.status == AgentToken.Status.ACTIVE

    def test_circuit_breaker_budget(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(test_user, test_app, [permissions[0]], budget_limit_usd=5.0)
        
        token.current_spend_usd = 6.0
        token.save()
        ok, reason = service.check_circuit_breaker(token)
        assert not ok
        assert reason == "BUDGET_EXCEEDED"

    def test_confirm_deny_invalid_and_expired(self, test_user, test_app):
        service = AgentTokenService()
        assert service.confirm_pending_action("fake", test_user) is None
        assert service.deny_pending_action("fake", test_user) is None
        
        token = AgentToken.objects.create(
            token="t2", agent_id="test", triggered_by=test_user, application=test_app, expires_at=timezone.now() + timedelta(days=1)
        )
        action = AgentPendingAction.objects.create(
            agent_token=token, confirmation_token="extoken", expires_at=timezone.now() - timedelta(days=1)
        )
        assert service.confirm_pending_action(action.confirmation_token, test_user) is None
        assert service.deny_pending_action(action.confirmation_token, test_user) is None

    def test_circuit_breaker_cache_rate_limit(self, test_user, test_app):
        # Missing lines: 259-260, 265-268
        from django.core.cache import cache
        service = AgentTokenService()
        token = AgentToken.objects.create(
            token="token-cache-cb", agent_id="c1", triggered_by=test_user, application=test_app,
            expires_at=timezone.now() + timedelta(days=1),
            max_requests_per_minute=2
        )
        cache_key = f"airs_rpm_{token.token}"
        
        # Test 1st request -> ok, sets cache to 1 (falls inside `current_minute_requests == 0`)
        cache.delete(cache_key)
        ok, res = service.check_circuit_breaker(token)
        assert ok is True
        assert cache.get(cache_key) == 1
        
        # Test 2nd request -> ok, incr cache
        ok, res = service.check_circuit_breaker(token)
        assert ok is True
        assert cache.get(cache_key) == 2
        
        # Test 3rd request -> fails
        ok, res = service.check_circuit_breaker(token)
        assert ok is False
        assert res == "RATE_LIMIT_EXCEEDED"
        
        # Test ValueError fallback for `incr`
        from unittest import mock
        with mock.patch('django.core.cache.cache.incr', side_effect=ValueError):
            cache.set(cache_key, 1) # reset
            token.status = AgentToken.Status.ACTIVE
            token.save()
            ok, res = service.check_circuit_breaker(token)
            assert ok is True # increments safely to 2 via fallback
            assert cache.get(cache_key) == 2

    def test_circuit_breaker_disabled(self, test_user, test_app, settings):
        settings.TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED = False
        service = AgentTokenService()
        token = AgentToken.objects.create(
            token="token-cb-disabled", agent_id="c2", triggered_by=test_user, application=test_app,
            expires_at=timezone.now() + timedelta(days=1),
            max_requests_total=1,
            current_request_count=10 # exceed
        )
        ok, res = service.check_circuit_breaker(token)
        assert ok is True # Disabled!
