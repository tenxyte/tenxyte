import pytest
from django.utils import timezone
from datetime import timedelta
from tenxyte.models.organization import (
    Organization, OrganizationRole, OrganizationMembership, OrganizationInvitation,
    get_organization_model, get_organization_role_model, get_organization_membership_model
)
from tenxyte.models import User

@pytest.mark.django_db
class TestOrganizationModels:
    def setup_method(self):
        self.user = User.objects.create(email="test@org.com")
        self.org_root = Organization.objects.create(name="Root", slug="root")
        self.org_child = Organization.objects.create(name="Child", slug="child", parent=self.org_root)
        self.org_grandchild = Organization.objects.create(name="GChild", slug="gchild", parent=self.org_child)
        
        self.role = OrganizationRole.objects.create(code="admin", name="Admin", permissions=["org.test"])
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=self.org_child, role=self.role)
        
    def test_organization_str(self):
        assert str(self.org_root) == "Root"
        
    def test_get_ancestors(self):
        ancestors = self.org_grandchild.get_ancestors(include_self=False)
        assert ancestors.count() == 2
        
    def test_get_root(self):
        assert self.org_grandchild.get_root() == self.org_root
        
    def test_role_str_and_perms(self):
        assert str(self.role) == "Admin (admin)"
        assert self.role.has_permission("org.test") is True
        assert self.role.has_permission("org.notfound") is False
        
    def test_membership_str(self):
        assert str(self.membership) == "test@org.com → Child (admin)"
        
    def test_invitation_methods(self):
        invite = OrganizationInvitation.create_invitation(self.org_child, "new@org.com", self.role, self.user)
        assert str(invite) == "Invite new@org.com to Child (pending)"
        
        assert invite.is_expired() is False
        assert invite.can_be_accepted() is True
        
        # Test accept failure (wrong email)
        assert invite.accept(self.user) is None
        
        # Test accept success
        new_user = User.objects.create(email="new@org.com")
        mem = invite.accept(new_user)
        assert mem is not None
        assert mem.user == new_user
        assert mem.organization == self.org_child
        assert invite.status == 'accepted'
        
        # Test can_be_accepted again
        assert invite.can_be_accepted() is False
        assert invite.accept(new_user) is None
        
        # Test decline
        invite2 = OrganizationInvitation.create_invitation(self.org_child, "other@org.com", self.role, self.user)
        invite2.decline()
        assert invite2.status == 'declined'
        assert invite2.can_be_accepted() is False
        
        # Test expired
        invite3 = OrganizationInvitation.create_invitation(self.org_child, "other2@org.com", self.role, self.user)
        invite3.expires_at = timezone.now() - timedelta(days=1)
        invite3.save()
        assert invite3.is_expired() is True
        assert invite3.can_be_accepted() is False
        
    def test_get_models(self):
        assert get_organization_model() == Organization
        assert get_organization_role_model() == OrganizationRole
        assert get_organization_membership_model() == OrganizationMembership
