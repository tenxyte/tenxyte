import pytest
import json
from unittest.mock import patch, MagicMock
from django.test import RequestFactory, override_settings
from django.http import JsonResponse, HttpResponse

from tenxyte.middleware import (
    ApplicationAuthMiddleware,
    JWTAuthMiddleware,
    OrganizationContextMiddleware,
    AgentTokenMiddleware,
    PIIRedactionMiddleware
)

pytestmark = pytest.mark.django_db

@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def get_response_ok():
    def _get_response(request):
        return HttpResponse("OK", status=200)
    return _get_response

@pytest.fixture
def get_response_json():
    def _get_response(request):
        return JsonResponse({"email": "test@example.com", "other": "data"}, status=200)
    return _get_response

class TestApplicationAuthMiddlewareExt:
    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_application_auth_disabled(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.application is None

    @override_settings(
        TENXYTE_APPLICATION_AUTH_ENABLED=True,
        TENXYTE_EXACT_EXEMPT_PATHS=["/api/v1/health/"]
    )
    def test_exempt_exact_path(self, rf, get_response_ok):
        request = rf.get("/api/v1/health/")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.application is None

    @override_settings(
        TENXYTE_APPLICATION_AUTH_ENABLED=True,
        TENXYTE_EXACT_EXEMPT_PATHS=[],
        TENXYTE_EXEMPT_PATHS=["/api/v1/public/"]
    )
    def test_exempt_prefix_path(self, rf, get_response_ok):
        request = rf.get("/api/v1/public/docs/")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.application is None

class TestJWTAuthMiddlewareExt:
    def test_valid_token(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_AUTHORIZATION="Bearer valid_token")
        middleware = JWTAuthMiddleware(get_response_ok)
        mock_payload = {"user_id": "user123"}
        with patch.object(middleware.jwt_service, "decode_token", return_value=mock_payload):
            response = middleware(request)
            assert response.status_code == 200
            assert request.jwt_payload == mock_payload
            assert request.user_id == "user123"

    def test_invalid_token(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_AUTHORIZATION="Bearer invalid_token")
        middleware = JWTAuthMiddleware(get_response_ok)
        with patch.object(middleware.jwt_service, "decode_token", return_value=None):
            response = middleware(request)
            assert response.status_code == 200
            assert request.jwt_payload is None
            assert request.user_id is None

    def test_no_bearer(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_AUTHORIZATION="Basic base64")
        middleware = JWTAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.jwt_payload is None
        assert request.user_id is None

    def test_no_authorization_header(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/")
        middleware = JWTAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.jwt_payload is None
        assert request.user_id is None

class TestOrganizationContextMiddlewareExt:
    @override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False)
    def test_organizations_disabled(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/")
        middleware = OrganizationContextMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.organization is None

    @override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True)
    def test_org_does_not_exist(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ORG_SLUG="unknown-org")
        middleware = OrganizationContextMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 404
        data = json.loads(response.content)
        assert data["code"] == "ORG_NOT_FOUND"

    @override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True)
    def test_exception_loading_org(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ORG_SLUG="error-org")
        middleware = OrganizationContextMiddleware(get_response_ok)
        with patch("tenxyte.models.get_organization_model") as mock_get_org:
            from tenxyte.models.organization import Organization
            mock_org_model = MagicMock()
            mock_org_model.DoesNotExist = Organization.DoesNotExist
            mock_org_model.objects.get.side_effect = Exception("DB error")
            mock_get_org.return_value = mock_org_model
            response = middleware(request)
            assert response.status_code == 500
            data = json.loads(response.content)
            assert data["code"] == "ORG_ERROR"

class TestAgentTokenMiddlewareExt:
    @override_settings(TENXYTE_AIRS_ENABLED=False)
    def test_airs_disabled(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_AUTHORIZATION="AgentBearer my_token")
        middleware = AgentTokenMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data["code"] == "AIRS_DISABLED"
            
    @override_settings(TENXYTE_AIRS_ENABLED=True, TENXYTE_AUDIT_LOGGING_ENABLED=True)
    def test_invalid_prompt_trace_id(self, rf, get_response_ok):
        request = rf.post("/api/v1/test/", HTTP_AUTHORIZATION="AgentBearer my_token", HTTP_X_PROMPT_TRACE_ID="invalid trace id #$")
        middleware = AgentTokenMiddleware(get_response_ok)
        with patch("tenxyte.services.agent_service.AgentTokenService.validate") as mock_validate, \
             patch("tenxyte.services.agent_service.AgentTokenService.check_circuit_breaker", return_value=(True, None)), \
             patch("tenxyte.models.security.AuditLog.log") as mock_log:
            mock_agent_token = MagicMock()
            mock_agent_token.triggered_by = MagicMock()
            mock_agent_token.triggered_by_id = 1
            mock_agent_token.agent_id = "agent-1"
            mock_validate.return_value = (mock_agent_token, None)
            
            response = middleware(request)
            assert response.status_code == 200
            mock_log.assert_called_once()
            kwargs = mock_log.call_args.kwargs
            assert kwargs["prompt_trace_id"] is None

class TestPIIRedactionMiddlewareExt:
    @override_settings(TENXYTE_AIRS_REDACT_PII=True)
    def test_pii_redaction_exception(self, rf):
        def _get_response_bad_json(request):
            response = HttpResponse("{bad json", status=200)
            response["Content-Type"] = "application/json"
            return response
            
        request = rf.get("/api/v1/test/")
        request.agent_token = MagicMock()
        middleware = PIIRedactionMiddleware(_get_response_bad_json)
        response = middleware(request)
        assert response.status_code == 200
        assert response.content == b"{bad json"

class TestRequestIDMiddlewareExt:
    def test_request_id_missing(self, rf, get_response_ok):
        from tenxyte.middleware import RequestIDMiddleware
        request = rf.get("/api/v1/test/")
        middleware = RequestIDMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.request_id is not None
        assert response["X-Request-ID"] == request.request_id

    def test_request_id_present(self, rf, get_response_ok):
        from tenxyte.middleware import RequestIDMiddleware
        request = rf.get("/api/v1/test/", HTTP_X_REQUEST_ID="my-custom-id-123")
        middleware = RequestIDMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 200
        assert request.request_id == "my-custom-id-123"
        assert response["X-Request-ID"] == "my-custom-id-123"

class TestApplicationAuthMiddlewareFull:
    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=True, TENXYTE_EXEMPT_PATHS=[], TENXYTE_EXACT_EXEMPT_PATHS=[])
    def test_missing_credentials(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        response = middleware(request)
        assert response.status_code == 401
        data = json.loads(response.content)
        assert data["code"] == "APP_AUTH_REQUIRED"

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=True, TENXYTE_EXEMPT_PATHS=[], TENXYTE_EXACT_EXEMPT_PATHS=[])
    def test_application_does_not_exist(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ACCESS_KEY="missing", HTTP_X_ACCESS_SECRET="secret")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        with patch("tenxyte.models.Application.objects.get") as mock_get:
            from tenxyte.models.application import Application
            mock_get.side_effect = Application.DoesNotExist
            response = middleware(request)
            assert response.status_code == 401
            data = json.loads(response.content)
            assert data["code"] == "APP_AUTH_INVALID"

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=True, TENXYTE_EXEMPT_PATHS=[], TENXYTE_EXACT_EXEMPT_PATHS=[])
    def test_invalid_secret(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ACCESS_KEY="valid-key", HTTP_X_ACCESS_SECRET="wrong-secret")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        with patch("tenxyte.models.Application.objects.get") as mock_get, \
             patch("django.core.cache.cache.get", return_value=None):
            mock_app = MagicMock()
            mock_app.verify_secret.return_value = False
            mock_get.return_value = mock_app
            response = middleware(request)
            assert response.status_code == 401
            data = json.loads(response.content)
            assert data["code"] == "APP_AUTH_INVALID"

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=True, TENXYTE_EXEMPT_PATHS=[], TENXYTE_EXACT_EXEMPT_PATHS=[])
    def test_valid_secret(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ACCESS_KEY="valid-key", HTTP_X_ACCESS_SECRET="valid-secret")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        with patch("tenxyte.models.Application.objects.get") as mock_get, \
             patch("django.core.cache.cache.get", return_value=None), \
             patch("django.core.cache.cache.set") as mock_set:
            mock_app = MagicMock()
            mock_app.id = 123
            mock_app.verify_secret.return_value = True
            mock_get.return_value = mock_app
            response = middleware(request)
            assert response.status_code == 200
            assert request.application == mock_app
            mock_set.assert_called_once()

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=True, TENXYTE_EXEMPT_PATHS=[], TENXYTE_EXACT_EXEMPT_PATHS=[])
    def test_cached_secret(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ACCESS_KEY="valid-key", HTTP_X_ACCESS_SECRET="valid-secret")
        middleware = ApplicationAuthMiddleware(get_response_ok)
        with patch("tenxyte.models.Application.objects.get") as mock_get, \
             patch("django.core.cache.cache.get", return_value=True):
            mock_app = MagicMock()
            mock_app.id = 123
            mock_app.verify_secret.return_value = True 
            mock_get.return_value = mock_app
            response = middleware(request)
            assert response.status_code == 200
            assert request.application == mock_app
            mock_app.verify_secret.assert_not_called()

class TestOrganizationContextMiddlewareFull:
    @override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True)
    def test_valid_organization(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/", HTTP_X_ORG_SLUG="valid-org")
        middleware = OrganizationContextMiddleware(get_response_ok)
        with patch("tenxyte.models.get_organization_model") as mock_get_org, \
             patch("tenxyte.tenant_context.set_current_organization") as mock_set_org:
            mock_org_model = MagicMock()
            mock_org = MagicMock()
            mock_org_model.objects.get.return_value = mock_org
            mock_get_org.return_value = mock_org_model
            response = middleware(request)
            assert response.status_code == 200
            assert request.organization == mock_org
            mock_set_org.assert_any_call(mock_org)
            mock_set_org.assert_any_call(None)

    @override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True)
    def test_no_organization_header(self, rf, get_response_ok):
        request = rf.get("/api/v1/test/")
        middleware = OrganizationContextMiddleware(get_response_ok)
        with patch("tenxyte.tenant_context.set_current_organization") as mock_set_org:
            response = middleware(request)
            assert response.status_code == 200
            assert request.organization is None
            mock_set_org.assert_called_with(None)

class TestPIIRedactionMiddlewareFull:
    def test_no_agent_token(self, rf, get_response_json):
        request = rf.get("/api/v1/test/")
        middleware = PIIRedactionMiddleware(get_response_json)
        response = middleware(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["email"] == "test@example.com"

    @override_settings(TENXYTE_AIRS_REDACT_PII=False)
    def test_airs_redact_disabled(self, rf, get_response_json):
        request = rf.get("/api/v1/test/")
        request.agent_token = MagicMock()
        middleware = PIIRedactionMiddleware(get_response_json)
        response = middleware(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["email"] == "test@example.com"

    @override_settings(TENXYTE_AIRS_REDACT_PII=True)
    def test_valid_redaction(self, rf):
        def _get_resp(request):
            data = {
                "safe_field": "hello",
                "email": "secret@example.com",
                "nested_list": [
                    {"phone": "123-456", "other": "ok"}
                ],
                "nested_dict": {
                    "credit_card": "4111",
                    "safe": "hi"
                }
            }
            return JsonResponse(data, status=200)

        request = rf.get("/api/v1/test/")
        request.agent_token = MagicMock()
        middleware = PIIRedactionMiddleware(_get_resp)
        response = middleware(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["safe_field"] == "hello"
        assert data["email"] == "***REDACTED***"
        assert data["nested_list"][0]["phone"] == "***REDACTED***"
        assert data["nested_list"][0]["other"] == "ok"
        assert data["nested_dict"]["credit_card"] == "***REDACTED***"
        assert data["nested_dict"]["safe"] == "hi"
