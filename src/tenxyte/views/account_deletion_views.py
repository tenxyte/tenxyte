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

from ..services.account_deletion_service import AccountDeletionService
from ..serializers import PasswordSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_account_deletion(request: Request) -> Response:
    """
    Demander la suppression de son compte.
    
    POST /api/auth/request-account-deletion/
    {
        "password": "current_password",
        "otp_code": "123456",  # Required if 2FA enabled
        "reason": "Optional reason for deletion"
    }
    """
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
def confirm_account_deletion(request: Request) -> Response:
    """
    Confirmer une demande de suppression via token email.
    
    POST /api/auth/confirm-account-deletion/
    {
        "token": "confirmation_token_from_email"
    }
    """
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
def cancel_account_deletion(request: Request) -> Response:
    """
    Annuler une demande de suppression de compte.
    
    POST /api/auth/cancel-account-deletion/
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
                for app in request.user.applications.all() if hasattr(request.user, 'applications')
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
