from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..decorators import require_jwt


class TwoFactorStatusView(APIView):
    """
    GET /api/auth/2fa/status/
    Récupère le statut 2FA de l'utilisateur
    """

    @extend_schema(
        tags=['2FA'],
        summary="Statut 2FA",
        description="Retourne si le 2FA est activé et le nombre de codes de secours restants.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def get(self, request):
        return Response({
            'is_enabled': request.user.is_2fa_enabled,
            'backup_codes_remaining': len(request.user.backup_codes) if request.user.backup_codes else 0
        })


class TwoFactorSetupView(APIView):
    """
    POST /api/auth/2fa/setup/
    Initialise la configuration 2FA
    """

    @extend_schema(
        tags=['2FA'],
        summary="Initialiser 2FA",
        description="Génère un nouveau secret TOTP et retourne le QR code et les codes de secours. "
                    "L'utilisateur doit ensuite confirmer avec un code TOTP valide.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        if request.user.is_2fa_enabled:
            return Response({
                'error': '2FA is already enabled',
                'code': '2FA_ALREADY_ENABLED'
            }, status=status.HTTP_400_BAD_REQUEST)

        setup_data = totp_service.setup_2fa(request.user)

        return Response({
            'message': 'Scan the QR code with your authenticator app, then confirm with a code.',
            'secret': setup_data['secret'],
            'qr_code': setup_data['qr_code'],
            'provisioning_uri': setup_data['provisioning_uri'],
            'backup_codes': setup_data['backup_codes'],
            'warning': 'Save the backup codes securely. They will not be shown again.'
        })


class TwoFactorConfirmView(APIView):
    """
    POST /api/auth/2fa/confirm/
    Confirme l'activation du 2FA avec un code TOTP
    """

    @extend_schema(
        tags=['2FA'],
        summary="Confirmer activation 2FA",
        description="Vérifie le premier code TOTP pour activer le 2FA.",
        request={"application/json": {"type": "object", "properties": {"code": {"type": "string"}}}},
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get('code', '')
        if not code:
            return Response({
                'error': 'Code is required',
                'code': 'CODE_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)

        success, error = totp_service.confirm_2fa(request.user, code)

        if not success:
            return Response({
                'error': error,
                'code': 'INVALID_CODE'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': '2FA enabled successfully',
            'is_enabled': True
        })


class TwoFactorDisableView(APIView):
    """
    POST /api/auth/2fa/disable/
    Désactive le 2FA
    """

    @extend_schema(
        tags=['2FA'],
        summary="Désactiver 2FA",
        description="Désactive le 2FA après vérification du code TOTP ou d'un code de secours.",
        request={"application/json": {"type": "object", "properties": {"code": {"type": "string"}}}},
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get('code', '')
        if not code:
            return Response({
                'error': 'Code is required',
                'code': 'CODE_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)

        success, error = totp_service.disable_2fa(request.user, code)

        if not success:
            return Response({
                'error': error,
                'code': 'INVALID_CODE'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': '2FA disabled successfully',
            'is_enabled': False
        })


class TwoFactorBackupCodesView(APIView):
    """
    POST /api/auth/2fa/backup-codes/
    Régénère les codes de secours
    """

    @extend_schema(
        tags=['2FA'],
        summary="Régénérer codes de secours",
        description="Génère de nouveaux codes de secours (les anciens sont invalidés). "
                    "Requiert un code TOTP valide.",
        request={"application/json": {"type": "object", "properties": {"code": {"type": "string"}}}},
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get('code', '')
        if not code:
            return Response({
                'error': 'TOTP code is required',
                'code': 'CODE_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)

        success, new_codes, error = totp_service.regenerate_backup_codes(request.user, code)

        if not success:
            return Response({
                'error': error,
                'code': 'INVALID_CODE'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Backup codes regenerated',
            'backup_codes': new_codes,
            'warning': 'Save these codes securely. They will not be shown again.'
        })
