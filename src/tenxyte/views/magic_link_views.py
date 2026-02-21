"""
Views for Magic Link (passwordless) authentication.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..services.magic_link_service import MagicLinkService
from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import MagicLinkRequestThrottle, MagicLinkVerifyThrottle


class MagicLinkRequestView(APIView):
    """
    POST /api/auth/magic-link/request/
    Demande un magic link par email (authentification sans mot de passe).
    """
    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkRequestThrottle]

    @extend_schema(
        tags=['Magic Link'],
        summary="Demander un magic link",
        description=(
            "Envoie un lien de connexion à usage unique par email. "
            "Valide pendant TENXYTE_MAGIC_LINK_EXPIRY_MINUTES (défaut: 15 min). "
            "Nécessite TENXYTE_MAGIC_LINK_ENABLED = True."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                },
                'required': ['email'],
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'error': 'Email is required', 'code': 'EMAIL_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get('device_info', '') or build_device_info_from_user_agent(
            request.META.get('HTTP_USER_AGENT', '')
        )
        app_name = getattr(request, 'application', None)
        app_name_str = app_name.name if app_name and hasattr(app_name, 'name') else 'Tenxyte'

        service = MagicLinkService()
        success, error = service.request_magic_link(
            email=email,
            application=getattr(request, 'application', None),
            ip_address=ip_address,
            device_info=device_info,
            app_name=app_name_str
        )

        if not success:
            return Response(
                {'error': error, 'code': 'MAGIC_LINK_FAILED'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Toujours retourner 200 même si l'email n'existe pas (sécurité)
        return Response({
            'message': 'If this email is registered, a magic link has been sent.'
        })


class MagicLinkVerifyView(APIView):
    """
    GET /api/auth/magic-link/verify/?token=xxx
    Valide un magic link et retourne des tokens JWT.
    """
    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkVerifyThrottle]

    @extend_schema(
        tags=['Magic Link'],
        summary="Valider un magic link",
        description=(
            "Valide le token du magic link et retourne des tokens JWT si valide. "
            "Le token est à usage unique — il est invalidé après la première utilisation."
        ),
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request):
        token = request.query_params.get('token', '').strip()
        if not token:
            return Response(
                {'error': 'Token is required', 'code': 'TOKEN_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = request.query_params.get('device_info', '') or build_device_info_from_user_agent(
            request.META.get('HTTP_USER_AGENT', '')
        )

        service = MagicLinkService()
        success, data, error = service.verify_magic_link(
            token=token,
            application=getattr(request, 'application', None),
            ip_address=ip_address,
            device_info=device_info
        )

        if not success:
            return Response(
                {'error': error, 'code': 'MAGIC_LINK_INVALID'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(data)
