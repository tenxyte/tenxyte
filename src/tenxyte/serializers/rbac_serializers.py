"""
RBAC serializers - Permission, Role, User roles & permissions management.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import get_role_model, get_permission_model

Role = get_role_model()
Permission = get_permission_model()


class PermissionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    parent_code = serializers.CharField(
        write_only=True, required=False, allow_null=True,
        help_text="Code de la permission parente (hiérarchie)"
    )
    parent = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'parent', 'parent_code', 'children', 'created_at']
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_parent(self, obj):
        if obj.parent:
            return {'id': str(obj.parent.id), 'code': obj.parent.code}
        return None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        children = obj.children.all()
        if not children.exists():
            return []
        return [{'id': str(c.id), 'code': c.code, 'name': c.name} for c in children]

    def create(self, validated_data):
        parent_code = validated_data.pop('parent_code', None)
        if parent_code:
            try:
                validated_data['parent'] = Permission.objects.get(code=parent_code)
            except Permission.DoesNotExist:
                raise serializers.ValidationError({'parent_code': f'Permission "{parent_code}" not found'})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        parent_code = validated_data.pop('parent_code', None)
        if parent_code is not None:
            if parent_code:
                try:
                    validated_data['parent'] = Permission.objects.get(code=parent_code)
                except Permission.DoesNotExist:
                    raise serializers.ValidationError({'parent_code': f'Permission "{parent_code}" not found'})
            else:
                validated_data['parent'] = None
        return super().update(instance, validated_data)


class RoleSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'permissions', 'permission_codes', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        permission_codes = validated_data.pop('permission_codes', [])
        role = Role.objects.create(**validated_data)
        if permission_codes:
            permissions = Permission.objects.filter(code__in=permission_codes)
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permission_codes = validated_data.pop('permission_codes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permission_codes is not None:
            permissions = Permission.objects.filter(code__in=permission_codes)
            instance.permissions.set(permissions)
        return instance


class RoleListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes"""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'is_default']


class ManageRolePermissionsSerializer(serializers.Serializer):
    permission_codes = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        help_text="Liste des codes de permissions à ajouter ou retirer"
    )


class AssignRoleSerializer(serializers.Serializer):
    role_code = serializers.CharField()


class UserRolesSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    role_codes = serializers.ListField(child=serializers.CharField())
