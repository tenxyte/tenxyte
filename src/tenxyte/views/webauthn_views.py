"""
Views for WebAuthn / Passkeys (FIDO2) authentication - Core facades.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.

Endpoints:
- POST {API_PREFIX}/auth/webauthn/register/begin/      — generate registration challenge
- POST {API_PREFIX}/auth/webauthn/register/complete/   — verify + store credential
- POST {API_PREFIX}/auth/webauthn/authenticate/begin/  — generate authentication challenge
- POST {API_PREFIX}/auth/webauthn/authenticate/complete/ — verify + return JWT
- GET  {API_PREFIX}/auth/webauthn/credentials/         — list user's passkeys
- DELETE {API_PREFIX}/auth/webauthn/credentials/<id>/  — delete a passkey
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..decorators import require_jwt, get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..models import get_user_model

# Core imports
from tenxyte.adapters.django.repositories import DjangoUserRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.adapters.django.webauthn_storage import DjangoWebAuthnStorage
from tenxyte.core import WebAuthnService, JWTService, Settings

User = get_user_model()

# Global Core services (lazy initialization)
_core_user_repo = None
_core_cache = None
_core_settings = None
_core_webauthn_storage = None
_core_webauthn_service = None
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


def get_core_webauthn_storage():
    global _core_webauthn_storage
    if _core_webauthn_storage is None:
        _core_webauthn_storage = DjangoWebAuthnStorage()
    return _core_webauthn_storage


def get_core_webauthn_service():
    global _core_webauthn_service
    if _core_webauthn_service is None:
        storage = get_core_webauthn_storage()
        _core_webauthn_service = WebAuthnService(
            settings=get_core_settings(),
            credential_repo=storage,
            challenge_repo=storage
        )
    return _core_webauthn_service


def get_core_jwt_service():
    global _core_jwt_service
    if _core_jwt_service is None:
        _core_jwt_service = JWTService(get_core_settings(), get_core_cache())
    return _core_jwt_service


class WebAuthnRegisterBeginView(APIView):
    """
    POST {API_PREFIX}/auth/webauthn/register/begin/
    Génère les options de registration WebAuthn (challenge).
    Requiert un utilisateur authentifié.
    """

    @extend_schema(
        tags=["WebAuthn"],
        summary="Commencer l'enregistrement d'une passkey",
        description="Génère un challenge WebAuthn pour l'enregistrement d'une nouvelle passkey. "
        "Le challenge expire après 5 minutes. "
        "Supporte l'authentification biométrique (Face ID, Touch ID, Windows Hello). "
        "Les options incluent user verification (required/preferred/discouraged) "
        "et les algorithmes cryptographiques supportés (ES256, RS256, EdDSA).",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "challenge": {"type": "string", "description": "Challenge base64url encodé"},
                    "rp": {"type": "object", "properties": {"name": {"type": "string"}, "id": {"type": "string"}}},
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "displayName": {"type": "string"},
                        },
                    },
                    "pubKeyCredParams": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"type": {"type": "string"}, "alg": {"type": "integer"}},
                        },
                    },
                    "timeout": {"type": "integer", "description": "Timeout en millisecondes"},
                    "authenticatorSelection": {
                        "type": "object",
                        "properties": {
                            "authenticatorAttachment": {"type": "string"},
                            "userVerification": {"type": "string"},
                            "requireResidentKey": {"type": "boolean"},
                        },
                    },
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        request=None,
        examples=[
            OpenApiExample(
                response_only=True, name="register_begin_success", summary="Début enregistrement réussi", value={}
            ),
            OpenApiExample(
                response_only=True,
                name="webauthn_disabled",
                summary="WebAuthn désactivé",
                value={"error": "WebAuthn is not enabled", "code": "WEBAUTHN_DISABLED"},
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        """Begin WebAuthn registration using Core service."""
        service = get_core_webauthn_service()
        success, options, error = service.begin_registration(
            user_id=str(request.user.id),
            email=request.user.email or str(request.user.id),
            display_name=request.user.email or str(request.user.id)
        )
        if not success:
            return Response(
                {"error": error or "WebAuthn registration failed", "code": "WEBAUTHN_ERROR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(options)


class WebAuthnRegisterCompleteView(APIView):
    """
    POST {API_PREFIX}/auth/webauthn/register/complete/
    Vérifie la réponse du navigateur et enregistre la credential.
    """

    @extend_schema(
        tags=["WebAuthn"],
        summary="Finaliser l'enregistrement d'une passkey",
        description="Vérifie la réponse WebAuthn du navigateur et enregistre la credential. "
        "Prévient les doublons via credential exclusion. "
        "Valide l'attestation et le format de la clé publique. "
        "Enregistre les métadonnées du device (nom, type, date).",
        request=inline_serializer(
            name="WebAuthnRegisterCompleteRequest",
            fields={
                "challenge_id": serializers.IntegerField(help_text="ID du challenge généré"),
                "credential": serializers.DictField(help_text="Credential WebAuthn du navigateur"),
                "device_name": serializers.CharField(
                    required=False, allow_blank=True, help_text="Nom optionnel du device"
                ),
            },
        ),
        responses={
            201: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "credential": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="register_complete_success",
                summary="Enregistrement réussi",
                value={
                    "challenge_id": 123,
                    "credential": {"id": "credentialId", "rawId": "rawId", "response": {}},
                    "device_name": "iPhone 14",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="credential_already_exists",
                summary="Credential déjà existante",
                value={"error": "Credential already registered", "code": "CREDENTIAL_EXISTS"},
            ),
        ],
    )
    @require_jwt
    def post(self, request):
        """Complete WebAuthn registration using Core service."""
        credential_data = request.data.get("credential")
        device_name = request.data.get("device_name", "")

        if not credential_data:
            return Response(
                {"error": "credential is required", "code": "MISSING_FIELDS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = get_core_webauthn_service()
        challenge_id = request.data.get("challenge_id")
        result = service.complete_registration(
            user_id=str(request.user.id),
            credential_data=credential_data,
            challenge_id=str(challenge_id) if challenge_id else "",
            device_name=device_name
        )
        
        if not result.success:
            return Response(
                {"error": result.error or "Registration failed", "code": "REGISTRATION_FAILED"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Passkey registered successfully",
                "credential": {
                    "id": result.credential.id,
                    "device_name": result.credential.device_name,
                    "created_at": result.credential.created_at.isoformat() if hasattr(result.credential.created_at, 'isoformat') else str(result.credential.created_at),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class WebAuthnAuthenticateBeginView(APIView):
    """
    POST {API_PREFIX}/auth/webauthn/authenticate/begin/
    Génère les options d'authentification WebAuthn.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["WebAuthn"],
        summary="Commencer l'authentification par passkey",
        description="Génère un challenge WebAuthn pour l'authentification. "
        "Supporte les passkeys resident keys (username-less). "
        "Le challenge expire après 5 minutes. "
        "User verification configurable (required/preferred/discouraged). "
        "AllowCredentials peut être vide pour resident keys ou spécifique.",
        request=inline_serializer(
            name="WebAuthnAuthenticateBeginRequest",
            fields={
                "email": serializers.EmailField(
                    required=False, help_text="Optionnel — pour credentials utilisateur spécifiques"
                )
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "challenge": {"type": "string", "description": "Challenge base64url encodé"},
                    "rpId": {"type": "string"},
                    "allowCredentials": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"id": {"type": "string"}, "type": {"type": "string"}},
                        },
                    },
                    "userVerification": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(name="auth_begin_resident_key", summary="Auth resident key", value={}),
            OpenApiExample(
                request_only=True,
                name="auth_begin_user_specific",
                summary="Auth utilisateur spécifique",
                value={"email": "user@example.com"},
            ),
        ],
    )
    def post(self, request):
        """Begin WebAuthn authentication using Core service."""
        email = request.data.get("email", "").strip().lower()
        
        user_id = None
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                user_id = str(user.id)

        service = get_core_webauthn_service()
        success, options, error = service.begin_authentication(user_id=user_id)
        if not success:
            return Response(
                {"error": error or "WebAuthn authentication failed", "code": "WEBAUTHN_ERROR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(options)


class WebAuthnAuthenticateCompleteView(APIView):
    """
    POST {API_PREFIX}/auth/webauthn/authenticate/complete/
    Vérifie l'assertion WebAuthn et retourne des tokens JWT.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["WebAuthn"],
        summary="Finaliser l'authentification par passkey",
        description="Vérifie l'assertion WebAuthn et retourne des tokens JWT. "
        "Valide le signature, le challenge et le counter de la credential. "
        "Le counter prévient les attaques replay. "
        "Device fingerprinting automatique via User-Agent. "
        "Supporte les resident keys (username-less authentication).",
        request=inline_serializer(
            name="WebAuthnAuthenticateCompleteRequest",
            fields={
                "challenge_id": serializers.IntegerField(help_text="ID du challenge généré"),
                "credential": serializers.DictField(help_text="Assertion WebAuthn du navigateur"),
                "device_info": serializers.CharField(
                    required=False, allow_blank=True, help_text="Informations sur le device (optionnel)"
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
                    "credential_used": {"type": "string"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
            401: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="auth_complete_success",
                summary="Authentification réussie",
                value={"challenge_id": 456, "credential": {"id": "credentialId", "rawId": "rawId", "response": {}}},
            ),
            OpenApiExample(
                response_only=True,
                name="counter_replay_attack",
                summary="Attaque replay détectée",
                value={"error": "Credential counter replay detected", "code": "REPLAY_ATTACK"},
            ),
        ],
    )
    def post(self, request):
        """Complete WebAuthn authentication using Core service."""
        credential_data = request.data.get("credential")

        if not credential_data:
            return Response(
                {"error": "credential is required", "code": "MISSING_FIELDS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip_address = get_client_ip(request)
        device_info = request.data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        service = get_core_webauthn_service()
        challenge_id = request.data.get("challenge_id")
        auth_result = service.complete_authentication(
            credential_data=credential_data,
            challenge_id=str(challenge_id) if challenge_id else ""
        )
        
        if not auth_result.success:
            return Response(
                {"error": auth_result.error or "Authentication failed", "code": "AUTH_FAILED"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate JWT tokens via Core service
        jwt_service = get_core_jwt_service()
        access_token = jwt_service.generate_access_token(auth_result.user_id)
        refresh_token = jwt_service.generate_refresh_token(auth_result.user_id, device_info=device_info)

        # Get user for response
        from ..serializers import UserSerializer
        try:
            user = User.objects.get(id=auth_result.user_id)
            user_data = UserSerializer(user).data
        except User.DoesNotExist:
            user_data = {"id": auth_result.user_id}

        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": user_data,
            "message": "Authentication successful",
            "credential_used": auth_result.credential_id,
        })


class WebAuthnCredentialListView(APIView):
    """
    GET {API_PREFIX}/auth/webauthn/credentials/
    Liste les passkeys de l'utilisateur connecté.
    """

    @extend_schema(
        tags=["WebAuthn"],
        summary="Lister les passkeys",
        description="Retourne la liste des passkeys enregistrées pour l'utilisateur. "
        "Inclut les métadonnées (nom, date de création, dernière utilisation). "
        "Le credential ID est masqué pour sécurité. "
        "Affiche le type d'authentificateur (platform, cross-platform).",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "credentials": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "device_name": {"type": "string"},
                                "created_at": {"type": "string", "format": "date-time"},
                                "last_used_at": {"type": "string", "format": "date-time", "nullable": True},
                                "authenticator_type": {"type": "string"},
                                "is_resident_key": {"type": "boolean"},
                            },
                        },
                    },
                    "count": {"type": "integer"},
                },
            }
        },
    )
    @require_jwt
    def get(self, request):
        """List credentials using Core service."""
        service = get_core_webauthn_service()
        credentials = service.list_credentials(user_id=str(request.user.id))
        return Response({"credentials": credentials, "count": len(credentials)})


class WebAuthnCredentialDeleteView(APIView):
    """
    DELETE {API_PREFIX}/auth/webauthn/credentials/<credential_id>/
    Supprime une passkey de l'utilisateur connecté.
    """

    @extend_schema(
        tags=["WebAuthn"],
        summary="Supprimer une passkey",
        description="Supprime définitivement une passkey de l'utilisateur. "
        "Action irréversible. "
        "Prévient l'accès depuis ce device à l'avenir. "
        "Vérifie que la credential appartient bien à l'utilisateur.",
        parameters=[
            OpenApiParameter(
                name="credential_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="ID de la passkey à supprimer",
            )
        ],
        responses={
            204: {"description": "Passkey supprimée avec succès"},
            404: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        },
    )
    @require_jwt
    def delete(self, request, credential_id: int):
        """Delete credential using Core service."""
        service = get_core_webauthn_service()
        success = service.delete_credential(
            credential_id=str(credential_id),
            user_id=str(request.user.id)
        )
        if not success:
            return Response({"error": "Credential not found", "code": "CREDENTIAL_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
