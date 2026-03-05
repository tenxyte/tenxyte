"""
Vues pour la gestion des suppressions de compte (RGPD).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes

from ..services.account_deletion_service import AccountDeletionService
from ..serializers import PasswordSerializer


@extend_schema(
    tags=["Account"],
    summary="Demander la suppression de compte",
    description="Initie le processus de suppression de compte conforme au RGPD. "
    "Le compte sera marqué pour suppression après une période de grâce "
    "de 30 jours pendant laquelle l'utilisateur peut annuler. "
    "Nécessite le mot de passe actuel et code OTP si 2FA activé. "
    "Toutes les données seront anonymisées après la période de grâce.",
    request=inline_serializer(
        name="RequestAccountDeletion",
        fields={
            "password": serializers.CharField(help_text="Mot de passe actuel requis pour confirmation"),
            "otp_code": serializers.CharField(
                required=False, allow_blank=True, help_text="Code OTP à 6 chiffres (requis si 2FA activé)"
            ),
            "reason": serializers.CharField(
                required=False, allow_blank=True, help_text="Raison optionnelle de la suppression"
            ),
        },
    ),
    responses={
        201: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "deletion_request_id": {"type": "integer"},
                "scheduled_deletion_date": {"type": "string", "format": "date-time"},
                "grace_period_days": {"type": "integer"},
                "cancellation_token": {"type": "string"},
                "data_retention_policy": {
                    "type": "object",
                    "properties": {
                        "anonymization_after": {"type": "string"},
                        "final_deletion_after": {"type": "string"},
                    },
                },
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        423: {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "code": {"type": "string"},
                "existing_request": {"type": "object"},
            },
        },
    },
    examples=[
        OpenApiExample(
            request_only=True,
            name="deletion_request_success",
            summary="Demande de suppression créée",
            value={"password": "CurrentPassword123!", "otp_code": "123456", "reason": "No longer need the account"},
        ),
        OpenApiExample(
            response_only=True,
            name="deletion_already_pending",
            summary="Suppression déjà en cours",
            value={
                "error": "Account deletion already pending",
                "code": "DELETION_ALREADY_PENDING",
                "existing_request": {
                    "scheduled_deletion_date": "2024-02-15T10:30:00Z",
                    "cancellation_token": "cancel_abc123",
                },
            },
        ),
        OpenApiExample(
            response_only=True,
            name="invalid_2fa",
            summary="Code 2FA invalide",
            value={"error": "Invalid or missing OTP code", "code": "INVALID_2FA_CODE"},
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_account_deletion(request: Request) -> Response:
    serializer = PasswordSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({"error": "Invalid password", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    service = AccountDeletionService()
    success, data, error = service.request_deletion(
        user=request.user,
        password=serializer.validated_data["password"],
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        otp_code=request.data.get("otp_code", ""),
        reason=request.data.get("reason", ""),
    )

    if success:
        return Response(data, status=status.HTTP_201_CREATED)

    return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Account"],
    summary="Confirmer la suppression de compte",
    description="Confirme la demande de suppression via token reçu par email. "
    "Le token est valide 24 heures. Cette étape est requise pour "
    "vérifier que l'utilisateur a bien accès à son email. "
    "Après confirmation, le compte entre en période de grâce de 30 jours.",
    request=inline_serializer(
        name="TokenRequest", fields={"token": serializers.CharField(help_text="Token de confirmation reçu par email")}
    ),
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "deletion_confirmed": {"type": "boolean"},
                "grace_period_ends": {"type": "string", "format": "date-time"},
                "cancellation_instructions": {"type": "string"},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        404: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        410: {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "code": {"type": "string"},
                "expired_at": {"type": "string", "format": "date-time"},
            },
        },
    },
    examples=[
        OpenApiExample(
            response_only=True,
            name="confirm_success",
            summary="Suppression confirmée",
            value={"token": "confirm_abc123def456"},
        ),
        OpenApiExample(
            response_only=True,
            name="token_expired",
            summary="Token expiré",
            value={
                "error": "Confirmation token has expired",
                "code": "TOKEN_EXPIRED",
                "expired_at": "2024-01-16T10:30:00Z",
            },
        ),
        OpenApiExample(
            response_only=True,
            name="invalid_token",
            summary="Token invalide",
            value={"error": "Invalid confirmation token", "code": "INVALID_TOKEN"},
        ),
    ],
)
@api_view(["POST"])
def confirm_account_deletion(request: Request) -> Response:
    token = request.data.get("token")

    if not token:
        return Response({"error": "Confirmation token is required"}, status=status.HTTP_400_BAD_REQUEST)

    service = AccountDeletionService()
    success, data, error = service.confirm_deletion(token=token, ip_address=_get_client_ip(request))

    if success:
        return Response(data, status=status.HTTP_200_OK)

    return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Account"],
    summary="Annuler la suppression de compte",
    description="Annule une demande de suppression de compte pendant la période de grâce. "
    "Nécessite le mot de passe actuel pour sécurité. "
    "Le compte sera réactivé immédiatement. "
    "Un email de confirmation sera envoyé. "
    "L'annulation est possible jusqu'à la fin de la période de grâce.",
    request=inline_serializer(
        name="CancelAccountDeletion",
        fields={"password": serializers.CharField(help_text="Mot de passe actuel requis pour annulation")},
    ),
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "deletion_cancelled": {"type": "boolean"},
                "account_reactivated": {"type": "boolean"},
                "cancellation_time": {"type": "string", "format": "date-time"},
                "security_note": {"type": "string"},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
        404: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
    },
    examples=[
        OpenApiExample(
            request_only=True,
            name="cancel_success",
            summary="Suppression annulée",
            value={"password": "CurrentPassword123!"},
        ),
        OpenApiExample(
            response_only=True,
            name="no_pending_deletion",
            summary="Aucune suppression en cours",
            value={"error": "No pending deletion request found", "code": "NO_PENDING_DELETION"},
        ),
        OpenApiExample(
            response_only=True,
            name="invalid_password",
            summary="Mot de passe invalide",
            value={"error": "Invalid password", "code": "INVALID_PASSWORD"},
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_account_deletion(request: Request) -> Response:
    serializer = PasswordSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({"error": "Invalid password", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    service = AccountDeletionService()
    success, data, error = service.cancel_deletion(
        user=request.user, password=serializer.validated_data["password"], ip_address=_get_client_ip(request)
    )

    if success:
        return Response(data, status=status.HTTP_200_OK)

    return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Account"],
    summary="Statut de suppression de compte",
    description="Obtenir le statut des demandes de suppression de compte de l'utilisateur actuel, "
    "y compris les demandes en attente, confirmées ou annulées.",
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_deletion_status(request: Request) -> Response:
    """
    Obtenir le statut des demandes de suppression de compte.

    GET {API_PREFIX}/auth/account-deletion-status/
    """
    service = AccountDeletionService()
    data = service.get_user_requests(request.user)

    return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Account"],
    summary="Exporter mes données",
    description="Exporte toutes les données personnelles de l'utilisateur conformément au droit à la portabilité du RGPD. "
    "Nécessite le mot de passe actuel pour des raisons de sécurité.",
    request=inline_serializer(
        name="ExportUserData",
        fields={"password": serializers.CharField(help_text="Mot de passe actuel requis pour exporter les données")},
    ),
    responses={
        200: {
            "type": "object",
            "description": "Données de l'utilisateur exportées avec succès.",
            "properties": {
                "user_info": {"type": "object"},
                "roles": {"type": "array"},
                "permissions": {"type": "array"},
                "applications": {"type": "array"},
                "audit_logs": {"type": "array"},
                "export_metadata": {"type": "object"},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}, "details": {"type": "object"}}},
        401: {"type": "object", "properties": {"detail": {"type": "string"}}},
        403: {"type": "object", "properties": {"detail": {"type": "string"}}},
        500: {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "user_id": {"type": "integer"},
                "export_requested_at": {"type": "string", "format": "date-time"},
            },
        },
    },
    examples=[
        OpenApiExample(
            request_only=True,
            name="export_success",
            summary="Exportation des données réussie",
            value={"password": "CurrentPassword123!"},
        ),
        OpenApiExample(
            response_only=True,
            name="invalid_password",
            summary="Mot de passe invalide",
            value={"error": "Invalid password"},
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def export_user_data(request: Request) -> Response:
    """
    Exporter les données de l'utilisateur (RGPD).

    POST {API_PREFIX}/auth/export-user-data/
    {
        "password": "current_password"
    }
    """
    serializer = PasswordSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({"error": "Invalid password", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier le mot de passe
    if not request.user.check_password(serializer.validated_data["password"]):
        return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)

    # Exporter les données de l'utilisateur (droit à la portabilité RGPD)
    try:
        user_data = {
            "user_info": {
                "id": request.user.id,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "phone_country_code": request.user.phone_country_code,
                "phone_number": request.user.phone_number,
                "is_email_verified": request.user.is_email_verified,
                "is_phone_verified": request.user.is_phone_verified,
                "is_2fa_enabled": request.user.is_2fa_enabled,
                "is_restricted": getattr(request.user, "is_restricted", False),
                "created_at": request.user.created_at.isoformat(),
                "last_login": request.user.last_login.isoformat() if request.user.last_login else None,
            },
            "roles": [
                {"code": role.code, "name": role.name, "assigned_at": role.created_at.isoformat()}
                for role in request.user.roles.all()
            ],
            "permissions": [
                {"code": perm.code, "name": perm.name, "granted_at": perm.created_at.isoformat()}
                for perm in request.user.get_all_permissions()
            ],
            "sessions": [
                {
                    "id": session.id,
                    "created_at": session.created_at.isoformat(),
                    "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
                    "ip_address": session.ip_address,
                    "device_info": session.device_info,
                    "is_revoked": session.revoked_at is not None,
                }
                for session in request.user.refresh_tokens.all()
            ],
            "social_connections": [
                {
                    "provider": conn.provider,
                    "provider_user_id": conn.provider_user_id,
                    "email": conn.email,
                    "created_at": conn.created_at.isoformat(),
                }
                for conn in (
                    request.user.social_connections.all() if hasattr(request.user, "social_connections") else []
                )
            ],
            "login_attempts": [
                {
                    "ip_address": attempt.ip_address,
                    "success": attempt.success,
                    "created_at": attempt.created_at.isoformat(),
                    "user_agent": attempt.user_agent,
                    "failure_reason": attempt.failure_reason,
                }
                for attempt in (request.user.login_attempts.all() if hasattr(request.user, "login_attempts") else [])
            ],
            "agent_tokens": [
                {
                    "agent_id": token.agent_id,
                    "status": token.status,
                    "created_at": token.created_at.isoformat(),
                    "expires_at": token.expires_at.isoformat(),
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                }
                for token in (request.user.agent_tokens.all() if hasattr(request.user, "agent_tokens") else [])
            ],
            "applications": [
                {"name": app.name, "created_at": app.created_at.isoformat()}
                for app in (request.user.applications.all() if hasattr(request.user, "applications") else [])
            ],
            "audit_logs": [
                {
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat(),
                    "details": log.details,
                }
                for log in request.user.audit_logs.all()  # R10 Audit: Supprimer la limite de 100
            ],
            "export_metadata": {
                "exported_at": timezone.now().isoformat(),
                "export_reason": "user_request",
                "user_id": request.user.id,
                "compliance": ["RGPD", "GDPR", "CCPA"],
            },
        }

        # Log l'export pour audit
        from ..models import AuditLog

        AuditLog.objects.create(
            action="data_exported",
            user=request.user,
            ip_address=_get_client_ip(request),
            details={"export_reason": "user_request", "exported_at": timezone.now().isoformat()},
        )

        return Response(user_data, status=status.HTTP_200_OK)

    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Error exporting user data: {e}", exc_info=True)
        return Response(
            {
                "error": "An unexpected error occurred while exporting user data.",
                "user_id": request.user.id,
                "export_requested_at": timezone.now().isoformat(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _get_client_ip(request: Request) -> str:
    """Obtenir l'IP client pour les logs."""
    from ..conf import auth_settings

    trusted = auth_settings.TRUSTED_PROXIES

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    remote_addr = request.META.get("REMOTE_ADDR", "")

    if x_forwarded_for:
        if not trusted:
            return x_forwarded_for.split(",")[0].strip()

        import ipaddress

        try:
            remote_ip = ipaddress.ip_address(remote_addr)
            for trusted_entry in trusted:
                try:
                    network = ipaddress.ip_network(trusted_entry, strict=False)
                    if remote_ip in network:
                        return x_forwarded_for.split(",")[0].strip()
                except ValueError:
                    continue
        except ValueError:
            pass

        import logging

        logging.getLogger("tenxyte.security").warning(
            "X-Forwarded-For header rejected: REMOTE_ADDR %s is not in TRUSTED_PROXIES.", remote_addr
        )
    return remote_addr or "127.0.0.1"
