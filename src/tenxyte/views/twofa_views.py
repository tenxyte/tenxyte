from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..decorators import require_jwt


class TwoFactorStatusView(APIView):
    """
    GET {API_PREFIX}/auth/2fa/status/
    Récupère le statut 2FA de l'utilisateur
    """

    @extend_schema(
        tags=["2FA"],
        summary="Statut 2FA",
        description="Retourne si le 2FA est activé et le nombre de codes de secours restants.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_jwt
    def get(self, request):
        return Response(
            {
                "is_enabled": request.user.is_2fa_enabled,
                "backup_codes_remaining": len(request.user.backup_codes) if request.user.backup_codes else 0,
            }
        )


class TwoFactorSetupView(APIView):
    """
    POST {API_PREFIX}/auth/2fa/setup/
    Initialise la configuration 2FA
    """

    @extend_schema(
        tags=["2FA"],
        summary="Initialiser 2FA",
        description="Génère un nouveau secret TOTP et retourne le QR code et les codes de secours. "
        "Le QR code peut être scanné avec Google Authenticator, Authy, etc. "
        "L'utilisateur doit ensuite confirmer avec un code TOTP valide pour activer le 2FA. "
        "Les codes de secours (10 codes à usage unique) permettent l'accès si l'appareil est perdu.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "secret": {"type": "string", "description": "Secret TOTP base32"},
                    "qr_code": {"type": "string", "description": "QR code en base64"},
                    "backup_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "10 codes de secours à usage unique",
                    },
                    "manual_entry_key": {"type": "string", "description": "Clé pour saisie manuelle"},
                    "instructions": {"type": "object", "description": "Instructions de configuration"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(response_only=True, name="setup_2fa_success", summary="Configuration 2FA réussie", value={}),
            OpenApiExample(
                response_only=True,
                name="2fa_already_enabled",
                summary="2FA déjà activé",
                value={"error": "2FA is already enabled", "code": "2FA_ALREADY_ENABLED"},
            ),
        ],
        request=None,
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        if request.user.is_2fa_enabled:
            return Response(
                {"error": "2FA is already enabled", "code": "2FA_ALREADY_ENABLED"}, status=status.HTTP_400_BAD_REQUEST
            )

        setup_data = totp_service.setup_2fa(request.user)

        return Response(
            {
                "message": "Scan the QR code with your authenticator app, then confirm with a code.",
                "secret": setup_data["secret"],
                "qr_code": setup_data["qr_code"],
                "provisioning_uri": setup_data["provisioning_uri"],
                "backup_codes": setup_data["backup_codes"],
                "warning": "Save the backup codes securely. They will not be shown again.",
            }
        )


class TwoFactorConfirmView(APIView):
    """
    POST {API_PREFIX}/auth/2fa/confirm/
    Confirme l'activation du 2FA avec un code TOTP
    """

    @extend_schema(
        tags=["2FA"],
        summary="Confirmer activation 2FA",
        description="Vérifie le premier code TOTP pour activer le 2FA. "
        "Le code TOTP utilise une fenêtre de 30 secondes avec une tolérance de 1 fenêtre avant/après. "
        "Une seule confirmation est requise après l'initialisation. "
        "Après activation, tous les codes de secours générés sont valides.",
        request=inline_serializer(
            name="TwoFactorConfirmRequest", fields={"code": serializers.CharField(help_text="Code TOTP à 6 chiffres")}
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "is_enabled": {"type": "boolean"},
                    "enabled_at": {"type": "string", "format": "date-time"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="confirm_2fa_success",
                summary="Confirmation 2FA réussie",
                value={"code": "123456"},
            ),
            OpenApiExample(
                response_only=True,
                name="invalid_totp_code",
                summary="Code TOTP invalide",
                value={
                    "error": "Invalid TOTP code",
                    "details": "The code provided is incorrect or outside the valid time window",
                    "code": "INVALID_CODE",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="totp_window_expired",
                summary="Fenêtre TOTP expirée",
                value={
                    "error": "TOTP code expired",
                    "details": "The code is outside the valid 30-second window",
                    "code": "TOTP_WINDOW_EXPIRED",
                },
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get("code", "")
        if not code:
            return Response({"error": "Code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        success, error = totp_service.confirm_2fa(request.user, code)

        if not success:
            return Response({"error": error, "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "2FA enabled successfully", "is_enabled": True})


class TwoFactorDisableView(APIView):
    """
    POST {API_PREFIX}/auth/2fa/disable/
    Désactive le 2FA
    """

    @extend_schema(
        tags=["2FA"],
        summary="Désactiver 2FA",
        description="Désactive le 2FA après vérification du code TOTP ou d'un code de secours. "
        "Pour des raisons de sécurité, le mot de passe de l'utilisateur est également requis. "
        "Une fois désactivé, tous les codes de secours restants sont invalidés. "
        "Cette action est irréversible et nécessitera une nouvelle configuration complète.",
        request=inline_serializer(
            name="TwoFactorDisableRequest",
            fields={
                "code": serializers.CharField(help_text="Code TOTP ou code de secours à 8 chiffres"),
                "password": serializers.CharField(help_text="Mot de passe de l'utilisateur pour confirmation"),
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "is_enabled": {"type": "boolean"},
                    "disabled_at": {"type": "string", "format": "date-time"},
                    "backup_codes_invalidated": {"type": "boolean"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="disable_2fa_totp",
                summary="Désactiver 2FA avec code TOTP",
                value={"code": "123456", "password": "UserP@ss123!"},
            ),
            OpenApiExample(
                request_only=True,
                name="disable_2fa_backup",
                summary="Désactiver 2FA avec code de secours",
                value={"code": "12345678", "password": "UserP@ss123!"},
            ),
            OpenApiExample(
                response_only=True,
                name="invalid_password_disable",
                summary="Mot de passe incorrect",
                value={
                    "error": "Invalid password",
                    "details": "The password provided is incorrect",
                    "code": "INVALID_PASSWORD",
                },
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get("code", "")
        if not code:
            return Response({"error": "Code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        success, error = totp_service.disable_2fa(request.user, code)

        if not success:
            return Response({"error": error, "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "2FA disabled successfully", "is_enabled": False})


class TwoFactorBackupCodesView(APIView):
    """
    POST {API_PREFIX}/auth/2fa/backup-codes/
    Régénère les codes de secours
    """

    @extend_schema(
        tags=["2FA"],
        summary="Régénérer codes de secours",
        description="Génère de nouveaux codes de secours (les anciens sont invalidés). "
        "Requiert un code TOTP valide pour sécurité. "
        "Génère 10 codes alphanumériques à usage unique de 8 caractères. "
        "Les codes ne seront affichés qu'une seule fois. Stockez-les en sécurité.",
        request=inline_serializer(
            name="TwoFactorBackupCodesRequest",
            fields={"code": serializers.CharField(help_text="Code TOTP à 6 chiffres pour validation")},
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "backup_codes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "pattern": "^[A-Z0-9]{8}$",
                            "description": "Code de secours à usage unique",
                        },
                    },
                    "codes_count": {"type": "integer"},
                    "generated_at": {"type": "string", "format": "date-time"},
                    "warning": {"type": "string"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                name="regenerate_backup_codes", summary="Régénérer codes de secours", value={"code": "123456"}
            ),
            OpenApiExample(
                response_only=True,
                name="backup_codes_response",
                summary="Réponse avec nouveaux codes",
                value={
                    "message": "Backup codes regenerated",
                    "backup_codes": [
                        "AB12CD34",
                        "EF56GH78",
                        "IJ90KL12",
                        "MN34OP56",
                        "QR78ST90",
                        "UV12WX34",
                        "YZ56AB78",
                        "CD90EF12",
                        "GH34IJ56",
                        "KL78MN90",
                    ],
                    "codes_count": 10,
                    "warning": "Save these codes securely. They will not be shown again.",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="invalid_totp_backup",
                summary="Code TOTP invalide",
                value={
                    "error": "Invalid TOTP code",
                    "details": "The TOTP code provided is incorrect",
                    "code": "INVALID_CODE",
                },
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        from ..services import totp_service

        code = request.data.get("code", "")
        if not code:
            return Response(
                {"error": "TOTP code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        success, new_codes, error = totp_service.regenerate_backup_codes(request.user, code)

        if not success:
            return Response({"error": error, "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Backup codes regenerated",
                "backup_codes": new_codes,
                "warning": "Save these codes securely. They will not be shown again.",
            }
        )
