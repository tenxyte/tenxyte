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
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers.gdpr_admin_serializers import (
    DeletionRequestSerializer, ProcessDeletionSerializer,
)
from ..models import AccountDeletionRequest
from ..decorators import require_permission
from ..pagination import TenxytePagination


class DeletionRequestListView(APIView):
    """
    GET /api/auth/admin/deletion-requests/
    List all account deletion requests (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Lister les demandes de suppression",
        description="Retourne les demandes de suppression de compte paginées et filtrées.",
        parameters=[
            OpenApiParameter('user_id', str, description='Filtrer par ID utilisateur'),
            OpenApiParameter('status', str, description='Filtrer par statut (pending, confirmation_sent, confirmed, completed, cancelled)'),
            OpenApiParameter('date_from', str, description='Demandé après (YYYY-MM-DD)'),
            OpenApiParameter('date_to', str, description='Demandé avant (YYYY-MM-DD)'),
            OpenApiParameter('ordering', str, description='Tri: requested_at, confirmed_at, grace_period_ends_at'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: DeletionRequestSerializer(many=True)}
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
    GET /api/auth/admin/deletion-requests/<request_id>/
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
    POST /api/auth/admin/deletion-requests/<request_id>/process/
    Execute a confirmed deletion request (admin action).
    """

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Traiter une demande de suppression",
        description="Exécute la suppression du compte pour une demande confirmée.",
        request=ProcessDeletionSerializer,
        responses={200: DeletionRequestSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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
                'code': 'INVALID_STATUS'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProcessDeletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin_notes = serializer.validated_data.get('admin_notes', '')
        if admin_notes:
            deletion_request.admin_notes = admin_notes
            deletion_request.save(update_fields=['admin_notes'])

        success = deletion_request.execute_deletion(processed_by=request.user)

        if success:
            return Response({
                'message': 'Account deletion processed successfully',
                'request': DeletionRequestSerializer(deletion_request).data,
            })

        return Response({
            'error': 'Failed to process deletion',
            'code': 'PROCESSING_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessExpiredDeletionsView(APIView):
    """
    POST /api/auth/admin/deletion-requests/process-expired/
    Process all confirmed requests whose grace period has expired.
    """

    @extend_schema(
        tags=['Admin - GDPR'],
        summary="Traiter les demandes expirées",
        description="Exécute la suppression pour toutes les demandes confirmées dont la période de grâce est expirée.",
        responses={200: OpenApiTypes.OBJECT}
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
