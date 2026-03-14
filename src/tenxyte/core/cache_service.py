"""
Cache service implementations for Tenxyte Core.

This module provides base cache service implementations that can be used
with any adapter (Django, FastAPI, Redis, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime, timedelta
import time


class CacheService(ABC):
    """
    Abstract base class for cache services.
    
    Implementations must provide concrete methods for caching operations
    regardless of the underlying cache backend (Redis, Memcached, in-memory, etc.).
    
    This service is used for:
    - Token blacklist storage
    - Rate limiting counters
    - Temporary data caching
    - Session storage
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        pass
    
    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Time to live in seconds (None for no expiration)
            
        Returns:
            True if value was cached successfully
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted or didn't exist
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and hasn't expired
        """
        pass
    
    @abstractmethod
    def increment(self, key: str, delta: int = 1) -> int:
        """
        Atomically increment a counter.
        
        Args:
            key: Counter key
            delta: Amount to increment (can be negative)
            
        Returns:
            New counter value
        """
        pass
    
    @abstractmethod
    def expire(self, key: str, timeout: int) -> bool:
        """
        Set expiration time on an existing key.
        
        Args:
            key: Cache key
            timeout: Time to live in seconds
            
        Returns:
            True if timeout was set
        """
        pass
    
    @abstractmethod
    def ttl(self, key: str) -> int:
        """
        Get remaining time to live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Seconds until expiration, -1 if no expiration, -2 if not found
        """
        pass
    
    # Token Blacklist Methods
    
    def add_to_blacklist(self, token_jti: str, expires_in: int) -> bool:
        """
        Add a token JTI (JWT ID) to the blacklist.
        
        Args:
            token_jti: The JWT ID to blacklist
            expires_in: How long to keep in blacklist (should match token expiry)
            
        Returns:
            True if added to blacklist
        """
        key = f"token_blacklist:{token_jti}"
        return self.set(key, True, timeout=expires_in)
    
    def is_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token JTI is blacklisted.
        
        Args:
            token_jti: The JWT ID to check
            
        Returns:
            True if token is blacklisted
        """
        key = f"token_blacklist:{token_jti}"
        return self.exists(key)
    
    def remove_from_blacklist(self, token_jti: str) -> bool:
        """
        Remove a token JTI from the blacklist (rarely needed).
        
        Args:
            token_jti: The JWT ID to remove
            
        Returns:
            True if removed
        """
        key = f"token_blacklist:{token_jti}"
        return self.delete(key)
    
    # Rate Limiting Methods
    
    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if a rate limit has been exceeded.
        
        Args:
            key: Rate limit key (e.g., "rate_limit:login:user@example.com")
            max_requests: Maximum allowed requests in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        current_count = self.get(key) or 0
        
        if current_count >= max_requests:
            # Rate limit exceeded
            ttl = max(0, self.ttl(key))
            return False, 0, ttl
        
        # Increment counter
        new_count = self.increment(key)
        
        # Set expiration on first request
        if new_count == 1:
            self.expire(key, window_seconds)
        
        remaining = max(0, max_requests - new_count)
        ttl = max(0, self.ttl(key))
        
        return True, remaining, ttl
    
    def reset_rate_limit(self, key: str) -> bool:
        """
        Reset a rate limit counter.
        
        Args:
            key: Rate limit key
            
        Returns:
            True if reset
        """
        return self.delete(key)


class InMemoryCacheService(CacheService):
    """
    In-memory cache service implementation.
    
    Useful for:
    - Development and testing
    - Single-instance deployments
    - When no external cache is available
    
    Note: This implementation is not thread-safe and data is lost
    on process restart. Use Redis or similar for production.
    """
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, Optional[float]]] = {}
    
    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key not in self._cache:
            return True
        
        value, expiry = self._cache[key]
        if expiry is None:
            return False
        
        return time.time() > expiry
    
    def _cleanup_expired(self):
        """Remove expired entries (simple cleanup)."""
        expired_keys = [
            key for key in self._cache.keys()
            if self._is_expired(key)
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from in-memory cache."""
        self._cleanup_expired()
        
        if key not in self._cache or self._is_expired(key):
            return None
        
        value, _ = self._cache[key]
        return value
    
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None
    ) -> bool:
        """Set value in in-memory cache."""
        expiry = time.time() + timeout if timeout else None
        self._cache[key] = (value, expiry)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete value from in-memory cache."""
        if key in self._cache:
            del self._cache[key]
        return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists in in-memory cache."""
        if key not in self._cache:
            return False
        return not self._is_expired(key)
    
    def increment(self, key: str, delta: int = 1) -> int:
        """Atomically increment a counter (not truly atomic in memory)."""
        current = self.get(key) or 0
        new_value = current + delta
        
        # Preserve expiry if exists
        expiry = None
        if key in self._cache:
            _, existing_expiry = self._cache[key]
            if existing_expiry:
                expiry = existing_expiry - time.time()
        
        self.set(key, new_value, timeout=int(expiry) if expiry else None)
        return new_value
    
    def expire(self, key: str, timeout: int) -> bool:
        """Set expiration on existing key."""
        if key not in self._cache or self._is_expired(key):
            return False
        
        value, _ = self._cache[key]
        self._cache[key] = (value, time.time() + timeout)
        return True
    
    def ttl(self, key: str) -> int:
        """Get remaining time to live."""
        if key not in self._cache:
            return -2
        
        _, expiry = self._cache[key]
        if expiry is None:
            return -1
        
        remaining = expiry - time.time()
        return int(max(0, remaining))
    
    def clear(self) -> bool:
        """Clear all cached data."""
        self._cache.clear()
        return True
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (simple wildcard support)."""
        import fnmatch
        self._cleanup_expired()
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
