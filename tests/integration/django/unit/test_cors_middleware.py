"""
Tests unitaires pour CORSMiddleware et SecurityHeadersMiddleware.

Vérifie que les headers CORS et de sécurité sont correctement ajoutés
selon la configuration dans settings.py.
"""

from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest  # noqa: E402
from django.http import HttpResponse  # noqa: E402
from django.test import RequestFactory, override_settings  # noqa: E402

from tenxyte.middleware import CORSMiddleware, SecurityHeadersMiddleware  # noqa: E402


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def get_response():
    """Simule une vue qui retourne 200."""
    def _get_response(request):
        return HttpResponse("OK", status=200)
    return _get_response


# =============================================================================
# CORSMiddleware
# =============================================================================

class TestCORSMiddlewareDisabled:
    """Tests quand CORS est désactivé (défaut)."""

    def test_cors_disabled_by_default(self, get_response, request_factory):
        """Par défaut, CORS est désactivé et aucun header n'est ajouté."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://example.com')
        response = mw(request)

        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(TENXYTE_CORS_ENABLED=False)
    def test_cors_explicitly_disabled(self, get_response, request_factory):
        """CORS explicitement désactivé n'ajoute aucun header."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://example.com')
        response = mw(request)

        assert 'Access-Control-Allow-Origin' not in response


class TestCORSMiddlewareEnabled:
    """Tests quand CORS est activé."""

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://example.com'],
    )
    def test_allowed_origin_gets_cors_headers(self, get_response, request_factory):
        """Une origine autorisée reçoit les headers CORS."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://example.com')
        response = mw(request)

        assert response['Access-Control-Allow-Origin'] == 'https://example.com'
        assert response['Vary'] == 'Origin'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://example.com'],
    )
    def test_disallowed_origin_no_cors_headers(self, get_response, request_factory):
        """Une origine non autorisée ne reçoit pas de headers CORS."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://evil.com')
        response = mw(request)

        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://example.com'],
    )
    def test_no_origin_header_no_cors(self, get_response, request_factory):
        """Sans header Origin, aucun header CORS n'est ajouté."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/')
        response = mw(request)

        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOW_ALL_ORIGINS=True,
    )
    def test_allow_all_origins(self, get_response, request_factory):
        """CORS_ALLOW_ALL_ORIGINS=True accepte toute origine."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://anything.com')
        response = mw(request)

        assert response['Access-Control-Allow-Origin'] == 'https://anything.com'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app.com'],
        TENXYTE_CORS_ALLOW_CREDENTIALS=True,
    )
    def test_credentials_header(self, get_response, request_factory):
        """Access-Control-Allow-Credentials est ajouté quand activé."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app.com')
        response = mw(request)

        assert response['Access-Control-Allow-Credentials'] == 'true'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app.com'],
        TENXYTE_CORS_ALLOW_CREDENTIALS=False,
    )
    def test_no_credentials_header_when_disabled(self, get_response, request_factory):
        """Access-Control-Allow-Credentials absent quand désactivé."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app.com')
        response = mw(request)

        assert 'Access-Control-Allow-Credentials' not in response


class TestCORSPreflight:
    """Tests pour les requêtes preflight (OPTIONS)."""

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://frontend.com'],
        TENXYTE_CORS_ALLOWED_METHODS=['GET', 'POST', 'DELETE'],
        TENXYTE_CORS_ALLOWED_HEADERS=['Content-Type', 'Authorization'],
        TENXYTE_CORS_MAX_AGE=3600,
    )
    def test_preflight_returns_200_with_cors_headers(self, get_response, request_factory):
        """Une requête OPTIONS preflight retourne 200 avec les headers CORS."""
        mw = CORSMiddleware(get_response)
        request = request_factory.options(f'{api_prefix}/test/', HTTP_ORIGIN='https://frontend.com')
        response = mw(request)

        assert response.status_code == 200
        assert response['Access-Control-Allow-Origin'] == 'https://frontend.com'
        assert 'GET' in response['Access-Control-Allow-Methods']
        assert 'POST' in response['Access-Control-Allow-Methods']
        assert 'DELETE' in response['Access-Control-Allow-Methods']
        assert 'Content-Type' in response['Access-Control-Allow-Headers']
        assert 'Authorization' in response['Access-Control-Allow-Headers']
        assert response['Access-Control-Max-Age'] == '3600'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://frontend.com'],
    )
    def test_preflight_disallowed_origin(self, get_response, request_factory):
        """Un preflight d'une origine non autorisée retourne 200 sans headers CORS."""
        mw = CORSMiddleware(get_response)
        request = request_factory.options(f'{api_prefix}/test/', HTTP_ORIGIN='https://evil.com')
        response = mw(request)

        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app.com'],
        TENXYTE_CORS_EXPOSE_HEADERS=['X-Custom-Header', 'X-Request-Id'],
    )
    def test_expose_headers(self, get_response, request_factory):
        """Access-Control-Expose-Headers est ajouté quand configuré."""
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app.com')
        response = mw(request)

        assert 'X-Custom-Header' in response['Access-Control-Expose-Headers']
        assert 'X-Request-Id' in response['Access-Control-Expose-Headers']


class TestCORSMultipleOrigins:
    """Tests avec plusieurs origines autorisées."""

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app1.com', 'https://app2.com'],
    )
    def test_first_origin_allowed(self, get_response, request_factory):
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app1.com')
        response = mw(request)
        assert response['Access-Control-Allow-Origin'] == 'https://app1.com'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app1.com', 'https://app2.com'],
    )
    def test_second_origin_allowed(self, get_response, request_factory):
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app2.com')
        response = mw(request)
        assert response['Access-Control-Allow-Origin'] == 'https://app2.com'

    @override_settings(
        TENXYTE_CORS_ENABLED=True,
        TENXYTE_CORS_ALLOWED_ORIGINS=['https://app1.com', 'https://app2.com'],
    )
    def test_unlisted_origin_rejected(self, get_response, request_factory):
        mw = CORSMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/', HTTP_ORIGIN='https://app3.com')
        response = mw(request)
        assert 'Access-Control-Allow-Origin' not in response


# =============================================================================
# SecurityHeadersMiddleware
# =============================================================================

class TestSecurityHeadersDisabled:
    """Tests quand les headers de sécurité sont désactivés (défaut)."""

    def test_security_headers_disabled_by_default(self, get_response, request_factory):
        """Par défaut, aucun header de sécurité n'est ajouté."""
        mw = SecurityHeadersMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/')
        response = mw(request)

        assert 'X-Content-Type-Options' not in response
        assert 'X-Frame-Options' not in response


class TestSecurityHeadersEnabled:
    """Tests quand les headers de sécurité sont activés."""

    @override_settings(TENXYTE_SECURITY_HEADERS_ENABLED=True)
    def test_default_security_headers(self, get_response, request_factory):
        """Les headers de sécurité par défaut sont ajoutés."""
        mw = SecurityHeadersMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/')
        response = mw(request)

        assert response['X-Content-Type-Options'] == 'nosniff'
        assert response['X-Frame-Options'] == 'DENY'
        assert response['Referrer-Policy'] == 'strict-origin-when-cross-origin'
        assert response['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains'
        assert "default-src 'none'" in response['Content-Security-Policy']

    @override_settings(
        TENXYTE_SECURITY_HEADERS_ENABLED=True,
        TENXYTE_SECURITY_HEADERS={
            'X-Frame-Options': 'SAMEORIGIN',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        },
    )
    def test_custom_security_headers(self, get_response, request_factory):
        """Les headers personnalisés remplacent les défauts."""
        mw = SecurityHeadersMiddleware(get_response)
        request = request_factory.get(f'{api_prefix}/test/')
        response = mw(request)

        assert response['X-Frame-Options'] == 'SAMEORIGIN'
        assert response['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains'
        # Les défauts non inclus dans le custom ne sont pas présents
        assert 'X-Content-Type-Options' not in response

    @override_settings(TENXYTE_SECURITY_HEADERS_ENABLED=True)
    def test_security_headers_on_all_responses(self, request_factory):
        """Les headers sont ajoutés même sur les réponses d'erreur."""
        def error_response(request):
            return HttpResponse("Not Found", status=404)

        mw = SecurityHeadersMiddleware(error_response)
        request = request_factory.get(f'{api_prefix}/missing/')
        response = mw(request)

        assert response.status_code == 404
        assert response['X-Content-Type-Options'] == 'nosniff'
