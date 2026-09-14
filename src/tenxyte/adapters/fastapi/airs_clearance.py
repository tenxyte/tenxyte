"""
`require_agent_clearance`-equivalent for the Reference_Stack (spec z_aud_3, Wave F, task 9.2) —
protects an arbitrary *business* endpoint against Agent Token callers, mirroring
`tenxyte.decorators.require_agent_clearance`. AIRS's actual value (a permission-gated business
action) is provided by integrator code applying this dependency, not by a fixed AIRS REST
endpoint — `routers/airs.py` itself never uses it. Its only consumer in this repository is the
AIRS Conformance Suite's demo probe endpoints (`spec/airs/conformance/tenxyte_ci_fastapi/`),
mirroring Django's own `spec/airs/conformance/tenxyte_ci/demo_views.py`.

Only gates AGENT (`AgentBearer`) callers — a request with no `AgentBearer` scheme (including a
plain human `Bearer <jwt>`, or no `Authorization` header at all) passes through unconditionally,
exactly like Django's decorator: it only ever inspects `request.agent_token`, which
`AgentAuthMiddleware` sets solely for `AgentBearer` requests, and does nothing at all otherwise.
This dependency resolves the `AgentBearer` token itself instead (see `airs_service.
resolve_agent_token_async`'s docstring for why the Reference_Stack has no equivalent global
middleware to rely on).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, Request
from tenxyte.adapters.fastapi import airs_service
from tenxyte.adapters.fastapi.deps import get_cache_service, get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import AgentClearancePending, TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import AgentPendingActionDB, AgentTokenDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.cache_service import CacheService
from tenxyte.core.settings import Settings


@dataclass
class AgentClearance:
    """What a route gets after `require_agent_clearance()` lets the request through.
    `agent_token` is `None` for a human (or unauthenticated-as-agent) caller — same "pass through
    unconditionally" semantics as Django's decorator for a non-agent request."""

    agent_token: AgentTokenDB | None


def require_agent_clearance(
    permission_code: str | None = None, *, human_in_the_loop_required: bool = False
) -> Callable[..., Coroutine[Any, Any, AgentClearance]]:
    async def _dependency(
        request: Request,
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
        settings: Settings = Depends(get_settings),  # noqa: B008
        cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
    ) -> AgentClearance:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("AgentBearer "):
            return AgentClearance(agent_token=None)

        raw_token = auth_header[12:]
        agent_token = await airs_service.resolve_agent_token_async(session, raw_token, settings, cache_service)

        if permission_code:
            user_repo = SQLAlchemyAsyncUserRepository(session)
            delegating_user = await user_repo.get_by_id(agent_token.triggered_by_user_id)
            if delegating_user is None or not airs_service.validate_permission(
                agent_token, permission_code, delegating_user, settings
            ):
                raise TenxyteAPIError(
                    f"Agent insufficient permissions: {permission_code}",
                    code="AGENT_PERMISSION_DENIED",
                    status_code=403,
                )

        is_hitl_required = human_in_the_loop_required
        if permission_code and permission_code in settings.airs_confirmation_required:
            is_hitl_required = True

        if is_hitl_required:
            confirmation_header = request.headers.get("X-Action-Confirmation")
            if confirmation_header:
                stmt = select(AgentPendingActionDB).where(
                    AgentPendingActionDB.confirmation_token == confirmation_header,
                    AgentPendingActionDB.agent_token_id == agent_token.id,
                    AgentPendingActionDB.confirmed_at.is_not(None),
                )
                confirmed_action = (await session.execute(stmt)).scalar_one_or_none()
                if confirmed_action is not None:
                    # [AIRS-HITL-7]: confirmation isn't consumed after one replay — every other
                    # applicable check (already run above: token status, Double Validation) still
                    # applies on each replay, it's just not re-created as a new Pending Action.
                    return AgentClearance(agent_token=agent_token)

            payload: dict = {}
            if request.method in ("POST", "PUT", "PATCH"):
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        payload = json.loads(body_bytes)
                    except ValueError:
                        payload = {}

            pending = await airs_service.create_pending_action_async(
                session,
                agent_token=agent_token,
                permission=permission_code or "unknown",
                endpoint=request.url.path,
                payload=payload,
                prompt_trace_id=airs_service.sanitize_prompt_trace_id(request.headers.get("X-Prompt-Trace-ID")),
            )
            raise AgentClearancePending(pending.confirmation_token, pending.expires_at.isoformat())

        return AgentClearance(agent_token=agent_token)

    return _dependency
