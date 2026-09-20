import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
def test_get_auto_field_class_exception():
    with patch("tenxyte.models.base.settings.DATABASES", new_callable=MagicMock) as mock_db:
        mock_db.get.side_effect = Exception("DB error")
        from django.db import models
        from tenxyte.models.base import _get_auto_field_class

        # Non-Mongo fallback is a functools.partial(models.UUIDField, default=uuid.uuid4,
        # editable=False) -- a drop-in replacement for the old `AutoFieldClass(primary_key=True)`
        # call shape every model uses (see models/base.py's own docstring on this). `partial`
        # doesn't support equality comparison, so assert on its shape and on the field it
        # actually produces when called, matching real usage.
        result = _get_auto_field_class()
        assert result.func is models.UUIDField
        assert result.keywords["editable"] is False
        field = result(primary_key=True)
        assert isinstance(field, models.UUIDField)
        assert field.primary_key is True


@pytest.mark.django_db
def test_get_auto_field_class_mongodb_available():
    import sys

    with patch("tenxyte.models.base.settings.DATABASES", {"default": {"ENGINE": "mongodb"}}):
        mock_fields = MagicMock()
        mock_fields.ObjectIdAutoField = "MockObjectIdAutoField"
        mock_mongodb_backend = MagicMock()
        mock_mongodb_backend.fields = mock_fields

        with patch.dict(
            sys.modules, {"django_mongodb_backend": mock_mongodb_backend, "django_mongodb_backend.fields": mock_fields}
        ):
            from tenxyte.models.base import _get_auto_field_class

            assert _get_auto_field_class() == "MockObjectIdAutoField"


@pytest.mark.django_db
def test_get_user_model_fallback():
    with patch("django.apps.apps.get_model", side_effect=LookupError):
        from tenxyte.models.auth import User
        from tenxyte.models.base import get_user_model

        assert get_user_model() == User


@pytest.mark.django_db
def test_get_role_model_fallback():
    with patch("django.apps.apps.get_model", side_effect=LookupError):
        from tenxyte.models.auth import Role
        from tenxyte.models.base import get_role_model

        assert get_role_model() == Role


@pytest.mark.django_db
def test_get_permission_model_fallback():
    with patch("django.apps.apps.get_model", side_effect=ValueError):
        from tenxyte.models.auth import Permission
        from tenxyte.models.base import get_permission_model

        assert get_permission_model() == Permission


@pytest.mark.django_db
def test_get_application_model_fallback():
    with patch("django.apps.apps.get_model", side_effect=LookupError):
        from tenxyte.models.application import Application
        from tenxyte.models.base import get_application_model

        assert get_application_model() == Application
