"""
Tenxyte - Framework-Agnostic Python Authentication Package

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

__version__ = "1.0.0"
__author__ = "Tenxyte Team"
__license__ = "MIT"

# Final 0.9.x packaging-inversion warning (Requirement 2.7, specs/z_aud_1).
# Self-disabling: this fires only while __version__ still starts with "0.9" — once the version is
# bumped to 1.0.0, the packaging change described here has already happened, so the warning goes
# silent on its own without needing a separate removal commit. See docs/en/MIGRATION_GUIDE.md
# "0.9 -> 1.0" for the full picture.
if __version__.startswith("0.9"):
    import warnings as _warnings

    _warnings.warn(
        "Tenxyte 1.0 will change what 'pip install tenxyte' installs: it will install only the "
        "framework-agnostic Core (no Django) by default. If you use Tenxyte with Django, start "
        "pinning 'tenxyte[django]' now so your install command keeps working unchanged after "
        "upgrading to 1.0. See the Migration Guide's '0.9 -> 1.0' section for details.",
        DeprecationWarning,
        stacklevel=2,
    )
    del _warnings

from tenxyte.exceptions import TenxyteMissingDependencyError

# Lazy imports (PEP 562 module __getattr__) to avoid AppRegistryNotReady error AND to keep
# `import tenxyte` succeeding in a Core-only install (`pip install tenxyte`, without Django).
# Users can also import from tenxyte.models directly:
#   from tenxyte.models import AbstractUser, AbstractRole, AbstractPermission

__all__ = [
    "AbstractApplication",
    "AbstractPermission",
    "AbstractRole",
    "AbstractUser",
    "TenxyteMissingDependencyError",
    "get_application_model",
    "get_permission_model",
    "get_role_model",
    "get_user_model",
    "setup",
]

# Symbols resolved lazily through tenxyte.models — every entry in __all__ except "setup" (a real
# top-level function, defined below) and "TenxyteMissingDependencyError" (already imported above).
_DJANGO_ONLY_ATTRS = frozenset(__all__) - {"setup", "TenxyteMissingDependencyError"}


def __getattr__(name):
    """Lazy import of Django-only symbols (PEP 562) to avoid AppRegistryNotReady error.

    Keeps `import tenxyte` working without Django installed: only *accessing* one of these
    attributes triggers the Django-backed import, and a missing Django stack raises
    `TenxyteMissingDependencyError` with an explicit `pip install tenxyte[django]` instruction —
    never a bare, confusing `ModuleNotFoundError` surfacing from deep inside `tenxyte.models`.
    """
    if name in _DJANGO_ONLY_ATTRS:
        try:
            from tenxyte import models
        except ImportError as exc:
            raise TenxyteMissingDependencyError(
                f"'tenxyte.{name}' requires the Django stack. Install it with: pip install tenxyte[django]"
            ) from exc
        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Ensure Django-only symbols show up in introspection even before first access."""
    return sorted(set(globals()) | set(__all__))


def setup(settings_module=None):
    """
    Auto-configure Django settings for Tenxyte — zero-config quickstart.

    Call from your settings.py:
        import tenxyte
        tenxyte.setup()

    Or pass globals() to modify the settings dict directly:
        import tenxyte
        tenxyte.setup(globals())

    This function will NOT override settings that are already explicitly defined.
    It only fills in the minimal defaults needed to get Tenxyte running.

    What it configures (if not already set):
        - AUTH_USER_MODEL = 'tenxyte.User'
        - Adds 'rest_framework' and 'tenxyte' to INSTALLED_APPS
        - Sets DEFAULT_AUTHENTICATION_CLASSES for REST_FRAMEWORK
        - Adds ApplicationAuthMiddleware to MIDDLEWARE
    """
    try:
        from django.conf import settings as django_settings
    except ImportError as exc:
        raise TenxyteMissingDependencyError(
            "'tenxyte.setup' requires the Django stack. Install it with: pip install tenxyte[django]"
        ) from exc

    target = settings_module or django_settings

    # Check if target is a dict (from globals()) or a module object
    is_dict = isinstance(target, dict)

    def get_setting(name, default=None):
        """Get a setting value from either dict or module."""
        if is_dict:
            return target.get(name, default)
        return getattr(target, name, default)

    def set_setting(name, value):
        """Set a setting value on either dict or module."""
        if is_dict:
            target[name] = value
        else:
            setattr(target, name, value)

    # AUTH_USER_MODEL: set to tenxyte.User if still default or unset
    current_auth_model = get_setting("AUTH_USER_MODEL", "auth.User")
    if current_auth_model == "auth.User":
        set_setting("AUTH_USER_MODEL", "tenxyte.User")

    # INSTALLED_APPS: ensure rest_framework and tenxyte are present
    apps = list(get_setting("INSTALLED_APPS", []))
    changed = False
    for app in ["rest_framework", "tenxyte"]:
        if app not in apps:
            apps.append(app)
            changed = True
    if changed:
        set_setting("INSTALLED_APPS", apps)

    # REST_FRAMEWORK: set default auth class and schema class if not already configured
    rf = dict(get_setting("REST_FRAMEWORK", {}))
    changed_rf = False
    if "DEFAULT_AUTHENTICATION_CLASSES" not in rf:
        rf["DEFAULT_AUTHENTICATION_CLASSES"] = [
            "tenxyte.authentication.JWTAuthentication",
        ]
        changed_rf = True

    if "DEFAULT_SCHEMA_CLASS" not in rf:
        rf["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
        changed_rf = True

    if "EXCEPTION_HANDLER" not in rf:
        rf["EXCEPTION_HANDLER"] = "tenxyte.exceptions.custom_exception_handler"
        changed_rf = True

    if changed_rf:
        set_setting("REST_FRAMEWORK", rf)

    # MIDDLEWARE: add ApplicationAuthMiddleware if missing
    mw = list(get_setting("MIDDLEWARE", []))
    app_auth_mw = "tenxyte.middleware.ApplicationAuthMiddleware"
    if app_auth_mw not in mw:
        mw.append(app_auth_mw)
        set_setting("MIDDLEWARE", mw)
