"""
Tests for the Wave E Organizations router (spec z_aud_3, Wave E, task 11.1) — organization CRUD
(chunk 1/4), hierarchy tree + org-roles listing (chunk 2/4), member management (chunk 3/4), and
invitations (chunk 4/4) — against a real app, a real ephemeral aiosqlite database, and real signed
tokens (no mocks).
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
    password_hash = hash_password("correct-horse-battery-staple")
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


@pytest.mark.anyio
async def test_organization_tree_always_starts_at_root():
    """Real Django finding (see org_service.py docstring): the tree always builds from the root
    ancestor down, even when scoped into a child via X-Org-Slug."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            parent = await client.post("/api/v1/organizations/", json={"name": "Parent"}, headers=headers)
            parent_id = parent.json()["id"]
            await client.post("/api/v1/organizations/", json={"name": "Child", "parent_id": parent_id}, headers=headers)

            tree = await client.get("/api/v1/organizations/tree/", headers={**headers, "X-Org-Slug": "child"})
            assert tree.status_code == 200
            body = tree.json()
            assert body["slug"] == "parent"
            assert body["is_root"] is True
            assert body["depth"] == 0
            assert len(body["children"]) == 1
            assert body["children"][0]["slug"] == "child"
            assert body["children"][0]["depth"] == 1
            assert body["children"][0]["children"] == []


@pytest.mark.anyio
async def test_organization_tree_requires_membership():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            response = await client.get(
                "/api/v1/organizations/tree/", headers={**outsider_headers, "X-Org-Slug": "acme"}
            )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_list_org_roles_is_global_and_unscoped():
    app = _build_app()
    async with app.router.lifespan_context(app):
        _, headers = await _create_user(app)
        async with await _client(app) as client:
            # No organization exists yet, so no "owner" role has been lazily created either.
            empty = await client.get("/api/v1/org-roles/", headers=headers)
            assert empty.status_code == 200
            assert empty.json() == []

            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=headers)

            # Still callable with no X-Org-Slug at all -- this endpoint is global, not org-scoped.
            listing = await client.get("/api/v1/org-roles/", headers=headers)
            assert listing.status_code == 200
            codes = [role["code"] for role in listing.json()]
            assert codes == ["owner"]
            assert listing.json()[0]["permissions"] == ["org.*"]


@pytest.mark.anyio
async def test_list_org_roles_requires_auth():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/org-roles/")
    assert response.status_code == 401


async def _seed_system_roles(app):
    """Django itself only ever creates admin/member/viewer roles from its own test fixtures
    (`initialize_system_roles()` is never called by any application code path — see
    org_service.py's module docstring); this port's tests seed the same way for the same reason."""
    from tenxyte.adapters.fastapi import org_service

    async with app.state.tenxyte_session_factory() as session:
        await org_service.initialize_system_roles_async(session)


@pytest.mark.anyio
async def test_add_member_success_and_rejects_duplicate():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        member_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**owner_headers, "X-Org-Slug": "acme"}

            add = await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": member_id, "role_code": "member"},
                headers=org_headers,
            )
            assert add.status_code == 201
            assert add.json()["user"]["id"] == member_id
            assert add.json()["role"]["code"] == "member"
            assert add.json()["status"] == "active"

            duplicate = await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": member_id, "role_code": "member"},
                headers=org_headers,
            )
            assert duplicate.status_code == 400
            assert duplicate.json() == {"error": "User is already a member"}


@pytest.mark.anyio
async def test_add_member_requires_invite_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        target_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            response = await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": target_id, "role_code": "member"},
                headers={**outsider_headers, "X-Org-Slug": "acme"},
            )
    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "ORG_PERMISSION_REQUIRED"}


@pytest.mark.anyio
async def test_add_member_unknown_user_404():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            response = await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": str(uuid.uuid4()), "role_code": "member"},
                headers={**owner_headers, "X-Org-Slug": "acme"},
            )
    assert response.status_code == 404
    assert response.json() == {"error": "User not found"}


@pytest.mark.anyio
async def test_list_members_and_filters():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        owner_id, owner_headers = await _create_user(app)
        member_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**owner_headers, "X-Org-Slug": "acme"}
            await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": member_id, "role_code": "member"},
                headers=org_headers,
            )

            listing = await client.get("/api/v1/organizations/members/", headers=org_headers)
            assert listing.status_code == 200
            assert listing.json()["count"] == 2

            owners_only = await client.get("/api/v1/organizations/members/?role=owner", headers=org_headers)
            assert owners_only.json()["count"] == 1
            assert owners_only.json()["results"][0]["user"]["id"] == owner_id


@pytest.mark.anyio
async def test_update_member_role_success_and_owner_protected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        owner_id, owner_headers = await _create_user(app)
        member_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**owner_headers, "X-Org-Slug": "acme"}
            await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": member_id, "role_code": "member"},
                headers=org_headers,
            )

            promote = await client.patch(
                f"/api/v1/organizations/members/{member_id}/",
                json={"role_code": "admin"},
                headers=org_headers,
            )
            assert promote.status_code == 200
            assert promote.json()["role"]["code"] == "admin"

            protect_owner = await client.patch(
                f"/api/v1/organizations/members/{owner_id}/",
                json={"role_code": "member"},
                headers=org_headers,
            )
            assert protect_owner.status_code == 400
            assert protect_owner.json() == {"error": "Cannot change owner role"}


@pytest.mark.anyio
async def test_remove_member_success_and_owner_protected():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        owner_id, owner_headers = await _create_user(app)
        member_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**owner_headers, "X-Org-Slug": "acme"}
            await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": member_id, "role_code": "member"},
                headers=org_headers,
            )

            remove = await client.delete(f"/api/v1/organizations/members/{member_id}/remove/", headers=org_headers)
            assert remove.status_code == 200
            assert remove.json() == {"message": "Member removed successfully"}

            protect_owner = await client.delete(
                f"/api/v1/organizations/members/{owner_id}/remove/", headers=org_headers
            )
            assert protect_owner.status_code == 400
            assert protect_owner.json() == {"error": "Cannot remove organization owner"}


@pytest.mark.anyio
async def test_add_member_respects_member_limit():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        target_id, _ = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme", "max_members": 1}, headers=owner_headers)
            response = await client.post(
                "/api/v1/organizations/members/add/",
                json={"user_id": target_id, "role_code": "member"},
                headers={**owner_headers, "X-Org-Slug": "acme"},
            )
    assert response.status_code == 400
    assert response.json() == {"error": "Organization has reached its member limit"}


@pytest.mark.anyio
async def test_invite_member_success():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            response = await client.post(
                "/api/v1/organizations/invitations/",
                json={"email": "invitee@example.com", "role_code": "member"},
                headers={**owner_headers, "X-Org-Slug": "acme"},
            )
            assert response.status_code == 201
            body = response.json()
            assert body["organization_name"] == "Acme"
            assert body["email"] == "invitee@example.com"
            assert body["role_name"] == "Member"
            assert body["status"] == "pending"
            assert body["invited_by_email"] is not None
            assert len(body["token"]) > 10
            assert "organization" not in body
            assert "role" not in body
            assert "invited_by" not in body


@pytest.mark.anyio
async def test_invite_member_duplicate_expires_previous_not_rejected():
    """Real Django finding (see org_service.py docstring): no INVITATION_EXISTS rejection --
    a second invite to the same email silently expires the first and creates a fresh one."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            org_headers = {**owner_headers, "X-Org-Slug": "acme"}

            first = await client.post(
                "/api/v1/organizations/invitations/",
                json={"email": "invitee@example.com", "role_code": "member"},
                headers=org_headers,
            )
            second = await client.post(
                "/api/v1/organizations/invitations/",
                json={"email": "invitee@example.com", "role_code": "admin"},
                headers=org_headers,
            )
            assert first.status_code == 201
            assert second.status_code == 201
            assert first.json()["token"] != second.json()["token"]
            assert second.json()["role_name"] == "Admin"


@pytest.mark.anyio
async def test_invite_member_rejects_existing_member_email():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        async with await _client(app) as client:
            create = await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            owner_email = create.json()["created_by_email"]
            response = await client.post(
                "/api/v1/organizations/invitations/",
                json={"email": owner_email, "role_code": "member"},
                headers={**owner_headers, "X-Org-Slug": "acme"},
            )
    assert response.status_code == 400
    assert response.json() == {"error": "User is already a member"}


@pytest.mark.anyio
async def test_invite_member_requires_permission():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_system_roles(app)
        _, owner_headers = await _create_user(app)
        _, outsider_headers = await _create_user(app)
        async with await _client(app) as client:
            await client.post("/api/v1/organizations/", json={"name": "Acme"}, headers=owner_headers)
            response = await client.post(
                "/api/v1/organizations/invitations/",
                json={"email": "invitee@example.com", "role_code": "member"},
                headers={**outsider_headers, "X-Org-Slug": "acme"},
            )
    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "ORG_PERMISSION_REQUIRED"}
