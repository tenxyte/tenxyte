"""
Async_Ports for `UserRepository` (spec z_aud_3, Requirement 1).

Generalizes the JWT_Async_Pattern already in production in `core/jwt_service.py` (a native
async method when the implementation provides one, otherwise a generic `asyncio.to_thread`
bridge — never a direct sync call from an async context) to the repository layer.

This module is additive: `ports/repositories.py`'s sync `UserRepository` is untouched, and every
existing consumer of it keeps working exactly as before. The other "request-path storage ports"
Requirement 1.1 also covers already have their own async protocols colocated with their service,
following the codebase's existing convention (see `core/totp_service.py`'s `AsyncTOTPStorage`,
`core/magic_link_service.py`'s async storage protocols, `core/cache_service.py`'s `CacheService`
ABC, which already declares its async methods directly) — this module does not duplicate those.
It adds the one still-missing piece at the port layer: `UserRepository`.

Resolution rule (Requirement 1.4): always go through `as_async()` from an async context. Never
call a sync repository method directly from `async def` code.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from tenxyte.ports.repositories import MFAType, User, UserRepository


class AsyncUserRepository(ABC):
    """
    Exact async mirror of `UserRepository` (spec z_aud_3, Requirement 1.1): same methods, same
    contracts, `async def` signatures. No additional methods — a port is a contract, not a place
    to grow convenience helpers (design.md: "manual and tested, not metaprogrammed").
    """

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: str) -> bool: ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None) -> list[User]: ...

    @abstractmethod
    async def count(self, filters: dict[str, Any] | None = None) -> int: ...

    @abstractmethod
    async def update_last_login(self, user_id: str, timestamp: datetime) -> bool: ...

    @abstractmethod
    async def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool: ...

    @abstractmethod
    async def verify_email(self, user_id: str) -> bool: ...


class SyncToAsyncUserRepository(AsyncUserRepository):
    """
    Sync_Bridge (Requirement 1.3): wraps any sync `UserRepository` implementation into
    `AsyncUserRepository` via `asyncio.to_thread`, so an existing sync repository (e.g. the
    Django ORM-backed one) can be used from async code without ever blocking the event loop.
    """

    def __init__(self, sync_repo: UserRepository):
        self._sync = sync_repo

    async def get_by_id(self, user_id: str) -> User | None:
        return await asyncio.to_thread(self._sync.get_by_id, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await asyncio.to_thread(self._sync.get_by_email, email)

    async def create(self, user: User) -> User:
        return await asyncio.to_thread(self._sync.create, user)

    async def update(self, user: User) -> User:
        return await asyncio.to_thread(self._sync.update, user)

    async def delete(self, user_id: str) -> bool:
        return await asyncio.to_thread(self._sync.delete, user_id)

    async def list_all(self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None) -> list[User]:
        return await asyncio.to_thread(self._sync.list_all, skip, limit, filters)

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        return await asyncio.to_thread(self._sync.count, filters)

    async def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        return await asyncio.to_thread(self._sync.update_last_login, user_id, timestamp)

    async def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        return await asyncio.to_thread(self._sync.set_mfa_secret, user_id, mfa_type, secret)

    async def verify_email(self, user_id: str) -> bool:
        return await asyncio.to_thread(self._sync.verify_email, user_id)


def as_async(repo: UserRepository | AsyncUserRepository) -> AsyncUserRepository:
    """
    Normalized async resolution (Requirement 1.4, Property 6): the single entry point async
    consumers use to obtain an `AsyncUserRepository` from whatever they were handed. Returns the
    repository itself when it is already a native `AsyncUserRepository`; wraps it in the
    Sync_Bridge otherwise. Never calls a sync method directly.
    """
    if isinstance(repo, AsyncUserRepository):
        return repo
    return SyncToAsyncUserRepository(repo)
