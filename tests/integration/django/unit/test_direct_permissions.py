"""
Tests unitaires pour les permissions directes par utilisateur.

Vérifie le champ direct_permissions M2M sur User,
et que has_permission()/get_all_permissions() incluent les permissions directes.
"""

import pytest
from tenxyte.models import User, Permission, Role


class TestDirectPermissionsModel:
    """Tests pour le champ direct_permissions M2M."""

    @pytest.mark.django_db
    def test_direct_permissions_empty_by_default(self):
        """Un utilisateur n'a aucune permission directe par défaut."""
        user = User.objects.create_user(email="dp1@test.com", password="Test123!@#")
        assert user.direct_permissions.count() == 0

    @pytest.mark.django_db
    def test_add_direct_permission(self):
        """On peut ajouter une permission directe à un utilisateur."""
        user = User.objects.create_user(email="dp2@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="special.action", name="Special Action")

        user.direct_permissions.add(perm)
        assert user.direct_permissions.count() == 1
        assert perm in user.direct_permissions.all()

    @pytest.mark.django_db
    def test_remove_direct_permission(self):
        """On peut retirer une permission directe."""
        user = User.objects.create_user(email="dp3@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="temp.perm", name="Temp")

        user.direct_permissions.add(perm)
        assert user.direct_permissions.count() == 1

        user.direct_permissions.remove(perm)
        assert user.direct_permissions.count() == 0

    @pytest.mark.django_db
    def test_users_direct_reverse_relation(self):
        """Le related_name 'users_direct' fonctionne sur Permission."""
        perm = Permission.objects.create(code="reverse.test", name="Reverse")
        user1 = User.objects.create_user(email="dp4a@test.com", password="Test123!@#")
        user2 = User.objects.create_user(email="dp4b@test.com", password="Test123!@#")

        user1.direct_permissions.add(perm)
        user2.direct_permissions.add(perm)

        assert perm.users_direct.count() == 2


class TestHasPermissionWithDirect:
    """Tests que has_permission() prend en compte les permissions directes."""

    @pytest.mark.django_db
    def test_has_direct_permission(self):
        """has_permission() retourne True pour une permission directe."""
        user = User.objects.create_user(email="dp5@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="direct.only", name="Direct Only")
        user.direct_permissions.add(perm)

        assert user.has_permission("direct.only") is True

    @pytest.mark.django_db
    def test_has_permission_no_role_no_direct(self):
        """has_permission() retourne False sans rôle ni permission directe."""
        user = User.objects.create_user(email="dp6@test.com", password="Test123!@#")
        Permission.objects.create(code="orphan.perm", name="Orphan")

        assert user.has_permission("orphan.perm") is False

    @pytest.mark.django_db
    def test_has_permission_via_role_and_direct(self):
        """has_permission() fonctionne quand la permission vient du rôle ou directe."""
        user = User.objects.create_user(email="dp7@test.com", password="Test123!@#")
        perm_role = Permission.objects.create(code="from.role", name="From Role")
        perm_direct = Permission.objects.create(code="from.direct", name="From Direct")

        role = Role.objects.create(code="basic", name="Basic")
        role.permissions.add(perm_role)
        user.roles.add(role)
        user.direct_permissions.add(perm_direct)

        assert user.has_permission("from.role") is True
        assert user.has_permission("from.direct") is True

    @pytest.mark.django_db
    def test_get_all_permissions_includes_direct(self):
        """get_all_permissions() inclut les permissions directes et celles des rôles."""
        user = User.objects.create_user(email="dp8@test.com", password="Test123!@#")
        perm_role = Permission.objects.create(code="role.perm", name="Role Perm")
        perm_direct = Permission.objects.create(code="direct.perm", name="Direct Perm")

        role = Role.objects.create(code="mixed", name="Mixed")
        role.permissions.add(perm_role)
        user.roles.add(role)
        user.direct_permissions.add(perm_direct)

        all_perms = user.get_all_permissions()
        assert "role.perm" in all_perms
        assert "direct.perm" in all_perms

    @pytest.mark.django_db
    def test_get_all_permissions_no_duplicates(self):
        """get_all_permissions() ne duplique pas si la même permission vient du rôle et directe."""
        user = User.objects.create_user(email="dp9@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="shared.perm", name="Shared")

        role = Role.objects.create(code="shared_role", name="Shared Role")
        role.permissions.add(perm)
        user.roles.add(role)
        user.direct_permissions.add(perm)

        all_perms = user.get_all_permissions()
        assert all_perms.count("shared.perm") == 1

    @pytest.mark.django_db
    def test_has_any_permission_with_direct(self):
        """has_any_permission() fonctionne avec les permissions directes."""
        user = User.objects.create_user(email="dp10@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="any.direct", name="Any Direct")
        user.direct_permissions.add(perm)

        assert user.has_any_permission(["any.direct", "nonexistent"]) is True
        assert user.has_any_permission(["nonexistent"]) is False

    @pytest.mark.django_db
    def test_has_all_permissions_with_direct(self):
        """has_all_permissions() fonctionne avec un mix rôle + direct."""
        user = User.objects.create_user(email="dp11@test.com", password="Test123!@#")
        perm1 = Permission.objects.create(code="all.one", name="One")
        perm2 = Permission.objects.create(code="all.two", name="Two")

        role = Role.objects.create(code="partial", name="Partial")
        role.permissions.add(perm1)
        user.roles.add(role)
        user.direct_permissions.add(perm2)

        assert user.has_all_permissions(["all.one", "all.two"]) is True
        assert user.has_all_permissions(["all.one", "nonexistent"]) is False


class TestDirectPermissionsWithHierarchy:
    """Tests combinant permissions directes et hiérarchie."""

    @pytest.mark.django_db
    def test_direct_parent_grants_children(self):
        """Une permission parente assignée directement donne accès aux enfants."""
        user = User.objects.create_user(email="dh1@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="mgmt", name="Management")
        Permission.objects.create(code="mgmt.users", name="Manage Users", parent=parent)

        user.direct_permissions.add(parent)

        assert user.has_permission("mgmt") is True
        assert user.has_permission("mgmt.users") is True

    @pytest.mark.django_db
    def test_get_all_permissions_direct_hierarchy(self):
        """get_all_permissions() inclut les enfants des permissions directes parentes."""
        user = User.objects.create_user(email="dh2@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="ops", name="Operations")
        Permission.objects.create(code="ops.deploy", name="Deploy", parent=parent)
        Permission.objects.create(code="ops.monitor", name="Monitor", parent=parent)

        user.direct_permissions.add(parent)

        all_perms = user.get_all_permissions()
        assert "ops" in all_perms
        assert "ops.deploy" in all_perms
        assert "ops.monitor" in all_perms
