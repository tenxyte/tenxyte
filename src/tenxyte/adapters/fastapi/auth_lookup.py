"""
`PasswordUserLookup` for the Reference_Stack (spec z_aud_3, Wave A) — feeds
`AuthenticationService.authenticate_async` (see `core/auth_service.py`). Exposes only the
`*_async` siblings (`get_by_identifier_async`, `is_account_locked_async`, `check_password_async`,
`record_failed_login_async`): `authenticate_async` detects and calls these directly via
`hasattr`, so the sync `PasswordUserLookup` methods are never needed here — an `AsyncSession`
query can't honestly be answered from a sync method without its own blocking engine anyway.

Lockout is modeled on the cache port rather than dedicated `is_locked`/`locked_until` columns —
`CacheService` already has exactly the counting primitives this needs (`increment_async`,
`expire_async`, `set_async`/`exists_async`), and using it keeps the Reference_Stack's `UserDB`
schema free of a Django-specific concept. Thresholds come straight from `Settings`
(`max_login_attempts`, `lockout_duration`), matching the Django_Adapter's configured values
even though the storage mechanism differs.
"""

from __future__ import annotations

from datetime import datetime, timezone

import bcrypt

from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.cache_service import CacheService
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

_FAILED_LOGIN_WINDOW_SECONDS = 1800  # 30 minutes — matches the Django_Adapter's own window


def _failed_login_key(user_id: str) -> str:
    return f"failed_login_{user_id}"


def _locked_key(user_id: str) -> str:
    return f"account_locked:{user_id}"


class _BasePasswordLookup:
    """Shared lockout/password-check logic for both identifier types — the Django_Adapter's
    `_EmailPasswordLookup` and `_PhonePasswordLookup` differ only in how they resolve an
    identifier to a user, never in how lockout or password verification works."""

    def __init__(self, user_repo: SQLAlchemyAsyncUserRepository, cache_service: CacheService, settings: Settings):
        self.user_repo = user_repo
        self.cache_service = cache_service
        self.settings = settings

    async def is_account_locked_async(self, user_id: str) -> bool:
        """Mirrors `DjangoUserRepository.is_account_locked()` exactly — that one checks the cache
        key FIRST, then falls back to `UserDB.is_locked`/`locked_until` (the administrative lock
        set by `POST /admin/users/{id}/lock/`). This adapter was missing that fallback entirely
        (found empirically: an admin-locked user could still log in fine against this backend,
        confirmed by comparing against the Django view's real behavior, not assumed) — the cache
        key only ever covers the AUTOMATIC failed-attempts lockout (`record_failed_login_async`
        below), never the administrative one. Queries `UserDB` directly via the repository's own
        session rather than through `get_by_id()` — the agnostic `User` port dataclass
        (`ports/repositories.py`) has no `is_locked`/`locked_until` fields at all."""
        if await self.cache_service.exists_async(_locked_key(user_id)):
            return True
        db_user = await self.user_repo.session.get(UserDB, user_id)
        if db_user is None or not db_user.is_locked or not db_user.locked_until:
            return False
        locked_until = db_user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)

    async def check_password_async(self, user_id: str, password: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.password_hash:
            return False
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            # bcrypt hard-fails past 72 bytes — no stored hash can legitimately correspond to a
            # password this long anyway (registration itself rejects it), so this is simply a
            # wrong password, not an error.
            return False
        return bcrypt.checkpw(password_bytes, user.password_hash.encode("utf-8"))

    async def record_failed_login_async(self, user_id: str) -> None:
        key = _failed_login_key(user_id)
        count = await self.cache_service.increment_async(key)
        if count == 1:
            await self.cache_service.expire_async(key, _FAILED_LOGIN_WINDOW_SECONDS)
        if count >= self.settings.max_login_attempts:
            await self.cache_service.set_async(_locked_key(user_id), True, timeout=self.settings.lockout_duration)


class SQLAlchemyEmailPasswordLookup(_BasePasswordLookup):
    """Email-based login lookup — the Reference_Stack's equivalent of the Django_Adapter's
    `_EmailPasswordLookup`."""

    async def get_by_identifier_async(self, identifier: object) -> User | None:
        return await self.user_repo.get_by_email(str(identifier))


class SQLAlchemyPhonePasswordLookup(_BasePasswordLookup):
    """Phone-based login lookup — the Reference_Stack's equivalent of the Django_Adapter's
    `_PhonePasswordLookup`. `identifier` is a `(phone_country_code, phone_number)` tuple, matching
    `PasswordUserLookup`'s own documented convention that `identifier` is adapter-defined."""

    async def get_by_identifier_async(self, identifier: object) -> User | None:
        phone_country_code, phone_number = identifier
        return await self.user_repo.get_by_phone(phone_country_code, phone_number)
