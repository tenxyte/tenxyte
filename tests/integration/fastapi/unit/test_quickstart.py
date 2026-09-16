"""
Tests for `tenxyte.adapters.fastapi.quickstart` (spec z_aud_3, follow-up) — the FastAPI
counterpart of the Django adapter's `python manage.py tenxyte_quickstart` — against a real
ephemeral aiosqlite database (no mocks): real schema creation, real RBAC rows, real Application
credentials.
"""

import uuid

import pytest
from sqlalchemy import func, select

from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.models_sa import ApplicationDB, PermissionDB, RoleDB, role_permissions_table
from tenxyte.adapters.fastapi.quickstart import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    bootstrap,
    create_default_application,
    seed_rbac,
)


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


async def _fresh_session_factory():
    engine = db_module.create_engine(_fresh_sqlite_url())
    await db_module.create_all_tables(engine)
    return engine, db_module.create_session_factory(engine)


@pytest.mark.anyio
async def test_seed_rbac_creates_all_default_permissions_and_roles():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        permissions_created, roles_created = await seed_rbac(session)
        assert permissions_created == len(DEFAULT_PERMISSIONS)
        assert roles_created == len(DEFAULT_ROLES)

        total_permissions = (await session.execute(select(func.count(PermissionDB.id)))).scalar_one()
        total_roles = (await session.execute(select(func.count(RoleDB.id)))).scalar_one()
        assert total_permissions == len(DEFAULT_PERMISSIONS)
        assert total_roles == len(DEFAULT_ROLES)
    await engine.dispose()


@pytest.mark.anyio
async def test_seed_rbac_is_idempotent():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        await seed_rbac(session)
        permissions_created, roles_created = await seed_rbac(session)
        assert (permissions_created, roles_created) == (0, 0)
    await engine.dispose()


@pytest.mark.anyio
async def test_permission_hierarchy_is_wired():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        await seed_rbac(session)
        stmt = select(PermissionDB).where(PermissionDB.code == "users.view")
        users_view = (await session.execute(stmt)).scalar_one()
        parent_stmt = select(PermissionDB).where(PermissionDB.id == users_view.parent_id)
        parent = (await session.execute(parent_stmt)).scalar_one()
        assert parent.code == "users"
    await engine.dispose()


@pytest.mark.anyio
async def test_super_admin_role_gets_every_permission():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        await seed_rbac(session)
        role = (await session.execute(select(RoleDB).where(RoleDB.code == "super_admin"))).scalar_one()
        total_permissions = (await session.execute(select(func.count(PermissionDB.id)))).scalar_one()
        assigned = (
            await session.execute(
                select(func.count())
                .select_from(role_permissions_table)
                .where(role_permissions_table.c.role_id == role.id)
            )
        ).scalar_one()
        assert assigned == total_permissions
    await engine.dispose()


@pytest.mark.anyio
async def test_viewer_role_is_the_default_role():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        await seed_rbac(session)
        role = (await session.execute(select(RoleDB).where(RoleDB.code == "viewer"))).scalar_one()
        assert role.is_default is True
    await engine.dispose()


@pytest.mark.anyio
async def test_create_default_application_creates_once_then_skips():
    engine, session_factory = await _fresh_session_factory()
    async with session_factory() as session:
        result = await create_default_application(session, "Default App")
        assert result is not None
        application, raw_secret = result
        assert application.access_key
        assert raw_secret

        second = await create_default_application(session, "Default App")
        assert second is None

        total_apps = (await session.execute(select(func.count(ApplicationDB.id)))).scalar_one()
        assert total_apps == 1
    await engine.dispose()


@pytest.mark.anyio
async def test_bootstrap_end_to_end_is_idempotent(tmp_path):
    # A real temp file, not the shared-cache in-memory URL the other tests use above: `bootstrap`
    # disposes its own engine internally, which would drop a shared-cache in-memory database the
    # moment its only connection closes — a real file survives that the same way a real deployment
    # does.
    url = f"sqlite+aiosqlite:///{tmp_path / 'quickstart_test.db'}"
    await bootstrap(url, app_name="Bootstrap Test App")

    engine = db_module.create_engine(url)
    session_factory = db_module.create_session_factory(engine)
    async with session_factory() as session:
        total_permissions = (await session.execute(select(func.count(PermissionDB.id)))).scalar_one()
        total_roles = (await session.execute(select(func.count(RoleDB.id)))).scalar_one()
        total_apps = (await session.execute(select(func.count(ApplicationDB.id)))).scalar_one()
        assert total_permissions == len(DEFAULT_PERMISSIONS)
        assert total_roles == len(DEFAULT_ROLES)
        assert total_apps == 1
    await engine.dispose()

    # Re-running bootstrap against the same database creates nothing new.
    await bootstrap(url, app_name="Bootstrap Test App")
    engine = db_module.create_engine(url)
    session_factory = db_module.create_session_factory(engine)
    async with session_factory() as session:
        total_apps = (await session.execute(select(func.count(ApplicationDB.id)))).scalar_one()
        assert total_apps == 1
    await engine.dispose()


@pytest.mark.anyio
async def test_bootstrap_no_seed_no_app_only_creates_schema(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'quickstart_test_schema_only.db'}"
    await bootstrap(url, seed=False, create_app=False)

    engine = db_module.create_engine(url)
    session_factory = db_module.create_session_factory(engine)
    async with session_factory() as session:
        total_permissions = (await session.execute(select(func.count(PermissionDB.id)))).scalar_one()
        total_apps = (await session.execute(select(func.count(ApplicationDB.id)))).scalar_one()
        assert total_permissions == 0
        assert total_apps == 0
    await engine.dispose()
