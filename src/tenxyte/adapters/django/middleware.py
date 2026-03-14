"""
Django Middleware Wrappers for Tenxyte Core.

These middlewares wrap the Core middleware logic in Django's middleware pattern.
They translate between Django's request/response objects and the Core's
framework-agnostic RequestContext/ResponseContext.
"""

from typing import Optional

from django.http import HttpResponse, JsonResponse
from django.conf import settings as django_settings

from tenxyte.core.middleware import (
    RequestContext,
    ResponseContext,
    MiddlewareResult,
    CoreMiddleware,
    RequestIDCoreMiddleware,
    ApplicationAuthCoreMiddleware,
    SecurityHeadersCoreMiddleware,
    JWTAuthCoreMiddleware,
    CORSCoreMiddleware,
    OrganizationContextCoreMiddleware,
)
from tenxyte.core.settings import Settings
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider


def _django_request_to_context(request) -> RequestContext:
    """
    Convert Django request to framework-agnostic RequestContext.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        RequestContext for Core processing
    """
    # Build headers dict from Django request
    headers = {}
    for key, value in request.headers.items():
        headers[key] = value
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR')
    
    context = RequestContext(
        method=request.method,
        path=request.path,
        headers=headers,
        query_params=dict(request.GET),
        client_ip=client_ip,
        user_agent=request.META.get('HTTP_USER_AGENT'),
    )
    
    # Preserve existing metadata from previous middleware
    if hasattr(request, 'request_id'):
        context.request_id = request.request_id
    if hasattr(request, 'user_id'):
        context.user_id = request.user_id
    if hasattr(request, 'application'):
        context.metadata['application'] = request.application
        if request.application:
            context.application_id = str(request.application.id)
    
    return context


def _context_to_django_response(context: ResponseContext) -> HttpResponse:
    """
    Convert Core ResponseContext to Django response.
    
    Args:
        context: ResponseContext from Core processing
        
    Returns:
        Django HttpResponse object
    """
    # Determine response type
    if context.json_data:
        response = JsonResponse(context.json_data, status=context.status_code)
    elif context.body:
        response = HttpResponse(
            content=context.body,
            status=context.status_code,
            content_type=context.headers.get('Content-Type', 'application/octet-stream')
        )
    else:
        response = HttpResponse(status=context.status_code)
    
    # Add headers
    for header, value in context.headers.items():
        if header != 'Content-Type':  # Already set for JsonResponse
            response[header] = value
    
    return response


def _update_django_request(request, context: RequestContext):
    """
    Update Django request object with data from Core context.
    
    Args:
        request: Django HttpRequest to update
        context: RequestContext with processed data
    """
    # Update request attributes from context
    if context.request_id:
        request.request_id = context.request_id
    if context.user_id:
        request.user_id = context.user_id
    if context.application_id:
        request.application = context.metadata.get('application')
    if context.organization_id:
        request.organization_id = context.organization_id
    
    # Store full context for access by other middleware
    request.tenxyte_context = context


class BaseDjangoMiddleware:
    """
    Base class for Django middleware wrappers.
    
    Handles the conversion between Django and Core request/response formats.
    """
    
    def __init__(self, get_response, core_middleware_class: type[CoreMiddleware]):
        """
        Initialize middleware.
        
        Args:
            get_response: Django get_response callable
            core_middleware_class: Core middleware class to wrap
        """
        self.get_response = get_response
        self.core_middleware_class = core_middleware_class
        self._core_middleware: Optional[CoreMiddleware] = None
    
    @property
    def core_middleware(self) -> CoreMiddleware:
        """Lazy initialization of Core middleware."""
        if self._core_middleware is None:
            settings = Settings(provider=DjangoSettingsProvider())
            self._core_middleware = self.core_middleware_class(settings)
        return self._core_middleware
    
    def __call__(self, request):
        """Django middleware entry point."""
        # Convert Django request to Core context
        context = _django_request_to_context(request)
        
        # Process request through Core middleware
        result = self.core_middleware.process_request(context)
        
        # Update Django request with context data
        if result.modified_request:
            _update_django_request(request, result.modified_request)
            context = result.modified_request
        
        # Check if middleware wants to respond immediately
        if not result.continue_processing:
            if result.response:
                return _context_to_django_response(result.response)
            else:
                # Should not happen, but handle gracefully
                return HttpResponse(status=500)
        
        # Continue to next middleware/handler
        response = self.get_response(request)
        
        # Convert Django response to Core context for response processing
        response_context = ResponseContext(
            status_code=response.status_code,
            headers={k: v for k, v in response.items()},
            body=response.content if hasattr(response, 'content') else None
        )
        
        # Process response through Core middleware
        modified_response = self.core_middleware.process_response(
            context,
            response_context
        )
        
        # Update Django response with modified headers
        for header, value in modified_response.headers.items():
            if header not in response:
                response[header] = value
        
        return response


# ============================================================
# Django Middleware Implementations
# ============================================================

class DjangoRequestIDMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for RequestIDCoreMiddleware.
    
    Adds X-Request-ID header for request tracing.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response, RequestIDCoreMiddleware)


class DjangoApplicationAuthMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for ApplicationAuthCoreMiddleware.
    
    Validates X-Access-Key and X-Access-Secret headers.
    """
    
    def __init__(self, get_response):
        # TODO: Inject ApplicationRepository in Phase 2
        # For now, use placeholder initialization
        super().__init__(get_response, ApplicationAuthCoreMiddleware)
    
    @property
    def core_middleware(self) -> CoreMiddleware:
        """Override to inject ApplicationRepository."""
        if self._core_middleware is None:
            from tenxyte.core.settings import Settings
            from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
            
            settings = Settings(provider=DjangoSettingsProvider())
            
            # TODO: Create DjangoApplicationRepository in Phase 2
            # For now, use a placeholder that will be implemented later
            class PlaceholderApplicationRepository:
                def get_by_access_key(self, access_key: str):
                    from tenxyte.models import Application
                    try:
                        return Application.objects.get(access_key=access_key, is_active=True)
                    except Application.DoesNotExist:
                        return None
            
            self._core_middleware = ApplicationAuthCoreMiddleware(
                settings,
                PlaceholderApplicationRepository()
            )
        return self._core_middleware


class DjangoSecurityHeadersMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for SecurityHeadersCoreMiddleware.
    
    Adds security headers to responses.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response, SecurityHeadersCoreMiddleware)


class DjangoJWTAuthMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for JWTAuthCoreMiddleware.
    
    Extracts and validates JWT tokens from Authorization header.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response, JWTAuthCoreMiddleware)


class DjangoCORSMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for CORSCoreMiddleware.
    
    Handles CORS preflight requests and headers.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response, CORSCoreMiddleware)


class DjangoOrganizationContextMiddleware(BaseDjangoMiddleware):
    """
    Django middleware wrapper for OrganizationContextCoreMiddleware.
    
    Loads organization context from X-Org-Slug header.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response, OrganizationContextCoreMiddleware)


# Backward compatibility aliases
# These maintain the old import paths while using the new Core-based implementation

RequestIDMiddleware = DjangoRequestIDMiddleware
ApplicationAuthMiddleware = DjangoApplicationAuthMiddleware
SecurityHeadersMiddleware = DjangoSecurityHeadersMiddleware
JWTAuthMiddleware = DjangoJWTAuthMiddleware
CORSMiddleware = DjangoCORSMiddleware
OrganizationContextMiddleware = DjangoOrganizationContextMiddleware
