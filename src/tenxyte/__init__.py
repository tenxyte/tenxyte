"""
Tenxyte - Complete Django Authentication Package

Features:
- JWT authentication with access and refresh tokens
- Role-Based Access Control (RBAC)
- Two-Factor Authentication (TOTP) compatible with Google Authenticator
- OTP verification (email and SMS)
- Multi-application support (multiple clients)
- Password validation and strength checking
- Rate limiting and security features
- Extensible User, Role, Permission, and Application models

Usage:
    # settings.py
    INSTALLED_APPS = [
        ...
        'rest_framework',
        'tenxyte',
    ]

    # urls.py
    urlpatterns = [
        path('api/auth/', include('tenxyte.urls')),
    ]

Extending Models:
    from tenxyte.models import AbstractUser, AbstractRole, AbstractPermission, AbstractApplication

    class CustomUser(AbstractUser):
        company = models.CharField(max_length=100)

        class Meta(AbstractUser.Meta):
            db_table = 'custom_users'

    class CustomApplication(AbstractApplication):
        owner = models.ForeignKey('myapp.CustomUser', on_delete=models.CASCADE)

        class Meta(AbstractApplication.Meta):
            db_table = 'custom_applications'

    # settings.py
    TENXYTE_USER_MODEL = 'myapp.CustomUser'
    AUTH_USER_MODEL = 'myapp.CustomUser'
    TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'

Documentation: https://tenxyte.readthedocs.io
"""

__version__ = "0.0.8.3.9.7"
__author__ = "Tenxyte Team"
__license__ = "MIT"

# Lazy imports to avoid AppRegistryNotReady error
# Users should import from tenxyte.models directly:
#   from tenxyte.models import AbstractUser, AbstractRole, AbstractPermission

__all__ = [
    'AbstractUser',
    'AbstractRole',
    'AbstractPermission',
    'AbstractApplication',
    'get_user_model',
    'get_role_model',
    'get_permission_model',
    'get_application_model',
]


def __getattr__(name):
    """Lazy import of models to avoid AppRegistryNotReady error."""
    if name in __all__:
        from tenxyte import models
        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
