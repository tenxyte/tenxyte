from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
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
        description="Crée une nouvelle application et retourne les credentials. "
                    "**Attention:** le secret n'est affiché qu'une seule fois à la création. "
                    "Stockez-le sécuritairement. Les secrets peuvent être régénérés via "
                    "l'endpoint dédié. L'application est inactive par défaut.",
        request=ApplicationCreateSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'client_id': {'type': 'string'},
                    'client_secret': {'type': 'string'},
                    'is_active': {'type': 'boolean'},
                    'created_at': {'type': 'string', 'format': 'date-time'},
                    'secret_rotation_warning': {
                        'type': 'string',
                        'description': 'Avertissement sur la sauvegarde du secret'
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name='create_app_success',
                summary='Application créée avec secret',
                value={
                    'name': 'Mobile App v2',
                    'description': 'Application mobile iOS/Android',
                    'redirect_uris': ['myapp://callback', 'https://app.example.com/auth']
                }
            ),
            OpenApiExample(
                name='secret_warning',
                summary='Avertissement secret',
                value={
                    'client_secret': 'sk_live_1234567890abcdef...',
                    'secret_rotation_warning': 'Save this secret securely. It will not be shown again.'
                }
            )
        ]
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
        description="Récupère les informations d'une application par son ID. "
                    "Inclut les statistiques d'utilisation et le statut actif. "
                    "Le secret n'est jamais affiché pour des raisons de sécurité.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'access_key': {'type': 'string'},
                    'is_active': {'type': 'boolean'},
                    'created_at': {'type': 'string', 'format': 'date-time'},
                    'updated_at': {'type': 'string', 'format': 'date-time'},
                    'last_used_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'usage_stats': {
                        'type': 'object',
                        'properties': {
                            'total_requests': {'type': 'integer'},
                            'requests_this_month': {'type': 'integer'},
                            'last_request': {'type': 'string', 'format': 'date-time', 'nullable': True}
                        }
                    }
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        }
    ),
    put=extend_schema(
        tags=['Applications'],
        summary="Modifier une application",
        description="Met à jour les informations d'une application. "
                    "Le secret ne peut pas être modifié (utilisez l'endpoint de régénération).",
        request=ApplicationUpdateSerializer,
        responses={200: ApplicationSerializer, 404: OpenApiTypes.OBJECT}
    ),
    patch=extend_schema(
        tags=['Applications'],
        summary="Basculer le statut actif",
        description="Active ou désactive une application. "
                    "Une application désactivée ne peut plus faire d'appels API. "
                    "Utile pour la maintenance ou en cas de compromission.",
        request={
            'type': 'object',
            'properties': {
                'is_active': {
                    'type': 'boolean',
                    'description': 'Nouveau statut actif de l\'application'
                }
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'is_active': {'type': 'boolean'},
                    'updated_at': {'type': 'string', 'format': 'date-time'},
                    'message': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='deactivate_app',
                summary='Désactiver application',
                value={
                    'is_active': False
                }
            ),
            OpenApiExample(
                name='activate_app',
                summary='Activer application',
                value={
                    'is_active': True
                }
            )
        ]
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

    @require_permission('applications.update')
    def patch(self, request, app_id):
        try:
            app = Application.objects.get(id=app_id)
        except Application.DoesNotExist:
            return Response({
                'error': 'Application not found',
                'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is not None:
            app.is_active = bool(is_active)
            app.save()
            action = 'activated' if is_active else 'deactivated'
            return Response({
                'message': f'Application {action} successfully',
                'application': ApplicationSerializer(app).data
            })

        return Response({
            'error': 'No valid fields provided',
            'code': 'INVALID_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)

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
        description="Régénère l'access_key et l'access_secret d'une application. "
                    "**Attention:** les anciens credentials seront immédiatement invalidés. "
                    "Le nouveau secret n'est affiché qu'une seule fois. "
                    "Action irréversible nécessitant confirmation.",
        request={
            'type': 'object',
            'properties': {
                'confirmation': {
                    'type': 'string',
                    'description': 'Texte de confirmation "REGENERATE"'
                }
            },
            'required': ['confirmation']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'application': {'type': 'object'},
                    'credentials': {
                        'type': 'object',
                        'properties': {
                            'access_key': {'type': 'string'},
                            'access_secret': {'type': 'string'}
                        }
                    },
                    'warning': {'type': 'string'},
                    'old_credentials_invalidated': {'type': 'boolean'}
                }
            },
            400: {
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
            OpenApiExample(
                name='regenerate_success',
                summary='Credentials régénérés',
                value={
                    'confirmation': 'REGENERATE'
                }
            ),
            OpenApiExample(
                name='confirmation_required',
                summary='Confirmation requise',
                value={
                    'error': 'Confirmation required',
                    'code': 'CONFIRMATION_REQUIRED'
                }
            )
        ]
    )
    @require_permission('applications.regenerate')
    def post(self, request, app_id):
        confirmation = request.data.get('confirmation')
        if confirmation != 'REGENERATE':
            return Response({
                'error': 'Confirmation required',
                'code': 'CONFIRMATION_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)

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
            'warning': 'Save the access_secret now! It will never be shown again.',
            'old_credentials_invalidated': True
        })
