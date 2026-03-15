"""Tenxyte Django Adapter."""

from .settings_provider import DjangoSettingsProvider, get_django_settings
from .email_service import DjangoEmailService, get_email_service
from .cache_service import DjangoCacheService, get_cache_service
from .task_service import CeleryTaskService, RQTaskService, SyncThreadTaskService
from .middleware import (
    DjangoRequestIDMiddleware,
    DjangoApplicationAuthMiddleware,
    DjangoSecurityHeadersMiddleware,
    DjangoJWTAuthMiddleware,
    DjangoCORSMiddleware,
    DjangoOrganizationContextMiddleware,
    # Backward compatibility aliases
    RequestIDMiddleware,
    ApplicationAuthMiddleware,
    SecurityHeadersMiddleware,
    JWTAuthMiddleware,
    CORSMiddleware,
    OrganizationContextMiddleware,
)

__all__ = [
    # Settings
    "DjangoSettingsProvider",
    "get_django_settings",
    # Services
    "DjangoEmailService",
    "get_email_service",
    "DjangoCacheService",
    "get_cache_service",
    "CeleryTaskService",
    "RQTaskService",
    "SyncThreadTaskService",
    # Middleware (new names)
    "DjangoRequestIDMiddleware",
    "DjangoApplicationAuthMiddleware",
    "DjangoSecurityHeadersMiddleware",
    "DjangoJWTAuthMiddleware",
    "DjangoCORSMiddleware",
    "DjangoOrganizationContextMiddleware",
    # Middleware (backward compatible names)
    "RequestIDMiddleware",
    "ApplicationAuthMiddleware",
    "SecurityHeadersMiddleware",
    "JWTAuthMiddleware",
    "CORSMiddleware",
    "OrganizationContextMiddleware",
]
