"""
Django Cache Service Adapter for Tenxyte Core.

This module provides a CacheService implementation using Django's cache framework.
"""

from typing import Any, Optional
from datetime import datetime


from tenxyte.core.cache_service import CacheService


class DjangoCacheService(CacheService):
    """
    Cache service implementation using Django's cache framework.

    This adapter uses Django's cache backends (Redis, Memcached, database,
    file-based, etc.) configured via Django settings.

    Example:
        # In settings.py
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': 'redis://127.0.0.1:6379/1',
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }

        # Usage
        from tenxyte.adapters.django import DjangoCacheService

        cache_service = DjangoCacheService()
        cache_service.set('key', 'value', timeout=300)
        value = cache_service.get('key')
    """

    def __init__(self, cache_name: str = "default"):
        """
        Initialize the Django cache service.

        Args:
            cache_name: Name of the cache to use from Django's CACHES setting.
                       Defaults to 'default'.
        """
        self._cache_name = cache_name
        self._cache = None

    def _get_cache(self):
        """Lazy initialization of cache connection."""
        if self._cache is None:
            from django.core.cache import caches

            self._cache = caches[self._cache_name]
        return self._cache

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Django cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        return self._get_cache().get(key)

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set a value in Django cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Time to live in seconds (None uses default timeout)

        Returns:
            True if value was cached successfully
        """
        self._get_cache().set(key, value, timeout=timeout)
        return True

    def delete(self, key: str) -> bool:
        """
        Delete a value from Django cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted or didn't exist
        """
        self._get_cache().delete(key)
        return True

    # Sentinel object used by exists() to distinguish a missing key from None
    _CACHE_MISS = object()

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Django cache.

        Args:
            key: Cache key

        Returns:
            True if key exists and hasn't expired
        """
        # Use a sentinel default to distinguish a missing key from a cached None value
        return self._get_cache().get(key, self._CACHE_MISS) is not self._CACHE_MISS

    def increment(self, key: str, delta: int = 1) -> int:
        """
        Atomically increment a counter.

        Args:
            key: Counter key
            delta: Amount to increment (can be negative)

        Returns:
            New counter value
        """
        try:
            new_value = self._get_cache().incr(key, delta)
            return new_value
        except ValueError:
            # Key doesn't exist, initialize with delta
            self._get_cache().set(key, delta)
            return delta

    def expire(self, key: str, timeout: int) -> bool:
        """
        Set expiration time on an existing key.

        Note: Django's cache doesn't support updating TTL directly.
        We need to get the value and re-set it with new timeout.

        Args:
            key: Cache key
            timeout: Time to live in seconds

        Returns:
            True if timeout was set
        """
        value = self._get_cache().get(key)
        if value is None:
            return False

        self._get_cache().set(key, value, timeout=timeout)
        return True

    def ttl(self, key: str) -> int:
        """
        Get remaining time to live for a key.

        Note: Django's cache doesn't expose TTL directly.
        Many backends (especially Redis via django-redis) support this,
        but we'll try to use it if available.

        Args:
            key: Cache key

        Returns:
            Seconds until expiration, -1 if no expiration, -2 if not found
        """
        cache_backend = self._get_cache()

        # Try to use native TTL if available (e.g., django-redis)
        if hasattr(cache_backend, "ttl"):
            try:
                ttl_value = cache_backend.ttl(key)
                if ttl_value is None:
                    return -1  # No expiration
                return int(ttl_value)
            except Exception:
                pass

        # Fallback: check if key exists
        if not self.exists(key):
            return -2

        # Can't determine TTL, assume it exists with unknown expiration
        return -1

    def clear(self) -> bool:
        """Clear all cached data."""
        self._get_cache().clear()
        return True

    def close(self):
        """Close cache connection if needed."""
        # Django handles connection management automatically
        pass

    # Replay protection methods for TOTP

    def is_code_used(self, user_id: str, code: str) -> bool:
        """
        Check if a TOTP code has been used recently (replay protection).

        Args:
            user_id: User ID
            code: TOTP code to check

        Returns:
            True if code was recently used
        """
        cache_key = f"totp_used_{user_id}_{code}"
        return self._get_cache().get(cache_key) is not None

    def mark_code_used(self, user_id: str, code: str, ttl_seconds: int = 60) -> bool:
        """
        Mark a TOTP code as used to prevent replay attacks.

        Args:
            user_id: User ID
            code: TOTP code that was used
            ttl_seconds: Time to keep code in cache (default 60s)

        Returns:
            True if marked successfully
        """
        cache_key = f"totp_used_{user_id}_{code}"
        self._get_cache().set(cache_key, True, timeout=ttl_seconds)
        return True

    def revoke_all_user_tokens(self, user_id: str) -> "datetime":
        """
        Revoke all tokens for a user by setting a revocation timestamp.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        self._get_cache().set(f"revoked_user_{user_id}", now.timestamp(), timeout=86400 * 30)  # 30 days
        return now

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        return self._get_cache().get(f"blacklisted_token_{jti}") is not None

    def blacklist_token(
        self, jti: str, expires_at: "datetime", user_id: Optional[str] = None, reason: str = ""
    ) -> bool:
        """Add a token JTI to the blacklist."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        ttl = max(0, int((expires_at - now).total_seconds()))
        self._get_cache().set(f"blacklisted_token_{jti}", True, timeout=ttl)
        return True

    def is_user_revoked(self, user_id: str, token_iat: "datetime" = None) -> bool:
        """Check if all tokens for a user issued before a certain time are revoked."""
        if not token_iat:
            return False

        revocation_time = self._get_cache().get(f"revoked_user_{user_id}")
        if not revocation_time:
            return False

        from datetime import datetime, timezone

        if isinstance(revocation_time, datetime):
            return token_iat < revocation_time
        elif isinstance(revocation_time, (int, float)):
            revocation_dt = datetime.fromtimestamp(revocation_time, tz=timezone.utc)
            return token_iat < revocation_dt
        return False


# Convenience function for getting configured cache service
def get_cache_service(cache_name: str = "default") -> DjangoCacheService:
    """
    Get a DjangoCacheService instance with settings from Django config.

    Args:
        cache_name: Name of the cache to use

    Returns:
        Configured DjangoCacheService instance

    Example:
        from tenxyte.adapters.django.cache_service import get_cache_service

        cache_service = get_cache_service()
        cache_service.add_to_blacklist(token_jti='abc123', expires_in=3600)
    """
    return DjangoCacheService(cache_name=cache_name)
