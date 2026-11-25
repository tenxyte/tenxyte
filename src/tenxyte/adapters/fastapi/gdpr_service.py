"""
Parity_Group G chunks 3-4/4 (spec z_aud_3, task 12.1) — GDPR user endpoints: `request-account-
deletion/`, `confirm-account-deletion/`, `cancel-account-deletion/`, `account-deletion-status/`,
`export-user-data/` (chunk 3, 5 endpoints); GDPR admin: `admin/deletion-requests/*` (chunk 4, 4
endpoints — see the `# GDPR admin` section further down this file for its own contract notes).
9 of Group G's 17 endpoints total, 17/17 cumulative once chunk 4 ships. Contract extracted from
`views/account_deletion_views.py`, `services/account_deletion_service.py`,
`services/reauth_service.py`, `models/gdpr.py::AccountDeletionRequest`, `views/gdpr_admin_views.py`,
and `serializers/gdpr_admin_serializers.py`, each read in full — Django never extracted any of
this to Core.

**Two real, previously-undiscovered Django bugs found while porting, fixed rather than
replicated — each confirmed empirically by calling the real view function directly against a live
Django test database, not just by reading the code:**

1. `export_user_data`'s `"permissions"` list iterates `request.user.get_all_permissions()` as if
   each item were a `Permission` object (`perm.code`/`perm.name`/`perm.created_at`). But
   `get_all_permissions()` returns `list(self._get_effective_permission_codes())`, and
   `_get_effective_permission_codes()` returns a `set` of plain code **strings**
   (`codes = set(user_perms.values_list("code", flat=True))` — read directly in
   `models/auth.py`). Any user holding at least one effective permission — virtually every real
   user, since a default role grants permissions — crashes this line with an uncaught
   `AttributeError: 'str' object has no attribute 'code'`, caught only by the view's own broad
   `except Exception`, which returns a 500 `"An unexpected error occurred while exporting user
   data."`. Confirmed empirically: calling `export_user_data` for a user with one real
   role+permission assigned (not mocked) raises exactly this. Django's own test suite already
   dodges this rather than exercising it for real —
   `test_account_deletion.py::TestExportUserDataView::test_export_data_success` explicitly
   `patch.object(user.__class__, "get_all_permissions", return_value=[])`, sidestepping the crash
   instead of triggering it. This port resolves the effective codes back to real `PermissionDB`
   rows instead (one extra query, reusing `rbac_service.effective_permission_codes_async`'s
   already-correct codes), so export never 500s for a user who actually holds permissions.
2. `request_deletion`'s 2FA gate calls `otp_service.verify_otp(user, otp_code,
   otp_type="login_2fa")` on Django's `OTPService` — but that class only ever defines
   `verify_login_otp`/`verify_email_otp`/`verify_phone_otp`/`verify_password_reset_otp`; no
   `verify_otp` method exists anywhere on it. This call sits outside
   `AccountDeletionService.request_deletion`'s own `try/except`, so nothing catches it — every
   2FA-enabled user who calls `request-account-deletion/` gets an uncaught
   `AttributeError: 'OTPService' object has no attribute 'verify_otp'`, regardless of what
   `otp_code` they send. Confirmed empirically the same way. Rather than replicate a crash on a
   sensitive, irreversible action, this port implements a real working 2FA gate: the same
   `TOTPService.verify_2fa_async` call `routers/auth.py`'s login flow already uses (real TOTP
   verification against `UserDB.mfa_secret`, via `SQLAlchemyTOTPStorage`).

**A third real finding, replicated exactly rather than fixed** (no crash, no security impact —
just a benign always-empty field, the same category as the WebAuthn chunk's preserved-as-is
quirks): `export_user_data`'s `"login_attempts"` and `"applications"` sections are always `[]` in
the real Django export, regardless of actual data. Both are guarded by
`hasattr(request.user, "login_attempts"/"applications")`, and neither attribute can ever exist —
`LoginAttempt` has no FK to `User` at all (only `identifier`/`ip_address`/`application`, verified
in `models/operational.py`), and `Application` has no FK to `User` either (verified in
`models/application.py` — the only `owner` FK mentioned there is inside a docstring example of
subclassing `AbstractApplication`, not the real concrete model). So `hasattr` is always `False`
for both, and the list comprehensions never run. This port does not query `LoginAttemptDB`/
`ApplicationDB` for the export either — wiring up relations Django itself never wired would be a
parity BREAK, not a fix, the same reasoning already applied to `routers/password.py`'s dead
`PasswordHistory` gap.

**Reauth stays password-only** (Requirement 6.4's `reauth_otp_code` — a Login_OTP_Code-based
alternative to the password — is NOT implemented here), matching the precedent already
established in `routers/password.py`/`routers/twofa.py`: a request with only `reauth_otp_code`
(or, for `cancel`/`export`, only `otp_code` used as a reauth alternative — see below) and no
`password` gets `REAUTH_REQUIRED`, an honest signal rather than a silent accept.

**`otp_code` means two different things across these 5 endpoints, exactly as it does in Django —
not a port inconsistency:**
- On `request-account-deletion/`, `otp_code` is the real 2FA gate (bug #2 above) — required only
  when `user.mfa_type != "none"`, verified as a live TOTP code.
- On `cancel-account-deletion/` and `export-user-data/`, `otp_code` is `ReauthService.verify()`'s
  password-alternative parameter (Requirement 6.4) — unimplemented, same REAUTH_REQUIRED
  treatment as `password/change/`'s own `otp_code`.

**Response shapes are the real ones, verified against each `return Response(...)` call site, not
the `@extend_schema` docs (which invent fields none of these views ever populate) — every real
failure response is `{"error": <message>}` with status 400 and NO `code` field, except:**
- The `REAUTH_REQUIRED` pre-check (password AND `reauth_otp_code`/`otp_code` both empty), done in
  the view before calling any service — carries `code: "REAUTH_REQUIRED"`.
- `export-user-data/`'s reauth failure specifically, which surfaces `ReauthService.verify()`'s own
  `error_code` (`INVALID_PASSWORD`/`OTP_INVALID`/`REAUTH_REQUIRED`) — the one place among these 5
  where a service-level failure does carry a code, because the view constructs the response
  directly from `reauth_service.verify()`'s return tuple instead of discarding the code the way
  `request_deletion`/`cancel_deletion` do internally.
- The docs' claimed `DELETION_ALREADY_PENDING` (423), `TOKEN_EXPIRED`/`INVALID_TOKEN` (404/410)
  and their extra fields (`existing_request`, `expired_at`, `cancellation_token`, etc.) are never
  produced by the real code — `AccountDeletionRequest.create_request` unconditionally cancels any
  existing active request and creates a new one (no duplicate-rejection, no 423, matching Wave
  E's already-documented `INVITATION_EXISTS` finding), and confirmation tokens never expire on
  their own (no 24h check exists anywhere despite the docs' claim) — an unrecognized/reused token
  just falls through to the same generic `AccountDeletionRequest.DoesNotExist` → 400 `"Invalid or
  expired confirmation token"` as every other invalid-token case. All replicated exactly: no
  DELETION_ALREADY_PENDING, no token expiry, no 404/410/423 anywhere in these 5 endpoints.

Real success-response shapes (also verified against the code, not the docs):
- `request-account-deletion/` (201): `{"request_id", "message", "grace_period_days"}` — not the
  docs' `deletion_request_id`/`scheduled_deletion_date`/`cancellation_token`/
  `data_retention_policy`.
- `confirm-account-deletion/` (200): `{"message", "grace_period_ends_at", "days_remaining"}` —
  `days_remaining` is literally an echo of the grace-period *setting*, not a computed remaining
  count (harmless since confirmation is when the grace period starts, but worth noting: it is NOT
  `(grace_period_ends_at - now).days`, unlike `account-deletion-status/`'s own `days_remaining`,
  which really is computed that way).
- `cancel-account-deletion/` (200): `{"message", "cancelled_count"}` — not the docs'
  `deletion_cancelled`/`account_reactivated`/`cancellation_time`/`security_note`.
- `account-deletion-status/` (200): `{"total_requests", "active_request", "history"}`.
- `export-user-data/` (200): the full data-portability dict (`user_info`, `roles`, `permissions`,
  `sessions`, `social_connections`, `login_attempts`, `agent_tokens`, `applications`,
  `audit_logs`, `export_metadata`) — an `AuditLogDB` row (`action="data_exported"`) is written on
  every successful export, matching Django's own `AuditLog.objects.create(...)` call.

**`user.is_restricted`**: a real Django model field (Art. 18 RGPD), but read-only everywhere —
no endpoint on either adapter, in any Parity_Group ported so far, ever sets it `True` (only
Django's admin console can). Hardcoded to `False` in `export-user-data/`'s output rather than
adding a whole new always-`False` `UserDB` column nothing would ever populate through this API —
same reasoning as `SocialConnectionDB` omitting Django's dead `access_token`/`refresh_token`
columns.

**`request_id`/`confirmation_token` are UUID strings here**, not the Django model's integer
`AutoField` id — same convention swap as every other Wave D/E table in this port
(`OrganizationDB.id`, etc.).
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi import rbac_service
from tenxyte.adapters.fastapi.models_sa import (
    AccountDeletionRequestDB,
    AgentTokenDB,
    AuditLogDB,
    PermissionDB,
    RefreshTokenDB,
    SocialConnectionDB,
    UserDB,
)
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.totp_storage import SQLAlchemyTOTPStorage
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService
from tenxyte.ports.repositories import User

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = ("pending", "confirmation_sent", "confirmed")


@dataclass
class ReauthResult:
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


async def verify_reauth_async(user: User, *, password: str, otp_code: str) -> ReauthResult:
    """Mirrors `ReauthService.verify()` exactly — password branch is real (bcrypt via the user
    repository's own hash check is done by the caller, this only decides which branch to take);
    the `otp_code` branch is unimplemented (see module docstring), so it always fails
    `OTP_INVALID` rather than silently succeeding."""
    import bcrypt

    if password:
        if user.password_hash and bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return ReauthResult(ok=True)
        return ReauthResult(ok=False, error_code="INVALID_PASSWORD", error_message="Current password is incorrect")
    if otp_code:
        return ReauthResult(
            ok=False,
            error_code="OTP_INVALID",
            error_message="OTP-based reauth is not supported by this adapter",
        )
    return ReauthResult(
        ok=False, error_code="REAUTH_REQUIRED", error_message="Current password or a valid OTP code is required"
    )


async def _audit_log_async(
    session: AsyncSession, action: str, user_id: str | None, ip_address: str | None, details: dict
) -> None:
    session.add(AuditLogDB(action=action, user_id=user_id, ip_address=ip_address, details=details))
    await session.commit()


async def request_deletion_async(
    session: AsyncSession,
    user: User,
    *,
    password: str,
    otp_code: str,
    reauth_otp_code: str,
    reason: str,
    ip_address: str | None,
    user_agent: str,
    settings: Settings,
    totp_service: TOTPService,
) -> tuple[bool, dict[str, Any] | None, str]:
    """Mirrors `AccountDeletionService.request_deletion`. Returns `(success, data, error)` — no
    error code, matching the real view (see module docstring)."""
    reauth = await verify_reauth_async(user, password=password, otp_code=reauth_otp_code)
    if not reauth.ok:
        await _audit_log_async(session, "deletion_request_failed", user.id, ip_address, {"reason": "invalid_password"})
        return False, None, "Invalid password"

    if user.mfa_type.value != "none":
        if not otp_code:
            await _audit_log_async(session, "deletion_request_failed", user.id, ip_address, {"reason": "missing_2fa"})
            return False, None, "Two-factor authentication code required"

        storage = SQLAlchemyTOTPStorage(SQLAlchemyAsyncUserRepository(session))
        ok, _error_message = await totp_service.verify_2fa_async(user.id, otp_code, storage)
        if not ok:
            await _audit_log_async(session, "deletion_request_failed", user.id, ip_address, {"reason": "invalid_2fa"})
            return False, None, "Invalid two-factor authentication code"

    await session.execute(
        update(AccountDeletionRequestDB)
        .where(AccountDeletionRequestDB.user_id == user.id, AccountDeletionRequestDB.status.in_(_ACTIVE_STATUSES))
        .values(status="cancelled")
    )

    grace_period_days = settings.account_deletion_grace_period_days
    deletion_request = AccountDeletionRequestDB(
        user_id=user.id,
        status="confirmation_sent",
        confirmation_token=secrets.token_urlsafe(48),
        ip_address=ip_address,
        user_agent=user_agent,
        reason=reason,
    )
    session.add(deletion_request)
    await session.commit()
    await session.refresh(deletion_request)

    logger.info(
        "Deletion confirmation email (no real backend wired in): user_id=%s token=%s",
        user.id,
        deletion_request.confirmation_token,
    )

    await _audit_log_async(
        session,
        "deletion_request_created",
        user.id,
        ip_address,
        {"request_id": deletion_request.id, "reason": reason},
    )

    return (
        True,
        {
            "request_id": deletion_request.id,
            "message": "Deletion request created. Please check your email for confirmation.",
            "grace_period_days": grace_period_days,
        },
        "",
    )


async def confirm_deletion_async(
    session: AsyncSession, *, token: str, ip_address: str | None, settings: Settings
) -> tuple[bool, dict[str, Any] | None, str]:
    """Mirrors `AccountDeletionService.confirm_deletion` — no expiry check exists in the real
    code (see module docstring); any token not currently `confirmation_sent` (wrong, reused, or
    from a since-cancelled request) hits the same generic error."""
    stmt = select(AccountDeletionRequestDB).where(
        AccountDeletionRequestDB.confirmation_token == token, AccountDeletionRequestDB.status == "confirmation_sent"
    )
    deletion_request = (await session.execute(stmt)).scalar_one_or_none()
    if deletion_request is None:
        return False, None, "Invalid or expired confirmation token"

    grace_period_days = settings.account_deletion_grace_period_days
    deletion_request.status = "confirmed"
    deletion_request.confirmed_at = datetime.now(timezone.utc)
    deletion_request.grace_period_ends_at = datetime.now(timezone.utc) + timedelta(days=grace_period_days)
    await session.commit()

    await _audit_log_async(
        session,
        "deletion_request_confirmed",
        deletion_request.user_id,
        ip_address,
        {
            "request_id": deletion_request.id,
            "grace_period_ends_at": deletion_request.grace_period_ends_at.isoformat(),
        },
    )

    return (
        True,
        {
            "message": "Deletion request confirmed. Your account will be deleted after the grace period.",
            "grace_period_ends_at": deletion_request.grace_period_ends_at.isoformat(),
            "days_remaining": grace_period_days,
        },
        "",
    )


async def cancel_deletion_async(
    session: AsyncSession, user: User, *, password: str, otp_code: str, ip_address: str | None
) -> tuple[bool, dict[str, Any] | None, str]:
    """Mirrors `AccountDeletionService.cancel_deletion`."""
    reauth = await verify_reauth_async(user, password=password, otp_code=otp_code)
    if not reauth.ok:
        await _audit_log_async(session, "deletion_cancel_failed", user.id, ip_address, {"reason": "invalid_password"})
        return False, None, "Invalid password"

    stmt = select(AccountDeletionRequestDB).where(
        AccountDeletionRequestDB.user_id == user.id, AccountDeletionRequestDB.status.in_(_ACTIVE_STATUSES)
    )
    active_requests = list((await session.execute(stmt)).scalars().all())
    if not active_requests:
        return False, None, "No active deletion requests found"

    for req in active_requests:
        req.status = "cancelled"
    await session.commit()

    await _audit_log_async(
        session, "deletion_request_cancelled", user.id, ip_address, {"cancelled_requests": len(active_requests)}
    )

    return (
        True,
        {"message": f"Cancelled {len(active_requests)} deletion request(s).", "cancelled_count": len(active_requests)},
        "",
    )


async def get_user_requests_async(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Mirrors `AccountDeletionService.get_user_requests`."""
    stmt = (
        select(AccountDeletionRequestDB)
        .where(AccountDeletionRequestDB.user_id == user_id)
        .order_by(AccountDeletionRequestDB.requested_at.desc())
    )
    requests = list((await session.execute(stmt)).scalars().all())
    active_request = next((r for r in requests if r.status in _ACTIVE_STATUSES), None)

    now = datetime.now(timezone.utc)

    def _days_remaining(req: AccountDeletionRequestDB) -> int | None:
        if not req.grace_period_ends_at:
            return None
        ends_at = req.grace_period_ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        return (ends_at - now).days

    return {
        "total_requests": len(requests),
        "active_request": (
            {
                "id": active_request.id,
                "status": active_request.status,
                "requested_at": active_request.requested_at.isoformat(),
                "grace_period_ends_at": (
                    active_request.grace_period_ends_at.isoformat() if active_request.grace_period_ends_at else None
                ),
                "days_remaining": _days_remaining(active_request),
            }
            if active_request
            else None
        ),
        "history": [
            {
                "id": req.id,
                "status": req.status,
                "requested_at": req.requested_at.isoformat(),
                "confirmed_at": req.confirmed_at.isoformat() if req.confirmed_at else None,
                "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                "reason": req.reason,
            }
            for req in requests
        ],
    }


async def export_user_data_async(session: AsyncSession, user: User, *, ip_address: str | None) -> dict[str, Any]:
    """Mirrors `export_user_data`'s real data assembly, with bug #1 (see module docstring) fixed:
    `permissions` resolves the effective codes back to real `PermissionDB` rows instead of
    treating each code string as if it already were one."""
    user_row = await session.get(UserDB, user.id)

    roles = await rbac_service.get_user_roles_async(session, user.id)
    effective_codes = await rbac_service.effective_permission_codes_async(session, user.id)
    permissions: list[PermissionDB] = []
    if effective_codes:
        perm_stmt = select(PermissionDB).where(PermissionDB.code.in_(effective_codes))
        permissions = list((await session.execute(perm_stmt)).scalars().all())

    refresh_tokens = list(
        (await session.execute(select(RefreshTokenDB).where(RefreshTokenDB.user_id == user.id))).scalars().all()
    )
    social_connections = list(
        (await session.execute(select(SocialConnectionDB).where(SocialConnectionDB.user_id == user.id))).scalars().all()
    )
    agent_tokens = list(
        (await session.execute(select(AgentTokenDB).where(AgentTokenDB.triggered_by_user_id == user.id)))
        .scalars()
        .all()
    )
    # login_attempts and applications: see module docstring (finding #3) — always `[]` in the
    # real Django export, because `LoginAttempt`/`Application` have no FK back to `User` at all,
    # so `hasattr(request.user, "login_attempts"/"applications")` is always `False` there.
    # Replicated exactly: no query against `LoginAttemptDB`/`ApplicationDB` here either.
    login_attempts: list = []
    applications: list = []
    audit_logs = list((await session.execute(select(AuditLogDB).where(AuditLogDB.user_id == user.id))).scalars().all())

    now = datetime.now(timezone.utc)
    data = {
        "user_info": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_country_code": user_row.phone_country_code if user_row else None,
            "phone_number": user_row.phone_number if user_row else None,
            "is_email_verified": user.email_verified,
            "is_phone_verified": user.phone_verified,
            "is_2fa_enabled": user.mfa_type.value != "none",
            "is_restricted": False,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "roles": [{"code": r.code, "name": r.name, "assigned_at": r.created_at.isoformat()} for r in roles],
        "permissions": [{"code": p.code, "name": p.name, "granted_at": p.created_at.isoformat()} for p in permissions],
        "sessions": [
            {
                "id": rt.id,
                "created_at": rt.created_at.isoformat(),
                "last_used_at": rt.last_used_at.isoformat() if rt.last_used_at else None,
                "ip_address": rt.ip_address,
                "device_info": rt.device_info,
                "is_revoked": rt.revoked_at is not None,
            }
            for rt in refresh_tokens
        ],
        "social_connections": [
            {
                "provider": sc.provider,
                "provider_user_id": sc.provider_user_id,
                "email": sc.email,
                "created_at": sc.created_at.isoformat(),
            }
            for sc in social_connections
        ],
        "login_attempts": [
            {
                "ip_address": la.ip_address,
                "success": la.success,
                "created_at": la.created_at.isoformat(),
                "user_agent": "",
                "failure_reason": la.failure_reason,
            }
            for la in login_attempts
        ],
        "agent_tokens": [
            {
                "agent_id": at.agent_id,
                "status": at.status,
                "created_at": at.created_at.isoformat(),
                "expires_at": at.expires_at.isoformat(),
                "last_used_at": at.last_used_at.isoformat() if at.last_used_at else None,
            }
            for at in agent_tokens
        ],
        "applications": [{"name": app.name, "created_at": app.created_at.isoformat()} for app in applications],
        "audit_logs": [
            {
                "action": log.action,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
                "details": log.details,
            }
            for log in audit_logs
        ],
        "export_metadata": {
            "exported_at": now.isoformat(),
            "export_reason": "user_request",
            "user_id": user.id,
            "compliance": ["RGPD", "GDPR", "CCPA"],
        },
    }

    await _audit_log_async(
        session,
        "data_exported",
        user.id,
        ip_address,
        {"export_reason": "user_request", "exported_at": now.isoformat()},
    )

    return data


# ============================================================
# GDPR admin (Wave G chunk 4/4, z_aud_3 task 12.1) — admin/deletion-requests/*. Contract
# extracted from `views/gdpr_admin_views.py` and `serializers/gdpr_admin_serializers.py`, both
# read in full.
#
# **Two different permissions, not one** — verified by reading each view's own
# `@require_permission(...)` decorator directly, not assumed uniform the way Wave D chunk 4's
# admin-security endpoints turned out to be: `DeletionRequestListView`/`DeletionRequestDetailView`
# require `gdpr.admin`; `ProcessDeletionView`/`ProcessExpiredDeletionsView` require `gdpr.process`
# — a real, deliberate read/write permission split (see `routers/gdpr_admin.py`).
#
# **`DeletionRequestSerializer`'s real fields, verified against `Meta.fields` directly, not the
# `@extend_schema` docs** (which claim `user_agent` is in the list response — it never is; the
# serializer's own `Meta.fields` list omits it entirely): `id`, `user`, `user_email`, `status`,
# `requested_at`, `confirmed_at`, `grace_period_ends_at`, `completed_at`, `ip_address`, `reason`,
# `admin_notes`, `processed_by`, `processed_by_email`, `is_grace_period_expired`.
#
# **`?grace_period_expiring=true` is a real, documented query param that does absolutely
# nothing** — `DeletionRequestListView.get` never reads it anywhere in its real filter logic.
# Accepted and silently ignored here too, same as every other never-implemented documented
# feature already found in this port (`?ordering=user__email` below is the same story).
#
# **Ordering replicated as Django's own literal set-membership check, not through the shared
# `pagination.apply_ordering` helper** — same reasoning as Wave D chunk 4's
# `BlacklistedTokenListView`/`RefreshTokenListView` finding: the real view does
# `if ordering in allowed_fields: queryset = queryset.order_by(ordering)`, where `allowed_fields`
# is exactly `{"requested_at", "-requested_at", "confirmed_at", "-confirmed_at",
# "grace_period_ends_at", "-grace_period_ends_at"}` — no comma-separated multi-field support, no
# `user__email`/`-user__email` despite the docs listing it as a valid `ordering` value, and an
# unrecognized value silently falls back to the model's own default ordering (`-requested_at`)
# rather than raising or being explicitly re-applied.
#
# **`ProcessDeletionView`'s real success response includes an undocumented extra field** —
# `"request": DeletionRequestSerializer(deletion_request).data` — alongside the 6 documented
# fields (`message`, `deletion_completed`, `processed_at`, `data_anonymized`, `audit_log_id`,
# `user_notified`). Replicated exactly (verified by reading the real `return Response({...})`
# call, not the `@extend_schema` docs, which omit it).
#
# **`ProcessExpiredDeletionsView`'s real response is just `{"message", "processed", "failed"}`**
# — not the docs' `processed_count`/`failed_count`/`skipped_count`/`processing_time`/`details`.
#
# **`execute_deletion` reuses `admin_user_service.soft_delete_async`** — the same lighter
# anonymization path (email rewritten, name cleared, `is_deleted`/`deleted_at` set) Wave D chunk 3
# already ported for the admin-user-management soft-delete action; Django's own
# `AccountDeletionRequest.execute_deletion` calls `self.user.soft_delete()`, the identical model
# method.
# ============================================================

_ORDERING_ALLOWED = {
    "requested_at",
    "-requested_at",
    "confirmed_at",
    "-confirmed_at",
    "grace_period_ends_at",
    "-grace_period_ends_at",
}


async def _user_email(session: AsyncSession, user_id: str | None) -> str | None:
    if not user_id:
        return None
    row = await session.get(UserDB, user_id)
    return row.email if row else None


async def serialize_deletion_request_async(session: AsyncSession, req: AccountDeletionRequestDB) -> dict:
    return {
        "id": req.id,
        "user": req.user_id,
        "user_email": await _user_email(session, req.user_id),
        "status": req.status,
        "requested_at": req.requested_at.isoformat(),
        "confirmed_at": req.confirmed_at.isoformat() if req.confirmed_at else None,
        "grace_period_ends_at": req.grace_period_ends_at.isoformat() if req.grace_period_ends_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "ip_address": req.ip_address,
        "reason": req.reason,
        "admin_notes": req.admin_notes,
        "processed_by": req.processed_by_id,
        "processed_by_email": await _user_email(session, req.processed_by_id),
        "is_grace_period_expired": bool(
            req.grace_period_ends_at
            and req.grace_period_ends_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
        ),
    }


async def list_deletion_requests_async(
    session: AsyncSession,
    *,
    user_id: str | None,
    status: str | None,
    date_from: str | None,
    date_to: str | None,
    ordering: str,
    page: int,
    page_size: int,
) -> tuple[list[AccountDeletionRequestDB], int]:
    stmt = select(AccountDeletionRequestDB)
    count_stmt = select(func.count(AccountDeletionRequestDB.id))

    if user_id:
        stmt = stmt.where(AccountDeletionRequestDB.user_id == user_id)
        count_stmt = count_stmt.where(AccountDeletionRequestDB.user_id == user_id)
    if status:
        stmt = stmt.where(AccountDeletionRequestDB.status == status)
        count_stmt = count_stmt.where(AccountDeletionRequestDB.status == status)
    if date_from:
        stmt = stmt.where(func.date(AccountDeletionRequestDB.requested_at) >= date_from)
        count_stmt = count_stmt.where(func.date(AccountDeletionRequestDB.requested_at) >= date_from)
    if date_to:
        stmt = stmt.where(func.date(AccountDeletionRequestDB.requested_at) <= date_to)
        count_stmt = count_stmt.where(func.date(AccountDeletionRequestDB.requested_at) <= date_to)

    if ordering in _ORDERING_ALLOWED:
        column = getattr(AccountDeletionRequestDB, ordering.lstrip("-"))
        stmt = stmt.order_by(column.desc() if ordering.startswith("-") else column.asc())
    else:
        stmt = stmt.order_by(AccountDeletionRequestDB.requested_at.desc())

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total


async def get_deletion_request_async(session: AsyncSession, request_id: str) -> AccountDeletionRequestDB | None:
    return await session.get(AccountDeletionRequestDB, request_id)


async def process_deletion_async(
    session: AsyncSession,
    deletion_request: AccountDeletionRequestDB,
    *,
    confirmation: str,
    admin_notes: str,
    admin_id: str,
) -> tuple[bool, dict[str, Any] | None, str, str | None]:
    """Mirrors `ProcessDeletionView.post`. Returns `(success, data, error, error_code)`."""
    from tenxyte.adapters.fastapi.admin_user_service import soft_delete_async

    if deletion_request.status != "confirmed":
        return (
            False,
            None,
            f'Cannot process request with status "{deletion_request.status}". Only confirmed requests can be processed.',
            "REQUEST_NOT_CONFIRMED",
        )

    if confirmation != "PERMANENTLY DELETE":
        return False, None, "Explicit confirmation required", "CONFIRMATION_REQUIRED"

    if admin_notes:
        deletion_request.admin_notes = admin_notes
        await session.commit()

    user_row = await session.get(UserDB, deletion_request.user_id)
    if user_row is None:
        return False, None, "Failed to process deletion", "PROCESSING_FAILED"

    await soft_delete_async(session, user_row)

    deletion_request.status = "completed"
    deletion_request.completed_at = datetime.now(timezone.utc)
    deletion_request.processed_by_id = admin_id
    await session.commit()
    await session.refresh(deletion_request)

    await _audit_log_async(
        session,
        "deletion_request_executed_admin",
        deletion_request.user_id,
        None,
        {"request_id": deletion_request.id, "admin_id": admin_id},
    )

    return (
        True,
        {
            "message": "Account deletion processed successfully",
            "deletion_completed": True,
            "processed_at": deletion_request.completed_at.isoformat(),
            "data_anonymized": True,
            "audit_log_id": deletion_request.id,
            "user_notified": True,
            "request": await serialize_deletion_request_async(session, deletion_request),
        },
        "",
        None,
    )


async def process_expired_deletions_async(session: AsyncSession, *, admin_id: str) -> dict[str, Any]:
    """Mirrors `ProcessExpiredDeletionsView.post` — processes every `confirmed` request whose
    grace period has passed."""
    from tenxyte.adapters.fastapi.admin_user_service import soft_delete_async

    now = datetime.now(timezone.utc)
    stmt = select(AccountDeletionRequestDB).where(
        AccountDeletionRequestDB.status == "confirmed", AccountDeletionRequestDB.grace_period_ends_at < now
    )
    expired = list((await session.execute(stmt)).scalars().all())

    processed = 0
    failed = 0
    for req in expired:
        user_row = await session.get(UserDB, req.user_id)
        if user_row is None:
            failed += 1
            continue
        await soft_delete_async(session, user_row)
        req.status = "completed"
        req.completed_at = now
        req.processed_by_id = admin_id
        await session.commit()
        processed += 1
        await _audit_log_async(session, "deletion_request_processed", req.user_id, None, {"request_id": req.id})

    return {"message": f"{processed} deletion(s) processed, {failed} failed", "processed": processed, "failed": failed}
