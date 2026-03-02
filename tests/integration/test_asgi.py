import pytest
from django.test import AsyncClient
from tenxyte.models import Application
from asgiref.sync import sync_to_async


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestASGIMiddlewares:

    async def test_application_auth_middleware_async(self):
        """
        Verify that ApplicationAuthMiddleware can run in an ASGI (async) context
        without raising SynchronousOnlyOperation errors.
        Application.create_application() hashes the secret and returns raw value.
        """
        app, raw_secret = await sync_to_async(Application.create_application)("Test ASGI App")
        client = AsyncClient()
        url = '/api/v1/applications/'

        headers = {
            'HTTP_X_ACCESS_KEY': app.access_key,
            'HTTP_X_ACCESS_SECRET': raw_secret,
            'HTTP_ACCEPT': 'application/json'
        }

        # The response status depends on view-level auth, but we assert
        # there is no SynchronousOnlyOperation error (which would cause a 500).
        response = await client.get(url, **headers)
        assert response.status_code in [200, 401, 403, 404]

    async def test_application_auth_middleware_invalid_async(self):
        """
        Verify ApplicationAuthMiddleware responds 401 with correct code
        when credentials are invalid — in an async context.
        """
        client = AsyncClient()
        url = '/api/v1/applications/'
        headers = {
            'HTTP_X_ACCESS_KEY': 'invalid_key',
            'HTTP_X_ACCESS_SECRET': 'invalid_secret',
            'HTTP_ACCEPT': 'application/json'
        }
        response = await client.get(url, **headers)

        assert response.status_code == 401
        data = response.json()
        assert data['code'] in ['APP_AUTH_INVALID', 'APP_AUTH_REQUIRED']

    async def test_application_auth_middleware_missing_headers_async(self):
        """
        Verify ApplicationAuthMiddleware responds 401 with APP_AUTH_REQUIRED
        when no credentials are provided at all — in an async context.
        """
        client = AsyncClient()
        url = '/api/v1/applications/'
        response = await client.get(url, HTTP_ACCEPT='application/json')

        assert response.status_code == 401
        data = response.json()
        assert data['code'] == 'APP_AUTH_REQUIRED'
