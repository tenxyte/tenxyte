"""
Middleware abstraction strategy for Tenxyte Core.

This module defines the core middleware logic that is framework-agnostic.
Each middleware in this module performs the business logic without
framework-specific request/response handling.

Framework adapters (Django, FastAPI) wrap these core functions in their
respective middleware patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum


@dataclass
class RequestContext:
    """
    Framework-agnostic request context.
    
    Adapters extract relevant information from framework-specific request
    objects and populate this context for Core middleware processing.
    """
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: Optional[bytes] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # These will be populated by middleware
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    application_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a header value case-insensitively."""
        name_lower = name.lower()
        for key, value in self.headers.items():
            if key.lower() == name_lower:
                return value
        return default


@dataclass  
class ResponseContext:
    """
    Framework-agnostic response context.
    
    Core middleware returns this context, which adapters then convert
to framework-specific response objects.
    """
    status_code: int = 200
    headers: Dict[str, str] = None
    body: Optional[bytes] = None
    json_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class MiddlewareResult:
    """
    Result of middleware processing.
    
    Indicates whether to continue to next middleware/respond immediately.
    """
    
    def __init__(
        self,
        continue_processing: bool = True,
        response: Optional[ResponseContext] = None,
        modified_request: Optional[RequestContext] = None
    ):
        self.continue_processing = continue_processing
        self.response = response
        self.modified_request = modified_request
    
    @classmethod
    def continue_(cls, modified_request: Optional[RequestContext] = None) -> 'MiddlewareResult':
        """Continue to next middleware."""
        return cls(continue_processing=True, modified_request=modified_request)
    
    @classmethod
    def respond(cls, response: ResponseContext) -> 'MiddlewareResult':
        """Stop processing and return response immediately."""
        return cls(continue_processing=False, response=response)
    
    @classmethod
    def error(cls, status: int, code: str, message: str, details: Optional[Dict] = None) -> 'MiddlewareResult':
        """Return an error response."""
        response = ResponseContext(
            status_code=status,
            json_data={
                "error": message,
                "code": code,
                **(details or {})
            }
        )
        return cls.respond(response)


# ============================================================
# Core Middleware Interface
# ============================================================

class CoreMiddleware(ABC):
    """
    Abstract base class for core middleware logic.
    
    Implementations provide framework-agnostic request/response processing.
    Framework adapters wrap these in their specific middleware patterns.
    """
    
    def __init__(self, settings: 'Settings'):
        """
        Initialize middleware with settings.
        
        Args:
            settings: Tenxyte Core settings instance
        """
        self.settings = settings
    
    @abstractmethod
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        """
        Process an incoming request.
        
        Args:
            request: Request context with request information
            
        Returns:
            MiddlewareResult indicating whether to continue or respond
        """
        pass
    
    def process_response(
        self,
        request: RequestContext,
        response: ResponseContext
    ) -> ResponseContext:
        """
        Process an outgoing response.
        
        Override this method to modify responses.
        Default implementation returns response unchanged.
        
        Args:
            request: Original request context
            response: Response context to modify
            
        Returns:
            Modified response context
        """
        return response


# ============================================================
# Middleware Chain
# ============================================================

class MiddlewareChain:
    """
    Chain of middleware for processing requests.
    
    Executes middleware in order, stopping early if a middleware
    returns a response.
    """
    
    def __init__(self, middlewares: List[CoreMiddleware]):
        """
        Initialize chain with middleware list.
        
        Args:
            middlewares: List of CoreMiddleware instances to execute
        """
        self.middlewares = middlewares
    
    def process(self, request: RequestContext) -> tuple[Optional[ResponseContext], RequestContext]:
        """
        Process request through middleware chain.
        
        Args:
            request: Initial request context
            
        Returns:
            Tuple of (response, modified_request)
            - If response is not None, return it immediately
            - If response is None, continue to handler with modified_request
        """
        current_request = request
        
        for middleware in self.middlewares:
            result = middleware.process_request(current_request)
            
            if result.modified_request:
                current_request = result.modified_request
            
            if not result.continue_processing:
                # Middleware wants to respond immediately
                if result.response:
                    return result.response, current_request
                else:
                    # Should not happen, but handle gracefully
                    return None, current_request
        
        # All middlewares processed, continue to handler
        return None, current_request
    
    def process_response(
        self,
        request: RequestContext,
        response: ResponseContext
    ) -> ResponseContext:
        """
        Process response through middleware chain in reverse order.
        
        Args:
            request: Request context
            response: Response from handler
            
        Returns:
            Modified response
        """
        current_response = response
        
        # Process in reverse order for response
        for middleware in reversed(self.middlewares):
            current_response = middleware.process_response(request, current_response)
        
        return current_response


# ============================================================
# Core Middleware Implementations
# ============================================================

class RequestIDCoreMiddleware(CoreMiddleware):
    """
    Core middleware for request ID tracking.
    
    Adds X-Request-ID header for request tracing.
    """
    
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        """Add or preserve request ID."""
        import uuid
        
        # Use existing request ID from header or generate new one
        request_id = request.get_header("X-Request-ID") or str(uuid.uuid4())
        
        # Attach to request context
        request.request_id = request_id
        request.metadata["request_id"] = request_id
        
        return MiddlewareResult.continue_(request)
    
    def process_response(
        self,
        request: RequestContext,
        response: ResponseContext
    ) -> ResponseContext:
        """Add X-Request-ID to response headers."""
        if request.request_id:
            response.headers["X-Request-ID"] = request.request_id
        return response


class ApplicationAuthCoreMiddleware(CoreMiddleware):
    """
    Core middleware for application-level authentication.
    
    Validates X-Access-Key and X-Access-Secret headers.
    """
    
    def __init__(self, settings: 'Settings', repository: 'ApplicationRepository'):
        """
        Initialize with settings and application repository.
        
        Args:
            settings: Tenxyte settings
            repository: Repository for loading applications
        """
        super().__init__(settings)
        self.repository = repository
        self._cache_service: Optional['CacheService'] = None
    
    @property
    def cache_service(self) -> 'CacheService':
        """Lazy-load cache service."""
        if self._cache_service is None:
            # This would be injected by the adapter or initialized globally
            from tenxyte.core.cache_service import InMemoryCacheService
            self._cache_service = InMemoryCacheService()
        return self._cache_service
    
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        """Validate application credentials."""
        # Check if application auth is enabled
        if not self.settings.application_auth_enabled:
            return MiddlewareResult.continue_(request)
        
        # Check exempt paths
        if self._is_exempt_path(request.path):
            return MiddlewareResult.continue_(request)
        
        # Get credentials
        access_key = request.get_header("X-Access-Key")
        access_secret = request.get_header("X-Access-Secret")
        
        if not access_key or not access_secret:
            return MiddlewareResult.error(
                401,
                "APP_AUTH_REQUIRED",
                "Missing application credentials"
            )
        
        # Validate credentials via repository
        application = self.repository.get_by_access_key(access_key)
        
        if not application or not application.is_active:
            return MiddlewareResult.error(
                401,
                "APP_AUTH_INVALID",
                "Invalid application credentials"
            )
        
        # Verify secret with caching to prevent DoS
        import hashlib
        
        secret_hash = hashlib.sha256(access_secret.encode("utf-8")).hexdigest()
        cache_key = f"app_auth_ok_{application.id}_{secret_hash}"
        
        if not self.cache_service.get(cache_key):
            if not application.verify_secret(access_secret):
                return MiddlewareResult.error(
                    401,
                    "APP_AUTH_INVALID",
                    "Invalid application credentials"
                )
            # Cache successful verification for 60 seconds
            self.cache_service.set(cache_key, True, timeout=60)
        
        # Attach application to request
        request.application_id = str(application.id)
        request.metadata["application"] = application
        
        return MiddlewareResult.continue_(request)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from application auth."""
        # Exact match
        if path in self.settings.exact_exempt_paths:
            return True
        
        # Prefix match
        for exempt_path in self.settings.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        return False


class SecurityHeadersCoreMiddleware(CoreMiddleware):
    """
    Core middleware for adding security headers.
    """
    
    DEFAULT_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    }
    
    def process_response(
        self,
        request: RequestContext,
        response: ResponseContext
    ) -> ResponseContext:
        """Add security headers to response."""
        # Check if enabled in settings
        if getattr(self.settings, 'security_headers_enabled', True):
            headers = getattr(self.settings, 'security_headers', self.DEFAULT_HEADERS)
            for header, value in headers.items():
                response.headers[header] = value
        
        return response


# ============================================================
# Placeholder for other middlewares (to be implemented in Phase 2)
# ============================================================

class JWTAuthCoreMiddleware(CoreMiddleware):
    """Core middleware for JWT validation (to be fully implemented in Phase 2)."""
    
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        # TODO: Implement JWT validation logic in Phase 2
        # For now, just extract token if present
        auth_header = request.get_header("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            request.metadata["jwt_token"] = token
        
        return MiddlewareResult.continue_(request)


class CORSCoreMiddleware(CoreMiddleware):
    """Core middleware for CORS handling (to be fully implemented in Phase 2)."""
    
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        # TODO: Implement CORS preflight and validation in Phase 2
        return MiddlewareResult.continue_(request)
    
    def process_response(
        self,
        request: RequestContext,
        response: ResponseContext
    ) -> ResponseContext:
        # TODO: Add CORS headers in Phase 2
        return response


class OrganizationContextCoreMiddleware(CoreMiddleware):
    """Core middleware for organization context (to be fully implemented in Phase 2)."""
    
    def process_request(self, request: RequestContext) -> MiddlewareResult:
        # TODO: Implement organization context loading in Phase 2
        org_slug = request.get_header("X-Org-Slug")
        
        if org_slug:
            request.metadata["org_slug"] = org_slug
        
        return MiddlewareResult.continue_(request)


# Type hint imports (to avoid circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from tenxyte.core.settings import Settings
    from tenxyte.ports.repositories import ApplicationRepository
    from tenxyte.core.cache_service import CacheService
