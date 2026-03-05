"""
Organization models for multi-tenancy and team management.

This module provides:
- AbstractOrganization: Hierarchical organizations with parent/child relationships
- AbstractOrganizationRole: Roles within organizations (separate from global roles)
- AbstractOrganizationMembership: User membership in organizations
- AbstractOrganizationInvitation: Email invitations to join organizations

Organizations are global (like Users). In Cloud deployments, isolation by project
is handled by the Project model in the Tenant Management Layer, not here.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets

from .base import AutoFieldClass


class AbstractOrganization(models.Model):
    """
    Organization with optional parent/child hierarchy.

    Hierarchy example:
        Acme Corp (root)
        ├── Acme France (child)
        │   ├── Acme Paris (grandchild)
        │   └── Acme Lyon
        └── Acme USA (child)

    Organizations are global (like Users). Application = platform (Web/Mobile/Desktop),
    not a tenant. In Cloud mode, isolation by project is handled by the Project model.
    """

    id = AutoFieldClass(primary_key=True)

    # Identity
    name = models.CharField(max_length=200, help_text="Organization name")
    slug = models.SlugField(max_length=200, unique=True, db_index=True, help_text="URL-safe unique identifier")
    description = models.TextField(blank=True)

    # Parent/child hierarchy
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Parent organization (null = root organization)",
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Flexible JSON metadata for custom fields")
    is_active = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(default=0, help_text="Maximum members allowed (0 = unlimited)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_organizations"
    )

    class Meta:
        abstract = True
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self):
        return self.name

    # Hierarchy methods

    def get_ancestors(self, include_self=False):
        """
        Get all ancestor organizations up to the root.

        Args:
            include_self: Include this organization in the result

        Returns:
            QuerySet of ancestor organizations
        """
        ancestors = []
        current = self if include_self else self.parent

        while current:
            ancestors.append(current.id)
            current = current.parent

        return self.__class__.objects.filter(id__in=ancestors).order_by("id")

    def get_descendants(self, include_self=False):
        """
        Get all descendant organizations (recursive).

        Args:
            include_self: Include this organization in the result

        Returns:
            QuerySet of descendant organizations
        """
        descendants = [self.id] if include_self else []

        def collect_children(org):
            for child in org.children.all():
                descendants.append(child.id)
                collect_children(child)

        collect_children(self)

        return self.__class__.objects.filter(id__in=descendants).order_by("id")

    def get_root(self):
        """
        Get the root organization (topmost parent).

        Returns:
            Root organization
        """
        current = self
        while current.parent:
            current = current.parent
        return current

    @property
    def depth(self):
        """
        Get the depth of this organization in the hierarchy (root = 0).

        Returns:
            Integer depth
        """
        depth = 0
        current = self
        while current.parent:
            depth += 1
            current = current.parent
        return depth

    @property
    def is_root(self):
        """Check if this is a root organization (no parent)."""
        return self.parent is None

    def can_add_child(self):
        """
        Check if a child organization can be added (respects max depth).

        Returns:
            Boolean
        """
        from ..conf import org_settings

        return self.depth < org_settings.ORG_MAX_DEPTH - 1

    def get_member_count(self):
        """Get the number of active members in this organization."""
        return self.memberships.filter(status="active").count()

    def is_at_member_limit(self):
        """Check if the organization is at its member limit."""
        if self.max_members == 0:
            return False
        return self.get_member_count() >= self.max_members


class AbstractOrganizationRole(models.Model):
    """
    Roles specific to Organizations (different from global roles).

    Examples of organization roles:
      - owner   : Owner, can delete the organization
      - admin   : Admin, can manage members
      - member  : Member, basic access
      - billing : Billing access only
      - viewer  : Read-only access

    These are separate from global User.roles to avoid polluting the global RBAC system.
    """

    id = AutoFieldClass(primary_key=True)

    code = models.CharField(
        max_length=50, unique=True, db_index=True, help_text="Unique role code (e.g., 'owner', 'admin', 'member')"
    )
    name = models.CharField(max_length=100, help_text="Display name")
    description = models.TextField(blank=True)

    # Role properties
    is_system = models.BooleanField(default=False, help_text="System role (owner, admin, member) - cannot be deleted")
    is_default = models.BooleanField(default=False, help_text="Assigned automatically to new members")

    # Organization-level permissions (as list of permission codes)
    permissions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of permission codes (e.g., ['org.members.invite', 'org.settings.read'])",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def has_permission(self, permission_code):
        """Check if this role has a specific permission (supports wildcards like 'org.*')."""
        for perm in self.permissions:
            if perm == permission_code:
                return True
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if permission_code == prefix or permission_code.startswith(prefix + "."):
                    return True
        return False


class AbstractOrganizationMembership(models.Model):
    """
    Membership = the relationship User ↔ Organization + role.

    This is the KEY TABLE. It answers:
    - "Is User X in Organization Y?"
    - "What is their role in Organization Y?"
    - "Who invited User X?"
    """

    id = AutoFieldClass(primary_key=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_memberships")
    organization = models.ForeignKey("tenxyte.Organization", on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(
        "tenxyte.OrganizationRole",
        on_delete=models.PROTECT,
        related_name="memberships",
        help_text="PROTECT: cannot delete a role while it's assigned",
    )

    # Membership status
    STATUS_CHOICES = [
        ("pending", "Invitation Pending"),
        ("active", "Active"),
        ("suspended", "Suspended"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Invitation workflow
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_org_invitations"
    )
    invited_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        unique_together = [("user", "organization")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "organization", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.organization.name} ({self.role.code})"

    def has_permission(self, permission_code):
        """Check if this membership has a specific permission via its role."""
        return self.role.has_permission(permission_code)

    def is_active_membership(self):
        """Check if this is an active membership."""
        return self.status == "active"


class AbstractOrganizationInvitation(models.Model):
    """
    Invitations to join an organization (by email or link).

    Workflow:
    1. Admin invites user by email
    2. Email sent with token
    3. User accepts/declines
    4. If accepted, Membership created
    """

    id = AutoFieldClass(primary_key=True)

    organization = models.ForeignKey("tenxyte.Organization", on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField(max_length=191, help_text="Email of invitee")
    role = models.ForeignKey(
        "tenxyte.OrganizationRole", on_delete=models.CASCADE, help_text="Role to assign upon acceptance"
    )

    # Security token
    token = models.CharField(
        max_length=64, unique=True, db_index=True, help_text="Secure token for accepting invitation"
    )

    # Invitation metadata
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_org_invitations_pending"
    )

    # Status tracking
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Invitation expiry date")
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["email", "status"]),
        ]

    def __str__(self):
        return f"Invite {self.email} to {self.organization.name} ({self.status})"

    @classmethod
    def create_invitation(cls, organization, email, role, invited_by, expires_in_days=7):
        """
        Create a new invitation with a secure token.

        Args:
            organization: Organization to invite to
            email: Email of invitee
            role: OrganizationRole to assign
            invited_by: User who sent the invitation
            expires_in_days: Days until expiration (default: 7)

        Returns:
            OrganizationInvitation instance
        """
        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timedelta(days=expires_in_days)

        return cls.objects.create(
            organization=organization, email=email, role=role, token=token, invited_by=invited_by, expires_at=expires_at
        )

    def is_expired(self):
        """Check if the invitation has expired."""
        return timezone.now() > self.expires_at or self.status == "expired"

    def can_be_accepted(self):
        """Check if the invitation can still be accepted."""
        return self.status == "pending" and not self.is_expired()

    def accept(self, user):
        """
        Accept the invitation and create membership.

        Args:
            user: User accepting the invitation

        Returns:
            OrganizationMembership instance or None if failed
        """
        from . import get_organization_membership_model

        if not self.can_be_accepted():
            return None

        # Check if user email matches invitation
        if user.email != self.email:
            return None

        # Create membership
        OrganizationMembership = get_organization_membership_model()
        membership, created = OrganizationMembership.objects.get_or_create(
            user=user,
            organization=self.organization,
            defaults={
                "role": self.role,
                "status": "active",
                "invited_by": self.invited_by,
                "invited_at": self.created_at,
            },
        )

        # Mark invitation as accepted
        self.status = "accepted"
        self.accepted_at = timezone.now()
        self.save()

        return membership

    def decline(self):
        """Decline the invitation."""
        self.status = "declined"
        self.save()


# =============================================================================
# CONCRETE MODELS - Default implementations (can be swapped)
# =============================================================================


class Organization(AbstractOrganization):
    """
    Concrete Organization model.

    Can be swapped via TENXYTE_ORGANIZATION_MODEL setting.
    """

    class Meta(AbstractOrganization.Meta):
        db_table = "organizations"
        swappable = "TENXYTE_ORGANIZATION_MODEL"


class OrganizationRole(AbstractOrganizationRole):
    """
    Concrete OrganizationRole model.

    Can be swapped via TENXYTE_ORGANIZATION_ROLE_MODEL setting.
    """

    class Meta(AbstractOrganizationRole.Meta):
        db_table = "organization_roles"
        swappable = "TENXYTE_ORGANIZATION_ROLE_MODEL"


class OrganizationMembership(AbstractOrganizationMembership):
    """
    Concrete OrganizationMembership model.

    Can be swapped via TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL setting.
    """

    class Meta(AbstractOrganizationMembership.Meta):
        db_table = "organization_memberships"
        swappable = "TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL"


class OrganizationInvitation(AbstractOrganizationInvitation):
    """
    Concrete OrganizationInvitation model.
    """

    class Meta(AbstractOrganizationInvitation.Meta):
        db_table = "organization_invitations"


# =============================================================================
# HELPERS - Get swappable organization models
# =============================================================================


def get_organization_model():
    """Get the configured Organization model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_MODEL)


def get_organization_role_model():
    """Get the configured OrganizationRole model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_ROLE_MODEL)


def get_organization_membership_model():
    """Get the configured OrganizationMembership model."""
    from django.apps import apps
    from ..conf import org_settings

    return apps.get_model(org_settings.ORGANIZATION_MEMBERSHIP_MODEL)
