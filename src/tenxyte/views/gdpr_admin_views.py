"""
GDPR admin views - Account deletion request management for admins.

Endpoints:
- List all deletion requests (paginated + filtered)
- Detail of a deletion request
- Process (execute) a confirmed deletion request
- Process all expired grace period requests
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from ..serializers.gdpr_admin_serializers import (
    DeletionRequestSerializer, ProcessDeletionSerializer,
)
from ..models import AccountDeletionRequest
from ..decorators import require_permission
from ..pagination import TenxytePagination


class DeletionRequestListView(APIView):
    """
    GET {API_PREFIX}/auth/admin/deletion-requests/
    List all account deletion requests (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - GDPR'],
        operation_id='admin_deletion_requests_list',
        summary="Lister les demandes de suppression",
        description="Retourne les demandes de suppression de compte paginées et filtrées. "
                    "Interface admin pour la gestion RGPD. Inclut les détails utilisateur, "
                    "statut de traitement, et dates importantes. Permet de surveiller "
                    "les demandes en attente et celles nécessitant un traitement manuel.",
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filtrer par ID utilisateur'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['pending', 'confirmation_sent', 'confirmed', 'completed', 'cancelled'],
                description='Filtrer par statut de la demande'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Demandé après cette date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Demandé avant cette date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='grace_period_expiring',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filtrer les demandes dont la période de grâce expire bientôt (7 jours)'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Tri: requested_at, confirmed_at, grace_period_ends_at, user__email'
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
                                'user': {'type': 'object'},
                                'status': {'type': 'string'},
                                'reason': {'type': 'string', 'nullable': True},
                                'requested_at': {'type': 'string', 'format': 'date-time'},
                                'confirmed_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                                'grace_period_ends_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                                'processed_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                                'processed_by': {'type': 'object', 'nullable': True},
                                'ip_address': {'type': 'string'},
                                'user_agent': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        },
        examples=[
            OpenApiExample(response_only=True, 
                name='pending_requests',
                summary='Demandes en attente',
                value={
                    'status': 'pending',
                    'grace_period_expiring': True
                }
            ),
            OpenApiExample(
                name='user_specific',
                summary='Demandes utilisateur spécifique',
                value={
                    'user_id': 12345,
                    'ordering': '-requested_at'
                }
            )
        ]
    )
    @require_permission('gdpr.admin')
    def get(self, request):
        queryset = AccountDeletionRequest.objects.select_related(
            'user', 'processed_by'
        ).all()

        # Filters
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        req_status = request.query_params.get('status')
        if req_status:
            queryset = queryset.filter(status=req_status)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(requested_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(requested_at__date__lte=date_to)

        # Ordering
        ordering = request.query_params.get('ordering', '-requested_at')
        allowed_fields = {
            'requested_at', '-requested_at',
            'confirmed_at', '-confirmed_at',
            'grace_period_ends_at', '-grace_period_ends_at',
        }
        if ordering in allowed_fields:
            queryset = queryset.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = DeletionRequestSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DeletionRequestSerializer(queryset, many=True)
        return Response(serializer.data)


class DeletionRequestDetailView(APIView):
    """
    GET {API_PREFIX}/auth/admin/deletion-requests/<request_id>/
    """

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Détails d'une demande de suppression",
        responses={200: DeletionRequestSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('gdpr.admin')
    def get(self, request, request_id):
        try:
            deletion_request = AccountDeletionRequest.objects.select_related(
                'user', 'processed_by'
            ).get(id=request_id)
        except AccountDeletionRequest.DoesNotExist:
            return Response({
                'error': 'Deletion request not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response(DeletionRequestSerializer(deletion_request).data)


class ProcessDeletionView(APIView):
    """
    POST {API_PREFIX}/auth/admin/deletion-requests/<request_id>/process/
    Execute a confirmed deletion request (admin action).
    """

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Traiter une demande de suppression",
        description="Exécute manuellement une demande de suppression confirmée. "
                    "**ATTENTION:** Cette action est irréversible et détruira "
                    "définitivement toutes les données utilisateur conformément au RGPD. "
                    "Nécessite une confirmation explicite. Un audit trail sera conservé. "
                    "Un email de notification sera envoyé à l'utilisateur.",
        parameters=[
            OpenApiParameter(
                name='request_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description='ID de la demande de suppression'
            )
        ],
        request=inline_serializer(
            name='ProcessDeletionRequest',
            fields={
                'confirmation': serializers.CharField(help_text='Texte de confirmation "PERMANENTLY DELETE"'),
                'admin_notes': serializers.CharField(required=False, allow_blank=True, help_text='Notes administratives optionnelles')
            }
        ),
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'deletion_completed': {'type': 'boolean'},
                    'processed_at': {'type': 'string', 'format': 'date-time'},
                    'data_anonymized': {'type': 'boolean'},
                    'audit_log_id': {'type': 'integer'},
                    'user_notified': {'type': 'boolean'}
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
                name='process_success',
                summary='Suppression traitée',
                value={
                    'confirmation': 'PERMANENTLY DELETE',
                    'admin_notes': 'Processed per user request - GDPR compliance'
                }
            ),
            OpenApiExample(response_only=True, 
                name='confirmation_required',
                summary='Confirmation requise',
                value={
                    'error': 'Explicit confirmation required',
                    'code': 'CONFIRMATION_REQUIRED'
                }
            ),
            OpenApiExample(response_only=True, 
                name='request_not_confirmed',
                summary='Demande non confirmée',
                value={
                    'error': 'Cannot process unconfirmed deletion request',
                    'code': 'REQUEST_NOT_CONFIRMED'
                }
            )
        ]
    )
    @require_permission('gdpr.process')
    def post(self, request, request_id):
        try:
            deletion_request = AccountDeletionRequest.objects.select_related(
                'user', 'processed_by'
            ).get(id=request_id)
        except AccountDeletionRequest.DoesNotExist:
            return Response({
                'error': 'Deletion request not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if deletion_request.status != 'confirmed':
            return Response({
                'error': f'Cannot process request with status "{deletion_request.status}". Only confirmed requests can be processed.',
                'code': 'REQUEST_NOT_CONFIRMED'
            }, status=status.HTTP_400_BAD_REQUEST)

        confirmation = request.data.get('confirmation')
        if confirmation != 'PERMANENTLY DELETE':
            return Response({
                'error': 'Explicit confirmation required',
                'code': 'CONFIRMATION_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)

        admin_notes = request.data.get('admin_notes', '')
        if admin_notes:
            deletion_request.admin_notes = admin_notes
            deletion_request.save(update_fields=['admin_notes'])

        success = deletion_request.execute_deletion(processed_by=request.user)

        if success:
            return Response({
                'message': 'Account deletion processed successfully',
                'deletion_completed': True,
                'processed_at': deletion_request.completed_at,
                'data_anonymized': True,
                'audit_log_id': deletion_request.id,
                'user_notified': True,
                'request': DeletionRequestSerializer(deletion_request).data,
            })

        return Response({
            'error': 'Failed to process deletion',
            'code': 'PROCESSING_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessExpiredDeletionsView(APIView):
    """
    POST {API_PREFIX}/auth/admin/deletion-requests/process-expired/
    Process all confirmed requests whose grace period has expired.
    """

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Traiter les demandes expirées",
        description="Exécute automatiquement la suppression pour toutes les demandes confirmées "
                    "dont la période de grâce de 30 jours est expirée. Action batch pour la "
                    "maintenance RGPD. Un rapport détaillé des traitements est retourné. "
                    "Cette action est généralement exécutée par une tâche cron quotidienne.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'processed_count': {'type': 'integer'},
                    'failed_count': {'type': 'integer'},
                    'skipped_count': {'type': 'integer'},
                    'processing_time': {'type': 'number'},
                    'details': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'request_id': {'type': 'integer'},
                                'user_email': {'type': 'string'},
                                'status': {'type': 'string'},
                                'grace_period_expired': {'type': 'string', 'format': 'date-time'}
                            }
                        }
                    }
                }
            }
        },
        examples=[
            OpenApiExample(response_only=True, 
                name='batch_success',
                summary='Traitement batch réussi',
                value=None
            )
        ],
        request=None
    )
    @require_permission('gdpr.process')
    def post(self, request):
        expired_requests = AccountDeletionRequest.get_expired_requests()
        processed = 0
        failed = 0

        for deletion_request in expired_requests:
            success = deletion_request.execute_deletion(processed_by=request.user)
            if success:
                processed += 1
            else:
                failed += 1

        return Response({
            'message': f'{processed} deletion(s) processed, {failed} failed',
            'processed': processed,
            'failed': failed,
        })
