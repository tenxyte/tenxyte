"""
Spec-fidelity tests for spec/airs/AIRS-1.0.md (spec z_aud_2, task 1.3).

These tests assert that specific normative values cited by the AIRS-1.0 specification
(clause IDs in comments) are actually present in Tenxyte's code, so that a future change
to the implementation which silently breaks the spec's factual claims fails CI here
rather than only being caught by the (HTTP, black-box) Conformance_Suite.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from tenxyte.decorators import require_agent_clearance
from tenxyte.models.agent import AgentPendingAction, AgentToken
from tenxyte.models.base import get_application_model, get_permission_model, get_user_model
from tenxyte.services.agent_service import AgentTokenService

pytestmark = pytest.mark.django_db

User = get_user_model()
Application = get_application_model()
Permission = get_permission_model()


class TestTokenStatusVocabulary:
    """[AIRS-CORE-5]: exactly four statuses."""

    def test_exactly_four_statuses(self):
        assert {c[0] for c in AgentToken.Status.choices} == {"ACTIVE", "SUSPENDED", "REVOKED", "EXPIRED"}


class TestSuspensionReasonVocabulary:
    """[AIRS-CORE-7]: exactly five suspension reasons."""

    def test_exactly_five_suspension_reasons(self):
        assert {c[0] for c in AgentToken.SuspendedReason.choices} == {
            "RATE_LIMIT",
            "ANOMALY",
            "MANUAL",
            "HEARTBEAT_MISSING",
            "BUDGET_EXCEEDED",
        }


class TestRawTokenHandling:
    """[AIRS-CORE-12]: only a hash is persisted; the raw value is a non-persistent attribute."""

    def test_stored_token_is_a_hash_not_the_raw_value(self):
        service = AgentTokenService()
        user = User.objects.create_user(email="fidelity-core12@example.com", password="password123")
        app = Application.create_application(name="Fidelity App")[0]
        perm = Permission.objects.create(code="fidelity.core12", name="Fidelity Core12")
        user.direct_permissions.add(perm)

        token = service.create(
            triggered_by=user, application=app, granted_permissions=[perm], agent_id="fidelity-agent"
        )

        assert token.raw_token is not None
        assert token.token != token.raw_token
        assert token.token == AgentToken._hash_token(token.raw_token)

    def test_raw_token_not_recoverable_after_reload(self):
        service = AgentTokenService()
        user = User.objects.create_user(email="fidelity-core12b@example.com", password="password123")
        app = Application.create_application(name="Fidelity App 2")[0]
        perm = Permission.objects.create(code="fidelity.core12b", name="Fidelity Core12b")
        user.direct_permissions.add(perm)

        token = service.create(
            triggered_by=user, application=app, granted_permissions=[perm], agent_id="fidelity-agent-2"
        )
        reloaded = AgentToken.objects.get(pk=token.pk)

        assert reloaded.raw_token is None


class TestPendingActionDefaultExpiry:
    """[AIRS-HITL-4]: default Pending Action lifetime is 10 minutes."""

    def test_default_expiry_is_ten_minutes(self):
        service = AgentTokenService()
        user = User.objects.create_user(email="fidelity-hitl4@example.com", password="password123")
        app = Application.create_application(name="Fidelity HITL App")[0]
        perm = Permission.objects.create(code="fidelity.hitl4", name="Fidelity HITL4")
        user.direct_permissions.add(perm)
        token = service.create(triggered_by=user, application=app, granted_permissions=[perm], agent_id="hitl-agent")

        before = timezone.now()
        action = service.create_pending_action(agent_token=token, permission="docs.write", endpoint="/x", payload={})
        after = timezone.now()

        assert action.expires_at >= before + timedelta(minutes=10)
        assert action.expires_at <= after + timedelta(minutes=10)


class TestAgentBearerScheme:
    """[AIRS-CORE-11]/[AIRS-CORE-13]: the `AgentBearer` scheme name is a fixed literal in the code."""

    def test_agent_bearer_prefix_used_by_middleware(self):
        import inspect

        from tenxyte import middleware

        source = inspect.getsource(middleware.AgentTokenMiddleware)
        assert '"AgentBearer ' in source or "'AgentBearer '" in source


class TestHitl202Shape:
    """[AIRS-HITL-3]: the 202 response body shape for a pending confirmation."""

    def test_hitl_response_contains_required_fields(self, rf):
        user = User.objects.create_user(email="fidelity-hitl3@example.com", password="password123")
        app = Application.create_application(name="Fidelity HITL Shape App")[0]
        perm = Permission.objects.create(code="fidelity.hitl3", name="Fidelity HITL3")
        user.direct_permissions.add(perm)

        service = AgentTokenService()
        token = service.create(
            triggered_by=user,
            application=app,
            granted_permissions=[perm],
            agent_id="hitl-shape-agent",
        )

        @require_agent_clearance(permission_code="fidelity.hitl3", human_in_the_loop_required=True)
        def view(request):
            from django.http import JsonResponse

            return JsonResponse({"executed": True})

        request = rf.post("/fidelity/hitl-shape/", data=b"{}", content_type="application/json")
        request.agent_token = token
        request.user = user

        response = view(request)

        assert response.status_code == 202
        import json

        body = json.loads(response.content)
        assert body["status"] == "pending_confirmation"
        assert "confirmation_token" in body
        assert "expires_at" in body

        # The Pending Action created for this request must exist and be resolvable by that token.
        assert AgentPendingAction.objects.filter(confirmation_token=body["confirmation_token"]).exists()
