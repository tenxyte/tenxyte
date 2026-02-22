"""
Vues pour la gestion des suppressions de compte (RGPD).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from ..services.account_deletion_service import AccountDeletionService
from ..serializers import PasswordSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(
    tags=['Account'],
    summary="Demander la suppression de compte",
    description="Initie le processus de suppression de compte conforme au RGPD. "
                "Le compte sera marqué pour suppression après une période de grâce "
                "de 30 jours pendant laquelle l'utilisateur peut annuler. "
                "Nécessite le mot de passe actuel et code OTP si 2FA activé. "
                "Toutes les données seront anonymisées après la période de grâce.",
    request={
        'type': 'object',
        'properties': {
            'password': {
                'type': 'string',
                'description': 'Mot de passe actuel requis pour confirmation'
            },
            'otp_code': {
                'type': 'string',
                'description': 'Code OTP à 6 chiffres (requis si 2FA activé)'
            },
            'reason': {
                'type': 'string',
                'description': 'Raison optionnelle de la suppression'
            }
        },
        'required': ['password']
    },
    responses={
        201: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'deletion_request_id': {'type': 'integer'},
                'scheduled_deletion_date': {'type': 'string', 'format': 'date-time'},
                'grace_period_days': {'type': 'integer'},
                'cancellation_token': {'type': 'string'},
                'data_retention_policy': {
                    'type': 'object',
                    'properties': {
                        'anonymization_after': {'type': 'string'},
                        'final_deletion_after': {'type': 'string'}
                    }
                }
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'}
            }
        },
        423: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'},
                'existing_request': {'type': 'object'}
            }
        }
    },
    examples=[
        OpenApiExample(
            name='deletion_request_success',
            summary='Demande de suppression créée',
            value={
                'password': 'CurrentPassword123!',
                'otp_code': '123456',
                'reason': 'No longer need the account'
            }
        ),
        OpenApiExample(
            name='deletion_already_pending',
            summary='Suppression déjà en cours',
            value={
                'error': 'Account deletion already pending',
                'code': 'DELETION_ALREADY_PENDING',
                'existing_request': {
                    'scheduled_deletion_date': '2024-02-15T10:30:00Z',
                    'cancellation_token': 'cancel_abc123'
                }
            }
        ),
        OpenApiExample(
            name='invalid_2fa',
            summary='Code 2FA invalide',
            value={
                'error': 'Invalid or missing OTP code',
                'code': 'INVALID_2FA_CODE'
            }
        )
    ]
)
def request_account_deletion(request: Request) -> Response:
    serializer = PasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid password', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    service = AccountDeletionService()
    success, data, error = service.request_deletion(
        user=request.user,
        password=serializer.validated_data['password'],
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        otp_code=request.data.get('otp_code', ''),
        reason=request.data.get('reason', '')
    )
    
    if success:
        return Response(data, status=status.HTTP_201_CREATED)
    
    return Response(
        {'error': error},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@extend_schema(
    tags=['Account'],
    summary="Confirmer la suppression de compte",
    description="Confirme la demande de suppression via token reçu par email. "
                "Le token est valide 24 heures. Cette étape est requise pour "
                "vérifier que l'utilisateur a bien accès à son email. "
                "Après confirmation, le compte entre en période de grâce de 30 jours.",
    request={
        'type': 'object',
        'properties': {
            'token': {
                'type': 'string',
                'description': 'Token de confirmation reçu par email'
            }
        },
        'required': ['token']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'deletion_confirmed': {'type': 'boolean'},
                'grace_period_ends': {'type': 'string', 'format': 'date-time'},
                'cancellation_instructions': {'type': 'string'}
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
        },
        410: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'},
                'code': {'type': 'string'},
                'expired_at': {'type': 'string', 'format': 'date-time'}
            }
        }
    },
    examples=[
        OpenApiExample(
            name='confirm_success',
            summary='Suppression confirmée',
            value={
                'token': 'confirm_abc123def456'
            }
        ),
        OpenApiExample(
            name='token_expired',
            summary='Token expiré',
            value={
                'error': 'Confirmation token has expired',
                'code': 'TOKEN_EXPIRED',
                'expired_at': '2024-01-16T10:30:00Z'
            }
        ),
        OpenApiExample(
            name='invalid_token',
            summary='Token invalide',
            value={
                'error': 'Invalid confirmation token',
                'code': 'INVALID_TOKEN'
            }
        )
    ]
)
def confirm_account_deletion(request: Request) -> Response:
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'Confirmation token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    service = AccountDeletionService()
    success, data, error = service.confirm_deletion(
        token=token,
        ip_address=_get_client_ip(request)
    )
    
    if success:
        return Response(data, status=status.HTTP_200_OK)
    
    return Response(
        {'error': error},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(
    tags=['Account'],
    summary="Annuler la suppression de compte",
    description="Annule une demande de suppression de compte pendant la période de grâce. "
                "Nécessite le mot de passe actuel pour sécurité. "
                "Le compte sera réactivé immédiatement. "
                "Un email de confirmation sera envoyé. "
                "L'annulation est possible jusqu'à la fin de la période de grâce.",
    request={
        'type': 'object',
        'properties': {
            'password': {
                'type': 'string',
                'description': 'Mot de passe actuel requis pour annulation'
            }
        },
        'required': ['password']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'deletion_cancelled': {'type': 'boolean'},
                'account_reactivated': {'type': 'boolean'},
                'cancellation_time': {'type': 'string', 'format': 'date-time'},
                'security_note': {'type': 'string'}
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
            name='cancel_success',
            summary='Suppression annulée',
            value={
                'password': 'CurrentPassword123!'
            }
        ),
        OpenApiExample(
            name='no_pending_deletion',
            summary='Aucune suppression en cours',
            value={
                'error': 'No pending deletion request found',
                'code': 'NO_PENDING_DELETION'
            }
        ),
        OpenApiExample(
            name='invalid_password',
            summary='Mot de passe invalide',
            value={
                'error': 'Invalid password',
                'code': 'INVALID_PASSWORD'
            }
        )
    ]
)
def cancel_account_deletion(request: Request) -> Response:
    serializer = PasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid password', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    service = AccountDeletionService()
    success, data, error = service.cancel_deletion(
        user=request.user,
        password=serializer.validated_data['password'],
        ip_address=_get_client_ip(request)
    )
    
    if success:
        return Response(data, status=status.HTTP_200_OK)
    
    return Response(
        {'error': error},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_deletion_status(request: Request) -> Response:
    """
    Obtenir le statut des demandes de suppression de compte.
    
    GET /api/auth/account-deletion-status/
    """
    service = AccountDeletionService()
    data = service.get_user_requests(request.user)
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_user_data(request: Request) -> Response:
    """
    Exporter les données de l'utilisateur (RGPD).
    
    POST /api/auth/export-user-data/
    {
        "password": "current_password"
    }
    """
    serializer = PasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid password', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier le mot de passe
    if not request.user.check_password(serializer.validated_data['password']):
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Exporter les données de l'utilisateur (droit à la portabilité RGPD)
    try:
        user_data = {
            'user_info': {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone_country_code': request.user.phone_country_code,
                'phone_number': request.user.phone_number,
                'is_email_verified': request.user.is_email_verified,
                'is_phone_verified': request.user.is_phone_verified,
                'is_2fa_enabled': request.user.is_2fa_enabled,
                'created_at': request.user.created_at.isoformat(),
                'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
            },
            'roles': [
                {
                    'code': role.code,
                    'name': role.name,
                    'assigned_at': role.created_at.isoformat()
                }
                for role in request.user.roles.all()
            ],
            'permissions': [
                {
                    'code': perm.code,
                    'name': perm.name,
                    'granted_at': perm.created_at.isoformat()
                }
                for perm in request.user.get_all_permissions()
            ],
            'applications': [
                {
                    'name': app.name,
                    'created_at': app.created_at.isoformat()
                }
                for app in (request.user.applications.all() if hasattr(request.user, 'applications') else [])
            ],
            'audit_logs': [
                {
                    'action': log.action,
                    'ip_address': log.ip_address,
                    'created_at': log.created_at.isoformat(),
                    'details': log.details
                }
                for log in request.user.audit_logs.all()[:100]  # Limiter aux 100 plus récents
            ],
            'export_metadata': {
                'exported_at': timezone.now().isoformat(),
                'export_reason': 'user_request',
                'user_id': request.user.id
            }
        }
        
        # Log l'export pour audit
        from ..models import AuditLog
        AuditLog.objects.create(
            action='data_exported',
            user=request.user,
            ip_address=_get_client_ip(request),
            details={
                'export_reason': 'user_request',
                'exported_at': timezone.now().isoformat()
            }
        )
        
        return Response(user_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Error exporting user data: {str(e)}',
            'user_id': request.user.id,
            'export_requested_at': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_client_ip(request: Request) -> str:
    """Obtenir l'IP client pour les logs."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'
