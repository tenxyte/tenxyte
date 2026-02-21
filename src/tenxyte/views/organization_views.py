"""
Organization views - Conditional on TENXYTE_ORGANIZATIONS_ENABLED setting.

All endpoints require X-Access-Key/X-Access-Secret (Application auth).
Org-specific endpoints require X-Org-Slug header.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ..decorators import (
    require_jwt,
    require_org_context,
    require_org_membership,
    require_org_role,
    require_org_permission,
    require_org_owner,
    require_org_admin,
)
from ..services.organization_service import OrganizationService
from ..serializers.organization_serializers import (
    OrganizationSerializer,
    OrganizationTreeSerializer,
    OrganizationRoleSerializer,
    OrganizationMembershipSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer,
    InviteMemberSerializer,
    OrganizationInvitationSerializer,
)
from ..models import get_user_model
from ..pagination import TenxytePagination
from ..filters import apply_organization_filters, apply_member_filters

User = get_user_model()


# =============================================
# Organization CRUD
# =============================================

@api_view(['POST'])
@require_jwt
def create_organization(request: Request) -> Response:
    """
    Create a new organization.
    
    POST /api/auth/organizations/
    {
        "name": "Acme Corp",
        "slug": "acme-corp",  // optional
        "description": "...",
        "parent_id": null,
        "metadata": {},
        "max_members": 0
    }
    """
    serializer = CreateOrganizationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    service = OrganizationService()
    success, organization, error = service.create_organization(
        name=serializer.validated_data['name'],
        created_by=request.user,
        slug=serializer.validated_data.get('slug'),
        description=serializer.validated_data.get('description', ''),
        parent_id=serializer.validated_data.get('parent_id'),
        metadata=serializer.validated_data.get('metadata'),
        max_members=serializer.validated_data.get('max_members', 0)
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(
        OrganizationSerializer(organization, context={'request': request}).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@require_jwt
def list_organizations(request: Request) -> Response:
    """
    List all organizations the user is a member of.
    
    GET /api/auth/organizations/list/
    
    Query params:
        ?search=      → Search in name, slug
        ?is_active=   → Filter by active status
        ?parent=null  → Root organizations only
        ?ordering=    → Order by name, slug, created_at
        ?page=        → Page number
        ?page_size=   → Items per page (max 100)
    """
    queryset = request.user.get_organizations()
    queryset = apply_organization_filters(queryset, request)

    paginator = TenxytePagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = OrganizationSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    serializer = OrganizationSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def get_organization(request: Request) -> Response:
    """
    Get organization details.
    
    GET /api/auth/organizations/{slug}/
    Headers: X-Org-Slug: acme-corp
    """
    serializer = OrganizationSerializer(request.organization, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@require_jwt
@require_org_context
@require_org_admin
def update_organization(request: Request) -> Response:
    """
    Update organization.
    
    PATCH /api/auth/organizations/{slug}/
    Headers: X-Org-Slug: acme-corp
    """
    serializer = UpdateOrganizationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    service = OrganizationService()
    success, error = service.update_organization(
        organization=request.organization,
        user=request.user,
        **serializer.validated_data
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(
        OrganizationSerializer(request.organization, context={'request': request}).data,
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])
@require_jwt
@require_org_context
@require_org_owner
def delete_organization(request: Request) -> Response:
    """
    Delete organization (soft delete).
    
    DELETE /api/auth/organizations/{slug}/
    Headers: X-Org-Slug: acme-corp
    """
    service = OrganizationService()
    success, error = service.delete_organization(
        organization=request.organization,
        user=request.user
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'Organization deleted successfully'}, status=status.HTTP_200_OK)


# =============================================
# Hierarchy
# =============================================

@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def get_organization_tree(request: Request) -> Response:
    """
    Get the organization hierarchy tree.
    
    GET /api/auth/organizations/{slug}/tree/
    Headers: X-Org-Slug: acme-corp
    """
    service = OrganizationService()
    tree = service.get_organization_tree(request.organization)
    
    return Response(tree, status=status.HTTP_200_OK)


# =============================================
# Members
# =============================================

@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def list_members(request: Request) -> Response:
    """
    List organization members.
    
    GET /api/auth/organizations/{slug}/members/
    Headers: X-Org-Slug: acme-corp
    
    Query params:
        ?search=    → Search in user email, first_name, last_name
        ?role=      → Filter by role code
        ?status=    → Filter by membership status
        ?ordering=  → Order by joined_at, user__email
        ?page=      → Page number
        ?page_size= → Items per page (max 100)
    """
    service = OrganizationService()
    memberships = service.get_members(request.organization)
    memberships = apply_member_filters(memberships, request)

    paginator = TenxytePagination()
    page = paginator.paginate_queryset(memberships, request)
    if page is not None:
        serializer = OrganizationMembershipSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = OrganizationMembershipSerializer(memberships, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@require_jwt
@require_org_context
@require_org_permission('org.members.invite')
def add_member(request: Request) -> Response:
    """
    Add a member to the organization.
    
    POST /api/auth/organizations/{slug}/members/
    Headers: X-Org-Slug: acme-corp
    {
        "user_id": 123,
        "role_code": "member"
    }
    """
    serializer = AddMemberSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_to_add = User.objects.get(id=serializer.validated_data['user_id'])
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service = OrganizationService()
    success, membership, error = service.add_member(
        organization=request.organization,
        user_to_add=user_to_add,
        role_code=serializer.validated_data['role_code'],
        added_by=request.user
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(
        OrganizationMembershipSerializer(membership).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['PATCH'])
@require_jwt
@require_org_context
@require_org_permission('org.members.manage')
def update_member_role(request: Request, user_id: int) -> Response:
    """
    Update a member's role.
    
    PATCH /api/auth/organizations/{slug}/members/{user_id}/
    Headers: X-Org-Slug: acme-corp
    {
        "role_code": "admin"
    }
    """
    serializer = UpdateMemberRoleSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_to_update = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service = OrganizationService()
    success, error = service.update_member_role(
        organization=request.organization,
        user_to_update=user_to_update,
        new_role_code=serializer.validated_data['role_code'],
        updated_by=request.user
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    membership = user_to_update.get_org_membership(request.organization)
    return Response(
        OrganizationMembershipSerializer(membership).data,
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])
@require_jwt
@require_org_context
@require_org_permission('org.members.remove')
def remove_member(request: Request, user_id: int) -> Response:
    """
    Remove a member from the organization.
    
    DELETE /api/auth/organizations/{slug}/members/{user_id}/
    Headers: X-Org-Slug: acme-corp
    """
    try:
        user_to_remove = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    service = OrganizationService()
    success, error = service.remove_member(
        organization=request.organization,
        user_to_remove=user_to_remove,
        removed_by=request.user
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'Member removed successfully'}, status=status.HTTP_200_OK)


# =============================================
# Invitations
# =============================================

@api_view(['POST'])
@require_jwt
@require_org_context
@require_org_permission('org.members.invite')
def invite_member(request: Request) -> Response:
    """
    Invite a user to the organization by email.
    
    POST /api/auth/organizations/{slug}/invitations/
    Headers: X-Org-Slug: acme-corp
    {
        "email": "user@example.com",
        "role_code": "member",
        "expires_in_days": 7
    }
    """
    serializer = InviteMemberSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    service = OrganizationService()
    success, invitation, error = service.create_invitation(
        organization=request.organization,
        email=serializer.validated_data['email'],
        role_code=serializer.validated_data['role_code'],
        invited_by=request.user,
        expires_in_days=serializer.validated_data.get('expires_in_days', 7)
    )
    
    if not success:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(
        OrganizationInvitationSerializer(invitation).data,
        status=status.HTTP_201_CREATED
    )


# =============================================
# Organization Roles
# =============================================

@api_view(['GET'])
@require_jwt
def list_org_roles(request: Request) -> Response:
    """
    List available organization roles.
    
    GET /api/auth/org-roles/
    """
    from ..models import get_organization_role_model
    OrganizationRole = get_organization_role_model()
    
    roles = OrganizationRole.objects.all()
    serializer = OrganizationRoleSerializer(roles, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)
