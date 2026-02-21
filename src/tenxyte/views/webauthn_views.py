"""
Views for WebAuthn / Passkeys (FIDO2) authentication.

Endpoints:
- POST /api/auth/webauthn/register/begin/      — generate registration challenge
- POST /api/auth/webauthn/register/complete/   — verify + store credential
- POST /api/auth/webauthn/authenticate/begin/  — generate authentication challenge
- POST /api/auth/webauthn/authenticate/complete/ — verify + return JWT
- GET  /api/auth/webauthn/credentials/         — list user's passkeys
- DELETE /api/auth/webauthn/credentials/<id>/  — delete a passkey
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..services.webauthn_service import WebAuthnService
from ..decorators import require_jwt, get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..models import get_user_model

User = get_user_model()


class WebAuthnRegisterBeginView(APIView):
    """
    POST /api/auth/webauthn/register/begin/
    Génère les options de registration WebAuthn (challenge).
    Requiert un utilisateur authentifié.
    """

    @extend_schema(
        tags=['WebAuthn'],
        summary="Commencer l'enregistrement d'une passkey",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        service = WebAuthnService()
        success, data, error = service.begin_registration(request.user)
        if not success:
            return Response({'error': error, 'code': 'WEBAUTHN_ERROR'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WebAuthnRegisterCompleteView(APIView):
    """
    POST /api/auth/webauthn/register/complete/
    Vérifie la réponse du navigateur et enregistre la credential.
    """

    @extend_schema(
        tags=['WebAuthn'],
        summary="Finaliser l'enregistrement d'une passkey",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'challenge_id': {'type': 'integer'},
                    'credential': {'type': 'object'},
                    'device_name': {'type': 'string'},
                },
                'required': ['challenge_id', 'credential'],
            }
        },
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def post(self, request):
        challenge_id = request.data.get('challenge_id')
        credential_data = request.data.get('credential')
        device_name = request.data.get('device_name', '')

        if not challenge_id or not credential_data:
            return Response(
                {'error': 'challenge_id and credential are required', 'code': 'MISSING_FIELDS'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = WebAuthnService()
        success, credential, error = service.complete_registration(
            user=request.user,
            credential_data=credential_data,
            challenge_id=challenge_id,
            device_name=device_name
        )

        if not success:
            return Response({'error': error, 'code': 'WEBAUTHN_REGISTRATION_FAILED'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Passkey registered successfully',
            'credential': {
                'id': credential.id,
                'device_name': credential.device_name,
                'created_at': credential.created_at.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)


class WebAuthnAuthenticateBeginView(APIView):
    """
    POST /api/auth/webauthn/authenticate/begin/
    Génère les options d'authentification WebAuthn.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['WebAuthn'],
        summary="Commencer l'authentification par passkey",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'description': 'Optional — for user-specific credentials'},
                },
            }
        },
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        user = None
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()

        service = WebAuthnService()
        success, data, error = service.begin_authentication(user=user)
        if not success:
            return Response({'error': error, 'code': 'WEBAUTHN_ERROR'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WebAuthnAuthenticateCompleteView(APIView):
    """
    POST /api/auth/webauthn/authenticate/complete/
    Vérifie l'assertion WebAuthn et retourne des tokens JWT.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['WebAuthn'],
        summary="Finaliser l'authentification par passkey",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'challenge_id': {'type': 'integer'},
                    'credential': {'type': 'object'},
                    'device_info': {'type': 'string'},
                },
                'required': ['challenge_id', 'credential'],
            }
        },
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        challenge_id = request.data.get('challenge_id')
        credential_data = request.data.get('credential')

        if not challenge_id or not credential_data:
            return Response(
                {'error': 'challenge_id and credential are required', 'code': 'MISSING_FIELDS'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get('device_info', '') or build_device_info_from_user_agent(
            request.META.get('HTTP_USER_AGENT', '')
        )

        service = WebAuthnService()
        success, data, error = service.complete_authentication(
            credential_data=credential_data,
            challenge_id=challenge_id,
            application=getattr(request, 'application', None),
            ip_address=ip_address,
            device_info=device_info
        )

        if not success:
            return Response({'error': error, 'code': 'WEBAUTHN_AUTH_FAILED'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(data)


class WebAuthnCredentialListView(APIView):
    """
    GET /api/auth/webauthn/credentials/
    Liste les passkeys de l'utilisateur connecté.
    """

    @extend_schema(
        tags=['WebAuthn'],
        summary="Lister les passkeys",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def get(self, request):
        service = WebAuthnService()
        credentials = service.list_credentials(request.user)
        return Response({'credentials': credentials, 'count': len(credentials)})


class WebAuthnCredentialDeleteView(APIView):
    """
    DELETE /api/auth/webauthn/credentials/<credential_id>/
    Supprime une passkey de l'utilisateur connecté.
    """

    @extend_schema(
        tags=['WebAuthn'],
        summary="Supprimer une passkey",
        responses={204: None, 404: OpenApiTypes.OBJECT}
    )
    @require_jwt
    def delete(self, request, credential_id: int):
        service = WebAuthnService()
        success, error = service.delete_credential(request.user, credential_id)
        if not success:
            return Response({'error': error, 'code': 'CREDENTIAL_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
