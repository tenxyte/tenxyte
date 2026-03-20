"""
Tests for core cache_service - targeting 100% coverage of
src/tenxyte/core/cache_service.py

Uses InMemoryCacheService as the concrete impl to also test
the abstract CacheService's blacklist/rate-limit methods.
"""
import time
import pytest

from tenxyte.core.cache_service import InMemoryCacheService


@pytest.fixture
def cache():
    return InMemoryCacheService()


# ═══════════════════════════════════════════════════════════════════════════════
# InMemoryCacheService basic operations  (lines 234-335)
# ═══════════════════════════════════════════════════════════════════════════════

def test_set_and_get(cache):
    """Lines 274-276, 259-265."""
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_get_missing_key(cache):
    """Line 261-262: key not in cache → None."""
    assert cache.get("missing") is None


def test_set_with_timeout(cache):
    cache.set("k", "v", timeout=60)
    assert cache.get("k") == "v"


def test_get_expired_key(cache):
    """Lines 239-246: expired key → None."""
    cache.set("k", "v", timeout=1)
    # Manually expire it
    cache._cache["k"] = ("v", time.time() - 1)
    assert cache.get("k") is None


def test_set_no_expiry(cache):
    """Line 243-244: expiry is None → not expired."""
    cache.set("k", "v")
    assert not cache._is_expired("k")


def test_is_expired_missing(cache):
    """Lines 239-240: key not in cache → expired."""
    assert cache._is_expired("nonexistent") is True


def test_delete_existing(cache):
    """Lines 280-282: key present → deleted."""
    cache.set("k", "v")
    assert cache.delete("k") is True
    assert cache.get("k") is None


def test_delete_missing(cache):
    """Line 280: key not present → still returns True."""
    assert cache.delete("nonexistent") is True


def test_exists_true(cache):
    """Lines 286-288."""
    cache.set("k", "v")
    assert cache.exists("k") is True


def test_exists_false(cache):
    """Line 286-287: missing key."""
    assert cache.exists("missing") is False


def test_exists_expired(cache):
    """Line 288: expired key → False."""
    cache.set("k", "v", timeout=1)
    cache._cache["k"] = ("v", time.time() - 1)
    assert cache.exists("k") is False


def test_increment_new_key(cache):
    """Lines 292-303: key not present → starts from 0."""
    result = cache.increment("counter")
    assert result == 1


def test_increment_existing(cache):
    cache.set("counter", 5)
    assert cache.increment("counter") == 6
    assert cache.increment("counter", delta=3) == 9


def test_increment_preserves_expiry(cache):
    """Lines 297-300: existing expiry preserved after increment."""
    cache.set("counter", 1, timeout=60)
    cache.increment("counter")
    assert cache.get("counter") == 2
    # TTL should still be positive
    assert cache.ttl("counter") > 0


def test_expire_existing(cache):
    """Lines 307-312."""
    cache.set("k", "v")
    assert cache.expire("k", 60) is True
    assert cache.ttl("k") > 0


def test_expire_missing(cache):
    """Line 307-308: missing key."""
    assert cache.expire("missing", 60) is False


def test_expire_already_expired(cache):
    """Line 307: expired key → False."""
    cache.set("k", "v", timeout=1)
    cache._cache["k"] = ("v", time.time() - 1)
    assert cache.expire("k", 60) is False


def test_ttl_missing(cache):
    """Line 316-317: missing key → -2."""
    assert cache.ttl("missing") == -2


def test_ttl_no_expiry(cache):
    """Lines 320-321: no expiry → -1."""
    cache.set("k", "v")
    assert cache.ttl("k") == -1


def test_ttl_with_expiry(cache):
    """Lines 323-324: remaining time."""
    cache.set("k", "v", timeout=60)
    ttl = cache.ttl("k")
    assert 0 < ttl <= 60


def test_clear(cache):
    """Lines 328-329."""
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.clear() is True
    assert cache.get("a") is None


def test_keys_all(cache):
    """Lines 333-335: all keys."""
    cache.set("x", 1)
    cache.set("y", 2)
    assert sorted(cache.keys()) == ["x", "y"]


def test_keys_pattern(cache):
    """Lines 333-335: pattern matching."""
    cache.set("prefix:a", 1)
    cache.set("prefix:b", 2)
    cache.set("other", 3)
    assert sorted(cache.keys("prefix:*")) == ["prefix:a", "prefix:b"]


def test_cleanup_expired(cache):
    """Lines 250-255: expired entries are cleaned up."""
    cache.set("live", "v", timeout=60)
    cache.set("dead", "v", timeout=1)
    cache._cache["dead"] = ("v", time.time() - 1)
    cache._cleanup_expired()
    assert "dead" not in cache._cache
    assert "live" in cache._cache


# ═══════════════════════════════════════════════════════════════════════════════
# CacheService blacklist methods  (lines 141-168)
# ═══════════════════════════════════════════════════════════════════════════════

def test_add_to_blacklist(cache):
    """Lines 141-142."""
    assert cache.add_to_blacklist("jti-1", 300) is True
    assert cache.exists("token_blacklist:jti-1") is True


def test_is_blacklisted(cache):
    """Lines 154-155."""
    cache.add_to_blacklist("jti-1", 300)
    assert cache.is_blacklisted("jti-1") is True
    assert cache.is_blacklisted("jti-unknown") is False


def test_remove_from_blacklist(cache):
    """Lines 167-168."""
    cache.add_to_blacklist("jti-1", 300)
    assert cache.remove_from_blacklist("jti-1") is True
    assert cache.is_blacklisted("jti-1") is False


# ═══════════════════════════════════════════════════════════════════════════════
# CacheService rate limiting  (lines 189-218)
# ═══════════════════════════════════════════════════════════════════════════════

def test_check_rate_limit_first_request(cache):
    """Lines 189-206: first request, allowed."""
    allowed, remaining, reset = cache.check_rate_limit("rl:test", 5, 60)
    assert allowed is True
    assert remaining == 4
    assert reset >= 0


def test_check_rate_limit_subsequent(cache):
    """Second request still allowed."""
    cache.check_rate_limit("rl:test", 5, 60)
    allowed, remaining, _ = cache.check_rate_limit("rl:test", 5, 60)
    assert allowed is True
    assert remaining == 3


def test_check_rate_limit_exceeded(cache):
    """Lines 191-194: rate limit exceeded."""
    for _ in range(5):
        cache.check_rate_limit("rl:test", 5, 60)
    allowed, remaining, reset = cache.check_rate_limit("rl:test", 5, 60)
    assert allowed is False
    assert remaining == 0


def test_reset_rate_limit(cache):
    """Line 218."""
    cache.check_rate_limit("rl:test", 5, 60)
    assert cache.reset_rate_limit("rl:test") is True
    # After reset, counter is gone
    assert cache.get("rl:test") is None
