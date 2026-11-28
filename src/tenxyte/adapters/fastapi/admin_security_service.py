"""
Framework-agnostic-in-spirit admin-security service for the Reference_Stack (spec z_aud_3, Wave D
chunk 4/5, task 10.1) — admin/audit-logs/*, admin/login-attempts/*, admin/blacklisted-tokens/*,
admin/refresh-tokens/*. Contract extracted from `views/security_views.py` (`AuditLogListView`,
`AuditLogDetailView`, `LoginAttemptListView`, `BlacklistedTokenListView`,
`BlacklistedTokenCleanupView`, `RefreshTokenListView`, `RefreshTokenRevokeView`),
`serializers/security_serializers.py`, and `filters.py` (`apply_audit_log_filters`,
`apply_login_attempt_filters`).

**Every one of these 7 endpoints requires `security.view`** — verified by reading
`security_views.py` directly rather than assuming a separate write permission exists for
`BlacklistedTokenCleanupView`/`RefreshTokenRevokeView`: both POST actions are gated by the same
`security.view` Django decorator as the GET listings, not a `security.manage`-style permission.
Replicated exactly (see `routers/admin_security.py`).

**Two ordering quirks replicated exactly rather than normalized to `pagination.apply_ordering`**:
`BlacklistedTokenListView`/`RefreshTokenListView` don't call `filters.apply_ordering()` at all —
each does its own inline check against a small literal set of exact `?ordering=` values (no
comma-separated multi-field support, no `-`-stripping) and silently ignores anything outside that
set instead of falling back to a default — `_BLACKLISTED_TOKEN_ORDERING`/`_REFRESH_TOKEN_ORDERING`
below reproduce that literal behavior; `list_audit_logs_async`/`list_login_attempts_async` (which
*do* mirror
`filters.apply_ordering`) still use the shared `pagination.apply_ordering` like every other Wave D
list endpoint.

**`BlacklistedTokenDB`/`AuditLogDB`/`LoginAttemptDB` population**: see each model's docstring in
`models_sa.py` — blacklisting is wired into the 3 real call sites that already blacklist a token
(so `admin/blacklisted-tokens/*` reflects real logout/2FA-bootstrap events), but audit-log and
login-attempt recording is out of this chunk's scope (an audit-logging retrofit of every Wave A-C
endpoint, not an admin-visibility listing endpoint) — those two tables are correctly served but
currently unpopulated outside of tests that seed them directly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import (
    ApplicationDB,
    AuditLogDB,
    BlacklistedTokenDB,
    LoginAttemptDB,
    RefreshTokenDB,
    UserDB,
)
from tenxyte.adapters.fastapi.pagination import apply_ordering
from tenxyte.core.jwt_service import JWTService


def _as_aware(dt: datetime) -> datetime:
    """DB-loaded datetimes come back tz-naive from the aiosqlite dev driver, even though we always
    write tz-aware UTC values — normalize before comparing against `datetime.now(tz=...)` (same
    convention as `airs_service._as_aware`)."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ============================================================
# Blacklisted-token recording — called alongside (not instead of) the actual
# in-memory-blacklist-checking path, purely so admin/blacklisted-tokens/* has real rows to show.
# ============================================================


class SQLAlchemyTokenBlacklistService:
    """DB-backed `AsyncTokenBlacklistService` over `tenxyte_blacklisted_tokens`.

    Shares the exact same `tenxyte_blacklisted_tokens` table as Django's `BlacklistedToken`
    so a JWT revoked in Django is immediately rejected by FastAPI and vice versa, even across
    restarts. User-level revocation timestamps (`revoke_all_user_tokens_async`) stay in memory
    (mirroring Django's cache-based user revocation).
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._user_revocations: dict[str, datetime] = {}

    def is_blacklisted(self, jti: str) -> bool:
        raise NotImplementedError("Use is_blacklisted_async in the async FastAPI Reference_Stack.")

    def is_user_revoked(self, user_id: str, token_iat: datetime) -> bool:
        revoked_at = self._user_revocations.get(user_id)
        if revoked_at is None:
            return False
        iat_aware = token_iat if token_iat.tzinfo else token_iat.replace(tzinfo=timezone.utc)
        return iat_aware < revoked_at

    def revoke_all_user_tokens(self, user_id: str) -> datetime:
        now = datetime.now(timezone.utc)
        self._user_revocations[user_id] = now
        return now

    def blacklist_token(self, jti: str, expires_at: datetime, user_id: str | None = None, reason: str = "") -> bool:
        raise NotImplementedError("Use blacklist_token_async in the async FastAPI Reference_Stack.")

    async def is_blacklisted_async(self, jti: str) -> bool:
        async with self._session_factory() as session:
            stmt = select(BlacklistedTokenDB).where(BlacklistedTokenDB.token_jti == jti)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return False
            return _as_aware(row.expires_at) > datetime.now(timezone.utc)

    async def is_user_revoked_async(self, user_id: str, token_iat: datetime) -> bool:
        return self.is_user_revoked(user_id, token_iat)

    async def revoke_all_user_tokens_async(self, user_id: str) -> datetime:
        return self.revoke_all_user_tokens(user_id)

    async def blacklist_token_async(
        self, jti: str, expires_at: datetime, user_id: str | None = None, reason: str = ""
    ) -> bool:
        async with self._session_factory() as session:
            existing = (
                await session.execute(select(BlacklistedTokenDB).where(BlacklistedTokenDB.token_jti == jti))
            ).scalar_one_or_none()
            if existing is None:
                session.add(
                    BlacklistedTokenDB(
                        token_jti=jti,
                        user_id=user_id,
                        expires_at=expires_at,
                        reason=reason,
                    )
                )
                await session.commit()
        return True


async def record_blacklisted_token_async(
    session: AsyncSession, jwt_service: JWTService, token: str, *, user_id: str | None = None, reason: str = ""
) -> None:
    decoded = await jwt_service.decode_token_async(token, check_blacklist=False)
    if not decoded or not decoded.jti:
        return
    existing = (
        await session.execute(select(BlacklistedTokenDB).where(BlacklistedTokenDB.token_jti == decoded.jti))
    ).scalar_one_or_none()
    if existing is not None:
        changed = False
        resolved_user_id = user_id or decoded.user_id
        if existing.user_id is None and resolved_user_id:
            existing.user_id = resolved_user_id
            changed = True
        if not existing.reason and reason:
            existing.reason = reason
            changed = True
        if changed:
            await session.commit()
        return
    session.add(
        BlacklistedTokenDB(
            token_jti=decoded.jti,
            user_id=user_id or decoded.user_id,
            expires_at=decoded.exp,
            reason=reason,
        )
    )
    await session.commit()


# ============================================================
# Shared lookups for user_email/application_name — small, single-row lookups (admin listings are
# low-volume, low-page-size; consistent with this adapter's existing per-row serialization style,
# e.g. rbac_service.serialize_role_async's per-row permission lookups).
# ============================================================


async def _user_email(session: AsyncSession, user_id: str | None) -> str | None:
    if not user_id:
        return None
    user = await session.get(UserDB, user_id)
    return user.email if user else None


async def _application_name(session: AsyncSession, application_id: str | None) -> str | None:
    if not application_id:
        return None
    app = await session.get(ApplicationDB, application_id)
    return app.name if app else None


# ============================================================
# Audit logs
# ============================================================


async def serialize_audit_log_async(session: AsyncSession, log: AuditLogDB) -> dict:
    return {
        "id": log.id,
        "user": log.user_id,
        "user_email": await _user_email(session, log.user_id),
        "action": log.action,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "application": log.application_id,
        "application_name": await _application_name(session, log.application_id),
        "details": log.details,
        "created_at": log.created_at.isoformat(),
    }


async def get_audit_log_by_id_async(session: AsyncSession, log_id: str) -> AuditLogDB | None:
    return await session.get(AuditLogDB, log_id)


async def list_audit_logs_async(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    action: str | None = None,
    ip_address: str | None = None,
    application_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ordering: str = "-created_at",
    page: int,
    page_size: int,
) -> tuple[list[AuditLogDB], int]:
    stmt = select(AuditLogDB)
    count_stmt = select(func.count(AuditLogDB.id))

    if user_id:
        stmt = stmt.where(AuditLogDB.user_id == user_id)
        count_stmt = count_stmt.where(AuditLogDB.user_id == user_id)

    if action:
        actions = [a.strip() for a in action.split(",")]
        stmt = stmt.where(AuditLogDB.action.in_(actions))
        count_stmt = count_stmt.where(AuditLogDB.action.in_(actions))

    if ip_address:
        stmt = stmt.where(AuditLogDB.ip_address == ip_address)
        count_stmt = count_stmt.where(AuditLogDB.ip_address == ip_address)

    if application_id:
        stmt = stmt.where(AuditLogDB.application_id == application_id)
        count_stmt = count_stmt.where(AuditLogDB.application_id == application_id)

    if date_from:
        stmt = stmt.where(AuditLogDB.created_at >= date_from)
        count_stmt = count_stmt.where(AuditLogDB.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLogDB.created_at <= date_to)
        count_stmt = count_stmt.where(AuditLogDB.created_at <= date_to)

    allowed_ordering = {
        "created_at": AuditLogDB.created_at,
        "action": AuditLogDB.action,
        "user_id": AuditLogDB.user_id,
        "ip_address": AuditLogDB.ip_address,
    }
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="-created_at")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


# ============================================================
# Login attempts
# ============================================================


def serialize_login_attempt(attempt: LoginAttemptDB) -> dict:
    return {
        "id": attempt.id,
        "identifier": attempt.identifier,
        "ip_address": attempt.ip_address,
        "application": attempt.application_id,
        "success": attempt.success,
        "failure_reason": attempt.failure_reason,
        "created_at": attempt.created_at.isoformat(),
    }


async def list_login_attempts_async(
    session: AsyncSession,
    *,
    identifier: str | None = None,
    ip_address: str | None = None,
    success: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ordering: str = "-created_at",
    page: int,
    page_size: int,
) -> tuple[list[LoginAttemptDB], int]:
    stmt = select(LoginAttemptDB)
    count_stmt = select(func.count(LoginAttemptDB.id))

    if identifier:
        clause = LoginAttemptDB.identifier.ilike(f"%{identifier}%")
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if ip_address:
        stmt = stmt.where(LoginAttemptDB.ip_address == ip_address)
        count_stmt = count_stmt.where(LoginAttemptDB.ip_address == ip_address)

    if success is not None:
        stmt = stmt.where(LoginAttemptDB.success == success)
        count_stmt = count_stmt.where(LoginAttemptDB.success == success)

    if date_from:
        stmt = stmt.where(LoginAttemptDB.created_at >= date_from)
        count_stmt = count_stmt.where(LoginAttemptDB.created_at >= date_from)
    if date_to:
        stmt = stmt.where(LoginAttemptDB.created_at <= date_to)
        count_stmt = count_stmt.where(LoginAttemptDB.created_at <= date_to)

    allowed_ordering = {
        "created_at": LoginAttemptDB.created_at,
        "identifier": LoginAttemptDB.identifier,
        "ip_address": LoginAttemptDB.ip_address,
        "success": LoginAttemptDB.success,
    }
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="-created_at")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


# ============================================================
# Blacklisted tokens
# ============================================================

_BLACKLISTED_TOKEN_ORDERING = {
    "blacklisted_at": BlacklistedTokenDB.blacklisted_at.asc(),
    "-blacklisted_at": BlacklistedTokenDB.blacklisted_at.desc(),
    "expires_at": BlacklistedTokenDB.expires_at.asc(),
    "-expires_at": BlacklistedTokenDB.expires_at.desc(),
}


async def serialize_blacklisted_token_async(session: AsyncSession, token: BlacklistedTokenDB) -> dict:
    return {
        "id": token.id,
        "token_jti": token.token_jti,
        "user": token.user_id,
        "user_email": await _user_email(session, token.user_id),
        "blacklisted_at": token.blacklisted_at.isoformat(),
        "expires_at": token.expires_at.isoformat(),
        "reason": token.reason,
        "is_expired": _as_aware(token.expires_at) < datetime.now(timezone.utc),
    }


async def list_blacklisted_tokens_async(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    reason: str | None = None,
    expired: bool | None = None,
    ordering: str = "-blacklisted_at",
    page: int,
    page_size: int,
) -> tuple[list[BlacklistedTokenDB], int]:
    stmt = select(BlacklistedTokenDB)
    count_stmt = select(func.count(BlacklistedTokenDB.id))

    if user_id:
        stmt = stmt.where(BlacklistedTokenDB.user_id == user_id)
        count_stmt = count_stmt.where(BlacklistedTokenDB.user_id == user_id)

    if reason:
        stmt = stmt.where(BlacklistedTokenDB.reason == reason)
        count_stmt = count_stmt.where(BlacklistedTokenDB.reason == reason)

    if expired is not None:
        now = datetime.now(timezone.utc)
        clause = BlacklistedTokenDB.expires_at < now if expired else BlacklistedTokenDB.expires_at >= now
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    # Mirrors BlacklistedTokenListView exactly: an unrecognized `ordering` value is silently
    # ignored — no `order_by()` call at all, not even a fallback default (Django's own
    # `if ordering in allowed_fields: queryset.order_by(ordering)` — no `else` branch).
    order_clause = _BLACKLISTED_TOKEN_ORDERING.get(ordering)
    if order_clause is not None:
        stmt = stmt.order_by(order_clause)

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


async def cleanup_expired_blacklisted_tokens_async(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    stmt = select(func.count(BlacklistedTokenDB.id)).where(BlacklistedTokenDB.expires_at < now)
    count = (await session.execute(stmt)).scalar_one()
    await session.execute(delete(BlacklistedTokenDB).where(BlacklistedTokenDB.expires_at < now))
    await session.commit()
    return count


# ============================================================
# Refresh tokens (admin view)
# ============================================================

_REFRESH_TOKEN_ORDERING = {
    "created_at": RefreshTokenDB.created_at.asc(),
    "-created_at": RefreshTokenDB.created_at.desc(),
    "expires_at": RefreshTokenDB.expires_at.asc(),
    "-expires_at": RefreshTokenDB.expires_at.desc(),
    "last_used_at": RefreshTokenDB.last_used_at.asc(),
    "-last_used_at": RefreshTokenDB.last_used_at.desc(),
}


async def serialize_refresh_token_admin_async(session: AsyncSession, token: RefreshTokenDB) -> dict:
    return {
        "id": token.id,
        "user": token.user_id,
        "user_email": await _user_email(session, token.user_id),
        "application": token.application_id,
        "application_name": await _application_name(session, token.application_id),
        "device_info": token.device_info,
        "ip_address": token.ip_address,
        "is_revoked": token.is_revoked,
        "is_expired": _as_aware(token.expires_at) < datetime.now(timezone.utc),
        "expires_at": token.expires_at.isoformat(),
        "created_at": token.created_at.isoformat(),
        "last_used_at": token.last_used_at.isoformat(),
    }


async def get_refresh_token_by_id_async(session: AsyncSession, token_id: str) -> RefreshTokenDB | None:
    return await session.get(RefreshTokenDB, token_id)


async def list_refresh_tokens_admin_async(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    application_id: str | None = None,
    is_revoked: bool | None = None,
    expired: bool | None = None,
    ordering: str = "-created_at",
    page: int,
    page_size: int,
) -> tuple[list[RefreshTokenDB], int]:
    stmt = select(RefreshTokenDB)
    count_stmt = select(func.count(RefreshTokenDB.id))

    if user_id:
        stmt = stmt.where(RefreshTokenDB.user_id == user_id)
        count_stmt = count_stmt.where(RefreshTokenDB.user_id == user_id)

    if application_id:
        stmt = stmt.where(RefreshTokenDB.application_id == application_id)
        count_stmt = count_stmt.where(RefreshTokenDB.application_id == application_id)

    if is_revoked is not None:
        clause = RefreshTokenDB.is_revoked.is_(True) if is_revoked else RefreshTokenDB.is_revoked.is_(False)
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if expired is not None:
        now = datetime.now(timezone.utc)
        clause = RefreshTokenDB.expires_at < now if expired else RefreshTokenDB.expires_at >= now
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    # Same "silently ignored, no fallback" quirk as BlacklistedTokenListView above — mirrors
    # RefreshTokenListView's own `if ordering in allowed_fields: queryset.order_by(ordering)`.
    order_clause = _REFRESH_TOKEN_ORDERING.get(ordering)
    if order_clause is not None:
        stmt = stmt.order_by(order_clause)

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total
