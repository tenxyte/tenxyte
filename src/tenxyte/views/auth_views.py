"""
Auth Views - Django DRF Facades for Tenxyte Core.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.
"""

import uuid
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..serializers import (
    RegisterSerializer,
    LoginEmailSerializer,
    LoginPhoneSerializer,
    RefreshTokenSerializer,
    UserSerializer,
)
from ..decorators import require_jwt, get_client_ip
from ..device_info import build_device_info_from_user_agent, get_device_summary
from ..throttles import (
    LoginThrottle,
    LoginHourlyThrottle,
    RegisterThrottle,
    RegisterDailyThrottle,
    RefreshTokenThrottle,
)
from ..conf import auth_settings

# Core imports
from tenxyte.core import JWTService, Settings
from tenxyte.adapters.django.repositories import DjangoUserRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider


# Lazy imports for legacy services still in use
def get_breach_check_service():
    from ..services.breach_check_service import breach_check_service

    return breach_check_service


def get_email_service():
    from tenxyte.adapters.django.email_service import DjangoEmailService

    return DjangoEmailService()


def get_otp_service():
    from ..services import OTPService

    return OTPService()


# Global Core service instances (lazy initialization)
_core_settings = None
_core_jwt_service = None
_core_user_repo = None


def get_core_settings():
    global _core_settings
    if _core_settings is None:
        _core_settings = Settings(DjangoSettingsProvider())
    return _core_settings


def get_core_jwt_service():
    global _core_jwt_service
    if _core_jwt_service is None:
        _core_jwt_service = JWTService(settings=get_core_settings(), blacklist_service=DjangoCacheService())
    return _core_jwt_service


def get_core_user_repo():
    global _core_user_repo
    if _core_user_repo is None:
        _core_user_repo = DjangoUserRepository()
    return _core_user_repo


def get_application_from_request(request):
    """
    Safely get the application from the request.
    Returns None if the application attribute doesn't exist or is None.
    This prevents crashes when ApplicationAuthMiddleware is not in the middleware chain.
    """
    return getattr(request, "application", None)


def validate_application_required(request):
    """Validate that an application is present when required."""
    if auth_settings.APPLICATION_AUTH_ENABLED:
        application = get_application_from_request(request)
        if not application:
            return Response(
                {
                    "error": "Application authentication is required but no valid application was found",
                    "code": "APP_AUTH_REQUIRED",
                    "details": "Please provide valid X-Access-Key and X-Access-Secret headers",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
    return None


def register_user_with_core(**kwargs):
    """
    Register a new user using Core repository.
    Returns (success, user_or_none, error_message_or_none)
    """
    from tenxyte.ports.repositories import User, UserStatus

    user_repo = get_core_user_repo()
    email = kwargs.get("email")

    # Check if email exists (for anti-enumeration)
    existing = user_repo.get_by_email(email)
    if existing:
        return False, None, "Email already registered"

    # Check phone if provided
    phone_country_code = kwargs.get("phone_country_code")
    phone_number = kwargs.get("phone_number")
    if phone_country_code and phone_number:
        # Phone uniqueness check requires Django ORM for now
        from ..models import get_user_model

        UserModel = get_user_model()
        if UserModel.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).exists():
            return False, None, "Phone number already registered"

    # Create Core User dataclass
    user_data = User(
        id="",  # Will be set by repository
        email=email,
        password_hash="",  # Will be set after creation
        first_name=kwargs.get("first_name", ""),
        last_name=kwargs.get("last_name", ""),
        is_active=True,
        is_superuser=False,
        is_staff=False,
        status=UserStatus.ACTIVE,
        email_verified=False,
    )

    # Create via Core repository
    created_user = user_repo.create(user_data)

    # Set password
    password = kwargs.get("password")
    if password:
        user_repo.set_password(created_user.id, password)
        created_user = user_repo.get_by_id(created_user.id)  # Reload with hash

    return True, created_user, None


class RegisterView(APIView):
    """
    POST {API_PREFIX}/auth/register/
    Inscription d'un nouvel utilisateur
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle, RegisterDailyThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Inscription d'un nouvel utilisateur",
        description="Crée un nouveau compte utilisateur. Envoie automatiquement un code OTP de vérification si configuré. Vérifie si le mot de passe a été exposé dans des fuites de données.",
        request=RegisterSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "verification_required": {
                        "type": "object",
                        "properties": {"email": {"type": "boolean"}, "phone": {"type": "boolean"}},
                    },
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "object"}, "code": {"type": "string"}},
            },
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
        },
        examples=[
            OpenApiExample(
                name="register_success",
                summary="Inscription réussie",
                value={
                    "message": "Registration successful",
                    "user": {
                        "id": "uuid-string",
                        "email": "user@example.com",
                        "phone_country_code": "+1",
                        "phone_number": "5551234567",
                        "first_name": "John",
                        "last_name": "Doe",
                        "is_email_verified": False,
                        "is_phone_verified": False,
                        "is_2fa_enabled": False,
                        "roles": [],
                        "permissions": [],
                        "created_at": "2023-10-01T12:00:00Z",
                        "last_login": None,
                    },
                    "verification_required": {"email": True, "phone": False},
                },
            ),
            OpenApiExample(
                response_only=True,
                name="breach_password",
                summary="Mot de passe trouvé dans une fuite",
                value={
                    "error": "Password breach detected",
                    "details": "This password has been found in known data breaches. Please choose a different password.",
                    "code": "PASSWORD_BREACH",
                },
            ),
        ],
    )
    def post(self, request):
        # Validate application is present if required
        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        login_after = serializer.validated_data.pop("login", False)
        device_info = serializer.validated_data.pop("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )
        ip_address = get_client_ip(request)

        # Breach password check (HIBP)
        breach_ok, breach_error = get_breach_check_service().check_password(
            serializer.validated_data.get("password", "")
        )
        if not breach_ok:
            return Response({"error": breach_error, "code": "PASSWORD_BREACHED"}, status=status.HTTP_400_BAD_REQUEST)

        success, user, error = register_user_with_core(**serializer.validated_data)

        if not success:
            if error in ["Email already registered", "Phone number already registered"]:
                # VULN-002 Mitigation: Anti-enumeration. Return a generic success to hide account existence.
                response_data = {
                    "message": "Registration successful",
                    "user": {
                        "id": str(uuid.uuid4()),
                        "email": serializer.validated_data.get("email"),
                        "phone": (
                            f"+{serializer.validated_data.get('phone_country_code')}{serializer.validated_data.get('phone_number')}"
                            if serializer.validated_data.get("phone_number")
                            else ""
                        ),
                        "first_name": serializer.validated_data.get("first_name", ""),
                        "last_name": serializer.validated_data.get("last_name", ""),
                        "is_email_verified": False,
                        "is_phone_verified": False,
                        "is_2fa_enabled": False,
                    },
                    "verification_required": {
                        "email": bool(serializer.validated_data.get("email")),
                        "phone": bool(serializer.validated_data.get("phone_number")),
                    },
                }

                # Send a security alert to the existing owner
                if error == "Email already registered":
                    try:
                        existing_user = get_core_user_repo().get_by_email(serializer.validated_data["email"])
                        if existing_user:
                            get_email_service().send_security_alert_email(
                                to_email=existing_user.email,
                                alert_type="duplicate_registration",
                                details={"ip": ip_address},
                                first_name=existing_user.first_name,
                            )
                    except Exception:
                        pass

                # Ignore login_after, we don't want to generate tokens for an account they don't own
                return Response(response_data, status=status.HTTP_201_CREATED)

            return Response({"error": error, "code": "REGISTRATION_FAILED"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate and send OTPs for verification (using legacy OTPService for now)
        # Convert Core user to Django user for legacy compatibility
        from ..models import get_user_model

        UserModel = get_user_model()
        try:
            django_user = UserModel.objects.get(id=user.id)
            otp_service = get_otp_service()

            if django_user.email:
                otp, raw_code = otp_service.generate_email_verification_otp(django_user)
                otp_service.send_email_otp(django_user, raw_code, otp.otp_type)

            if serializer.validated_data.get("phone_country_code") and serializer.validated_data.get("phone_number"):
                otp, raw_code = otp_service.generate_phone_verification_otp(django_user)
                otp_service.send_phone_otp(django_user, raw_code)
        except Exception:
            pass  # OTP sending failure shouldn't block registration

        response_data = {
            "message": "Registration successful",
            "user": UserSerializer(django_user).data,
            "verification_required": {
                "email": bool(django_user.email and not django_user.is_email_verified),
                "phone": bool(django_user.phone_number and not django_user.is_phone_verified),
            },
        }

        if login_after:
            # Generate tokens using Core JWT service
            jwt_service = get_core_jwt_service()
            tokens = jwt_service.generate_new_token_pair(
                user_id=user.id,
                application_id="default",
                extra_claims={"device_info": device_info, "ip_address": ip_address},
            )
            response_data.update(
                {
                    "access_token": tokens.access_token,
                    "refresh_token": tokens.refresh_token,
                    "token_type": "Bearer",
                    "expires_in": get_core_settings().jwt_access_token_lifetime,
                    "refresh_expires_in": get_core_settings().jwt_refresh_token_lifetime,
                }
            )

        return Response(response_data, status=status.HTTP_201_CREATED)


def authenticate_by_email_with_core(email, password, ip_address=None, device_info="", application=None):
    """
    Authenticate user by email using Core repository.
    Returns (success, data_dict_or_none, error_message_or_none)
    """
    from tenxyte.ports.repositories import MFAType

    user_repo = get_core_user_repo()
    jwt_service = get_core_jwt_service()

    user = user_repo.get_by_email(email)
    if not user:
        # Record failed attempt for non-existent user
        try:
            from tenxyte.models import LoginAttempt

            LoginAttempt.record(
                identifier=email,
                ip_address=ip_address or "127.0.0.1",
                application=application,
                success=False,
                failure_reason="User not found",
            )
        except Exception:
            pass
        return False, None, "Invalid email or password"

    # Check if user is active
    if not user.is_active:
        # Record failed attempt for inactive user
        try:
            from tenxyte.models import LoginAttempt

            LoginAttempt.record(
                identifier=email,
                ip_address=ip_address or "127.0.0.1",
                application=application,
                success=False,
                failure_reason="Account inactive",
            )
        except Exception:
            pass
        return False, None, "Account is inactive"

    # Check if user is banned (stored in metadata)
    if user.metadata and user.metadata.get("is_banned"):
        # Record failed attempt for banned user
        try:
            from tenxyte.models import LoginAttempt

            LoginAttempt.record(
                identifier=email,
                ip_address=ip_address or "127.0.0.1",
                application=application,
                success=False,
                failure_reason="Account banned",
            )
        except Exception:
            pass
        return False, None, "Account has been banned"

    # Check if account is locked
    if user_repo.is_account_locked(user.id):
        # Record failed attempt for locked account
        try:
            from tenxyte.models import LoginAttempt

            LoginAttempt.record(
                identifier=email,
                ip_address=ip_address or "127.0.0.1",
                application=application,
                success=False,
                failure_reason="Account locked",
            )
        except Exception:
            pass
        return False, None, "Account has been locked due to too many failed login attempts"

    # Verify password
    if not user_repo.check_password(user.id, password):
        # Record failed attempt
        try:
            from tenxyte.models import LoginAttempt

            LoginAttempt.record(
                identifier=email,
                ip_address=ip_address or "127.0.0.1",
                application=application,
                success=False,
                failure_reason="Invalid password",
            )
        except Exception:
            pass
        # Record failed attempt via repository for account locking
        user_repo.record_failed_login(user.id)
        return False, None, "Invalid email or password"

    # Update last login
    user_repo.update_last_login(user.id, datetime.now(timezone.utc))

    # Get application ID for token generation
    app_id = str(application.id) if application else "default"

    # Generate tokens
    tokens = jwt_service.generate_new_token_pair(
        user_id=user.id,
        application_id=app_id,
        extra_claims={"email": user.email, "device_info": device_info, "ip_address": ip_address},
    )

    # Store refresh token in database for validation during refresh
    try:
        from tenxyte.models import RefreshToken
        from django.utils import timezone as django_timezone
        from django.db import transaction as db_transaction
        from datetime import timedelta

        # Resolve application_id — FK is NOT NULL so we need a valid application
        app_for_token = application
        if app_for_token is None:
            from tenxyte.models import Application as AppModel
            app_for_token = AppModel.objects.filter(is_active=True).first()

        if app_for_token is not None:
            with db_transaction.atomic():
                RefreshToken.objects.create(
                    user_id=user.id,
                    application_id=app_for_token.id,
                    token=RefreshToken._hash_token(tokens.refresh_token),
                    expires_at=django_timezone.now() + timedelta(days=7),
                    ip_address=ip_address,
                    device_info=device_info,
                )
    except Exception:
        pass  # Don't fail login if refresh token storage fails

    # Build response data - Convert Core User to Django User for serialization
    try:
        from ..models import get_user_model

        UserModel = get_user_model()
        django_user = UserModel.objects.get(id=user.id)
        user_data = UserSerializer(django_user).data
    except Exception:
        # Fallback to basic user info if serialization fails
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
        "_user": user,  # Internal field for 2FA check (not serialized)
        "requires_2fa": user.mfa_type != MFAType.NONE,
        "session_id": tokens.session_id if hasattr(tokens, "session_id") else None,
        "device_id": tokens.device_id if hasattr(tokens, "device_id") else None,
    }

    return True, data, None


def authenticate_by_phone_with_core(
    country_code, phone_number, password, ip_address=None, device_info="", application=None
):
    """
    Authenticate user by phone using Django ORM lookup + Core validation.
    Note: Phone lookup is Django-specific extension.
    """
    from tenxyte.ports.repositories import MFAType

    # Phone lookup requires Django ORM for now
    from ..models import get_user_model

    UserModel = get_user_model()

    try:
        django_user = UserModel.objects.get(
            phone_country_code=country_code, phone_number=phone_number, is_deleted=False
        )
    except UserModel.DoesNotExist:
        return False, None, "Invalid phone number or password"

    # Use Core repository for user operations
    user_repo = get_core_user_repo()
    jwt_service = get_core_jwt_service()

    user = user_repo.get_by_id(str(django_user.id))
    if not user:
        return False, None, "Invalid phone number or password"

    # Check if account is locked
    if user_repo.is_account_locked(user.id):
        return False, None, "Account has been locked due to too many failed login attempts"

    # Verify password
    if not user_repo.check_password(user.id, password):
        user_repo.record_failed_login(user.id)
        return False, None, "Invalid phone number or password"

    # Update last login
    user_repo.update_last_login(user.id, datetime.now(timezone.utc))

    # Get application ID for token generation
    app_id = str(application.id) if application else "default"

    # Generate tokens
    tokens = jwt_service.generate_new_token_pair(
        user_id=user.id,
        application_id=app_id,
        extra_claims={"email": user.email, "device_info": device_info, "ip_address": ip_address},
    )

    # Store refresh token in database for validation during refresh
    try:
        from tenxyte.models import RefreshToken
        from django.utils import timezone as django_timezone
        from datetime import timedelta

        RefreshToken.objects.create(
            user_id=user.id,
            application_id=application.id if application else None,
            token=tokens.refresh_token,
            expires_at=django_timezone.now() + timedelta(days=7),
            ip_address=ip_address,
            device_info=device_info,
        )
    except Exception:
        pass

    # Convert Core User to Django User for serialization
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
        "_user": user,  # Internal field for 2FA check
        "requires_2fa": user.mfa_type != MFAType.NONE,
        "session_id": tokens.session_id if hasattr(tokens, "session_id") else None,
        "device_id": tokens.device_id if hasattr(tokens, "device_id") else None,
    }

    return True, data, None


class LoginEmailView(APIView):
    """
    POST {API_PREFIX}/auth/login/email/
    Connexion par email + password (+ 2FA si activé)
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Connexion par email",
        description="Authentifie un utilisateur avec son email et mot de passe. "
        "Si 2FA est activé, le champ totp_code est requis. "
        "Le device fingerprinting est automatiquement effectué via User-Agent. "
        "Les limites de session et de device sont respectées.",
        request=LoginEmailSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "requires_2fa": {"type": "boolean"},
                    "session_id": {"type": "string"},
                    "device_id": {"type": "string"},
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "details": {"type": "string"},
                    "code": {"type": "string"},
                    "retry_after": {"type": "integer", "nullable": True},
                },
            },
            409: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
            423: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="login_success",
                summary="Connexion réussie",
                value={"email": "user@example.com", "password": "SecureP@ss123!"},
            ),
            OpenApiExample(
                request_only=True,
                name="login_with_2fa",
                summary="Connexion avec 2FA",
                value={"email": "user@example.com", "password": "SecureP@ss123!", "totp_code": "123456"},
            ),
            OpenApiExample(
                response_only=True,
                name="session_limit_exceeded",
                summary="Limite de session dépassée",
                value={
                    "error": "Session limit exceeded",
                    "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
                    "code": "SESSION_LIMIT_EXCEEDED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="account_locked",
                summary="Compte verrouillé",
                value={
                    "error": "Account locked",
                    "details": "Account has been locked due to too many failed login attempts.",
                    "code": "ACCOUNT_LOCKED",
                    "retry_after": 1800,
                },
            ),
        ],
    )
    def post(self, request):
        # Validate application is present if required
        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = LoginEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = serializer.validated_data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        success, data, error = authenticate_by_email_with_core(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip_address=ip_address,
            device_info=device_info,
            application=getattr(request, "application", None),
        )

        if not success:
            # Check if account is locked for 423 status
            if error and "locked due to too many failed login attempts" in error:
                return Response(
                    {
                        "error": "Account locked",
                        "details": error,
                        "code": "ACCOUNT_LOCKED",
                        "retry_after": get_core_settings().lockout_duration,
                    },
                    status=status.HTTP_423_LOCKED,
                )
            return Response({"error": error, "code": "LOGIN_FAILED"}, status=status.HTTP_401_UNAUTHORIZED)

        # Vérifier 2FA si activé ou obligatoire pour ce profil
        user = data.get("_user")
        if user:
            is_admin = user.is_superuser or user.is_staff
            # Get MFA type - handle both Core User (mfa_type) and Django User (is_2fa_enabled)
            mfa_type_value = "none"
            if hasattr(user, "mfa_type"):
                mfa_type_value = user.mfa_type.value if hasattr(user.mfa_type, "value") else str(user.mfa_type)
            elif getattr(user, "is_2fa_enabled", False):
                mfa_type_value = "totp"

            if is_admin and mfa_type_value == "none":
                return Response(
                    {"error": "Administrators must have 2FA enabled to login.", "code": "ADMIN_2FA_SETUP_REQUIRED"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if mfa_type_value != "none":
                from tenxyte.core import TOTPService

                totp_code = serializer.validated_data.get("totp_code", "")
                if not totp_code:
                    return Response(
                        {"error": "2FA code required", "code": "2FA_REQUIRED", "requires_2fa": True},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

                # Use Core TOTP service
                totp_service = TOTPService(settings=get_core_settings(), replay_protection=DjangoCacheService())
                is_valid, error_msg = totp_service.verify_2fa(
                    user_id=user.id, code=totp_code, storage=get_core_user_repo()
                )
                if not is_valid:
                    return Response(
                        {"error": error_msg, "code": "INVALID_2FA_CODE"}, status=status.HTTP_401_UNAUTHORIZED
                    )

        # Retirer l'user de la réponse (on ne veut pas l'exposer)
        if "_user" in data:
            del data["_user"]

        # Convert user to serialized format
        if "user" in data and data["user"]:
            from ..models import get_user_model

            UserModel = get_user_model()
            try:
                django_user = UserModel.objects.get(id=data["user"].id)
                data["user"] = UserSerializer(django_user).data
            except Exception:
                pass

        return Response(data)


class LoginPhoneView(APIView):
    """
    POST {API_PREFIX}/auth/login/phone/
    Connexion par téléphone + password (+ 2FA si activé)
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginHourlyThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Connexion par téléphone",
        description="Authentifie un utilisateur avec son numéro de téléphone et mot de passe. "
        "Le numéro doit être au format international (ex: +33 pour la France). "
        "Si 2FA est activé, le champ totp_code est requis. "
        "Le device fingerprinting est automatiquement effectué.",
        request=LoginPhoneSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {"$ref": "#/components/schemas/User"},
                    "requires_2fa": {"type": "boolean"},
                    "session_id": {"type": "string"},
                    "device_id": {"type": "string"},
                },
            },
            401: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "object"}}},
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="login_phone_success",
                summary="Connexion par téléphone réussie",
                value={"phone_country_code": "+33", "phone_number": "612345678", "password": "SecureP@ss123!"},
            ),
            OpenApiExample(
                request_only=True,
                name="login_phone_with_2fa",
                summary="Connexion par téléphone avec 2FA",
                value={
                    "phone_country_code": "+33",
                    "phone_number": "612345678",
                    "password": "SecureP@ss123!",
                    "totp_code": "123456",
                },
            ),
            OpenApiExample(
                name="invalid_phone_format",
                summary="Format de téléphone invalide",
                value={
                    "error": "Validation error",
                    "details": {
                        "phone_country_code": ["Invalid country code format. Use +XX format."],
                        "phone_number": ["Phone number must be 9-15 digits."],
                    },
                },
            ),
        ],
    )
    def post(self, request):
        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = LoginPhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = serializer.validated_data.get("device_info", "") or build_device_info_from_user_agent(
            request.META.get("HTTP_USER_AGENT", "")
        )

        success, data, error = authenticate_by_phone_with_core(
            country_code=serializer.validated_data["phone_country_code"],
            phone_number=serializer.validated_data["phone_number"],
            password=serializer.validated_data["password"],
            ip_address=ip_address,
            device_info=device_info,
            application=getattr(request, "application", None),
        )

        if not success:
            # Check if account is locked for 423 status
            if error and "locked due to too many failed login attempts" in error:
                return Response(
                    {
                        "error": "Account locked",
                        "details": error,
                        "code": "ACCOUNT_LOCKED",
                        "retry_after": get_core_settings().lockout_duration,
                    },
                    status=status.HTTP_423_LOCKED,
                )
            return Response({"error": error, "code": "LOGIN_FAILED"}, status=status.HTTP_401_UNAUTHORIZED)

        # Vérifier 2FA si activé
        user = data.get("_user")
        if user:
            is_admin = user.is_superuser or user.is_staff
            # Get MFA type - handle both Core User (mfa_type) and Django User (is_2fa_enabled)
            mfa_type_value = "none"
            if hasattr(user, "mfa_type"):
                mfa_type_value = user.mfa_type.value if hasattr(user.mfa_type, "value") else str(user.mfa_type)
            elif getattr(user, "is_2fa_enabled", False):
                mfa_type_value = "totp"

            if is_admin and mfa_type_value == "none":
                return Response(
                    {"error": "Administrators must have 2FA enabled to login.", "code": "ADMIN_2FA_SETUP_REQUIRED"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if mfa_type_value != "none":
                from tenxyte.core import TOTPService

                totp_code = serializer.validated_data.get("totp_code", "")
                if not totp_code:
                    return Response(
                        {"error": "2FA code required", "code": "2FA_REQUIRED", "requires_2fa": True},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

                totp_service = TOTPService(settings=get_core_settings(), replay_protection=DjangoCacheService())
                is_valid, error_msg = totp_service.verify_2fa(
                    user_id=user.id, code=totp_code, storage=get_core_user_repo()
                )
                if not is_valid:
                    return Response(
                        {"error": error_msg, "code": "INVALID_2FA_CODE"}, status=status.HTTP_401_UNAUTHORIZED
                    )

        if "_user" in data:
            del data["_user"]

        # Convert user to serialized format
        if "user" in data and data["user"]:
            from ..models import get_user_model

            UserModel = get_user_model()
            try:
                django_user = UserModel.objects.get(id=data["user"].id)
                data["user"] = UserSerializer(django_user).data
            except Exception:
                pass

        return Response(data)


class RefreshTokenView(APIView):
    """
    POST {API_PREFIX}/auth/refresh/
    Rafraîchir le access token
    """

    permission_classes = [AllowAny]
    throttle_classes = [RefreshTokenThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Rafraîchir le token d'accès",
        description="Génère un nouveau access token à partir d'un refresh token valide. "
        "Le refresh token est automatiquement roté pour améliorer la sécurité. "
        "Les refresh tokens expirés ou blacklistés sont rejetés.",
        request=RefreshTokenSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string", "description": "Nouveau refresh token (rotation)"},
                    "token_type": {"type": "string"},
                    "expires_in": {"type": "integer"},
                    "user": {"$ref": "#/components/schemas/User"},
                },
            },
            401: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "details": {"type": "string"}, "code": {"type": "string"}},
            },
            429: {"type": "object", "properties": {"error": {"type": "string"}, "retry_after": {"type": "integer"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="refresh_success",
                summary="Rafraîchissement réussi",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
            ),
            OpenApiExample(
                response_only=True,
                name="refresh_expired",
                summary="Refresh token expiré",
                value={
                    "error": "Refresh token expired",
                    "details": "Please login again to get a new refresh token",
                    "code": "REFRESH_EXPIRED",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="refresh_blacklisted",
                summary="Refresh token blacklisté",
                value={
                    "error": "Refresh token has been revoked",
                    "details": "This refresh token has been blacklisted due to logout",
                    "code": "REFRESH_BLACKLISTED",
                },
            ),
        ],
    )
    def post(self, request):
        app_error = validate_application_required(request)
        if app_error:
            return app_error

        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        jwt_service = get_core_jwt_service()
        refresh_token_str = serializer.validated_data["refresh_token"]

        # Use core service refresh_tokens which handles all the logic
        result = jwt_service.refresh_tokens(refresh_token_str)
        
        if not result:
            return Response(
                {"error": "Invalid or expired refresh token", "code": "REFRESH_FAILED"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Build response data
        data = {
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": "Bearer",
            "expires_in": get_core_settings().jwt_access_token_lifetime,
            "refresh_expires_in": get_core_settings().jwt_refresh_token_lifetime,
        }

        # Add user data if available
        try:
            decoded = jwt_service.decode_token(result.access_token, check_blacklist=False)
            if decoded and decoded.user_id:
                from ..models import get_user_model
                UserModel = get_user_model()
                user = UserModel.objects.get(id=decoded.user_id)
                data["user"] = UserSerializer(user).data
        except Exception:
            pass

        return Response(data)


class LogoutView(APIView):
    """
    POST {API_PREFIX}/auth/logout/
    Déconnexion (révoque le refresh token)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Déconnexion",
        description="Révoque le refresh token fourni pour déconnecter l'utilisateur. "
        "Si un access token est fourni dans l'en-tête Authorization, "
        "il est également blacklisté pour une déconnexion immédiate.",
        parameters=[
            OpenApiParameter(
                name="Authorization",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                description="Bearer token pour blacklistage immédiat (optionnel)",
                required=False,
                pattern="Bearer [a-zA-Z0-9._-]+",
            )
        ],
        request=RefreshTokenSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "access_token_blacklisted": {"type": "boolean"},
                    "refresh_token_revoked": {"type": "boolean"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "object"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="logout_success",
                summary="Déconnexion réussie",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
            ),
            OpenApiExample(
                name="logout_with_access_token",
                summary="Déconnexion avec blacklistage access token",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
            ),
        ],
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Extract access token from Authorization header for blacklisting
        access_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header[7:]

        jwt_service = get_core_jwt_service()

        # Revoke refresh token (DB-backed or JWT)
        try:
            # First try as a DB opaque token
            from tenxyte.models import RefreshToken

            token_obj = RefreshToken.get_by_raw_token(serializer.validated_data["refresh_token"])
            if hasattr(token_obj, "revoke"):
                token_obj.revoke()
            else:
                token_obj.is_revoked = True
                token_obj.save(update_fields=["is_revoked"])
        except Exception:
            # If not in DB, try to blacklist as a JWT refresh token
            try:
                decoded = jwt_service.decode_token(serializer.validated_data["refresh_token"])
                if decoded:
                    jwt_service.blacklist_token(
                        jti=decoded.jti, expires_at=decoded.exp, user_id=decoded.user_id, reason="logout"
                    )
            except Exception:
                pass

        # Blacklist access token if provided
        if access_token:
            try:
                decoded = jwt_service.decode_token(access_token)
                if decoded:
                    jwt_service.blacklist_token(
                        jti=decoded.jti, expires_at=decoded.exp, user_id=decoded.user_id, reason="logout"
                    )
            except Exception as e:
                print(f"Exception blacklisting access token: {repr(e)}")
                pass

        return Response({"message": "Logged out successfully"})


class LogoutAllView(APIView):
    """
    POST {API_PREFIX}/auth/logout/all/
    Déconnexion de tous les appareils
    """

    @extend_schema(
        tags=["Auth"],
        summary="Déconnexion de tous les appareils",
        description="Révoque tous les refresh tokens de l'utilisateur connecté. "
        "L'access token actuel est également blacklisté. "
        "Utile pour une déconnexion de sécurité sur tous les appareils.",
        request=None,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "devices_logged_out": {"type": "integer"},
                    "access_token_blacklisted": {"type": "boolean"},
                },
            },
            401: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="logout_all_success",
                summary="Déconnexion de tous les appareils réussie",
                value={
                    "message": "Logged out from 3 devices",
                    "devices_logged_out": 3,
                    "access_token_blacklisted": True,
                },
            )
        ],
    )
    @require_jwt
    def post(self, request):
        # Extract access token from Authorization header for blacklisting
        access_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header[7:]

        jwt_service = get_core_jwt_service()

        # Blacklist current access token
        if access_token:
            try:
                decoded = jwt_service.decode_token(access_token)
                if decoded:
                    jwt_service.blacklist_token(
                        jti=decoded.jti, expires_at=decoded.exp, user_id=decoded.user_id, reason="logout_all"
                    )
            except Exception:
                pass

        # Revoke all active sessions in database
        count = 1
        try:
            from tenxyte.models import RefreshToken

            # getattr avoids issues if User model structure differs between apps
            user_id = getattr(request.user, "id", None)
            if user_id:
                count = RefreshToken.objects.filter(user_id=user_id, is_revoked=False).update(is_revoked=True)
            else:
                # If no user.id available, we only invalidated current session via blacklist
                pass
        except Exception:
            pass

        return Response({"message": f"Logged out from {count} devices"})
