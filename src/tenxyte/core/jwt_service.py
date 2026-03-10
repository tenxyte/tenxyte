"""
JWT Service for Tenxyte Core.

Framework-agnostic JWT token generation, validation, and blacklisting.
Works with any underlying cache implementation.
"""

import jwt
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable

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
        ...
    
    def blacklist_token(
        self,
        jti: str,
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """Add a token JTI to the blacklist."""
        ...


class InMemoryTokenBlacklistService:
    """
    In-memory implementation of token blacklist.
    
    Suitable for development and single-instance deployments.
    For production with multiple instances, use a shared cache (Redis, etc.).
    """
    
    def __init__(self):
        self._blacklisted: Dict[str, datetime] = {}
        self._reasons: Dict[str, str] = {}
    
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
    
    def blacklist_token(
        self,
        jti: str,
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """Add a token JTI to the blacklist."""
        self._blacklisted[jti] = expires_at
        if reason:
            self._reasons[jti] = reason
        return True
    
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
    
    def __init__(
        self,
        settings: Settings,
        blacklist_service: Optional[TokenBlacklistService] = None
    ):
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
        self,
        user_id: str,
        application_id: str,
        extra_claims: Optional[Dict[str, Any]] = None
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
                f"JWT signing key is required for algorithm {self.algorithm}. "
                f"Set TENXYTE_JWT_SECRET in settings."
            )
        
        if self.is_asymmetric and not self.private_key:
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
    
    def generate_token_pair(
        self,
        user_id: str,
        application_id: str,
        refresh_token_str: str,
        extra_claims: Optional[Dict[str, Any]] = None
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
        access_token, jti, expires_at = self.generate_access_token(
            user_id, application_id, extra_claims
        )
        
        return TokenPair(
            access_token=access_token,
            access_token_jti=jti,
            access_token_expires_at=expires_at,
            refresh_token=refresh_token_str,
            token_type="Bearer",
            expires_in=int(self.access_token_lifetime.total_seconds()),
        )
    
    def decode_token(
        self,
        token: str,
        check_blacklist: bool = True
    ) -> Optional[DecodedToken]:
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
                    error="Missing required claims (user_id, app_id, or jti)"
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
            
            return DecodedToken(
                user_id=str(user_id),
                app_id=str(app_id),
                jti=str(jti),
                exp=exp_dt,
                iat=iat_dt,
                type=payload.get("type", "access"),
                claims=payload,
                is_blacklisted=is_blacklisted,
                is_valid=not is_blacklisted
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
                error=f"Invalid token: {str(e)}"
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
    
    def blacklist_token(
        self,
        token: str,
        user_id: Optional[str] = None,
        reason: str = ""
    ) -> bool:
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
            jti=result.jti,
            expires_at=result.exp,
            user_id=user_id,
            reason=reason
        )
    
    def blacklist_token_by_jti(
        self,
        jti: str,
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """Blacklist a token by its JTI directly."""
        return self.blacklist_service.blacklist_token(
            jti=jti,
            expires_at=expires_at,
            user_id=user_id,
            reason=reason
        )
