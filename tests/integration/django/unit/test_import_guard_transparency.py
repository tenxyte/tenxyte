"""
Import_Guard transparency tests — with Django installed, every historical `tenxyte.*` symbol must
resolve exactly as before the PEP 562 refactor.

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 2.5 / 8.2, design.md "Property 3".
"""

import tenxyte
from tenxyte import models as tenxyte_models


def test_setup_resolves_to_the_real_function():
    assert callable(tenxyte.setup)
    assert tenxyte.setup.__name__ == "setup"


def test_abstract_model_symbols_resolve_identically_to_tenxyte_models():
    """Feature: z_aud_1, Property 3: transparence de l'Import_Guard avec Django présent."""
    assert tenxyte.AbstractUser is tenxyte_models.AbstractUser
    assert tenxyte.AbstractRole is tenxyte_models.AbstractRole
    assert tenxyte.AbstractPermission is tenxyte_models.AbstractPermission
    assert tenxyte.AbstractApplication is tenxyte_models.AbstractApplication


def test_model_factory_functions_resolve_identically():
    assert tenxyte.get_user_model is tenxyte_models.get_user_model
    assert tenxyte.get_role_model is tenxyte_models.get_role_model
    assert tenxyte.get_permission_model is tenxyte_models.get_permission_model
    assert tenxyte.get_application_model is tenxyte_models.get_application_model


def test_dir_includes_all_documented_symbols():
    exported = set(dir(tenxyte))
    for name in tenxyte.__all__:
        assert name in exported


def test_repeated_access_returns_the_same_object():
    """No re-import / re-creation on repeated attribute access."""
    first = tenxyte.AbstractUser
    second = tenxyte.AbstractUser
    assert first is second


def test_setup_is_still_callable_end_to_end():
    """Non-regression (Requirement 8.2): setup() behaves identically with Django installed."""
    fake_settings = {"INSTALLED_APPS": [], "MIDDLEWARE": [], "REST_FRAMEWORK": {}}
    tenxyte.setup(fake_settings)
    assert "rest_framework" in fake_settings["INSTALLED_APPS"]
    assert "tenxyte" in fake_settings["INSTALLED_APPS"]
    assert fake_settings["AUTH_USER_MODEL"] == "tenxyte.User"
