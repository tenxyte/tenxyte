"""Tenxyte Django Adapter."""

from .cache_service import DjangoCacheService, get_cache_service
from .email_service import DjangoEmailService, get_email_service
from .middleware import (
    ApplicationAuthMiddleware,
    CORSMiddleware,
    DjangoApplicationAuthMiddleware,
    DjangoCORSMiddleware,
    DjangoJWTAuthMiddleware,
    DjangoOrganizationContextMiddleware,
    DjangoRequestIDMiddleware,
    DjangoSecurityHeadersMiddleware,
    JWTAuthMiddleware,
    OrganizationContextMiddleware,
    # Backward compatibility aliases
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from .settings_provider import DjangoSettingsProvider, get_django_settings
from .task_service import CeleryTaskService, RQTaskService, SyncThreadTaskService

__all__ = [  # noqa: RUF022
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
