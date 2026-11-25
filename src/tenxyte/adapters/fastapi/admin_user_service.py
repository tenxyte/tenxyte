"""
Framework-agnostic-in-spirit admin-user-management service for the Reference_Stack (spec z_aud_3,
Wave D chunk 3/5, task 10.1) — admin/users/* (list/detail/update/soft-delete/ban/unban/lock/
unlock). Contract extracted from `views/user_views.py` (`UserListView`, `UserDetailView`,
`UserBanView`, `UserUnbanView`, `UserLockView`, `UserUnlockView`),
`serializers/user_admin_serializers.py`, `filters.py` (`apply_user_filters`), and the ban/lock/
soft-delete logic actually exercised by `adapters/django/repositories.py`'s
`DjangoUserRepository.ban/unban/lock/unlock/soft_delete` plus `models/auth.py`'s
`User.lock_account`/`unlock_account`/`soft_delete` — NOT `AbstractUser.delete()` (a second,
heavier anonymization path Django defines but the admin API never calls; see `soft_delete_async`
below for the real behavior difference).

**Two independent findings, verified by reading the Core repository code (not assumed), replicated
rather than "fixed"**:

1. `PATCH admin/users/<id>/`'s `AdminUserUpdateSerializer` validates `is_staff`/`is_superuser`/
   `max_sessions`/`max_devices` as acceptable input fields, but `DjangoUserRepository.update_user()`
   — the only thing the view actually calls to persist the change — only recognizes `first_name`,
   `last_name`, `email`, `is_active`, `is_email_verified`, `phone_country_code`, `phone_number`,
   `is_phone_verified`, `username`, `bio`, `timezone`, `language`, `custom_fields`. Submitting
   `is_staff`/`is_superuser`/`max_sessions`/`max_devices` passes validation and is silently
   discarded — no error, no effect. `must_change_password` is the one exception: the view special-
   cases it (`DJANGO_ONLY_FIELDS`) and applies it directly to the Django model, bypassing the Core
   repository entirely.
2. `UserBanView`/`UserLockView` both accept a `reason` field (documented as "stored in audit log")
   but `DjangoUserRepository.ban()`/`lock()` never persist it anywhere — there is no `AuditLog`
   write in either path (Wave D chunk 4 will add real audit-log persistence, but even once it
   exists this specific call site doesn't feed it). `reason` is accepted, validated, and dropped.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi import rbac_service
from tenxyte.adapters.fastapi.models_sa import RoleDB, UserDB, user_roles_table
from tenxyte.adapters.fastapi.pagination import apply_ordering

# ============================================================
# Serialization — matches AdminUserListSerializer/AdminUserDetailSerializer exactly.
# ============================================================


async def serialize_user_list_item_async(session: AsyncSession, user: UserDB) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_active": user.is_active,
        "is_locked": user.is_locked,
        "is_banned": user.is_banned,
        "is_deleted": user.is_deleted,
        "is_email_verified": user.email_verified,
        "is_phone_verified": user.phone_verified,
        "is_2fa_enabled": user.mfa_type.value != "none",
        "roles": await rbac_service.get_all_role_codes_async(session, user.id),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


async def serialize_user_detail_async(session: AsyncSession, user: UserDB) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "phone_country_code": user.phone_country_code,
        "phone_number": user.phone_number,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_active": user.is_active,
        "is_locked": user.is_locked,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "is_banned": user.is_banned,
        "is_deleted": user.is_deleted,
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        "is_email_verified": user.email_verified,
        "is_phone_verified": user.phone_verified,
        "is_2fa_enabled": user.mfa_type.value != "none",
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "max_sessions": user.max_sessions,
        "max_devices": user.max_devices,
        "roles": await rbac_service.get_all_role_codes_async(session, user.id),
        "permissions": await rbac_service.effective_permission_codes_async(session, user.id),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ============================================================
# Lookup / listing
# ============================================================


async def get_user_by_id_async(session: AsyncSession, user_id: str) -> UserDB | None:
    return await session.get(UserDB, user_id)


async def list_users_async(
    session: AsyncSession,
    *,
    search: str = "",
    is_active: bool | None = None,
    is_locked: bool | None = None,
    is_banned: bool | None = None,
    is_deleted: bool | None = None,
    is_email_verified: bool | None = None,
    is_2fa_enabled: bool | None = None,
    role: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ordering: str = "-created_at",
    page: int,
    page_size: int,
) -> tuple[list[UserDB], int]:
    stmt = select(UserDB)
    count_stmt = select(func.count(UserDB.id))

    if search:
        like = f"%{search}%"
        clause = or_(UserDB.email.ilike(like), UserDB.first_name.ilike(like), UserDB.last_name.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    boolean_filters = {
        UserDB.is_active: is_active,
        UserDB.is_locked: is_locked,
        UserDB.is_banned: is_banned,
        UserDB.is_deleted: is_deleted,
        UserDB.email_verified: is_email_verified,
    }
    for column, value in boolean_filters.items():
        if value is not None:
            stmt = stmt.where(column == value)
            count_stmt = count_stmt.where(column == value)

    if is_2fa_enabled is not None:
        clause = (UserDB.mfa_type != "none") if is_2fa_enabled else (UserDB.mfa_type == "none")
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if role:
        role_clause = UserDB.id.in_(
            select(user_roles_table.c.user_id)
            .join(RoleDB, RoleDB.id == user_roles_table.c.role_id)
            .where(RoleDB.code == role)
        )
        stmt = stmt.where(role_clause)
        count_stmt = count_stmt.where(role_clause)

    if date_from:
        stmt = stmt.where(UserDB.created_at >= date_from)
        count_stmt = count_stmt.where(UserDB.created_at >= date_from)
    if date_to:
        stmt = stmt.where(UserDB.created_at <= date_to)
        count_stmt = count_stmt.where(UserDB.created_at <= date_to)

    allowed_ordering = {
        "email": UserDB.email,
        "created_at": UserDB.created_at,
        "last_login": UserDB.last_login,
        "first_name": UserDB.first_name,
    }
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="-created_at")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


# ============================================================
# Update / soft-delete
# ============================================================

# Of everything AdminUserUpdateSerializer accepts (first_name, last_name, is_active, is_staff,
# is_superuser, max_sessions, max_devices, must_change_password), only these three are also in
# DjangoUserRepository.update_user()'s whitelist and therefore actually persisted by the real
# admin endpoint — is_staff/is_superuser/max_sessions/max_devices are deliberately excluded here,
# see module docstring finding (1). must_change_password is handled separately below (Django
# special-cases it too — applied directly to the model, bypassing the Core repository).
_CORE_UPDATE_FIELDS = {"first_name", "last_name", "is_active"}


async def update_user_async(session: AsyncSession, user: UserDB, fields: dict) -> UserDB:
    for key in _CORE_UPDATE_FIELDS:
        if key in fields:
            setattr(user, key, fields[key])
    if "must_change_password" in fields:
        user.must_change_password = fields["must_change_password"]
    await session.commit()
    await session.refresh(user)
    return user


async def soft_delete_async(session: AsyncSession, user: UserDB) -> None:
    """Mirrors `User.soft_delete()` (the lighter of Django's two anonymization paths — the admin
    API's Core repository calls this one, never the heavier `AbstractUser.delete()` override that
    also clears phone/TOTP/backup codes): email rewritten to `deleted_{id}@deleted.local`,
    first/last name cleared, `is_deleted`/`deleted_at`/`anonymization_token` set, account
    deactivated. Refresh-token revocation isn't replicated — the Reference_Stack has no persisted-
    session table to revoke against yet (refresh tokens are looked up by hash only)."""
    import secrets

    user.email = f"deleted_{user.id}@deleted.local"
    user.first_name = ""
    user.last_name = ""
    user.is_deleted = True
    user.deleted_at = datetime.now(dt_timezone.utc)
    user.is_active = False
    user.anonymization_token = secrets.token_urlsafe(32)
    await session.commit()


# ============================================================
# Ban / unban / lock / unlock
# ============================================================


async def ban_async(session: AsyncSession, user: UserDB) -> None:
    """`reason` is deliberately not a parameter — see module docstring finding (2)."""
    user.is_active = False
    user.is_banned = True
    await session.commit()
    await session.refresh(user)


async def unban_async(session: AsyncSession, user: UserDB) -> None:
    user.is_active = True
    user.is_banned = False
    await session.commit()
    await session.refresh(user)


async def lock_async(session: AsyncSession, user: UserDB, *, duration_minutes: int) -> int:
    """Mirrors `User.lock_account()`'s exponential-backoff escalation exactly: the 2nd+ consecutive
    lock multiplies the requested duration by `2 ** (lockout_count - 1)`, capped at 1440 minutes
    (Django's `LOCKOUT_MAX_DURATION_MINUTES` default — the Reference_Stack has no equivalent
    settings override yet, so the cap is hardcoded to match the default). Returns the actual
    (possibly escalated) duration applied, since the response message embeds it."""
    user.lockout_count += 1
    if user.lockout_count > 1:
        escalated = duration_minutes * (2 ** (user.lockout_count - 1))
        duration_minutes = min(escalated, 1440)

    user.is_locked = True
    user.locked_until = datetime.now(dt_timezone.utc) + timedelta(minutes=duration_minutes)
    await session.commit()
    await session.refresh(user)
    return duration_minutes


async def unlock_async(session: AsyncSession, user: UserDB) -> None:
    user.is_locked = False
    user.locked_until = None
    await session.commit()
    await session.refresh(user)
