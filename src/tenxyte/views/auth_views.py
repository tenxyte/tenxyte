from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    RegisterSerializer, LoginEmailSerializer, LoginPhoneSerializer,
    RefreshTokenSerializer, GoogleAuthSerializer, UserSerializer
)
from ..services import AuthService, OTPService, GoogleAuthService
from ..decorators import require_jwt, get_client_ip
from ..device_info import build_device_info_from_user_agent
from ..throttles import (
    LoginThrottle, LoginHourlyThrottle,
    RegisterThrottle, RegisterDailyThrottle,
    RefreshTokenThrottle, GoogleAuthThrottle,
)


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Inscription d'un nouvel utilisateur
    """
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle, RegisterDailyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Inscription d'un nouvel utilisateur",
        description="Crée un nouveau compte utilisateur. Envoie automatiquement un code OTP de vérification.",
        request=RegisterSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
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
    POST /api/auth/login/email/
    Connexion par email + password (+ 2FA si activé)
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Connexion par email",
        description="Authentifie un utilisateur avec son email et mot de passe. "
                    "Si 2FA est activé, le champ totp_code est requis.",
        request=LoginEmailSerializer,
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT}
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
    POST /api/auth/login/phone/
    Connexion par téléphone + password (+ 2FA si activé)
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Connexion par téléphone",
        description="Authentifie un utilisateur avec son numéro de téléphone et mot de passe. "
                    "Si 2FA est activé, le champ totp_code est requis.",
        request=LoginPhoneSerializer,
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT}
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


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/
    Authentification via Google OAuth
    """
    permission_classes = [AllowAny]
    throttle_classes = [GoogleAuthThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Authentification Google OAuth",
        description="Authentifie un utilisateur via Google OAuth. Accepte id_token, access_token ou code.",
        request=GoogleAuthSerializer,
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        google_service = GoogleAuthService()
        ip_address = get_client_ip(request)
        google_data = None

        # Essayer de récupérer les données Google
        if serializer.validated_data.get('id_token'):
            google_data = google_service.verify_id_token(
                serializer.validated_data['id_token']
            )
        elif serializer.validated_data.get('access_token'):
            google_data = google_service.get_user_info(
                serializer.validated_data['access_token']
            )
        elif serializer.validated_data.get('code'):
            tokens = google_service.exchange_code_for_tokens(
                serializer.validated_data['code'],
                serializer.validated_data['redirect_uri']
            )
            if tokens and 'access_token' in tokens:
                google_data = google_service.get_user_info(tokens['access_token'])

        if not google_data:
            return Response({
                'error': 'Invalid Google credentials',
                'code': 'GOOGLE_AUTH_FAILED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        success, data, error = google_service.authenticate_with_google(
            google_data=google_data,
            application=request.application,
            ip_address=ip_address,
            device_info=serializer.validated_data.get('device_info', '') or build_device_info_from_user_agent(
                request.META.get('HTTP_USER_AGENT', '')
            )
        )

        if not success:
            return Response({
                'error': error,
                'code': 'GOOGLE_AUTH_FAILED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(data)


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/
    Rafraîchir le access token
    """
    permission_classes = [AllowAny]
    throttle_classes = [RefreshTokenThrottle]

    @extend_schema(
        tags=['Auth'],
        summary="Rafraîchir le token d'accès",
        description="Génère un nouveau access token à partir d'un refresh token valide.",
        request=RefreshTokenSerializer,
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT}
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
    POST /api/auth/logout/
    Déconnexion (révoque le refresh token)
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary="Déconnexion",
        description="Révoque le refresh token fourni pour déconnecter l'utilisateur.",
        request=RefreshTokenSerializer,
        responses={200: OpenApiTypes.OBJECT}
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
    POST /api/auth/logout/all/
    Déconnexion de tous les appareils
    """

    @extend_schema(
        tags=['Auth'],
        summary="Déconnexion de tous les appareils",
        description="Révoque tous les refresh tokens de l'utilisateur connecté.",
        request=None,
        responses={200: OpenApiTypes.OBJECT}
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
