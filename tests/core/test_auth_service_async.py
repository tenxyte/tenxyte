"""
Tests for AuthenticationService.authenticate_async (spec z_aud_3, Requirement 2 — Core async
completion; needed by the FastAPI_Adapter's Wave A auth router, task 5.1). Same JWT_Async_Pattern
as the rest of Core: native `*_async` sibling methods used when the lookup provides them,
otherwise each sync method is bridged through `asyncio.to_thread`.
"""

from dataclasses import dataclass

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tenxyte.core.auth_service import AuthenticationService
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


@dataclass
class _FakeUser:
    id: str
    password: str
    is_active: bool = True
    is_banned: bool = False
    is_locked: bool = False
    failed_attempts: int = 0


class _SyncLookup:
    """A purely sync PasswordUserLookup — no *_async siblings — exercising the to_thread bridge."""

    def __init__(self, users: dict[str, _FakeUser]):
        self.users = users

    def get_by_identifier(self, identifier: object) -> User | None:
        fake = self.users.get(identifier)
        if fake is None:
            return None
        return User(id=fake.id, email=str(identifier), is_active=fake.is_active, metadata={"is_banned": fake.is_banned})

    def is_account_locked(self, user_id: str) -> bool:
        return any(u.is_locked for u in self.users.values() if u.id == user_id)

    def check_password(self, user_id: str, password: str) -> bool:
        return any(u.id == user_id and u.password == password for u in self.users.values())

    def record_failed_login(self, user_id: str) -> None:
        for u in self.users.values():
            if u.id == user_id:
                u.failed_attempts += 1


class _NativeAsyncLookup(_SyncLookup):
    """Same behavior as _SyncLookup but exposes async-native siblings — spies on which path
    authenticate_async actually took."""

    def __init__(self, users: dict[str, _FakeUser]):
        super().__init__(users)
        self.calls: list[str] = []

    async def get_by_identifier_async(self, identifier: object) -> User | None:
        self.calls.append("get_by_identifier_async")
        return super().get_by_identifier(identifier)

    async def is_account_locked_async(self, user_id: str) -> bool:
        self.calls.append("is_account_locked_async")
        return super().is_account_locked(user_id)

    async def check_password_async(self, user_id: str, password: str) -> bool:
        self.calls.append("check_password_async")
        return super().check_password(user_id, password)

    async def record_failed_login_async(self, user_id: str) -> None:
        self.calls.append("record_failed_login_async")
        super().record_failed_login(user_id)

    # Sync siblings must never be called once native async ones exist.
    def get_by_identifier(self, identifier: object) -> User | None:
        self.calls.append("get_by_identifier")
        return super().get_by_identifier(identifier)

    def is_account_locked(self, user_id: str) -> bool:
        self.calls.append("is_account_locked")
        return super().is_account_locked(user_id)

    def check_password(self, user_id: str, password: str) -> bool:
        self.calls.append("check_password")
        return super().check_password(user_id, password)

    def record_failed_login(self, user_id: str) -> None:
        self.calls.append("record_failed_login")
        super().record_failed_login(user_id)


def _settings() -> Settings:
    return Settings(provider=EnvSettingsProvider())


@pytest.mark.anyio
async def test_property_native_async_lookup_never_falls_back_to_sync():
    """Feature: z_aud_3, Property: native async resolution for AuthenticationService — when the
    lookup exposes *_async siblings, authenticate_async must use only those, never the sync ones
    (which, for a real SQLAlchemy AsyncSession-backed lookup, wouldn't even be safely callable
    from a running event loop)."""
    users = {"alice@example.com": _FakeUser(id="u1", password="correct-horse")}
    lookup = _NativeAsyncLookup(users)
    service = AuthenticationService(settings=_settings(), user_lookup=lookup)

    result = await service.authenticate_async("alice@example.com", "correct-horse")

    assert result.success is True
    assert lookup.calls == [
        "get_by_identifier_async",
        "is_account_locked_async",
        "check_password_async",
    ]


@pytest.mark.anyio
async def test_bridge_used_when_no_async_siblings_exist():
    users = {"alice@example.com": _FakeUser(id="u1", password="correct-horse")}
    lookup = _SyncLookup(users)
    service = AuthenticationService(settings=_settings(), user_lookup=lookup)

    result = await service.authenticate_async("alice@example.com", "correct-horse")

    assert result.success is True


_SCENARIOS = st.sampled_from(
    [
        ("unknown", "unknown@example.com", "whatever", "user_not_found"),
        ("wrong_password", "alice@example.com", "wrong-password", "invalid_password"),
        ("correct_password", "alice@example.com", "correct-horse", None),
        ("inactive", "bob@example.com", "hunter2", "account_inactive"),
        ("banned", "carol@example.com", "hunter2", "account_banned"),
        ("locked", "dave@example.com", "hunter2", "account_locked"),
    ]
)


def _build_users() -> dict[str, _FakeUser]:
    return {
        "alice@example.com": _FakeUser(id="u-alice", password="correct-horse"),
        "bob@example.com": _FakeUser(id="u-bob", password="hunter2", is_active=False),
        "carol@example.com": _FakeUser(id="u-carol", password="hunter2", is_banned=True),
        "dave@example.com": _FakeUser(id="u-dave", password="hunter2", is_locked=True),
    }


@settings(deadline=None)  # bcrypt's dummy-check comparison is deliberately expensive
@given(scenario=_SCENARIOS)
def test_property_sync_and_async_bridge_agree(scenario):
    """Feature: z_aud_3, Property: sync/async semantic equivalence for AuthenticationService —
    for every scenario, authenticate() and authenticate_async() (via the to_thread bridge) must
    produce the same success/failure_reason."""
    import asyncio

    _name, identifier, password, expected_failure_reason = scenario

    sync_service = AuthenticationService(settings=_settings(), user_lookup=_SyncLookup(_build_users()))
    sync_result = sync_service.authenticate(identifier, password)

    async_service = AuthenticationService(settings=_settings(), user_lookup=_SyncLookup(_build_users()))
    async_result = asyncio.run(async_service.authenticate_async(identifier, password))

    assert sync_result.success == async_result.success
    assert sync_result.failure_reason == async_result.failure_reason
    assert sync_result.failure_reason == (expected_failure_reason or "")


@pytest.mark.anyio
async def test_failed_login_recorded_via_async_path():
    users = {"alice@example.com": _FakeUser(id="u1", password="correct-horse")}
    lookup = _SyncLookup(users)
    service = AuthenticationService(settings=_settings(), user_lookup=lookup)

    result = await service.authenticate_async("alice@example.com", "wrong")

    assert result.success is False
    assert users["alice@example.com"].failed_attempts == 1
