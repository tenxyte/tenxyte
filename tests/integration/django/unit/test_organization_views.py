"""
Tests organization_views.py - CRUD, members, invitations, roles.

Coverage cible : views/organization_views.py (0% → ~80%)

Pattern : requêtes DRF directes sur les fonctions de vue,
avec JWT forgé + request.organization injecté manuellement.
"""

import pytest
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.models.organization import (
    OrganizationMembership,
)
from tenxyte.services.organization_service import OrganizationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="OrgViewApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, app=None):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _jwt_token(user, app):
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


def _authed_request(method, path, user, app, data=None, org=None):
    """Build an authenticated DRF request with optional org context."""
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    req = getattr(factory, method)(
        path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs
    )
    req.application = app
    req.user = user
    req.organization = org
    if org:
        req.org_membership = OrganizationMembership.objects.filter(
            organization=org, user=user
        ).first()
    return req


def _setup_org(owner, app):
    """Create org with system roles, return (org, service)."""
    service = OrganizationService()
    service.initialize_system_roles()
    _, org, _ = service.create_organization(name="Test Org", created_by=owner)
    return org, service


def _owner_of(org):
    return OrganizationMembership.objects.get(
        organization=org, role__code="owner"
    ).user


# ---------------------------------------------------------------------------
# create_organization
# ---------------------------------------------------------------------------

class TestCreateOrganizationView:

    @pytest.mark.django_db
    def test_create_success_returns_201(self):
        from tenxyte.views.organization_views import create_organization
        app = _app("CreateOrgApp")
        user = _user("create_ok@test.com", app)
        OrganizationService().initialize_system_roles()

        req = _authed_request("post", "/organizations/", user, app, data={"name": "My Org"})
        response = create_organization(req)

        assert response.status_code == 201
        assert response.data["name"] == "My Org"

    @pytest.mark.django_db
    def test_create_invalid_data_returns_400(self):
        from tenxyte.views.organization_views import create_organization
        app = _app("CreateOrgBadApp")
        user = _user("create_bad@test.com", app)
        OrganizationService().initialize_system_roles()

        req = _authed_request("post", "/organizations/", user, app, data={})
        response = create_organization(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_with_nonexistent_parent_returns_400(self):
        from tenxyte.views.organization_views import create_organization
        app = _app("CreateOrgParentApp")
        user = _user("create_parent@test.com", app)
        OrganizationService().initialize_system_roles()

        req = _authed_request(
            "post", "/organizations/", user, app,
            data={"name": "Child", "parent_id": 99999}
        )
        response = create_organization(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_without_auth_returns_401(self):
        from tenxyte.views.organization_views import create_organization
        factory = APIRequestFactory()
        req = factory.post("/organizations/", data={"name": "Org"}, format="json")
        req.application = _app("NoAuthApp")
        response = create_organization(req)

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# list_organizations
# ---------------------------------------------------------------------------

class TestListOrganizationsView:

    @pytest.mark.django_db
    def test_list_returns_user_orgs(self):
        from tenxyte.views.organization_views import list_organizations
        app = _app("ListOrgApp")
        user = _user("list_org@test.com", app)
        org, service = _setup_org(user, app)

        req = _authed_request("get", "/organizations/list/", user, app)
        response = list_organizations(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_without_auth_returns_401(self):
        from tenxyte.views.organization_views import list_organizations
        factory = APIRequestFactory()
        req = factory.get("/organizations/list/")
        req.application = _app("ListNoAuthApp")
        response = list_organizations(req)

        assert response.status_code == 401

    @pytest.mark.django_db
    def test_list_unpaginated(self):
        from tenxyte.views.organization_views import list_organizations
        app = _app("ListOrgAppUP")
        user = _user("list_org_up@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("get", "/organizations/list/", user, app)
        
        from unittest import mock
        with mock.patch('tenxyte.pagination.TenxytePagination.paginate_queryset', return_value=None):
            response = list_organizations(req)
        
        assert response.status_code == 200
        assert isinstance(response.data, list)


# ---------------------------------------------------------------------------
# get_organization
# ---------------------------------------------------------------------------

class TestGetOrganizationView:

    @pytest.mark.django_db
    def test_get_returns_200_for_member(self):
        from tenxyte.views.organization_views import get_organization
        app = _app("GetOrgApp")
        user = _user("get_org@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("get", "/organizations/detail/", user, app, org=org)
        response = get_organization(req)

        assert response.status_code == 200
        assert response.data["name"] == "Test Org"

    @pytest.mark.django_db
    def test_get_without_org_context_returns_400(self):
        from tenxyte.views.organization_views import get_organization
        app = _app("GetOrgNoCtxApp")
        user = _user("get_noctx@test.com", app)

        req = _authed_request("get", "/organizations/detail/", user, app, org=None)
        response = get_organization(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_get_as_non_member_returns_403(self):
        from tenxyte.views.organization_views import get_organization
        app = _app("GetOrgNonMemberApp")
        owner = _user("get_owner@test.com", app)
        outsider = _user("get_outsider@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request("get", "/organizations/detail/", outsider, app, org=org)
        response = get_organization(req)

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# update_organization
# ---------------------------------------------------------------------------

class TestUpdateOrganizationView:

    @pytest.mark.django_db
    def test_update_by_owner_returns_200(self):
        from tenxyte.views.organization_views import update_organization
        app = _app("UpdateOrgApp")
        user = _user("update_org@test.com", app)
        org, service = _setup_org(user, app)

        # Give user admin role via membership (owner already has it)
        req = _authed_request(
            "patch", "/organizations/update/", user, app,
            data={"name": "Updated Name"}, org=org
        )
        response = update_organization(req)

        assert response.status_code == 200
        assert response.data["name"] == "Updated Name"

    @pytest.mark.django_db
    def test_update_invalid_data_returns_400(self):
        from tenxyte.views.organization_views import update_organization
        app = _app("UpdateOrgBadApp")
        user = _user("update_bad@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request(
            "patch", "/organizations/update/", user, app,
            data={"max_members": -1}, org=org
        )
        response = update_organization(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_update_without_org_context_returns_400(self):
        from tenxyte.views.organization_views import update_organization
        app = _app("UpdateOrgNoCtxApp")
        user = _user("update_noctx@test.com", app)

        req = _authed_request("patch", "/organizations/update/", user, app, data={"name": "X"}, org=None)
        response = update_organization(req)

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# delete_organization
# ---------------------------------------------------------------------------

class TestDeleteOrganizationView:

    @pytest.mark.django_db
    def test_delete_by_owner_returns_200(self):
        from tenxyte.views.organization_views import delete_organization
        app = _app("DeleteOrgApp")
        user = _user("delete_org@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("delete", "/organizations/delete/", user, app, org=org)
        response = delete_organization(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_by_non_owner_returns_403(self):
        from tenxyte.views.organization_views import delete_organization
        app = _app("DeleteOrgNonOwnerApp")
        owner = _user("del_owner@test.com", app)
        member = _user("del_member@test.com", app)
        org, service = _setup_org(owner, app)
        service.add_member(org, member, "admin", owner)

        req = _authed_request("delete", "/organizations/delete/", member, app, org=org)
        response = delete_organization(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_delete_fails_with_children_returns_400(self):
        from tenxyte.views.organization_views import delete_organization
        app = _app("DeleteOrgChildApp")
        user = _user("del_parent@test.com", app)
        org, service = _setup_org(user, app)
        
        # Add a child org
        service.create_organization(name="Child", created_by=user, parent_id=org.id)

        req = _authed_request("delete", "/organizations/delete/", user, app, org=org)
        response = delete_organization(req)

        assert response.status_code == 400
        assert "child" in response.data["error"].lower()


# ---------------------------------------------------------------------------
# get_organization_tree
# ---------------------------------------------------------------------------

class TestGetOrganizationTreeView:

    @pytest.mark.django_db
    def test_tree_returns_200_for_member(self):
        from tenxyte.views.organization_views import get_organization_tree
        app = _app("TreeApp")
        user = _user("tree@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("get", "/organizations/tree/", user, app, org=org)
        response = get_organization_tree(req)

        assert response.status_code == 200
        assert "name" in response.data
        assert "children" in response.data


# ---------------------------------------------------------------------------
# list_members
# ---------------------------------------------------------------------------

class TestListMembersView:

    @pytest.mark.django_db
    def test_list_members_returns_200(self):
        from tenxyte.views.organization_views import list_members
        app = _app("ListMembersApp")
        user = _user("list_members@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("get", "/organizations/members/", user, app, org=org)
        response = list_members(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_members_non_member_returns_403(self):
        from tenxyte.views.organization_views import list_members
        app = _app("ListMembersNonMemberApp")
        owner = _user("lm_owner@test.com", app)
        outsider = _user("lm_outsider@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request("get", "/organizations/members/", outsider, app, org=org)
        response = list_members(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_members_unpaginated(self):
        from tenxyte.views.organization_views import list_members
        app = _app("ListMembersUPApp")
        user = _user("list_members_up@test.com", app)
        org, _ = _setup_org(user, app)

        req = _authed_request("get", "/organizations/members/", user, app, org=org)
        
        from unittest import mock
        with mock.patch('tenxyte.pagination.TenxytePagination.paginate_queryset', return_value=None):
            response = list_members(req)

        assert response.status_code == 200
        assert isinstance(response.data, list)


# ---------------------------------------------------------------------------
# add_member
# ---------------------------------------------------------------------------

class TestAddMemberView:

    @pytest.mark.django_db
    def test_add_member_success_returns_201(self):
        from tenxyte.views.organization_views import add_member
        app = _app("AddMemberApp")
        owner = _user("am_owner@test.com", app)
        new_member = _user("am_new@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/members/add/", owner, app,
            data={"user_id": new_member.id, "role_code": "member"}, org=org
        )
        response = add_member(req)

        assert response.status_code == 201

    @pytest.mark.django_db
    def test_add_member_nonexistent_user_returns_404(self):
        from tenxyte.views.organization_views import add_member
        app = _app("AddMemberNotFoundApp")
        owner = _user("am_nf_owner@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/members/add/", owner, app,
            data={"user_id": 99999, "role_code": "member"}, org=org
        )
        response = add_member(req)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_add_member_invalid_data_returns_400(self):
        from tenxyte.views.organization_views import add_member
        app = _app("AddMemberBadApp")
        owner = _user("am_bad@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/members/add/", owner, app,
            data={}, org=org
        )
        response = add_member(req)

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# update_member_role
# ---------------------------------------------------------------------------

class TestUpdateMemberRoleView:

    @pytest.mark.django_db
    def test_update_role_success_returns_200(self):
        from tenxyte.views.organization_views import update_member_role
        app = _app("UpdateRoleApp")
        owner = _user("ur_owner@test.com", app)
        member = _user("ur_member@test.com", app)
        org, service = _setup_org(owner, app)
        service.add_member(org, member, "member", owner)

        req = _authed_request(
            "patch", f"/organizations/members/{member.id}/", owner, app,
            data={"role_code": "admin"}, org=org
        )
        response = update_member_role(req, user_id=member.id)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_update_role_nonexistent_user_returns_404(self):
        from tenxyte.views.organization_views import update_member_role
        app = _app("UpdateRoleNFApp")
        owner = _user("ur_nf_owner@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "patch", "/organizations/members/99999/", owner, app,
            data={"role_code": "admin"}, org=org
        )
        response = update_member_role(req, user_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_role_invalid_data_returns_400(self):
        from tenxyte.views.organization_views import update_member_role
        app = _app("UpdateRoleBadApp")
        owner = _user("ur_bad@test.com", app)
        member = _user("ur_bad_member@test.com", app)
        org, service = _setup_org(owner, app)
        service.add_member(org, member, "member", owner)

        req = _authed_request(
            "patch", f"/organizations/members/{member.id}/", owner, app,
            data={}, org=org
        )
        response = update_member_role(req, user_id=member.id)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_update_role_owner_fails_returns_400(self):
        from tenxyte.views.organization_views import update_member_role
        app = _app("UpdateRoleOwnerApp")
        owner = _user("ur_owner2@test.com", app)
        org, service = _setup_org(owner, app)

        req = _authed_request(
            "patch", f"/organizations/members/{owner.id}/", owner, app,
            data={"role_code": "member"}, org=org
        )
        response = update_member_role(req, user_id=owner.id)

        assert response.status_code == 400
        assert "owner" in response.data["error"].lower()


# ---------------------------------------------------------------------------
# remove_member
# ---------------------------------------------------------------------------

class TestRemoveMemberView:

    @pytest.mark.django_db
    def test_remove_member_success_returns_200(self):
        from tenxyte.views.organization_views import remove_member
        app = _app("RemoveMemberApp")
        owner = _user("rm_owner@test.com", app)
        member = _user("rm_member@test.com", app)
        org, service = _setup_org(owner, app)
        service.add_member(org, member, "member", owner)

        req = _authed_request(
            "delete", f"/organizations/members/{member.id}/remove/", owner, app,
            org=org
        )
        response = remove_member(req, user_id=member.id)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_remove_nonexistent_user_returns_404(self):
        from tenxyte.views.organization_views import remove_member
        app = _app("RemoveMemberNFApp")
        owner = _user("rm_nf_owner@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "delete", "/organizations/members/99999/remove/", owner, app, org=org
        )
        response = remove_member(req, user_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_remove_owner_fails_returns_400(self):
        from tenxyte.views.organization_views import remove_member
        app = _app("RemoveOwnerNFApp")
        owner = _user("rm_owner_nf@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "delete", f"/organizations/members/{owner.id}/remove/", owner, app, org=org
        )
        response = remove_member(req, user_id=owner.id)

        assert response.status_code == 400
        assert "owner" in response.data["error"].lower()


# ---------------------------------------------------------------------------
# invite_member
# ---------------------------------------------------------------------------

class TestInviteMemberView:

    @pytest.mark.django_db
    def test_invite_success_returns_201(self):
        from tenxyte.views.organization_views import invite_member
        app = _app("InviteApp")
        owner = _user("inv_owner@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/invitations/", owner, app,
            data={"email": "invited@test.com", "role_code": "member"}, org=org
        )
        response = invite_member(req)

        assert response.status_code == 201

    @pytest.mark.django_db
    def test_invite_invalid_data_returns_400(self):
        from tenxyte.views.organization_views import invite_member
        app = _app("InviteBadApp")
        owner = _user("inv_bad@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/invitations/", owner, app,
            data={}, org=org
        )
        response = invite_member(req)

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_invite_non_member_returns_403(self):
        from tenxyte.views.organization_views import invite_member
        app = _app("InviteNonMemberApp")
        owner = _user("inv_owner2@test.com", app)
        outsider = _user("inv_outsider@test.com", app)
        org, _ = _setup_org(owner, app)

        req = _authed_request(
            "post", "/organizations/invitations/", outsider, app,
            data={"email": "x@test.com", "role_code": "member"}, org=org
        )
        response = invite_member(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_invite_existing_member_returns_400(self):
        from tenxyte.views.organization_views import invite_member
        app = _app("InviteExistApp")
        owner = _user("inv_exist_owner@test.com", app)
        member = _user("inv_exist_member@test.com", app)
        org, service = _setup_org(owner, app)
        service.add_member(org, member, "member", owner)

        req = _authed_request(
            "post", "/organizations/invitations/", owner, app,
            data={"email": member.email, "role_code": "member"}, org=org
        )
        response = invite_member(req)

        assert response.status_code == 400
        assert "already a member" in response.data["error"].lower()


# ---------------------------------------------------------------------------
# list_org_roles
# ---------------------------------------------------------------------------

class TestListOrgRolesView:

    @pytest.mark.django_db
    def test_list_roles_returns_200(self):
        from tenxyte.views.organization_views import list_org_roles
        app = _app("ListRolesApp")
        user = _user("list_roles@test.com", app)
        OrganizationService().initialize_system_roles()

        req = _authed_request("get", "/org-roles/", user, app)
        response = list_org_roles(req)

        assert response.status_code == 200
        assert len(response.data) == 4  # owner, admin, member, viewer

    @pytest.mark.django_db
    def test_list_roles_without_auth_returns_401(self):
        from tenxyte.views.organization_views import list_org_roles
        factory = APIRequestFactory()
        req = factory.get("/org-roles/")
        req.application = _app("ListRolesNoAuthApp")
        response = list_org_roles(req)

        assert response.status_code == 401
