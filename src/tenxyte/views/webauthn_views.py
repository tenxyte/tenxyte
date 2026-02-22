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
from drf_spectacular.utils import extend_schema, OpenApiExample
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
        description="Génère un challenge WebAuthn pour l'enregistrement d'une nouvelle passkey. "
                    "Le challenge expire après 5 minutes. "
                    "Supporte l'authentification biométrique (Face ID, Touch ID, Windows Hello). "
                    "Les options incluent user verification (required/preferred/discouraged) "
                    "et les algorithmes cryptographiques supportés (ES256, RS256, EdDSA).",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'challenge': {'type': 'string', 'description': 'Challenge base64url encodé'},
                    'rp': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'id': {'type': 'string'}
                        }
                    },
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'displayName': {'type': 'string'}
                        }
                    },
                    'pubKeyCredParams': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'type': {'type': 'string'},
                                'alg': {'type': 'integer'}
                            }
                        }
                    },
                    'timeout': {'type': 'integer', 'description': 'Timeout en millisecondes'},
                    'authenticatorSelection': {
                        'type': 'object',
                        'properties': {
                            'authenticatorAttachment': {'type': 'string'},
                            'userVerification': {'type': 'string'},
                            'requireResidentKey': {'type': 'boolean'}
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='register_begin_success',
                summary='Début enregistrement réussi',
                value={}
            ),
            OpenApiExample(
                name='webauthn_disabled',
                summary='WebAuthn désactivé',
                value={
                    'error': 'WebAuthn is not enabled',
                    'code': 'WEBAUTHN_DISABLED'
                }
            )
        ]
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
        description="Vérifie la réponse WebAuthn du navigateur et enregistre la credential. "
                    "Prévient les doublons via credential exclusion. "
                    "Valide l'attestation et le format de la clé publique. "
                    "Enregistre les métadonnées du device (nom, type, date).",
        request={
            'type': 'object',
            'properties': {
                'challenge_id': {'type': 'integer', 'description': 'ID du challenge généré'},
                'credential': {'type': 'object', 'description': 'Credential WebAuthn du navigateur'},
                'device_name': {'type': 'string', 'description': 'Nom optionnel du device'}
            },
            'required': ['challenge_id', 'credential']
        },
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'credential': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'created_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='register_complete_success',
                summary='Enregistrement réussi',
                value={
                    'challenge_id': 123,
                    'credential': {'id': 'credentialId', 'rawId': 'rawId', 'response': {}},
                    'device_name': 'iPhone 14'
                }
            ),
            OpenApiExample(
                name='credential_already_exists',
                summary='Credential déjà existante',
                value={
                    'error': 'Credential already registered',
                    'code': 'CREDENTIAL_EXISTS'
                }
            )
        ]
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
        description="Génère un challenge WebAuthn pour l'authentification. "
                    "Supporte les passkeys resident keys (username-less). "
                    "Le challenge expire après 5 minutes. "
                    "User verification configurable (required/preferred/discouraged). "
                    "AllowCredentials peut être vide pour resident keys ou spécifique.",
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email', 'description': 'Optionnel — pour credentials utilisateur spécifiques'}
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'challenge': {'type': 'string', 'description': 'Challenge base64url encodé'},
                    'rpId': {'type': 'string'},
                    'allowCredentials': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'type': {'type': 'string'}
                            }
                        }
                    },
                    'userVerification': {'type': 'string'},
                    'timeout': {'type': 'integer'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='auth_begin_resident_key',
                summary='Auth resident key',
                value={}
            ),
            OpenApiExample(
                name='auth_begin_user_specific',
                summary='Auth utilisateur spécifique',
                value={
                    'email': 'user@example.com'
                }
            )
        ]
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
        description="Vérifie l'assertion WebAuthn et retourne des tokens JWT. "
                    "Valide le signature, le challenge et le counter de la credential. "
                    "Le counter prévient les attaques replay. "
                    "Device fingerprinting automatique via User-Agent. "
                    "Supporte les resident keys (username-less authentication).",
        request={
            'type': 'object',
            'properties': {
                'challenge_id': {'type': 'integer', 'description': 'ID du challenge généré'},
                'credential': {'type': 'object', 'description': 'Assertion WebAuthn du navigateur'},
                'device_info': {'type': 'string', 'description': 'Informations sur le device (optionnel)'}
            },
            'required': ['challenge_id', 'credential']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/User'},
                    'message': {'type': 'string'},
                    'credential_used': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='auth_complete_success',
                summary='Authentification réussie',
                value={
                    'challenge_id': 456,
                    'credential': {'id': 'credentialId', 'rawId': 'rawId', 'response': {}}
                }
            ),
            OpenApiExample(
                name='counter_replay_attack',
                summary='Attaque replay détectée',
                value={
                    'error': 'Credential counter replay detected',
                    'code': 'REPLAY_ATTACK'
                }
            )
        ]
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
        description="Retourne la liste des passkeys enregistrées pour l'utilisateur. "
                    "Inclut les métadonnées (nom, date de création, dernière utilisation). "
                    "Le credential ID est masqué pour sécurité. "
                    "Affiche le type d'authentificateur (platform, cross-platform).",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'credentials': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'device_name': {'type': 'string'},
                                'created_at': {'type': 'string', 'format': 'date-time'},
                                'last_used_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                                'authenticator_type': {'type': 'string'},
                                'is_resident_key': {'type': 'boolean'}
                            }
                        }
                    },
                    'count': {'type': 'integer'}
                }
            }
        }
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
        description="Supprime définitivement une passkey de l'utilisateur. "
                    "Action irréversible. "
                    "Prévient l'accès depuis ce device à l'avenir. "
                    "Vérifie que la credential appartient bien à l'utilisateur.",
        parameters=[
            {
                'name': 'credential_id',
                'in': 'path',
                'required': True,
                'type': 'integer',
                'description': 'ID de la passkey à supprimer'
            }
        ],
        responses={
            204: {'description': 'Passkey supprimée avec succès'},
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            }
        }
    )
    @require_jwt
    def delete(self, request, credential_id: int):
        service = WebAuthnService()
        success, error = service.delete_credential(request.user, credential_id)
        if not success:
            return Response({'error': error, 'code': 'CREDENTIAL_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
