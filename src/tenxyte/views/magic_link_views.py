"""
Views for Magic Link (passwordless) authentication - Core facades.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiParameter
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import MagicLinkRequestThrottle, MagicLinkVerifyThrottle

# Core imports
from tenxyte.adapters.django.repositories import DjangoUserRepository, DjangoMagicLinkRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.adapters.django.email_service import DjangoEmailService
from tenxyte.core import MagicLinkService, JWTService, Settings

# Global Core services (lazy initialization)
_core_user_repo = None
_core_magic_link_repo = None
_core_cache = None
_core_settings = None
_core_email_service = None
_core_magic_link_service = None
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


def get_core_email_service():
    global _core_email_service
    if _core_email_service is None:
        _core_email_service = DjangoEmailService()
    return _core_email_service


def get_core_magic_link_repo():
    global _core_magic_link_repo
    if _core_magic_link_repo is None:
        _core_magic_link_repo = DjangoMagicLinkRepository()
    return _core_magic_link_repo


def get_core_magic_link_service():
    global _core_magic_link_service
    if _core_magic_link_service is None:
        _core_magic_link_service = MagicLinkService(
            settings=get_core_settings(),
            repo=get_core_magic_link_repo(),
            user_lookup=get_core_user_repo(),
            email_service=get_core_email_service()
        )
    return _core_magic_link_service


def get_core_jwt_service():
    global _core_jwt_service
    if _core_jwt_service is None:
        _core_jwt_service = JWTService(get_core_settings(), get_core_cache())
    return _core_jwt_service


class MagicLinkRequestView(APIView):
    """
    POST {API_PREFIX}/auth/magic-link/request/
    Demande un magic link par email (authentification sans mot de passe).
    """

    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkRequestThrottle]

    @extend_schema(
        tags=["Magic Link"],
        summary="Demander un magic link",
        description=(
            "Envoie un lien de connexion à usage unique par email. "
            "Valide pendant 15 minutes par défaut (configurable via TENXYTE_MAGIC_LINK_EXPIRY_MINUTES). "
            "Le lien contient un token unique et peut être utilisé une seule fois. "
            "Pour des raisons de sécurité, ne révèle pas si l'email existe. "
            "Limité à 3 requêtes par heure par email. "
            "Nécessite TENXYTE_MAGIC_LINK_ENABLED = True."
        ),
        request=inline_serializer(
            name="MagicLinkRequest",
            fields={
                "email": serializers.EmailField(help_text="Adresse email pour recevoir le magic link"),
                "validation_url": serializers.URLField(
                    help_text="URL pour construire le lien de vérification (obligatoire)"
                ),
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "expires_in_minutes": {"type": "integer"},
                    "sent_to": {"type": "string", "description": "Email masqué pour sécurité"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "object"}}},
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
            503: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="request_magic_link",
                summary="Demander magic link",
                value={"email": "user@example.com", "validation_url": "https://app.example.com/auth-magic/link/verify"},
            ),
            OpenApiExample(
                response_only=True,
                name="magic_link_disabled",
                summary="Magic link désactivé",
                value={
                    "error": "Magic links are disabled",
                    "details": "Contact administrator to enable magic link authentication",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="validation_url_missing",
                summary="Validation URL manquant",
                value={"error": "Validation URL is required", "code": "VALIDATION_URL_REQUIRED"},
            ),
            OpenApiExample(
                response_only=True,
                name="magic_link_rate_limited",
                summary="Limite de rate dépassée",
                value={"error": "Too many magic link requests", "retry_after": 3600},
            ),
        ],
    )
    def post(self, request):
        """Request magic link using Core service."""
        email = request.data.get("email", "").strip().lower()
        validation_url = request.data.get("validation_url", "").strip()

        if not email:
            return Response(
                {"error": "Email is required", "code": "EMAIL_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not validation_url:
            return Response(
                {"error": "Validation URL is required", "code": "VALIDATION_URL_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )
        app_name = getattr(request, "application", None)
        app_name_str = app_name.name if app_name and hasattr(app_name, "name") else "Tenxyte"

        service = get_core_magic_link_service()
        success, error_msg = service.request_magic_link(
            email=email,
            validation_url=validation_url,
            ip_address=ip_address,
            device_info=device_info
        )

        if not success:
            return Response(
                {"error": "Service unavailable", "code": "SERVICE_UNAVAILABLE"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Toujours retourner 200 même si l'email n'existe pas (sécurité)
        return Response({"message": "If this email is registered, a magic link has been sent."})


class MagicLinkVerifyView(APIView):
    """
    GET {API_PREFIX}/auth/magic-link/verify/?token=xxx
    Valide un magic link et retourne des tokens JWT.
    """

    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkVerifyThrottle]

    @extend_schema(
        tags=["Magic Link"],
        summary="Valider un magic link",
        description=(
            "Valide le token du magic link et retourne des tokens JWT si valide. "
            "Le token est à usage unique — il est invalidé après la première utilisation. "
            "Le token expire après 15 minutes par défaut. "
            "Le device fingerprinting est automatiquement effectué via User-Agent. "
            "Une fois utilisé, le token ne peut plus être utilisé même si non expiré."
        ),
        parameters=[
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Token unique du magic link reçu par email",
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "message": {"type": "string"},
                    "session_id": {"type": "string"},
                    "device_id": {"type": "string"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
            401: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                name="verify_magic_link_success",
                summary="Vérification magic link réussie",
                value={
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "user": {"id": 42, "email": "user@example.com", "first_name": "John", "last_name": "Doe"},
                    "message": "Magic link verified successfully",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="magic_link_already_used",
                summary="Magic link déjà utilisé",
                value={
                    "error": "Magic link has already been used",
                    "details": "This magic link was already used and cannot be used again",
                    "code": "LINK_ALREADY_USED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="magic_link_expired",
                summary="Magic link expiré",
                value={
                    "error": "Magic link has expired",
                    "details": "Please request a new magic link",
                    "code": "LINK_EXPIRED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="invalid_magic_link_token",
                summary="Token magic link invalide",
                value={
                    "error": "Invalid magic link token",
                    "details": "The token provided is not valid",
                    "code": "INVALID_TOKEN",
                },
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Verify magic link using Core service."""
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"error": "Token is required", "code": "TOKEN_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = request.query_params.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        # Verify magic link via Core service
        service = get_core_magic_link_service()
        auth_result = service.verify_magic_link(
            token=token,
            ip_address=ip_address,
            device_info=device_info
        )

        if not auth_result.success:
            return Response(
                {"error": auth_result.error, "code": "MAGIC_LINK_INVALID"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate JWT tokens via Core service
        jwt_service = get_core_jwt_service()
        app_id = str(request.application.id) if hasattr(request, 'application') and request.application else "default"
        access_token = jwt_service.generate_access_token(auth_result.user_id, application_id=app_id)
        refresh_token = jwt_service.generate_refresh_token(auth_result.user_id, application_id=app_id, device_info=device_info)

        # Get user for response
        from ..models import get_user_model
        from ..serializers import UserSerializer
        User = get_user_model()
        try:
            user = User.objects.get(id=auth_result.user_id)
            user_data = UserSerializer(user).data
        except User.DoesNotExist:
            user_data = {"id": auth_result.user_id}

        response_data = {
            "access": access_token,
            "refresh": refresh_token,
            "user": user_data,
            "message": "Magic link verified successfully",
            "session_id": auth_result.session_id if hasattr(auth_result, 'session_id') else None,
            "device_id": auth_result.device_id if hasattr(auth_result, 'device_id') else None,
        }

        response = Response(response_data)
        response["Referrer-Policy"] = "no-referrer"
        return response
