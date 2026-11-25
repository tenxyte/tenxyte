"""
`AsyncMagicLinkRepository` + `AsyncUserLookup` for the Reference_Stack (spec z_aud_3, Wave C, task
7.1) — backs `core.magic_link_service.MagicLinkService`, which is already fully framework-agnostic
and async-complete (no Django imports anywhere in the file; confirmed by reading it directly).

Async-only, same convention as `SQLAlchemyTOTPStorage`: the sync Protocol methods raise
`NotImplementedError` since nothing here ever calls them (`MagicLinkService`'s async methods
detect and prefer the `_async` sibling via `hasattr`, never falling back to the sync one when it's
present).

Tokens are stored as a SHA-256 hash (`MagicLinkTokenDB.token_hash`) — same invariant as
`refresh_tokens.py`'s `RefreshTokenDB.token_hash` — the raw token exists in plaintext only once,
returned by `MagicLinkService.request_magic_link_async` at generation time. `email` isn't a column
on `MagicLinkTokenDB` (mirrors Django's own `MagicLinkToken` model, which has none either — the
Django_Adapter's `DjangoMagicLinkRepository.get_by_token` derives it via `token_obj.user.email`, a
join); this repository does the same via a second `UserDB` lookup.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.auth_lookup import _locked_key
from tenxyte.adapters.fastapi.models_sa import MagicLinkTokenDB, UserDB
from tenxyte.core.cache_service import CacheService
from tenxyte.core.magic_link_service import MagicLinkToken


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _as_aware(dt: datetime) -> datetime:
    """DB-loaded datetimes come back tz-naive from the aiosqlite dev driver, even though we always
    write tz-aware UTC values — normalize before comparing against `datetime.now(tz=...)`."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class SQLAlchemyMagicLinkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _email_for(self, user_id: str) -> str:
        user = await self.session.get(UserDB, user_id)
        return user.email if user else ""

    async def create_async(
        self,
        token_hash: str,
        user_id: str,
        email: str,
        application_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expiry_minutes: int = 15,
    ) -> MagicLinkToken:
        row = MagicLinkTokenDB(
            user_id=user_id,
            application_id=application_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return MagicLinkToken(
            id=row.id,
            token="",
            user_id=row.user_id,
            email=email,
            application_id=row.application_id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=_as_aware(row.created_at),
            expires_at=_as_aware(row.expires_at),
            used_at=None,
            is_used=False,
        )

    def create(self, *args, **kwargs) -> MagicLinkToken:
        raise NotImplementedError(
            "SQLAlchemyMagicLinkRepository is async-only in the Reference_Stack; use create_async."
        )

    async def get_by_token_async(self, token: str) -> MagicLinkToken | None:
        stmt = select(MagicLinkTokenDB).where(MagicLinkTokenDB.token_hash == _hash_token(token))
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return MagicLinkToken(
            id=row.id,
            token="",
            user_id=row.user_id,
            email=await self._email_for(row.user_id),
            application_id=row.application_id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=_as_aware(row.created_at),
            expires_at=_as_aware(row.expires_at),
            used_at=_as_aware(row.used_at) if row.used_at else None,
            is_used=row.is_used,
        )

    def get_by_token(self, token: str) -> MagicLinkToken | None:
        raise NotImplementedError(
            "SQLAlchemyMagicLinkRepository is async-only in the Reference_Stack; use get_by_token_async."
        )

    async def invalidate_user_tokens_async(self, user_id: str, application_id: str | None = None) -> int:
        stmt = update(MagicLinkTokenDB).where(MagicLinkTokenDB.user_id == user_id, MagicLinkTokenDB.is_used == False)
        if application_id:
            stmt = stmt.where(MagicLinkTokenDB.application_id == application_id)
        stmt = stmt.values(is_used=True, used_at=datetime.now(timezone.utc)).execution_options(
            synchronize_session=False
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    def invalidate_user_tokens(self, user_id: str, application_id: str | None = None) -> int:
        raise NotImplementedError(
            "SQLAlchemyMagicLinkRepository is async-only in the Reference_Stack; use invalidate_user_tokens_async."
        )

    async def consume_async(self, token_id: str) -> bool:
        row = await self.session.get(MagicLinkTokenDB, token_id)
        if row is None:
            return False
        row.is_used = True
        row.used_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    def consume(self, token_id: str) -> bool:
        raise NotImplementedError(
            "SQLAlchemyMagicLinkRepository is async-only in the Reference_Stack; use consume_async."
        )


class SQLAlchemyUserLookup:
    """`AsyncUserLookup` for `MagicLinkService` — thin wrapper over `UserDB` plus the same
    cache-based lockout state `auth_lookup.py`'s `_BasePasswordLookup` already uses (Wave A), so
    "locked" means the same thing everywhere in the Reference_Stack."""

    def __init__(self, session: AsyncSession, cache_service: CacheService):
        self.session = session
        self.cache_service = cache_service

    async def get_by_email_async(self, email: str) -> dict | None:
        stmt = select(UserDB).where(UserDB.email == email)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {"id": row.id, "email": row.email, "first_name": row.first_name}

    def get_by_email(self, email: str) -> dict | None:
        raise NotImplementedError("SQLAlchemyUserLookup is async-only in the Reference_Stack; use get_by_email_async.")

    async def is_active_async(self, user_id: str) -> bool:
        row = await self.session.get(UserDB, user_id)
        return bool(row and row.is_active)

    def is_active(self, user_id: str) -> bool:
        raise NotImplementedError("SQLAlchemyUserLookup is async-only in the Reference_Stack; use is_active_async.")

    async def is_locked_async(self, user_id: str) -> bool:
        return await self.cache_service.exists_async(_locked_key(user_id))

    def is_locked(self, user_id: str) -> bool:
        raise NotImplementedError("SQLAlchemyUserLookup is async-only in the Reference_Stack; use is_locked_async.")
