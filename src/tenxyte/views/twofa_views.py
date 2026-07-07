"""
2FA Views - Django DRF Facades for Tenxyte Core.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..decorators import require_jwt

# Core imports
from tenxyte.adapters.django.repositories import DjangoUserRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.adapters.django.crypto_service import DjangoCryptoService
from tenxyte.adapters.django.totp_storage import DjangoTOTPStorage
from tenxyte.adapters.django.email_service import DjangoEmailService
from tenxyte.core import TOTPService, Settings
from tenxyte.core.jwt_service import JWTService
from tenxyte.services.reauth_service import ReauthService

# Global Core services (lazy initialization)
_core_user_repo = None
_core_cache = None
_core_settings = None
_core_crypto = None
_core_totp_storage = None
_core_email = None
_core_totp_service = None
_core_jwt_service = None


def get_core_user_repo():
    global _core_user_repo
    if _core_user_repo is None:
        _core_user_repo = DjangoUserRepository()
    return _core_user_repo


def get_core_cache():
    global _core_cache
    if _core_cache is None:
        _core_cache = DjangoCacheService()
    return _core_cache


def get_core_settings():
    global _core_settings
    if _core_settings is None:
        _core_settings = Settings(DjangoSettingsProvider())
    return _core_settings


def get_core_crypto():
    global _core_crypto
    if _core_crypto is None:
        _core_crypto = DjangoCryptoService(get_core_settings())
    return _core_crypto


def get_core_totp_storage():
    global _core_totp_storage
    if _core_totp_storage is None:
        _core_totp_storage = DjangoTOTPStorage()
    return _core_totp_storage


def get_core_email():
    global _core_email
    if _core_email is None:
        _core_email = DjangoEmailService()
    return _core_email


def get_core_totp_service():
    global _core_totp_service
    if _core_totp_service is None:
        _core_totp_service = TOTPService(
            settings=get_core_settings(), replay_protection=get_core_cache()  # Use cache for replay protection
        )
    return _core_totp_service


def get_core_jwt_service():
    global _core_jwt_service
    if _core_jwt_service is None:
        _core_jwt_service = JWTService(settings=get_core_settings(), blacklist_service=DjangoCacheService())
    return _core_jwt_service


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
    @require_jwt(allowed_scopes=["2fa_setup_only"])
    def post(self, request):
        """Setup 2FA using Core TOTPService.

        Accepts both full-scope tokens and the short-lived bootstrap token
        (scope="2fa_setup_only") issued during login when an admin must
        configure 2FA. Tokens carrying any other restricted scope are rejected
        with HTTP 403 INSUFFICIENT_SCOPE by the require_jwt decorator.
        """
        if request.user.is_2fa_enabled:
            return Response(
                {"error": "2FA is already enabled", "code": "2FA_ALREADY_ENABLED"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Use Core TOTP service with storage
        totp_service = get_core_totp_service()
        storage = get_core_totp_storage()
        setup_result = totp_service.setup_2fa(
            user_id=str(request.user.id), email=request.user.email or str(request.user.id), storage=storage
        )

        return Response(
            {
                "message": "Scan the QR code with your authenticator app, then confirm with a code.",
                "secret": setup_result.secret,
                "qr_code": setup_result.qr_code,
                "provisioning_uri": setup_result.provisioning_uri,
                "backup_codes": setup_result.backup_codes,
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
    @require_jwt(allowed_scopes=["2fa_setup_only"])
    def post(self, request):
        """Confirm 2FA using Core TOTPService.

        Accepts both full-scope tokens and the short-lived bootstrap token
        (scope="2fa_setup_only") issued during login when an admin must
        configure 2FA. Tokens carrying any other restricted scope are rejected
        with HTTP 403 INSUFFICIENT_SCOPE by the require_jwt decorator.

        When the request is authenticated with a bootstrap token, a fresh
        full-scope token pair is issued after 2FA is activated so the admin can
        continue without re-authenticating, and the bootstrap token is
        invalidated. Full-scope token confirmations are unchanged.
        """
        code = request.data.get("code", "")
        if not code:
            return Response({"error": "Code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        # Use Core TOTP service with storage
        totp_service = get_core_totp_service()
        storage = get_core_totp_storage()
        is_valid, error_msg = totp_service.confirm_2fa_setup(user_id=str(request.user.id), code=code, storage=storage)

        if not is_valid:
            return Response(
                {"error": error_msg or "Invalid TOTP code", "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Enable 2FA via Core user repository
        user_repo = get_core_user_repo()
        user_repo.enable_mfa(str(request.user.id), mfa_type="totp")

        response_data = {"message": "2FA enabled successfully", "is_enabled": True}

        # Bootstrap upgrade: if this confirmation was performed with a restricted
        # bootstrap token (scope="2fa_setup_only"), issue a new full-scope token
        # pair so the admin can proceed with normal authenticated operations
        # without re-logging in, then invalidate the bootstrap token.
        if getattr(request, "jwt_scope", None) == "2fa_setup_only":
            jwt_service = get_core_jwt_service()
            app_id = str(request.application.id) if getattr(request, "application", None) else "default"
            token_pair = jwt_service.generate_new_token_pair(
                user_id=str(request.user.id),
                application_id=app_id,
            )
            response_data.update(
                {
                    "access_token": token_pair.access_token,
                    "refresh_token": token_pair.refresh_token,
                    "token_type": "Bearer",
                    "expires_in": get_core_settings().jwt_access_token_lifetime,
                }
            )

            # Invalidate the bootstrap token so it cannot be reused after the
            # upgrade. Best-effort: the bootstrap token is short-lived (15 min)
            # and expires on its own even if blacklisting is unavailable.
            try:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    bootstrap_token = auth_header[7:]
                    jwt_service.blacklist_token(
                        bootstrap_token,
                        user_id=str(request.user.id),
                        reason="2fa_bootstrap_completed",
                    )
            except Exception:  # pragma: no cover - defensive, blacklist optional
                pass

        return Response(response_data)


class TwoFactorDisableView(APIView):
    """
    POST {API_PREFIX}/auth/2fa/disable/
    Désactive le 2FA
    """

    @extend_schema(
        tags=["2FA"],
        summary="Désactiver 2FA",
        description="Désactive le 2FA après vérification du code TOTP ou d'un code de secours. "
        "Pour des raisons de sécurité, le mot de passe de l'utilisateur est également requis, "
        "sauf si un code OTP de réauthentification valide (`otp_code`) est fourni à la place. "
        "Une fois désactivé, tous les codes de secours restants sont invalidés. "
        "Cette action est irréversible et nécessitera une nouvelle configuration complète.",
        request=inline_serializer(
            name="TwoFactorDisableRequest",
            fields={
                "code": serializers.CharField(help_text="Code TOTP ou code de secours à 8 chiffres"),
                "password": serializers.CharField(
                    required=False, allow_blank=True, help_text="Mot de passe de l'utilisateur pour confirmation"
                ),
                "otp_code": serializers.CharField(
                    required=False,
                    allow_blank=True,
                    help_text="Code OTP de réauthentification, alternative au mot de passe",
                ),
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
        """Disable 2FA using Core TOTPService."""
        code = request.data.get("code", "")
        if not code:
            return Response({"error": "Code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify current password OR a fresh OTP_Reauth_Challenge (Requirement 6.4/6.5/6.6)
        reauth_service = ReauthService()
        is_valid_reauth, reauth_error_code, reauth_error_message = reauth_service.verify(
            request.user,
            password=request.data.get("password", ""),
            otp_code=request.data.get("otp_code", ""),
        )

        if not is_valid_reauth:
            return Response(
                {"error": reauth_error_message, "code": reauth_error_code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use Core TOTP service with storage
        totp_service = get_core_totp_service()
        storage = get_core_totp_storage()
        is_valid, error_msg = totp_service.disable_2fa(user_id=str(request.user.id), code=code, storage=storage)

        if not is_valid:
            return Response(
                {"error": error_msg or "Invalid code", "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Disable 2FA via Core user repository
        user_repo = get_core_user_repo()
        user_repo.disable_mfa(str(request.user.id))

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
                request_only=True,
                name="regenerate_backup_codes",
                summary="Régénérer codes de secours",
                value={"code": "123456"},
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
        """Regenerate backup codes using Core TOTPService."""
        code = request.data.get("code", "")
        if not code:
            return Response(
                {"error": "TOTP code is required", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Use Core TOTP service with storage
        totp_service = get_core_totp_service()
        storage = get_core_totp_storage()
        is_valid, plain_codes, error_msg = totp_service.regenerate_backup_codes(
            user_id=str(request.user.id), code=code, storage=storage
        )

        if not is_valid:
            return Response(
                {"error": error_msg or "Invalid TOTP code", "code": "INVALID_CODE"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Backup codes regenerated",
                "backup_codes": plain_codes,
                "warning": "Save these codes securely. They will not be shown again.",
            }
        )
