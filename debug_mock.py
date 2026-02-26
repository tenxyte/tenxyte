import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from unittest.mock import patch
from tenxyte.models import Role, Permission
from tenxyte.views.rbac_views import RolePermissionsView

role = Role.objects.create(code="test_debug_role", name="Test Role")
Permission.objects.all().delete()
p1 = Permission.objects.create(code="p1", name="p1")
p2 = Permission.objects.create(code="p2", name="p2")

view = RolePermissionsView()

print("Original add works:")
view._safe_add_permissions(role, [p1])
print("Role perms:", role.permissions.count())

print("\nTrying to patch role.permissions.add on the instance:")
def fake_add(*args, **kwargs):
    print(f"fake_add called with {len(args)} args!")
    raise TypeError("fake_add type error")

with patch.object(role.permissions, 'add', side_effect=fake_add):
    try:
        view._safe_add_permissions(role, [p2])
    except Exception as e:
        print("Exception escaped?", e)
    print("Role perms after fake_add:", role.permissions.count())

print("\nLet's patch the class method:")
ManagerClass = role.permissions.__class__
with patch.object(ManagerClass, 'add', side_effect=fake_add, autospec=True):
    try:
        view._safe_add_permissions(role, [p2])
    except Exception as e:
        print("Exception escaped?", e)
    print("Role perms after class patch:", role.permissions.count())
