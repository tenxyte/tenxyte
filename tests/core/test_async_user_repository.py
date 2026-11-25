"""
Property-based tests for Async_Ports / UserRepository (spec z_aud_3, Requirement 1).

Feature: z_aud_3, Property 4: Équivalence sémantique sync/async des ports
Feature: z_aud_3, Property 6: Résolution async normalisée

Network/DB-free: uses a small in-memory UserRepository test double, exactly the kind of
implementation an adapter author would write.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from tenxyte.ports.async_repositories import AsyncUserRepository, SyncToAsyncUserRepository, as_async
from tenxyte.ports.repositories import MFAType, User, UserRepository

pytestmark = [pytest.mark.no_django]

USER_IDS = ["u1", "u2", "u3"]


class InMemoryUserRepository(UserRepository):
    """A minimal, fully sync reference implementation — the kind of thing an adapter author
    writes, used here purely as a test double."""

    def __init__(self):
        self._users: dict[str, User] = {}

    def get_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    def create(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def update(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def delete(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None

    def list_all(self, skip: int = 0, limit: int = 100, filters: dict | None = None) -> list[User]:
        items = list(self._users.values())
        return items[skip : skip + limit]

    def count(self, filters: dict | None = None) -> int:
        return len(self._users)

    def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user.last_login = timestamp
        return True

    def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user.mfa_type = mfa_type
        user.mfa_secret = secret
        return True

    def verify_email(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user.email_verified = True
        return True


def _apply_sync(repo: UserRepository, op: tuple):
    name = op[0]
    if name == "create":
        _, uid, suffix = op
        return repo.create(User(id=uid, email=f"{uid}-{suffix}@example.com"))
    if name == "get_by_id":
        return repo.get_by_id(op[1])
    if name == "update_last_login":
        return repo.update_last_login(op[1], datetime(2026, 1, 1, tzinfo=timezone.utc))
    if name == "set_mfa_secret":
        return repo.set_mfa_secret(op[1], MFAType.TOTP, "secret")
    if name == "verify_email":
        return repo.verify_email(op[1])
    if name == "delete":
        return repo.delete(op[1])
    raise AssertionError(f"unknown op {name}")


async def _apply_async(repo: AsyncUserRepository, op: tuple):
    name = op[0]
    if name == "create":
        _, uid, suffix = op
        return await repo.create(User(id=uid, email=f"{uid}-{suffix}@example.com"))
    if name == "get_by_id":
        return await repo.get_by_id(op[1])
    if name == "update_last_login":
        return await repo.update_last_login(op[1], datetime(2026, 1, 1, tzinfo=timezone.utc))
    if name == "set_mfa_secret":
        return await repo.set_mfa_secret(op[1], MFAType.TOTP, "secret")
    if name == "verify_email":
        return await repo.verify_email(op[1])
    if name == "delete":
        return await repo.delete(op[1])
    raise AssertionError(f"unknown op {name}")


_op_strategy = st.one_of(
    st.tuples(st.just("create"), st.sampled_from(USER_IDS), st.integers(min_value=0, max_value=5)),
    st.tuples(st.just("get_by_id"), st.sampled_from(USER_IDS)),
    st.tuples(st.just("update_last_login"), st.sampled_from(USER_IDS)),
    st.tuples(st.just("set_mfa_secret"), st.sampled_from(USER_IDS)),
    st.tuples(st.just("verify_email"), st.sampled_from(USER_IDS)),
    st.tuples(st.just("delete"), st.sampled_from(USER_IDS)),
)


@given(ops=st.lists(_op_strategy, min_size=1, max_size=15))
@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_4_sync_and_bridge_produce_identical_states_and_results(ops):
    sync_repo = InMemoryUserRepository()
    bridge_backing = InMemoryUserRepository()
    bridged = as_async(bridge_backing)
    assert isinstance(bridged, SyncToAsyncUserRepository)

    sync_results = [_apply_sync(sync_repo, op) for op in ops]

    async def run_bridge():
        return [await _apply_async(bridged, op) for op in ops]

    bridge_results = asyncio.run(run_bridge())

    assert sync_results == bridge_results
    assert sync_repo._users == bridge_backing._users


class _SpyAsyncUserRepository(AsyncUserRepository):
    """A native async implementation, to prove `as_async()` returns it unchanged (Property 6)."""

    def __init__(self):
        self.calls: list[str] = []

    async def get_by_id(self, user_id):
        self.calls.append("get_by_id")

    async def get_by_email(self, email):
        self.calls.append("get_by_email")

    async def create(self, user):
        self.calls.append("create")
        return user

    async def update(self, user):
        self.calls.append("update")
        return user

    async def delete(self, user_id):
        self.calls.append("delete")
        return True

    async def list_all(self, skip=0, limit=100, filters=None):
        self.calls.append("list_all")
        return []

    async def count(self, filters=None):
        self.calls.append("count")
        return 0

    async def update_last_login(self, user_id, timestamp):
        self.calls.append("update_last_login")
        return True

    async def set_mfa_secret(self, user_id, mfa_type, secret):
        self.calls.append("set_mfa_secret")
        return True

    async def verify_email(self, user_id):
        self.calls.append("verify_email")
        return True


def test_property_6_native_async_returned_unchanged():
    """Feature: z_aud_3, Property 6: as_async() uses the native implementation, never the bridge,
    when one is already provided."""
    native = _SpyAsyncUserRepository()
    resolved = as_async(native)

    assert resolved is native

    asyncio.run(resolved.get_by_id("u1"))
    assert native.calls == ["get_by_id"]


def test_property_6_sync_implementation_wrapped_in_bridge():
    sync_repo = InMemoryUserRepository()
    resolved = as_async(sync_repo)

    assert isinstance(resolved, SyncToAsyncUserRepository)
    assert not isinstance(sync_repo, AsyncUserRepository)

    user = asyncio.run(resolved.create(User(id="u1", email="u1@example.com")))
    assert user.id == "u1"
    assert sync_repo.get_by_id("u1") is user  # actually reached the sync repo
