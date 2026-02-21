from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    ApplicationSerializer, ApplicationCreateSerializer, ApplicationUpdateSerializer
)
from ..models import get_application_model
from ..decorators import require_permission
from ..pagination import TenxytePagination
from ..filters import apply_application_filters
Application = get_application_model()


@extend_schema_view(
    get=extend_schema(
        tags=['Applications'],
        summary="Lister les applications",
        description="Retourne la liste paginée de toutes les applications enregistrées.",
        parameters=[
            OpenApiParameter('search', str, description='Recherche dans name et description'),
            OpenApiParameter('is_active', bool, description='Filtrer par statut actif'),
            OpenApiParameter('ordering', str, description='Tri: name, is_active, created_at, updated_at'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: ApplicationSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['Applications'],
        summary="Créer une application",
        description="Crée une nouvelle application et retourne les credentials. **Attention:** le secret n'est affiché qu'une seule fois.",
        request=ApplicationCreateSerializer,
        responses={201: OpenApiTypes.OBJECT}
    )
)
class ApplicationListView(APIView):
    """
    GET /api/v1/auth/applications/
    Liste toutes les applications (paginé + filtres)

    POST /api/v1/auth/applications/
    Crée une nouvelle application
    """
    pagination_class = TenxytePagination

    @require_permission('applications.view')
    def get(self, request):
        queryset = Application.objects.all()
        queryset = apply_application_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ApplicationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ApplicationSerializer(queryset, many=True)
        return Response(serializer.data)

    @require_permission('applications.create')
    def post(self, request):
        serializer = ApplicationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        app, raw_secret = Application.create_application(
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', '')
        )

        return Response({
            'message': 'Application created successfully',
            'application': ApplicationSerializer(app).data,
            'credentials': {
                'access_key': app.access_key,
                'access_secret': raw_secret
            },
            'warning': 'Save the access_secret now! It will never be shown again.'
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=['Applications'],
        summary="Détails d'une application",
        description="Récupère les informations d'une application par son ID.",
        responses={200: ApplicationSerializer, 404: OpenApiTypes.OBJECT}
    ),
    put=extend_schema(
        tags=['Applications'],
        summary="Modifier une application",
        description="Met à jour les informations d'une application.",
        request=ApplicationUpdateSerializer,
        responses={200: ApplicationSerializer, 404: OpenApiTypes.OBJECT}
    ),
    delete=extend_schema(
        tags=['Applications'],
        summary="Supprimer une application",
        description="Supprime définitivement une application.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
)
class ApplicationDetailView(APIView):
    """
    GET /api/v1/auth/applications/<app_id>/
    Récupère les détails d'une application

    PUT /api/v1/auth/applications/<app_id>/
    Met à jour une application

    DELETE /api/v1/auth/applications/<app_id>/
    Supprime une application
    """

    @require_permission('applications.view')
    def get(self, request, app_id):
        try:
            app = Application.objects.get(id=app_id)
            return Response(ApplicationSerializer(app).data)
        except Application.DoesNotExist:
            return Response({
                'error': 'Application not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

    @require_permission('applications.update')
    def put(self, request, app_id):
        try:
            app = Application.objects.get(id=app_id)
        except Application.DoesNotExist:
            return Response({
                'error': 'Application not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mise à jour des champs
        for field, value in serializer.validated_data.items():
            setattr(app, field, value)
        app.save()

        return Response(ApplicationSerializer(app).data)

    @require_permission('applications.delete')
    def delete(self, request, app_id):
        try:
            app = Application.objects.get(id=app_id)
            app_name = app.name
            app.delete()
            return Response({
                'message': f'Application "{app_name}" deleted successfully'
            })
        except Application.DoesNotExist:
            return Response({
                'error': 'Application not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)


class ApplicationRegenerateView(APIView):
    """
    POST /api/v1/auth/applications/<app_id>/regenerate/
    Régénère les credentials d'une application
    """

    @extend_schema(
        tags=['Applications'],
        summary="Régénérer les credentials",
        description="Régénère l'access_key et l'access_secret d'une application. **Attention:** les anciens credentials seront invalidés.",
        request=None,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('applications.regenerate')
    def post(self, request, app_id):
        try:
            app = Application.objects.get(id=app_id)
        except Application.DoesNotExist:
            return Response({
                'error': 'Application not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        credentials = app.regenerate_credentials()

        return Response({
            'message': 'Credentials regenerated successfully',
            'application': ApplicationSerializer(app).data,
            'credentials': credentials,
            'warning': 'Save the access_secret now! It will never be shown again.'
        })
