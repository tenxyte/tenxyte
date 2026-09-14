"""
Framework-agnostic-in-spirit AIRS/1.0 service for the Reference_Stack (spec z_aud_3, Wave F, task
9.1) — a from-scratch equivalent of `tenxyte.services.agent_service.AgentTokenService`. Like
`otp_service.py`, this isn't a "reimplementation avoiding a Django import": Django has never
extracted AIRS to Core (it's 100% ORM-coupled — `models/agent.py`, `services/agent_service.py`,
`decorators.py`, `middleware.py`), so there's no portable original to diverge from. This is a new
implementation, verified against both Django's actual (not documented) behavior AND the normative
wire protocol it implements, `spec/airs/AIRS-1.0.md` — cited inline as `[AIRS-<LEVEL>-n]`.

**The one deliberate, documented divergence from Django: permission validation.**
[AIRS-CORE-2]/[AIRS-CORE-6] require verifying that the Delegating User genuinely holds each
permission being granted or exercised. Django does this via full RBAC (roles, hierarchical
permissions, direct grants — `User.has_permission`/`has_org_permission`, ~30 lines of query logic
in `models/auth.py`). The Reference_Stack has no permission/role tables yet (Group D, task 10.1,
which per the spec's own A→B→C→F→D→E→G ordering ships *after* this wave) — there is nothing to
validate a non-superuser's permissions against.

Rather than silently accepting any requested permission (a real security downgrade from Django) or
blocking this entire wave on Group D, the chosen scope (confirmed by the maintainer) is: a
`User.is_superuser` bypass — mirroring the one RBAC short-circuit that already exists on the Core
`User` port dataclass and that Django's own `has_permission()` checks first anyway — and a hard
reject for everyone else. This is honest and fails closed: every AIRS security guarantee
([AIRS-CORE-1] through [AIRS-CORE-9]) still holds, it's just that only a superuser can
successfully exercise the permission-delegation feature until Group D ships. `PermissionCheckError`
below carries this distinction in its message; `validate_permission`'s docstring repeats it.

Organization scoping (`organization_id`) is accepted and echoed back for round-trip fidelity but
never used to authorize anything — same reasoning: no `Organization` table exists yet (Group E).
"""

from __future__ import annotations

import hashlib
import re
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import AgentActionLogDB, AgentPendingActionDB, AgentTokenDB
from tenxyte.core.cache_service import CacheService
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

# [AIRS-TRACE-2]: opaque string, at most 128 characters, restricted to [A-Za-z0-9_-].
_PROMPT_TRACE_ID_PATTERN = re.compile(r"^[\w\-]{1,128}$")

# AIRS/1.0 §3 — the four statuses an Agent Token may hold.
STATUS_ACTIVE = "ACTIVE"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_REVOKED = "REVOKED"
STATUS_EXPIRED = "EXPIRED"

# AIRS/1.0 [AIRS-CORE-7] — the fixed five-value Suspension Reason vocabulary.
REASON_RATE_LIMIT = "RATE_LIMIT"
REASON_ANOMALY = "ANOMALY"
REASON_MANUAL = "MANUAL"
REASON_HEARTBEAT_MISSING = "HEARTBEAT_MISSING"
REASON_BUDGET_EXCEEDED = "BUDGET_EXCEEDED"

_HITL_PENDING_ACTION_LIFETIME_MINUTES = 10


class PermissionCheckError(Exception):
    """Raised by `create_async`/`validate_permission` — maps to `PERMISSION_DENIED`/
    `AGENT_PERMISSION_DENIED` at the router layer, never a 500."""


def _generate_token() -> str:
    """48-character random token — same alphabet and length as Django's `_generate_token`."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(48))


def _generate_confirmation_token() -> str:
    return secrets.token_urlsafe(64)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def sanitize_prompt_trace_id(raw: str | None) -> str | None:
    """[AIRS-TRACE-2]: a malformed value is silently discarded (treated as absent), never
    rejected — matches `middleware.py`'s own `re.match` validation exactly."""
    if not raw or not _PROMPT_TRACE_ID_PATTERN.match(raw):
        return None
    return raw


async def log_agent_action_async(
    session: AsyncSession, *, agent_token: AgentTokenDB, endpoint: str, prompt_trace_id: str | None
) -> None:
    """[AIRS-TRACE-3]: persists a well-formed Prompt Trace ID for a successful, state-changing
    Agent Token request — a no-op when `prompt_trace_id` is absent/malformed, matching Django's
    own "don't persist a null trace id" posture. See `AgentActionLogDB`'s docstring."""
    if prompt_trace_id is None:
        return
    session.add(AgentActionLogDB(agent_token_id=agent_token.id, endpoint=endpoint, prompt_trace_id=prompt_trace_id))
    await session.commit()


def _as_aware(dt: datetime) -> datetime:
    """DB-loaded datetimes come back tz-naive from the aiosqlite dev driver, even though we always
    write tz-aware UTC values — normalize before comparing against `datetime.now(tz=...)`."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class CreateResult:
    row: AgentTokenDB
    raw_token: str


async def create_async(
    session: AsyncSession,
    *,
    triggered_by: User,
    application_id: str | None,
    agent_id: str,
    granted_permissions: list[str],
    expires_in: int | None,
    organization_id: str | None,
    circuit_breaker: dict | None,
    dead_mans_switch: dict | None,
    budget_limit_usd: float | None,
    settings: Settings,
) -> CreateResult:
    """[AIRS-CORE-14]: issues a new Agent Token for `triggered_by`. Raises `PermissionCheckError`
    if [AIRS-CORE-2] (issuance-time permission validation) fails — see module docstring for the
    Reference_Stack's scoped-down (superuser-only) version of that check."""
    if settings.airs_require_explicit_permissions and not granted_permissions:
        raise PermissionCheckError("Agent tokens must request explicit permissions.")

    for perm_code in granted_permissions:
        if not triggered_by.is_superuser:
            raise PermissionCheckError(
                f"User does not have permission '{perm_code}' "
                "(Reference_Stack has no RBAC tables yet — only a superuser can delegate "
                "permissions to an Agent Token until Group D ships; see module docstring)."
            )

    expires_in = min(
        expires_in if expires_in is not None else settings.airs_default_expiry, settings.airs_token_max_lifetime
    )

    cb_kwargs: dict = {}
    if circuit_breaker:
        for key in ("max_requests_per_minute", "max_requests_total", "max_failed_requests"):
            if key in circuit_breaker:
                cb_kwargs[key] = circuit_breaker[key]

    dms_kwargs: dict = {}
    if dead_mans_switch and "heartbeat_required_every" in dead_mans_switch:
        dms_kwargs["heartbeat_required_every"] = dead_mans_switch["heartbeat_required_every"]
        dms_kwargs["last_heartbeat_at"] = datetime.now(timezone.utc)

    raw_token = _generate_token()
    row = AgentTokenDB(
        token_hash=_hash_token(raw_token),
        agent_id=agent_id,
        triggered_by_user_id=triggered_by.id,
        application_id=application_id,
        organization_id=organization_id,
        granted_permissions=list(granted_permissions),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        budget_limit_usd=Decimal(str(budget_limit_usd)) if budget_limit_usd is not None else None,
        **cb_kwargs,
        **dms_kwargs,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return CreateResult(row=row, raw_token=raw_token)


async def validate_async(session: AsyncSession, raw_token: str) -> tuple[AgentTokenDB | None, str | None]:
    """[AIRS-CORE-9]/[AIRS-CORE-16]: validates a raw Agent Token, returning `(row, error_code)` —
    `error_code` is `None` on success. Mirrors Django's `AgentTokenService.validate` exactly,
    including its side effects (marking a lazily-detected expiry, suspending on missed heartbeat,
    bumping `current_request_count`/`last_used_at` atomically on success)."""
    stmt = select(AgentTokenDB).where(AgentTokenDB.token_hash == _hash_token(raw_token))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None, "NOT_FOUND"

    if row.status != STATUS_ACTIVE:
        return row, f"STATUS_{row.status}"

    if _as_aware(row.expires_at) < datetime.now(timezone.utc):
        row.status = STATUS_EXPIRED
        await session.commit()
        return row, "EXPIRED"

    if row.heartbeat_required_every and row.last_heartbeat_at:
        max_age = datetime.now(timezone.utc) - timedelta(seconds=row.heartbeat_required_every)
        if _as_aware(row.last_heartbeat_at) < max_age:
            await suspend_async(session, row, REASON_HEARTBEAT_MISSING)
            return row, "HEARTBEAT_MISSING"

    await session.execute(
        update(AgentTokenDB)
        .where(AgentTokenDB.id == row.id)
        .values(last_used_at=datetime.now(timezone.utc), current_request_count=AgentTokenDB.current_request_count + 1)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    await session.refresh(row)
    return row, None


def validate_permission(agent_token: AgentTokenDB, permission_code: str, user: User, settings: Settings) -> bool:
    """[AIRS-CORE-6] Double Validation: (a) `permission_code` is in the token's Granted
    Permissions, AND (b) the Delegating User currently holds it. See module docstring — (b) is
    scoped down to `user.is_superuser` in the Reference_Stack; a non-superuser Delegating User can
    never satisfy Double Validation here, by design, until Group D ships real permission
    tracking."""
    agent_has_perm = permission_code in agent_token.granted_permissions
    if not agent_has_perm:
        if settings.airs_require_explicit_permissions:
            return False
        if agent_token.granted_permissions:
            return False
    return bool(user.is_superuser)


async def revoke_async(
    session: AsyncSession, row: AgentTokenDB, *, revoked_by_user_id: str | None = None, reason: str = REASON_MANUAL
) -> AgentTokenDB:
    row.status = STATUS_REVOKED
    row.revoked_at = datetime.now(timezone.utc)
    row.revoked_by_user_id = revoked_by_user_id
    row.suspended_reason = reason
    await session.commit()
    await session.refresh(row)
    return row


async def suspend_async(session: AsyncSession, row: AgentTokenDB, reason: str) -> AgentTokenDB:
    row.status = STATUS_SUSPENDED
    row.suspended_at = datetime.now(timezone.utc)
    row.suspended_reason = reason
    await session.commit()
    await session.refresh(row)
    return row


async def revoke_all_for_user_async(session: AsyncSession, user_id: str) -> int:
    """The nuclear circuit-breaker: revokes every `ACTIVE` token belonging to `user_id`."""
    stmt = select(AgentTokenDB).where(
        AgentTokenDB.triggered_by_user_id == user_id, AgentTokenDB.status == STATUS_ACTIVE
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.status = STATUS_REVOKED
        row.revoked_at = now
        row.revoked_by_user_id = user_id
        row.suspended_reason = REASON_MANUAL
    await session.commit()
    return len(rows)


async def send_heartbeat_async(session: AsyncSession, row: AgentTokenDB) -> AgentTokenDB:
    row.last_heartbeat_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def check_circuit_breaker_async(
    session: AsyncSession, row: AgentTokenDB, settings: Settings, cache_service: CacheService
) -> tuple[bool, str | None]:
    """[AIRS-GUARDS-1]/[AIRS-GUARDS-2]/[AIRS-BUDGET-3]: evaluates every guardrail threshold
    configured on `row`, suspending and returning `(False, reason)` on the first breach."""
    if not settings.airs_circuit_breaker_enabled:
        return True, None

    if row.max_requests_total and row.current_request_count > row.max_requests_total:
        await suspend_async(session, row, REASON_RATE_LIMIT)
        return False, "MAX_REQUESTS_TOTAL_EXCEEDED"

    if row.max_failed_requests and row.current_failed_count > row.max_failed_requests:
        await suspend_async(session, row, REASON_ANOMALY)
        return False, "MAX_FAILED_REQUESTS_EXCEEDED"

    if row.budget_limit_usd and row.current_spend_usd >= row.budget_limit_usd:
        await suspend_async(session, row, REASON_BUDGET_EXCEEDED)
        return False, "BUDGET_EXCEEDED"

    if row.max_requests_per_minute:
        cache_key = f"airs_rpm_{row.token_hash}"
        current = await cache_service.get_async(cache_key)
        current = int(current) if current is not None else 0

        if current >= row.max_requests_per_minute:
            await suspend_async(session, row, REASON_RATE_LIMIT)
            return False, "RATE_LIMIT_EXCEEDED"

        if current == 0:
            await cache_service.set_async(cache_key, 1, timeout=60)
        else:
            await cache_service.increment_async(cache_key)

    return True, None


async def create_pending_action_async(
    session: AsyncSession,
    *,
    agent_token: AgentTokenDB,
    permission: str,
    endpoint: str,
    payload: dict,
    prompt_trace_id: str | None = None,
) -> AgentPendingActionDB:
    """[AIRS-HITL-3]: creates a Pending Action with a fresh, unguessable Confirmation Token and
    the default 10-minute lifetime ([AIRS-HITL-4])."""
    row = AgentPendingActionDB(
        agent_token_id=agent_token.id,
        permission_requested=permission,
        endpoint=endpoint,
        payload=payload,
        confirmation_token=_generate_confirmation_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=_HITL_PENDING_ACTION_LIFETIME_MINUTES),
        prompt_trace_id=prompt_trace_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def _get_actionable_pending_action(session: AsyncSession, confirmation_token: str) -> AgentPendingActionDB | None:
    stmt = select(AgentPendingActionDB).where(
        AgentPendingActionDB.confirmation_token == confirmation_token,
        AgentPendingActionDB.confirmed_at.is_(None),
        AgentPendingActionDB.denied_at.is_(None),
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if _as_aware(row.expires_at) < datetime.now(timezone.utc):
        return None
    return row


async def confirm_pending_action_async(session: AsyncSession, confirmation_token: str) -> AgentPendingActionDB | None:
    """[AIRS-HITL-5]: confirming an action that doesn't exist, is already confirmed/denied, or has
    expired MUST fail without side effect — returns `None` in every such case, never raises."""
    row = await _get_actionable_pending_action(session, confirmation_token)
    if row is None:
        return None
    row.confirmed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def deny_pending_action_async(session: AsyncSession, confirmation_token: str) -> AgentPendingActionDB | None:
    row = await _get_actionable_pending_action(session, confirmation_token)
    if row is None:
        return None
    row.denied_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def report_usage_async(session: AsyncSession, row: AgentTokenDB, *, cost_usd: float, settings: Settings) -> bool:
    """[AIRS-BUDGET-2]/[AIRS-BUDGET-3]: accumulates `cost_usd` against `row.current_spend_usd`;
    returns `False` (and suspends the token) once the running total reaches or exceeds
    `row.budget_limit_usd`. A no-op success (`True`) when budget tracking is disabled or the token
    declared no budget limit — matches Django exactly."""
    if not settings.airs_budget_tracking_enabled:
        return True
    if not row.budget_limit_usd:
        return True

    row.current_spend_usd = row.current_spend_usd + Decimal(str(cost_usd))
    await session.commit()

    if row.current_spend_usd >= row.budget_limit_usd:
        await suspend_async(session, row, REASON_BUDGET_EXCEEDED)
        return False
    return True
