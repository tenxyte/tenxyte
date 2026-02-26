from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from ..serializers import RequestOTPSerializer, VerifyOTPSerializer
from ..services import OTPService
from ..decorators import require_jwt
from ..throttles import OTPRequestThrottle, OTPVerifyThrottle


class RequestOTPView(APIView):
    """
    POST {API_PREFIX}/auth/otp/request/
    Demander un code OTP
    """
    throttle_classes = [OTPRequestThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Demander un code OTP",
        description="Génère et envoie un code OTP par email ou SMS selon le type demandé. "
                    "Le code expire après 10 minutes. Limité à 5 requêtes par heure par utilisateur. "
                    "Supporte les types : email_verification, phone_verification, password_reset.",
        request=RequestOTPSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'otp_id': {'type': 'string'},
                    'expires_at': {'type': 'string', 'format': 'date-time'},
                    'channel': {'type': 'string', 'enum': ['email', 'sms']},
                    'masked_recipient': {'type': 'string'}
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
                name='request_email_otp',
                summary='Demande OTP par email',
                value={
                    'otp_type': 'email_verification'
                }
            ),
            OpenApiExample(
                name='request_phone_otp',
                summary='Demande OTP par SMS',
                value={
                    'otp_type': 'phone_verification'
                }
            ),
            OpenApiExample(
                name='no_email_error',
                summary='Aucune adresse email',
                value={
                    'error': 'No email address on account',
                    'code': 'NO_EMAIL'
                }
            ),
            OpenApiExample(
                name='otp_rate_limited',
                summary='Limite OTP dépassée',
                value={
                    'error': 'Too many OTP requests',
                    'retry_after': 300
                }
            )
        ]
    )
    @require_jwt
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_service = OTPService()
        otp_type = serializer.validated_data['otp_type']

        if otp_type == 'email':
            if not request.user.email:
                return Response({
                    'error': 'No email address on account',
                    'code': 'NO_EMAIL'
                }, status=status.HTTP_400_BAD_REQUEST)

            otp, raw_code = otp_service.generate_email_verification_otp(request.user)
            otp_service.send_email_otp(request.user, raw_code, otp.otp_type)

        elif otp_type == 'phone':
            if not request.user.phone_number:
                return Response({
                    'error': 'No phone number on account',
                    'code': 'NO_PHONE'
                }, status=status.HTTP_400_BAD_REQUEST)

            otp, raw_code = otp_service.generate_phone_verification_otp(request.user)
            otp_service.send_phone_otp(request.user, raw_code)

        return Response({'message': 'OTP sent successfully'})


class VerifyEmailOTPView(APIView):
    """
    POST {API_PREFIX}/auth/otp/verify/email/
    Vérifier le code OTP email
    """
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Vérifier le code OTP email",
        description="Vérifie le code OTP envoyé par email pour valider l'adresse email. "
                    "Le code doit être utilisé dans les 10 minutes après réception. "
                    "Après 3 tentatives échouées, le code est invalidé. "
                    "Une fois vérifiée, l'adresse email ne peut plus être modifiée.",
        request=VerifyOTPSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'email_verified': {'type': 'boolean'},
                    'verified_at': {'type': 'string', 'format': 'date-time'}
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
                name='verify_email_success',
                summary='Vérification email réussie',
                value={
                    'code': '123456'
                }
            ),
            OpenApiExample(
                name='invalid_otp_code',
                summary='Code OTP invalide',
                value={
                    'error': 'Invalid OTP code',
                    'details': 'The code provided is incorrect or has expired',
                    'code': 'INVALID_OTP'
                }
            ),
            OpenApiExample(
                name='otp_expired',
                summary='Code OTP expiré',
                value={
                    'error': 'OTP code has expired',
                    'details': 'Please request a new verification code',
                    'code': 'OTP_EXPIRED'
                }
            ),
            OpenApiExample(
                name='max_attempts_reached',
                summary='Maximum de tentatives atteint',
                value={
                    'error': 'Maximum OTP attempts reached',
                    'details': 'Please request a new verification code',
                    'code': 'MAX_ATTEMPTS_REACHED'
                }
            )
        ]
    )
    @require_jwt
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_service = OTPService()
        success, error = otp_service.verify_email_otp(
            request.user,
            serializer.validated_data['code']
        )

        if not success:
            return Response({
                'error': error,
                'code': 'OTP_VERIFICATION_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Email verified successfully'})


class VerifyPhoneOTPView(APIView):
    """
    POST {API_PREFIX}/auth/otp/verify/phone/
    Vérifier le code OTP téléphone
    """
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Vérifier le code OTP téléphone",
        description="Vérifie le code OTP envoyé par SMS pour valider le numéro de téléphone. "
                    "Le code doit être utilisé dans les 10 minutes après réception. "
                    "Après 3 tentatives échouées, le code est invalidé. "
                    "Le numéro de téléphone doit être au format international enregistré.",
        request=VerifyOTPSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'phone_verified': {'type': 'boolean'},
                    'verified_at': {'type': 'string', 'format': 'date-time'},
                    'phone_number': {'type': 'string'}
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
                name='verify_phone_success',
                summary='Vérification téléphone réussie',
                value={
                    'code': '123456'
                }
            ),
            OpenApiExample(
                name='invalid_phone_otp',
                summary='Code OTP téléphone invalide',
                value={
                    'error': 'Invalid OTP code',
                    'details': 'The code provided is incorrect or has expired',
                    'code': 'INVALID_OTP'
                }
            ),
            OpenApiExample(
                name='phone_not_verified',
                summary='Téléphone non vérifié',
                value={
                    'error': 'Phone number not verified',
                    'details': 'Please request an OTP verification first',
                    'code': 'PHONE_NOT_VERIFIED'
                }
            ),
            OpenApiExample(
                name='otp_window_expired',
                summary='Fenêtre de vérification expirée',
                value={
                    'error': 'OTP verification window expired',
                    'details': 'The 10-minute verification window has passed',
                    'code': 'OTP_WINDOW_EXPIRED'
                }
            )
        ]
    )
    @require_jwt
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_service = OTPService()
        success, error = otp_service.verify_phone_otp(
            request.user,
            serializer.validated_data['code']
        )

        if not success:
            return Response({
                'error': error,
                'code': 'OTP_VERIFICATION_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Phone verified successfully'})
