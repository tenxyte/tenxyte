"""
Security views - User sessions, devices, audit logs, and admin security.

User endpoints: /me/sessions/, /me/devices/, /me/audit-log/
Admin endpoints: /admin/audit-logs/, /admin/login-attempts/, etc.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from ..serializers.security_serializers import (
    AuditLogSerializer, LoginAttemptSerializer,
    BlacklistedTokenSerializer, RefreshTokenAdminSerializer,
    SessionSerializer, DeviceSerializer
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


# =============================================================================
# User Security Views
# =============================================================================

@api_view(['GET'])
@extend_schema(
    tags=['Security'],
    summary="Lister les sessions actives",
    description="Retourne la liste des sessions actives de l'utilisateur. "
                "Inclut les informations device, IP, localisation, et durée. "
                "Permet de détecter les sessions suspectes. "
                "La session actuelle est marquée comme 'current'.",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'device_info': {'type': 'object'},
                    'ip_address': {'type': 'string'},
                    'user_agent': {'type': 'string'},
                    'location': {'type': 'object', 'nullable': True},
                    'is_current': {'type': 'boolean'},
                    'created_at': {'type': 'string', 'format': 'date-time'},
                    'last_activity': {'type': 'string', 'format': 'date-time'},
                    'expires_at': {'type': 'string', 'format': 'date-time'}
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            name='sessions_list',
            summary='Liste sessions avec device info',
            value=[
                {
                    'id': 'sess_123456',
                    'device_info': {
                        'platform': 'iOS',
                        'browser': 'Safari',
                        'device': 'iPhone 14'
                    },
                    'ip_address': '192.168.1.100',
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                    'location': {'city': 'Paris', 'country': 'France'},
                    'is_current': True,
                    'created_at': '2024-01-15T10:30:00Z',
                    'last_activity': '2024-01-15T14:22:00Z',
                    'expires_at': '2024-01-22T10:30:00Z'
                }
            ]
        )
    ]
)
def list_sessions(request):
    """GET /me/sessions/"""
    from ..services.security_service import SecurityService
    service = SecurityService()
    sessions = service.get_user_sessions(request.user)
    return Response(sessions)


@api_view(['DELETE'])
@extend_schema(
    tags=['Security'],
    summary="Révoquer une session",
    description="Révoque une session spécifique. "
                "La session actuelle ne peut pas être révoquée (utilisez logout). "
                "L'utilisateur sera déconnecté immédiatement de cette session. "
                "Utile pour supprimer les sessions suspectes.",
    parameters=[
        OpenApiParameter(
            name='session_id',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID de la session à révoquer'
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
            name='revoke_session_success',
            summary='Session révoquée',
            value=None
        ),
        OpenApiExample(
            name='cannot_revoke_current',
            summary='Impossible de révoquer session actuelle',
            value={
                'error': 'Cannot revoke current session',
                'code': 'CANNOT_REVOKE_CURRENT'
            }
        )
    ]
)
def revoke_session(request, session_id):
    """DELETE /me/sessions/{session_id}/"""
    from ..services.security_service import SecurityService
    service = SecurityService()
    success, error = service.revoke_session(request.user, session_id)
    
    if not success:
        if error == 'SESSION_NOT_FOUND':
            return Response({
                'error': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        elif error == 'CANNOT_REVOKE_CURRENT':
            return Response({
                'error': 'Cannot revoke current session',
                'code': 'CANNOT_REVOKE_CURRENT'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': error,
                'code': 'REVOKE_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'Session revoked successfully'})


@api_view(['DELETE'])
@extend_schema(
    tags=['Security'],
    summary="Révoquer toutes les sessions",
    description="Révoque toutes les sessions sauf la session actuelle. "
                "Utile en cas de compromission de compte. "
                "Tous les autres appareils seront déconnectés. "
                "Action irréversible nécessitant confirmation.",
    request={
        'type': 'object',
        'properties': {
            'confirmation': {
                'type': 'string',
                'description': 'Texte de confirmation "REVOKE ALL"'
            }
        },
        'required': ['confirmation']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'revoked_count': {'type': 'integer'}
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
        OpenApiExample(
            name='revoke_all_success',
            summary='Toutes sessions révoquées',
            value={
                'confirmation': 'REVOKE ALL'
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
def revoke_all_sessions(request):
    """DELETE /me/sessions/"""
    confirmation = request.data.get('confirmation')
    if confirmation != 'REVOKE ALL':
        return Response({
            'error': 'Confirmation required',
            'code': 'CONFIRMATION_REQUIRED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from ..services.security_service import SecurityService
    service = SecurityService()
    revoked_count = service.revoke_all_sessions(request.user)
    
    return Response({
        'message': f'{revoked_count} sessions revoked successfully',
        'revoked_count': revoked_count
    })


@api_view(['GET'])
@extend_schema(
    tags=['Security'],
    summary="Lister les devices",
    description="Retourne la liste des devices enregistrés de l'utilisateur. "
                "Inclut le device fingerprinting et historique de connexion. "
                "Permet d'identifier les devices non reconnus. "
                "Les devices peuvent être révoqués individuellement.",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'fingerprint': {'type': 'string'},
                    'name': {'type': 'string'},
                    'type': {'type': 'string'},
                    'platform': {'type': 'string'},
                    'browser': {'type': 'string'},
                    'is_trusted': {'type': 'boolean'},
                    'first_seen': {'type': 'string', 'format': 'date-time'},
                    'last_seen': {'type': 'string', 'format': 'date-time'},
                    'login_count': {'type': 'integer'},
                    'ip_history': {'type': 'array'}
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            name='devices_list',
            summary='Liste devices avec fingerprinting',
            value=[
                {
                    'id': 1,
                    'fingerprint': 'fp_abc123',
                    'name': 'iPhone 14 - Safari',
                    'type': 'mobile',
                    'platform': 'iOS',
                    'browser': 'Safari',
                    'is_trusted': True,
                    'first_seen': '2024-01-15T10:30:00Z',
                    'last_seen': '2024-01-15T14:22:00Z',
                    'login_count': 15,
                    'ip_history': ['192.168.1.100', '10.0.0.5']
                }
            ]
        )
    ]
)
def list_devices(request):
    """GET /me/devices/"""
    from ..services.security_service import SecurityService
    service = SecurityService()
    devices = service.get_user_devices(request.user)
    return Response(devices)


@api_view(['DELETE'])
@extend_schema(
    tags=['Security'],
    summary="Révoquer un device",
    description="Révoque un device spécifique et supprime toutes ses sessions. "
                "Le device fingerprint sera blacklisté temporairement. "
                "Utile pour supprimer les devices perdus ou volés. "
                "Le device ne pourra plus se connecter pendant 24h.",
    parameters=[
        OpenApiParameter(
            name='device_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID du device à révoquer'
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'sessions_revoked': {'type': 'integer'}
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
            name='revoke_device_success',
            summary='Device révoqué',
            value=None
        )
    ]
)
def revoke_device(request, device_id):
    """DELETE /me/devices/{device_id}/"""
    from ..services.security_service import SecurityService
    service = SecurityService()
    success, data, error = service.revoke_device(request.user, device_id)
    
    if not success:
        if error == 'DEVICE_NOT_FOUND':
            return Response({
                'error': 'Device not found',
                'code': 'DEVICE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({
                'error': error,
                'code': 'REVOKE_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'message': 'Device revoked successfully',
        'sessions_revoked': data.get('sessions_revoked', 0)
    })


@api_view(['GET'])
@extend_schema(
    tags=['Security'],
    summary="Audit log personnel",
    description="Retourne l'historique des actions de sécurité de l'utilisateur. "
                "Inclut les connexions, changements de mot de passe, "
                "activations 2FA, et autres événements de sécurité. "
                "Données paginées et filtrables par date et type d'action.",
    parameters=[
        OpenApiParameter(
            name='action',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=['login', 'login_failed', 'password_change', '2fa_enabled', '2fa_disabled', 'device_added'],
            description='Filtrer par type d\'action'
        ),
        OpenApiParameter(
            name='date_from',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filtrer depuis cette date'
        ),
        OpenApiParameter(
            name='date_to',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filtrer jusqu\'à cette date'
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
                            'action': {'type': 'string'},
                            'description': {'type': 'string'},
                            'ip_address': {'type': 'string'},
                            'user_agent': {'type': 'string'},
                            'location': {'type': 'object', 'nullable': True},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'metadata': {'type': 'object'}
                        }
                    }
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            name='audit_log_filtered',
            summary='Audit log filtré par action',
            value={
                'count': 25,
                'results': [
                    {
                        'id': 1234,
                        'action': 'login',
                        'description': 'Successful login via email',
                        'ip_address': '192.168.1.100',
                        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)',
                        'location': {'city': 'Paris', 'country': 'France'},
                        'created_at': '2024-01-15T10:30:00Z',
                        'metadata': {'method': 'email', 'device_trusted': True}
                    }
                ]
            }
        )
    ]
)
def user_audit_log(request):
    """GET /me/audit-log/"""
    from ..services.security_service import SecurityService
    service = SecurityService()
    
    action = request.query_params.get('action')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    
    audit_data = service.get_user_audit_log(
        user=request.user,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=int(page),
        page_size=min(int(page_size), 100)
    )
    
    return Response(audit_data)
