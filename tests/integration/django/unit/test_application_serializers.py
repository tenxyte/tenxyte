import pytest
from tenxyte.serializers.application_serializers import (
    ApplicationSerializer,
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
)
from tenxyte.models import get_application_model

Application = get_application_model()


@pytest.mark.django_db
class TestApplicationSerializer:
    def test_application_serialization(self):
        app, secret = Application.create_application(name="Test App", description="Desc")
        serializer = ApplicationSerializer(app)
        data = serializer.data
        
        assert data['name'] == "Test App"
        assert data['description'] == "Desc"
        assert data['access_key'] == app.access_key
        assert data['is_active'] is True
        assert 'access_secret' not in data

class TestApplicationCreateSerializer:
    def test_valid_create(self):
        data = {'name': 'New App', 'description': 'Some description'}
        serializer = ApplicationCreateSerializer(data=data)
        assert serializer.is_valid()
        
    def test_missing_name(self):
        data = {'description': 'Some description'}
        serializer = ApplicationCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    def test_empty_description(self):
        data = {'name': 'New App'}
        serializer = ApplicationCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['description'] == ''


class TestApplicationUpdateSerializer:
    def test_valid_update_all_fields(self):
        data = {'name': 'Updated App', 'description': 'Updated desc', 'is_active': False}
        serializer = ApplicationUpdateSerializer(data=data)
        assert serializer.is_valid()

    def test_valid_update_partial_fields(self):
        data = {'name': 'Updated App'}
        serializer = ApplicationUpdateSerializer(data=data)
        assert serializer.is_valid()

    def test_empty_update(self):
        data = {}
        serializer = ApplicationUpdateSerializer(data=data)
        assert serializer.is_valid()
