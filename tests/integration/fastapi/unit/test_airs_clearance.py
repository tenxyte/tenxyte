"""
Tests for `airs_clearance.require_agent_clearance` (spec z_aud_3, task 9.2) — the FastAPI
equivalent of `tenxyte.decorators.require_agent_clearance`, exercised here against the same demo
probe router the AIRS Conformance Suite's ephemeral FastAPI instance mounts
(`spec/airs/conformance/tenxyte_ci_fastapi/demo_views.py`), the FastAPI mirror of Django's own
`tenxyte_ci/demo_views.py`. No mocks; a real app, a real ephemeral aiosqlite database, real signed
tokens.
"""

import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import ApplicationDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

# The demo probe router lives under spec/ (not src/tenxyte) since it's CI/conformance-testing
# infrastructure, not adapter code — same split as Django's tenxyte_ci/demo_views.py. Reused here
# (rather than duplicated) so both this suite and the Conformance Suite's ephemeral server exercise
# the exact same router.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from spec.airs.conformance.tenxyte_ci_fastapi.demo_views import (
    CONFORMANCE_PROBE_PERMISSION as TEST_PERMISSION,
)
from spec.airs.conformance.tenxyte_ci_fastapi.demo_views import router as _demo_router


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-airs-clearance-tests"
        return super().get(name, default)


def _build_app():
    settings = Settings(provider=_TestProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())
    app.include_router(_demo_router, prefix=settings.api_prefix)
    return app


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_application(app) -> None:
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        session.add(ApplicationDB(name="Test App", access_key=str(uuid.uuid4()), access_secret="hashed"))
        await session.commit()


async def _create_superuser(app, *, email: str) -> User:
    session_factory = app.state.tenxyte_session_factory
    password_hash = hash_password("correct-horse-battery-staple")
    async with session_factory() as session:
        repo = SQLAlchemyAsyncUserRepository(session)
        return await repo.create(
            User(id=str(uuid.uuid4()), email=email, password_hash=password_hash, is_active=True, is_superuser=True)
        )


def _full_scope_token(app, user: User) -> str:
    return app.state.tenxyte_jwt_service.generate_new_token_pair(user_id=user.id, application_id="default").access_token


async def _issue_agent_token(client, headers, permissions=None) -> dict:
    payload = {"agent_id": "conformance-bot", "permissions": [TEST_PERMISSION] if permissions is None else permissions}
    response = await client.post("/api/v1/ai/tokens/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_human_request_passes_through_unconditionally():
    """No `AgentBearer` scheme at all — the same "not an agent request" pass-through Django's
    decorator gives a plain human/unauthenticated caller."""
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/ai/_conformance_probe/")
    assert response.status_code == 200
    assert response.json() == {"executed": True}


@pytest.mark.anyio
async def test_valid_agent_bearer_with_permission_executes():
    """[AIRS-CORE-11]/[AIRS-CORE-13]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance1@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.get(
                "/api/v1/ai/_conformance_probe/", headers={"Authorization": f"AgentBearer {issued['token']}"}
            )

    assert response.status_code == 200
    assert response.json() == {"executed": True}


@pytest.mark.anyio
async def test_garbage_agent_bearer_rejected():
    """[AIRS-CORE-16] condition 1."""
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get(
            "/api/v1/ai/_conformance_probe/", headers={"Authorization": "AgentBearer not-a-real-token"}
        )
    assert 400 <= response.status_code < 500
    assert response.json()["code"] == "AGENT_TOKEN_NOT_FOUND"


@pytest.mark.anyio
async def test_permission_absent_from_grant_rejected():
    """[AIRS-CORE-6](a): Double Validation's grant-scope check."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance2@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers, permissions=["some.other.permission"])
            response = await client.get(
                "/api/v1/ai/_conformance_probe/", headers={"Authorization": f"AgentBearer {issued['token']}"}
            )

    assert response.status_code == 403
    assert response.json()["code"] == "AGENT_PERMISSION_DENIED"


@pytest.mark.anyio
async def test_revoked_token_rejected():
    """[AIRS-CORE-9]/[AIRS-CORE-16] condition 3."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance3@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            await client.post(f"/api/v1/ai/tokens/{issued['id']}/revoke/", headers=headers)
            response = await client.get(
                "/api/v1/ai/_conformance_probe/", headers={"Authorization": f"AgentBearer {issued['token']}"}
            )

    assert 400 <= response.status_code < 500
    assert response.json()["code"] == "AGENT_TOKEN_STATUS_REVOKED"


@pytest.mark.anyio
async def test_hitl_returns_202_pending_confirmation():
    """[AIRS-HITL-3]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance4@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(
                "/api/v1/ai/_hitl_probe/", headers={"Authorization": f"AgentBearer {issued['token']}"}, json={}
            )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending_confirmation"
    assert body["confirmation_token"]
    assert body["expires_at"]


@pytest.mark.anyio
async def test_hitl_confirm_then_replay_executes():
    """[AIRS-HITL-5]/[AIRS-HITL-6]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance5@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            agent_headers = {"Authorization": f"AgentBearer {issued['token']}"}

            pending = await client.post("/api/v1/ai/_hitl_probe/", headers=agent_headers, json={})
            confirmation_token = pending.json()["confirmation_token"]

            confirm = await client.post(
                f"/api/v1/ai/pending-actions/{confirmation_token}/confirm/",
                json={"token": confirmation_token},
                headers=headers,
            )
            assert confirm.status_code == 200

            replay_headers = {**agent_headers, "X-Action-Confirmation": confirmation_token}
            replay = await client.post("/api/v1/ai/_hitl_probe/", headers=replay_headers, json={})

    assert replay.status_code == 200
    assert replay.json() == {"executed": True}


@pytest.mark.anyio
async def test_hitl_deny_then_replay_does_not_execute():
    """[AIRS-HITL-5]/[AIRS-HITL-6]: a denied action's Confirmation Token must not authorize
    execution — the replay MUST NOT return the "executed" success shape (it MAY come back as a
    fresh 202, since there's no confirmed record for that token)."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance6@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            agent_headers = {"Authorization": f"AgentBearer {issued['token']}"}

            pending = await client.post("/api/v1/ai/_hitl_probe/", headers=agent_headers, json={})
            confirmation_token = pending.json()["confirmation_token"]

            deny = await client.post(
                f"/api/v1/ai/pending-actions/{confirmation_token}/deny/",
                json={"token": confirmation_token},
                headers=headers,
            )
            assert deny.status_code == 200

            replay_headers = {**agent_headers, "X-Action-Confirmation": confirmation_token}
            replay = await client.post("/api/v1/ai/_hitl_probe/", headers=replay_headers, json={})

    assert replay.status_code != 200


@pytest.mark.anyio
async def test_hitl_unconfirmed_replay_does_not_execute():
    """[AIRS-HITL-6]: a bogus/never-confirmed `X-Action-Confirmation` must not execute."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_superuser(app, email="clearance7@example.com")
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(
                "/api/v1/ai/_hitl_probe/",
                headers={"Authorization": f"AgentBearer {issued['token']}", "X-Action-Confirmation": "never-confirmed"},
                json={},
            )

    assert response.status_code != 200
