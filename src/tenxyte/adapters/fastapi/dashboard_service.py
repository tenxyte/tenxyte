"""
Framework-agnostic-in-spirit dashboard/stats service for the Reference_Stack (spec z_aud_3, Wave D
chunk 5/5, task 10.1) — dashboard/stats, dashboard/auth, dashboard/security, dashboard/gdpr,
dashboard/organizations. Contract extracted from `views/dashboard_views.py` (all 5 gated by the
same `dashboard.view` permission, verified by reading the Django views) and
`services/stats_service.py`'s `StatsService`.

**Aggregation is done in Python, not SQL `FILTER`/`GROUP BY`**: `StatsService` leans on Django
ORM's `Count(..., filter=Q(...))` (conditional aggregates) and `.values().annotate()` (GROUP BY).
SQLAlchemy's closest equivalent (`func.count().filter(...)`) compiles to a SQL `FILTER` clause
that isn't portably supported across the sqlite versions this dev driver might run against, and
dashboard endpoints are inherently low-frequency/low-volume (an admin console, not a hot request
path) — so this module fetches the relevant rows and aggregates them in Python instead. Simpler,
fully portable, and easy to verify against `StatsService`'s exact output shape.

**Two of Django's five sub-stats can't be faithfully backed by real data yet, documented rather
than faked with a backing table that doesn't belong to this task**:
- `dashboard/organizations/` always returns `{"enabled": False}` — the exact shape Django itself
  returns when `org_settings.ORGANIZATIONS_ENABLED` is off. The Reference_Stack has no
  organizations concept at all yet (Parity_Group E, not yet ported), so "disabled" is simply true
  today, not a placeholder.
- `dashboard/gdpr/` (and the `gdpr` sub-object of `dashboard/stats/`) returns the correctly-shaped
  *zero-value* response `StatsService` would produce against an empty `AccountDeletionRequest`
  table, computed without a backing table — Group G (GDPR deletion requests) hasn't shipped, and
  standing up a table now, in a Group D task, ahead of Group G's own schema design would be
  scope creep this chunk doesn't need. Once Group G lands, these two functions get real queries.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import (
    ApplicationDB,
    AuditLogDB,
    BlacklistedTokenDB,
    LoginAttemptDB,
    RefreshTokenDB,
    UserDB,
)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def _count(session: AsyncSession, stmt) -> int:
    return (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()


# ============================================================
# User stats (shared by dashboard/stats/'s "users" section)
# ============================================================


async def _user_stats_async(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today = _day_start(now)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    rows = (await session.execute(select(UserDB))).scalars().all()
    return {
        "total": len(rows),
        "active": sum(1 for u in rows if u.is_active),
        "locked": sum(1 for u in rows if u.is_locked),
        "banned": sum(1 for u in rows if u.is_banned),
        "deleted": sum(1 for u in rows if u.is_deleted),
        "verified_email": sum(1 for u in rows if u.email_verified),
        "verified_phone": sum(1 for u in rows if u.phone_verified),
        "with_2fa": sum(1 for u in rows if u.mfa_type.value != "none"),
        "new_today": sum(1 for u in rows if u.created_at and _as_aware(u.created_at) >= today),
        "new_this_week": sum(1 for u in rows if u.created_at and _as_aware(u.created_at) >= week_ago),
        "new_this_month": sum(1 for u in rows if u.created_at and _as_aware(u.created_at) >= month_ago),
    }


def _as_aware(dt: datetime) -> datetime:
    """DB-loaded datetimes come back tz-naive from the aiosqlite dev driver, even though we always
    write tz-aware UTC values — same convention as `airs_service._as_aware`/
    `admin_security_service._as_aware`."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _application_stats_async(session: AsyncSession) -> dict:
    rows = (await session.execute(select(ApplicationDB))).scalars().all()
    return {"total": len(rows), "active": sum(1 for a in rows if a.is_active)}


async def _auth_summary_async(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today = _day_start(now)
    login_rows = (
        (await session.execute(select(LoginAttemptDB).where(LoginAttemptDB.created_at >= today))).scalars().all()
    )
    active_refresh = await _count(
        session, select(RefreshTokenDB).where(RefreshTokenDB.revoked_at.is_(None), RefreshTokenDB.expires_at > now)
    )
    return {
        "total_logins_today": sum(1 for r in login_rows if r.success),
        "failed_logins_today": sum(1 for r in login_rows if not r.success),
        "active_refresh_tokens": active_refresh,
    }


async def _security_summary_async(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    active_blacklisted = await _count(session, select(BlacklistedTokenDB).where(BlacklistedTokenDB.expires_at > now))
    suspicious_24h = await _count(
        session,
        select(AuditLogDB).where(
            AuditLogDB.action.in_(["suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"]),
            AuditLogDB.created_at >= day_ago,
        ),
    )
    return {"blacklisted_tokens": active_blacklisted, "suspicious_activity_24h": suspicious_24h}


_GDPR_ZERO_SUMMARY = {"pending": 0, "confirmed": 0, "expiring_7d": 0}


async def get_global_stats_async(session: AsyncSession) -> dict:
    """GET /dashboard/stats/ — mirrors `StatsService.get_global_stats`."""
    return {
        "users": await _user_stats_async(session),
        "auth": await _auth_summary_async(session),
        "applications": await _application_stats_async(session),
        "security": await _security_summary_async(session),
        "gdpr": dict(_GDPR_ZERO_SUMMARY),
    }


# ============================================================
# Auth stats
# ============================================================


async def get_auth_stats_async(session: AsyncSession) -> dict:
    """GET /dashboard/auth/ — mirrors `StatsService.get_auth_stats`."""
    now = datetime.now(timezone.utc)
    today = _day_start(now)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    return {
        "login_stats": {
            "today": await _login_period_stats_async(session, today),
            "this_week": await _login_period_stats_async(session, week_ago),
            "this_month": await _login_period_stats_async(session, month_ago),
        },
        "login_by_method": await _login_by_method_async(session, today),
        "registration_stats": {
            "today": await _count(session, select(UserDB).where(UserDB.created_at >= today)),
            "this_week": await _count(session, select(UserDB).where(UserDB.created_at >= week_ago)),
            "this_month": await _count(session, select(UserDB).where(UserDB.created_at >= month_ago)),
        },
        "token_stats": await _token_stats_async(session, today),
        "top_login_failure_reasons": await _top_failure_reasons_async(session, month_ago),
        "charts": {"logins_per_day_7d": await _logins_per_day_async(session, 7)},
    }


async def _login_period_stats_async(session: AsyncSession, since: datetime) -> dict:
    rows = (await session.execute(select(LoginAttemptDB).where(LoginAttemptDB.created_at >= since))).scalars().all()
    return {
        "total": len(rows),
        "success": sum(1 for r in rows if r.success),
        "failed": sum(1 for r in rows if not r.success),
    }


async def _login_by_method_async(session: AsyncSession, since: datetime) -> dict:
    stmt = select(AuditLogDB).where(AuditLogDB.action == "login", AuditLogDB.created_at >= since)
    rows = (await session.execute(stmt)).scalars().all()
    counts = Counter((r.details or {}).get("method") or "unknown" for r in rows)
    if not counts:
        return {"total": len(rows)}
    return dict(counts)


async def _token_stats_async(session: AsyncSession, today: datetime) -> dict:
    now = datetime.now(timezone.utc)
    active_refresh = await _count(
        session, select(RefreshTokenDB).where(RefreshTokenDB.revoked_at.is_(None), RefreshTokenDB.expires_at > now)
    )
    refreshed_today = await _count(
        session, select(AuditLogDB).where(AuditLogDB.action == "token_refresh", AuditLogDB.created_at >= today)
    )
    revoked_today = await _count(
        session,
        select(RefreshTokenDB).where(RefreshTokenDB.revoked_at.is_not(None), RefreshTokenDB.last_used_at >= today),
    )
    return {
        "active_refresh_tokens": active_refresh,
        "tokens_refreshed_today": refreshed_today,
        "tokens_revoked_today": revoked_today,
    }


async def _top_failure_reasons_async(session: AsyncSession, since: datetime, limit: int = 5) -> list[dict]:
    stmt = select(LoginAttemptDB).where(
        LoginAttemptDB.success.is_(False), LoginAttemptDB.created_at >= since, LoginAttemptDB.failure_reason != ""
    )
    rows = (await session.execute(stmt)).scalars().all()
    counts = Counter(r.failure_reason for r in rows)
    return [{"reason": reason, "count": count} for reason, count in counts.most_common(limit)]


async def _logins_per_day_async(session: AsyncSession, days: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await session.execute(select(LoginAttemptDB).where(LoginAttemptDB.created_at >= since))).scalars().all()
    by_day: dict[str, dict[str, int]] = {}
    for row in rows:
        day = _as_aware(row.created_at).date().isoformat()
        bucket = by_day.setdefault(day, {"success": 0, "failed": 0})
        bucket["success" if row.success else "failed"] += 1
    return [{"date": day, **counts} for day, counts in sorted(by_day.items())]


# ============================================================
# Security stats
# ============================================================


async def get_security_stats_async(session: AsyncSession) -> dict:
    """GET /dashboard/security/ — mirrors `StatsService.get_security_stats`."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    today = _day_start(now)

    suspicious_actions = ["suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"]
    return {
        "audit_summary_24h": await _audit_summary_async(session, day_ago),
        "blacklisted_tokens": await _blacklisted_token_stats_async(session, now),
        "suspicious_activity": {
            "last_24h": await _count(
                session,
                select(AuditLogDB).where(AuditLogDB.action.in_(suspicious_actions), AuditLogDB.created_at >= day_ago),
            ),
            "last_7d": await _count(
                session,
                select(AuditLogDB).where(AuditLogDB.action.in_(suspicious_actions), AuditLogDB.created_at >= week_ago),
            ),
            "top_ips": await _top_ips_async(session, day_ago),
        },
        "account_security": {
            "locked_accounts": await _count(session, select(UserDB).where(UserDB.is_locked.is_(True))),
            "banned_accounts": await _count(session, select(UserDB).where(UserDB.is_banned.is_(True))),
            "2fa_adoption_rate": await _2fa_rate_async(session),
            "password_changes_today": await _count(
                session,
                select(AuditLogDB).where(AuditLogDB.action == "password_change", AuditLogDB.created_at >= today),
            ),
        },
    }


async def _audit_summary_async(session: AsyncSession, since: datetime) -> dict:
    rows = (await session.execute(select(AuditLogDB).where(AuditLogDB.created_at >= since))).scalars().all()
    by_action = Counter(r.action for r in rows)
    return {"total_events": len(rows), "by_action": dict(by_action)}


async def _blacklisted_token_stats_async(session: AsyncSession, now: datetime) -> dict:
    active_rows = (
        (await session.execute(select(BlacklistedTokenDB).where(BlacklistedTokenDB.expires_at > now))).scalars().all()
    )
    by_reason = Counter(r.reason or "unknown" for r in active_rows)
    expired_pending = await _count(session, select(BlacklistedTokenDB).where(BlacklistedTokenDB.expires_at < now))
    return {
        "total_active": len(active_rows),
        "by_reason": dict(by_reason),
        "expired_pending_cleanup": expired_pending,
    }


async def _top_ips_async(session: AsyncSession, since: datetime, limit: int = 5) -> list[dict]:
    stmt = select(AuditLogDB).where(
        AuditLogDB.action.in_(["login_failed", "suspicious_activity"]), AuditLogDB.created_at >= since
    )
    rows = (await session.execute(stmt)).scalars().all()
    counts = Counter(r.ip_address for r in rows if r.ip_address)
    return [{"ip_address": ip, "events": events} for ip, events in counts.most_common(limit)]


async def _2fa_rate_async(session: AsyncSession) -> float:
    rows = (await session.execute(select(UserDB).where(UserDB.is_active.is_(True)))).scalars().all()
    if not rows:
        return 0.0
    with_2fa = sum(1 for u in rows if u.mfa_type.value != "none")
    return round((with_2fa / len(rows)) * 100, 1)


# ============================================================
# GDPR stats — see module docstring: no backing table yet (Group G).
# ============================================================


async def get_gdpr_stats_async(session: AsyncSession) -> dict:
    """GET /dashboard/gdpr/ — the zero-value shape `StatsService.get_gdpr_stats` would produce
    against an empty `AccountDeletionRequest` table."""
    return {
        "deletion_requests": {"total": 0, "by_status": {}, "grace_period_expiring_7d": 0},
        "data_exports": {"total_today": 0, "total_this_month": 0},
    }


# ============================================================
# Organization stats — see module docstring: Group E hasn't shipped.
# ============================================================


async def get_organization_stats_async(session: AsyncSession) -> dict:
    """GET /dashboard/organizations/ — matches Django's own `{"enabled": False}` shape for a
    deployment with organizations disabled, which the Reference_Stack always is today."""
    return {"enabled": False}
