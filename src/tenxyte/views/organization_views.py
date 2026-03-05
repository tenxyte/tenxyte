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
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

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

@extend_schema(
    tags=['Organizations'],
    summary="Créer une organisation",
    description="Crée une nouvelle organisation. L'utilisateur devient automatiquement owner. "
                "Supporte les hiérarchies (parent/child) avec profondeur maximale de 5 niveaux. "
                "Le slug doit être unique globalement. "
                "Limite de membres configurable (0 = illimité).",
    request=inline_serializer(
        name='CreateOrganizationRequest',
        fields={
            'name': serializers.CharField(help_text='Nom de l\'organisation'),
            'slug': serializers.CharField(required=False, allow_blank=True, help_text='Slug unique (optionnel, généré automatiquement)'),
            'description': serializers.CharField(required=False, allow_blank=True, help_text='Description (optionnel)'),
            'parent_id': serializers.IntegerField(required=False, allow_null=True, help_text='ID organisation parent (optionnel)'),
            'metadata': serializers.DictField(required=False, allow_null=True, help_text='Métadonnées personnalisées (optionnel)'),
            'max_members': serializers.IntegerField(required=False, default=0, help_text='Limite de membres (0 = illimité)')
        }
    ),
    responses={
        201: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'slug': {'type': 'string'},
                'description': {'type': 'string'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'is_active': {'type': 'boolean'},
                'member_count': {'type': 'integer'},
                'max_members': {'type': 'integer'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='create_org_success',
            summary='Création réussie',
            value={
                'name': 'Acme Corp',
                'slug': 'acme-corp',
                'description': 'Technologie et innovation',
                'max_members': 100
            }
        ),
        OpenApiExample(
            name='create_org_with_parent',
            summary='Création avec parent',
            value={
                'name': 'Acme France',
                'slug': 'acme-france',
                'parent_id': 1,
                'description': 'Filiale française'
            }
        ),
        OpenApiExample(response_only=True, 
            name='hierarchy_depth_limit',
            summary='Limite profondeur hiérarchie',
            value={
                'error': 'Organization hierarchy depth limit exceeded (max 5 levels)',
                'code': 'HIERARCHY_DEPTH_LIMIT'
            }
        )
    ]
)
@api_view(['POST'])
@require_jwt
def create_organization(request: Request) -> Response:
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


@extend_schema(
    tags=['Organizations'],
    summary="Lister les organisations",
    description="Retourne la liste des organisations où l'utilisateur est membre. "
                "Supporte la recherche, le filtrage et la pagination. "
                "Inclut les statistiques (nombre de membres, hiérarchie).",
    parameters=[
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Recherche dans name et slug'
        ),
        OpenApiParameter(
            name='is_active',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filtrer par statut actif'
        ),
        OpenApiParameter(
            name='parent',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filtrer par parent (null = racine)'
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=['name', 'slug', 'created_at', '-name', '-slug', '-created_at'],
            description='Ordre de tri'
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Numéro de page'
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Éléments par page (max 100)'
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'name': {'type': 'string'},
                            'slug': {'type': 'string'},
                            'description': {'type': 'string'},
                            'member_count': {'type': 'integer'},
                            'max_members': {'type': 'integer'},
                            'is_active': {'type': 'boolean'},
                            'created_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='list_orgs_success',
            summary='Liste paginée',
            value={
                'count': 25,
                'next': 'http://api.example.com/organizations/?page=2',
                'previous': None,
                'results': [
                    {
                        'id': 1,
                        'name': 'Acme Corp',
                        'slug': 'acme-corp',
                        'member_count': 15,
                        'is_active': True
                    }
                ]
            }
        )
    ]
)
@api_view(['GET'])
@require_jwt
def list_organizations(request: Request) -> Response:
    queryset = request.user.get_organizations()
    queryset = apply_organization_filters(queryset, request)

    paginator = TenxytePagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = OrganizationSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    serializer = OrganizationSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Organizations'],
    summary="Détails d'une organisation",
    description="Retourne les détails complets d'une organisation. "
                "Nécessite le header X-Org-Slug pour identifier l'organisation. "
                "Inclut les métadonnées, statistiques membres, et hiérarchie. "
                "Uniquement accessible aux membres de l'organisation.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'slug': {'type': 'string'},
                'description': {'type': 'string'},
                'metadata': {'type': 'object'},
                'is_active': {'type': 'boolean'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'},
                'member_count': {'type': 'integer'},
                'max_members': {'type': 'integer'},
                'parent': {'type': 'object', 'nullable': True},
                'children': {
                    'type': 'array',
                    'items': {'type': 'object'}
                },
                'user_role': {'type': 'string'},
                'user_permissions': {'type': 'array'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='get_org_success',
            summary='Détails organisation',
            value={
                'id': 1,
                'name': 'Acme Corp',
                'slug': 'acme-corp',
                'description': 'Technologie et innovation',
                'member_count': 15,
                'max_members': 100,
                'user_role': 'admin',
                'user_permissions': ['manage_members', 'view_reports']
            }
        ),
        OpenApiExample(response_only=True, 
            name='org_not_member',
            summary='Non-membre',
            value={
                'error': 'User is not a member of this organization',
                'code': 'NOT_MEMBER'
            }
        )
    ]
)
@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def get_organization(request: Request) -> Response:
    serializer = OrganizationSerializer(request.organization, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Organizations'],
    summary="Mettre à jour une organisation",
    description="Met à jour les informations d'une organisation. "
                "Nécessite le header X-Org-Slug et droits d'admin. "
                "Le changement de parent respecte les contraintes de hiérarchie. "
                "Impossible de créer des boucles ou dépasser 5 niveaux. "
                "La limite de membres ne peut pas être inférieure au nombre actuel.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        )
    ],
    request=inline_serializer(
        name='UpdateOrganizationRequest',
        fields={
            'name': serializers.CharField(required=False, allow_blank=True, help_text='Nom de l\'organisation'),
            'slug': serializers.CharField(required=False, allow_blank=True, help_text='Nouveau slug unique'),
            'description': serializers.CharField(required=False, allow_blank=True, help_text='Description'),
            'parent_id': serializers.IntegerField(required=False, allow_null=True, help_text='Nouveau parent ID'),
            'metadata': serializers.DictField(required=False, allow_null=True, help_text='Métadonnées'),
            'max_members': serializers.IntegerField(required=False, allow_null=True, help_text='Nouvelle limite membres'),
            'is_active': serializers.BooleanField(required=False, allow_null=True, help_text='Statut actif')
        }
    ),
    responses={
        200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'slug': {'type': 'string'},
                'description': {'type': 'string'},
                'updated_at': {'type': 'string', 'format': 'date-time'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='update_org_success',
            summary='Mise à jour réussie',
            value={
                'name': 'Acme Corporation',
                'description': 'Mise à jour description',
                'max_members': 200
            }
        ),
        OpenApiExample(response_only=True, 
            name='parent_constraint_violation',
            summary='Violation contrainte parent',
            value={
                'error': 'Cannot set parent: would create circular hierarchy',
                'code': 'CIRCULAR_HIERARCHY'
            }
        ),
        OpenApiExample(response_only=True, 
            name='member_limit_too_low',
            summary='Limite membres trop basse',
            value={
                'error': 'Member limit cannot be less than current member count',
                'code': 'MEMBER_LIMIT_VIOLATION'
            }
        )
    ]
)
@api_view(['PATCH'])
@require_jwt
@require_org_context
@require_org_admin
def update_organization(request: Request) -> Response:
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


@extend_schema(
    tags=['Organizations'],
    summary="Supprimer une organisation",
    description="Supprime une organisation (soft delete). "
                "Nécessite droits de propriétaire et header X-Org-Slug. "
                "Impossible si l'organisation a des organisations enfants. "
                "Action irréversible mais récupérable via admin. "
                "Tous les membres perdent l'accès.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        )
    ],
    responses={
        200: {'description': 'Organisation supprimée avec succès', 'type': 'object'},
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='delete_org_success',
            summary='Suppression réussie',
            value=None
        ),
        OpenApiExample(response_only=True, 
            name='has_child_organizations',
            summary='Organisations enfants présentes',
            value={
                'error': 'Cannot delete organization with child organizations',
                'code': 'HAS_CHILDREN'
            }
        ),
        OpenApiExample(response_only=True, 
            name='not_owner',
            summary='Pas propriétaire',
            value={
                'error': 'Only organization owners can delete organizations',
                'code': 'NOT_OWNER'
            }
        )
    ]
)
@api_view(['DELETE'])
@require_jwt
@require_org_context
@require_org_owner
def delete_organization(request: Request) -> Response:
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

@extend_schema(
    tags=['Organizations'],
    summary="Hiérarchie de l'organisation",
    description="Retourne l'arbre hiérarchique de l'organisation.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
        )
    ],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def get_organization_tree(request: Request) -> Response:
    """
    Get the organization hierarchy tree.
    
    GET {API_PREFIX}/auth/organizations/{slug}/tree/
    Headers: X-Org-Slug: acme-corp
    """
    service = OrganizationService()
    tree = service.get_organization_tree(request.organization)
    
    return Response(tree, status=status.HTTP_200_OK)


# =============================================
# Members
# =============================================

@extend_schema(
    tags=['Organizations'],
    summary="Lister les membres",
    description="Retourne la liste des membres de l'organisation. "
                "Inclut les rôles, permissions héritées, et statut. "
                "Supporte la recherche, filtrage par rôle et pagination. "
                "Affiche les permissions effectives (directes + héritées).",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Recherche dans email, prénom, nom'
        ),
        OpenApiParameter(
            name='role',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=['owner', 'admin', 'member'],
            description='Filtrer par rôle'
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=['active', 'inactive', 'pending'],
            description='Filtrer par statut'
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=['joined_at', '-joined_at', 'user__email', '-user__email'],
            description='Ordre de tri'
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Numéro de page'
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Éléments par page (max 100)'
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'user': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'email': {'type': 'string'},
                                    'first_name': {'type': 'string'},
                                    'last_name': {'type': 'string'}
                                }
                            },
                            'role': {'type': 'string'},
                            'role_display': {'type': 'string'},
                            'permissions': {'type': 'array'},
                            'inherited_permissions': {'type': 'array'},
                            'effective_permissions': {'type': 'array'},
                            'joined_at': {'type': 'string', 'format': 'date-time'},
                            'status': {'type': 'string'}
                        }
                    }
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            name='list_members_success',
            summary='Liste membres avec permissions',
            value={
                'count': 15,
                'results': [
                    {
                        'id': 1,
                        'user': {'id': 42, 'email': 'admin@acme.com', 'first_name': 'John', 'last_name': 'Doe'},
                        'role': 'admin',
                        'role_display': 'Administrator',
                        'permissions': ['manage_members', 'view_reports'],
                        'inherited_permissions': ['org.read'],
                        'effective_permissions': ['org.read', 'manage_members', 'view_reports'],
                        'joined_at': '2024-01-15T10:30:00Z',
                        'status': 'active'
                    }
                ]
            }
        )
    ]
)
@api_view(['GET'])
@require_jwt
@require_org_context
@require_org_membership
def list_members(request: Request) -> Response:
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


@extend_schema(
    tags=['Organizations'],
    summary="Ajouter un membre",
    description="Ajoute un utilisateur comme membre de l'organisation. "
                "Nécessite la permission org.members.invite. "
                "Respecte les limites de membres configurées. "
                "L'utilisateur reçoit une notification d'invitation. "
                "Le propriétaire ne peut pas être ajouté comme membre simple.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        )
    ],
    request=inline_serializer(
        name='AddOrganizationMemberRequest',
        fields={
            'user_id': serializers.IntegerField(help_text='ID de l\'utilisateur à ajouter'),
            'role_code': serializers.CharField(help_text='Rôle du membre (owner non autorisé)')
        }
    ),
    responses={
        201: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'user': {'type': 'object'},
                'role': {'type': 'string'},
                'joined_at': {'type': 'string', 'format': 'date-time'},
                'status': {'type': 'string'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='add_member_success',
            summary='Membre ajouté avec succès',
            value={
                'user_id': 123,
                'role_code': 'member'
            }
        ),
        OpenApiExample(response_only=True, 
            name='member_limit_exceeded',
            summary='Limite de membres dépassée',
            value={
                'error': 'Organization member limit exceeded',
                'code': 'MEMBER_LIMIT_EXCEEDED'
            }
        ),
        OpenApiExample(response_only=True, 
            name='already_member',
            summary='Déjà membre',
            value={
                'error': 'User is already a member of this organization',
                'code': 'ALREADY_MEMBER'
            }
        ),
        OpenApiExample(response_only=True, 
            name='invalid_role',
            summary='Rôle invalide',
            value={
                'error': 'Cannot assign owner role through add_member',
                'code': 'INVALID_ROLE'
            }
        )
    ]
)
@api_view(['POST'])
@require_jwt
@require_org_context
@require_org_permission('org.members.invite')
def add_member(request: Request) -> Response:
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


@extend_schema(
    tags=['Organizations'],
    summary="Mettre à jour le rôle d'un membre",
    description="Met à jour le rôle d'un membre existant. "
                "Nécessite la permission org.members.manage. "
                "Un propriétaire ne peut pas être rétrogradé par un autre membre. "
                "Le dernier propriétaire ne peut pas être rétrogradé. "
                "L'utilisateur reçoit une notification de changement de rôle.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        ),
        OpenApiParameter(
            name='user_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID de l\'utilisateur à modifier'
        )
    ],
    request=inline_serializer(
        name='UpdateOrganizationMemberRoleRequest',
        fields={
            'role_code': serializers.CharField(help_text='Nouveau rôle (owner nécessite droits appropriés)')
        }
    ),
    responses={
        200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'user': {'type': 'object'},
                'role': {'type': 'string'},
                'updated_at': {'type': 'string', 'format': 'date-time'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='update_role_success',
            summary='Rôle mis à jour',
            value={
                'role_code': 'admin'
            }
        ),
        OpenApiExample(response_only=True, 
            name='cannot_demote_owner',
            summary='Impossible de rétrograder owner',
            value={
                'error': 'Cannot demote organization owner',
                'code': 'CANNOT_DEMOTE_OWNER'
            }
        ),
        OpenApiExample(response_only=True, 
            name='last_owner_error',
            summary='Dernier propriétaire',
            value={
                'error': 'Cannot remove role from last organization owner',
                'code': 'LAST_OWNER_REQUIRED'
            }
        )
    ]
)
@api_view(['PATCH'])
@require_jwt
@require_org_context
@require_org_permission('org.members.manage')
def update_member_role(request: Request, user_id: int) -> Response:
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


@extend_schema(
    tags=['Organizations'],
    summary="Retirer un membre",
    description="Retire un membre de l'organisation. "
                "Nécessite la permission org.members.remove. "
                "Un propriétaire ne peut pas être retiré par un autre membre. "
                "Le dernier propriétaire ne peut pas être retiré. "
                "Un membre peut se retirer lui-même (auto-suppression). "
                "L'utilisateur perd immédiatement l'accès à l'organisation.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        ),
        OpenApiParameter(
            name='user_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID de l\'utilisateur à retirer'
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(response_only=True, 
            name='remove_member_success',
            summary='Membre retiré avec succès',
            value=None
        ),
        OpenApiExample(response_only=True, 
            name='cannot_remove_owner',
            summary='Impossible de retirer owner',
            value={
                'error': 'Cannot remove organization owner',
                'code': 'CANNOT_REMOVE_OWNER'
            }
        ),
        OpenApiExample(response_only=True, 
            name='last_owner_error',
            summary='Dernier propriétaire',
            value={
                'error': 'Cannot remove last organization owner',
                'code': 'LAST_OWNER_REQUIRED'
            }
        ),
        OpenApiExample(response_only=True, 
            name='self_removal',
            summary='Auto-suppression',
            value={
                'message': 'Member removed successfully'
            }
        )
    ]
)
@api_view(['DELETE'])
@require_jwt
@require_org_context
@require_org_permission('org.members.remove')
def remove_member(request: Request, user_id: int) -> Response:
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

@extend_schema(
    tags=['Organizations'],
    summary="Inviter un membre par email",
    description="Invite un utilisateur à rejoindre l'organisation par email. "
                "Nécessite la permission org.members.invite. "
                "Un email avec un lien d'acceptation est envoyé. "
                "L'invitation expire après le nombre de jours spécifié. "
                "L'utilisateur doit créer un compte ou se connecter pour accepter.",
    parameters=[
        OpenApiParameter(
            name='X-Org-Slug',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Slug de l\'organisation (multi-tenant context)'
        )
    ],
    request=inline_serializer(
        name='InviteOrganizationMemberRequest',
        fields={
            'email': serializers.EmailField(help_text='Email de l\'utilisateur à inviter'),
            'role_code': serializers.CharField(help_text='Rôle attribué après acceptation'),
            'expires_in_days': serializers.IntegerField(required=False, default=7, min_value=1, max_value=30, help_text='Durée de validité en jours (1-30)')
        }
    ),
    responses={
        201: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'email': {'type': 'string'},
                'role': {'type': 'string'},
                'token': {'type': 'string'},
                'expires_at': {'type': 'string', 'format': 'date-time'},
                'invited_by': {'type': 'object'},
                'organization': {'type': 'object'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        }
    },
    examples=[
        OpenApiExample(request_only=True, 
            name='invite_success',
            summary='Invitation envoyée',
            value={
                'email': 'new.user@example.com',
                'role_code': 'member',
                'expires_in_days': 7
            }
        ),
        OpenApiExample(response_only=True, 
            name='already_member',
            summary='Déjà membre',
            value={
                'error': 'User is already a member of this organization',
                'code': 'ALREADY_MEMBER'
            }
        ),
        OpenApiExample(response_only=True, 
            name='invitation_exists',
            summary='Invitation existante',
            value={
                'error': 'Pending invitation already exists for this email',
                'code': 'INVITATION_EXISTS'
            }
        )
    ]
)
@api_view(['POST'])
@require_jwt
@require_org_context
@require_org_permission('org.members.invite')
def invite_member(request: Request) -> Response:
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

@extend_schema(
    tags=['Organizations'],
    summary="Lister les rôles d'organisation",
    description="Retourne la liste des rôles disponibles pour les organisations. "
                "Inclut les permissions associées à chaque rôle. "
                "Affiche la hiérarchie des rôles et poids de permission. "
                "Utile pour comprendre les capacités de chaque rôle.",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'string'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'weight': {'type': 'integer'},
                    'permissions': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'string'},
                                'name': {'type': 'string'},
                                'description': {'type': 'string'}
                            }
                        }
                    },
                    'is_system_role': {'type': 'boolean'},
                    'created_at': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            name='roles_list',
            summary='Liste des rôles avec permissions',
            value=[
                {
                    'code': 'owner',
                    'name': 'Owner',
                    'description': 'Full control over organization',
                    'weight': 100,
                    'permissions': [
                        {'code': 'org.*', 'name': 'All organization permissions'}
                    ],
                    'is_system_role': True
                },
                {
                    'code': 'admin',
                    'name': 'Administrator',
                    'description': 'Can manage members and settings',
                    'weight': 50,
                    'permissions': [
                        {'code': 'org.members.manage', 'name': 'Manage members'},
                        {'code': 'org.settings.edit', 'name': 'Edit settings'}
                    ],
                    'is_system_role': True
                },
                {
                    'code': 'member',
                    'name': 'Member',
                    'description': 'Basic organization access',
                    'weight': 10,
                    'permissions': [
                        {'code': 'org.read', 'name': 'View organization'}
                    ],
                    'is_system_role': True
                }
            ]
        )
    ]
)
@api_view(['GET'])
@require_jwt
def list_org_roles(request: Request) -> Response:
    from ..models import get_organization_role_model
    OrganizationRole = get_organization_role_model()
    
    roles = OrganizationRole.objects.all()
    serializer = OrganizationRoleSerializer(roles, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)
