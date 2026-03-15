"""
Async coverage tests for:
  - core/session_service.py (lines 49, 53, 57, 61, 65, 152-200, 238-268, 293-306, 334-341)
"""
import pytest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from tenxyte.core.session_service import (
    SessionService,
    AsyncSessionRepository,
    SessionRepository,
)
from tenxyte.core.cache_service import InMemoryCacheService
from tenxyte.core.schemas import UserResponse


# ─── Helpers ─────────────────────────────────────────────────────────────────

class DummyProvider:
    def get(self, name, default=None):
        return default


class DummySettings:
    jwt_refresh_token_lifetime = 3600
    device_fingerprinting_enabled = True
    max_devices_per_user = 0


class SyncRepo:
    """Plain synchronous SessionRepository."""
    def __init__(self):
        self._sessions: Dict[str, Any] = {}

    def create(self, user_id, device_id, metadata, expires_at) -> str:
        sid = metadata["session_id"]
        self._sessions[sid] = metadata
        return sid

    def get(self, session_id):
        return self._sessions.get(session_id)

    def revoke(self, session_id) -> bool:
        self._sessions.pop(session_id, None)
        return True

    def revoke_all_for_user(self, user_id, except_session_id=None) -> int:
        keys = [k for k, v in self._sessions.items()
                if v.get("user_id") == user_id and k != except_session_id]
        for k in keys:
            self._sessions.pop(k)
        return len(keys)

    def get_user_sessions(self, user_id) -> List[Dict]:
        return [v for v in self._sessions.values() if v.get("user_id") == user_id]


class AsyncRepo(SyncRepo):
    """AsyncSessionRepository with async methods."""
    async def create_async(self, user_id, device_id, metadata, expires_at):
        return self.create(user_id, device_id, metadata, expires_at)

    async def get_async(self, session_id):
        return self.get(session_id)

    async def revoke_async(self, session_id):
        return self.revoke(session_id)

    async def revoke_all_for_user_async(self, user_id, except_session_id=None):
        return self.revoke_all_for_user(user_id, except_session_id)

    async def get_user_sessions_async(self, user_id):
        return self.get_user_sessions(user_id)


@pytest.fixture
def settings():
    return DummySettings()


@pytest.fixture
def cache():
    return InMemoryCacheService()


@pytest.fixture
def user():
    return UserResponse(id="user-1", email="u@example.com")


# ─── AsyncSessionRepository protocol stubs (lines 49, 53, 57, 61, 65) ────────

class TestAsyncSessionRepositoryProtocol:
    @pytest.mark.anyio
    async def test_session_repo_stubs(self):
        """Lines 24, 28, 32, 36, 40: SessionRepository stubs."""
        # Call on class directly to hit "..." statement
        SessionRepository.create(None, "u", "d", {}, datetime.now())
        SessionRepository.get(None, "s")
        SessionRepository.revoke(None, "s")
        SessionRepository.revoke_all_for_user(None, "u")
        SessionRepository.get_user_sessions(None, "u")
        
    @pytest.mark.anyio
    async def test_async_session_repo_stubs(self):
        """Lines 49, 53, 57, 61, 65: AsyncSessionRepository stubs."""
        await AsyncSessionRepository.create_async(None, "u", "d", {}, datetime.now())
        await AsyncSessionRepository.get_async(None, "s")
        await AsyncSessionRepository.revoke_async(None, "s")
        await AsyncSessionRepository.revoke_all_for_user_async(None, "u")
        await AsyncSessionRepository.get_user_sessions_async(None, "u")


# ─── SessionService.create_session_async (lines 152-200) ─────────────────────

class TestCreateSessionAsync:
    @pytest.mark.anyio
    async def test_create_session_async_with_async_repo(self, settings, cache, user):
        """Lines 176-187: uses async repo methods."""
        repo = AsyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        data = await service.create_session_async(user, device_id="dev-1", ip_address="1.2.3.4")
        assert data["user_id"] == "user-1"

    @pytest.mark.anyio
    async def test_create_session_async_with_sync_repo(self, settings, cache, user):
        """Lines 186-187: falls back to sync repo via to_thread."""
        repo = SyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        data = await service.create_session_async(user)
        assert data["user_id"] == "user-1"

    @pytest.mark.anyio
    async def test_create_session_async_max_devices_check(self, settings, cache, user):
        """Lines 174-182: max_devices > 0 triggers session list check."""
        settings.max_devices_per_user = 5
        repo = AsyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        data = await service.create_session_async(user)
        assert "session_id" in data

    @pytest.mark.anyio
    async def test_create_session_async_max_devices_sync_repo(self, settings, cache, user):
        """Lines 178-179: max_devices > 0 with sync repo uses to_thread for session list."""
        settings.max_devices_per_user = 5
        repo = SyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        data = await service.create_session_async(user)
        assert "session_id" in data

    @pytest.mark.anyio
    async def test_create_session_async_no_repo(self, settings, cache, user):
        """Lines 189-198: no repo, uses async cache set."""
        service = SessionService(settings=settings, cache_service=cache)
        data = await service.create_session_async(user)
        assert "session_id" in data


# ─── SessionService.validate_session_async (lines 238-268) ───────────────────

class TestValidateSessionAsync:
    @pytest.mark.anyio
    async def test_validate_session_async_cache_hit(self, settings, cache, user):
        """Lines 238-245: cache hit returns early."""
        service = SessionService(settings=settings, cache_service=cache)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        result = await service.validate_session_async(sid)
        assert result is not None
        assert result["session_id"] == sid

    @pytest.mark.anyio
    async def test_validate_session_async_repo_fallback(self, settings, cache, user):
        """Lines 248-266: cache miss, repo lookup."""
        repo = AsyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        # Clear the cache to force repo fallback
        cache.delete(f"session:{sid}")
        result = await service.validate_session_async(sid)
        assert result is not None

    @pytest.mark.anyio
    async def test_validate_session_async_sync_repo_fallback(self, settings, cache, user):
        """Lines 251-252: sync repo fallback via to_thread."""
        repo = SyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        cache.delete(f"session:{sid}")
        result = await service.validate_session_async(sid)
        assert result is not None

    @pytest.mark.anyio
    async def test_validate_session_async_miss(self, settings, cache):
        """Lines 267-268: truly missing session -> None."""
        service = SessionService(settings=settings, cache_service=cache)
        result = await service.validate_session_async("nonexistent-session")
        assert result is None


# ─── SessionService.revoke_session_async (lines 293-306) ─────────────────────

class TestRevokeSessionAsync:
    @pytest.mark.anyio
    async def test_revoke_session_async_with_async_repo(self, settings, cache, user):
        """Lines 300-302: async repo revoke."""
        repo = AsyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        result = await service.revoke_session_async(sid)
        assert result is True

    @pytest.mark.anyio
    async def test_revoke_session_async_with_sync_repo(self, settings, cache, user):
        """Lines 303-304: sync repo via to_thread."""
        repo = SyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        result = await service.revoke_session_async(sid)
        assert result is True

    @pytest.mark.anyio
    async def test_revoke_session_async_no_repo(self, settings, cache, user):
        """Lines 290-306: no repo -> returns True."""
        service = SessionService(settings=settings, cache_service=cache)
        created = await service.create_session_async(user)
        sid = created["session_id"]
        result = await service.revoke_session_async(sid)
        assert result is True


# ─── SessionService.revoke_all_sessions_async (lines 334-341) ────────────────

class TestRevokeAllSessionsAsync:
    @pytest.mark.anyio
    async def test_revoke_all_sessions_async_no_repo(self, settings, cache):
        """Lines 334-341: no repo -> 0."""
        service = SessionService(settings=settings, cache_service=cache)
        result = await service.revoke_all_sessions_async("user-x")
        assert result == 0

    @pytest.mark.anyio
    async def test_revoke_all_sessions_async_with_async_repo(self, settings, cache, user):
        """Lines 336-337: async repo revoke_all_for_user_async."""
        repo = AsyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        await service.create_session_async(user)
        await service.create_session_async(user)
        count = await service.revoke_all_sessions_async("user-1")
        assert count == 2

    @pytest.mark.anyio
    async def test_revoke_all_sessions_async_with_sync_repo(self, settings, cache, user):
        """Lines 338-339: sync repo via to_thread."""
        repo = SyncRepo()
        service = SessionService(settings=settings, cache_service=cache, session_repository=repo)
        await service.create_session_async(user)
        count = await service.revoke_all_sessions_async("user-1")
        assert count == 1
