"""
Application serializers - Application CRUD.
"""
from rest_framework import serializers
from ..models import get_application_model

Application = get_application_model()


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les applications (sans le secret)"""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'access_key', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'access_key', 'created_at', 'updated_at']


class ApplicationCreateSerializer(serializers.Serializer):
    """Serializer pour créer une application"""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, default='', allow_blank=True)


class ApplicationUpdateSerializer(serializers.Serializer):
    """Serializer pour mettre à jour une application"""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
