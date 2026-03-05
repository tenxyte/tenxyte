"""
Serializers for Organizations feature.
"""

from rest_framework import serializers
from ..models import (
    get_organization_model,
    get_organization_role_model,
    get_organization_membership_model,
    get_user_model,
)

Organization = get_organization_model()
OrganizationRole = get_organization_role_model()
OrganizationMembership = get_organization_membership_model()
User = get_user_model()


class OrganizationRoleSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationRole."""

    class Meta:
        model = OrganizationRole
        fields = ["id", "code", "name", "description", "is_system", "is_default", "permissions", "created_at"]
        read_only_fields = ["id", "is_system", "created_at"]


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for nested serialization."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationMembership."""

    user = UserBasicSerializer(read_only=True)
    role = OrganizationRoleSerializer(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "user",
            "organization_name",
            "role",
            "status",
            "invited_by",
            "invited_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "invited_by", "invited_at", "created_at", "updated_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization."""

    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "parent_name",
            "metadata",
            "is_active",
            "max_members",
            "member_count",
            "created_at",
            "updated_at",
            "created_by_email",
            "user_role",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at", "created_by_email"]

    def get_member_count(self, obj):
        """Get the number of active members."""
        return obj.get_member_count()

    def get_user_role(self, obj):
        """Get the current user's role in this organization."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            role = request.user.get_org_role(obj)
            return role.code if role else None
        return None


class OrganizationTreeSerializer(serializers.ModelSerializer):
    """Serializer for organization hierarchy tree."""

    children = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "depth", "is_root", "member_count", "children"]

    def get_children(self, obj):
        """Recursively serialize children."""
        children = obj.children.filter(is_active=True)
        return OrganizationTreeSerializer(children, many=True).data

    def get_member_count(self, obj):
        """Get the number of active members."""
        return obj.get_member_count()


class CreateOrganizationSerializer(serializers.Serializer):
    """Serializer for creating an organization."""

    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=200, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)
    max_members = serializers.IntegerField(required=False, default=0, min_value=0)


class UpdateOrganizationSerializer(serializers.Serializer):
    """Serializer for updating an organization."""

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    max_members = serializers.IntegerField(required=False, min_value=0)


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding a member to an organization."""

    user_id = serializers.IntegerField()
    role_code = serializers.CharField(max_length=50)


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating a member's role."""

    role_code = serializers.CharField(max_length=50)


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting a member to an organization."""

    email = serializers.EmailField()
    role_code = serializers.CharField(max_length=50)
    expires_in_days = serializers.IntegerField(default=7, min_value=1, max_value=30)


class OrganizationInvitationSerializer(serializers.Serializer):
    """Serializer for organization invitation."""

    id = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    email = serializers.EmailField(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    status = serializers.CharField(read_only=True)
    invited_by_email = serializers.CharField(source="invited_by.email", read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    token = serializers.CharField(read_only=True, write_only=False)
