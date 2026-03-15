"""
Tests for async methods of cache_service.py
Targets lines: 125, 129, 133, 137, 141, 145, 149, 195-196, 200-201, 205-206, 255-272, 276
"""
import pytest
from tenxyte.core.cache_service import InMemoryCacheService


@pytest.fixture
def cache():
    return InMemoryCacheService()


class TestCacheServiceAsyncMethods:
    @pytest.mark.anyio
    async def test_get_async(self, cache):
        cache.set("key1", "value1")
        result = await cache.get_async("key1")
        assert result == "value1"

    @pytest.mark.anyio
    async def test_set_async(self, cache):
        result = await cache.set_async("key2", "value2", timeout=60)
        assert result is True
        assert cache.get("key2") == "value2"

    @pytest.mark.anyio
    async def test_delete_async(self, cache):
        cache.set("key3", "value3")
        result = await cache.delete_async("key3")
        assert result is True
        assert cache.get("key3") is None

    @pytest.mark.anyio
    async def test_exists_async(self, cache):
        cache.set("key4", "value4")
        assert await cache.exists_async("key4") is True
        assert await cache.exists_async("nonexistent") is False

    @pytest.mark.anyio
    async def test_increment_async(self, cache):
        result = await cache.increment_async("counter")
        assert result == 1
        result2 = await cache.increment_async("counter", delta=4)
        assert result2 == 5

    @pytest.mark.anyio
    async def test_expire_async(self, cache):
        cache.set("expkey", "v")
        result = await cache.expire_async("expkey", 60)
        assert result is True

    @pytest.mark.anyio
    async def test_ttl_async(self, cache):
        cache.set("ttl_key", "v", timeout=60)
        ttl = await cache.ttl_async("ttl_key")
        assert 0 < ttl <= 60

    @pytest.mark.anyio
    async def test_add_to_blacklist_async(self, cache):
        result = await cache.add_to_blacklist_async("jti-async-1", 300)
        assert result is True
        assert cache.is_blacklisted("jti-async-1") is True

    @pytest.mark.anyio
    async def test_is_blacklisted_async(self, cache):
        cache.add_to_blacklist("jti-async-2", 300)
        assert await cache.is_blacklisted_async("jti-async-2") is True
        assert await cache.is_blacklisted_async("nonexistent") is False

    @pytest.mark.anyio
    async def test_remove_from_blacklist_async(self, cache):
        cache.add_to_blacklist("jti-async-3", 300)
        result = await cache.remove_from_blacklist_async("jti-async-3")
        assert result is True
        assert cache.is_blacklisted("jti-async-3") is False

    @pytest.mark.anyio
    async def test_check_rate_limit_async_allowed(self, cache):
        allowed, remaining, reset = await cache.check_rate_limit_async("rl_async:test", 5, 60)
        assert allowed is True
        assert remaining == 4

    @pytest.mark.anyio
    async def test_check_rate_limit_async_second_request(self, cache):
        await cache.check_rate_limit_async("rl_async:test2", 5, 60)
        allowed, remaining, _ = await cache.check_rate_limit_async("rl_async:test2", 5, 60)
        assert allowed is True
        assert remaining == 3

    @pytest.mark.anyio
    async def test_check_rate_limit_async_exceeded(self, cache):
        for _ in range(5):
            await cache.check_rate_limit_async("rl_async:flood", 5, 60)
        allowed, remaining, reset = await cache.check_rate_limit_async("rl_async:flood", 5, 60)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.anyio
    async def test_reset_rate_limit_async(self, cache):
        await cache.check_rate_limit_async("rl_async:reset", 5, 60)
        result = await cache.reset_rate_limit_async("rl_async:reset")
        assert result is True
        assert cache.get("rl_async:reset") is None


class TestCacheServiceSyncMethods:
    def test_remove_from_blacklist(self, cache):
        """Line 190-191."""
        cache.add_to_blacklist("jti-sync-1", 300)
        result = cache.remove_from_blacklist("jti-sync-1")
        assert result is True
        assert cache.is_blacklisted("jti-sync-1") is False

    def test_check_rate_limit(self, cache):
        """Lines 222-239."""
        # First request
        allowed, remaining, _ = cache.check_rate_limit("rl_sync:test", 5, 60)
        assert allowed is True
        assert remaining == 4
        
        # Subsequent request
        allowed, remaining, _ = cache.check_rate_limit("rl_sync:test", 5, 60)
        assert allowed is True
        assert remaining == 3
        
        # Exceed limit
        for _ in range(3):
            cache.check_rate_limit("rl_sync:test", 5, 60)
        allowed, remaining, _ = cache.check_rate_limit("rl_sync:test", 5, 60)
        assert allowed is False
        assert remaining == 0

    def test_reset_rate_limit(self, cache):
        """Line 251."""
        cache.check_rate_limit("rl_sync:reset", 5, 60)
        result = cache.reset_rate_limit("rl_sync:reset")
        assert result is True
        assert cache.get("rl_sync:reset") is None

    def test_is_expired_unexistent(self, cache):
        """Line 298."""
        assert cache._is_expired("really-nonexistent-key") is True

    def test_cleanup_expired_real_deletion(self, cache):
        """Line 310."""
        import time
        from unittest.mock import patch
        with patch("time.time", return_value=1000):
            cache.set("ephemeral", "val", timeout=10) # expires at 1010
        
        with patch("time.time", return_value=1011):
            # This should trigger cleanup
            assert cache.get("ephemeral") is None
            assert "ephemeral" not in cache._cache

    def test_expire_nonexistent(self, cache):
        """Line 358."""
        assert cache.expire("no-such-key", 60) is False

    def test_ttl_special_values(self, cache):
        """Lines 367, 371."""
        assert cache.ttl("not-here") == -2
        cache.set("forever", "val") # no timeout
        assert cache.ttl("forever") == -1

    def test_clear(self, cache):
        """Lines 378-379."""
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() is True
        assert cache.exists("a") is False
        assert cache.exists("b") is False

    def test_keys_pattern(self, cache):
        """Lines 383-386."""
        cache.set("user:1", "a")
        cache.set("user:2", "b")
        cache.set("other:1", "c")
        
        user_keys = cache.keys("user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys
        
        all_keys = cache.keys("*")
        assert len(all_keys) == 3
