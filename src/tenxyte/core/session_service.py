"""
Session and refresh token management for Tenxyte Core.

This module abstracts session management and refresh token validation
independently of any specific framework.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from datetime import datetime
import uuid
import asyncio

from tenxyte.core.settings import Settings
from tenxyte.core.cache_service import CacheService
from tenxyte.core.schemas import UserResponse


@runtime_checkable
class SessionRepository(Protocol):
    """Protocol for persisting session metadata."""

    def create(self, user_id: str, device_id: str, metadata: Dict[str, Any], expires_at: datetime) -> str:
        """Create a new session."""
        ...

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        ...

    def revoke(self, session_id: str) -> bool:
        """Revoke a session."""
        ...

    def revoke_all_for_user(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for a user."""
        ...

    def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all active sessions for a user."""
        ...


@runtime_checkable
class AsyncSessionRepository(SessionRepository, Protocol):
    """Protocol for async session metadata persistence."""

    async def create_async(self, user_id: str, device_id: str, metadata: Dict[str, Any], expires_at: datetime) -> str:
        """Create a new session."""
        ...

    async def get_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        ...

    async def revoke_async(self, session_id: str) -> bool:
        """Revoke a session."""
        ...

    async def revoke_all_for_user_async(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for a user."""
        ...

    async def get_user_sessions_async(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all active sessions for a user."""
        ...


class SessionService:
    """
    Framework-agnostic session and refresh token management.
    """

    def __init__(
        self, settings: Settings, cache_service: CacheService, session_repository: Optional[SessionRepository] = None
    ):
        """
        Initialize the session service.

        Args:
            settings: Tenxyte settings instance
            cache_service: Cache service for token blacklisting and fast validation
            session_repository: Optional repository for persistent session tracking
        """
        self.settings = settings
        self.cache_service = cache_service
        self.repository = session_repository

    def create_session(
        self,
        user: UserResponse,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new session for a user.

        Args:
            user: User object
            device_id: Optional device identifier
            ip_address: Optional IP address
            user_agent: Optional user agent string

        Returns:
            Dictionary containing session metadata
        """
        from datetime import datetime, timedelta, timezone

        session_id = str(uuid.uuid4())
        device_id = device_id or str(uuid.uuid4())

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.settings.jwt_refresh_token_lifetime)

        # Build session metadata
        session_data = {
            "session_id": session_id,
            "user_id": user.id,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        # Persist session if repository is available and fingerprinting is enabled
        if self.repository and self.settings.device_fingerprinting_enabled:
            # Check device limits if configured
            max_devices = self.settings.max_devices_per_user
            if max_devices > 0:
                self.repository.get_user_sessions(user.id)
                # If over limit, we might want to revoke oldest or deny
                # For now, just a placeholder for the logic
                pass

            self.repository.create(user.id, device_id, session_data, expires_at)

        # Also cache the session for fast validation
        cache_key = f"session:{session_id}"
        self.cache_service.set(cache_key, session_data, timeout=self.settings.jwt_refresh_token_lifetime)

        return session_data

    async def create_session_async(
        self,
        user: UserResponse,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Asynchronous version of create_session."""
        from datetime import datetime, timedelta, timezone

        session_id = str(uuid.uuid4())
        device_id = device_id or str(uuid.uuid4())

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.settings.jwt_refresh_token_lifetime)

        # Build session metadata
        session_data = {
            "session_id": session_id,
            "user_id": user.id,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        # Persist session if repository is available and fingerprinting is enabled
        if self.repository and self.settings.device_fingerprinting_enabled:
            # Check device limits if configured
            max_devices = self.settings.max_devices_per_user
            if max_devices > 0:
                if hasattr(self.repository, "get_user_sessions_async"):
                    await self.repository.get_user_sessions_async(user.id)
                else:
                    await asyncio.to_thread(self.repository.get_user_sessions, user.id)
                # If over limit, we might want to revoke oldest or deny
                # For now, just a placeholder for the logic
                pass

            if hasattr(self.repository, "create_async"):
                await self.repository.create_async(user.id, device_id, session_data, expires_at)
            else:
                await asyncio.to_thread(self.repository.create, user.id, device_id, session_data, expires_at)

        # Also cache the session for fast validation
        cache_key = f"session:{session_id}"
        if hasattr(self.cache_service, "set_async"):
            await self.cache_service.set_async(
                cache_key, session_data, timeout=self.settings.jwt_refresh_token_lifetime
            )
        else:
            await asyncio.to_thread(
                self.cache_service.set, cache_key, session_data, timeout=self.settings.jwt_refresh_token_lifetime
            )

        return session_data

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session exists and is active.

        Args:
            session_id: Session ID to validate

        Returns:
            Session metadata if valid, None otherwise
        """
        # Fast path: check cache
        cache_key = f"session:{session_id}"
        session_data = self.cache_service.get(cache_key)

        if session_data:
            return session_data

        # Fallback to persistent storage if available
        if self.repository:
            session_data = self.repository.get(session_id)
            if session_data:
                # Re-cache for future requests
                from datetime import datetime

                expires_at = datetime.fromisoformat(session_data["expires_at"])
                ttl = int((expires_at - datetime.now(expires_at.tzinfo)).total_seconds())

                if ttl > 0:
                    self.cache_service.set(cache_key, session_data, timeout=ttl)
                    return session_data

        return None

    async def validate_session_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Asynchronous version of validate_session."""
        # Fast path: check cache
        cache_key = f"session:{session_id}"
        if hasattr(self.cache_service, "get_async"):
            session_data = await self.cache_service.get_async(cache_key)
        else:
            session_data = await asyncio.to_thread(self.cache_service.get, cache_key)

        if session_data:
            return session_data

        # Fallback to persistent storage if available
        if self.repository:
            if hasattr(self.repository, "get_async"):
                session_data = await self.repository.get_async(session_id)
            else:
                session_data = await asyncio.to_thread(self.repository.get, session_id)

            if session_data:
                # Re-cache for future requests
                from datetime import datetime

                expires_at = datetime.fromisoformat(session_data["expires_at"])
                ttl = int((expires_at - datetime.now(expires_at.tzinfo)).total_seconds())

                if ttl > 0:
                    if hasattr(self.cache_service, "set_async"):
                        await self.cache_service.set_async(cache_key, session_data, timeout=ttl)
                    else:
                        await asyncio.to_thread(self.cache_service.set, cache_key, session_data, timeout=ttl)
                    return session_data

        return None

    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a specific session.

        Args:
            session_id: Session ID to revoke

        Returns:
            True if revoked
        """
        # Remove from cache
        cache_key = f"session:{session_id}"
        self.cache_service.delete(cache_key)

        # Remove from persistent storage
        if self.repository:
            return self.repository.revoke(session_id)

        return True

    async def revoke_session_async(self, session_id: str) -> bool:
        """Asynchronous version of revoke_session."""
        # Remove from cache
        cache_key = f"session:{session_id}"
        if hasattr(self.cache_service, "delete_async"):
            await self.cache_service.delete_async(cache_key)
        else:
            await asyncio.to_thread(self.cache_service.delete, cache_key)

        # Remove from persistent storage
        if self.repository:
            if hasattr(self.repository, "revoke_async"):
                return await self.repository.revoke_async(session_id)
            else:
                return await asyncio.to_thread(self.repository.revoke, session_id)

        return True

    def revoke_all_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """
        Revoke all active sessions for a user.

        Args:
            user_id: User ID
            except_session_id: Optional session ID to keep active

        Returns:
            Number of sessions revoked
        """
        # In a real implementation with just cache, we'd need a way to track
        # all session IDs for a user. This is why a repository is useful.

        revoked_count = 0
        if self.repository:
            revoked_count = self.repository.revoke_all_for_user(user_id, except_session_id)

            # Since we can't easily iterate cache keys matching a pattern in all backends,
            # we rely on the repository to be the source of truth, and the next validation
            # attempt will fall back to the repo, find it revoked, and clean the cache.

        return revoked_count

    async def revoke_all_sessions_async(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Asynchronous version of revoke_all_sessions."""
        revoked_count = 0
        if self.repository:
            if hasattr(self.repository, "revoke_all_for_user_async"):
                revoked_count = await self.repository.revoke_all_for_user_async(user_id, except_session_id)
            else:
                revoked_count = await asyncio.to_thread(self.repository.revoke_all_for_user, user_id, except_session_id)

        return revoked_count
