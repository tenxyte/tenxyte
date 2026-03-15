"""
Tests unitaires pour les permissions hiérarchiques.

Vérifie le champ parent FK sur Permission, get_all_children(), get_ancestors(),
et que has_permission() respecte la hiérarchie.
"""

import pytest
from tenxyte.models import User, Permission, Role


class TestPermissionHierarchyModel:
    """Tests pour le champ parent et les méthodes hiérarchiques."""

    @pytest.mark.django_db
    def test_permission_parent_null_by_default(self):
        """Une permission créée sans parent a parent=None."""
        perm = Permission.objects.create(code="test.perm", name="Test")
        assert perm.parent is None

    @pytest.mark.django_db
    def test_permission_parent_assignment(self):
        """On peut assigner un parent à une permission."""
        parent = Permission.objects.create(code="users", name="Users")
        child = Permission.objects.create(code="users.view", name="View Users", parent=parent)

        child.refresh_from_db()
        assert child.parent == parent
        assert child.parent_id == parent.pk

    @pytest.mark.django_db
    def test_children_relation(self):
        """Le related_name 'children' fonctionne."""
        parent = Permission.objects.create(code="roles", name="Roles")
        child1 = Permission.objects.create(code="roles.view", name="View Roles", parent=parent)
        child2 = Permission.objects.create(code="roles.create", name="Create Roles", parent=parent)

        children = list(parent.children.all())
        assert len(children) == 2
        assert child1 in children
        assert child2 in children

    @pytest.mark.django_db
    def test_get_all_children_include_self(self):
        """get_all_children(include_self=True) inclut la permission elle-même."""
        parent = Permission.objects.create(code="content", name="Content")
        Permission.objects.create(code="content.view", name="View", parent=parent)

        result = parent.get_all_children(include_self=True)
        codes = [p.code for p in result]
        assert "content" in codes
        assert "content.view" in codes

    @pytest.mark.django_db
    def test_get_all_children_exclude_self(self):
        """get_all_children(include_self=False) exclut la permission elle-même."""
        parent = Permission.objects.create(code="content", name="Content")
        Permission.objects.create(code="content.view", name="View", parent=parent)

        result = parent.get_all_children(include_self=False)
        codes = [p.code for p in result]
        assert "content" not in codes
        assert "content.view" in codes

    @pytest.mark.django_db
    def test_get_all_children_recursive(self):
        """get_all_children() descend récursivement dans la hiérarchie."""
        root = Permission.objects.create(code="users", name="Users")
        mid = Permission.objects.create(code="users.roles", name="User Roles", parent=root)
        Permission.objects.create(code="users.roles.assign", name="Assign", parent=mid)

        result = root.get_all_children(include_self=True)
        codes = [p.code for p in result]
        assert "users" in codes
        assert "users.roles" in codes
        assert "users.roles.assign" in codes
        assert len(codes) == 3

    @pytest.mark.django_db
    def test_get_all_children_no_children(self):
        """get_all_children() sur une feuille retourne uniquement elle-même."""
        leaf = Permission.objects.create(code="leaf.perm", name="Leaf")
        result = leaf.get_all_children(include_self=True)
        assert len(result) == 1
        assert result[0].code == "leaf.perm"

    @pytest.mark.django_db
    def test_get_ancestors_no_parent(self):
        """get_ancestors() sur une racine retourne une liste vide."""
        root = Permission.objects.create(code="root", name="Root")
        assert root.get_ancestors() == []

    @pytest.mark.django_db
    def test_get_ancestors_include_self(self):
        """get_ancestors(include_self=True) inclut la permission elle-même."""
        root = Permission.objects.create(code="root", name="Root")
        child = Permission.objects.create(code="root.child", name="Child", parent=root)

        result = child.get_ancestors(include_self=True)
        codes = [p.code for p in result]
        assert "root.child" in codes
        assert "root" in codes

    @pytest.mark.django_db
    def test_get_ancestors_recursive(self):
        """get_ancestors() remonte toute la chaîne d'ancêtres."""
        root = Permission.objects.create(code="a", name="A")
        mid = Permission.objects.create(code="a.b", name="B", parent=root)
        leaf = Permission.objects.create(code="a.b.c", name="C", parent=mid)

        ancestors = leaf.get_ancestors(include_self=False)
        codes = [p.code for p in ancestors]
        assert "a.b" in codes
        assert "a" in codes
        assert "a.b.c" not in codes

    @pytest.mark.django_db
    def test_cascade_delete(self):
        """Supprimer un parent supprime ses enfants (CASCADE)."""
        parent = Permission.objects.create(code="parent", name="Parent")
        Permission.objects.create(code="parent.child", name="Child", parent=parent)

        parent.delete()
        assert Permission.objects.filter(code="parent.child").count() == 0


class TestHasPermissionHierarchy:
    """Tests que has_permission() respecte la hiérarchie."""

    @pytest.mark.django_db
    def test_has_permission_via_role_direct(self):
        """has_permission() retourne True pour une permission directement assignée via un rôle."""
        user = User.objects.create_user(email="h1@test.com", password="Test123!@#")
        perm = Permission.objects.create(code="users.view", name="View Users")
        role = Role.objects.create(code="viewer", name="Viewer")
        role.permissions.add(perm)
        user.roles.add(role)

        assert user.has_permission("users.view") is True

    @pytest.mark.django_db
    def test_has_permission_via_hierarchy(self):
        """Avoir la permission parent donne accès aux enfants (hiérarchie)."""
        user = User.objects.create_user(email="h2@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="users", name="Users")
        Permission.objects.create(code="users.view", name="View Users", parent=parent)

        role = Role.objects.create(code="user_admin", name="User Admin")
        role.permissions.add(parent)  # Seulement le parent
        user.roles.add(role)

        # L'utilisateur a la permission parente
        assert user.has_permission("users") is True
        # Et aussi la permission enfant via la hiérarchie
        assert user.has_permission("users.view") is True

    @pytest.mark.django_db
    def test_has_permission_via_deep_hierarchy(self):
        """La hiérarchie fonctionne sur plusieurs niveaux."""
        user = User.objects.create_user(email="h3@test.com", password="Test123!@#")
        root = Permission.objects.create(code="users", name="Users")
        mid = Permission.objects.create(code="users.roles", name="User Roles", parent=root)
        Permission.objects.create(code="users.roles.assign", name="Assign", parent=mid)

        role = Role.objects.create(code="full_user_admin", name="Full User Admin")
        role.permissions.add(root)  # Seulement la racine
        user.roles.add(role)

        assert user.has_permission("users") is True
        assert user.has_permission("users.roles") is True
        assert user.has_permission("users.roles.assign") is True

    @pytest.mark.django_db
    def test_has_permission_child_does_not_grant_parent(self):
        """Avoir un enfant ne donne PAS accès au parent."""
        user = User.objects.create_user(email="h4@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="users", name="Users")
        child = Permission.objects.create(code="users.view", name="View Users", parent=parent)

        role = Role.objects.create(code="limited", name="Limited")
        role.permissions.add(child)  # Seulement l'enfant
        user.roles.add(role)

        assert user.has_permission("users.view") is True
        assert user.has_permission("users") is False

    @pytest.mark.django_db
    def test_has_permission_nonexistent(self):
        """has_permission() retourne False pour une permission inexistante."""
        user = User.objects.create_user(email="h5@test.com", password="Test123!@#")
        assert user.has_permission("nonexistent.perm") is False

    @pytest.mark.django_db
    def test_get_all_permissions_includes_hierarchy(self):
        """get_all_permissions() inclut les enfants des permissions parentes."""
        user = User.objects.create_user(email="h6@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="content", name="Content")
        Permission.objects.create(code="content.view", name="View", parent=parent)
        Permission.objects.create(code="content.edit", name="Edit", parent=parent)

        role = Role.objects.create(code="content_mgr", name="Content Manager")
        role.permissions.add(parent)
        user.roles.add(role)

        all_perms = user.get_all_permissions()
        assert "content" in all_perms
        assert "content.view" in all_perms
        assert "content.edit" in all_perms

    @pytest.mark.django_db
    def test_has_any_permission_with_hierarchy(self):
        """has_any_permission() fonctionne avec la hiérarchie."""
        user = User.objects.create_user(email="h7@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="sys", name="System")
        Permission.objects.create(code="sys.logs", name="Logs", parent=parent)

        role = Role.objects.create(code="sysadmin", name="SysAdmin")
        role.permissions.add(parent)
        user.roles.add(role)

        assert user.has_any_permission(["sys.logs", "nonexistent"]) is True
        assert user.has_any_permission(["nonexistent"]) is False

    @pytest.mark.django_db
    def test_has_all_permissions_with_hierarchy(self):
        """has_all_permissions() fonctionne avec la hiérarchie."""
        user = User.objects.create_user(email="h8@test.com", password="Test123!@#")
        parent = Permission.objects.create(code="app", name="App")
        Permission.objects.create(code="app.view", name="View", parent=parent)
        Permission.objects.create(code="app.edit", name="Edit", parent=parent)

        role = Role.objects.create(code="app_admin", name="App Admin")
        role.permissions.add(parent)
        user.roles.add(role)

        assert user.has_all_permissions(["app.view", "app.edit"]) is True
        assert user.has_all_permissions(["app.view", "nonexistent"]) is False
