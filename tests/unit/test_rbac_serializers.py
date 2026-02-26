import pytest
from tenxyte.serializers.rbac_serializers import (
    PermissionSerializer,
    RoleSerializer,
    RoleListSerializer,
    ManageRolePermissionsSerializer,
    AssignRoleSerializer,
    UserRolesSerializer,
)
from tenxyte.models import get_role_model, get_permission_model
from rest_framework.exceptions import ValidationError

Role = get_role_model()
Permission = get_permission_model()


@pytest.mark.django_db
class TestPermissionSerializer:
    def test_serialization_with_hierarchy(self):
        parent = Permission.objects.create(code='parent_perm', name='Parent')
        child = Permission.objects.create(code='child_perm', name='Child', parent=parent)
        
        serializer = PermissionSerializer(child)
        data = serializer.data
        
        assert data['code'] == 'child_perm'
        assert data['parent']['code'] == 'parent_perm'
        assert data['children'] == []
        
        parent_serializer = PermissionSerializer(parent)
        parent_data = parent_serializer.data
        assert len(parent_data['children']) == 1
        assert parent_data['children'][0]['code'] == 'child_perm'

    def test_create_permission(self):
        parent = Permission.objects.create(code='parent_perm', name='Parent')
        data = {
            'code': 'new_perm',
            'name': 'New Perm',
            'parent_code': 'parent_perm'
        }
        serializer = PermissionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        
        perm = Permission.objects.get(code='new_perm')
        assert perm.parent == parent

    def test_create_with_invalid_parent(self):
        data = {
            'code': 'new_perm',
            'name': 'New Perm',
            'parent_code': 'nonexistent'
        }
        # In DRF, if a field is not defined in the model or serializer explicitly, 
        # but is in data and not in fields, it might be ignored. However, parent_code IS defined.
        # It's a CharField. It passes is_valid, but during create, the ObjectDoesNotExist
        # is caught and a serializers.ValidationError is raised.
        serializer = PermissionSerializer(data=data)
        assert serializer.is_valid()
        with pytest.raises(ValidationError) as exc_info:
            serializer.save()
        assert 'parent_code' in exc_info.value.detail

    def test_update_permission(self):
        parent1 = Permission.objects.create(code='parent_1', name='P1')
        parent2 = Permission.objects.create(code='parent_2', name='P2')
        child = Permission.objects.create(code='child', name='C', parent=parent1)
        
        data = {'parent_code': 'parent_2'}
        serializer = PermissionSerializer(instance=child, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        
        child.refresh_from_db()
        assert child.parent == parent2

    def test_update_permission_remove_parent(self):
        parent = Permission.objects.create(code='parent_1', name='P1')
        child = Permission.objects.create(code='child', name='C', parent=parent)
        
        # To remove parent, parent_code must be None
        # But DRF CharField by default does not allow null unless allow_null=True
        # In PermissionSerializer: parent_code = serializers.CharField(..., allow_null=True)
        # So None IS allowed.
        data = {'parent_code': None}
        serializer = PermissionSerializer(instance=child, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        
        child.refresh_from_db()
        assert child.parent is None
        
    def test_update_with_invalid_parent(self):
        child = Permission.objects.create(code='child', name='C')
        data = {'parent_code': 'invalid'}
        serializer = PermissionSerializer(instance=child, data=data, partial=True)
        # Similar to create, is_valid will pass, save will fail
        assert serializer.is_valid()
        with pytest.raises(ValidationError) as exc_info:
            serializer.save()
        assert 'parent_code' in exc_info.value.detail


@pytest.mark.django_db
class TestRoleSerializer:
    def test_create_role_with_permissions(self):
        Permission.objects.create(code='perm1', name='P1')
        Permission.objects.create(code='perm2', name='P2')
        
        data = {
            'code': 'new_role',
            'name': 'New Role',
            'permission_codes': ['perm1', 'perm2']
        }
        serializer = RoleSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        role = serializer.save()
        
        assert role.code == 'new_role'
        assert role.permissions.count() == 2

    def test_update_role_permissions(self):
        perm1 = Permission.objects.create(code='perm1', name='P1')
        perm2 = Permission.objects.create(code='perm2', name='P2')
        role = Role.objects.create(code='test_role', name='Test')
        role.permissions.add(perm1)
        
        data = {
            'permission_codes': ['perm2']
        }
        serializer = RoleSerializer(instance=role, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        role = serializer.save()
        
        assert role.permissions.count() == 1
        assert role.permissions.first() == perm2


@pytest.mark.django_db
class TestRoleListSerializer:
    def test_serialization(self):
        role = Role.objects.create(code='list_role', name='List', is_default=True)
        serializer = RoleListSerializer(role)
        data = serializer.data
        
        assert data['code'] == 'list_role'
        assert data['is_default'] is True
        assert 'permissions' not in data


class TestManageRolePermissionsSerializer:
    def test_valid_data(self):
        data = {'permission_codes': ['perm1', 'perm2']}
        serializer = ManageRolePermissionsSerializer(data=data)
        assert serializer.is_valid()

    def test_empty_permissions(self):
        data = {'permission_codes': []}
        serializer = ManageRolePermissionsSerializer(data=data)
        assert not serializer.is_valid()
        assert 'permission_codes' in serializer.errors


class TestAssignRoleSerializer:
    def test_valid_data(self):
        data = {'role_code': 'admin'}
        serializer = AssignRoleSerializer(data=data)
        assert serializer.is_valid()


class TestUserRolesSerializer:
    def test_valid_data(self):
        data = {'user_id': 'user123', 'role_codes': ['admin', 'user']}
        serializer = UserRolesSerializer(data=data)
        assert serializer.is_valid()
