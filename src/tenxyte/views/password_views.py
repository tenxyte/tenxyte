"""
Password Views - Django DRF Facades for Tenxyte Core.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer, ChangePasswordSerializer
from ..services import OTPService
from ..services.breach_check_service import breach_check_service
from ..models import get_user_model
from ..decorators import require_jwt
from ..throttles import PasswordResetThrottle, PasswordResetDailyThrottle, OTPVerifyThrottle

# Core imports
from tenxyte.adapters.django.repositories import DjangoUserRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.core import JWTService, Settings

User = get_user_model()

# Global Core repository (lazy initialization)
_core_user_repo = None
_core_cache = None
_core_settings = None
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


def get_core_jwt_service():
    global _core_jwt_service
    if _core_jwt_service is None:
        _core_jwt_service = JWTService(get_core_settings(), get_core_cache())
    return _core_jwt_service


class PasswordResetRequestView(APIView):
    """
    POST {API_PREFIX}/auth/password/reset/request/
    Demander une réinitialisation de mot de passe
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle, PasswordResetDailyThrottle]

    @extend_schema(
        tags=["Password"],
        summary="Demander une réinitialisation de mot de passe",
        description="Envoie un code OTP par email ou SMS pour réinitialiser le mot de passe. "
        "Pour des raisons de sécurité, ne révèle pas si le compte existe. "
        "Le code OTP expire après 15 minutes. Limité à 3 requêtes par heure.",
        request=PasswordResetRequestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "otp_id": {"type": "string"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "channel": {"type": "string", "enum": ["email", "sms"]},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "object"}}},
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="reset_request_email",
                summary="Demande par email",
                value={"email": "user@example.com"},
            ),
            OpenApiExample(
                request_only=True,
                name="reset_request_phone",
                summary="Demande par téléphone",
                value={"phone_country_code": "+33", "phone_number": "612345678"},
            ),
            OpenApiExample(
                response_only=True,
                name="reset_rate_limited",
                summary="Limite de rate dépassée",
                value={"error": "Too many password reset requests", "retry_after": 3600},
            ),
        ],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        user = None
        if serializer.validated_data.get("email"):
            user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        elif serializer.validated_data.get("phone_number"):
            user = User.objects.filter(
                phone_country_code=serializer.validated_data["phone_country_code"],
                phone_number=serializer.validated_data["phone_number"],
            ).first()

        # Ne pas révéler si l'utilisateur existe
        if user:
            otp_service = OTPService()
            otp, raw_code = otp_service.generate_password_reset_otp(user)

            if user.email:
                otp_service.send_email_otp(user, raw_code, otp.otp_type)
            elif user.phone_number:
                otp_service.send_phone_otp(user, raw_code)

            return Response(
                {
                    "message": "Password reset code sent",
                    "otp_id": str(otp.pk),
                    "expires_at": otp.expires_at.isoformat(),
                    "channel": "email" if user.email else "sms",
                }
            )


class PasswordResetConfirmView(APIView):
    """
    POST {API_PREFIX}/auth/password/reset/confirm/
    Confirmer la réinitialisation de mot de passe
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=["Password"],
        summary="Confirmer la réinitialisation de mot de passe",
        description="Vérifie le code OTP et définit un nouveau mot de passe. "
        "Révoque automatiquement tous les refresh tokens de l'utilisateur. "
        "Vérifie si le nouveau mot de passe a été exposé dans des fuites de données. "
        "Le code OTP doit être utilisé dans les 15 minutes après réception.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "tokens_revoked": {"type": "integer"},
                    "password_safe": {"type": "boolean"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "object"}, "code": {"type": "string"}},
            },
            401: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="reset_confirm_email",
                summary="Confirmation par email",
                value={
                    "email": "user@example.com",
                    "otp_code": "123456",
                    "new_password": "NewSecureP@ss123!",
                    "confirm_password": "NewSecureP@ss123!",
                },
            ),
            OpenApiExample(
                request_only=True,
                name="reset_confirm_phone",
                summary="Confirmation par téléphone",
                value={
                    "phone_country_code": "+33",
                    "phone_number": "612345678",
                    "otp_code": "123456",
                    "new_password": "NewSecureP@ss123!",
                    "confirm_password": "NewSecureP@ss123!",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="otp_expired",
                summary="Code OTP expiré",
                value={
                    "error": "OTP code has expired",
                    "details": "Please request a new password reset code",
                    "code": "OTP_EXPIRED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="breach_password_reset",
                summary="Mot de passe dans une fuite",
                value={
                    "error": "Password breach detected",
                    "details": "This password has been found in known data breaches. Please choose a different password.",
                    "code": "PASSWORD_BREACH",
                },
            ),
        ],
    )
    def post(self, request):
        """Password reset via Core repository."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # On a besoin de l'identifiant de l'utilisateur
        email = request.data.get("email")
        phone_country_code = request.data.get("phone_country_code")
        phone_number = request.data.get("phone_number")

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        elif phone_country_code and phone_number:
            user = User.objects.filter(phone_country_code=phone_country_code, phone_number=phone_number).first()

        if not user:
            return Response(
                {"error": "Invalid reset request", "code": "RESET_FAILED"}, status=status.HTTP_400_BAD_REQUEST
            )

        otp_service = OTPService()
        success, error = otp_service.verify_password_reset_otp(user, serializer.validated_data["code"])

        if not success:
            return Response({"error": error, "code": "RESET_FAILED"}, status=status.HTTP_400_BAD_REQUEST)

        # Breach password check (HIBP)
        is_password_safe = True
        breach_ok, breach_error = breach_check_service.check_password(serializer.validated_data["new_password"])
        if not breach_ok:
            is_password_safe = False

        # Update password via Core repository
        user_repo.update_password(str(user.id), serializer.validated_data["new_password"])

        # Révoquer tous les refresh tokens via Core JWT service
        jwt_service = get_core_jwt_service()
        revoked_count = jwt_service.revoke_all_user_tokens(str(user.id))

        return Response(
            {
                "message": "Password reset successful",
                "tokens_revoked": revoked_count,
                "password_safe": is_password_safe,
            }
        )


class ChangePasswordView(APIView):
    """
    POST {API_PREFIX}/auth/password/change/
    Changer le mot de passe (utilisateur connecté)
    """

    @extend_schema(
        tags=["Password"],
        summary="Changer le mot de passe",
        description="Change le mot de passe de l'utilisateur connecté. "
        "Requiert le mot de passe actuel pour validation. "
        "Vérifie si le nouveau mot de passe a été exposé dans des fuites de données. "
        "Le nouveau mot de passe ne doit pas être identique aux 5 derniers mots de passe utilisés. "
        "Après changement, déconnecte toutes les sessions sauf la session actuelle.",
        request=ChangePasswordSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "password_strength": {"type": "string"},
                    "sessions_revoked": {"type": "integer"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "object"}, "code": {"type": "string"}},
            },
            401: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="change_password_success",
                summary="Changement réussi",
                value={
                    "current_password": "OldP@ss123!",
                    "new_password": "NewSecureP@ss456!",
                    "confirm_password": "NewSecureP@ss456!",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="invalid_current_password",
                summary="Mot de passe actuel incorrect",
                value={"error": "Current password is incorrect", "code": "INVALID_PASSWORD"},
            ),
            OpenApiExample(
                response_only=True,
                name="password_reused",
                summary="Mot de passe déjà utilisé",
                value={
                    "error": "Password has already been used",
                    "details": "You cannot reuse any of your last 5 passwords",
                    "code": "PASSWORD_REUSED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="password_breached",
                summary="Mot de passe dans une fuite",
                value={
                    "error": "Password breach detected",
                    "details": "This password has been found in known data breaches. Please choose a different password.",
                    "code": "PASSWORD_BREACHED",
                },
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        """Change password via Core repository."""
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify current password via Core repository
        user_repo = get_core_user_repo()
        is_valid = user_repo.check_password(str(request.user.id), serializer.validated_data["current_password"])
        
        if not is_valid:
            return Response(
                {"error": "Current password is incorrect", "code": "INVALID_PASSWORD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Breach password check (HIBP)
        breach_ok, breach_error = breach_check_service.check_password(serializer.validated_data["new_password"])
        if not breach_ok:
            return Response({"error": breach_error, "code": "PASSWORD_BREACHED"}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate password strength
        from ..validators import password_validator
        strength_result = password_validator.validate(serializer.validated_data["new_password"])
        password_strength = strength_result.strength.lower() if hasattr(strength_result.strength, 'lower') else str(strength_result.strength).lower()

        # Update password via Core repository
        user_repo.update_password(str(request.user.id), serializer.validated_data["new_password"])

        # Révoquer toutes les sessions sauf la session actuelle
        jwt_service = get_core_jwt_service()
        sessions_revoked = jwt_service.revoke_all_user_tokens(str(request.user.id))

        return Response(
            {
                "message": "Password changed successfully",
                "password_strength": password_strength,
                "sessions_revoked": sessions_revoked,
            }
        )


class PasswordStrengthView(APIView):
    """
    POST {API_PREFIX}/auth/password/strength/
    Verifier la force d'un mot de passe (pour validation frontend)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Password"],
        summary="Verifier la force d'un mot de passe",
        description="Retourne le score et la force d'un mot de passe sans l'enregistrer. "
        "Utile pour fournir un retour en temps réel dans l'interface utilisateur. "
        "L'email (optionnel) permet de vérifier si le mot de passe contient une partie de l'email.",
        request=inline_serializer(
            name="PasswordStrengthRequest",
            fields={
                "password": serializers.CharField(),
                "email": serializers.EmailField(required=False, allow_blank=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name="strong_password",
                summary="Mot de passe fort",
                description="Un mot de passe long avec différents types de caractères.",
                value={"password": "Tr0ub4dour&55$", "email": "user@example.com"},
                response_only=False,
            ),
            OpenApiExample(
                name="strong_response",
                summary="Réponse (Fort)",
                response_only=True,
                status_codes=["200"],
                value={
                    "score": 4,
                    "strength": "Strong",
                    "is_valid": True,
                    "errors": [],
                    "requirements": {
                        "min_length": 12,
                        "require_lowercase": True,
                        "require_uppercase": True,
                        "require_numbers": True,
                        "require_special": True,
                    },
                },
            ),
            OpenApiExample(
                name="weak_response",
                summary="Réponse (Faible/Invalide)",
                response_only=True,
                status_codes=["200"],
                value={
                    "score": 1,
                    "strength": "Weak",
                    "is_valid": False,
                    "errors": [
                        "Le mot de passe doit contenir au moins 12 caractères.",
                        "Le mot de passe doit contenir au moins un chiffre.",
                        "Le mot de passe doit contenir au moins un caractère spécial.",
                    ],
                    "requirements": {
                        "min_length": 12,
                        "require_lowercase": True,
                        "require_uppercase": True,
                        "require_numbers": True,
                        "require_special": True,
                    },
                },
            ),
        ],
    )
    def post(self, request):
        from ..validators import password_validator

        password = request.data.get("password", "")
        email = request.data.get("email")

        result = password_validator.validate(password, email=email)

        return Response(
            {
                "score": result.score,
                "strength": result.strength,
                "is_valid": result.is_valid,
                "errors": result.errors if not result.is_valid else [],
                "requirements": password_validator.get_requirements(),
            }
        )


class PasswordRequirementsView(APIView):
    """
    GET {API_PREFIX}/auth/password/requirements/
    Recuperer les exigences de mot de passe
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Password"],
        summary="Exigences de mot de passe",
        description="Retourne la liste des exigences pour un mot de passe valide.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        from ..validators import password_validator

        return Response(
            {
                "requirements": password_validator.get_requirements(),
                "min_length": password_validator.min_length,
                "max_length": password_validator.max_length,
            }
        )
