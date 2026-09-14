"""
Parity_Group F — AIRS/1.0 (spec z_aud_3, task 9.1): the 12 endpoints of `spec/airs/AIRS-1.0.md`
§7, mounted under `{api_prefix}/ai/` exactly as the Django_Adapter mounts them (Annex A). Contract
extracted from `views/agent_views.py` (routing/response shapes), `services/agent_service.py`
(business logic), `middleware.py`'s `AgentAuthMiddleware` (the `AgentBearer` resolution + circuit
breaker gate that actually produces AIRS/1.0's coded error responses — see below), and the
normative spec itself, cited inline as `[AIRS-<LEVEL>-n]`.

**Permission validation is deliberately scoped down** — see `airs_service.py`'s module docstring
for the full rationale: the Reference_Stack has no RBAC tables yet (Group D ships after this
wave), so `[AIRS-CORE-2]`/`[AIRS-CORE-6]` are enforced via a `user.is_superuser` bypass only; a
non-superuser Delegating User is rejected for any permission it requests or exercises. This fails
closed (no security downgrade from Django) but means only a superuser can use AIRS's
permission-delegation feature in the Reference_Stack today.

**`AgentBearer` resolution is a route-local dependency here, not global middleware** — unlike
Django, where `AgentAuthMiddleware` intercepts every request site-wide (so an `AgentBearer` token
could, in principle, authenticate to any business endpoint an integrator gates with
`@require_agent_clearance`). The Reference_Stack has no other business endpoints for that to matter
against yet (Groups D/E), so `resolve_agent_token_async` below is invoked explicitly by the two
endpoints that need it (`heartbeat`, `report_usage`) rather than wired as app-wide middleware. It
reproduces the middleware's exact checks and error codes (`AIRS_DISABLED`, `AGENT_TOKEN_<reason>`,
`AGENT_TOKEN_SUSPENDED` with a `reason`), which Annex A documents as Tenxyte's chosen strings for
`[AIRS-CORE-16]`'s six conditions.

**Not replicated: Django's double-validation double-count.** Django's `AgentAuthMiddleware`
validates (and increments `current_request_count`) once, sets `request.agent_token`, then
`AgentTokenHeartbeatView`/`AgentTokenReportUsageView` ignore that and call
`AgentTokenService.validate()` again from scratch — so every real agent request to those two
endpoints increments the counter *twice*. This reads as an accidental side effect of dead code
(the view never reads `request.agent_token`), not a deliberate contract, and deliberately
replicating it would mean an intentionally-wrong request count. Each endpoint here calls
`resolve_agent_token_async` exactly once. No Conformance Suite test asserts an exact count, only
threshold-crossing, so this doesn't affect conformance — it just trips a configured threshold at
the count Guards were actually configured with, rather than half of it.

**Uncoded errors are real, not omissions.** Several Django responses here genuinely have no `code`
field at all (`AIRS is disabled`, `Application context required`, `Organization not found`, the
bare-`Authorization`-header and token/pk-mismatch checks on `heartbeat`/`report_usage`) — verified
directly from `agent_views.py`, not assumed. Built as raw `JSONResponse`s rather than through
`TenxyteAPIError` (which requires a `code`), for exact shape fidelity.

Organization scoping (`organization` field) is accepted and echoed back but never authorizes
anything (no `Organization` table exists yet — Group E) — a lookup against an always-empty table
still correctly 404s "Organization not found" for any slug a caller supplies, so this endpoint's
observable behavior doesn't silently diverge from Django's real behavior when Group E is genuinely
absent.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from tenxyte.adapters.fastapi import airs_service
from tenxyte.adapters.fastapi.airs_service import resolve_agent_token_async
from tenxyte.adapters.fastapi.deps import get_cache_service, get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import AgentPendingActionDB, AgentTokenDB, ApplicationDB
from tenxyte.adapters.fastapi.schemas import (
    AgentReportUsageRequest,
    AgentTokenCreateRequest,
    PendingActionTokenRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.cache_service import CacheService
from tenxyte.core.settings import Settings

router = APIRouter()


def _serialize_token(row: AgentTokenDB) -> dict:
    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "status": row.status,
        "expires_at": row.expires_at.isoformat(),
        "created_at": row.created_at.isoformat(),
        "organization": row.organization_id,
        "current_request_count": row.current_request_count,
    }


@router.get("/ai/tokens/")
async def list_agent_tokens(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    stmt = (
        select(AgentTokenDB)
        .where(AgentTokenDB.triggered_by_user_id == auth.user.id)
        .order_by(AgentTokenDB.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize_token(row) for row in rows]


@router.post("/ai/tokens/", status_code=201)
async def create_agent_token(
    body: AgentTokenCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    if not settings.airs_enabled:
        return JSONResponse({"error": "AIRS is disabled"}, status_code=400)

    application = getattr(request.state, "application", None)
    if application is None:
        stmt = select(ApplicationDB).where(ApplicationDB.is_active == True).limit(1)
        application = (await session.execute(stmt)).scalar_one_or_none()
        if application is None:
            return JSONResponse({"error": "Application context required"}, status_code=400)

    organization_slug = body.organization or request.headers.get("X-Org-Slug")
    organization_id = None
    if organization_slug:
        # No Organization table exists yet (Group E) — any slug is, correctly, not found.
        return JSONResponse({"error": "Organization not found"}, status_code=404)

    try:
        result = await airs_service.create_async(
            session,
            triggered_by=auth.user,
            application_id=application.id,
            agent_id=body.agent_id,
            granted_permissions=body.permissions,
            expires_in=body.expires_in,
            organization_id=organization_id,
            circuit_breaker=body.circuit_breaker,
            dead_mans_switch=body.dead_mans_switch,
            budget_limit_usd=body.budget_limit_usd,
            settings=settings,
        )
    except airs_service.PermissionCheckError as exc:
        raise TenxyteAPIError(str(exc), code="PERMISSION_DENIED", status_code=403) from exc

    return JSONResponse(
        {
            "id": result.row.id,
            "token": result.raw_token,
            "agent_id": result.row.agent_id,
            "status": result.row.status,
            "expires_at": result.row.expires_at.isoformat(),
        },
        status_code=201,
    )


@router.get("/ai/tokens/{pk}/")
async def get_agent_token(
    pk: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    row = await session.get(AgentTokenDB, pk)
    if row is None or row.triggered_by_user_id != auth.user.id:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return _serialize_token(row)


@router.post("/ai/tokens/{pk}/revoke/")
async def revoke_agent_token(
    pk: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    row = await session.get(AgentTokenDB, pk)
    if row is None or row.triggered_by_user_id != auth.user.id:
        return JSONResponse({"error": "Not found"}, status_code=404)

    await airs_service.revoke_async(session, row, revoked_by_user_id=auth.user.id)
    return {"status": "revoked"}


@router.post("/ai/tokens/{pk}/suspend/")
async def suspend_agent_token(
    pk: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    row = await session.get(AgentTokenDB, pk)
    if row is None or row.triggered_by_user_id != auth.user.id:
        return JSONResponse({"error": "Not found"}, status_code=404)

    await airs_service.suspend_async(session, row, airs_service.REASON_MANUAL)
    return {"status": "suspended"}


@router.post("/ai/tokens/revoke-all/")
async def revoke_all_agent_tokens(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    count = await airs_service.revoke_all_for_user_async(session, auth.user.id)
    return {"status": "revoked", "count": count}


@router.post("/ai/tokens/{pk}/heartbeat/")
async def agent_token_heartbeat(
    pk: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("AgentBearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    raw_token = auth_header[12:]
    row = await resolve_agent_token_async(session, raw_token, settings, cache_service)
    if str(row.id) != str(pk):
        return JSONResponse({"error": "Unauthorized or token mismatch"}, status_code=403)

    await airs_service.send_heartbeat_async(session, row)
    await airs_service.log_agent_action_async(
        session,
        agent_token=row,
        endpoint=request.url.path,
        prompt_trace_id=airs_service.sanitize_prompt_trace_id(request.headers.get("X-Prompt-Trace-ID")),
    )
    return {"status": "ok"}


@router.post("/ai/tokens/{pk}/report-usage/")
async def agent_token_report_usage(
    pk: str,
    body: AgentReportUsageRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("AgentBearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    raw_token = auth_header[12:]
    row = await resolve_agent_token_async(session, raw_token, settings, cache_service)
    if str(row.id) != str(pk):
        return JSONResponse({"error": "Unauthorized or token mismatch"}, status_code=403)

    success = await airs_service.report_usage_async(session, row, cost_usd=body.cost_usd, settings=settings)
    if not success:
        return JSONResponse({"error": "Budget exceeded", "status": "suspended"}, status_code=403)

    await airs_service.log_agent_action_async(
        session,
        agent_token=row,
        endpoint=request.url.path,
        prompt_trace_id=airs_service.sanitize_prompt_trace_id(request.headers.get("X-Prompt-Trace-ID")),
    )
    return {"status": "ok"}


@router.get("/ai/pending-actions/")
async def list_pending_actions(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    stmt = (
        select(AgentPendingActionDB)
        .join(AgentTokenDB, AgentPendingActionDB.agent_token_id == AgentTokenDB.id)
        .where(
            AgentTokenDB.triggered_by_user_id == auth.user.id,
            AgentPendingActionDB.confirmed_at.is_(None),
            AgentPendingActionDB.denied_at.is_(None),
            AgentPendingActionDB.expires_at > datetime.now(timezone.utc),
        )
        .order_by(AgentPendingActionDB.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()

    result = []
    for action in rows:
        agent_token = await session.get(AgentTokenDB, action.agent_token_id)
        result.append(
            {
                "id": action.id,
                "agent_id": agent_token.agent_id if agent_token else None,
                "permission": action.permission_requested,
                "endpoint": action.endpoint,
                "payload": action.payload,
                "confirmation_token": action.confirmation_token,
                "expires_at": action.expires_at.isoformat(),
                "created_at": action.created_at.isoformat(),
            }
        )
    return result


async def _resolve_pending_action_token(body_token: str, token: str | None) -> str | None:
    """Body takes precedence, path is a fallback — same precedence as Django's own
    `AgentPendingActionConfirmView`/`DenyView` (kept "for backward compatibility")."""
    return body_token or token or None


@router.post("/ai/pending-actions/{token}/confirm/")
async def confirm_pending_action(
    token: str,
    body: PendingActionTokenRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    confirmation_token = await _resolve_pending_action_token(body.token, token)
    if not confirmation_token:
        return JSONResponse({"error": "Token is required in the request body."}, status_code=400)

    action = await airs_service.confirm_pending_action_async(session, confirmation_token)
    if action is None:
        return JSONResponse({"error": "Invalid or expired token"}, status_code=400)

    agent_token = await session.get(AgentTokenDB, action.agent_token_id)
    if agent_token is None or agent_token.triggered_by_user_id != auth.user.id:
        return JSONResponse({"error": "Invalid or expired token"}, status_code=400)

    return {"status": "confirmed"}


@router.post("/ai/pending-actions/{token}/deny/")
async def deny_pending_action(
    token: str,
    body: PendingActionTokenRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    confirmation_token = await _resolve_pending_action_token(body.token, token)
    if not confirmation_token:
        return JSONResponse({"error": "Token is required in the request body."}, status_code=400)

    action = await airs_service.deny_pending_action_async(session, confirmation_token)
    if action is None:
        return JSONResponse({"error": "Invalid or expired token"}, status_code=400)

    agent_token = await session.get(AgentTokenDB, action.agent_token_id)
    if agent_token is None or agent_token.triggered_by_user_id != auth.user.id:
        return JSONResponse({"error": "Invalid or expired token"}, status_code=400)

    return {"status": "denied"}


def _endpoint_map(settings: Settings) -> dict:
    """[AIRS-DISC-1]'s `endpoints` map — hardcoded path templates under `settings.api_prefix`,
    matching the convention every other router in this adapter already uses (no dynamic route
    reversal is used anywhere in the Reference_Stack)."""
    base = f"{settings.api_prefix}/ai"
    return {
        "tokens": f"{base}/tokens/",
        "token_detail": f"{base}/tokens/{{id}}/",
        "token_revoke": f"{base}/tokens/{{id}}/revoke/",
        "token_suspend": f"{base}/tokens/{{id}}/suspend/",
        "token_revoke_all": f"{base}/tokens/revoke-all/",
        "heartbeat": f"{base}/tokens/{{id}}/heartbeat/",
        "report_usage": f"{base}/tokens/{{id}}/report-usage/",
        "pending_actions": f"{base}/pending-actions/",
        "pending_action_confirm": f"{base}/pending-actions/{{confirmation_token}}/confirm/",
        "pending_action_deny": f"{base}/pending-actions/{{confirmation_token}}/deny/",
        "discovery": f"{base}/.well-known/airs/",
    }


@router.get("/ai/.well-known/airs/")
async def airs_discovery(settings: Settings = Depends(get_settings)):  # noqa: B008
    """[AIRS-DISC-1]/[AIRS-DISC-2]/[AIRS-DISC-3]: unauthenticated, capabilities-only, identical
    for every caller under a given server configuration."""
    if not settings.airs_enabled:
        return JSONResponse({"error": "This feature is not enabled", "code": "FEATURE_DISABLED"}, status_code=404)

    conformance = ["core", "hitl", "trace"]
    if settings.airs_circuit_breaker_enabled:
        conformance.append("guards")
    if settings.airs_budget_tracking_enabled:
        conformance.append("budget")

    return {
        "airs_version": "1.0",
        "conformance": sorted(conformance),
        "endpoints": _endpoint_map(settings),
        "limits": {
            "token_max_lifetime": settings.airs_token_max_lifetime,
            "default_expiry": settings.airs_default_expiry,
        },
    }
