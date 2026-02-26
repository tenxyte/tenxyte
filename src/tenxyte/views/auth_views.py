from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    RegisterSerializer, LoginEmailSerializer, LoginPhoneSerializer,
    RefreshTokenSerializer, UserSerializer
)
from ..services import AuthService, OTPService
from ..services.breach_check_service import breach_check_service
from ..decorators import require_jwt, get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import (
    LoginThrottle, LoginHourlyThrottle,
    RegisterThrottle, RegisterDailyThrottle,
    RefreshTokenThrottle,
)


class RegisterView(APIView):
    """
    POST {API_PREFIX}/auth/register/
    Inscription d'un nouvel utilisateur
    """
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle, RegisterDailyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Inscription d'un nouvel utilisateur",
        description="Crée un nouveau compte utilisateur. Envoie automatiquement un code OTP de vérification si configuré. Vérifie si le mot de passe a été exposé dans des fuites de données.",
        request=RegisterSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/User'},
                    'requires_otp': {'type': 'boolean'},
                    'otp_id': {'type': 'string', 'nullable': True}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'object'},
                    'code': {'type': 'string'}
                }
            },
            429: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'retry_after': {'type': 'integer'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='register_success',
                summary='Inscription réussie',
                value={
                    'email': 'user@example.com',
                    'password': 'SecureP@ss123!',
                    'first_name': 'John',
                    'last_name': 'Doe'
                }
            ),
            OpenApiExample(
                name='breach_password',
                summary='Mot de passe trouvé dans une fuite',
                value={
                    'error': 'Password breach detected',
                    'details': 'This password has been found in known data breaches. Please choose a different password.',
                    'code': 'PASSWORD_BREACH'
                }
            )
        ]
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        auth_service = AuthService()
        login_after = serializer.validated_data.pop('login', False)
        device_info = serializer.validated_data.pop('device_info', '') or build_device_info_from_user_agent(
            request.META.get('HTTP_USER_AGENT', '')
        )
        ip_address = get_client_ip(request)

        # Breach password check (HIBP)
        breach_ok, breach_error = breach_check_service.check_password(
            serializer.validated_data.get('password', '')
        )
        if not breach_ok:
            return Response({
                'error': breach_error,
                'code': 'PASSWORD_BREACHED'
            }, status=status.HTTP_400_BAD_REQUEST)

        success, user, error = auth_service.register_user(
            **serializer.validated_data,
            ip_address=ip_address,
            application=request.application,
            device_info=device_info
        )

        if not success:
            return Response({
                'error': error,
                'code': 'REGISTRATION_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Générer et envoyer les OTP de vérification
        otp_service = OTPService()
        if user.email:
            otp, raw_code = otp_service.generate_email_verification_otp(user)
            otp_service.send_email_otp(user, raw_code, otp.otp_type)

        if serializer.validated_data.get('phone_country_code') and serializer.validated_data.get('phone_number'):
            otp, raw_code = otp_service.generate_phone_verification_otp(user)
            otp_service.send_phone_otp(user, raw_code)

        response_data = {
            'message': 'Registration successful',
            'user': UserSerializer(user).data,
            'verification_required': {
                'email': bool(user.email and not user.is_email_verified),
                'phone': bool(user.phone_number and not user.is_phone_verified)
            }
        }

        if login_after:
            tokens = auth_service.generate_tokens_for_user(
                user=user,
                application=request.application,
                ip_address=ip_address,
                device_info=device_info
            )
            response_data.update(tokens)

        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginEmailView(APIView):
    """
    POST {API_PREFIX}/auth/login/email/
    Connexion par email + password (+ 2FA si activé)
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Connexion par email",
        description="Authentifie un utilisateur avec son email et mot de passe. "
                    "Si 2FA est activé, le champ totp_code est requis. "
                    "Le device fingerprinting est automatiquement effectué via User-Agent. "
                    "Les limites de session et de device sont respectées.",
        request=LoginEmailSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/User'},
                    'requires_2fa': {'type': 'boolean'},
                    'session_id': {'type': 'string'},
                    'device_id': {'type': 'string'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'},
                    'retry_after': {'type': 'integer', 'nullable': True}
                }
            },
            409: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            423: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            429: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'retry_after': {'type': 'integer'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='login_success',
                summary='Connexion réussie',
                value={
                    'email': 'user@example.com',
                    'password': 'SecureP@ss123!'
                }
            ),
            OpenApiExample(
                name='login_with_2fa',
                summary='Connexion avec 2FA',
                value={
                    'email': 'user@example.com',
                    'password': 'SecureP@ss123!',
                    'totp_code': '123456'
                }
            ),
            OpenApiExample(
                name='session_limit_exceeded',
                summary='Limite de session dépassée',
                value={
                    'error': 'Session limit exceeded',
                    'details': 'Maximum concurrent sessions (1) already reached. Please logout from other devices.',
                    'code': 'SESSION_LIMIT_EXCEEDED'
                }
            ),
            OpenApiExample(
                name='account_locked',
                summary='Compte verrouillé',
                value={
                    'error': 'Account locked',
                    'details': 'Account has been locked due to too many failed login attempts.',
                    'code': 'ACCOUNT_LOCKED',
                    'retry_after': 1800
                }
            )
        ]
    )
    def post(self, request):
        serializer = LoginEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        auth_service = AuthService()
        ip_address = get_client_ip(request)

        success, data, error = auth_service.authenticate_by_email(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            application=request.application,
            ip_address=ip_address,
            device_info=serializer.validated_data.get('device_info', '') or build_device_info_from_user_agent(
                request.META.get('HTTP_USER_AGENT', '')
            )
        )

        if not success:
            return Response({
                'error': error,
                'code': 'LOGIN_FAILED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Vérifier 2FA si activé
        user = data.get('_user')  # L'AuthService doit retourner l'user
        if user and user.is_2fa_enabled:
            from ..services import totp_service

            totp_code = serializer.validated_data.get('totp_code', '')
            if not totp_code:
                return Response({
                    'error': '2FA code required',
                    'code': '2FA_REQUIRED',
                    'requires_2fa': True
                }, status=status.HTTP_401_UNAUTHORIZED)

            is_valid, error_msg = totp_service.verify_2fa(user, totp_code)
            if not is_valid:
                return Response({
                    'error': error_msg,
                    'code': 'INVALID_2FA_CODE'
                }, status=status.HTTP_401_UNAUTHORIZED)

        # Retirer l'user de la réponse (on ne veut pas l'exposer)
        if '_user' in data:
            del data['_user']

        return Response(data)


class LoginPhoneView(APIView):
    """
    POST {API_PREFIX}/auth/login/phone/
    Connexion par téléphone + password (+ 2FA si activé)
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Connexion par téléphone",
        description="Authentifie un utilisateur avec son numéro de téléphone et mot de passe. "
                    "Le numéro doit être au format international (ex: +33 pour la France). "
                    "Si 2FA est activé, le champ totp_code est requis. "
                    "Le device fingerprinting est automatiquement effectué.",
        request=LoginPhoneSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/User'},
                    'requires_2fa': {'type': 'boolean'},
                    'session_id': {'type': 'string'},
                    'device_id': {'type': 'string'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'object'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='login_phone_success',
                summary='Connexion par téléphone réussie',
                value={
                    'phone_country_code': '+33',
                    'phone_number': '612345678',
                    'password': 'SecureP@ss123!'
                }
            ),
            OpenApiExample(
                name='login_phone_with_2fa',
                summary='Connexion par téléphone avec 2FA',
                value={
                    'phone_country_code': '+33',
                    'phone_number': '612345678',
                    'password': 'SecureP@ss123!',
                    'totp_code': '123456'
                }
            ),
            OpenApiExample(
                name='invalid_phone_format',
                summary='Format de téléphone invalide',
                value={
                    'error': 'Validation error',
                    'details': {
                        'phone_country_code': ['Invalid country code format. Use +XX format.'],
                        'phone_number': ['Phone number must be 9-15 digits.']
                    }
                }
            )
        ]
    )
    def post(self, request):
        serializer = LoginPhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        auth_service = AuthService()
        ip_address = get_client_ip(request)

        success, data, error = auth_service.authenticate_by_phone(
            country_code=serializer.validated_data['phone_country_code'],
            phone_number=serializer.validated_data['phone_number'],
            password=serializer.validated_data['password'],
            application=request.application,
            ip_address=ip_address,
            device_info=serializer.validated_data.get('device_info', '') or build_device_info_from_user_agent(
                request.META.get('HTTP_USER_AGENT', '')
            )
        )

        if not success:
            return Response({
                'error': error,
                'code': 'LOGIN_FAILED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Vérifier 2FA si activé
        user = data.get('_user')
        if user and user.is_2fa_enabled:
            from ..services import totp_service

            totp_code = serializer.validated_data.get('totp_code', '')
            if not totp_code:
                return Response({
                    'error': '2FA code required',
                    'code': '2FA_REQUIRED',
                    'requires_2fa': True
                }, status=status.HTTP_401_UNAUTHORIZED)

            is_valid, error_msg = totp_service.verify_2fa(user, totp_code)
            if not is_valid:
                return Response({
                    'error': error_msg,
                    'code': 'INVALID_2FA_CODE'
                }, status=status.HTTP_401_UNAUTHORIZED)

        # Retirer l'user de la réponse
        if '_user' in data:
            del data['_user']

        return Response(data)


class RefreshTokenView(APIView):
    """
    POST {API_PREFIX}/auth/refresh/
    Rafraîchir le access token
    """
    permission_classes = [AllowAny]
    throttle_classes = [RefreshTokenThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Rafraîchir le token d'accès",
        description="Génère un nouveau access token à partir d'un refresh token valide. "
                    "Le refresh token est automatiquement roté pour améliorer la sécurité. "
                    "Les refresh tokens expirés ou blacklistés sont rejetés.",
        request=RefreshTokenSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string', 'description': 'Nouveau refresh token (rotation)'},
                    'user': {'$ref': '#/components/schemas/User'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            429: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'retry_after': {'type': 'integer'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='refresh_success',
                summary='Rafraîchissement réussi',
                value={
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            ),
            OpenApiExample(
                name='refresh_expired',
                summary='Refresh token expiré',
                value={
                    'error': 'Refresh token expired',
                    'details': 'Please login again to get a new refresh token',
                    'code': 'REFRESH_EXPIRED'
                }
            ),
            OpenApiExample(
                name='refresh_blacklisted',
                summary='Refresh token blacklisté',
                value={
                    'error': 'Refresh token has been revoked',
                    'details': 'This refresh token has been blacklisted due to logout',
                    'code': 'REFRESH_BLACKLISTED'
                }
            )
        ]
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        auth_service = AuthService()
        success, data, error = auth_service.refresh_access_token(
            refresh_token_str=serializer.validated_data['refresh_token'],
            application=request.application
        )

        if not success:
            return Response({
                'error': error,
                'code': 'REFRESH_FAILED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(data)


class LogoutView(APIView):
    """
    POST {API_PREFIX}/auth/logout/
    Déconnexion (révoque le refresh token)
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary="Déconnexion",
        description="Révoque le refresh token fourni pour déconnecter l'utilisateur. "
                    "Si un access token est fourni dans l'en-tête Authorization, "
                    "il est également blacklisté pour une déconnexion immédiate.",
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                description='Bearer token pour blacklistage immédiat (optionnel)',
                required=False,
                pattern='Bearer [a-zA-Z0-9._-]+'
            )
        ],
        request=RefreshTokenSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'access_token_blacklisted': {'type': 'boolean'},
                    'refresh_token_revoked': {'type': 'boolean'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'object'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='logout_success',
                summary='Déconnexion réussie',
                value={
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            ),
            OpenApiExample(
                name='logout_with_access_token',
                summary='Déconnexion avec blacklistage access token',
                value={
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            )
        ]
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Extract access token from Authorization header for blacklisting
        access_token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            access_token = auth_header[7:]

        auth_service = AuthService()
        auth_service.logout(
            serializer.validated_data['refresh_token'],
            access_token=access_token,
        )

        return Response({'message': 'Logged out successfully'})


class LogoutAllView(APIView):
    """
    POST {API_PREFIX}/auth/logout/all/
    Déconnexion de tous les appareils
    """

    @extend_schema(
        tags=['Auth'],
        summary="Déconnexion de tous les appareils",
        description="Révoque tous les refresh tokens de l'utilisateur connecté. "
                    "L'access token actuel est également blacklisté. "
                    "Utile pour une déconnexion de sécurité sur tous les appareils.",
        request=None,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'devices_logged_out': {'type': 'integer'},
                    'access_token_blacklisted': {'type': 'boolean'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                name='logout_all_success',
                summary='Déconnexion de tous les appareils réussie',
                value={
                    'message': 'Logged out from 3 devices',
                    'devices_logged_out': 3,
                    'access_token_blacklisted': True
                }
            )
        ]
    )
    @require_jwt
    def post(self, request):
        # Extract access token from Authorization header for blacklisting
        access_token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            access_token = auth_header[7:]

        auth_service = AuthService()
        count = auth_service.logout_all_devices(request.user, access_token=access_token)

        return Response({
            'message': f'Logged out from {count} devices'
        })
