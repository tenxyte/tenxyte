from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..serializers import RequestOTPSerializer, VerifyOTPSerializer
from ..services import OTPService
from ..decorators import require_jwt
from ..throttles import OTPRequestThrottle, OTPVerifyThrottle


class RequestOTPView(APIView):
    """
    POST /api/auth/otp/request/
    Demander un code OTP
    """
    throttle_classes = [OTPRequestThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Demander un code OTP",
        description="Génère et envoie un code OTP par email ou SMS selon le type demandé.",
        request=RequestOTPSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
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
    POST /api/auth/otp/verify/email/
    Vérifier le code OTP email
    """
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Vérifier le code OTP email",
        description="Vérifie le code OTP envoyé par email pour valider l'adresse email.",
        request=VerifyOTPSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
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
    POST /api/auth/otp/verify/phone/
    Vérifier le code OTP téléphone
    """
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=['OTP'],
        summary="Vérifier le code OTP téléphone",
        description="Vérifie le code OTP envoyé par SMS pour valider le numéro de téléphone.",
        request=VerifyOTPSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
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
