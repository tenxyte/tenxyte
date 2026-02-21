"""
Tests OrganizationService - CRUD, hiérarchie, membres, invitations.

Coverage cible : organization_service.py (0% → ~80%)
"""

import pytest
from django.utils import timezone
from datetime import timedelta

from tenxyte.models import Application, User
from tenxyte.models.organization import (
    Organization,
    OrganizationRole,
    OrganizationMembership,
    OrganizationInvitation,
)
from tenxyte.services.organization_service import OrganizationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    return OrganizationService()


@pytest.fixture
def app():
    a, _ = Application.create_application(name="OrgTestApp")
    return a


@pytest.fixture
def owner(app):
    u = User.objects.create(email="owner@test.com", is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


@pytest.fixture
def member_user(app):
    u = User.objects.create(email="member@test.com", is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


@pytest.fixture
def other_user(app):
    u = User.objects.create(email="other@test.com", is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


@pytest.fixture
def system_roles(service):
    """Initialize system roles before tests."""
    return service.initialize_system_roles()


@pytest.fixture
def org(service, owner, system_roles):
    """Create a base organization owned by owner."""
    success, organization, error = service.create_organization(
        name="Test Org",
        created_by=owner,
    )
    assert success, error
    return organization


def owner_of(org):
    """Helper: get the owner user of an org."""
    membership = OrganizationMembership.objects.get(
        organization=org, role__code="owner"
    )
    return membership.user


# ---------------------------------------------------------------------------
# initialize_system_roles
# ---------------------------------------------------------------------------

class TestInitializeSystemRoles:

    @pytest.mark.django_db
    def test_creates_four_system_roles(self, service):
        roles = service.initialize_system_roles()
        codes = {r.code for r in roles}
        assert {"owner", "admin", "member", "viewer"} == codes

    @pytest.mark.django_db
    def test_idempotent_on_second_call(self, service):
        service.initialize_system_roles()
        roles = service.initialize_system_roles()
        assert OrganizationRole.objects.count() == 4

    @pytest.mark.django_db
    def test_member_role_is_default(self, service):
        service.initialize_system_roles()
        member_role = OrganizationRole.objects.get(code="member")
        assert member_role.is_default is True

    @pytest.mark.django_db
    def test_owner_role_is_system(self, service):
        service.initialize_system_roles()
        owner_role = OrganizationRole.objects.get(code="owner")
        assert owner_role.is_system is True


# ---------------------------------------------------------------------------
# create_organization
# ---------------------------------------------------------------------------

class TestCreateOrganization:

    @pytest.mark.django_db
    def test_create_basic_organization(self, service, owner, system_roles):
        success, org, error = service.create_organization(
            name="Acme Corp",
            created_by=owner,
        )
        assert success is True
        assert org is not None
        assert org.name == "Acme Corp"
        assert error == ""

    @pytest.mark.django_db
    def test_auto_generates_slug(self, service, owner, system_roles):
        success, org, _ = service.create_organization(
            name="My Organization",
            created_by=owner,
        )
        assert org.slug == "my-organization"

    @pytest.mark.django_db
    def test_slug_uniqueness_auto_increments(self, service, owner, system_roles):
        service.create_organization(name="Acme", created_by=owner)
        success, org2, _ = service.create_organization(name="Acme", created_by=owner)
        assert org2.slug == "acme-1"

    @pytest.mark.django_db
    def test_custom_slug_accepted(self, service, owner, system_roles):
        success, org, _ = service.create_organization(
            name="Acme Corp",
            created_by=owner,
            slug="custom-slug",
        )
        assert org.slug == "custom-slug"

    @pytest.mark.django_db
    def test_creator_assigned_as_owner(self, service, owner, system_roles):
        success, org, _ = service.create_organization(name="Org", created_by=owner)
        membership = OrganizationMembership.objects.get(organization=org, user=owner)
        assert membership.role.code == "owner"
        assert membership.status == "active"

    @pytest.mark.django_db
    def test_create_with_parent(self, service, owner, system_roles):
        _, parent, _ = service.create_organization(name="Parent", created_by=owner)
        success, child, error = service.create_organization(
            name="Child",
            created_by=owner,
            parent_id=parent.id,
        )
        assert success is True
        assert child.parent == parent

    @pytest.mark.django_db
    def test_create_with_nonexistent_parent_fails(self, service, owner, system_roles):
        success, org, error = service.create_organization(
            name="Orphan",
            created_by=owner,
            parent_id=99999,
        )
        assert success is False
        assert "not found" in error

    @pytest.mark.django_db
    def test_create_with_description_and_metadata(self, service, owner, system_roles):
        success, org, _ = service.create_organization(
            name="Org",
            created_by=owner,
            description="A test org",
            metadata={"key": "value"},
        )
        assert org.description == "A test org"
        assert org.metadata == {"key": "value"}


# ---------------------------------------------------------------------------
# get_organization
# ---------------------------------------------------------------------------

class TestGetOrganization:

    @pytest.mark.django_db
    def test_get_by_slug(self, service, org):
        result = service.get_organization(slug=org.slug)
        assert result == org

    @pytest.mark.django_db
    def test_get_by_id(self, service, org):
        result = service.get_organization(org_id=org.id)
        assert result == org

    @pytest.mark.django_db
    def test_get_nonexistent_returns_none(self, service):
        result = service.get_organization(slug="does-not-exist")
        assert result is None

    @pytest.mark.django_db
    def test_get_inactive_returns_none(self, service, org):
        org.is_active = False
        org.save()
        result = service.get_organization(slug=org.slug)
        assert result is None

    @pytest.mark.django_db
    def test_get_with_no_args_returns_none(self, service):
        result = service.get_organization()
        assert result is None


# ---------------------------------------------------------------------------
# update_organization
# ---------------------------------------------------------------------------

class TestUpdateOrganization:

    @pytest.mark.django_db
    def test_owner_can_update_name(self, service, org, system_roles):
        o = owner_of(org)
        success, error = service.update_organization(org, o, name="New Name")
        assert success is True, error
        org.refresh_from_db()
        assert org.name == "New Name"

    @pytest.mark.django_db
    def test_non_member_cannot_update(self, service, org, other_user, system_roles):
        success, error = service.update_organization(org, other_user, name="Hack")
        assert success is False
        assert "permissions" in error.lower()

    @pytest.mark.django_db
    def test_max_members_validated_against_current_count(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        # org now has 2 members (owner + member_user)
        success, error = service.update_organization(org, o, max_members=1)
        assert success is False
        assert "already has" in error

    @pytest.mark.django_db
    def test_max_members_zero_is_unlimited(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, error = service.update_organization(org, o, max_members=0)
        assert success is True

    @pytest.mark.django_db
    def test_update_description_and_metadata(self, service, org, system_roles):
        o = owner_of(org)
        success, _ = service.update_organization(
            org, o, description="Updated", metadata={"x": 1}
        )
        assert success is True
        org.refresh_from_db()
        assert org.description == "Updated"
        assert org.metadata == {"x": 1}


# ---------------------------------------------------------------------------
# delete_organization
# ---------------------------------------------------------------------------

class TestDeleteOrganization:

    @pytest.mark.django_db
    def test_owner_can_delete(self, service, org, system_roles):
        o = owner_of(org)
        success, error = service.delete_organization(org, o)
        assert success is True, error
        org.refresh_from_db()
        assert org.is_active is False

    @pytest.mark.django_db
    def test_non_owner_cannot_delete(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "admin", o)
        success, error = service.delete_organization(org, member_user)
        assert success is False
        assert "owner" in error.lower()

    @pytest.mark.django_db
    def test_cannot_delete_with_children(self, service, org, system_roles):
        o = owner_of(org)
        _, child, _ = service.create_organization(
            name="Child", created_by=o, parent_id=org.id
        )
        success, error = service.delete_organization(org, o)
        assert success is False
        assert "child" in error.lower()


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------

class TestOrganizationHierarchy:

    @pytest.mark.django_db
    def test_get_organization_tree(self, service, org, system_roles):
        o = owner_of(org)
        _, child, _ = service.create_organization(
            name="Child", created_by=o, parent_id=org.id
        )
        tree = service.get_organization_tree(org)
        assert tree["name"] == org.name
        assert len(tree["children"]) == 1
        assert tree["children"][0]["name"] == "Child"

    @pytest.mark.django_db
    def test_move_organization_to_new_parent(self, service, owner, system_roles):
        _, parent_a, _ = service.create_organization(name="Parent A", created_by=owner)
        _, parent_b, _ = service.create_organization(name="Parent B", created_by=owner)
        _, child, _ = service.create_organization(
            name="Child", created_by=owner, parent_id=parent_a.id
        )
        o = owner_of(child)
        success, error = service.move_organization(child, parent_b.id, o)
        assert success is True, error
        child.refresh_from_db()
        assert child.parent == parent_b

    @pytest.mark.django_db
    def test_cannot_move_to_own_descendant(self, service, owner, system_roles):
        _, parent, _ = service.create_organization(name="Parent", created_by=owner)
        _, child, _ = service.create_organization(
            name="Child", created_by=owner, parent_id=parent.id
        )
        o = owner_of(parent)
        success, error = service.move_organization(parent, child.id, o)
        assert success is False
        assert "descendant" in error.lower()

    @pytest.mark.django_db
    def test_cannot_move_to_self(self, service, owner, system_roles):
        _, local_org, _ = service.create_organization(name="Org", created_by=owner)
        o = owner_of(local_org)
        success, error = service.move_organization(local_org, local_org.id, o)
        assert success is False
        assert "itself" in error.lower()

    @pytest.mark.django_db
    def test_move_to_nonexistent_parent_fails(self, service, owner, system_roles):
        _, local_org, _ = service.create_organization(name="Org", created_by=owner)
        o = owner_of(local_org)
        success, error = service.move_organization(local_org, 99999, o)
        assert success is False
        assert "not found" in error.lower()


# ---------------------------------------------------------------------------
# Member Management
# ---------------------------------------------------------------------------

class TestMemberManagement:

    @pytest.mark.django_db
    def test_add_member_success(self, service, org, member_user, system_roles):
        o = owner_of(org)
        success, membership, error = service.add_member(
            org, member_user, "member", o
        )
        assert success is True, error
        assert membership is not None
        assert membership.user == member_user
        assert membership.role.code == "member"

    @pytest.mark.django_db
    def test_add_member_nonexistent_role_fails(self, service, org, member_user, system_roles):
        o = owner_of(org)
        success, _, error = service.add_member(org, member_user, "nonexistent", o)
        assert success is False
        assert "not found" in error

    @pytest.mark.django_db
    def test_add_duplicate_member_fails(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, _, error = service.add_member(org, member_user, "member", o)
        assert success is False
        assert "already a member" in error

    @pytest.mark.django_db
    def test_add_member_respects_max_members(self, service, org, member_user, system_roles):
        o = owner_of(org)
        # org has 1 member (owner), set limit to 1
        service.update_organization(org, o, max_members=1)
        success, _, error = service.add_member(org, member_user, "member", o)
        assert success is False
        assert "limit" in error.lower()

    @pytest.mark.django_db
    def test_get_members_returns_active(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        members = service.get_members(org)
        assert members.count() == 2  # owner + member

    @pytest.mark.django_db
    def test_update_member_role(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, error = service.update_member_role(org, member_user, "admin", o)
        assert success is True, error
        membership = OrganizationMembership.objects.get(organization=org, user=member_user)
        assert membership.role.code == "admin"

    @pytest.mark.django_db
    def test_cannot_update_owner_role(self, service, org, system_roles):
        o = owner_of(org)
        success, error = service.update_member_role(org, o, "member", o)
        assert success is False
        assert "owner" in error.lower()

    @pytest.mark.django_db
    def test_update_role_nonexistent_role_fails(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, error = service.update_member_role(org, member_user, "ghost", o)
        assert success is False
        assert "not found" in error

    @pytest.mark.django_db
    def test_remove_member_success(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, error = service.remove_member(org, member_user, o)
        assert success is True, error
        assert not OrganizationMembership.objects.filter(
            organization=org, user=member_user
        ).exists()

    @pytest.mark.django_db
    def test_cannot_remove_owner(self, service, org, system_roles):
        o = owner_of(org)
        success, error = service.remove_member(org, o, o)
        assert success is False
        assert "owner" in error.lower()

    @pytest.mark.django_db
    def test_remove_nonmember_fails(self, service, org, other_user, system_roles):
        o = owner_of(org)
        success, error = service.remove_member(org, other_user, o)
        assert success is False
        assert "not a member" in error


# ---------------------------------------------------------------------------
# Invitation Management
# ---------------------------------------------------------------------------

class TestInvitationManagement:

    @pytest.mark.django_db
    def test_create_invitation_success(self, service, org, system_roles):
        o = owner_of(org)
        success, invitation, error = service.create_invitation(
            organization=org,
            email="newuser@test.com",
            role_code="member",
            invited_by=o,
        )
        assert success is True, error
        assert invitation is not None
        assert invitation.email == "newuser@test.com"
        assert invitation.status == "pending"

    @pytest.mark.django_db
    def test_invitation_has_token(self, service, org, system_roles):
        o = owner_of(org)
        _, invitation, _ = service.create_invitation(
            org, "invite@test.com", "member", o
        )
        assert invitation.token is not None
        assert len(invitation.token) > 10

    @pytest.mark.django_db
    def test_invitation_nonexistent_role_fails(self, service, org, system_roles):
        o = owner_of(org)
        success, _, error = service.create_invitation(
            org, "x@test.com", "ghost_role", o
        )
        assert success is False
        assert "not found" in error

    @pytest.mark.django_db
    def test_invitation_existing_member_fails(self, service, org, member_user, system_roles):
        o = owner_of(org)
        service.add_member(org, member_user, "member", o)
        success, _, error = service.create_invitation(
            org, member_user.email, "member", o
        )
        assert success is False
        assert "already a member" in error

    @pytest.mark.django_db
    def test_duplicate_invitation_cancels_previous(self, service, org, system_roles):
        o = owner_of(org)
        service.create_invitation(org, "dup@test.com", "member", o)
        service.create_invitation(org, "dup@test.com", "member", o)
        expired = OrganizationInvitation.objects.filter(
            organization=org, email="dup@test.com", status="expired"
        )
        assert expired.count() == 1

    @pytest.mark.django_db
    def test_invitation_respects_member_limit(self, service, org, system_roles):
        o = owner_of(org)
        service.update_organization(org, o, max_members=1)
        success, _, error = service.create_invitation(
            org, "new@test.com", "member", o
        )
        assert success is False
        assert "limit" in error.lower()
