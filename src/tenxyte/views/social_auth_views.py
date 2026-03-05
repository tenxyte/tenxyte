"""
Views for Social Login Multi-Provider authentication.

Endpoint générique: POST {API_PREFIX}/auth/social/<provider>/
Providers supportés: google, github, microsoft, facebook
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from ..services.social_auth_service import SocialAuthService, get_provider
from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import LoginThrottle, LoginHourlyThrottle


class SocialAuthView(APIView):
    """
    POST {API_PREFIX}/auth/social/<provider>/
    Authentification via un provider social OAuth2.

    Providers supportés: google, github, microsoft, facebook

    Accepte:
    - access_token: token d'accès OAuth2
    - code + redirect_uri: authorization code flow
    - id_token: pour Google uniquement
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=["Social Auth"],
        summary="Authentification sociale OAuth2",
        description=(
            "Authentifie un utilisateur via un provider OAuth2 (google, github, microsoft, facebook). "
            "Accepte un access_token, un authorization code, ou un id_token (Google uniquement). "
            "Crée automatiquement un compte si l'utilisateur n'existe pas encore. "
            "Device fingerprinting automatique via User-Agent. "
            "Rate limiting appliqué par provider (10 requêtes/heure)."
        ),
        parameters=[
            OpenApiParameter(
                name="provider",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                enum=["google", "github", "microsoft", "facebook"],
                description="Provider OAuth2 à utiliser",
            )
        ],
        request=inline_serializer(
            name="SocialAuthRequest",
            fields={
                "access_token": serializers.CharField(required=False, help_text="OAuth2 access token du provider"),
                "code": serializers.CharField(required=False, help_text="Authorization code flow"),
                "redirect_uri": serializers.CharField(
                    required=False, allow_blank=True, help_text="URI de redirection (requis avec code)"
                ),
                "id_token": serializers.CharField(
                    required=False, allow_blank=True, help_text="Google ID token uniquement"
                ),
                "device_info": serializers.CharField(
                    required=False, allow_blank=True, help_text="Informations device (optionnel)"
                ),
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "message": {"type": "string"},
                    "provider": {"type": "string"},
                    "is_new_user": {"type": "boolean"},
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "code": {"type": "string"},
                    "supported_providers": {"type": "array", "items": {"type": "string"}},
                },
            },
            401: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                name="social_auth_google_token",
                summary="Auth Google avec access_token",
                value={"access_token": "ya29.a0AfH6SMC..."},
            ),
            OpenApiExample(
                name="social_auth_github_code",
                summary="Auth GitHub avec authorization code",
                value={"code": "e72e28cde4a64a2e9e5c", "redirect_uri": "https://app.example.com/auth/github/callback"},
            ),
            OpenApiExample(
                name="social_auth_google_id_token",
                summary="Auth Google avec ID token",
                value={"id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."},
            ),
            OpenApiExample(
                response_only=True,
                name="provider_not_supported",
                summary="Provider non supporté",
                value={
                    "error": "Provider 'linkedin' is not supported or not enabled.",
                    "code": "PROVIDER_NOT_SUPPORTED",
                    "supported_providers": ["google", "github", "microsoft", "facebook"],
                },
            ),
            OpenApiExample(
                response_only=True,
                name="missing_redirect_uri",
                summary="Redirect URI manquant",
                value={"error": "redirect_uri is required with code", "code": "REDIRECT_URI_REQUIRED"},
            ),
        ],
    )
    def post(self, request, provider: str):
        provider_name = provider.lower()

        # Validate provider
        oauth_provider = get_provider(provider_name)
        if not oauth_provider:
            return Response(
                {
                    "error": f"Provider '{provider_name}' is not supported or not enabled.",
                    "code": "PROVIDER_NOT_SUPPORTED",
                    "supported_providers": ["google", "github", "microsoft", "facebook"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        # Retrieve user data from provider
        user_data = None

        if request.data.get("access_token"):
            user_data = oauth_provider.get_user_info(request.data["access_token"])

        elif request.data.get("code"):
            redirect_uri = request.data.get("redirect_uri", "")
            if not redirect_uri:
                return Response(
                    {"error": "redirect_uri is required with code", "code": "REDIRECT_URI_REQUIRED"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tokens = oauth_provider.exchange_code(request.data["code"], redirect_uri)
            if tokens and tokens.get("access_token"):
                user_data = oauth_provider.get_user_info(tokens["access_token"])

        elif request.data.get("id_token") and provider_name == "google":
            # Google-specific: verify id_token directly
            user_data = oauth_provider.verify_id_token(request.data["id_token"])

        else:
            return Response(
                {
                    "error": "Provide access_token, code+redirect_uri, or id_token (Google only).",
                    "code": "MISSING_CREDENTIALS",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_data:
            return Response(
                {
                    "error": f"Could not retrieve user data from {provider_name}.",
                    "code": "PROVIDER_AUTH_FAILED",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Authenticate / create user
        social_service = SocialAuthService()
        success, data, error = social_service.authenticate(
            provider_name=provider_name,
            user_data=user_data,
            application=getattr(request, "application", None),
            ip_address=ip_address,
            device_info=device_info,
        )

        if not success:
            return Response({"error": error, "code": "SOCIAL_AUTH_FAILED"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(data)


class SocialAuthCallbackView(APIView):
    """
    GET {API_PREFIX}/auth/social/<provider>/callback/
    Callback OAuth2 pour le authorization code flow.

    Généralement utilisé par les applications web traditionnelles
    où le provider redirige l'utilisateur vers ce endpoint
    après autorisation avec un authorization code.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Social Auth"],
        summary="Callback OAuth2",
        description=(
            "Endpoint de callback pour le flow OAuth2 authorization code. "
            "Reçoit le code d'autorisation du provider et le redirect_uri. "
            "Échange le code contre des tokens et authentifie l'utilisateur. "
            "Retourne les tokens JWT ou redirige vers l'application cliente."
        ),
        parameters=[
            OpenApiParameter(
                name="provider",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                enum=["google", "github", "microsoft", "facebook"],
                description="Provider OAuth2",
            ),
            OpenApiParameter(
                name="code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Authorization code du provider",
            ),
            OpenApiParameter(
                name="state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Parameter CSRF/state pour sécurité",
            ),
            OpenApiParameter(
                name="redirect_uri",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="URI de redirection originale",
            ),
        ],
        responses={
            200: inline_serializer(
                name="SocialCallbackResponse",
                fields={
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                    "provider": serializers.CharField(),
                    "is_new_user": serializers.BooleanField(),
                },
            ),
            302: inline_serializer(
                name="SocialCallbackRedirect",
                fields={
                    "location": serializers.CharField(help_text="URL de redirection avec tokens en paramètres query"),
                },
            ),
            400: inline_serializer(
                name="SocialCallbackError",
                fields={
                    "error": serializers.CharField(),
                    "code": serializers.CharField(),
                },
            ),
            401: inline_serializer(
                name="SocialCallbackUnauthorized",
                fields={
                    "error": serializers.CharField(),
                    "code": serializers.CharField(),
                },
            ),
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="callback_success",
                summary="Callback réussi",
                value={
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "provider": "google",
                    "is_new_user": False,
                },
            ),
            OpenApiExample(
                response_only=True,
                name="callback_invalid_code",
                summary="Code invalide",
                value={"error": "Invalid authorization code", "code": "INVALID_CODE"},
            ),
        ],
    )
    def get(self, request, provider: str):
        provider_name = provider.lower()

        # Validate provider
        oauth_provider = get_provider(provider_name)
        if not oauth_provider:
            return Response(
                {"error": f"Provider '{provider_name}' is not supported.", "code": "PROVIDER_NOT_SUPPORTED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = request.GET.get("code")
        redirect_uri = request.GET.get("redirect_uri")

        if not code:
            return Response(
                {"error": "Authorization code is required", "code": "MISSING_CODE"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not redirect_uri:
            return Response(
                {"error": "redirect_uri is required", "code": "MISSING_REDIRECT_URI"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange code for tokens
        try:
            tokens = oauth_provider.exchange_code(code, redirect_uri)
            if not tokens or not tokens.get("access_token"):
                return Response(
                    {"error": "Failed to exchange authorization code", "code": "CODE_EXCHANGE_FAILED"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Get user info
            user_data = oauth_provider.get_user_info(tokens["access_token"])
            if not user_data:
                return Response(
                    {"error": f"Could not retrieve user data from {provider_name}", "code": "PROVIDER_AUTH_FAILED"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Authenticate / create user
            ip_address = get_client_ip(request)
            device_info = build_device_info_from_user_agent(request.META.get("HTTP_USER_AGENT", ""))

            social_service = SocialAuthService()
            success, data, error = social_service.authenticate(
                provider_name=provider_name,
                user_data=user_data,
                application=getattr(request, "application", None),
                ip_address=ip_address,
                device_info=device_info,
            )

            if not success:
                return Response({"error": error, "code": "SOCIAL_AUTH_FAILED"}, status=status.HTTP_401_UNAUTHORIZED)

            return Response(data)

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"OAuth callback failed: {e}", exc_info=True)
            return Response(
                {
                    "error": "OAuth2 callback processing failed",
                    "code": "CALLBACK_ERROR",
                    "details": "An unexpected error occurred during authentication.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
