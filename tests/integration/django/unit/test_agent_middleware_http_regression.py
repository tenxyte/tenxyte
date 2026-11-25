"""
Regression test for a real, end-to-end HTTP crash bug in AgentTokenMiddleware, discovered while
building the spec z_aud_2 AIRS Conformance Suite (spec/airs/conformance/).

Every existing test of AgentTokenMiddleware (test_agent_middleware.py) instantiates the
middleware directly against a stub `get_response` callable that never touches `request.user` the
way a real DRF view does — so it never exercised the actual production request path. Through a
real HTTP round trip, DRF's `APIView.dispatch()` unconditionally calls `perform_authentication()`,
which accesses `request.user`; since `JWTAuthentication` doesn't recognize the `AgentBearer`
scheme, DRF resets `request.user` to `AnonymousUser` (and, via its `Request.user` setter, writes
that back onto the same underlying `HttpRequest` that `AgentTokenMiddleware` had already set to
the Delegating User). By the time `AgentTokenMiddleware`'s post-response audit-logging code ran,
`request.user` was `AnonymousUser`, and `AuditLog.log(user=request.user, ...)` raised `ValueError`
(assigning `AnonymousUser` to a `User` foreign key) — turning every successful agent-authenticated
mutating request (heartbeat, report-usage, or any `@require_agent_clearance`-protected endpoint)
into a 500, with `AUDIT_LOGGING_ENABLED=True` (the default), even though the underlying action had
already silently succeeded.

Fixed by reading `agent_token.triggered_by` (resolved earlier in the same middleware call, never
touched by DRF) instead of `request.user` for the audit log's `user`/`on_behalf_of` fields.
"""

import pytest
from django.test import Client, override_settings

from tenxyte.models.base import get_application_model, get_permission_model, get_user_model
from tenxyte.services.agent_service import AgentTokenService

pytestmark = pytest.mark.django_db

User = get_user_model()
Application = get_application_model()
Permission = get_permission_model()

# The full middleware stack a real AIRS-enabled deployment runs, including AgentTokenMiddleware —
# which the shared test settings omit precisely because it lets unit tests instantiate the
# middleware class directly (see test_agent_middleware.py). This is what actually exposed the bug.
_FULL_AIRS_MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "tenxyte.middleware.RequestIDMiddleware",
    "tenxyte.middleware.ApplicationAuthMiddleware",
    "tenxyte.middleware.AgentTokenMiddleware",
]


class TestAgentTokenMiddlewareHttpRegression:
    @override_settings(MIDDLEWARE=_FULL_AIRS_MIDDLEWARE, TENXYTE_AUDIT_LOGGING_ENABLED=True)
    def test_heartbeat_via_real_http_stack_does_not_500(self):
        user = User.objects.create_user(email="airs-http-regression@example.com", password="password123")
        app = Application.create_application(name="AIRS HTTP Regression App")[0]
        perm = Permission.objects.create(code="airs.http.regression", name="AIRS HTTP Regression")
        user.direct_permissions.add(perm)

        token = AgentTokenService().create(
            triggered_by=user, application=app, granted_permissions=[perm], agent_id="http-regression-agent"
        )

        client = Client()
        response = client.post(
            f"/api/v1/auth/ai/tokens/{token.id}/heartbeat/",
            HTTP_AUTHORIZATION=f"AgentBearer {token.raw_token}",
        )

        assert response.status_code == 200, response.content

    @override_settings(MIDDLEWARE=_FULL_AIRS_MIDDLEWARE, TENXYTE_AUDIT_LOGGING_ENABLED=True)
    def test_report_usage_via_real_http_stack_does_not_500(self):
        user = User.objects.create_user(email="airs-http-regression-2@example.com", password="password123")
        app = Application.create_application(name="AIRS HTTP Regression App 2")[0]
        perm = Permission.objects.create(code="airs.http.regression.2", name="AIRS HTTP Regression 2")
        user.direct_permissions.add(perm)

        token = AgentTokenService().create(
            triggered_by=user, application=app, granted_permissions=[perm], agent_id="http-regression-agent-2"
        )

        client = Client()
        response = client.post(
            f"/api/v1/auth/ai/tokens/{token.id}/report-usage/",
            data={"cost_usd": 0.01, "prompt_tokens": 10, "completion_tokens": 5},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"AgentBearer {token.raw_token}",
        )

        assert response.status_code == 200, response.content

    @override_settings(MIDDLEWARE=_FULL_AIRS_MIDDLEWARE, TENXYTE_AUDIT_LOGGING_ENABLED=True)
    def test_audit_log_records_the_real_delegating_user(self):
        """The fix's whole point: the AuditLog entry must attribute the real human, not anonymous."""
        from tenxyte.models.security import AuditLog

        user = User.objects.create_user(email="airs-http-regression-3@example.com", password="password123")
        app = Application.create_application(name="AIRS HTTP Regression App 3")[0]
        perm = Permission.objects.create(code="airs.http.regression.3", name="AIRS HTTP Regression 3")
        user.direct_permissions.add(perm)

        token = AgentTokenService().create(
            triggered_by=user, application=app, granted_permissions=[perm], agent_id="http-regression-agent-3"
        )

        client = Client()
        response = client.post(
            f"/api/v1/auth/ai/tokens/{token.id}/heartbeat/",
            HTTP_AUTHORIZATION=f"AgentBearer {token.raw_token}",
        )
        assert response.status_code == 200

        entry = AuditLog.objects.filter(agent_token=token).order_by("-created_at").first()
        assert entry is not None
        assert entry.user_id == user.id
        assert entry.on_behalf_of_id == user.id
