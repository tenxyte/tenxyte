"""
Views for Social Login Multi-Provider authentication.

Endpoint générique: POST /api/auth/social/<provider>/
Providers supportés: google, github, microsoft, facebook
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..services.social_auth_service import SocialAuthService, get_provider
from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import GoogleAuthThrottle


class SocialAuthView(APIView):
    """
    POST /api/auth/social/<provider>/
    Authentification via un provider social OAuth2.

    Providers supportés: google, github, microsoft, facebook

    Accepte:
    - access_token: token d'accès OAuth2
    - code + redirect_uri: authorization code flow
    - id_token: pour Google uniquement
    """
    permission_classes = [AllowAny]
    throttle_classes = [GoogleAuthThrottle]

    @extend_schema(
        tags=['Social Auth'],
        summary="Authentification sociale OAuth2",
        description=(
            "Authentifie un utilisateur via un provider OAuth2 (google, github, microsoft, facebook). "
            "Accepte un access_token, un authorization code, ou un id_token (Google uniquement). "
            "Crée automatiquement un compte si l'utilisateur n'existe pas encore."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string', 'description': 'OAuth2 access token'},
                    'code': {'type': 'string', 'description': 'Authorization code'},
                    'redirect_uri': {'type': 'string', 'description': 'Required with code'},
                    'id_token': {'type': 'string', 'description': 'Google ID token only'},
                    'device_info': {'type': 'string'},
                },
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request, provider: str):
        provider_name = provider.lower()

        # Validate provider
        oauth_provider = get_provider(provider_name)
        if not oauth_provider:
            return Response(
                {
                    'error': f"Provider '{provider_name}' is not supported or not enabled.",
                    'code': 'PROVIDER_NOT_SUPPORTED',
                    'supported_providers': ['google', 'github', 'microsoft', 'facebook'],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get('device_info', '') or build_device_info_from_user_agent(
            request.META.get('HTTP_USER_AGENT', '')
        )

        # Retrieve user data from provider
        user_data = None

        if request.data.get('access_token'):
            user_data = oauth_provider.get_user_info(request.data['access_token'])

        elif request.data.get('code'):
            redirect_uri = request.data.get('redirect_uri', '')
            if not redirect_uri:
                return Response(
                    {'error': 'redirect_uri is required with code', 'code': 'REDIRECT_URI_REQUIRED'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tokens = oauth_provider.exchange_code(request.data['code'], redirect_uri)
            if tokens and tokens.get('access_token'):
                user_data = oauth_provider.get_user_info(tokens['access_token'])

        elif request.data.get('id_token') and provider_name == 'google':
            # Google-specific: verify id_token directly
            user_data = oauth_provider.verify_id_token(request.data['id_token'])

        else:
            return Response(
                {
                    'error': 'Provide access_token, code+redirect_uri, or id_token (Google only).',
                    'code': 'MISSING_CREDENTIALS',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_data:
            return Response(
                {
                    'error': f'Could not retrieve user data from {provider_name}.',
                    'code': 'PROVIDER_AUTH_FAILED',
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Authenticate / create user
        social_service = SocialAuthService()
        success, data, error = social_service.authenticate(
            provider_name=provider_name,
            user_data=user_data,
            application=getattr(request, 'application', None),
            ip_address=ip_address,
            device_info=device_info
        )

        if not success:
            return Response(
                {'error': error, 'code': 'SOCIAL_AUTH_FAILED'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(data)
