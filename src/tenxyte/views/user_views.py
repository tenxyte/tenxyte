from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers import UserSerializer
from ..serializers.user_admin_serializers import (
    AdminUserListSerializer, AdminUserDetailSerializer,
    AdminUserUpdateSerializer, BanUserSerializer, LockUserSerializer,
)
from ..models import get_user_model
from ..decorators import require_jwt, require_permission
from ..pagination import TenxytePagination
from ..filters import apply_user_filters

User = get_user_model()


class MeView(APIView):
    """
    GET /api/auth/me/
    Récupérer le profil de l'utilisateur connecté
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User'],
        summary="Récupérer mon profil",
        description="Retourne les informations de l'utilisateur connecté.",
        responses={200: UserSerializer}
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=['User'],
        summary="Modifier mon profil",
        description="Met à jour les informations de l'utilisateur connecté.",
        request=UserSerializer,
        responses={200: UserSerializer, 400: OpenApiTypes.OBJECT}
    )
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)


class MyRolesView(APIView):
    """
    GET /api/auth/me/roles/
    Récupère les rôles et permissions de l'utilisateur connecté
    """

    @extend_schema(
        tags=['User'],
        summary="Récupérer mes rôles et permissions",
        description="Retourne la liste des rôles et permissions de l'utilisateur connecté.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def get(self, request):
        return Response({
            'roles': request.user.get_all_roles(),
            'permissions': request.user.get_all_permissions()
        })


# =============================================================================
# Admin User Management
# =============================================================================


class UserListView(APIView):
    """
    GET /api/auth/admin/users/
    Liste tous les utilisateurs (admin, paginé + filtres)
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - Users'],
        summary="Lister les utilisateurs",
        description="Retourne la liste paginée de tous les utilisateurs. Réservé aux admins.",
        parameters=[
            OpenApiParameter('search', str, description='Recherche dans email, first_name, last_name'),
            OpenApiParameter('is_active', bool, description='Filtrer par statut actif'),
            OpenApiParameter('is_locked', bool, description='Filtrer par compte verrouillé'),
            OpenApiParameter('is_banned', bool, description='Filtrer par compte banni'),
            OpenApiParameter('is_deleted', bool, description='Filtrer par compte supprimé'),
            OpenApiParameter('is_email_verified', bool, description='Filtrer par email vérifié'),
            OpenApiParameter('is_2fa_enabled', bool, description='Filtrer par 2FA activé'),
            OpenApiParameter('role', str, description='Filtrer par code de rôle'),
            OpenApiParameter('date_from', str, description='Créé après (YYYY-MM-DD)'),
            OpenApiParameter('date_to', str, description='Créé avant (YYYY-MM-DD)'),
            OpenApiParameter('ordering', str, description='Tri: email, created_at, last_login, first_name'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: AdminUserListSerializer(many=True)}
    )
    @require_permission('users.view')
    def get(self, request):
        queryset = User.objects.all()
        queryset = apply_user_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = AdminUserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminUserListSerializer(queryset, many=True)
        return Response(serializer.data)


class UserDetailView(APIView):
    """
    GET /api/auth/admin/users/<user_id>/
    PATCH /api/auth/admin/users/<user_id>/
    DELETE /api/auth/admin/users/<user_id>/
    """

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @extend_schema(
        tags=['Admin - Users'],
        summary="Détails d'un utilisateur",
        description="Récupère les informations complètes d'un utilisateur.",
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.view')
    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserDetailSerializer(user).data)

    @extend_schema(
        tags=['Admin - Users'],
        summary="Modifier un utilisateur (admin)",
        description="Met à jour les informations d'un utilisateur. Réservé aux admins.",
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserDetailSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.update')
    def patch(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error', 'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        for attr, value in serializer.validated_data.items():
            setattr(user, attr, value)
        user.save()

        return Response(AdminUserDetailSerializer(user).data)

    @extend_schema(
        tags=['Admin - Users'],
        summary="Supprimer un utilisateur (soft delete)",
        description="Suppression logique d'un utilisateur (anonymisation RGPD).",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.delete')
    def delete(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.is_deleted:
            return Response({
                'error': 'User already deleted', 'code': 'ALREADY_DELETED'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.soft_delete()
        return Response({
            'message': 'User soft-deleted successfully',
            'user_id': str(user.id)
        })


class UserBanView(APIView):
    """
    POST /api/auth/admin/users/<user_id>/ban/
    """

    @extend_schema(
        tags=['Admin - Users'],
        summary="Bannir un utilisateur",
        description="Bannit un utilisateur de manière permanente. Nécessite la permission users.ban.",
        request=BanUserSerializer,
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.ban')
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.is_banned:
            return Response({
                'error': 'User already banned', 'code': 'ALREADY_BANNED'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_banned = True
        user.is_active = False
        user.save()

        return Response({
            'message': 'User banned successfully',
            'user': AdminUserDetailSerializer(user).data
        })


class UserUnbanView(APIView):
    """
    POST /api/auth/admin/users/<user_id>/unban/
    """

    @extend_schema(
        tags=['Admin - Users'],
        summary="Débannir un utilisateur",
        description="Lève le bannissement d'un utilisateur.",
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.ban')
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if not user.is_banned:
            return Response({
                'error': 'User is not banned', 'code': 'NOT_BANNED'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_banned = False
        user.is_active = True
        user.save()

        return Response({
            'message': 'User unbanned successfully',
            'user': AdminUserDetailSerializer(user).data
        })


class UserLockView(APIView):
    """
    POST /api/auth/admin/users/<user_id>/lock/
    """

    @extend_schema(
        tags=['Admin - Users'],
        summary="Verrouiller un compte",
        description="Verrouille temporairement un compte utilisateur.",
        request=LockUserSerializer,
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.lock')
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.is_locked:
            return Response({
                'error': 'User already locked', 'code': 'ALREADY_LOCKED'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = LockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        duration = serializer.validated_data.get('duration_minutes', 30)
        user.lock_account(duration_minutes=duration)

        return Response({
            'message': f'User locked for {duration} minutes',
            'user': AdminUserDetailSerializer(user).data
        })


class UserUnlockView(APIView):
    """
    POST /api/auth/admin/users/<user_id>/unlock/
    """

    @extend_schema(
        tags=['Admin - Users'],
        summary="Déverrouiller un compte",
        description="Déverrouille un compte utilisateur.",
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('users.lock')
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if not user.is_locked:
            return Response({
                'error': 'User is not locked', 'code': 'NOT_LOCKED'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.unlock_account()

        return Response({
            'message': 'User unlocked successfully',
            'user': AdminUserDetailSerializer(user).data
        })
