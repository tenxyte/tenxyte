"""
Tests unitaires pour le middleware ApplicationAuthMiddleware.

Vérifie que les settings TENXYTE_EXEMPT_PATHS et TENXYTE_EXACT_EXEMPT_PATHS
sont correctement appliqués.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, override_settings

from tenxyte.middleware import ApplicationAuthMiddleware


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def get_response():
    """Simule une vue qui retourne 200."""
    def _get_response(request):
        return HttpResponse("OK", status=200)
    return _get_response


@pytest.fixture
def middleware(get_response):
    return ApplicationAuthMiddleware(get_response)


class TestExemptPathsPrefixMatch:
    """Test que TENXYTE_EXEMPT_PATHS (prefix match) est appliqué."""

    def test_default_admin_path_is_exempt(self, middleware, request_factory):
        """Le chemin /admin/ est exempté par défaut."""
        request = request_factory.get('/admin/')
        response = middleware(request)
        assert response.status_code == 200

    def test_default_admin_subpath_is_exempt(self, middleware, request_factory):
        """Les sous-chemins de /admin/ sont exemptés par défaut (prefix match)."""
        request = request_factory.get('/admin/login/')
        response = middleware(request)
        assert response.status_code == 200

    def test_default_health_path_is_exempt(self, middleware, request_factory):
        """Le chemin /api/v1/health/ est exempté par défaut."""
        request = request_factory.get('/api/v1/health/')
        response = middleware(request)
        assert response.status_code == 200

    def test_default_docs_path_is_exempt(self, middleware, request_factory):
        """Le chemin /api/v1/docs/ est exempté par défaut."""
        request = request_factory.get('/api/v1/docs/')
        response = middleware(request)
        assert response.status_code == 200

    def test_non_exempt_path_requires_auth(self, middleware, request_factory):
        """Un chemin non exempté requiert l'authentification application."""
        request = request_factory.get('/api/v1/users/')
        response = middleware(request)
        assert response.status_code == 401

    @override_settings(TENXYTE_EXEMPT_PATHS=[
        '/admin/',
        '/api/v1/health/',
        '/api/v1/docs/',
        '/api/v1/public/',
    ])
    def test_custom_exempt_paths_are_applied(self, get_response, request_factory):
        """Les chemins personnalisés dans TENXYTE_EXEMPT_PATHS sont appliqués."""
        mw = ApplicationAuthMiddleware(get_response)

        # /api/v1/public/ doit être exempté
        request = request_factory.get('/api/v1/public/')
        response = mw(request)
        assert response.status_code == 200

        # /api/v1/public/some-resource/ doit aussi être exempté (prefix)
        request = request_factory.get('/api/v1/public/some-resource/')
        response = mw(request)
        assert response.status_code == 200

    @override_settings(TENXYTE_EXEMPT_PATHS=[
        '/admin/',
        '/api/v1/health/',
        '/api/v1/docs/',
        '/api/v1/public/',
    ])
    def test_custom_exempt_paths_non_listed_still_requires_auth(self, get_response, request_factory):
        """Un chemin non listé dans les paths personnalisés requiert toujours l'auth."""
        mw = ApplicationAuthMiddleware(get_response)

        request = request_factory.get('/api/v1/users/')
        response = mw(request)
        assert response.status_code == 401

    @override_settings(TENXYTE_EXEMPT_PATHS=['/custom/'])
    def test_overriding_removes_defaults(self, get_response, request_factory):
        """Surcharger TENXYTE_EXEMPT_PATHS remplace les défauts, pas les complète."""
        mw = ApplicationAuthMiddleware(get_response)

        # /custom/ est exempté
        request = request_factory.get('/custom/path/')
        response = mw(request)
        assert response.status_code == 200

        # /admin/ N'est plus exempté car les défauts sont remplacés
        request = request_factory.get('/admin/')
        response = mw(request)
        assert response.status_code == 401


class TestExactExemptPaths:
    """Test que TENXYTE_EXACT_EXEMPT_PATHS (exact match) est appliqué."""

    def test_default_api_v1_root_is_exempt(self, middleware, request_factory):
        """Le chemin exact /api/v1/ est exempté par défaut."""
        request = request_factory.get('/api/v1/')
        response = middleware(request)
        assert response.status_code == 200

    def test_exact_match_does_not_match_subpaths(self, middleware, request_factory):
        """Le match exact ne s'applique PAS aux sous-chemins."""
        request = request_factory.get('/api/v1/something/')
        response = middleware(request)
        assert response.status_code == 401

    @override_settings(TENXYTE_EXACT_EXEMPT_PATHS=['/api/v1/', '/'])
    def test_custom_exact_exempt_paths_are_applied(self, get_response, request_factory):
        """Les chemins exacts personnalisés dans TENXYTE_EXACT_EXEMPT_PATHS sont appliqués."""
        mw = ApplicationAuthMiddleware(get_response)

        # / doit être exempté
        request = request_factory.get('/')
        response = mw(request)
        assert response.status_code == 200

        # /api/v1/ doit aussi être exempté
        request = request_factory.get('/api/v1/')
        response = mw(request)
        assert response.status_code == 200

    @override_settings(TENXYTE_EXACT_EXEMPT_PATHS=['/api/v1/', '/'])
    def test_custom_exact_exempt_subpath_not_exempt(self, get_response, request_factory):
        """Les sous-chemins ne sont PAS exemptés par match exact."""
        mw = ApplicationAuthMiddleware(get_response)

        request = request_factory.get('/api/v1/users/')
        response = mw(request)
        assert response.status_code == 401

    @override_settings(TENXYTE_EXACT_EXEMPT_PATHS=['/'])
    def test_overriding_exact_removes_defaults(self, get_response, request_factory):
        """Surcharger TENXYTE_EXACT_EXEMPT_PATHS remplace les défauts."""
        mw = ApplicationAuthMiddleware(get_response)

        # / est exempté
        request = request_factory.get('/')
        response = mw(request)
        assert response.status_code == 200

        # /api/v1/ N'est plus exempté (défaut remplacé)
        request = request_factory.get('/api/v1/')
        response = mw(request)
        assert response.status_code == 401


class TestFullUserSettings:
    """
    Test de la configuration complète fournie par l'utilisateur:

    TENXYTE_EXEMPT_PATHS = [
        '/admin/',
        '/api/v1/health/',
        '/api/v1/docs/',
        '/api/v1/public/',
    ]

    TENXYTE_EXACT_EXEMPT_PATHS = [
        '/api/v1/',
        '/',
    ]
    """

    @override_settings(
        TENXYTE_EXEMPT_PATHS=[
            '/admin/',
            '/api/v1/health/',
            '/api/v1/docs/',
            '/api/v1/public/',
        ],
        TENXYTE_EXACT_EXEMPT_PATHS=[
            '/api/v1/',
            '/',
        ],
    )
    def test_all_prefix_paths_exempt(self, get_response, request_factory):
        """Tous les chemins préfixés sont exemptés."""
        mw = ApplicationAuthMiddleware(get_response)

        exempt_paths = [
            '/admin/',
            '/admin/login/',
            '/admin/dashboard/stats/',
            '/api/v1/health/',
            '/api/v1/health/status/',
            '/api/v1/docs/',
            '/api/v1/docs/swagger/',
            '/api/v1/public/',
            '/api/v1/public/terms/',
        ]
        for path in exempt_paths:
            request = request_factory.get(path)
            response = mw(request)
            assert response.status_code == 200, f"Path {path} should be exempt but got {response.status_code}"

    @override_settings(
        TENXYTE_EXEMPT_PATHS=[
            '/admin/',
            '/api/v1/health/',
            '/api/v1/docs/',
            '/api/v1/public/',
        ],
        TENXYTE_EXACT_EXEMPT_PATHS=[
            '/api/v1/',
            '/',
        ],
    )
    def test_all_exact_paths_exempt(self, get_response, request_factory):
        """Tous les chemins exacts sont exemptés."""
        mw = ApplicationAuthMiddleware(get_response)

        exact_exempt = ['/', '/api/v1/']
        for path in exact_exempt:
            request = request_factory.get(path)
            response = mw(request)
            assert response.status_code == 200, f"Path {path} should be exempt but got {response.status_code}"

    @override_settings(
        TENXYTE_EXEMPT_PATHS=[
            '/admin/',
            '/api/v1/health/',
            '/api/v1/docs/',
            '/api/v1/public/',
        ],
        TENXYTE_EXACT_EXEMPT_PATHS=[
            '/api/v1/',
            '/',
        ],
    )
    def test_protected_paths_require_auth(self, get_response, request_factory):
        """Les chemins non exemptés requièrent l'authentification."""
        mw = ApplicationAuthMiddleware(get_response)

        protected_paths = [
            '/api/v1/users/',
            '/api/v1/auth/login/',
            '/api/v1/auth/register/',
            '/api/v1/private/data/',
            '/api/v2/something/',
            '/other/',
        ]
        for path in protected_paths:
            request = request_factory.get(path)
            response = mw(request)
            assert response.status_code == 401, f"Path {path} should require auth but got {response.status_code}"

    @override_settings(
        TENXYTE_EXEMPT_PATHS=[
            '/admin/',
            '/api/v1/health/',
            '/api/v1/docs/',
            '/api/v1/public/',
        ],
        TENXYTE_EXACT_EXEMPT_PATHS=[
            '/api/v1/',
            '/',
        ],
    )
    def test_error_response_format(self, get_response, request_factory):
        """Vérifie le format de la réponse d'erreur 401."""
        import json
        mw = ApplicationAuthMiddleware(get_response)

        request = request_factory.get('/api/v1/users/')
        response = mw(request)
        assert response.status_code == 401
        data = json.loads(response.content)
        assert data['code'] == 'APP_AUTH_REQUIRED'
        assert 'error' in data


class TestApplicationAuthDisabled:
    """Test que TENXYTE_APPLICATION_AUTH_ENABLED=False désactive tout."""

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_disabled_auth_passes_all_requests(self, get_response, request_factory):
        """Quand l'auth application est désactivée, toutes les requêtes passent."""
        mw = ApplicationAuthMiddleware(get_response)

        paths = ['/api/v1/users/', '/admin/', '/anything/', '/']
        for path in paths:
            request = request_factory.get(path)
            response = mw(request)
            assert response.status_code == 200, f"Path {path} should pass when auth disabled"

    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_disabled_auth_sets_application_none(self, get_response, request_factory):
        """Quand l'auth est désactivée, request.application est None."""
        captured = {}

        def capturing_response(request):
            captured['application'] = getattr(request, 'application', 'NOT_SET')
            return HttpResponse("OK")

        mw = ApplicationAuthMiddleware(capturing_response)
        request = request_factory.get('/api/v1/users/')
        mw(request)

        assert captured['application'] is None
