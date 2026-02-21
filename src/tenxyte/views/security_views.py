"""
Security admin views - Audit logs, Login attempts, Blacklisted tokens, Refresh tokens.

All endpoints require admin permissions (audit.view, security.view).
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers.security_serializers import (
    AuditLogSerializer, LoginAttemptSerializer,
    BlacklistedTokenSerializer, RefreshTokenAdminSerializer,
)
from ..models import AuditLog, BlacklistedToken, RefreshToken, LoginAttempt
from ..decorators import require_permission
from ..pagination import TenxytePagination
from ..filters import apply_audit_log_filters, apply_login_attempt_filters


# =============================================================================
# Audit Logs
# =============================================================================


class AuditLogListView(APIView):
    """
    GET /api/auth/admin/audit-logs/
    List all audit log entries (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - Security'],
        summary="Lister les audit logs",
        description="Retourne les événements d'audit paginés et filtrés.",
        parameters=[
            OpenApiParameter('user_id', str, description='Filtrer par ID utilisateur'),
            OpenApiParameter('action', str, description='Filtrer par action (login, login_failed, password_change, etc.)'),
            OpenApiParameter('ip_address', str, description="Filtrer par adresse IP"),
            OpenApiParameter('application_id', str, description="Filtrer par ID application"),
            OpenApiParameter('date_from', str, description='Après (YYYY-MM-DD)'),
            OpenApiParameter('date_to', str, description='Avant (YYYY-MM-DD)'),
            OpenApiParameter('ordering', str, description='Tri: created_at, action, user'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: AuditLogSerializer(many=True)}
    )
    @require_permission('audit.view')
    def get(self, request):
        queryset = AuditLog.objects.select_related('user', 'application').all()
        queryset = apply_audit_log_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data)


class AuditLogDetailView(APIView):
    """
    GET /api/auth/admin/audit-logs/<log_id>/
    """

    @extend_schema(
        tags=['Admin - Security'],
        summary="Détails d'un audit log",
        responses={200: AuditLogSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('audit.view')
    def get(self, request, log_id):
        try:
            log = AuditLog.objects.select_related('user', 'application').get(id=log_id)
        except AuditLog.DoesNotExist:
            return Response({
                'error': 'Audit log not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(AuditLogSerializer(log).data)


# =============================================================================
# Login Attempts
# =============================================================================


class LoginAttemptListView(APIView):
    """
    GET /api/auth/admin/login-attempts/
    List login attempt records (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - Security'],
        summary="Lister les tentatives de connexion",
        description="Retourne les tentatives de connexion paginées et filtrées.",
        parameters=[
            OpenApiParameter('identifier', str, description='Filtrer par identifiant (email/phone)'),
            OpenApiParameter('ip_address', str, description="Filtrer par adresse IP"),
            OpenApiParameter('success', bool, description='Filtrer par succès/échec'),
            OpenApiParameter('date_from', str, description='Après (YYYY-MM-DD)'),
            OpenApiParameter('date_to', str, description='Avant (YYYY-MM-DD)'),
            OpenApiParameter('ordering', str, description='Tri: created_at, identifier, ip_address'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: LoginAttemptSerializer(many=True)}
    )
    @require_permission('security.view')
    def get(self, request):
        queryset = LoginAttempt.objects.all()
        queryset = apply_login_attempt_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = LoginAttemptSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = LoginAttemptSerializer(queryset, many=True)
        return Response(serializer.data)


# =============================================================================
# Blacklisted Tokens
# =============================================================================


class BlacklistedTokenListView(APIView):
    """
    GET /api/auth/admin/blacklisted-tokens/
    List blacklisted JWT tokens (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - Security'],
        summary="Lister les tokens blacklistés",
        description="Retourne les tokens JWT révoqués.",
        parameters=[
            OpenApiParameter('user_id', str, description='Filtrer par ID utilisateur'),
            OpenApiParameter('reason', str, description='Filtrer par raison (logout, password_change, security)'),
            OpenApiParameter('expired', bool, description='Filtrer par expiré (true/false)'),
            OpenApiParameter('ordering', str, description='Tri: blacklisted_at, expires_at'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: BlacklistedTokenSerializer(many=True)}
    )
    @require_permission('security.view')
    def get(self, request):
        queryset = BlacklistedToken.objects.select_related('user').all()

        # Apply filters
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        reason = request.query_params.get('reason')
        if reason:
            queryset = queryset.filter(reason=reason)

        expired = request.query_params.get('expired')
        if expired is not None:
            from django.utils import timezone
            if expired.lower() in ('true', '1'):
                queryset = queryset.filter(expires_at__lt=timezone.now())
            elif expired.lower() in ('false', '0'):
                queryset = queryset.filter(expires_at__gte=timezone.now())

        # Ordering
        ordering = request.query_params.get('ordering', '-blacklisted_at')
        allowed_fields = {'blacklisted_at', 'expires_at', '-blacklisted_at', '-expires_at'}
        if ordering in allowed_fields:
            queryset = queryset.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = BlacklistedTokenSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = BlacklistedTokenSerializer(queryset, many=True)
        return Response(serializer.data)


class BlacklistedTokenCleanupView(APIView):
    """
    POST /api/auth/admin/blacklisted-tokens/cleanup/
    Remove expired tokens from the blacklist.
    """

    @extend_schema(
        tags=['Admin - Security'],
        summary="Nettoyer les tokens expirés",
        description="Supprime les tokens blacklistés qui ont déjà expiré naturellement.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('security.view')
    def post(self, request):
        deleted_count = BlacklistedToken.cleanup_expired()
        return Response({
            'message': f'{deleted_count} expired tokens cleaned up',
            'deleted_count': deleted_count,
        })


# =============================================================================
# Refresh Tokens
# =============================================================================


class RefreshTokenListView(APIView):
    """
    GET /api/auth/admin/refresh-tokens/
    List refresh tokens (paginated + filtered).
    """
    pagination_class = TenxytePagination

    @extend_schema(
        tags=['Admin - Security'],
        summary="Lister les refresh tokens",
        description="Retourne les refresh tokens (valeur du token masquée).",
        parameters=[
            OpenApiParameter('user_id', str, description='Filtrer par ID utilisateur'),
            OpenApiParameter('application_id', str, description='Filtrer par ID application'),
            OpenApiParameter('is_revoked', bool, description='Filtrer par révoqué'),
            OpenApiParameter('expired', bool, description='Filtrer par expiré'),
            OpenApiParameter('ordering', str, description='Tri: created_at, expires_at, last_used_at'),
            OpenApiParameter('page', int, description='Numéro de page'),
            OpenApiParameter('page_size', int, description='Éléments par page (max 100)'),
        ],
        responses={200: RefreshTokenAdminSerializer(many=True)}
    )
    @require_permission('security.view')
    def get(self, request):
        queryset = RefreshToken.objects.select_related('user', 'application').all()

        # Apply filters
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        application_id = request.query_params.get('application_id')
        if application_id:
            queryset = queryset.filter(application_id=application_id)

        is_revoked = request.query_params.get('is_revoked')
        if is_revoked is not None:
            queryset = queryset.filter(is_revoked=is_revoked.lower() in ('true', '1'))

        expired = request.query_params.get('expired')
        if expired is not None:
            from django.utils import timezone
            if expired.lower() in ('true', '1'):
                queryset = queryset.filter(expires_at__lt=timezone.now())
            elif expired.lower() in ('false', '0'):
                queryset = queryset.filter(expires_at__gte=timezone.now())

        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        allowed_fields = {
            'created_at', '-created_at', 'expires_at', '-expires_at',
            'last_used_at', '-last_used_at',
        }
        if ordering in allowed_fields:
            queryset = queryset.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = RefreshTokenAdminSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = RefreshTokenAdminSerializer(queryset, many=True)
        return Response(serializer.data)


class RefreshTokenRevokeView(APIView):
    """
    POST /api/auth/admin/refresh-tokens/<token_id>/revoke/
    Revoke a refresh token.
    """

    @extend_schema(
        tags=['Admin - Security'],
        summary="Révoquer un refresh token",
        description="Révoque un refresh token spécifique.",
        responses={200: RefreshTokenAdminSerializer, 404: OpenApiTypes.OBJECT}
    )
    @require_permission('security.view')
    def post(self, request, token_id):
        try:
            token = RefreshToken.objects.select_related('user', 'application').get(id=token_id)
        except RefreshToken.DoesNotExist:
            return Response({
                'error': 'Refresh token not found', 'code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        if token.is_revoked:
            return Response({
                'error': 'Token already revoked', 'code': 'ALREADY_REVOKED'
            }, status=status.HTTP_400_BAD_REQUEST)

        token.revoke()

        return Response({
            'message': 'Token revoked successfully',
            'token': RefreshTokenAdminSerializer(token).data,
        })
