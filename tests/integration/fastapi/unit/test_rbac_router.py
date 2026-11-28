"""
Tests for the Wave D RBAC router (spec z_aud_3, task 10.1) — permissions/*, roles/*,
roles/{id}/permissions/*, users/{id}/roles/*, users/{id}/permissions/* — against a real app, a
real ephemeral aiosqlite database, and real signed tokens (no mocks).
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
            return "test-secret-key-for-rbac-router-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(app, *, email: str, is_superuser: bool = False) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password("correct-horse-battery-staple")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=password_hash,
                is_active=True,
                is_superuser=is_superuser,
            )
        )


def _token(app, user: User) -> str:
    return app.state.tenxyte_jwt_service.generate_new_token_pair(user_id=user.id, application_id="default").access_token


async def _admin_headers(app) -> dict:
    admin = await _create_user(app, email=f"admin-{uuid.uuid4().hex}@example.com", is_superuser=True)
    return {"Authorization": f"Bearer {_token(app, admin)}"}


@pytest.mark.anyio
async def test_permission_crud_lifecycle():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            create = await client.post(
                "/api/v1/permissions/", json={"code": "reports.view", "name": "View reports"}, headers=headers
            )
            assert create.status_code == 201
            body = create.json()
            assert body["code"] == "reports.view"
            assert body["parent"] is None
            assert body["children"] == []
            permission_id = body["id"]

            get_resp = await client.get(f"/api/v1/permissions/{permission_id}/", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["code"] == "reports.view"

            update = await client.put(
                f"/api/v1/permissions/{permission_id}/", json={"name": "View all reports"}, headers=headers
            )
            assert update.status_code == 200
            assert update.json()["name"] == "View all reports"

            delete = await client.delete(f"/api/v1/permissions/{permission_id}/", headers=headers)
            assert delete.status_code == 200

            missing = await client.get(f"/api/v1/permissions/{permission_id}/", headers=headers)
            assert missing.status_code == 404
            assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_permission_hierarchy_parent_child():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            parent = await client.post(
                "/api/v1/permissions/", json={"code": "reports.view", "name": "View reports"}, headers=headers
            )
            child = await client.post(
                "/api/v1/permissions/",
                json={"code": "reports.export", "name": "Export reports", "parent_code": "reports.view"},
                headers=headers,
            )
            assert child.status_code == 201
            assert child.json()["parent"] == {"id": parent.json()["id"], "code": "reports.view"}

            parent_refetched = await client.get(f"/api/v1/permissions/{parent.json()['id']}/", headers=headers)
            assert parent_refetched.json()["children"] == [
                {"id": child.json()["id"], "code": "reports.export", "name": "Export reports"}
            ]


@pytest.mark.anyio
async def test_permission_create_unknown_parent_code_400():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/permissions/",
                json={"code": "x", "name": "X", "parent_code": "does.not.exist"},
                headers=headers,
            )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_permission_list_filters_and_pagination():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            for i in range(25):
                await client.post(
                    "/api/v1/permissions/", json={"code": f"perm.{i:03d}", "name": f"Permission {i}"}, headers=headers
                )

            page1 = await client.get("/api/v1/permissions/", headers=headers)
            assert page1.status_code == 200
            body = page1.json()
            assert body["count"] == 25
            assert body["page"] == 1
            assert body["page_size"] == 20
            assert body["total_pages"] == 2
            assert len(body["results"]) == 20
            assert body["previous"] is None
            assert body["next"] is not None

            page2 = await client.get("/api/v1/permissions/?page=2", headers=headers)
            assert len(page2.json()["results"]) == 5
            assert page2.json()["next"] is None
            assert page2.json()["previous"] is not None

            searched = await client.get("/api/v1/permissions/?search=perm.001", headers=headers)
            assert searched.json()["count"] == 1


@pytest.mark.anyio
async def test_permission_list_parent_null_filter():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            await client.post("/api/v1/permissions/", json={"code": "root", "name": "Root"}, headers=headers)
            await client.post(
                "/api/v1/permissions/", json={"code": "child", "name": "Child", "parent_code": "root"}, headers=headers
            )

            roots_only = await client.get("/api/v1/permissions/?parent=null", headers=headers)

    codes = {p["code"] for p in roots_only.json()["results"]}
    assert codes == {"root"}


@pytest.mark.anyio
async def test_role_crud_lifecycle_with_permissions():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            await client.post(
                "/api/v1/permissions/", json={"code": "users.view", "name": "View users"}, headers=headers
            )
            await client.post("/api/v1/permissions/", json={"code": "logs.view", "name": "View logs"}, headers=headers)

            create = await client.post(
                "/api/v1/roles/",
                json={
                    "code": "tech_support",
                    "name": "Support Technique",
                    "permission_codes": ["users.view", "logs.view"],
                },
                headers=headers,
            )
            assert create.status_code == 201
            body = create.json()
            assert body["code"] == "tech_support"
            assert {p["code"] for p in body["permissions"]} == {"users.view", "logs.view"}
            role_id = body["id"]

            listing = await client.get("/api/v1/roles/", headers=headers)
            assert listing.status_code == 200
            assert any(r["code"] == "tech_support" for r in listing.json()["results"])
            # List uses the lightweight serializer — no `permissions` field.
            assert "permissions" not in listing.json()["results"][0]

            update = await client.put(
                f"/api/v1/roles/{role_id}/", json={"permission_codes": ["users.view"]}, headers=headers
            )
            assert update.status_code == 200
            assert [p["code"] for p in update.json()["permissions"]] == ["users.view"]

            delete = await client.delete(f"/api/v1/roles/{role_id}/", headers=headers)
            assert delete.status_code == 200
            missing = await client.get(f"/api/v1/roles/{role_id}/", headers=headers)
            assert missing.status_code == 404


@pytest.mark.anyio
async def test_role_permissions_add_remove():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            await client.post("/api/v1/permissions/", json={"code": "a", "name": "A"}, headers=headers)
            await client.post("/api/v1/permissions/", json={"code": "b", "name": "B"}, headers=headers)
            role = await client.post("/api/v1/roles/", json={"code": "r1", "name": "R1"}, headers=headers)
            role_id = role.json()["id"]

            add = await client.post(
                f"/api/v1/roles/{role_id}/permissions/", json={"permission_codes": ["a", "b"]}, headers=headers
            )
            assert add.status_code == 200
            assert set(add.json()["added"]) == {"a", "b"}
            assert "already_assigned" not in add.json()

            add_again = await client.post(
                f"/api/v1/roles/{role_id}/permissions/", json={"permission_codes": ["a"]}, headers=headers
            )
            assert add_again.json()["added"] == []
            assert add_again.json()["already_assigned"] == ["a"]

            get_perms = await client.get(f"/api/v1/roles/{role_id}/permissions/", headers=headers)
            assert {p["code"] for p in get_perms.json()["permissions"]} == {"a", "b"}

            remove = await client.request(
                "DELETE",
                f"/api/v1/roles/{role_id}/permissions/",
                json={"permission_codes": ["a"]},
                headers=headers,
            )
            assert remove.status_code == 200
            assert remove.json()["removed"] == ["a"]

            unknown = await client.post(
                f"/api/v1/roles/{role_id}/permissions/", json={"permission_codes": ["does-not-exist"]}, headers=headers
            )
            assert unknown.status_code == 400
            assert unknown.json()["code"] == "PERMISSIONS_NOT_FOUND"
            assert unknown.json()["not_found"] == ["does-not-exist"]


@pytest.mark.anyio
async def test_role_permissions_empty_list_validation_error():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            role = await client.post("/api/v1/roles/", json={"code": "r2", "name": "R2"}, headers=headers)
            response = await client.post(
                f"/api/v1/roles/{role.json()['id']}/permissions/", json={"permission_codes": []}, headers=headers
            )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_user_roles_assign_and_remove():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        target = await _create_user(app, email="target@example.com")
        async with await _client(app) as client:
            await client.post("/api/v1/roles/", json={"code": "viewer", "name": "Viewer"}, headers=headers)

            assign = await client.post(
                f"/api/v1/users/{target.id}/roles/", json={"role_code": "viewer"}, headers=headers
            )
            assert assign.status_code == 200
            assert assign.json() == {"message": "Role assigned", "roles": ["viewer"]}

            get_roles = await client.get(f"/api/v1/users/{target.id}/roles/", headers=headers)
            assert get_roles.json()["roles"] == [
                {"id": get_roles.json()["roles"][0]["id"], "code": "viewer", "name": "Viewer", "is_default": False}
            ]

            unknown_role = await client.post(
                f"/api/v1/users/{target.id}/roles/", json={"role_code": "does-not-exist"}, headers=headers
            )
            assert unknown_role.status_code == 404
            assert unknown_role.json()["code"] == "ROLE_NOT_FOUND"

            missing_param = await client.delete(f"/api/v1/users/{target.id}/roles/", headers=headers)
            assert missing_param.status_code == 400
            assert missing_param.json()["code"] == "MISSING_PARAM"

            remove = await client.delete(f"/api/v1/users/{target.id}/roles/?role_code=viewer", headers=headers)
            assert remove.status_code == 200
            assert remove.json() == {"message": "Role removed", "roles": []}


@pytest.mark.anyio
async def test_user_roles_unknown_user_404():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        async with await _client(app) as client:
            response = await client.get(f"/api/v1/users/{uuid.uuid4()}/roles/", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_user_direct_permissions_add_remove_and_effective_permissions():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        target = await _create_user(app, email="direct@example.com")
        async with await _client(app) as client:
            await client.post("/api/v1/permissions/", json={"code": "reports.view", "name": "View"}, headers=headers)
            await client.post(
                "/api/v1/permissions/",
                json={"code": "reports.export", "name": "Export", "parent_code": "reports.view"},
                headers=headers,
            )

            add = await client.post(
                f"/api/v1/users/{target.id}/permissions/", json={"permission_codes": ["reports.view"]}, headers=headers
            )
            assert add.status_code == 200
            assert add.json()["added"] == ["reports.view"]

            get_perms = await client.get(f"/api/v1/users/{target.id}/permissions/", headers=headers)
            assert [p["code"] for p in get_perms.json()["direct_permissions"]] == ["reports.view"]
            # Hierarchy: holding the parent grants the child too.
            assert set(get_perms.json()["all_permissions"]) == {"reports.view", "reports.export"}

            remove = await client.request(
                "DELETE",
                f"/api/v1/users/{target.id}/permissions/",
                json={"permission_codes": ["reports.view"]},
                headers=headers,
            )
            assert remove.status_code == 200
            assert remove.json()["removed"] == ["reports.view"]


@pytest.mark.anyio
async def test_super_admin_role_bypasses_permission_checks():
    """[has_permission()'s second bypass]: holding the `super_admin` *role* (not just
    `is_superuser`) also passes every RBAC check."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        admin_headers = await _admin_headers(app)
        regular = await _create_user(app, email="delegate@example.com")
        regular_headers = {"Authorization": f"Bearer {_token(app, regular)}"}
        async with await _client(app) as client:
            await client.post(
                "/api/v1/roles/", json={"code": "super_admin", "name": "Super Admin"}, headers=admin_headers
            )
            await client.post(
                f"/api/v1/users/{regular.id}/roles/", json={"role_code": "super_admin"}, headers=admin_headers
            )

            response = await client.post(
                "/api/v1/permissions/", json={"code": "anything.at.all", "name": "Anything"}, headers=regular_headers
            )

    assert response.status_code == 201


@pytest.mark.anyio
async def test_non_privileged_user_rejected_with_generic_message():
    """Matches Django's non-verbose `TENXYTE_VERBOSE_ERRORS=False` default exactly — the specific
    permission code is never echoed back."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        regular = await _create_user(app, email="norole@example.com")
        headers = {"Authorization": f"Bearer {_token(app, regular)}"}
        async with await _client(app) as client:
            response = await client.get("/api/v1/permissions/", headers=headers)

    assert response.status_code == 403
    assert response.json() == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}


@pytest.mark.anyio
async def test_me_roles_reflects_real_rbac_state():
    app = _build_app()
    async with app.router.lifespan_context(app):
        headers = await _admin_headers(app)
        target = await _create_user(app, email="selfview@example.com")
        target_headers = {"Authorization": f"Bearer {_token(app, target)}"}
        async with await _client(app) as client:
            empty = await client.get("/api/v1/me/roles/", headers=target_headers)
            assert empty.json() == {"roles": [], "permissions": []}

            await client.post("/api/v1/permissions/", json={"code": "x.y", "name": "XY"}, headers=headers)
            await client.post(
                "/api/v1/roles/",
                json={"code": "member", "name": "Member", "permission_codes": ["x.y"]},
                headers=headers,
            )
            await client.post(f"/api/v1/users/{target.id}/roles/", json={"role_code": "member"}, headers=headers)

            populated = await client.get("/api/v1/me/roles/", headers=target_headers)

    assert populated.json() == {"roles": ["member"], "permissions": ["x.y"]}
