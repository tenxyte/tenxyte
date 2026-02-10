from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    PermissionSerializer, RoleSerializer, RoleListSerializer, AssignRoleSerializer
)
from ..models import get_user_model, get_role_model, get_permission_model
from ..decorators import require_permission

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()


@extend_schema_view(
    get=extend_schema(
        tags=['RBAC'],
        summary="Lister les permissions",
        description="Retourne la liste de toutes les permissions disponibles.",
        responses={200: PermissionSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Créer une permission",
        description="Crée une nouvelle permission.",
        request=PermissionSerializer,
        responses={201: PermissionSerializer, 400: OpenApiTypes.OBJECT}
    )
)
class PermissionListView(APIView):
    """
    GET /api/auth/permissions/
    Liste toutes les permissions
    """

    @require_permission('permissions.view')
    def get(self, request):
        permissions = Permission.objects.all()
        serializer = PermissionSerializer(permissions, many=True)
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
        description="Met à jour les informations d'une permission.",
        request=PermissionSerializer,
        responses={200: PermissionSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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
    GET/PUT/DELETE /api/auth/permissions/<permission_id>/
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
        description="Retourne la liste de tous les rôles disponibles.",
        responses={200: RoleListSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Créer un rôle",
        description="Crée un nouveau rôle avec les permissions spécifiées.",
        request=RoleSerializer,
        responses={201: RoleSerializer, 400: OpenApiTypes.OBJECT}
    )
)
class RoleListView(APIView):
    """
    GET /api/auth/roles/
    Liste tous les rôles
    """

    @require_permission('roles.view')
    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleListSerializer(roles, many=True)
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
        description="Met à jour les informations d'un rôle.",
        request=RoleSerializer,
        responses={200: RoleSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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
    GET/PUT/DELETE /api/auth/roles/<role_id>/
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
        summary="Lister les rôles d'un utilisateur",
        description="Récupère tous les rôles assignés à un utilisateur.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    ),
    post=extend_schema(
        tags=['RBAC'],
        summary="Assigner un rôle",
        description="Ajoute un rôle à un utilisateur.",
        request=AssignRoleSerializer,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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
    GET /api/auth/users/<user_id>/roles/
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
