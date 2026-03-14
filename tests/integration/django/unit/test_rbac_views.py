"""
Tests Phase 2 - RbacViews : Permission CRUD, Role CRUD, RolePermissions, UserRoles, UserDirectPermissions

Couvre :
- PermissionListView   GET (lister) / POST (créer)
- PermissionDetailView GET / PUT / DELETE
- RoleListView         GET / POST
- RoleDetailView       GET / PUT / DELETE
- RolePermissionsView  GET / POST (add) / DELETE (remove)
- UserRolesView        GET / POST / DELETE
- UserDirectPermissionsView GET / POST / DELETE
"""

from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import json
NONEXISTENT_ID = 999999999  # ID entier qui n'existera jamais en DB (BigAutoField)
import pytest
from rest_framework.test import APIRequestFactory

from tenxyte.views.rbac_views import (
    PermissionListView,
    PermissionDetailView,
    RoleListView,
    RoleDetailView,
    RolePermissionsView,
    UserRolesView,
    UserDirectPermissionsView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_request(method, path, user, app, data=None):
    """Construit une requête DRF authentifiée par JWT."""
    from tenxyte.services.jwt_service import JWTService
    token = JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]

    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    req = getattr(factory, method)(path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs)
    req.application = app
    return req


def _create_user_with_perms(email, app, *codes):
    """Crée un user actif avec les permissions indiquées."""
    from tenxyte.models import User, Permission
    user = User.objects.create(email=email, is_active=True)
    user.set_password("pass"); user.save()
    for code in codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        user.direct_permissions.add(perm)
    return user


def _app(name):
    """Crée une application de test."""
    from tenxyte.models import Application
    app, _ = Application.create_application(name=name)
    return app


# ===========================================================================
# Tests : PermissionListView
# ===========================================================================

class TestPermissionListView:

    @pytest.mark.django_db
    def test_list_permissions_with_permission(self):
        """GET permissions.view → 200."""
        app = _app("PListApp")
        user = _create_user_with_perms("plist_ok@t.com", app, "permissions.view")
        req = _authed_request("get", f"{api_prefix}/auth/permissions/", user, app)
        response = PermissionListView.as_view()(req)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_permissions_without_permission_returns_403(self):
        """GET sans permissions.view → 403."""
        app = _app("PListNoPerm")
        user = _create_user_with_perms("plist_noperm@t.com", app)
        req = _authed_request("get", f"{api_prefix}/auth/permissions/", user, app)
        response = PermissionListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_create_permission_success(self):
        """POST permissions.create → 201."""
        app = _app("PCreateApp")
        user = _create_user_with_perms("pcreate_ok@t.com", app, "permissions.create")
        req = _authed_request(
            "post", f"{api_prefix}/auth/permissions/", user, app,
            data={"code": "test.new_perm_v2", "name": "New Test Perm V2"}
        )
        response = PermissionListView.as_view()(req)
        assert response.status_code == 201
        assert response.data["code"] == "test.new_perm_v2"

    @pytest.mark.django_db
    def test_create_permission_validation_error(self):
        """POST sans code → 400."""
        app = _app("PCreateBad")
        user = _create_user_with_perms("pcreate_bad@t.com", app, "permissions.create")
        req = _authed_request(
            "post", f"{api_prefix}/auth/permissions/", user, app,
            data={"name": "Missing Code"}
        )
        response = PermissionListView.as_view()(req)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_permission_without_permission_returns_403(self):
        """POST sans permissions.create → 403."""
        app = _app("PCreateNoPerm")
        user = _create_user_with_perms("pcreate_noperm@t.com", app)
        req = _authed_request(
            "post", f"{api_prefix}/auth/permissions/", user, app,
            data={"code": "x.y", "name": "XY"}
        )
        response = PermissionListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_permissions_unpaginated(self):
        """GET unpaginated permissions."""
        from unittest.mock import patch
        app = _app("PListUnpagApp")
        user = _create_user_with_perms("plist_unpag@t.com", app, "permissions.view")
        req = _authed_request("get", f"{api_prefix}/auth/permissions/", user, app)
        with patch('tenxyte.views.rbac_views.TenxytePagination.paginate_queryset', return_value=None):
            response = PermissionListView.as_view()(req)
        assert response.status_code == 200
        assert isinstance(response.data, list)


# ===========================================================================
# Tests : PermissionDetailView
# ===========================================================================

class TestPermissionDetailView:

    @pytest.mark.django_db
    def test_get_permission_detail(self):
        """GET permissions.view → 200."""
        from tenxyte.models import Permission
        app = _app("PDetailApp")
        user = _create_user_with_perms("pdetail_ok@t.com", app, "permissions.view")
        perm = Permission.objects.create(code="detail.test.perm", name="Detail Test Perm")

        req = _authed_request("get", f"{api_prefix}/auth/permissions/{perm.id}/", user, app)
        response = PermissionDetailView.as_view()(req, permission_id=str(perm.id))
        assert response.status_code == 200
        assert response.data["code"] == "detail.test.perm"

    @pytest.mark.django_db
    def test_get_permission_not_found(self):
        """GET sur ID inexistant → 404."""
        app = _app("PDetailApp404")
        user = _create_user_with_perms("pdetail_404@t.com", app, "permissions.view")
        req = _authed_request("get", f"{api_prefix}/auth/permissions/bad/", user, app)
        response = PermissionDetailView.as_view()(req, permission_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_permission_success(self):
        """PUT permissions.update → 200."""
        from tenxyte.models import Permission
        app = _app("PUpdateApp")
        user = _create_user_with_perms("pupdate_ok@t.com", app, "permissions.update")
        perm = Permission.objects.create(code="update.this.perm", name="Original Name")

        req = _authed_request(
            "put", f"{api_prefix}/auth/permissions/{perm.id}/", user, app,
            data={"name": "Updated Name"}
        )
        response = PermissionDetailView.as_view()(req, permission_id=str(perm.id))
        assert response.status_code == 200
        assert response.data["name"] == "Updated Name"

    @pytest.mark.django_db
    def test_update_permission_not_found(self):
        """PUT sur ID inexistant → 404."""
        app = _app("PUpdateApp404")
        user = _create_user_with_perms("pupdate_404@t.com", app, "permissions.update")
        req = _authed_request(
            "put", f"{api_prefix}/auth/permissions/bad/", user, app,
            data={"name": "X"}
        )
        response = PermissionDetailView.as_view()(req, permission_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_delete_permission_success(self):
        """DELETE permissions.delete → 200."""
        from tenxyte.models import Permission
        app = _app("PDeleteApp")
        user = _create_user_with_perms("pdelete_ok@t.com", app, "permissions.delete")
        perm = Permission.objects.create(code="delete.me.perm", name="Delete Me")

        req = _authed_request("delete", f"{api_prefix}/auth/permissions/{perm.id}/", user, app)
        response = PermissionDetailView.as_view()(req, permission_id=str(perm.id))
        assert response.status_code == 200
        assert not Permission.objects.filter(id=perm.id).exists()

    @pytest.mark.django_db
    def test_delete_permission_not_found(self):
        """DELETE sur ID inexistant → 404."""
        app = _app("PDeleteApp404")
        user = _create_user_with_perms("pdelete_404@t.com", app, "permissions.delete")
        req = _authed_request("delete", f"{api_prefix}/auth/permissions/bad/", user, app)
        response = PermissionDetailView.as_view()(req, permission_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_delete_without_permission_returns_403(self):
        """DELETE sans permissions.delete → 403."""
        from tenxyte.models import Permission
        app = _app("PDeleteNoPerm")
        user = _create_user_with_perms("pdelete_noperm@t.com", app)
        perm = Permission.objects.create(code="delete.me.noperm", name="Del NoPerm")

        req = _authed_request("delete", f"{api_prefix}/auth/permissions/{perm.id}/", user, app)
        response = PermissionDetailView.as_view()(req, permission_id=str(perm.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_update_permission_validation_error(self):
        """PUT avec erreurs de validation → 400."""
        from tenxyte.models import Permission
        app = _app("PUpdateVal")
        user = _create_user_with_perms("pupdate_val@t.com", app, "permissions.update")
        perm = Permission.objects.create(code="update.val", name="Original Name")

        req = _authed_request(
            "put", f"{api_prefix}/auth/permissions/{perm.id}/", user, app,
            data={"name": ""}
        )
        response = PermissionDetailView.as_view()(req, permission_id=str(perm.id))
        assert response.status_code == 400


# ===========================================================================
# Tests : RoleListView
# ===========================================================================

class TestRoleListView:

    @pytest.mark.django_db
    def test_list_roles_with_permission(self):
        """GET roles.view → 200."""
        app = _app("RListApp")
        user = _create_user_with_perms("rlist_ok@t.com", app, "roles.view")
        req = _authed_request("get", f"{api_prefix}/auth/roles/", user, app)
        response = RoleListView.as_view()(req)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_roles_without_permission_returns_403(self):
        """GET sans roles.view → 403."""
        app = _app("RListNoPerm")
        user = _create_user_with_perms("rlist_noperm@t.com", app)
        req = _authed_request("get", f"{api_prefix}/auth/roles/", user, app)
        response = RoleListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_create_role_success(self):
        """POST roles.create → 201."""
        app = _app("RCreateApp")
        user = _create_user_with_perms("rcreate_ok@t.com", app, "roles.create")
        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/", user, app,
            data={"code": "new_test_role_v2", "name": "New Test Role V2"}
        )
        response = RoleListView.as_view()(req)
        assert response.status_code == 201
        assert response.data["code"] == "new_test_role_v2"

    @pytest.mark.django_db
    def test_create_role_validation_error(self):
        """POST sans code → 400."""
        app = _app("RCreateBad")
        user = _create_user_with_perms("rcreate_bad@t.com", app, "roles.create")
        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/", user, app,
            data={"name": "Missing Code"}
        )
        response = RoleListView.as_view()(req)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_role_without_permission_returns_403(self):
        """POST sans roles.create → 403."""
        app = _app("RCreateNoPerm")
        user = _create_user_with_perms("rcreate_noperm@t.com", app)
        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/", user, app,
            data={"code": "x", "name": "X"}
        )
        response = RoleListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_roles_unpaginated(self):
        """GET unpaginated roles."""
        from unittest.mock import patch
        app = _app("RListUnpagApp")
        user = _create_user_with_perms("rlist_unpag@t.com", app, "roles.view")
        req = _authed_request("get", f"{api_prefix}/auth/roles/", user, app)
        with patch('tenxyte.views.rbac_views.TenxytePagination.paginate_queryset', return_value=None):
            response = RoleListView.as_view()(req)
        assert response.status_code == 200
        assert isinstance(response.data, list)


# ===========================================================================
# Tests : RoleDetailView
# ===========================================================================

class TestRoleDetailView:

    @pytest.mark.django_db
    def test_get_role_detail(self):
        """GET roles.view → 200."""
        from tenxyte.models import Role
        app = _app("RDetailApp")
        user = _create_user_with_perms("rdetail_ok@t.com", app, "roles.view")
        role = Role.objects.create(code="detail_role_v2", name="Detail Role V2")

        req = _authed_request("get", f"{api_prefix}/auth/roles/{role.id}/", user, app)
        response = RoleDetailView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert response.data["code"] == "detail_role_v2"

    @pytest.mark.django_db
    def test_get_role_not_found(self):
        """GET sur ID inexistant → 404."""
        app = _app("RDetailApp404")
        user = _create_user_with_perms("rdetail_404@t.com", app, "roles.view")
        req = _authed_request("get", f"{api_prefix}/auth/roles/bad/", user, app)
        response = RoleDetailView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_role_success(self):
        """PUT roles.update → 200."""
        from tenxyte.models import Role
        app = _app("RUpdateApp")
        user = _create_user_with_perms("rupdate_ok@t.com", app, "roles.update")
        role = Role.objects.create(code="update_role_v2", name="Update Role V2")

        req = _authed_request(
            "put", f"{api_prefix}/auth/roles/{role.id}/", user, app,
            data={"name": "Updated Role Name"}
        )
        response = RoleDetailView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert response.data["name"] == "Updated Role Name"

    @pytest.mark.django_db
    def test_delete_role_success(self):
        """DELETE roles.delete → 200 + rôle supprimé."""
        from tenxyte.models import Role
        app = _app("RDeleteApp")
        user = _create_user_with_perms("rdelete_ok@t.com", app, "roles.delete")
        role = Role.objects.create(code="delete_this_role_v2", name="Delete This V2")

        req = _authed_request("delete", f"{api_prefix}/auth/roles/{role.id}/", user, app)
        response = RoleDetailView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert not Role.objects.filter(id=role.id).exists()

    @pytest.mark.django_db
    def test_delete_role_not_found(self):
        """DELETE sur ID inexistant → 404."""
        app = _app("RDeleteApp404")
        user = _create_user_with_perms("rdelete_404@t.com", app, "roles.delete")
        req = _authed_request("delete", f"{api_prefix}/auth/roles/bad/", user, app)
        response = RoleDetailView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_role_not_found(self):
        """PUT sur ID inexistant → 404."""
        app = _app("RUpdateApp404")
        user = _create_user_with_perms("rupdate_404@t.com", app, "roles.update")
        req = _authed_request(
            "put", f"{api_prefix}/auth/roles/bad/", user, app,
            data={"name": "X"}
        )
        response = RoleDetailView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_role_validation_error(self):
        """PUT avec format invalide → 400."""
        from tenxyte.models import Role
        app = _app("RUpdateVal")
        user = _create_user_with_perms("rupdate_val@t.com", app, "roles.update")
        role = Role.objects.create(code="update_val", name="Original Name")

        req = _authed_request(
            "put", f"{api_prefix}/auth/roles/{role.id}/", user, app,
            data={"name": ""}
        )
        response = RoleDetailView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 400


# ===========================================================================
# Tests : RolePermissionsView
# ===========================================================================

class TestRolePermissionsView:

    @pytest.mark.django_db
    def test_get_role_permissions(self):
        """GET roles.manage_permissions → 200 avec la liste des permissions du rôle."""
        from tenxyte.models import Role, Permission
        app = _app("RPGetApp")
        user = _create_user_with_perms("rpget_ok@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_get_role_v2", name="RP Get Role V2")
        perm = Permission.objects.create(code="rp.get.perm.v2", name="RP Get Perm V2")
        role.permissions.add(perm)

        req = _authed_request("get", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app)
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert "permissions" in response.data
        perms_codes = [p["code"] for p in response.data["permissions"]]
        assert "rp.get.perm.v2" in perms_codes

    @pytest.mark.django_db
    def test_get_role_permissions_not_found(self):
        """GET sur rôle inexistant → 404."""
        app = _app("RPGetApp404")
        user = _create_user_with_perms("rpget_404@t.com", app, "roles.manage_permissions")
        req = _authed_request("get", f"{api_prefix}/auth/roles/bad/permissions/", user, app)
        response = RolePermissionsView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_add_permissions_to_role(self):
        """POST ajouter une permission à un rôle → 200."""
        from tenxyte.models import Role, Permission
        app = _app("RPAddApp")
        user = _create_user_with_perms("rpadd_ok@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_add_role_v2", name="RP Add Role V2")
        Permission.objects.create(code="rp.add.perm.v2", name="RP Add Perm V2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["rp.add.perm.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert "rp.add.perm.v2" in response.data["added"]

    @pytest.mark.django_db
    def test_add_nonexistent_permission_returns_400(self):
        """POST avec permission inexistante → 400 PERMISSIONS_NOT_FOUND."""
        from tenxyte.models import Role
        app = _app("RPAddBad")
        user = _create_user_with_perms("rpadd_bad@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_add_bad_role_v2", name="RP Add Bad V2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["nonexistent.perm.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 400
        assert response.data["code"] == "PERMISSIONS_NOT_FOUND"

    @pytest.mark.django_db
    def test_remove_permissions_from_role(self):
        """DELETE retirer une permission d'un rôle → 200."""
        from tenxyte.models import Role, Permission
        app = _app("RPRemoveApp")
        user = _create_user_with_perms("rpremove_ok@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_remove_role_v2", name="RP Remove Role V2")
        perm = Permission.objects.create(code="rp.remove.perm.v2", name="RP Remove Perm V2")
        role.permissions.add(perm)

        req = _authed_request(
            "delete", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["rp.remove.perm.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert "rp.remove.perm.v2" in response.data["removed"]

    @pytest.mark.django_db
    def test_remove_nonexistent_permission_returns_400(self):
        """DELETE avec permission inexistante → 400."""
        from tenxyte.models import Role
        app = _app("RPRemoveBad")
        user = _create_user_with_perms("rpremove_bad@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_rm_bad_role_v2", name="RP Rm Bad V2")

        req = _authed_request(
            "delete", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["does.not.exist.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_add_already_assigned_permission_is_idempotent(self):
        """POST avec permission déjà assignée → 200 avec already_assigned."""
        from tenxyte.models import Role, Permission
        app = _app("RPIdempApp")
        user = _create_user_with_perms("rpidemp_ok@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_idemp_role_v2", name="RP Idemp Role V2")
        perm = Permission.objects.create(code="rp.idemp.perm.v2", name="RP Idemp Perm V2")
        role.permissions.add(perm)  # déjà assignée

        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["rp.idemp.perm.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert "already_assigned" in response.data

    @pytest.mark.django_db
    def test_add_permissions_role_not_found(self):
        app = _app("RPAddApp404")
        user = _create_user_with_perms("rpadd_404@t.com", app, "roles.manage_permissions")
        req = _authed_request("post", f"{api_prefix}/auth/roles/bad/permissions/", user, app, data={})
        response = RolePermissionsView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_add_permissions_validation_error(self):
        from tenxyte.models import Role
        app = _app("RPAddVal")
        user = _create_user_with_perms("rpadd_val@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_add_val", name="RP Add Val")

        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ""}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_remove_permissions_role_not_found(self):
        app = _app("RPRmApp404")
        user = _create_user_with_perms("rprm_404@t.com", app, "roles.manage_permissions")
        req = _authed_request("delete", f"{api_prefix}/auth/roles/bad/permissions/", user, app, data={})
        response = RolePermissionsView.as_view()(req, role_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_remove_permissions_validation_error(self):
        from tenxyte.models import Role
        app = _app("RPRmVal")
        user = _create_user_with_perms("rprm_val@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_rm_val", name="RP Rm Val")

        req = _authed_request(
            "delete", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ""}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_remove_permissions_not_removed(self):
        from tenxyte.models import Role, Permission
        app = _app("RPRmNot")
        user = _create_user_with_perms("rprm_not@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_rm_not", name="RP Rm Not")
        Permission.objects.create(code="not_assigned.perm.v2", name="Not Assigned")

        req = _authed_request(
            "delete", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["not_assigned.perm.v2"]}
        )
        response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert "not_assigned.perm.v2" in response.data["not_removed"]

    @pytest.mark.django_db
    def test_safe_add_permissions_type_error(self):
        from unittest.mock import patch, MagicMock
        from tenxyte.models import Role, Permission
        app = _app("RPSafeAdd")
        user = _create_user_with_perms("rpsafeadd@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_safe_add", name="RP Safe Add")
        Permission.objects.create(code="safe.add.perm1", name="Safe Add Perm 1")
        Permission.objects.create(code="safe.add.perm2", name="Safe Add Perm 2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["safe.add.perm1", "safe.add.perm2"]}
        )
        
        ManagerClass = type(role.permissions)
        def fake_add(self, *args, **kwargs):
            raise TypeError("Direct addition of multiple items not supported")
            
        with patch.object(ManagerClass, 'add', autospec=True, side_effect=fake_add):
            response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_safe_remove_permissions_type_error(self):
        from unittest.mock import patch
        from tenxyte.models import Role, Permission
        app = _app("RPSafeRm")
        user = _create_user_with_perms("rpsaferm@t.com", app, "roles.manage_permissions")
        role = Role.objects.create(code="rp_safe_rm", name="RP Safe Rm")
        perm = Permission.objects.create(code="safe.rm.perm", name="Safe Rm Perm")
        role.permissions.add(perm)

        req = _authed_request(
            "delete", f"{api_prefix}/auth/roles/{role.id}/permissions/", user, app,
            data={"permission_codes": ["safe.rm.perm"]}
        )
        
        ManagerClass = type(role.permissions)
        def fake_remove(self, *args, **kwargs):
            raise TypeError("Direct removal of multiple items not supported")
            
        with patch.object(ManagerClass, 'remove', autospec=True, side_effect=fake_remove):
            response = RolePermissionsView.as_view()(req, role_id=str(role.id))
        assert response.status_code == 200
        assert not role.permissions.filter(code="safe.rm.perm").exists()


# ===========================================================================
# Tests : UserRolesView
# ===========================================================================

class TestUserRolesView:

    @pytest.mark.django_db
    def test_get_user_roles(self):
        """GET users.roles.view → 200 avec liste des rôles."""
        from tenxyte.models import User, Role
        app = _app("URGetApp")
        admin = _create_user_with_perms("urget_admin@t.com", app, "users.roles.view")
        target = User.objects.create(email="urget_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        role = Role.objects.create(code="ur_get_role_v2", name="UR Get Role V2")
        target.roles.add(role)

        req = _authed_request("get", f"{api_prefix}/auth/users/{target.id}/roles/", admin, app)
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        role_codes = [r["code"] for r in response.data["roles"]]
        assert "ur_get_role_v2" in role_codes

    @pytest.mark.django_db
    def test_get_user_roles_user_not_found(self):
        """GET sur user_id inexistant → 404."""
        app = _app("URGetApp404")
        admin = _create_user_with_perms("urget_404@t.com", app, "users.roles.view")

        req = _authed_request("get", f"{api_prefix}/auth/users/bad/roles/", admin, app)
        response = UserRolesView.as_view()(req, user_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_assign_role_to_user(self):
        """POST users.roles.assign → 200 role assigné."""
        from tenxyte.models import User, Role
        app = _app("URAssignApp")
        admin = _create_user_with_perms("urassign_admin@t.com", app, "users.roles.assign")
        target = User.objects.create(email="urassign_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        Role.objects.create(code="ur_assign_role_v2", name="UR Assign Role V2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/roles/", admin, app,
            data={"role_code": "ur_assign_role_v2"}
        )
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        # get_all_roles() retourne une liste de codes (strings)
        assert "ur_assign_role_v2" in response.data["roles"]

    @pytest.mark.django_db
    def test_assign_nonexistent_role_returns_404(self):
        """POST avec role_code inexistant → 404."""
        from tenxyte.models import User
        app = _app("URAssignBad")
        admin = _create_user_with_perms("urassign_bad@t.com", app, "users.roles.assign")
        target = User.objects.create(email="urassign_bad_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/roles/", admin, app,
            data={"role_code": "does_not_exist_v2"}
        )
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_remove_role_from_user(self):
        """DELETE users.roles.remove → 200 rôle retiré."""
        from tenxyte.models import User, Role
        app = _app("URRemoveApp")
        admin = _create_user_with_perms("urremove_admin@t.com", app, "users.roles.remove")
        target = User.objects.create(email="urremove_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        role = Role.objects.create(code="ur_remove_role_v2", name="UR Remove Role V2")
        target.roles.add(role)

        req = _authed_request(
            "delete",
            f"{api_prefix}/auth/users/{target.id}/roles/?role_code=ur_remove_role_v2",
            admin, app
        )
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        # get_all_roles() retourne une liste de codes (strings)
        assert "ur_remove_role_v2" not in response.data["roles"]

    @pytest.mark.django_db
    def test_remove_role_missing_param_returns_400(self):
        """DELETE sans role_code → 400 MISSING_PARAM."""
        from tenxyte.models import User
        app = _app("URRemoveBad")
        admin = _create_user_with_perms("urremove_bad@t.com", app, "users.roles.remove")
        target = User.objects.create(email="urremove_bad_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        # Pas de query param role_code
        req = _authed_request("delete", f"{api_prefix}/auth/users/{target.id}/roles/", admin, app)
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 400
        assert response.data["code"] == "MISSING_PARAM"

    @pytest.mark.django_db
    def test_get_user_roles_without_permission_returns_403(self):
        """GET sans users.roles.view → 403."""
        from tenxyte.models import User
        app = _app("URGetNoPerm")
        admin = _create_user_with_perms("urget_noperm@t.com", app)  # pas la permission
        target = User.objects.create(email="urget_noperm_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request("get", f"{api_prefix}/auth/users/{target.id}/roles/", admin, app)
        response = UserRolesView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 403


# ===========================================================================
# Tests : UserDirectPermissionsView
# ===========================================================================

class TestUserDirectPermissionsView:

    @pytest.mark.django_db
    def test_get_user_direct_permissions(self):
        """GET users.permissions.view → 200 avec direct_permissions."""
        from tenxyte.models import User, Permission
        app = _app("UDPGetApp")
        admin = _create_user_with_perms("udpget_admin@t.com", app, "users.permissions.view")
        target = User.objects.create(email="udpget_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        perm = Permission.objects.create(code="udp.test.perm.v2", name="UDP Test Perm V2")
        target.direct_permissions.add(perm)

        req = _authed_request("get", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app)
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        dp_codes = [p["code"] for p in response.data["direct_permissions"]]
        assert "udp.test.perm.v2" in dp_codes

    @pytest.mark.django_db
    def test_get_user_direct_permissions_not_found(self):
        """GET sur user inexistant → 404."""
        app = _app("UDPGetApp404")
        admin = _create_user_with_perms("udpget_404@t.com", app, "users.permissions.view")
        req = _authed_request("get", f"{api_prefix}/auth/users/bad/permissions/", admin, app)
        response = UserDirectPermissionsView.as_view()(req, user_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_add_direct_permission_to_user(self):
        """POST users.permissions.assign → 200 permission ajoutée."""
        from tenxyte.models import User, Permission
        app = _app("UDPAddApp")
        admin = _create_user_with_perms("udpadd_admin@t.com", app, "users.permissions.assign")
        target = User.objects.create(email="udpadd_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        Permission.objects.create(code="udp.add.perm.v2", name="UDP Add Perm V2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.add.perm.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        assert "udp.add.perm.v2" in response.data["added"]

    @pytest.mark.django_db
    def test_add_nonexistent_permission_to_user_returns_400(self):
        """POST avec permission inexistante → 400."""
        from tenxyte.models import User
        app = _app("UDPAddBad")
        admin = _create_user_with_perms("udpadd_bad@t.com", app, "users.permissions.assign")
        target = User.objects.create(email="udpadd_bad_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.nonexistent.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_remove_direct_permission_from_user(self):
        """DELETE users.permissions.remove → 200 permission retirée."""
        from tenxyte.models import User, Permission
        app = _app("UDPRemoveApp")
        admin = _create_user_with_perms("udpremove_admin@t.com", app, "users.permissions.remove")
        target = User.objects.create(email="udpremove_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        perm = Permission.objects.create(code="udp.remove.perm.v2", name="UDP Remove Perm V2")
        target.direct_permissions.add(perm)

        req = _authed_request(
            "delete", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.remove.perm.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        assert "udp.remove.perm.v2" in response.data["removed"]

    @pytest.mark.django_db
    def test_remove_nonexistent_permission_from_user_returns_400(self):
        """DELETE avec permission inexistante → 400."""
        from tenxyte.models import User
        app = _app("UDPRemoveBad")
        admin = _create_user_with_perms("udpremove_bad@t.com", app, "users.permissions.remove")
        target = User.objects.create(email="udpremove_bad_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request(
            "delete", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.nonexistent.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_add_already_assigned_is_idempotent(self):
        """POST avec permission déjà assignée → 200 avec already_assigned."""
        from tenxyte.models import User, Permission
        app = _app("UDPIdempApp")
        admin = _create_user_with_perms("udpidemp_admin@t.com", app, "users.permissions.assign")
        target = User.objects.create(email="udpidemp_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        perm = Permission.objects.create(code="udp.idemp.perm.v2", name="UDP Idemp Perm V2")
        target.direct_permissions.add(perm)  # déjà assignée

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.idemp.perm.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        assert "already_assigned" in response.data

    @pytest.mark.django_db
    def test_get_direct_permissions_without_permission_returns_403(self):
        """GET sans users.permissions.view → 403."""
        from tenxyte.models import User
        app = _app("UDPGetNoPerm")
        admin = _create_user_with_perms("udpget_noperm@t.com", app)  # pas la permission
        target = User.objects.create(email="udpget_noperm_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request("get", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app)
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_add_direct_permissions_user_not_found(self):
        app = _app("UDPAddApp404")
        admin = _create_user_with_perms("udpadd_404@t.com", app, "users.permissions.assign")
        req = _authed_request("post", f"{api_prefix}/auth/users/bad/permissions/", admin, app, data={})
        response = UserDirectPermissionsView.as_view()(req, user_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_add_direct_permissions_validation_error(self):
        from tenxyte.models import User
        app = _app("UDPAddVal")
        admin = _create_user_with_perms("udpadd_val_ad@t.com", app, "users.permissions.assign")
        target = User.objects.create(email="udpadd_val_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ""}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_remove_direct_permissions_user_not_found(self):
        app = _app("UDPRmApp404")
        admin = _create_user_with_perms("udprm_404@t.com", app, "users.permissions.remove")
        req = _authed_request("delete", f"{api_prefix}/auth/users/bad/permissions/", admin, app, data={})
        response = UserDirectPermissionsView.as_view()(req, user_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_remove_direct_permissions_validation_error(self):
        from tenxyte.models import User
        app = _app("UDPRmVal")
        admin = _create_user_with_perms("udprm_val_ad@t.com", app, "users.permissions.remove")
        target = User.objects.create(email="udprm_val_target@t.com", is_active=True)
        target.set_password("pass"); target.save()

        req = _authed_request(
            "delete", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ""}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_remove_direct_permissions_not_removed(self):
        from tenxyte.models import User, Permission
        app = _app("UDPRmNot")
        admin = _create_user_with_perms("udprm_not_ad@t.com", app, "users.permissions.remove")
        target = User.objects.create(email="udprm_not_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        Permission.objects.create(code="udp.not_assigned.perm.v2", name="Not Assigned UDP")

        req = _authed_request(
            "delete", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.not_assigned.perm.v2"]}
        )
        response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        assert "udp.not_assigned.perm.v2" in response.data["not_removed"]

    @pytest.mark.django_db
    def test_safe_add_direct_permissions_type_error(self):
        from unittest.mock import patch, MagicMock
        from tenxyte.models import User, Permission
        app = _app("UDPSafeAdd")
        admin = _create_user_with_perms("udpsafeadd_ad@t.com", app, "users.permissions.assign")
        target = User.objects.create(email="udpsafeadd_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        Permission.objects.create(code="udp.safe.add.perm1", name="UDP Safe Add Perm 1")
        Permission.objects.create(code="udp.safe.add.perm2", name="UDP Safe Add Perm 2")

        req = _authed_request(
            "post", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.safe.add.perm1", "udp.safe.add.perm2"]}
        )
        
        ManagerClass = type(target.direct_permissions)
        def fake_add(self, *args, **kwargs):
            raise TypeError("Direct addition of multiple items not supported")
            
        with patch.object(ManagerClass, 'add', autospec=True, side_effect=fake_add):
            response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_safe_remove_direct_permissions_type_error(self):
        from unittest.mock import patch
        from tenxyte.models import User, Permission
        app = _app("UDPSafeRm")
        admin = _create_user_with_perms("udpsaferm_ad@t.com", app, "users.permissions.remove")
        target = User.objects.create(email="udpsaferm_target@t.com", is_active=True)
        target.set_password("pass"); target.save()
        perm = Permission.objects.create(code="udp.safe.rm.perm", name="UDP Safe Rm Perm")
        target.direct_permissions.add(perm)

        req = _authed_request(
            "delete", f"{api_prefix}/auth/users/{target.id}/permissions/", admin, app,
            data={"permission_codes": ["udp.safe.rm.perm"]}
        )
        
        ManagerClass = type(target.direct_permissions)
        def fake_remove(self, *args, **kwargs):
            raise TypeError("Direct removal of multiple items not supported")
            
        with patch.object(ManagerClass, 'remove', autospec=True, side_effect=fake_remove):
            response = UserDirectPermissionsView.as_view()(req, user_id=str(target.id))
        assert response.status_code == 200
        assert not target.direct_permissions.filter(code="udp.safe.rm.perm").exists()
