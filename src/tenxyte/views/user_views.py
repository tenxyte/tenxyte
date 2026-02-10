from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..serializers import UserSerializer
from ..decorators import require_jwt


class MeView(APIView):
    """
    GET /api/auth/me/
    Récupérer le profil de l'utilisateur connecté
    """

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
