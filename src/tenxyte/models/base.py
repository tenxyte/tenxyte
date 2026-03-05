"""
Tenxyte Models - Base utilities and model helpers.

Contains:
- AutoFieldClass: Auto-detection of MongoDB vs SQL auto field
- get_user_model, get_role_model, get_permission_model, get_application_model: Swappable model helpers
"""

from django.db import models
from django.conf import settings


# Détection du backend pour MongoDB
# On vérifie le moteur DB configuré, pas juste la disponibilité du package,
# pour éviter d'utiliser ObjectIdAutoField sur SQLite/PG/MySQL quand
# django-mongodb-backend est installé.
def _get_auto_field_class():
    try:
        db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    except Exception:
        db_engine = ""
    if "mongodb" in db_engine:
        try:
            from django_mongodb_backend.fields import ObjectIdAutoField

            return ObjectIdAutoField
        except ImportError:
            pass
    return models.BigAutoField


AutoFieldClass = _get_auto_field_class()


# =============================================================================
# HELPERS - Get swappable models
# =============================================================================


def get_user_model():
    """
    Returns the User model that is active in this project.
    Similar to django.contrib.auth.get_user_model().
    """
    from django.apps import apps

    model_path = getattr(settings, "TENXYTE_USER_MODEL", "tenxyte.User")
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        from .auth import User

        return User


def get_role_model():
    """
    Returns the Role model that is active in this project.
    """
    from django.apps import apps

    model_path = getattr(settings, "TENXYTE_ROLE_MODEL", "tenxyte.Role")
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        from .auth import Role

        return Role


def get_permission_model():
    """
    Returns the Permission model that is active in this project.
    """
    from django.apps import apps

    model_path = getattr(settings, "TENXYTE_PERMISSION_MODEL", "tenxyte.Permission")
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        from .auth import Permission

        return Permission


def get_application_model():
    """
    Returns the Application model that is active in this project.
    """
    from django.apps import apps

    model_path = getattr(settings, "TENXYTE_APPLICATION_MODEL", "tenxyte.Application")
    try:
        return apps.get_model(model_path, require_ready=False)
    except (ValueError, LookupError):
        from .application import Application

        return Application


def get_organization_model():
    """Get the configured Organization model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_MODEL)


def get_organization_role_model():
    """Get the configured OrganizationRole model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_ROLE_MODEL)


def get_organization_membership_model():
    """Get the configured OrganizationMembership model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_MEMBERSHIP_MODEL)
