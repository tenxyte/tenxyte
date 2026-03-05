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
    'setup',
]


def __getattr__(name):
    """Lazy import of models to avoid AppRegistryNotReady error."""
    if name in __all__:
        from tenxyte import models
        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def setup(settings_module=None):
    """
    Auto-configure Django settings for Tenxyte — zero-config quickstart.

    Call from your settings.py:
        import tenxyte
        tenxyte.setup()

    This function will NOT override settings that are already explicitly defined.
    It only fills in the minimal defaults needed to get Tenxyte running.

    What it configures (if not already set):
        - AUTH_USER_MODEL = 'tenxyte.User'
        - Adds 'rest_framework' and 'tenxyte' to INSTALLED_APPS
        - Sets DEFAULT_AUTHENTICATION_CLASSES for REST_FRAMEWORK
        - Adds ApplicationAuthMiddleware to MIDDLEWARE
    """
    from django.conf import settings as django_settings

    target = settings_module or django_settings

    # AUTH_USER_MODEL: set to tenxyte.User if still default or unset
    current_auth_model = getattr(target, 'AUTH_USER_MODEL', 'auth.User')
    if current_auth_model == 'auth.User':
        target.AUTH_USER_MODEL = 'tenxyte.User'

    # INSTALLED_APPS: ensure rest_framework and tenxyte are present
    apps = list(getattr(target, 'INSTALLED_APPS', []))
    changed = False
    for app in ['rest_framework', 'tenxyte']:
        if app not in apps:
            apps.append(app)
            changed = True
    if changed:
        target.INSTALLED_APPS = apps

    # REST_FRAMEWORK: set default auth class if not already configured
    rf = dict(getattr(target, 'REST_FRAMEWORK', {}))
    if 'DEFAULT_AUTHENTICATION_CLASSES' not in rf:
        rf['DEFAULT_AUTHENTICATION_CLASSES'] = [
            'tenxyte.authentication.JWTAuthentication',
        ]
        target.REST_FRAMEWORK = rf

    # MIDDLEWARE: add ApplicationAuthMiddleware if missing
    mw = list(getattr(target, 'MIDDLEWARE', []))
    app_auth_mw = 'tenxyte.middleware.ApplicationAuthMiddleware'
    if app_auth_mw not in mw:
        mw.append(app_auth_mw)
        target.MIDDLEWARE = mw
