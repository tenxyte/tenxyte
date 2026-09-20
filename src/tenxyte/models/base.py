"""
Tenxyte Models - Base utilities and model helpers.

Contains:
- AutoFieldClass: Auto-detection of MongoDB vs SQL auto field
- get_user_model, get_role_model, get_permission_model, get_application_model: Swappable model helpers
"""

import functools
import uuid

from django.conf import settings
from django.db import models


# Détection du backend pour MongoDB
# On vérifie le moteur DB configuré, pas juste la disponibilité du package,
# pour éviter d'utiliser ObjectIdAutoField sur SQLite/PG/MySQL quand
# django-mongodb-backend est installé.
#
# On SQL backends, every concrete model calls this as `AutoFieldClass(primary_key=True)` — a
# `functools.partial(models.UUIDField, default=uuid.uuid4, editable=False)` is a drop-in
# replacement for that call shape: once called with `primary_key=True`, the result is exactly
# Django's own documented UUID-PK pattern. This makes every Django ID UUID-shaped, matching the
# FastAPI_Adapter's Reference_Stack (`generate_uuid` default throughout `models_sa.py`) — a
# real cross-adapter inconsistency (sequential integer IDs on Django, UUIDs on FastAPI) the user
# asked to resolve in favor of UUID everywhere, for the non-enumerable-ID security property a
# sequential integer PK doesn't have (breaking change, MAJOR version only — see stability.md and
# the v0.9.x -> v1.0.0 entry in MIGRATION_GUIDE.md).
def _get_auto_field_class():
    try:
        db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    except Exception:  # noqa: BLE001
        db_engine = ""
    if "mongodb" in db_engine:
        try:
            from django_mongodb_backend.fields import ObjectIdAutoField

            return ObjectIdAutoField
        except ImportError:
            pass
    return functools.partial(models.UUIDField, default=uuid.uuid4, editable=False)


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
