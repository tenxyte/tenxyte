"""
Login OTP Views - Connexion passwordless par OTP téléphonique.

Ces vues répliquent le comportement de sécurité (application requise,
anti-énumération) et la forme de réponse des vues d'authentification
existantes (`RegisterView`, `LoginPhoneView`, `RequestOTPView`), sans jamais
exiger de mot de passe.
"""

import secrets
import uuid
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..conf import auth_settings
from ..decorators import get_client_ip
from ..device_info import build_device_info_from_user_agent, get_device_summary
from ..serializers import LoginOTPRequestSerializer, LoginOTPVerifySerializer, UserSerializer
from ..services import OTPService
from ..throttles import LoginOTPRequestThrottle, LoginOTPRequestDailyThrottle, OTPVerifyThrottle
from .auth_views import (
    get_core_jwt_service,
    get_core_settings,
    get_core_user_repo,
    register_user_with_core,
    validate_application_required,
)


def _otp_response_payload(otp, channel: str = "sms") -> dict:
    """Forme de réponse partagée entre les chemins compte-existant,
    auto-register et anti-énumération (mêmes clés et mêmes types)."""
    return {
        "message": "OTP sent",
        "otp_id": str(otp.pk),
        "expires_at": otp.expires_at.isoformat(),
        "channel": channel,
    }


class LoginOTPRequestView(APIView):
    """
    POST {API_PREFIX}/auth/login/otp/request/
    Demande un code OTP pour connexion passwordless par téléphone.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginOTPRequestThrottle, LoginOTPRequestDailyThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Demander un code OTP de connexion passwordless",
        description="Envoie un code OTP par SMS permettant de se connecter sans mot de passe. "
        "Si aucun compte n'existe pour ce numéro et que l'auto-enregistrement est activé, "
        "un nouveau compte passwordless est créé. Sinon, une réponse anti-énumération "
        "de forme identique est retournée sans effet de bord.",
        request=LoginOTPRequestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "otp_id": {"type": "string"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "channel": {"type": "string", "enum": ["sms"]},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "object"}, "code": {"type": "string"}},
            },
            404: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
        },
        examples=[
            OpenApiExample(
                name="login_otp_request",
                summary="Demande de code OTP de connexion",
                value={"phone_country_code": "+33", "phone_number": "612345678"},
            ),
        ],
    )
    def post(self, request):
        # Feature-disabled: reject every request without generating or
        # sending anything, and without leaking whether the feature exists.
        if not auth_settings.OTP_LOGIN_ENABLED:
            return Response(
                {"error": "This feature is not enabled", "code": "FEATURE_DISABLED"},
                status=status.HTTP_404_NOT_FOUND,
            )

        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = LoginOTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        phone_country_code = serializer.validated_data["phone_country_code"]
        phone_number = serializer.validated_data["phone_number"]

        from ..models import get_user_model

        UserModel = get_user_model()
        otp_service = OTPService()

        django_user = UserModel.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).first()

        if django_user is None and auth_settings.OTP_LOGIN_AUTO_REGISTER:
            # Passwordless_Account : mot de passe aléatoire inutilisable,
            # jamais choisi par l'utilisateur.
            success, core_user, error = register_user_with_core(
                phone_country_code=phone_country_code,
                phone_number=phone_number,
                password=secrets.token_urlsafe(32),
            )
            if success and core_user:
                django_user = UserModel.objects.filter(id=core_user.id).first()
                if django_user is not None:
                    django_user.has_usable_password = False
                    django_user.is_phone_verified = False
                    django_user.save(update_fields=["has_usable_password", "is_phone_verified"])

        if django_user is not None:
            otp, raw_code = otp_service.generate_login_otp(django_user)
            otp_service.send_phone_otp(django_user, raw_code)
            return Response(_otp_response_payload(otp), status=status.HTTP_200_OK)

        # Anti-enumeration: no account found and auto-register disabled (or
        # failed). Return a response with a strictly identical shape, using
        # non-exploitable substitute values, without creating anything or
        # sending anything.
        validity_minutes = auth_settings.OTP_LOGIN_VALIDITY_MINUTES
        fake_expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        return Response(
            {
                "message": "OTP sent",
                "otp_id": str(uuid.uuid4()),
                "expires_at": fake_expires_at.isoformat(),
                "channel": "sms",
            },
            status=status.HTTP_200_OK,
        )


class LoginOTPVerifyView(APIView):
    """
    POST {API_PREFIX}/auth/login/otp/verify/
    Vérifie un code OTP de connexion et émet des jetons, en répliquant
    les contrôles de sécurité et la forme de réponse de LoginPhoneView.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Vérifier le code OTP de connexion passwordless",
        description="Vérifie le code OTP reçu par SMS et, en cas de succès, émet une paire "
        "de jetons access/refresh, exactement comme /login/phone/. Si le compte a un type "
        "de MFA différent de none, le champ totp_code est également requis.",
        request=LoginOTPVerifySerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string"},
                    "token_type": {"type": "string"},
                    "expires_in": {"type": "integer"},
                    "refresh_expires_in": {"type": "integer"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "requires_2fa": {"type": "boolean"},
                    "session_id": {"type": "string"},
                    "device_id": {"type": "string"},
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "object"}},
            },
            401: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "code": {"type": "string"}},
            },
            404: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
            423: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "code": {"type": "string"},
                    "retry_after": {"type": "integer"},
                },
            },
        },
        examples=[
            OpenApiExample(
                name="login_otp_verify",
                summary="Vérification du code OTP de connexion",
                value={"phone_country_code": "+33", "phone_number": "612345678", "otp_code": "123456"},
            ),
        ],
    )
    def post(self, request):
        # Feature-disabled: reject every request completely, without any
        # internal processing, without verifying any code, and without
        # issuing any token.
        if not auth_settings.OTP_LOGIN_ENABLED:
            return Response(
                {"error": "This feature is not enabled", "code": "FEATURE_DISABLED"},
                status=status.HTTP_404_NOT_FOUND,
            )

        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = LoginOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        phone_country_code = serializer.validated_data["phone_country_code"]
        phone_number = serializer.validated_data["phone_number"]
        otp_code = serializer.validated_data["otp_code"]

        from ..models import get_user_model

        UserModel = get_user_model()
        otp_service = OTPService()

        # Anti-enumeration: an absent account must yield exactly the same
        # response shape/code as an existing account with an incorrect code.
        invalid_code_response = Response(
            {"error": "Invalid or expired code", "code": "OTP_INVALID"}, status=status.HTTP_401_UNAUTHORIZED
        )

        django_user = UserModel.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).first()

        if django_user is None:
            return invalid_code_response

        success, error = otp_service.verify_login_otp(django_user, otp_code)
        if not success:
            code = "OTP_EXPIRED" if "expired" in error.lower() else "OTP_INVALID"
            return Response({"error": error, "code": code}, status=status.HTTP_401_UNAUTHORIZED)

        # Account_Status_Checks (identiques à authenticate_by_phone_with_core)
        user_repo = get_core_user_repo()
        jwt_service = get_core_jwt_service()

        user = user_repo.get_by_id(str(django_user.id))
        if not user:
            return invalid_code_response

        if user_repo.is_account_locked(user.id):
            return Response(
                {
                    "error": "Account locked",
                    "details": "Account has been locked due to too many failed login attempts",
                    "code": "ACCOUNT_LOCKED",
                    "retry_after": get_core_settings().lockout_duration,
                },
                status=status.HTTP_423_LOCKED,
            )

        if django_user.is_banned:
            return Response(
                {"error": "Account has been banned", "code": "ACCOUNT_BANNED"}, status=status.HTTP_401_UNAUTHORIZED
            )

        if not django_user.is_active:
            return Response(
                {"error": "Account is inactive", "code": "ACCOUNT_INACTIVE"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Le login OTP prouve la possession du numéro de téléphone.
        django_user.is_phone_verified = True
        django_user.save(update_fields=["is_phone_verified"])

        application = getattr(request, "application", None)

        # Bloc 2FA identique à celui de LoginPhoneView.
        is_admin = user.is_superuser or user.is_staff
        mfa_type_value = "none"
        if hasattr(user, "mfa_type"):
            mfa_type_value = user.mfa_type.value if hasattr(user.mfa_type, "value") else str(user.mfa_type)
        elif getattr(user, "is_2fa_enabled", False):
            mfa_type_value = "totp"

        if is_admin and mfa_type_value == "none":
            # Super Admin 2FA Bootstrap : identique au bloc de LoginPhoneView
            # (voir authenticate_by_phone_with_core / LoginPhoneView.post).
            app_id_bootstrap = str(application.id) if application else "default"
            bootstrap_token, _jti, _expires_at = jwt_service.generate_access_token(
                user_id=user.id,
                application_id=app_id_bootstrap,
                extra_claims={"scope": "2fa_setup_only"},
                custom_lifetime=timedelta(minutes=15),
            )
            return Response(
                {
                    "access_token": bootstrap_token,
                    "token_type": "Bearer",
                    "token_scope": "2fa_setup_only",
                    "requires_2fa_setup": True,
                    "expires_in": 900,
                },
                status=status.HTTP_200_OK,
            )

        if mfa_type_value != "none":
            from tenxyte.core import TOTPService
            from tenxyte.adapters.django.cache_service import DjangoCacheService
            from tenxyte.adapters.django.totp_storage import DjangoTOTPStorage

            totp_code = serializer.validated_data.get("totp_code", "")
            if not totp_code:
                return Response(
                    {"error": "2FA code required", "code": "2FA_REQUIRED", "requires_2fa": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            totp_service = TOTPService(settings=get_core_settings(), replay_protection=DjangoCacheService())
            is_valid, error_msg = totp_service.verify_2fa(user_id=user.id, code=totp_code, storage=DjangoTOTPStorage())
            if not is_valid:
                return Response({"error": error_msg, "code": "INVALID_2FA_CODE"}, status=status.HTTP_401_UNAUTHORIZED)

        ip_address = get_client_ip(request)
        device_info = serializer.validated_data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        # update_last_login, génération de jetons et persistance du
        # RefreshToken (identique à authenticate_by_phone_with_core).
        from datetime import datetime, timezone as dt_timezone

        user_repo.update_last_login(user.id, datetime.now(dt_timezone.utc))

        app_id = str(application.id) if application else "default"
        tokens = jwt_service.generate_new_token_pair(
            user_id=user.id,
            application_id=app_id,
            extra_claims={"email": user.email, "device_info": device_info, "ip_address": ip_address},
        )

        try:
            from tenxyte.models import RefreshToken

            RefreshToken.objects.create(
                user_id=user.id,
                application_id=application.id if application else None,
                token=tokens.refresh_token,
                expires_at=timezone.now() + timedelta(days=7),
                ip_address=ip_address,
                device_info=device_info,
            )
        except Exception:
            pass

        try:
            user_data = UserSerializer(django_user).data
        except Exception:
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }

        data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "Bearer",
            "expires_in": get_core_settings().jwt_access_token_lifetime,
            "refresh_expires_in": get_core_settings().jwt_refresh_token_lifetime,
            "device_summary": get_device_summary(device_info) if device_info else "Unknown device",
            "user": user_data,
            "requires_2fa": mfa_type_value != "none",
            "session_id": tokens.session_id if hasattr(tokens, "session_id") else None,
            "device_id": tokens.device_id if hasattr(tokens, "device_id") else None,
        }

        response = Response(data, status=status.HTTP_200_OK)
        if auth_settings.REFRESH_TOKEN_COOKIE_ENABLED and "refresh_token" in data:
            from .auth_views import _set_refresh_cookie

            response = _set_refresh_cookie(response, data["refresh_token"])
            del data["refresh_token"]
            response.data = data
        return response
