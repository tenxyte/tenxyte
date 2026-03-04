"""
Views for Magic Link (passwordless) authentication.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiParameter
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..services.magic_link_service import MagicLinkService
from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import MagicLinkRequestThrottle, MagicLinkVerifyThrottle


class MagicLinkRequestView(APIView):
    """
    POST {API_PREFIX}/auth/magic-link/request/
    Demande un magic link par email (authentification sans mot de passe).
    """
    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkRequestThrottle]

    @extend_schema(
        tags=['Magic Link'],
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
            name='MagicLinkRequest',
            fields={
                'email': serializers.EmailField(help_text='Adresse email pour recevoir le magic link'),
                'validation_url': serializers.URLField(help_text='URL pour construire le lien de vérification (obligatoire)')
            }
        ),
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'expires_in_minutes': {'type': 'integer'},
                    'sent_to': {'type': 'string', 'description': 'Email masqué pour sécurité'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'object'}
                }
            },
            429: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'retry_after': {'type': 'integer'}
                }
            },
            503: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(request_only=True, 
                name='request_magic_link',
                summary='Demander magic link',
                value={
                    'email': 'user@example.com',
                    'validation_url': 'https://app.example.com/auth-magic/link/verify'
                }
            ),
            OpenApiExample(response_only=True, 
                name='magic_link_disabled',
                summary='Magic link désactivé',
                value={
                    'error': 'Magic links are disabled',
                    'details': 'Contact administrator to enable magic link authentication'
                }
            ),
            OpenApiExample(response_only=True, 
                name='validation_url_missing',
                summary='Validation URL manquant',
                value={
                    'error': 'Validation URL is required',
                    'code': 'VALIDATION_URL_REQUIRED'
                }
            ),
            OpenApiExample(response_only=True, 
                name='magic_link_rate_limited',
                summary='Limite de rate dépassée',
                value={
                    'error': 'Too many magic link requests',
                    'retry_after': 3600
                }
            )
        ]
    )
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        validation_url = request.data.get('validation_url', '').strip()
        
        if not email:
            return Response(
                {'error': 'Email is required', 'code': 'EMAIL_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validation_url:
            return Response(
                {'error': 'VALIDATION URL is required', 'code': 'VALIDATION_URL_REQUIRED'},
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
            app_name=app_name_str,
            validation_url=validation_url
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
    GET {API_PREFIX}/auth/magic-link/verify/?token=xxx
    Valide un magic link et retourne des tokens JWT.
    """
    permission_classes = [AllowAny]
    throttle_classes = [MagicLinkVerifyThrottle]

    @extend_schema(
        tags=['Magic Link'],
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
                name='token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Token unique du magic link reçu par email'
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/User'},
                    'message': {'type': 'string'},
                    'session_id': {'type': 'string'},
                    'device_id': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='verify_magic_link_success',
                summary='Vérification magic link réussie',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'user': {
                        'id': 42,
                        'email': 'user@example.com',
                        'first_name': 'John',
                        'last_name': 'Doe'
                    },
                    'message': 'Magic link verified successfully'
                }
            ),
            OpenApiExample(response_only=True, 
                name='magic_link_already_used',
                summary='Magic link déjà utilisé',
                value={
                    'error': 'Magic link has already been used',
                    'details': 'This magic link was already used and cannot be used again',
                    'code': 'LINK_ALREADY_USED'
                }
            ),
            OpenApiExample(response_only=True, 
                name='magic_link_expired',
                summary='Magic link expiré',
                value={
                    'error': 'Magic link has expired',
                    'details': 'Please request a new magic link',
                    'code': 'LINK_EXPIRED'
                }
            ),
            OpenApiExample(response_only=True, 
                name='invalid_magic_link_token',
                summary='Token magic link invalide',
                value={
                    'error': 'Invalid magic link token',
                    'details': 'The token provided is not valid',
                    'code': 'INVALID_TOKEN'
                }
            )
        ]
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
            response = Response(
                {'error': error, 'code': 'MAGIC_LINK_INVALID'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            response['Referrer-Policy'] = 'no-referrer'
            return response

        response = Response(data)
        response['Referrer-Policy'] = 'no-referrer'
        return response
