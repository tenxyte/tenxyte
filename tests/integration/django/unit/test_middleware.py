import pytest
from unittest.mock import Mock, patch
from django.http import HttpResponse, JsonResponse
from tenxyte.middleware import (
    ApplicationAuthMiddleware,
    JWTAuthMiddleware,
    CORSMiddleware,
    SecurityHeadersMiddleware,
    OrganizationContextMiddleware
)
from tenxyte.models import Application, Organization, User
from tenxyte.services.jwt_service import JWTService

class DummyResponse:
    def __init__(self):
        self.status_code = 200
        self.headers = {}
    def __setitem__(self, key, value):
        self.headers[key] = value

def dummy_get_response(request):
    response = HttpResponse("OK")
    return response

@pytest.fixture
def get_response_mock():
    return Mock(return_value=HttpResponse("OK"))

@pytest.fixture
def app(db):
    # Use create_application to ensure access_key and access_secret are generated
    app, _ = Application.create_application(name="Test App")
    app.is_active = True
    app.save()
    return app

# ===========================================================================
# ApplicationAuthMiddleware
# ===========================================================================

class TestApplicationAuthMiddleware:
    def test_disabled_auth(self, rf, get_response_mock, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = False
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/some/path/')
        response = middleware(request)
        assert getattr(request, 'application', False) is None
        assert get_response_mock.called

    def test_exact_exempt_path(self, rf, get_response_mock, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = ['/exempt/']
        settings.TENXYTE_EXEMPT_PATHS = []
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/exempt/')
        response = middleware(request)
        assert get_response_mock.called

    def test_prefix_exempt_path(self, rf, get_response_mock, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = []
        settings.TENXYTE_EXEMPT_PATHS = ['/api/public/']
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/api/public/data/')
        response = middleware(request)
        assert get_response_mock.called

    def test_missing_credentials(self, rf, get_response_mock, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = []
        settings.TENXYTE_EXEMPT_PATHS = []
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/protected/')
        response = middleware(request)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 401
        import json
        assert json.loads(response.content)['code'] == 'APP_AUTH_REQUIRED'
        assert not get_response_mock.called

    @pytest.mark.django_db
    def test_invalid_credentials_wrong_secret(self, rf, get_response_mock, app, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = []
        settings.TENXYTE_EXEMPT_PATHS = []
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/protected/', HTTP_X_ACCESS_KEY=app.access_key, HTTP_X_ACCESS_SECRET='wrong')
        response = middleware(request)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 401
        import json
        assert json.loads(response.content)['code'] == 'APP_AUTH_INVALID'

    @pytest.mark.django_db
    def test_invalid_credentials_not_found(self, rf, get_response_mock, settings):
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = []
        settings.TENXYTE_EXEMPT_PATHS = []
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/protected/', HTTP_X_ACCESS_KEY='notfound', HTTP_X_ACCESS_SECRET='wrong')
        response = middleware(request)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 401
        import json
        assert json.loads(response.content)['code'] == 'APP_AUTH_INVALID'

    @pytest.mark.django_db
    def test_valid_credentials(self, rf, get_response_mock, settings):
        app, raw_secret = Application.create_application(name="Middleware Test App")
        settings.TENXYTE_APPLICATION_AUTH_ENABLED = True
        settings.TENXYTE_EXACT_EXEMPT_PATHS = []
        settings.TENXYTE_EXEMPT_PATHS = []
        middleware = ApplicationAuthMiddleware(get_response_mock)
        request = rf.get('/protected/', HTTP_X_ACCESS_KEY=app.access_key, HTTP_X_ACCESS_SECRET=raw_secret)
        response = middleware(request)
        assert getattr(request, 'application', None) == app
        assert get_response_mock.called

# ===========================================================================
# JWTAuthMiddleware
# ===========================================================================

class TestJWTAuthMiddleware:
    @pytest.mark.django_db
    def test_no_token(self, rf, get_response_mock):
        middleware = JWTAuthMiddleware(get_response_mock)
        request = rf.get('/')
        middleware(request)
        assert request.jwt_payload is None
        assert request.user_id is None
        assert get_response_mock.called

    @pytest.mark.django_db
    def test_invalid_token(self, rf, get_response_mock):
        middleware = JWTAuthMiddleware(get_response_mock)
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer invalid_token')
        middleware(request)
        assert request.jwt_payload is None
        assert request.user_id is None
        assert get_response_mock.called

    @pytest.mark.django_db
    def test_valid_token(self, rf, get_response_mock):
        user = User.objects.create(email="jwt_mid@test.com")
        app, _ = Application.objects.get_or_create(name="JWT App")
        token, _, _ = JWTService().generate_access_token(user.id, app.id)
        
        middleware = JWTAuthMiddleware(get_response_mock)
        request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        middleware(request)
        
        assert request.jwt_payload is not None
        assert request.user_id == str(user.id)
        assert get_response_mock.called


# ===========================================================================
# CORSMiddleware
# ===========================================================================

class TestCORSMiddleware:
    def test_cors_disabled(self, rf, get_response_mock, settings):
        settings.TENXYTE_CORS_ENABLED = False
        middleware = CORSMiddleware(get_response_mock)
        request = rf.get('/')
        response = middleware(request)
        assert get_response_mock.called

    def test_options_preflight_allowed_origin(self, rf, get_response_mock, settings):
        settings.TENXYTE_CORS_ENABLED = True
        settings.TENXYTE_CORS_ALLOW_ALL_ORIGINS = False
        settings.TENXYTE_CORS_ALLOWED_ORIGINS = ['https://example.com']
        settings.TENXYTE_CORS_ALLOW_CREDENTIALS = True
        settings.TENXYTE_CORS_EXPOSE_HEADERS = ['X-Custom']
        settings.TENXYTE_CORS_ALLOWED_METHODS = ['GET']
        settings.TENXYTE_CORS_ALLOWED_HEADERS = ['Content-Type']
        settings.TENXYTE_CORS_MAX_AGE = 86400

        middleware = CORSMiddleware(get_response_mock)
        request = rf.options('/', HTTP_ORIGIN='https://example.com')
        response = middleware(request)
        
        assert not get_response_mock.called
        assert response.status_code == 200
        assert response['Access-Control-Allow-Origin'] == 'https://example.com'
        assert response['Access-Control-Allow-Credentials'] == 'true'
        assert response['Access-Control-Expose-Headers'] == 'X-Custom'
        assert response['Access-Control-Allow-Methods'] == 'GET'
        assert response['Access-Control-Allow-Headers'] == 'Content-Type'
        assert response['Access-Control-Max-Age'] == '86400'

    def test_options_preflight_disallowed_origin(self, rf, get_response_mock, settings):
        settings.TENXYTE_CORS_ENABLED = True
        settings.TENXYTE_CORS_ALLOW_ALL_ORIGINS = False
        settings.TENXYTE_CORS_ALLOWED_ORIGINS = ['https://example.com']

        middleware = CORSMiddleware(get_response_mock)
        request = rf.options('/', HTTP_ORIGIN='https://bad.com')
        response = middleware(request)
        
        assert not get_response_mock.called
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' not in response

    def test_cors_allow_all_origins(self, rf, get_response_mock, settings):
        settings.TENXYTE_CORS_ENABLED = True
        settings.TENXYTE_CORS_ALLOW_ALL_ORIGINS = True
        settings.TENXYTE_CORS_ALLOW_CREDENTIALS = False
        settings.TENXYTE_CORS_EXPOSE_HEADERS = []

        middleware = CORSMiddleware(get_response_mock)
        request = rf.get('/', HTTP_ORIGIN='https://any.com')
        response = middleware(request)
        
        assert get_response_mock.called
        assert response['Access-Control-Allow-Origin'] == 'https://any.com'

# ===========================================================================
# SecurityHeadersMiddleware
# ===========================================================================

class TestSecurityHeadersMiddleware:
    def test_security_headers(self, rf, get_response_mock, settings):
        settings.TENXYTE_SECURITY_HEADERS_ENABLED = True
        settings.TENXYTE_SECURITY_HEADERS = {'X-Frame-Options': 'DENY'}
        middleware = SecurityHeadersMiddleware(get_response_mock)
        request = rf.get('/')
        response = middleware(request)
        assert get_response_mock.called
        assert response['X-Frame-Options'] == 'DENY'

    def test_security_headers_disabled(self, rf, get_response_mock, settings):
        settings.TENXYTE_SECURITY_HEADERS_ENABLED = False
        middleware = SecurityHeadersMiddleware(get_response_mock)
        request = rf.get('/')
        response = middleware(request)
        assert get_response_mock.called
        assert 'X-Frame-Options' not in response

# ===========================================================================
# OrganizationContextMiddleware
# ===========================================================================

class TestOrganizationContextMiddleware:
    def test_org_disabled(self, rf, get_response_mock, settings):
        settings.TENXYTE_ORGANIZATIONS_ENABLED = False
        middleware = OrganizationContextMiddleware(get_response_mock)
        request = rf.get('/')
        response = middleware(request)
        assert getattr(request, 'organization', False) is None
        assert get_response_mock.called

    def test_no_org_header(self, rf, get_response_mock, settings):
        settings.TENXYTE_ORGANIZATIONS_ENABLED = True
        middleware = OrganizationContextMiddleware(get_response_mock)
        request = rf.get('/')
        response = middleware(request)
        assert getattr(request, 'organization', False) is None
        assert get_response_mock.called

    @pytest.mark.django_db
    def test_valid_org_header(self, rf, get_response_mock, settings):
        settings.TENXYTE_ORGANIZATIONS_ENABLED = True
        org = Organization.objects.create(name="Test Org", slug="test-org")
        middleware = OrganizationContextMiddleware(get_response_mock)
        request = rf.get('/', HTTP_X_ORG_SLUG="test-org")
        response = middleware(request)
        assert request.organization == org
        assert get_response_mock.called

    @pytest.mark.django_db
    def test_invalid_org_header(self, rf, get_response_mock, settings):
        settings.TENXYTE_ORGANIZATIONS_ENABLED = True
        middleware = OrganizationContextMiddleware(get_response_mock)
        request = rf.get('/', HTTP_X_ORG_SLUG="non-existent")
        response = middleware(request)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 404
        import json
        assert json.loads(response.content)['code'] == 'ORG_NOT_FOUND'
        assert not get_response_mock.called

    @pytest.mark.django_db
    def test_org_error(self, rf, get_response_mock, settings):
        settings.TENXYTE_ORGANIZATIONS_ENABLED = True
        middleware = OrganizationContextMiddleware(get_response_mock)
        request = rf.get('/', HTTP_X_ORG_SLUG="test-org")
        
        with patch('tenxyte.models.Organization.objects.get', side_effect=Exception('Test Error')):
            response = middleware(request)
            assert isinstance(response, JsonResponse)
            assert response.status_code == 500
            import json
            assert json.loads(response.content)['code'] == 'ORG_ERROR'
            assert not get_response_mock.called
