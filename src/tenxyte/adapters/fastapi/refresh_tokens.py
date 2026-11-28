"""
Refresh-token issuance and redemption for the Reference_Stack (spec z_aud_3, Wave A) —
`JWTService.generate_new_token_pair`/`generate_access_token` produce an *opaque* refresh token
(a bare UUID4 string, not a JWT: see `jwt_service.py`'s `generate_new_token_pair`), so it can only
ever be redeemed again by looking it up in storage. `JWTService.refresh_tokens_async` is NOT used
here — reading it shows it imports `tenxyte.models.RefreshToken` directly (Django's ORM model),
making it unusable from a Django-less FastAPI process; it always fails closed (returns `None`)
outside a Django environment. This module is the Reference_Stack's own equivalent, storing only a
SHA-256 hash of the token (`RefreshTokenDB.token_hash`) — the raw token is never persisted,
mirroring the Django_Adapter's own invariant.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import RefreshTokenDB


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    session: AsyncSession,
    user_id: str,
    *,
    lifetime_seconds: int,
    device_id: str | None = None,
    ip_address: str | None = None,
) -> str:
    """Create a new opaque refresh token, persist only its hash, return the raw token (shown to
    the caller exactly once — it can never be recovered from storage afterwards). `ip_address` is
    optional (added for Wave G's social-auth chunk, task 12.1 — `RefreshTokenDB.ip_address` has
    existed since Wave D chunk 4 but no earlier caller had a real value to pass)."""
    raw_token = str(uuid4())
    row = RefreshTokenDB(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        device_info=device_id or "",
        ip_address=ip_address,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=lifetime_seconds),
    )
    session.add(row)
    await session.commit()
    return raw_token


async def redeem_refresh_token(session: AsyncSession, raw_token: str) -> RefreshTokenDB | None:
    """The stored row for `raw_token`, or None if it doesn't exist, is revoked, or has expired —
    never raises, mirroring the Django_Adapter's fail-closed-but-silent posture on a bad token."""
    if not raw_token:
        return None

    stmt = select(RefreshTokenDB).where(RefreshTokenDB.token_hash == hash_token(raw_token))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if row.is_revoked:
        return None

    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    # Wave D chunk 4 follow-up (z_aud_3 task 10.1) — mirrors Django's RefreshToken.last_used_at
    # (auto_now=True: touched on every save, including revoke()) so admin/refresh-tokens/ has a
    # real value to show.
    row.last_used_at = datetime.now(timezone.utc)
    await session.commit()

    return row


async def revoke_refresh_token_row(session: AsyncSession, row: RefreshTokenDB) -> None:
    row.is_revoked = True
    row.last_used_at = datetime.now(timezone.utc)
    await session.commit()


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> bool:
    """Best-effort revoke by raw token value — True if a live row was found and revoked."""
    row = await redeem_refresh_token(session, raw_token)
    if row is None:
        return False
    await revoke_refresh_token_row(session, row)
    return True


async def revoke_all_for_user(session: AsyncSession, user_id: str) -> int:
    """Revoke every still-live refresh token for a user (logout/all). Returns the count revoked."""
    stmt = select(RefreshTokenDB).where(RefreshTokenDB.user_id == user_id, RefreshTokenDB.is_revoked.is_(False))
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.is_revoked = True
        row.last_used_at = now
    await session.commit()
    return len(rows)
