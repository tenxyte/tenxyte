"""
Tests for the Wave D Applications router (spec z_aud_3, Wave D chunk 2/5, task 10.1) —
applications/* — against a real app, a real ephemeral aiosqlite database, and real signed tokens
(no mocks).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-applications-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _admin_headers(app) -> dict:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password("correct-horse-battery-staple")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        admin = await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=f"admin-{uuid.uuid4().hex}@example.com",
                password_hash=password_hash,
                is_active=True,
                is_superuser=True,
            )
        )
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=admin.id, application_id="default"
    ).access_token
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_application_crud_lifecycle():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            create = await client.post(
                "/api/v1/applications/", json={"name": "Mobile App", "description": "iOS/Android"}, headers=headers
            )
            assert create.status_code == 201
            body = create.json()
            assert body["message"] == "Application created successfully"
            assert body["application"]["name"] == "Mobile App"
            assert "access_secret" not in body["application"]
            raw_secret = body["credentials"]["access_secret"]
            assert raw_secret
            app_id = body["application"]["id"]

            get_resp = await client.get(f"/api/v1/applications/{app_id}/", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["name"] == "Mobile App"
            assert "access_secret" not in get_resp.json()

            update = await client.put(
                f"/api/v1/applications/{app_id}/", json={"name": "Mobile App v2"}, headers=headers
            )
            assert update.status_code == 200
            assert update.json()["name"] == "Mobile App v2"

            delete = await client.delete(f"/api/v1/applications/{app_id}/", headers=headers)
            assert delete.status_code == 200

            missing = await client.get(f"/api/v1/applications/{app_id}/", headers=headers)
            assert missing.status_code == 404
            assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_application_toggle_active_status():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            create = await client.post("/api/v1/applications/", json={"name": "Toggle App"}, headers=headers)
            app_id = create.json()["application"]["id"]
            assert create.json()["application"]["is_active"] is True

            deactivate = await client.patch(
                f"/api/v1/applications/{app_id}/", json={"is_active": False}, headers=headers
            )
            assert deactivate.status_code == 200
            assert deactivate.json()["message"] == "Application deactivated successfully"
            assert deactivate.json()["application"]["is_active"] is False

            no_fields = await client.patch(f"/api/v1/applications/{app_id}/", json={}, headers=headers)
            assert no_fields.status_code == 400
            assert no_fields.json()["code"] == "INVALID_FIELDS"


@pytest.mark.anyio
async def test_application_regenerate_requires_confirmation():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            create = await client.post("/api/v1/applications/", json={"name": "Regen App"}, headers=headers)
            app_id = create.json()["application"]["id"]
            original_key = create.json()["application"]["access_key"]

            missing_confirmation = await client.post(
                f"/api/v1/applications/{app_id}/regenerate/", json={}, headers=headers
            )
            assert missing_confirmation.status_code == 400
            assert missing_confirmation.json()["code"] == "CONFIRMATION_REQUIRED"

            regenerate = await client.post(
                f"/api/v1/applications/{app_id}/regenerate/", json={"confirmation": "REGENERATE"}, headers=headers
            )
            assert regenerate.status_code == 200
            assert regenerate.json()["old_credentials_invalidated"] is True
            assert regenerate.json()["credentials"]["access_key"] != original_key
            assert regenerate.json()["application"]["access_key"] == regenerate.json()["credentials"]["access_key"]


@pytest.mark.anyio
async def test_application_list_filters_and_pagination():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            for i in range(22):
                await client.post("/api/v1/applications/", json={"name": f"App {i:03d}"}, headers=headers)

            page1 = await client.get("/api/v1/applications/", headers=headers)
            assert page1.json()["count"] == 22
            assert len(page1.json()["results"]) == 20

            page2 = await client.get("/api/v1/applications/?page=2", headers=headers)
            assert len(page2.json()["results"]) == 2

            searched = await client.get("/api/v1/applications/?search=App 005", headers=headers)
            assert searched.json()["count"] == 1


@pytest.mark.anyio
async def test_application_endpoints_require_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        password_hash = hash_password("correct-horse-battery-staple")
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            regular = await repo.create(
                User(id=str(uuid.uuid4()), email="regular@example.com", password_hash=password_hash, is_active=True)
            )
        token = app.state.tenxyte_jwt_service.generate_new_token_pair(
            user_id=regular.id, application_id="default"
        ).access_token
        headers = {"Authorization": f"Bearer {token}"}
        async with await _client(app) as client:
            response = await client.get("/api/v1/applications/", headers=headers)

    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
