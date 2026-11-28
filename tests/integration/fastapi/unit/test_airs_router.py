"""
Tests for the Wave F AIRS router (spec z_aud_3, task 9.1) — the 12 endpoints of
`spec/airs/AIRS-1.0.md` §7 — against a real app, a real ephemeral aiosqlite database, and real
signed tokens (no mocks). Cross-referenced against the normative spec (`[AIRS-<LEVEL>-n]` cited
inline), not just against Django's implementation.
"""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import ApplicationDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def __init__(self, *, airs_enabled: bool = True, budget_tracking_enabled: bool = False):
        super().__init__()
        self._airs_enabled = airs_enabled
        self._budget_tracking_enabled = budget_tracking_enabled

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-airs-router-tests"
        if name == "TENXYTE_AIRS_ENABLED":
            return self._airs_enabled
        if name == "TENXYTE_AIRS_BUDGET_TRACKING_ENABLED":
            return self._budget_tracking_enabled
        return super().get(name, default)


def _build_app(**flags):
    settings = Settings(provider=_TestProvider(**flags))
    return create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_application(app) -> None:
    session_factory = app.state.tenxyte_session_factory
    async with session_factory() as session:
        session.add(ApplicationDB(name="Test App", access_key=str(uuid.uuid4()), access_secret="hashed"))
        await session.commit()


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


def _full_scope_token(app, user: User) -> str:
    """Mints a full-scope access token directly (bypassing `/login/email/`) — a superuser with no
    2FA configured would otherwise get the `2fa_setup_only` bootstrap token on real login, which
    `require_jwt()` (bare) rejects; see `routers/auth.py`'s `_login()`."""
    return app.state.tenxyte_jwt_service.generate_new_token_pair(user_id=user.id, application_id="default").access_token


async def _issue_agent_token(client, headers, **extra) -> dict:
    payload = {"agent_id": "conformance-bot", "permissions": ["read:reports"], **extra}
    response = await client.post("/api/v1/ai/tokens/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_discovery_reports_conformance_and_limits():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/ai/.well-known/airs/")

    assert response.status_code == 200
    body = response.json()
    assert body["airs_version"] == "1.0"
    # [AIRS-CORE-19]: core is always present; hitl/trace are unconditional; guards/budget follow
    # their own settings (circuit_breaker defaults on, budget_tracking defaults off).
    assert set(body["conformance"]) == {"core", "hitl", "trace", "guards"}
    assert body["endpoints"]["tokens"] == "/api/v1/ai/tokens/"
    assert body["limits"]["token_max_lifetime"] == 86400
    assert body["limits"]["default_expiry"] == 3600


@pytest.mark.anyio
async def test_discovery_disabled_is_404_feature_disabled():
    """[AIRS-DISC-3]."""
    app = _build_app(airs_enabled=False)
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.get("/api/v1/ai/.well-known/airs/")

    assert response.status_code == 404
    assert response.json() == {"error": "This feature is not enabled", "code": "FEATURE_DISABLED"}


@pytest.mark.anyio
async def test_discovery_identical_regardless_of_caller():
    """[AIRS-DISC-2]: unauthenticated and authenticated callers get byte-identical bodies."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="disco@example.com")
        async with await _client(app) as client:
            anon = await client.get("/api/v1/ai/.well-known/airs/")
            authed = await client.get(
                "/api/v1/ai/.well-known/airs/", headers={"Authorization": f"Bearer {_full_scope_token(app, user)}"}
            )

    assert anon.json() == authed.json()


@pytest.mark.anyio
async def test_create_success_returns_raw_token_once():
    """[AIRS-CORE-14]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="super@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            body = await _issue_agent_token(client, headers)

    assert body["status"] == "ACTIVE"
    assert body["token"]
    assert "id" in body
    assert "expires_at" in body


@pytest.mark.anyio
async def test_raw_token_not_retransmitted_on_detail_fetch():
    """[AIRS-CORE-12]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="super2@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            detail = await client.get(f"/api/v1/ai/tokens/{issued['id']}/", headers=headers)

    assert detail.status_code == 200
    assert issued["token"] not in str(detail.json())


@pytest.mark.anyio
async def test_create_requires_explicit_permissions_by_default():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="super3@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            response = await client.post("/api/v1/ai/tokens/", json={"agent_id": "bot"}, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.anyio
async def test_create_rejects_non_superuser_requesting_permission():
    """[AIRS-CORE-2]: the Reference_Stack's scoped-down version (superuser bypass only, see
    airs_service.py's module docstring) — a non-superuser can never be verified to hold a
    permission without RBAC tables, so issuance is rejected, not silently accepted."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="regular@example.com", is_superuser=False)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/ai/tokens/", json={"agent_id": "bot", "permissions": ["read:reports"]}, headers=headers
            )

    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.anyio
async def test_create_airs_disabled_uncoded_400():
    """Real Django quirk, not an omission: `{"error": "AIRS is disabled"}` has no `code` field —
    verified directly from `views/agent_views.py`."""
    app = _build_app(airs_enabled=False)
    async with app.router.lifespan_context(app):
        user = await _create_user(app, email="super4@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/ai/tokens/", json={"agent_id": "bot", "permissions": ["x"]}, headers=headers
            )

    assert response.status_code == 400
    assert response.json() == {"error": "AIRS is disabled"}


@pytest.mark.anyio
async def test_create_requires_application_context():
    app = _build_app()
    async with app.router.lifespan_context(app):
        # No ApplicationDB row seeded.
        user = await _create_user(app, email="super5@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/ai/tokens/", json={"agent_id": "bot", "permissions": ["x"]}, headers=headers
            )

    assert response.status_code == 400
    assert response.json() == {"error": "Application context required"}


@pytest.mark.anyio
async def test_create_unknown_organization_404():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="super6@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            response = await client.post(
                "/api/v1/ai/tokens/",
                json={"agent_id": "bot", "permissions": ["x"], "organization": "does-not-exist"},
                headers=headers,
            )

    assert response.status_code == 404
    assert response.json() == {"error": "Organization not found"}


@pytest.mark.anyio
async def test_list_and_detail_scoped_to_owner():
    """[AIRS-CORE-15]-adjacent: a user cannot see another user's tokens."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        owner = await _create_user(app, email="owner@example.com", is_superuser=True)
        other = await _create_user(app, email="other@example.com", is_superuser=True)
        owner_headers = {"Authorization": f"Bearer {_full_scope_token(app, owner)}"}
        other_headers = {"Authorization": f"Bearer {_full_scope_token(app, other)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, owner_headers)

            other_list = await client.get("/api/v1/ai/tokens/", headers=other_headers)
            other_detail = await client.get(f"/api/v1/ai/tokens/{issued['id']}/", headers=other_headers)
            owner_list = await client.get("/api/v1/ai/tokens/", headers=owner_headers)

    assert other_list.json() == []
    assert other_detail.status_code == 404
    assert other_detail.json() == {"error": "Not found"}
    assert len(owner_list.json()) == 1


@pytest.mark.anyio
async def test_revocation_is_human_only():
    """[AIRS-CORE-15]: revocation authenticates as the Delegating User, not the agent."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="revoker@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(f"/api/v1/ai/tokens/{issued['id']}/revoke/", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "revoked"}


@pytest.mark.anyio
async def test_revoke_all_counts_active_tokens():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="nuke@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            await _issue_agent_token(client, headers, agent_id="bot-a")
            await _issue_agent_token(client, headers, agent_id="bot-b")
            response = await client.post("/api/v1/ai/tokens/revoke-all/", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "revoked", "count": 2}


@pytest.mark.anyio
async def test_terminal_conditions_yield_pairwise_distinct_codes():
    """[AIRS-CORE-16]: not-found / suspended / revoked / expired must be pairwise distinguishable
    — same property the AIRS Conformance Suite's `test_terminal_conditions_yield_pairwise_distinct_codes`
    checks black-box."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="terminal@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            revoked = await _issue_agent_token(client, headers, agent_id="revoked-bot")
            await client.post(f"/api/v1/ai/tokens/{revoked['id']}/revoke/", headers=headers)

            suspended = await _issue_agent_token(client, headers, agent_id="suspended-bot")
            await client.post(f"/api/v1/ai/tokens/{suspended['id']}/suspend/", headers=headers)

            expired = await _issue_agent_token(client, headers, agent_id="expired-bot", expires_in=1)
            await asyncio.sleep(2)

            async def code_for(raw_token: str, token_id: str) -> str:
                resp = await client.post(
                    f"/api/v1/ai/tokens/{token_id}/heartbeat/", headers={"Authorization": f"AgentBearer {raw_token}"}
                )
                assert 400 <= resp.status_code < 500
                return resp.json()["code"]

            codes = {
                "not_found": await code_for("not-a-real-token", "00000000-0000-0000-0000-000000000000"),
                "revoked": await code_for(revoked["token"], revoked["id"]),
                "suspended": await code_for(suspended["token"], suspended["id"]),
                "expired": await code_for(expired["token"], expired["id"]),
            }

    assert len(set(codes.values())) == len(codes), codes
    assert codes["revoked"] == "AGENT_TOKEN_STATUS_REVOKED"
    assert codes["suspended"] == "AGENT_TOKEN_STATUS_SUSPENDED"


@pytest.mark.anyio
async def test_heartbeat_requires_agentbearer_prefix():
    app = _build_app()
    async with app.router.lifespan_context(app), await _client(app) as client:
        response = await client.post(
            "/api/v1/ai/tokens/some-id/heartbeat/", headers={"Authorization": "Bearer not-agent-scheme"}
        )
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.anyio
async def test_heartbeat_token_id_mismatch_uncoded_403():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="mismatch@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(
                "/api/v1/ai/tokens/not-the-real-id/heartbeat/",
                headers={"Authorization": f"AgentBearer {issued['token']}"},
            )

    assert response.status_code == 403
    assert response.json() == {"error": "Unauthorized or token mismatch"}


@pytest.mark.anyio
async def test_circuit_breaker_rpm_threshold_suspends_token():
    """[AIRS-GUARDS-1]/[AIRS-GUARDS-2]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="guards@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers, circuit_breaker={"max_requests_per_minute": 2})
            agent_headers = {"Authorization": f"AgentBearer {issued['token']}"}

            statuses = []
            for _ in range(6):
                resp = await client.post(f"/api/v1/ai/tokens/{issued['id']}/heartbeat/", headers=agent_headers)
                statuses.append(resp.status_code)

    assert 403 in statuses


@pytest.mark.anyio
async def test_heartbeat_missing_suspends_token():
    """[AIRS-GUARDS-3]/[AIRS-GUARDS-4]."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="dms@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers, dead_mans_switch={"heartbeat_required_every": 1})
            await asyncio.sleep(2.5)
            response = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/heartbeat/",
                headers={"Authorization": f"AgentBearer {issued['token']}"},
            )

    assert response.status_code == 403
    assert response.json()["code"] == "AGENT_TOKEN_HEARTBEAT_MISSING"


@pytest.mark.anyio
async def test_budget_tracking_disabled_by_default_always_accepts():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="nobudget@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers, budget_limit_usd=0.01)
            response = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/report-usage/",
                json={"cost_usd": 100.0},
                headers={"Authorization": f"AgentBearer {issued['token']}"},
            )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_budget_exceeded_suspends_and_rejects_further_use():
    """[AIRS-BUDGET-2]/[AIRS-BUDGET-3]."""
    app = _build_app(budget_tracking_enabled=True)
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="budget@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers, budget_limit_usd=1.0)
            agent_headers = {"Authorization": f"AgentBearer {issued['token']}"}

            under = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/report-usage/", json={"cost_usd": 0.6}, headers=agent_headers
            )
            over = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/report-usage/", json={"cost_usd": 0.6}, headers=agent_headers
            )
            further = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/report-usage/", json={"cost_usd": 0.0}, headers=agent_headers
            )

    assert under.status_code == 200
    assert over.status_code == 403
    assert over.json() == {"error": "Budget exceeded", "status": "suspended"}
    assert further.status_code == 403


@pytest.mark.anyio
async def test_hitl_confirm_and_deny_lifecycle():
    """[AIRS-HITL-3] through [AIRS-HITL-6], exercised directly against `airs_service` (no
    `@require_agent_clearance`-gated demo endpoint exists in the Reference_Stack yet — see
    routers/airs.py's module docstring; the full black-box HITL contract is exercised by the AIRS
    Conformance Suite once task 9.2 wires up a probe endpoint)."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="hitl@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}

        from tenxyte.adapters.fastapi import airs_service
        from tenxyte.adapters.fastapi.models_sa import AgentTokenDB

        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)

            session_factory = app.state.tenxyte_session_factory
            async with session_factory() as session:
                token_row = await session.get(AgentTokenDB, issued["id"])
                pending = await airs_service.create_pending_action_async(
                    session, agent_token=token_row, permission="read:reports", endpoint="/demo/", payload={}
                )

            listing = await client.get("/api/v1/ai/pending-actions/", headers=headers)
            assert listing.status_code == 200
            assert len(listing.json()) == 1
            assert listing.json()[0]["confirmation_token"] == pending.confirmation_token

            confirm = await client.post(
                f"/api/v1/ai/pending-actions/{pending.confirmation_token}/confirm/",
                json={"token": pending.confirmation_token},
                headers=headers,
            )
            assert confirm.status_code == 200
            assert confirm.json() == {"status": "confirmed"}

            confirm_again = await client.post(
                f"/api/v1/ai/pending-actions/{pending.confirmation_token}/confirm/",
                json={"token": pending.confirmation_token},
                headers=headers,
            )
            assert confirm_again.status_code == 400

            listing_after = await client.get("/api/v1/ai/pending-actions/", headers=headers)

    assert listing_after.json() == []


@pytest.mark.anyio
async def test_pending_action_deny_prevents_confirm():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="deny@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}

        from tenxyte.adapters.fastapi import airs_service
        from tenxyte.adapters.fastapi.models_sa import AgentTokenDB

        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            session_factory = app.state.tenxyte_session_factory
            async with session_factory() as session:
                token_row = await session.get(AgentTokenDB, issued["id"])
                pending = await airs_service.create_pending_action_async(
                    session, agent_token=token_row, permission="read:reports", endpoint="/demo/", payload={}
                )

            deny = await client.post(
                f"/api/v1/ai/pending-actions/{pending.confirmation_token}/deny/",
                json={"token": pending.confirmation_token},
                headers=headers,
            )
            assert deny.status_code == 200
            assert deny.json() == {"status": "denied"}

            confirm_after_deny = await client.post(
                f"/api/v1/ai/pending-actions/{pending.confirmation_token}/confirm/",
                json={"token": pending.confirmation_token},
                headers=headers,
            )

    assert confirm_after_deny.status_code == 400


@pytest.mark.anyio
async def test_wellformed_and_malformed_trace_id_never_break_a_request():
    """[AIRS-TRACE-2]: a trace ID (well-formed or not) must never affect the outcome."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="trace@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            agent_headers = {"Authorization": f"AgentBearer {issued['token']}"}

            well_formed = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/heartbeat/",
                headers={**agent_headers, "X-Prompt-Trace-ID": f"trace-{uuid.uuid4().hex}"},
            )
            malformed = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/heartbeat/",
                headers={**agent_headers, "X-Prompt-Trace-ID": "not a valid id! spaces & punctuation"},
            )

    assert well_formed.status_code == 200
    assert malformed.status_code == 200


@pytest.mark.anyio
async def test_wellformed_trace_id_is_durably_persisted():
    """[AIRS-TRACE-3]: earns the `trace` Conformance Level claim for real — a well-formed trace ID
    on a successful mutation must be retrievable via internal tooling (`AgentActionLogDB` here;
    see its docstring), not merely accepted-and-discarded."""
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="trace-persist@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        trace_id = f"trace-{uuid.uuid4().hex}"
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/heartbeat/",
                headers={"Authorization": f"AgentBearer {issued['token']}", "X-Prompt-Trace-ID": trace_id},
            )
            assert response.status_code == 200

        from sqlalchemy import select

        from tenxyte.adapters.fastapi.models_sa import AuditLogDB

        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            row = (
                await session.execute(select(AuditLogDB).where(AuditLogDB.prompt_trace_id == trace_id))
            ).scalar_one_or_none()

    assert row is not None
    assert row.agent_token_id == issued["id"]
    assert row.action == "agent_action"


@pytest.mark.anyio
async def test_malformed_trace_id_is_not_persisted():
    app = _build_app()
    async with app.router.lifespan_context(app):
        await _seed_application(app)
        user = await _create_user(app, email="trace-malformed@example.com", is_superuser=True)
        headers = {"Authorization": f"Bearer {_full_scope_token(app, user)}"}
        async with await _client(app) as client:
            issued = await _issue_agent_token(client, headers)
            response = await client.post(
                f"/api/v1/ai/tokens/{issued['id']}/heartbeat/",
                headers={
                    "Authorization": f"AgentBearer {issued['token']}",
                    "X-Prompt-Trace-ID": "not a valid id! spaces & punctuation",
                },
            )
            assert response.status_code == 200

        from sqlalchemy import select

        from tenxyte.adapters.fastapi.models_sa import AuditLogDB

        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            rows = (
                (await session.execute(select(AuditLogDB).where(AuditLogDB.agent_token_id == issued["id"])))
                .scalars()
                .all()
            )

    assert rows == []
