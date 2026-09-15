"""
Tests for the Wave E Organizations router (spec z_aud_3, Wave E chunk 1/4, task 11.1) —
organization CRUD — against a real app, a real ephemeral aiosqlite database, and real signed
tokens (no mocks).
"""

import uuid

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _OrgsEnabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-orgs-router-tests"
        if name == "TENXYTE_ORGANIZATIONS_ENABLED":
            return True
        return super().get(name, default)


class _OrgsDisabledProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-orgs-router-tests"
        return super().get(name, default)


def _build_app(*, orgs_enabled: bool = True):
    provider = _OrgsEnabledProvider() if orgs_enabled else _OrgsDisabledProvider()
    settings = Settings(provider=provider)
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app) -> tuple[str, dict]:
    session_factory = app.state.tenxyte_session_factory
    password_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        created = await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=f"user-{uuid.uuid4().hex}@example.com",
                password_hash=password_hash,
                is_active=True,
            )
        )
    token = app.state.tenxyte_jwt_service.generate_new_token_pair(
        user_id=created.id, application_id="default"
    ).access_token
    return created.id, {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_organizations_feature_disabled_by_default_404s():
    """Mirrors Django's own conditional urlpatterns: a disabled deployment never registers these
    routes, so it 404s rather than returning a JSON ORG_FEATURE_DISABLED body."""
    app = _build_app(orgs_enabled=False)
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/organizations/list/", headers=headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_organization_makes_creator_owner():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            create = await client.post("/api/v1/organizations/", json={"name": "Acme Corp"}, headers=headers)
            assert create.status_code == 201
            body = create.json()
            assert body["name"] == "Acme Corp"
            assert body["slug"] == "acme-corp"
            assert body["user_role"] == "owner"
            assert body["member_count"] == 1
            assert body["max_members"] == 0

            slug_headers = {**headers, "X-Org-Slug": "acme-corp"}
            detail = await client.get("/api/v1/organizations/detail/", headers=slug_headers)
            assert detail.status_code == 200
            assert detail.json()["slug"] == "acme-corp"


@pytest.mark.anyio
async def test_create_organization_slug_auto_uniquifies():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            first = await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=headers)
            second = await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=headers)
            assert first.json()["slug"] == "acme"
            assert second.json()["slug"] == "acme-1"


@pytest.mark.anyio
async def test_get_organization_requires_membership():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Private Org"}, headers=owner_headers)

            outsider_ctx = {**outsider_headers, "X-Org-Slug": "private-org"}
            response = await client.get("/api/v1/organizations/detail/", headers=outsider_ctx)
            assert response.status_code == 403
            assert response.json() == {
                "error": "You are not a member of this organization",
                "code": "ORG_MEMBERSHIP_REQUIRED",
                "organization": "private-org",
            }


@pytest.mark.anyio
async def test_missing_org_slug_header_returns_context_required():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get("/api/v1/organizations/detail/", headers=headers)
    assert response.status_code == 400
    assert response.json() == {
        "error": "Organization context required. Please provide X-Org-Slug header.",
        "code": "ORG_CONTEXT_REQUIRED",
    }


@pytest.mark.anyio
async def test_unknown_org_slug_returns_404_with_slug():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            response = await client.get(
                "/api/v1/organizations/detail/", headers={**headers, "X-Org-Slug": "does-not-exist"}
            )
    assert response.status_code == 404
    assert response.json() == {"error": "Organization not found", "code": "ORG_NOT_FOUND", "slug": "does-not-exist"}


@pytest.mark.anyio
async def test_update_organization_owner_allowed():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=headers)
            org_headers = {**headers, "X-Org-Slug": "acme"}

            update = await client.patch(
                "/api/v1/organizations/update/",
                json={"description": "Updated", "max_members": 5},
                headers=org_headers,
            )
            assert update.status_code == 200
            assert update.json()["description"] == "Updated"
            assert update.json()["max_members"] == 5


@pytest.mark.anyio
async def test_update_organization_rejects_non_admin_with_no_code():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**outsider_headers, "X-Org-Slug": "acme"}

            response = await client.patch(
                "/api/v1/organizations/update/", json={"description": "Hijack"}, headers=org_headers
            )
            assert response.status_code == 403
            assert response.json() == {"error": "Permission denied.", "code": "ORG_ROLE_REQUIRED"}


@pytest.mark.anyio
async def test_delete_organization_owner_only():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)

            non_owner_delete = await client.delete(
                "/api/v1/organizations/delete/", headers={**outsider_headers, "X-Org-Slug": "acme"}
            )
            assert non_owner_delete.status_code == 403

            delete = await client.delete(
                "/api/v1/organizations/delete/", headers={**owner_headers, "X-Org-Slug": "acme"}
            )
            assert delete.status_code == 200
            assert delete.json() == {"message": "Organization deleted successfully"}

            missing = await client.get("/api/v1/organizations/detail/", headers={**owner_headers, "X-Org-Slug": "acme"})
            assert missing.status_code == 404


@pytest.mark.anyio
async def test_delete_organization_blocked_by_children():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            parent = await client.post("/api/v1/organizations/", json={"name": "Parent"}, headers=headers)
            parent_id = parent.json()["id"]
            await client.post("/api/v1/organizations/", json={"name": "Child", "parent_id": parent_id}, headers=headers)

            response = await client.delete("/api/v1/organizations/delete/", headers={**headers, "X-Org-Slug": "parent"})
            assert response.status_code == 400
            assert response.json() == {"error": "Cannot delete organization with child organizations"}


@pytest.mark.anyio
async def test_create_child_organization_needs_no_relationship_to_parent():
    """Real Django finding (see org_service.py docstring): create_organization has no permission
    check against parent_id at all — any authenticated user can nest under any existing org."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, owner_headers = await _create_user(app)
        _, stranger_headers = await _create_user(app)
        async with await _client(app) as client:
            parent = await client.post("/api/v1/organizations/", json={"name": "Private Parent"}, headers=owner_headers)
            parent_id = parent.json()["id"]

            child = await client.post(
                "/api/v1/organizations/",
                json={"name": "Squatter Child", "parent_id": parent_id},
                headers=stranger_headers,
            )
            assert child.status_code == 201
            assert child.json()["user_role"] == "owner"


@pytest.mark.anyio
async def test_list_organizations_only_shows_membership():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers_a = await _create_user(app)
        _, headers_b = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Org A"}, headers=headers_a)
            await client.post("/api/v1/organizations/", json={"name": "Org B"}, headers=headers_b)

            listing_a = await client.get("/api/v1/organizations/list/", headers=headers_a)
            assert listing_a.status_code == 200
            names = [org["name"] for org in listing_a.json()["results"]]
            assert names == ["Org A"]
