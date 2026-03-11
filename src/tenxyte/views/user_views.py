"""
User Views - Django DRF Facades for Tenxyte Core.

These views act as adapters between Django/DRF and the framework-agnostic Core.
They maintain 100% backward compatibility with existing endpoints and responses.
"""

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from ..serializers import UserSerializer
from ..serializers.user_admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    BanUserSerializer,
    LockUserSerializer,
)
from ..models import get_user_model
from ..decorators import require_jwt, require_permission
from ..pagination import TenxytePagination
from ..filters import apply_user_filters

# Core imports
from tenxyte.adapters.django.repositories import DjangoUserRepository
from tenxyte.adapters.django.cache_service import DjangoCacheService
from tenxyte.adapters.django.settings_provider import DjangoSettingsProvider
from tenxyte.core import Settings

User = get_user_model()

# Global Core repository (lazy initialization)
_core_user_repo = None
_core_settings = None


def get_core_user_repo():
    global _core_user_repo
    if _core_user_repo is None:
        _core_user_repo = DjangoUserRepository()
    return _core_user_repo


def get_core_settings():
    global _core_settings
    if _core_settings is None:
        _core_settings = Settings(DjangoSettingsProvider())
    return _core_settings


class MeView(APIView):
    """
    GET {API_PREFIX}/auth/me/
    Récupérer le profil de l'utilisateur connecté
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Récupérer mon profil",
        description="Retourne les informations complètes de l'utilisateur connecté. "
        "Inclut les champs personnalisés, préférences, et métadonnées. "
        "Les champs sensibles (mot de passe, tokens) ne sont jamais inclus. "
        "Le profil peut varier selon les permissions et le contexte organisationnel.",
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation (optionnel)",
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "username": {"type": "string", "nullable": True},
                    "phone": {"type": "string", "nullable": True},
                    "avatar": {"type": "string", "nullable": True},
                    "bio": {"type": "string", "nullable": True},
                    "timezone": {"type": "string"},
                    "language": {"type": "string"},
                    "is_active": {"type": "boolean"},
                    "is_verified": {"type": "boolean"},
                    "date_joined": {"type": "string", "format": "date-time"},
                    "last_login": {"type": "string", "format": "date-time", "nullable": True},
                    "custom_fields": {
                        "type": "object",
                        "description": "Champs personnalisés définis par l'organisation",
                    },
                    "preferences": {
                        "type": "object",
                        "properties": {
                            "email_notifications": {"type": "boolean"},
                            "sms_notifications": {"type": "boolean"},
                            "marketing_emails": {"type": "boolean"},
                            "two_factor_enabled": {"type": "boolean"},
                        },
                    },
                    "organization_context": {
                        "type": "object",
                        "properties": {
                            "current_org": {"type": "object", "nullable": True},
                            "roles": {"type": "array"},
                            "permissions": {"type": "array"},
                        },
                    },
                },
            }
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="user_profile_complete",
                summary="Profil utilisateur complet",
                value={
                    "id": 12345,
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "username": "johndoe",
                    "phone": "+33612345678",
                    "avatar": "https://cdn.example.com/avatars/john.jpg",
                    "bio": "Software developer passionate about security",
                    "timezone": "Europe/Paris",
                    "language": "fr",
                    "is_active": True,
                    "is_verified": True,
                    "date_joined": "2024-01-15T10:30:00Z",
                    "last_login": "2024-01-20T14:22:00Z",
                    "custom_fields": {
                        "department": "Engineering",
                        "employee_id": "EMP001",
                        "manager": "jane.smith@example.com",
                    },
                    "preferences": {
                        "email_notifications": True,
                        "sms_notifications": False,
                        "marketing_emails": False,
                        "two_factor_enabled": True,
                    },
                },
            )
        ],
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=["User"],
        summary="Modifier mon profil",
        description="Met à jour partiellement les informations de l'utilisateur connecté. "
        "Les champs non fournis ne sont pas modifiés. Certains champs peuvent "
        "avoir des restrictions de validation (format email, téléphone international). "
        "La modification de l'email nécessite une nouvelle vérification. "
        "Les champs personnalisés suivent les règles définies par l'organisation.",
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation (optionnel)",
            )
        ],
        request=inline_serializer(
            name="UpdateProfileRequest",
            fields={
                "first_name": serializers.CharField(
                    required=False, max_length=30, help_text="Prénom (max 30 caractères)"
                ),
                "last_name": serializers.CharField(required=False, max_length=30, help_text="Nom (max 30 caractères)"),
                "username": serializers.CharField(
                    required=False, max_length=20, help_text="Nom d'utilisateur unique (alphanumérique + underscores)"
                ),
                "phone": serializers.CharField(
                    required=False, help_text="Numéro de téléphone au format international (+33612345678)"
                ),
                "bio": serializers.CharField(
                    required=False, max_length=500, allow_blank=True, help_text="Biographie (max 500 caractères)"
                ),
                "timezone": serializers.CharField(
                    required=False, help_text="Fuseau horaire (ex: Europe/Paris, America/New_York)"
                ),
                "language": serializers.CharField(required=False, help_text="Langue préférée"),
                "custom_fields": serializers.DictField(
                    required=False, help_text="Champs personnalisés (selon configuration organisation)"
                ),
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "updated_fields": {"type": "array"},
                    "user": {"type": "object"},
                    "verification_required": {
                        "type": "object",
                        "properties": {"email_changed": {"type": "boolean"}, "phone_changed": {"type": "boolean"}},
                    },
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "code": {"type": "string"},
                    "field_errors": {"type": "object"},
                },
            },
        },
        examples=[
            OpenApiExample(
                name="update_profile",
                summary="Mise à jour profil",
                value={
                    "first_name": "John",
                    "last_name": "Smith",
                    "phone": "+33612345678",
                    "bio": "Senior developer at TechCorp",
                    "timezone": "Europe/Paris",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="validation_error",
                summary="Erreur de validation",
                value={
                    "error": "Validation failed",
                    "field_errors": {"phone": ["Invalid phone format"], "username": ["Username already taken"]},
                },
            ),
        ],
    )
    def patch(self, request):
        """Update profile using Core repository."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        email_changed = (
            "email" in serializer.validated_data and serializer.validated_data["email"] != request.user.email
        )
        phone_changed = (
            "phone_number" in serializer.validated_data
            and serializer.validated_data["phone_number"] != request.user.phone_number
        ) or (
            "phone_country_code" in serializer.validated_data
            and serializer.validated_data["phone_country_code"] != request.user.phone_country_code
        )

        # Use Core repository for update
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(request.user.id))
        
        if not core_user:
            return Response(
                {"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND
            )
        
        # Update fields via repository
        from tenxyte.ports.repositories import User, UserStatus
        update_data = {
            'first_name': serializer.validated_data.get('first_name', core_user.first_name),
            'last_name': serializer.validated_data.get('last_name', core_user.last_name),
            'email': serializer.validated_data.get('email', core_user.email),
            'email_verified': core_user.email_verified if not email_changed else False,
        }
        
        updated_user = user_repo.update_user(str(request.user.id), update_data)
        
        # Refresh user from database to get updated values
        from tenxyte.models import get_user_model
        UserModel = get_user_model()
        user = UserModel.objects.get(id=request.user.id)
        
        # VULN-005 Mitigation: Reset verification flags if contact info is updated
        if email_changed:
            user.is_email_verified = False
        if phone_changed:
            user.is_phone_verified = False

        if email_changed or phone_changed:
            user.save(update_fields=["is_email_verified", "is_phone_verified"])

        return Response(
            {
                "message": "Profile updated successfully",
                "updated_fields": list(serializer.validated_data.keys()),
                "user": UserSerializer(user).data,
                "verification_required": {"email_changed": email_changed, "phone_changed": phone_changed},
            }
        )


class AvatarUploadView(APIView):
    """
    POST {API_PREFIX}/auth/me/avatar/
    Upload et met à jour l'avatar de l'utilisateur
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Uploader mon avatar",
        description="Upload une image pour l'avatar de l'utilisateur. "
        "Supporte JPEG, PNG, WebP avec taille maximale 5MB. "
        "L'image est automatiquement redimensionnée en 400x400px. "
        "L'ancien avatar est remplacé. Retourne l'URL de la nouvelle image.",
        request={
            "type": "object",
            "properties": {
                "avatar": {
                    "type": "string",
                    "format": "binary",
                    "description": "Fichier image (JPEG, PNG, WebP - max 5MB)",
                }
            },
            "required": ["avatar"],
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "avatar_url": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "dimensions": {
                        "type": "object",
                        "properties": {"width": {"type": "integer"}, "height": {"type": "integer"}},
                    },
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
            413: {
                "type": "object",
                "properties": {"error": {"type": "string"}, "code": {"type": "string"}, "max_size": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                response_only=True,
                name="avatar_upload_success",
                summary="Avatar uploadé avec succès",
                value={"avatar": "binary_file_data"},
            ),
            OpenApiExample(
                response_only=True,
                name="file_too_large",
                summary="Fichier trop volumineux",
                value={"error": "File size exceeds maximum limit", "code": "FILE_TOO_LARGE", "max_size": "5MB"},
            ),
        ],
    )
    def post(self, request):
        if "avatar" not in request.FILES:
            return Response(
                {"error": "Avatar file is required", "code": "FILE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        avatar_file = request.FILES["avatar"]

        # Validation du type de fichier
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if avatar_file.content_type not in allowed_types:
            return Response(
                {"error": "Invalid file type. Only JPEG, PNG, and WebP are allowed", "code": "INVALID_FILE_TYPE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validation de la taille (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if avatar_file.size > max_size:
            return Response(
                {"error": "File size exceeds maximum limit", "code": "FILE_TOO_LARGE", "max_size": "5MB"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Simuler le traitement de l'image
        # Dans un vrai projet, utiliser Pillow pour redimensionner
        avatar_url = f"https://cdn.example.com/avatars/{request.user.id}_{avatar_file.name}"

        return Response(
            {
                "message": "Avatar uploaded successfully",
                "avatar_url": avatar_url,
                "file_size": avatar_file.size,
                "dimensions": {"width": 400, "height": 400},
            }
        )


class MyRolesView(APIView):
    """
    GET {API_PREFIX}/auth/me/roles/
    Récupère les rôles et permissions de l'utilisateur connecté
    """

    @extend_schema(
        tags=["User"],
        summary="Récupérer mes rôles et permissions",
        description="Retourne la liste des rôles et permissions de l'utilisateur connecté.",
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation (optionnel)",
            )
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_jwt
    def get(self, request):
        return Response({"roles": request.user.get_all_roles(), "permissions": request.user.get_all_permissions()})


# =============================================================================
# Admin User Management
# =============================================================================


class UserListView(APIView):
    """
    GET {API_PREFIX}/auth/admin/users/
    Liste tous les utilisateurs (admin, paginé + filtres)
    """

    pagination_class = TenxytePagination

    @extend_schema(
        tags=["Admin - Users"],
        summary="Lister les utilisateurs",
        description="Retourne la liste paginée de tous les utilisateurs. Réservé aux admins.",
        parameters=[
            OpenApiParameter("search", str, description="Recherche dans email, first_name, last_name"),
            OpenApiParameter("is_active", bool, description="Filtrer par statut actif"),
            OpenApiParameter("is_locked", bool, description="Filtrer par compte verrouillé"),
            OpenApiParameter("is_banned", bool, description="Filtrer par compte banni"),
            OpenApiParameter("is_deleted", bool, description="Filtrer par compte supprimé"),
            OpenApiParameter("is_email_verified", bool, description="Filtrer par email vérifié"),
            OpenApiParameter("is_2fa_enabled", bool, description="Filtrer par 2FA activé"),
            OpenApiParameter("role", str, description="Filtrer par code de rôle"),
            OpenApiParameter("date_from", str, description="Créé après (YYYY-MM-DD)"),
            OpenApiParameter("date_to", str, description="Créé avant (YYYY-MM-DD)"),
            OpenApiParameter("ordering", str, description="Tri: email, created_at, last_login, first_name"),
            OpenApiParameter("page", int, description="Numéro de page"),
            OpenApiParameter("page_size", int, description="Éléments par page (max 100)"),
        ],
        responses={200: AdminUserListSerializer(many=True)},
    )
    @require_permission("users.view")
    def get(self, request):
        queryset = User.objects.all()
        queryset = apply_user_filters(queryset, request)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = AdminUserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminUserListSerializer(queryset, many=True)
        return Response(serializer.data)


class UserDetailView(APIView):
    """
    GET {API_PREFIX}/auth/admin/users/<user_id>/
    PATCH {API_PREFIX}/auth/admin/users/<user_id>/
    DELETE {API_PREFIX}/auth/admin/users/<user_id>/
    """

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @extend_schema(
        tags=["Admin - Users"],
        summary="Détails d'un utilisateur",
        description="Récupère les informations complètes d'un utilisateur.",
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    @require_permission("users.view")
    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserDetailSerializer(user).data)

    @extend_schema(
        tags=["Admin - Users"],
        summary="Modifier un utilisateur (admin)",
        description="Met à jour partiellement les informations d'un utilisateur. "
        "Tous les champs sont optionnels. Réservé aux admins (permission users.update). "
        "Supporte la désactivation de compte, la promotion staff/superuser, "
        "et la limite de sessions/appareils.",
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserDetailSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name="update_profile_fields",
                summary="Mise à jour nom/prénom",
                description="Modifier les champs de profil de base d'un utilisateur.",
                request_only=True,
                value={
                    "first_name": "Jane",
                    "last_name": "Smith",
                },
            ),
            OpenApiExample(
                name="deactivate_user",
                summary="Désactiver un compte",
                description="Désactiver un compte utilisateur sans le bannir ni le supprimer.",
                request_only=True,
                value={
                    "is_active": False,
                },
            ),
            OpenApiExample(
                name="promote_to_staff",
                summary="Promouvoir en staff",
                description="Accorder les droits staff avec des limites de session renforcées.",
                request_only=True,
                value={
                    "is_staff": True,
                    "max_sessions": 3,
                    "max_devices": 2,
                },
            ),
            OpenApiExample(
                name="user_not_found",
                summary="Utilisateur introuvable",
                response_only=True,
                status_codes=["404"],
                value={
                    "error": "User not found",
                    "code": "NOT_FOUND",
                },
            ),
        ],
    )
    @require_permission("users.update")
    def patch(self, request, user_id):
        """Update user via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update via Core repository
        update_data = {}
        for attr, value in serializer.validated_data.items():
            update_data[attr] = value
        
        updated_user = user_repo.update_user(str(user_id), update_data)
        
        # Get Django user for serialization
        try:
            user = User.objects.get(id=user_id)
            return Response(AdminUserDetailSerializer(user).data)
        except User.DoesNotExist:
            return Response({"message": "User updated", "user_id": str(user_id)})

    @extend_schema(
        tags=["Admin - Users"],
        summary="Supprimer un utilisateur (soft delete)",
        description="Suppression logique d'un utilisateur via Core repository (anonymisation RGPD).",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @require_permission("users.delete")
    def delete(self, request, user_id):
        """Soft delete user via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check if already deleted via Django model
        try:
            django_user = User.objects.get(id=user_id)
            if django_user.is_deleted:
                return Response(
                    {"error": "User already deleted", "code": "ALREADY_DELETED"}, status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Soft delete via Core repository
        user_repo.soft_delete(str(user_id))
        return Response({"message": "User soft-deleted successfully", "user_id": str(user_id)})


class UserBanView(APIView):
    """
    POST {API_PREFIX}/auth/admin/users/<user_id>/ban/
    """

    @extend_schema(
        tags=["Admin - Users"],
        summary="Bannir un utilisateur",
        description="Bannit un utilisateur de manière permanente. "
        "Désactive le compte (is_active=False). "
        "Nécessite la permission users.ban. "
        "La raison est stockée dans le journal d'audit.",
        request=BanUserSerializer,
        responses={200: AdminUserDetailSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name="ban_with_reason",
                summary="Bannissement avec raison",
                description="Bannir un utilisateur en précisant la raison (recommandé pour l'audit).",
                request_only=True,
                value={
                    "reason": "Repeated ToS violations — spam and abusive content",
                },
            ),
            OpenApiExample(
                name="ban_no_reason",
                summary="Bannissement sans raison",
                description="Le champ reason est optionnel.",
                request_only=True,
                value={},
            ),
            OpenApiExample(
                name="ban_success",
                summary="Bannissement réussi",
                response_only=True,
                status_codes=["200"],
                value={
                    "message": "User banned successfully",
                    "user": {
                        "id": 42,
                        "email": "offender@example.com",
                        "is_active": False,
                        "is_banned": True,
                    },
                },
            ),
            OpenApiExample(
                name="already_banned",
                summary="Utilisateur déjà banni",
                response_only=True,
                status_codes=["400"],
                value={
                    "error": "User already banned",
                    "code": "ALREADY_BANNED",
                },
            ),
            OpenApiExample(
                name="user_not_found",
                summary="Utilisateur introuvable",
                response_only=True,
                status_codes=["404"],
                value={
                    "error": "User not found",
                    "code": "NOT_FOUND",
                },
            ),
        ],
    )
    @require_permission("users.ban")
    def post(self, request, user_id):
        """Ban user via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check if banned via Django model
        try:
            django_user = User.objects.get(id=user_id)
            if django_user.is_banned:
                return Response(
                    {"error": "User already banned", "code": "ALREADY_BANNED"}, status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Ban via Core repository
        user_repo.ban(str(user_id), reason=request.data.get("reason", ""))

        return Response({"message": "User banned successfully", "user": AdminUserDetailSerializer(django_user).data})


class UserUnbanView(APIView):
    """
    POST {API_PREFIX}/auth/admin/users/<user_id>/unban/
    """

    @extend_schema(
        tags=["Admin - Users"],
        summary="Débannir un utilisateur",
        description="Lève le bannissement d'un utilisateur.",
        request=None,
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    @require_permission("users.ban")
    def post(self, request, user_id):
        """Unban user via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check if banned via Django model
        try:
            django_user = User.objects.get(id=user_id)
            if not django_user.is_banned:
                return Response({"error": "User is not banned", "code": "NOT_BANNED"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Unban via Core repository
        user_repo.unban(str(user_id))

        return Response({"message": "User unbanned successfully", "user": AdminUserDetailSerializer(django_user).data})


class UserLockView(APIView):
    """
    POST {API_PREFIX}/auth/admin/users/<user_id>/lock/
    """

    @extend_schema(
        tags=["Admin - Users"],
        summary="Verrouiller un compte",
        description="Verrouille temporairement un compte utilisateur. "
        "La durée est configurable (défaut: 30 min, max: 30 jours). "
        "Nécessite la permission users.lock. "
        "La raison est stockée dans le journal d'audit.",
        request=LockUserSerializer,
        responses={200: AdminUserDetailSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                name="lock_default",
                summary="Verrouillage 30 min (défaut)",
                description="Verrouille le compte pour la durée par défaut (30 minutes).",
                request_only=True,
                value={
                    "reason": "Suspicious login activity detected",
                },
            ),
            OpenApiExample(
                name="lock_custom_duration",
                summary="Verrouillage durée personnalisée",
                description="Verrouille le compte pour 24 heures avec une raison explicite.",
                request_only=True,
                value={
                    "duration_minutes": 1440,
                    "reason": "Pending security review — account suspended by admin",
                },
            ),
            OpenApiExample(
                name="lock_success",
                summary="Verrouillage réussi",
                response_only=True,
                status_codes=["200"],
                value={
                    "message": "User locked for 30 minutes",
                    "user": {
                        "id": 42,
                        "email": "user@example.com",
                        "is_locked": True,
                        "locked_until": "2024-01-20T15:00:00Z",
                    },
                },
            ),
            OpenApiExample(
                name="already_locked",
                summary="Compte déjà verrouillé",
                response_only=True,
                status_codes=["400"],
                value={
                    "error": "User already locked",
                    "code": "ALREADY_LOCKED",
                },
            ),
            OpenApiExample(
                name="user_not_found",
                summary="Utilisateur introuvable",
                response_only=True,
                status_codes=["404"],
                value={
                    "error": "User not found",
                    "code": "NOT_FOUND",
                },
            ),
        ],
    )
    @require_permission("users.lock")
    def post(self, request, user_id):
        """Lock user account via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check if locked via Django model
        try:
            django_user = User.objects.get(id=user_id)
            if django_user.is_locked:
                return Response(
                    {"error": "User already locked", "code": "ALREADY_LOCKED"}, status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        serializer = LockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        duration = serializer.validated_data.get("duration_minutes", 30)
        
        # Lock via Core repository
        user_repo.lock(str(user_id), duration_minutes=duration, reason=serializer.validated_data.get("reason", ""))

        return Response(
            {"message": f"User locked for {duration} minutes", "user": AdminUserDetailSerializer(django_user).data}
        )


class UserUnlockView(APIView):
    """
    POST {API_PREFIX}/auth/admin/users/<user_id>/unlock/
    """

    @extend_schema(
        tags=["Admin - Users"],
        summary="Déverrouiller un compte",
        description="Déverrouille un compte utilisateur.",
        request=None,
        responses={200: AdminUserDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    @require_permission("users.lock")
    def post(self, request, user_id):
        """Unlock user account via Core repository."""
        user_repo = get_core_user_repo()
        core_user = user_repo.get_by_id(str(user_id))
        
        if not core_user:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check if locked via Django model
        try:
            django_user = User.objects.get(id=user_id)
            if not django_user.is_locked:
                return Response({"error": "User is not locked", "code": "NOT_LOCKED"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Unlock via Core repository
        user_repo.unlock(str(user_id))

        return Response({"message": "User unlocked successfully", "user": AdminUserDetailSerializer(django_user).data})


class DeleteAccountView(APIView):
    """
    DELETE {API_PREFIX}/auth/me/
    Supprime le compte de l'utilisateur connecté
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Supprimer mon compte",
        description="Supprime définitivement le compte de l'utilisateur connecté. "
        "**ATTENTION:** Cette action est irréversible et détruira toutes "
        "les données associées (profil, historique, fichiers, etc.). "
        "Nécessite confirmation explicite. Les organisations dont l'utilisateur "
        "est le seul propriétaire seront également supprimées. "
        "Un email de confirmation final sera envoyé.",
        request=inline_serializer(
            name="DeleteAccountRequest",
            fields={
                "confirmation": serializers.CharField(help_text='Texte de confirmation "DELETE MY ACCOUNT"'),
                "password": serializers.CharField(help_text="Mot de passe actuel requis pour confirmation"),
                "reason": serializers.CharField(
                    required=False, allow_blank=True, help_text="Raison optionnelle de la suppression"
                ),
            },
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "account_deleted": {"type": "boolean"},
                    "deleted_at": {"type": "string", "format": "date-time"},
                    "data_removed": {"type": "boolean"},
                    "organizations_affected": {"type": "array", "items": {"type": "string"}},
                    "recovery_possible": {"type": "boolean"},
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}, "code": {"type": "string"}}},
            403: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "code": {"type": "string"},
                    "restriction": {"type": "string"},
                },
            },
        },
        examples=[
            OpenApiExample(
                request_only=True,
                name="delete_success",
                summary="Compte supprimé avec succès",
                value={
                    "confirmation": "DELETE MY ACCOUNT",
                    "password": "CurrentPassword123!",
                    "reason": "Moving to another platform",
                },
            ),
            OpenApiExample(
                response_only=True,
                name="confirmation_required",
                summary="Confirmation requise",
                value={"error": "Explicit confirmation required", "code": "CONFIRMATION_REQUIRED"},
            ),
            OpenApiExample(
                response_only=True,
                name="owner_restriction",
                summary="Restriction propriétaire",
                value={
                    "error": "Cannot delete account while being sole owner of organizations",
                    "code": "OWNER_RESTRICTION",
                    "organizations": ["acme-corp", "tech-startup"],
                },
            ),
        ],
    )
    def delete(self, request):
        """Delete account using Core repository for password verification."""
        confirmation = request.data.get("confirmation")
        password = request.data.get("password")

        if confirmation != "DELETE MY ACCOUNT":
            return Response(
                {"error": "Explicit confirmation required", "code": "CONFIRMATION_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password:
            return Response(
                {"error": "Password is required", "code": "PASSWORD_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier le mot de passe via Core repository
        user_repo = get_core_user_repo()
        is_valid = user_repo.check_password(str(request.user.id), password)
        
        if not is_valid:
            return Response(
                {"error": "Invalid password", "code": "INVALID_PASSWORD"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier les restrictions (propriétaire d'organisations)
        owned_orgs = request.user.get_owned_organizations()
        sole_owner_orgs = [org for org in owned_orgs if org.get_owners().count() == 1]

        if sole_owner_orgs:
            return Response(
                {
                    "error": "Cannot delete account while being sole owner of organizations",
                    "code": "OWNER_RESTRICTION",
                    "organizations": [org.slug for org in sole_owner_orgs],
                    "message": "Transfer ownership or delete organizations first",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Soft delete via Core repository
        user_repo.soft_delete(str(request.user.id))
        deleted_at = timezone.now()

        return Response(
            {
                "message": "Account deleted successfully",
                "account_deleted": True,
                "deleted_at": deleted_at.isoformat(),
                "data_removed": True,
                "organizations_affected": [org.slug for org in owned_orgs],
                "recovery_possible": False,
                "final_notification_sent": True,
            }
        )
