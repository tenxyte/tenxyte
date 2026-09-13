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

import bcrypt

from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.cache_service import CacheService
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

_FAILED_LOGIN_WINDOW_SECONDS = 1800  # 30 minutes — matches the Django_Adapter's own window


def _failed_login_key(user_id: str) -> str:
    return f"failed_login_{user_id}"


def _locked_key(user_id: str) -> str:
    return f"account_locked:{user_id}"


class SQLAlchemyEmailPasswordLookup:
    """Email-based login lookup — the Reference_Stack's equivalent of the Django_Adapter's
    `_EmailPasswordLookup`. Phone-based login (`_PhonePasswordLookup`'s counterpart) is deferred:
    the Reference_Stack's `UserDB` has no indexed phone columns yet (phone data lives in the
    Core `User.metadata` dict, same as the register flow), so a real phone lookup needs schema
    work that's out of scope for this pass — tracked as a follow-up to task 5.1."""

    def __init__(self, user_repo: SQLAlchemyAsyncUserRepository, cache_service: CacheService, settings: Settings):
        self.user_repo = user_repo
        self.cache_service = cache_service
        self.settings = settings

    async def get_by_identifier_async(self, identifier: object) -> User | None:
        return await self.user_repo.get_by_email(str(identifier))

    async def is_account_locked_async(self, user_id: str) -> bool:
        return await self.cache_service.exists_async(_locked_key(user_id))

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
