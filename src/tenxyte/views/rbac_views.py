from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    PermissionSerializer, RoleSerializer, RoleListSerializer,
    ManageRolePermissionsSerializer, AssignRoleSerializer
)
from ..models import get_user_model, get_role_model, get_permission_model
from ..decorators import require_permission
from ..pagination import TenxytePagination
from ..filters import apply_permission_filters, apply_role_filters

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les permissions",
        description="Retourne la liste paginée de toutes les permissions disponibles.",
        parameters=[
            OpenApiParameter('search', str, description='Recherche dans code et name'),
            OpenApiParameter('parent', str, description='Filtrer par parent (null=racines, id=enfants)'),
            OpenApiParameter('ordering', str, description='Tri: code, name, created_at (prefix - pour DESC)'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: PermissionSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Créer une permission",
        description="Crée une nouvelle permission. "
                    "Le code doit être unique et structuré (ex: `users.view`). "
                    "Peut être rattaché à une permission parente via `parent_code`.",
        request=PermissionSerializer,
        responses={201: PermissionSerializer, 400: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='create_standalone_permission',
                summary='Permission globale',
                description='Création d\'une permission principale sans parent.',
                request_only=True,
                value={
                    'code': 'reports.view',
                    'name': 'Consulter les rapports',
                    'description': 'Permet de voir tous les rapports d\'activité.'
                }
            ),
            OpenApiExample(
                name='create_child_permission',
                summary='Permission enfant',
                description='Création d\'une sous-permission rattachée à une permission parente (via parent_code).',
                request_only=True,
                value={
                    'code': 'reports.export',
                    'name': 'Exporter les rapports',
                    'description': 'Permet d\'exporter les rapports au format PDF ou CSV.',
                    'parent_code': 'reports.view'
                }
            ),
            OpenApiExample(
                name='create_success',
                summary='Permission créée',
                response_only=True,
                status_codes=['201'],
                value={
                    'id': '10',
                    'code': 'reports.export',
                    'name': 'Exporter les rapports',
                    'description': 'Permet d\'exporter les rapports au format PDF ou CSV.',
                    'parent': {
                        'id': '9',
                        'code': 'reports.view'
                    },
                    'children': [],
                    'created_at': '2024-01-20T10:00:00Z'
                }
            )
        ]
    )
)
class PermissionListView(APIView):
    """
    GET {API_PREFIX}/auth/permissions/
    Liste toutes les permissions (paginé + filtres)
    """
    pagination_class = TenxytePagination

    @require_permission('permissions.view')
    def get(self, request):
        queryset = Permission.objects.all()
        queryset = apply_permission_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = PermissionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = PermissionSerializer(queryset, many=True)
        return Response(serializer.data)

    @require_permission('permissions.create')
    def post(self, request):
        serializer = PermissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Détails d'une permission",
        description="Récupère les informations d'une permission par son ID.",
        responses={200: PermissionSerializer, 404: OpenApiTypes.OBJECT}
    ),
    put=extend_schema(
        tags=['RBAC'],
        summary="Modifier une permission",
        description="Met à jour les informations d'une permission. "
                    "Seuls le nom et la description sont généralement modifiés, "
                    "le code servant d'identifiant technique immuable.",
        request=PermissionSerializer,
        responses={200: PermissionSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='update_permission',
                summary='Mise à jour d\'une permission',
                description='Modifier le nom et la description d\'une permission existante.',
                request_only=True,
                value={
                    'name': 'Consulter tous les rapports (Admin)',
                    'description': 'Permet de voir les rapports de toutes les organisations.'
                }
            ),
            OpenApiExample(
                name='update_success',
                summary='Mise à jour réussie',
                response_only=True,
                status_codes=['200'],
                value={
                    'id': '9',
                    'code': 'reports.view',
                    'name': 'Consulter tous les rapports (Admin)',
                    'description': 'Permet de voir les rapports de toutes les organisations.',
                    'parent': None,
                    'children': [
                        {
                            'id': '10',
                            'code': 'reports.export',
                            'name': 'Exporter les rapports'
                        }
                    ],
                    'created_at': '2024-01-20T10:00:00Z'
                }
            ),
            OpenApiExample(
                name='permission_not_found',
                summary='Permission introuvable',
                response_only=True,
                status_codes=['404'],
                value={
                    'error': 'Permission not found',
                    'code': 'NOT_FOUND'
                }
            )
        ]
    ),
    delete=extend_schema(
        tags=['RBAC'],
        summary="Supprimer une permission",
        description="Supprime définitivement une permission.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class PermissionDetailView(APIView):
    """
    GET/PUT/DELETE {API_PREFIX}/auth/permissions/<permission_id>/
    """

    @require_permission('permissions.view')
    def get(self, request, permission_id):
        try:
            permission = Permission.objects.get(id=permission_id)
            return Response(PermissionSerializer(permission).data)
        except Permission.DoesNotExist:
            return Response({
                'error': 'Permission not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

    @require_permission('permissions.update')
    def put(self, request, permission_id):
        try:
            permission = Permission.objects.get(id=permission_id)
        except Permission.DoesNotExist:
            return Response({
                'error': 'Permission not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = PermissionSerializer(permission, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)

    @require_permission('permissions.delete')
    def delete(self, request, permission_id):
        try:
            permission = Permission.objects.get(id=permission_id)
            permission.delete()
            return Response({'message': 'Permission deleted'}, status=status.HTTP_200_OK)
        except Permission.DoesNotExist:
            return Response({
                'error': 'Permission not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les rôles",
        description="Retourne la liste paginée de tous les rôles disponibles.",
        parameters=[
            OpenApiParameter(
                name='X-Org-Slug',
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation pour le filtrage contextuel"
            ),
            OpenApiParameter('search', str, description='Recherche dans code et name'),
            OpenApiParameter('is_default', bool, description='Filtrer par is_default'),
            OpenApiParameter('ordering', str, description='Tri: code, name, is_default, created_at'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: RoleListSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Créer un rôle",
        description="Crée un nouveau rôle. "
                    "Vous pouvez assigner des permissions immédiatement via la liste `permission_codes`.",
        request=RoleSerializer,
        responses={201: RoleSerializer, 400: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='create_role',
                summary='Rôle avec permissions',
                description='Création d\'un rôle "Support Technique" incluant des permissions initiales.',
                request_only=True,
                value={
                    'code': 'tech_support',
                    'name': 'Support Technique',
                    'description': 'Accès en lecture aux utilisateurs et logs.',
                    'permission_codes': ['users.view', 'logs.view'],
                    'is_default': False
                }
            ),
            OpenApiExample(
                name='create_success',
                summary='Création réussie',
                response_only=True,
                status_codes=['201'],
                value={
                    'id': '19',
                    'code': 'tech_support',
                    'name': 'Support Technique',
                    'description': 'Accès en lecture aux utilisateurs et logs.',
                    'permissions': [
                        {
                            'id': '5',
                            'code': 'users.view',
                            'name': 'Lister les utilisateurs'
                        },
                        {
                            'id': '12',
                            'code': 'logs.view',
                            'name': 'Consulter les logs'
                        }
                    ],
                    'is_default': False,
                    'created_at': '2024-01-20T10:00:00Z',
                    'updated_at': '2024-01-20T10:00:00Z'
                }
            )
        ]
    )
)
class RoleListView(APIView):
    """
    GET {API_PREFIX}/auth/roles/
    Liste tous les rôles (paginé + filtres)
    """
    pagination_class = TenxytePagination

    @require_permission('roles.view')
    def get(self, request):
        queryset = Role.objects.all()
        queryset = apply_role_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = RoleListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = RoleListSerializer(queryset, many=True)
        return Response(serializer.data)

    @require_permission('roles.create')
    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Détails d'un rôle",
        description="Récupère les informations d'un rôle par son ID.",
        responses={200: RoleSerializer, 404: OpenApiTypes.OBJECT}
    ),
    put=extend_schema(
        tags=['RBAC'],
        summary="Modifier un rôle",
        description="Met à jour les informations d'un rôle. "
                    "Vous pouvez modifier le nom, la description, le statut par défaut, "
                    "et remplacer toutes les permissions assignées via `permission_codes`.",
        request=RoleSerializer,
        responses={200: RoleSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='update_role',
                summary='Mise à jour d\'un rôle',
                description='Renomme le rôle et met à jour ses permissions.',
                request_only=True,
                value={
                    'name': 'Support Technique (Niveau 2)',
                    'description': 'Accès étendu pour la résolution d\'incidents.',
                    'permission_codes': ['users.view', 'logs.view', 'logs.export'],
                    'is_default': False
                }
            ),
            OpenApiExample(
                name='update_success',
                summary='Mise à jour réussie',
                response_only=True,
                status_codes=['200'],
                value={
                    'id': '19',
                    'code': 'tech_support',
                    'name': 'Support Technique (Niveau 2)',
                    'description': 'Accès étendu pour la résolution d\'incidents.',
                    'permissions': [
                        {
                            'id': '5',
                            'code': 'users.view',
                            'name': 'Lister les utilisateurs'
                        },
                        {
                            'id': '12',
                            'code': 'logs.view',
                            'name': 'Consulter les logs'
                        },
                        {
                            'id': '13',
                            'code': 'logs.export',
                            'name': 'Exporter les logs'
                        }
                    ],
                    'is_default': False,
                    'created_at': '2024-01-20T10:00:00Z',
                    'updated_at': '2024-02-15T14:30:00Z'
                }
            ),
            OpenApiExample(
                name='role_not_found',
                summary='Rôle introuvable',
                response_only=True,
                status_codes=['404'],
                value={
                    'error': 'Role not found',
                    'code': 'NOT_FOUND'
                }
            )
        ]
    ),
    delete=extend_schema(
        tags=['RBAC'],
        summary="Supprimer un rôle",
        description="Supprime définitivement un rôle.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class RoleDetailView(APIView):
    """
    GET/PUT/DELETE {API_PREFIX}/auth/roles/<role_id>/
    """

    @require_permission('roles.view')
    def get(self, request, role_id):
        try:
            role = Role.objects.get(id=role_id)
            return Response(RoleSerializer(role).data)
        except Role.DoesNotExist:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

    @require_permission('roles.update')
    def put(self, request, role_id):
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = RoleSerializer(role, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)

    @require_permission('roles.delete')
    def delete(self, request, role_id):
        try:
            role = Role.objects.get(id=role_id)
            role.delete()
            return Response({'message': 'Role deleted'}, status=status.HTTP_200_OK)
        except Role.DoesNotExist:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les permissions d'un rôle",
        description="Récupère toutes les permissions assignées à un rôle.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Ajouter des permissions à un rôle",
        description="Ajoute une ou plusieurs permissions à un rôle existant. "
                    "Seuls les codes de permissions sont requis.",
        request=ManageRolePermissionsSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='add_permissions_request',
                summary='Ajouter des permissions',
                description='Ajoute deux permissions spécifiques au rôle.',
                request_only=True,
                value={
                    'permission_codes': ['users.create', 'users.update']
                }
            ),
            OpenApiExample(
                name='add_permissions_success',
                summary='Permissions ajoutées',
                response_only=True,
                status_codes=['200'],
                value={
                    'message': '2 permission(s) added',
                    'added': ['users.create', 'users.update'],
                    'role_code': 'tech_support',
                    'permissions': [
                        {'id': '5', 'code': 'users.view', 'name': 'Lister les utilisateurs'},
                        {'id': '6', 'code': 'users.create', 'name': 'Créer un utilisateur'},
                        {'id': '7', 'code': 'users.update', 'name': 'Modifier un utilisateur'}
                    ]
                }
            ),
            OpenApiExample(
                name='permissions_already_assigned',
                summary='Certaines déjà assignées',
                response_only=True,
                status_codes=['200'],
                value={
                    'message': '1 permission(s) added',
                    'added': ['users.update'],
                    'already_assigned': ['users.create'],
                    'role_code': 'tech_support',
                    'permissions': [
                        {'id': '5', 'code': 'users.view', 'name': 'Lister les utilisateurs'},
                        {'id': '6', 'code': 'users.create', 'name': 'Créer un utilisateur'},
                        {'id': '7', 'code': 'users.update', 'name': 'Modifier un utilisateur'}
                    ]
                }
            ),
            OpenApiExample(
                name='permissions_not_found',
                summary='Permissions introuvables',
                response_only=True,
                status_codes=['400'],
                value={
                    'error': 'Some permissions not found',
                    'code': 'PERMISSIONS_NOT_FOUND',
                    'not_found': ['users.delete_all']
                }
            )
        ]
    ),
    delete=extend_schema(
        tags=['RBAC'],
        summary="Retirer des permissions d'un rôle",
        description="Retire une ou plusieurs permissions d'un rôle existant.",
        request=ManageRolePermissionsSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class RolePermissionsView(APIView):
    """
    GET/POST/DELETE {API_PREFIX}/auth/roles/<role_id>/permissions/
    Gère les permissions d'un rôle
    """

    def _get_role(self, role_id):
        try:
            return Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return None

    def _safe_add_permissions(self, role, permissions):
        """Add permissions to a role, with MongoDB-compatible fallback."""
        try:
            role.permissions.add(*permissions)
        except TypeError:
            for perm in permissions:
                try:
                    role.permissions.add(perm)
                except TypeError:
                    pass

    def _safe_remove_permissions(self, role, permissions):
        """Remove permissions from a role, with MongoDB-compatible fallback."""
        try:
            role.permissions.remove(*permissions)
        except TypeError:
            # MongoDB: remove() fails due to deletion collector issue
            # Fallback: delete through-table entries directly, bypassing collector
            through = role.permissions.through
            source = role.permissions.source_field_name
            target = role.permissions.target_field_name
            remove_pks = [p.pk for p in permissions]
            db = role._state.db or 'default'
            through.objects.using(db).filter(**{
                source: role.pk,
                f'{target}__in': remove_pks,
            })._raw_delete(db)

    @require_permission('roles.manage_permissions')
    def get(self, request, role_id):
        role = self._get_role(role_id)
        if not role:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'role_id': str(role.id),
            'role_code': role.code,
            'permissions': PermissionSerializer(role.permissions.all(), many=True).data
        })

    @require_permission('roles.manage_permissions')
    def post(self, request, role_id):
        """Ajoute des permissions au rôle"""
        role = self._get_role(role_id)
        if not role:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ManageRolePermissionsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        permission_codes = serializer.validated_data['permission_codes']
        permissions = Permission.objects.filter(code__in=permission_codes)
        found_codes = set(permissions.values_list('code', flat=True))

        not_found = set(permission_codes) - found_codes
        if not_found:
            return Response({
                'error': 'Some permissions not found',
                'code': 'PERMISSIONS_NOT_FOUND',
                'not_found': list(not_found)
            }, status=status.HTTP_400_BAD_REQUEST)

        existing_codes = set(role.permissions.filter(
            code__in=permission_codes
        ).values_list('code', flat=True))
        new_permissions = [p for p in permissions if p.code not in existing_codes]

        if new_permissions:
            self._safe_add_permissions(role, new_permissions)

        response_data = {
            'message': f'{len(new_permissions)} permission(s) added',
            'added': [p.code for p in new_permissions],
            'role_code': role.code,
            'permissions': PermissionSerializer(role.permissions.all(), many=True).data
        }
        if existing_codes:
            response_data['already_assigned'] = list(existing_codes)

        return Response(response_data)

    @require_permission('roles.manage_permissions')
    def delete(self, request, role_id):
        """Retire des permissions du rôle"""
        role = self._get_role(role_id)
        if not role:
            return Response({
                'error': 'Role not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ManageRolePermissionsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        permission_codes = serializer.validated_data['permission_codes']
        permissions = Permission.objects.filter(code__in=permission_codes)
        found_codes = set(permissions.values_list('code', flat=True))

        not_found = set(permission_codes) - found_codes
        if not_found:
            return Response({
                'error': 'Some permissions not found',
                'code': 'PERMISSIONS_NOT_FOUND',
                'not_found': list(not_found)
            }, status=status.HTTP_400_BAD_REQUEST)

        assigned_codes = set(role.permissions.filter(
            code__in=permission_codes
        ).values_list('code', flat=True))
        to_remove = [p for p in permissions if p.code in assigned_codes]
        not_removed = [p.code for p in permissions if p.code not in assigned_codes]

        if to_remove:
            self._safe_remove_permissions(role, to_remove)

        response_data = {
            'message': f'{len(to_remove)} permission(s) removed',
            'removed': [p.code for p in to_remove],
            'role_code': role.code,
            'permissions': PermissionSerializer(role.permissions.all(), many=True).data
        }
        if not_removed:
            response_data['not_removed'] = not_removed

        return Response(response_data)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les rôles d'un utilisateur",
        description="Récupère tous les rôles assignés à un utilisateur.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Assigner un rôle",
        description="Ajoute un rôle à un utilisateur à l'aide de son `role_code` "
                    "(ex: `admin`, `tech_support`).",
        request=AssignRoleSerializer,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='assign_role_request',
                summary='Assigner un rôle',
                description='Affecter le rôle "Support Technique" à l\'utilisateur.',
                request_only=True,
                value={
                    'role_code': 'tech_support'
                }
            ),
            OpenApiExample(
                name='assign_role_success',
                summary='Assignation réussie',
                response_only=True,
                status_codes=['200'],
                value={
                    'message': 'Role assigned',
                    'roles': ['tech_support', 'default_user']
                }
            ),
            OpenApiExample(
                name='role_not_found',
                summary='Rôle introuvable',
                response_only=True,
                status_codes=['404'],
                value={
                    'error': 'Role not found',
                    'code': 'ROLE_NOT_FOUND'
                }
            )
        ]
    ),
    delete=extend_schema(
        tags=['RBAC'],
        summary="Retirer un rôle",
        description="Retire un rôle d'un utilisateur. Le role_code doit être passé en query parameter.",
        parameters=[
            OpenApiParameter(
                name='role_code',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Le code du rôle à retirer',
                required=True
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class UserRolesView(APIView):
    """
    GET {API_PREFIX}/auth/users/<user_id>/roles/
    Gère les rôles d'un utilisateur
    """

    @require_permission('users.roles.view')
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            roles = user.roles.all()
            return Response({
                'user_id': str(user.id),
                'roles': RoleListSerializer(roles, many=True).data
            })
        except User.DoesNotExist:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

    @require_permission('users.roles.assign')
    def post(self, request, user_id):
        """Ajoute un rôle à l'utilisateur"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = AssignRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.assign_role(serializer.validated_data['role_code']):
            return Response({
                'message': 'Role assigned',
                'roles': user.get_all_roles()
            })
        else:
            return Response({
                'error': 'Role not found',
                'code': 'ROLE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

    @require_permission('users.roles.remove')
    def delete(self, request, user_id):
        """Retire un rôle à l'utilisateur"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        role_code = request.query_params.get('role_code')
        if not role_code:
            return Response({
                'error': 'role_code query parameter required',
                'code': 'MISSING_PARAM'
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.remove_role(role_code):
            return Response({
                'message': 'Role removed',
                'roles': user.get_all_roles()
            })
        else:
            return Response({
                'error': 'Role not found',
                'code': 'ROLE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les permissions directes d'un utilisateur",
        description="Récupère toutes les permissions assignées directement à un utilisateur (hors rôles).",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Ajouter des permissions directes à un utilisateur",
        description="Ajoute une ou plusieurs permissions directement à un utilisateur.",
        request=ManageRolePermissionsSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name='add_direct_permissions_request',
                summary='Ajouter des permissions directes',
                description='Ajoute deux permissions spécifiques à l\'utilisateur.',
                request_only=True,
                value={
                    'permission_codes': ['users.view', 'reports.export']
                }
            ),
            OpenApiExample(
                name='add_direct_permissions_success',
                summary='Succès de l\'ajout',
                description='Les permissions ont été ajoutées avec succès.',
                response_only=True,
                status_codes=['200'],
                value={
                    'status': 'Permissions issues successfully added',
                    'direct_permissions': ['users.view', 'reports.export']
                }
            ),
            OpenApiExample(
                name='user_not_found',
                summary='Utilisateur introuvable',
                description='L\'ID utilisateur fourni n\'existe pas.',
                response_only=True,
                status_codes=['404'],
                value={
                    'error': 'User not found',
                    'code': 'NOT_FOUND'
                }
            )
        ]
    ),
    delete=extend_schema(
        tags=['RBAC'],
        summary="Retirer des permissions directes d'un utilisateur",
        description="Retire une ou plusieurs permissions directes d'un utilisateur.",
        request=ManageRolePermissionsSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class UserDirectPermissionsView(APIView):
    """
    GET/POST/DELETE {API_PREFIX}/auth/users/<user_id>/permissions/
    Gère les permissions directes d'un utilisateur
    """

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def _safe_add_permissions(self, user, permissions):
        """Add direct permissions to a user, with MongoDB-compatible fallback."""
        try:
            user.direct_permissions.add(*permissions)
        except TypeError:
            for perm in permissions:
                try:
                    user.direct_permissions.add(perm)
                except TypeError:
                    pass

    def _safe_remove_permissions(self, user, permissions):
        """Remove direct permissions from a user, with MongoDB-compatible fallback."""
        try:
            user.direct_permissions.remove(*permissions)
        except TypeError:
            through = user.direct_permissions.through
            source = user.direct_permissions.source_field_name
            target = user.direct_permissions.target_field_name
            remove_pks = [p.pk for p in permissions]
            db = user._state.db or 'default'
            through.objects.using(db).filter(**{
                source: user.pk,
                f'{target}__in': remove_pks,
            })._raw_delete(db)

    @require_permission('users.permissions.view')
    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'user_id': str(user.id),
            'email': user.email,
            'direct_permissions': PermissionSerializer(
                user.direct_permissions.all(), many=True
            ).data,
            'all_permissions': user.get_all_permissions()
        })

    @require_permission('users.permissions.assign')
    def post(self, request, user_id):
        """Ajoute des permissions directes à l'utilisateur"""
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ManageRolePermissionsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        permission_codes = serializer.validated_data['permission_codes']
        permissions = Permission.objects.filter(code__in=permission_codes)
        found_codes = set(permissions.values_list('code', flat=True))

        not_found = set(permission_codes) - found_codes
        if not_found:
            return Response({
                'error': 'Some permissions not found',
                'code': 'PERMISSIONS_NOT_FOUND',
                'not_found': list(not_found)
            }, status=status.HTTP_400_BAD_REQUEST)

        existing_codes = set(user.direct_permissions.filter(
            code__in=permission_codes
        ).values_list('code', flat=True))
        new_permissions = [p for p in permissions if p.code not in existing_codes]

        if new_permissions:
            self._safe_add_permissions(user, new_permissions)

        response_data = {
            'message': f'{len(new_permissions)} permission(s) added',
            'added': [p.code for p in new_permissions],
            'user_id': str(user.id),
            'direct_permissions': PermissionSerializer(
                user.direct_permissions.all(), many=True
            ).data
        }
        if existing_codes:
            response_data['already_assigned'] = list(existing_codes)

        return Response(response_data)

    @require_permission('users.permissions.remove')
    def delete(self, request, user_id):
        """Retire des permissions directes de l'utilisateur"""
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ManageRolePermissionsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        permission_codes = serializer.validated_data['permission_codes']
        permissions = Permission.objects.filter(code__in=permission_codes)
        found_codes = set(permissions.values_list('code', flat=True))

        not_found = set(permission_codes) - found_codes
        if not_found:
            return Response({
                'error': 'Some permissions not found',
                'code': 'PERMISSIONS_NOT_FOUND',
                'not_found': list(not_found)
            }, status=status.HTTP_400_BAD_REQUEST)

        assigned_codes = set(user.direct_permissions.filter(
            code__in=permission_codes
        ).values_list('code', flat=True))
        to_remove = [p for p in permissions if p.code in assigned_codes]
        not_removed = [p.code for p in permissions if p.code not in assigned_codes]

        if to_remove:
            self._safe_remove_permissions(user, to_remove)

        response_data = {
            'message': f'{len(to_remove)} permission(s) removed',
            'removed': [p.code for p in to_remove],
            'user_id': str(user.id),
            'direct_permissions': PermissionSerializer(
                user.direct_permissions.all(), many=True
            ).data
        }
        if not_removed:
            response_data['not_removed'] = not_removed

        return Response(response_data)
