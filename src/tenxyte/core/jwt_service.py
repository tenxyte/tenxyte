"""
JWT Service for Tenxyte Core.

Framework-agnostic JWT token generation, validation, and blacklisting.
Works with any underlying cache implementation.
"""

import jwt
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable
import asyncio

from tenxyte.core.settings import Settings


@dataclass
class TokenPair:
    """Result of generating a token pair."""

    access_token: str
    access_token_jti: str
    access_token_expires_at: datetime
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


@dataclass
class DecodedToken:
    """Decoded JWT token with metadata."""

    user_id: str
    app_id: str
    jti: str
    exp: datetime
    iat: datetime
    type: str
    claims: Dict[str, Any]
    is_blacklisted: bool = False
    is_valid: bool = True
    error: Optional[str] = None


@runtime_checkable
class TokenBlacklistService(Protocol):
    """Protocol for token blacklist operations."""

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        ...  # pragma: no cover

    def is_user_revoked(self, user_id: str, token_iat: datetime) -> bool:
        """Check if a user's tokens are revoked."""
        ...  # pragma: no cover

    def revoke_all_user_tokens(self, user_id: str) -> datetime:
        """Mark all tokens for a user as revoked."""
        ...  # pragma: no cover

    def blacklist_token(self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = "") -> bool:
        """Add a token JTI to the blacklist."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncTokenBlacklistService(TokenBlacklistService, Protocol):
    """Protocol for async token blacklist operations."""

    async def is_blacklisted_async(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        ...  # pragma: no cover

    async def is_user_revoked_async(self, user_id: str, token_iat: datetime) -> bool:
        """Check if a user's tokens are revoked."""
        ...  # pragma: no cover

    async def revoke_all_user_tokens_async(self, user_id: str) -> datetime:
        """Mark all tokens for a user as revoked."""
        ...  # pragma: no cover

    async def blacklist_token_async(
        self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = ""
    ) -> bool:
        """Add a token JTI to the blacklist."""
        ...  # pragma: no cover


class InMemoryTokenBlacklistService:
    """
    In-memory implementation of token blacklist.

    Suitable for development and single-instance deployments.
    For production with multiple instances, use a shared cache (Redis, etc.).
    """

    def __init__(self):
        self._blacklisted: Dict[str, datetime] = {}
        self._reasons: Dict[str, str] = {}
        # User-level revocation: user_id -> revocation timestamp
        self._user_revocations: Dict[str, datetime] = {}

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        if jti not in self._blacklisted:
            return False

        # Check if expired
        expires_at = self._blacklisted[jti]
        if datetime.now(timezone.utc) > expires_at:
            # Clean up expired entry
            del self._blacklisted[jti]
            if jti in self._reasons:
                del self._reasons[jti]
            return False

        return True

    def is_user_revoked(self, user_id: str, token_iat: datetime) -> bool:
        """Check if all tokens for a user issued before a certain time are revoked."""
        if user_id not in self._user_revocations:
            return False

        revocation_time = self._user_revocations[user_id]
        # If token was issued before revocation, it's revoked
        return token_iat < revocation_time

    def revoke_all_user_tokens(self, user_id: str) -> datetime:
        """Mark all current and future tokens for a user as revoked until now."""
        now = datetime.now(timezone.utc)
        self._user_revocations[user_id] = now
        return now

    def blacklist_token(self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = "") -> bool:
        """Add a token JTI to the blacklist."""
        self._blacklisted[jti] = expires_at
        if reason:
            self._reasons[jti] = reason
        return True

    async def is_blacklisted_async(self, jti: str) -> bool:
        return await asyncio.to_thread(self.is_blacklisted, jti)

    async def is_user_revoked_async(self, user_id: str, token_iat: datetime) -> bool:
        return await asyncio.to_thread(self.is_user_revoked, user_id, token_iat)

    async def revoke_all_user_tokens_async(self, user_id: str) -> datetime:
        return await asyncio.to_thread(self.revoke_all_user_tokens, user_id)

    async def blacklist_token_async(
        self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = ""
    ) -> bool:
        return await asyncio.to_thread(self.blacklist_token, jti, expires_at, user_id, reason)

    def get_reason(self, jti: str) -> Optional[str]:
        """Get the blacklist reason for a JTI (for debugging)."""
        return self._reasons.get(jti)

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count cleaned."""
        now = datetime.now(timezone.utc)
        expired = [jti for jti, exp in self._blacklisted.items() if now > exp]
        for jti in expired:
            del self._blacklisted[jti]
            if jti in self._reasons:
                del self._reasons[jti]
        return len(expired)


class JWTService:
    """
    Framework-agnostic JWT service for token management.

    This service handles JWT token generation, validation, and blacklisting
    without dependencies on any specific framework.

    Example:
        from tenxyte.core import Settings, JWTService
        from tenxyte.adapters.django import DjangoSettingsProvider

        settings = Settings(provider=DjangoSettingsProvider())
        jwt_service = JWTService(settings=settings)

        # Generate tokens
        token_pair = jwt_service.generate_token_pair(
            user_id="user123",
            application_id="app456",
            refresh_token_str="refresh_token_here"
        )
    """

    def __init__(self, settings: Settings, blacklist_service: Optional[TokenBlacklistService] = None):
        """
        Initialize JWT service.

        Args:
            settings: Tenxyte settings instance
            blacklist_service: Optional blacklist service for token revocation
        """
        self.settings = settings
        self.blacklist_service = blacklist_service or InMemoryTokenBlacklistService()

        # Algorithm configuration
        self.algorithm = settings.jwt_algorithm
        self.is_asymmetric = self.algorithm.startswith(("RS", "PS", "ES"))

        # Key configuration
        if self.is_asymmetric:
            self.private_key = settings.jwt_secret  # For RS*, this should be the private key
            self.public_key = settings.jwt_public_key
            self.signing_key = self.private_key
            self.verifying_key = self.public_key or self.private_key
        else:
            self.secret_key = settings.jwt_secret
            self.signing_key = self.secret_key
            self.verifying_key = self.secret_key

        # Token lifetimes
        self.access_token_lifetime = timedelta(seconds=settings.jwt_access_token_lifetime)
        self.refresh_token_lifetime = timedelta(seconds=settings.jwt_refresh_token_lifetime)

        # Issuer/Audience (optional)
        self.issuer = settings.jwt_issuer
        self.audience = settings.jwt_audience

    def generate_access_token(
        self, user_id: str, application_id: str, extra_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Generate an access token JWT with JTI for blacklisting.

        Args:
            user_id: User identifier
            application_id: Application identifier
            extra_claims: Additional claims to include in token

        Returns:
            Tuple of (token, jti, expires_at)

        Raises:
            ValueError: If signing key is not configured
        """
        if not self.signing_key:
            raise ValueError(
                f"JWT signing key is required for algorithm {self.algorithm}. " f"Set TENXYTE_JWT_SECRET in settings."
            )

        if self.is_asymmetric and not self.private_key:  # pragma: no cover
            raise ValueError(
                f"JWT private key is required for asymmetric algorithm {self.algorithm}. "
                f"Set TENXYTE_JWT_SECRET (private key) in settings."
            )

        now = datetime.now(timezone.utc)
        jti = str(uuid.uuid4())
        expires_at = now + self.access_token_lifetime

        payload: Dict[str, Any] = {
            "type": "access",
            "jti": jti,
            "user_id": str(user_id),
            "app_id": str(application_id),
            "iat": now,
            "exp": expires_at,
            "nbf": now,
        }

        # Add issuer if configured
        if self.issuer:
            payload["iss"] = self.issuer

        # Add audience if configured
        if self.audience:
            payload["aud"] = self.audience

        # Add extra claims
        if extra_claims:
            # Prevent overriding protected claims
            protected = {"type", "jti", "user_id", "app_id", "iat", "exp", "nbf", "iss", "aud"}
            for key, value in extra_claims.items():
                if key not in protected:
                    payload[key] = value

        token = jwt.encode(payload, self.signing_key, algorithm=self.algorithm)
        return token, jti, expires_at

    def generate_refresh_token(
        self,
        user_id: str,
        application_id: str,
        device_info: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a refresh token (opaque UUID string).

        Args:
            user_id: User identifier
            application_id: Application identifier
            device_info: Optional device information to include in claims
            extra_claims: Additional claims to include in token (for JWT refresh tokens)

        Returns:
            Refresh token string (UUID)
        """
        # For now, return a simple UUID - this matches Django model expectation
        return str(uuid.uuid4())

    def generate_token_pair(
        self, user_id: str, application_id: str, refresh_token_str: str, extra_claims: Optional[Dict[str, Any]] = None
    ) -> TokenPair:
        """
        Generate an access token + refresh token pair.

        Args:
            user_id: User identifier
            application_id: Application identifier
            refresh_token_str: Existing refresh token string
            extra_claims: Additional claims for access token

        Returns:
            TokenPair with both tokens and metadata
        """
        access_token, jti, expires_at = self.generate_access_token(user_id, application_id, extra_claims)

        return TokenPair(
            access_token=access_token,
            access_token_jti=jti,
            access_token_expires_at=expires_at,
            refresh_token=refresh_token_str,
            token_type="Bearer",
            expires_in=int(self.access_token_lifetime.total_seconds()),
        )

    def generate_new_token_pair(
        self, user_id: str, application_id: str, extra_claims: Optional[Dict[str, Any]] = None
    ) -> TokenPair:
        """
        Generate a NEW access token + refresh token pair for initial login.

        This creates a fresh refresh token (not rotation of existing one).

        Args:
            user_id: User identifier
            application_id: Application identifier
            extra_claims: Additional claims for access token

        Returns:
            TokenPair with both new tokens and metadata
        """
        # Generate access token
        access_token, jti, expires_at = self.generate_access_token(user_id, application_id, extra_claims)

        # Generate refresh token (opaque string)
        refresh_token = str(uuid.uuid4())

        return TokenPair(
            access_token=access_token,
            access_token_jti=jti,
            access_token_expires_at=expires_at,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(self.access_token_lifetime.total_seconds()),
        )

    def decode_token(self, token: str, check_blacklist: bool = True) -> Optional[DecodedToken]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string
            check_blacklist: Whether to check if token is blacklisted

        Returns:
            DecodedToken if valid, None if invalid/expired
        """
        if not self.verifying_key:
            raise ValueError(
                f"JWT verifying key is required for algorithm {self.algorithm}. "
                f"Set TENXYTE_JWT_SECRET or TENXYTE_JWT_PUBLIC_KEY in settings."
            )

        try:
            # Decode with required claims
            options = {"require": ["exp", "iat"]}

            payload = jwt.decode(
                token,
                self.verifying_key,
                algorithms=[self.algorithm],
                options=options,
                issuer=self.issuer if self.issuer else None,
                audience=self.audience if self.audience else None,
            )

            # Extract required fields
            user_id = payload.get("user_id")
            app_id = payload.get("app_id")
            jti = payload.get("jti")

            if not user_id or not app_id or not jti:
                return DecodedToken(
                    user_id=user_id or "",
                    app_id=app_id or "",
                    jti=jti or "",
                    exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc),
                    type=payload.get("type", "unknown"),
                    claims=payload,
                    is_valid=False,
                    error="Missing required claims (user_id, app_id, or jti)",
                )

            # Convert timestamps to datetime
            exp_ts = payload.get("exp", 0)
            iat_ts = payload.get("iat", 0)
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            iat_dt = datetime.fromtimestamp(iat_ts, tz=timezone.utc)

            # Check blacklist
            is_blacklisted = False
            if check_blacklist:
                is_blacklisted = self.blacklist_service.is_blacklisted(jti)

                # Also check user-level revocation (for password change, etc.)
                if not is_blacklisted and user_id:
                    is_blacklisted = self.blacklist_service.is_user_revoked(user_id, iat_dt)

            return DecodedToken(
                user_id=str(user_id),
                app_id=str(app_id),
                jti=str(jti),
                exp=exp_dt,
                iat=iat_dt,
                type=payload.get("type", "access"),
                claims=payload,
                is_blacklisted=is_blacklisted,
                is_valid=not is_blacklisted,
            )

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            return DecodedToken(
                user_id="",
                app_id="",
                jti="",
                exp=datetime.now(timezone.utc),
                iat=datetime.now(timezone.utc),
                type="error",
                claims={},
                is_valid=False,
                error=f"Invalid token: {str(e)}",
            )

    async def decode_token_async(self, token: str, check_blacklist: bool = True) -> Optional[DecodedToken]:
        """Asynchronous version of decode_token."""
        if not self.verifying_key:
            raise ValueError(
                f"JWT verifying key is required for algorithm {self.algorithm}. "
                f"Set TENXYTE_JWT_SECRET or TENXYTE_JWT_PUBLIC_KEY in settings."
            )

        try:
            options = {"require": ["exp", "iat"]}

            # Decoding is CPU bound, run in thread
            payload = await asyncio.to_thread(
                jwt.decode,
                token,
                self.verifying_key,
                algorithms=[self.algorithm],
                options=options,
                issuer=self.issuer if self.issuer else None,
                audience=self.audience if self.audience else None,
            )

            user_id = payload.get("user_id")
            app_id = payload.get("app_id")
            jti = payload.get("jti")

            if not user_id or not app_id or not jti:
                return DecodedToken(
                    user_id=user_id or "",
                    app_id=app_id or "",
                    jti=jti or "",
                    exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc),
                    type=payload.get("type", "unknown"),
                    claims=payload,
                    is_valid=False,
                    error="Missing required claims (user_id, app_id, or jti)",
                )

            exp_ts = payload.get("exp", 0)
            iat_ts = payload.get("iat", 0)
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            iat_dt = datetime.fromtimestamp(iat_ts, tz=timezone.utc)

            is_blacklisted = False
            if check_blacklist:
                if hasattr(self.blacklist_service, "is_blacklisted_async"):
                    is_blacklisted = await self.blacklist_service.is_blacklisted_async(str(jti))
                else:
                    is_blacklisted = await asyncio.to_thread(self.blacklist_service.is_blacklisted, str(jti))

                if not is_blacklisted and user_id:
                    if hasattr(self.blacklist_service, "is_user_revoked_async"):
                        is_blacklisted = await self.blacklist_service.is_user_revoked_async(str(user_id), iat_dt)
                    else:
                        is_blacklisted = await asyncio.to_thread(
                            self.blacklist_service.is_user_revoked, str(user_id), iat_dt
                        )

            return DecodedToken(
                user_id=str(user_id),
                app_id=str(app_id),
                jti=str(jti),
                exp=exp_dt,
                iat=iat_dt,
                type=payload.get("type", "access"),
                claims=payload,
                is_blacklisted=is_blacklisted,
                is_valid=not is_blacklisted,
            )

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            return DecodedToken(
                user_id="",
                app_id="",
                jti="",
                exp=datetime.now(timezone.utc),
                iat=datetime.now(timezone.utc),
                type="error",
                claims={},
                is_valid=False,
                error=f"Invalid token: {str(e)}",
            )

    def is_token_valid(self, token: str) -> bool:
        """Check if a token is valid (not expired, not blacklisted)."""
        result = self.decode_token(token)
        return result is not None and result.is_valid

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from token."""
        result = self.decode_token(token)
        if result and result.is_valid:
            return result.user_id
        return None

    def get_application_id_from_token(self, token: str) -> Optional[str]:
        """Extract application ID from token."""
        result = self.decode_token(token)
        if result and result.is_valid:
            return result.app_id
        return None

    def blacklist_token(self, token: str, user_id: Optional[str] = None, reason: str = "") -> bool:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            user_id: Optional user ID for logging
            reason: Reason for blacklisting (logout, security, etc.)

        Returns:
            True if token was blacklisted
        """
        # Decode without checking blacklist to get the JTI
        result = self.decode_token(token, check_blacklist=False)

        if not result or not result.jti:
            return False

        # Use expiration from token
        return self.blacklist_service.blacklist_token(
            jti=result.jti, expires_at=result.exp, user_id=user_id, reason=reason
        )

    def blacklist_token_by_jti(
        self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = ""
    ) -> bool:
        """Blacklist a token by its JTI directly."""
        return self.blacklist_service.blacklist_token(jti=jti, expires_at=expires_at, user_id=user_id, reason=reason)

    async def blacklist_token_async(self, token: str, user_id: Optional[str] = None, reason: str = "") -> bool:
        """Asynchronous version of blacklist_token."""
        result = await self.decode_token_async(token, check_blacklist=False)
        if not result or not result.jti:
            return False

        if hasattr(self.blacklist_service, "blacklist_token_async"):
            return await self.blacklist_service.blacklist_token_async(
                jti=result.jti, expires_at=result.exp, user_id=user_id, reason=reason
            )
        else:
            return await asyncio.to_thread(
                self.blacklist_service.blacklist_token,
                jti=result.jti,
                expires_at=result.exp,
                user_id=user_id,
                reason=reason,
            )

    async def blacklist_token_by_jti_async(
        self, jti: str, expires_at: datetime, user_id: Optional[str] = None, reason: str = ""
    ) -> bool:
        """Asynchronous version of blacklist_token_by_jti."""
        if hasattr(self.blacklist_service, "blacklist_token_async"):
            return await self.blacklist_service.blacklist_token_async(
                jti=jti, expires_at=expires_at, user_id=user_id, reason=reason
            )
        else:
            return await asyncio.to_thread(
                self.blacklist_service.blacklist_token, jti=jti, expires_at=expires_at, user_id=user_id, reason=reason
            )

    def revoke_all_user_tokens(self, user_id: str, reason: str = "password_change") -> bool:
        """
        Revoke all tokens for a specific user.

        This revokes:
        1. All refresh tokens in the database (marks them as revoked)
        2. All current JWT access tokens via user-level revocation timestamp

        Typically called when a user changes their password to invalidate
        all existing sessions.

        Args:
            user_id: User identifier
            reason: Reason for revocation (default: password_change)

        Returns:
            True if operation was successful
        """
        revoked_count = 0

        # 1. Revoke all refresh tokens in database
        try:
            from tenxyte.models import RefreshToken as RefreshTokenModel

            # Get all non-revoked refresh tokens for this user
            active_tokens = RefreshTokenModel.objects.filter(user_id=user_id, is_revoked=False)

            # Revoke each token
            for token_obj in active_tokens:
                token_obj.is_revoked = True
                token_obj.save(update_fields=["is_revoked"])
                revoked_count += 1

        except ImportError:
            # Django models not available, skip database revocation
            pass

        # 2. Mark all current JWT access tokens as revoked via user-level revocation
        # This sets a timestamp - any token issued before this time is considered revoked
        revocation_time = self.blacklist_service.revoke_all_user_tokens(user_id)

        # Also store the revocation event for audit purposes
        self.blacklist_service.blacklist_token(
            jti=f"user_revocation:{user_id}:{revocation_time.isoformat()}",
            expires_at=datetime.now(timezone.utc) + self.refresh_token_lifetime,
            user_id=user_id,
            reason=reason,
        )

        return True

    async def revoke_all_user_tokens_async(self, user_id: str, reason: str = "password_change") -> bool:
        """Asynchronous version of revoke_all_user_tokens."""

        # We keep the database revocation inside to_thread as ORMs block
        def _db_revoke():
            try:
                from tenxyte.models import RefreshToken as RefreshTokenModel

                active_tokens = RefreshTokenModel.objects.filter(user_id=user_id, is_revoked=False)
                count = 0
                for token_obj in active_tokens:
                    token_obj.is_revoked = True
                    token_obj.save(update_fields=["is_revoked"])
                    count += 1
                return count
            except ImportError:
                return 0

        await asyncio.to_thread(_db_revoke)

        if hasattr(self.blacklist_service, "revoke_all_user_tokens_async"):
            revocation_time = await self.blacklist_service.revoke_all_user_tokens_async(user_id)
        else:
            revocation_time = await asyncio.to_thread(self.blacklist_service.revoke_all_user_tokens, user_id)

        jti = f"user_revocation:{user_id}:{revocation_time.isoformat()}"
        expires_at = datetime.now(timezone.utc) + self.refresh_token_lifetime

        if hasattr(self.blacklist_service, "blacklist_token_async"):
            await self.blacklist_service.blacklist_token_async(
                jti=jti, expires_at=expires_at, user_id=user_id, reason=reason
            )
        else:
            await asyncio.to_thread(
                self.blacklist_service.blacklist_token, jti=jti, expires_at=expires_at, user_id=user_id, reason=reason
            )

        return True

    def refresh_tokens(self, refresh_token: str, user_repository: Optional[Any] = None) -> Optional[TokenPair]:
        """
        Refresh tokens using a refresh token.

        Validates the refresh token and generates a new access token.
        For opaque refresh tokens (UUID strings), validates against database.
        For JWT refresh tokens, validates cryptographically.

        Args:
            refresh_token: The refresh token to use
            user_repository: Optional user repository to look up user info

        Returns:
            TokenPair with new tokens, or None if refresh failed
        """
        # For opaque refresh tokens (UUID format from generate_new_token_pair)
        try:
            # Try to look up in database using Django model's get_by_raw_token
            # which properly hashes the token before lookup
            from tenxyte.models import RefreshToken as RefreshTokenModel

            try:
                token_obj = RefreshTokenModel.get_by_raw_token(refresh_token)

                if token_obj.is_revoked:
                    return None

                # Check if expired
                if token_obj.expires_at and token_obj.expires_at < datetime.now(timezone.utc):
                    return None

                # Generate new tokens
                user_id = str(token_obj.user_id)
                app_id = str(token_obj.application_id) if token_obj.application_id else "default"

                # Generate new access token
                access_token, jti, expires_at = self.generate_access_token(user_id=user_id, application_id=app_id)

                # Rotate refresh token (create new one)
                new_refresh_token = str(uuid.uuid4())

                # Revoke old token
                token_obj.is_revoked = True
                token_obj.save(update_fields=["is_revoked"])

                # Create new refresh token
                RefreshTokenModel.objects.create(
                    user_id=user_id,
                    application_id=token_obj.application_id,
                    token=new_refresh_token,
                    expires_at=datetime.now(timezone.utc) + self.refresh_token_lifetime,
                )

                return TokenPair(
                    access_token=access_token,
                    access_token_jti=jti,
                    access_token_expires_at=expires_at,
                    refresh_token=new_refresh_token,
                    token_type="Bearer",
                    expires_in=int(self.access_token_lifetime.total_seconds()),
                )

            except RefreshTokenModel.DoesNotExist:
                # Token not found in DB, might be a JWT refresh token
                # Try to decode as JWT
                try:
                    result = self.decode_token(refresh_token, check_blacklist=True)
                    if not result or not result.is_valid:
                        return None

                    if result.type != "refresh":
                        return None

                    # Generate new tokens
                    access_token, jti, expires_at = self.generate_access_token(
                        user_id=result.user_id, application_id=result.app_id
                    )

                    # Generate new refresh token
                    new_refresh_token = str(uuid.uuid4())

                    # Blacklist old refresh token
                    self.blacklist_token_by_jti(
                        jti=result.jti, expires_at=result.exp, user_id=result.user_id, reason="token_rotation"
                    )

                    return TokenPair(
                        access_token=access_token,
                        access_token_jti=jti,
                        access_token_expires_at=expires_at,
                        refresh_token=new_refresh_token,
                        token_type="Bearer",
                        expires_in=int(self.access_token_lifetime.total_seconds()),
                    )

                except Exception:
                    return None

        except ImportError:
            # Django models not available, try JWT decode only
            try:
                result = self.decode_token(refresh_token, check_blacklist=True)
                if not result or not result.is_valid:
                    return None

                # Generate new access token
                access_token, jti, expires_at = self.generate_access_token(
                    user_id=result.user_id, application_id=result.app_id
                )

                # Generate new refresh token
                new_refresh_token = str(uuid.uuid4())

                return TokenPair(
                    access_token=access_token,
                    access_token_jti=jti,
                    access_token_expires_at=expires_at,
                    refresh_token=new_refresh_token,
                    token_type="Bearer",
                    expires_in=int(self.access_token_lifetime.total_seconds()),
                )
            except Exception:
                return None

    async def refresh_tokens_async(
        self, refresh_token: str, user_repository: Optional[Any] = None
    ) -> Optional[TokenPair]:
        """Asynchronous version of refresh_tokens."""

        # For database operations, we delegate to a thread since models are sync.
        # But we do JWT checks asynchronously.
        def _db_lookup_and_rotate():
            try:
                from tenxyte.models import RefreshToken as RefreshTokenModel

                try:
                    token_obj = RefreshTokenModel.get_by_raw_token(refresh_token)
                    if token_obj.is_revoked or (
                        token_obj.expires_at and token_obj.expires_at < datetime.now(timezone.utc)
                    ):
                        return False, None

                    user_id = str(token_obj.user_id)
                    app_id = str(token_obj.application_id) if token_obj.application_id else "default"

                    access_token, jti, expires_at = self.generate_access_token(user_id=user_id, application_id=app_id)
                    new_refresh_token = str(uuid.uuid4())

                    token_obj.is_revoked = True
                    token_obj.save(update_fields=["is_revoked"])

                    RefreshTokenModel.objects.create(
                        user_id=user_id,
                        application_id=token_obj.application_id,
                        token=new_refresh_token,
                        expires_at=datetime.now(timezone.utc) + self.refresh_token_lifetime,
                    )

                    return True, TokenPair(
                        access_token=access_token,
                        access_token_jti=jti,
                        access_token_expires_at=expires_at,
                        refresh_token=new_refresh_token,
                        token_type="Bearer",
                        expires_in=int(self.access_token_lifetime.total_seconds()),
                    )
                except RefreshTokenModel.DoesNotExist:
                    return False, "not_found"
            except ImportError:
                return False, "no_django"

        is_db, result = await asyncio.to_thread(_db_lookup_and_rotate)

        if is_db:
            return result

        # If not db, treat as JWT refresh token
        try:
            decoded = await self.decode_token_async(refresh_token, check_blacklist=True)
            if not decoded or not decoded.is_valid or decoded.type != "refresh":
                return None

            access_token, jti, expires_at = self.generate_access_token(
                user_id=decoded.user_id, application_id=decoded.app_id
            )
            new_refresh_token = str(uuid.uuid4())

            await self.blacklist_token_by_jti_async(
                jti=decoded.jti, expires_at=decoded.exp, user_id=decoded.user_id, reason="token_rotation"
            )

            return TokenPair(
                access_token=access_token,
                access_token_jti=jti,
                access_token_expires_at=expires_at,
                refresh_token=new_refresh_token,
                token_type="Bearer",
                expires_in=int(self.access_token_lifetime.total_seconds()),
            )
        except Exception:
            return None
