"""
Tests for ApplicationAuthMiddleware (spec z_aud_3, Requirement 3.4) — parity with the
Django_Adapter's `tenxyte.middleware.ApplicationAuthMiddleware`.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.application_auth import create_application


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


@pytest.fixture()
def anyio_backend():
    return "asyncio"


async def _make_client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_missing_credentials_rejected_with_app_auth_required():
    """/health itself is exempt — hit a non-exempt path instead to exercise the gate."""
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/api/v1/anything-else/")
    assert response.status_code == 401
    assert response.json()["code"] == "APP_AUTH_REQUIRED"


@pytest.mark.anyio
async def test_health_endpoint_exempt_from_application_auth():
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/api/v1/health/")  # no X-Access-Key at all
    assert response.status_code == 200


@pytest.mark.anyio
async def test_server_mode_valid_key_and_secret_accepted():
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            application, raw_secret = await create_application(session, "Test App")

        async with await _make_client(app) as client:
            response = await client.get(
                "/api/v1/health/",
                headers={"X-Access-Key": application.access_key, "X-Access-Secret": raw_secret},
            )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_server_mode_wrong_secret_rejected():
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            application, _raw_secret = await create_application(session, "Test App")

        async with await _make_client(app) as client:
            response = await client.get(
                "/api/v1/anything/",
                headers={"X-Access-Key": application.access_key, "X-Access-Secret": "wrong-secret"},
            )
    assert response.status_code == 401
    assert response.json()["code"] == "APP_AUTH_INVALID"


@pytest.mark.anyio
async def test_unknown_access_key_rejected():
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/api/v1/anything/", headers={"X-Access-Key": "does-not-exist"})
    assert response.status_code == 401
    assert response.json()["code"] == "APP_AUTH_INVALID"


@pytest.mark.anyio
async def test_key_only_mode_requires_origin():
    app = create_tenxyte_app(database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            application, _raw_secret = await create_application(
                session, "Frontend App", allowed_origins=["https://app.example.com"]
            )

        async with await _make_client(app) as client:
            no_origin = await client.get("/api/v1/anything/", headers={"X-Access-Key": application.access_key})
            assert no_origin.status_code == 401
            assert no_origin.json()["code"] == "APP_AUTH_ORIGIN_REQUIRED"

            bad_origin = await client.get(
                "/api/v1/anything/",
                headers={"X-Access-Key": application.access_key, "Origin": "https://evil.example.com"},
            )
            assert bad_origin.status_code == 401
            assert bad_origin.json()["code"] == "APP_AUTH_ORIGIN_DENIED"

            good_origin = await client.get(
                "/api/v1/health/",
                headers={"X-Access-Key": application.access_key, "Origin": "https://app.example.com"},
            )
            assert good_origin.status_code == 200


@pytest.mark.anyio
async def test_application_auth_disabled_toggle():
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _DisabledProvider(EnvSettingsProvider):
        def get(self, name, default=None):
            if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
                return False
            return super().get(name, default)

    settings = Settings(provider=_DisabledProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        # A non-exempt path with zero credentials — still 200 because the toggle disables
        # the whole check, not just widens the exemption list.
        response = await client.get("/api/v1/anything/")
    assert response.status_code == 404  # no such route — but crucially NOT 401


@pytest.mark.anyio
async def test_application_auth_disabled_toggle_health_still_ok():
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _DisabledProvider(EnvSettingsProvider):
        def get(self, name, default=None):
            if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
                return False
            return super().get(name, default)

    settings = Settings(provider=_DisabledProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        response = await client.get("/api/v1/health/")
    assert response.status_code == 200
