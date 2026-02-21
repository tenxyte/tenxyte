"""
Dashboard views — Admin dashboard statistics endpoints.

All endpoints require `dashboard.view` permission.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from ..services.stats_service import StatsService
from ..decorators import require_permission


class DashboardGlobalView(APIView):
    """
    GET /api/auth/dashboard/stats/
    Cross-module aggregate stats for admin panel.
    """

    @extend_schema(
        tags=['Dashboard'],
        summary="Stats globales",
        description="Agrégats cross-modules : users, auth, applications, security, GDPR.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('dashboard.view')
    def get(self, request):
        service = StatsService()
        return Response(service.get_global_stats())


class DashboardAuthView(APIView):
    """
    GET /api/auth/dashboard/auth/
    Detailed authentication statistics.
    """

    @extend_schema(
        tags=['Dashboard'],
        summary="Stats d'authentification",
        description="Login stats, méthodes, registrations, tokens, top failure reasons, graphiques 7j.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('dashboard.view')
    def get(self, request):
        service = StatsService()
        return Response(service.get_auth_stats())


class DashboardSecurityView(APIView):
    """
    GET /api/auth/dashboard/security/
    Security-focused statistics.
    """

    @extend_schema(
        tags=['Dashboard'],
        summary="Stats de sécurité",
        description="Audit summary, blacklisted tokens, activité suspecte, adoption 2FA.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('dashboard.view')
    def get(self, request):
        service = StatsService()
        return Response(service.get_security_stats())


class DashboardGDPRView(APIView):
    """
    GET /api/auth/dashboard/gdpr/
    GDPR compliance statistics.
    """

    @extend_schema(
        tags=['Dashboard'],
        summary="Stats RGPD",
        description="Demandes de suppression par statut, exports de données.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('dashboard.view')
    def get(self, request):
        service = StatsService()
        return Response(service.get_gdpr_stats())


class DashboardOrganizationsView(APIView):
    """
    GET /api/auth/dashboard/organizations/
    Organization statistics (only if organizations are enabled).
    """

    @extend_schema(
        tags=['Dashboard'],
        summary="Stats organisations",
        description="Organisations, membres, rôles, top organisations.",
        responses={200: OpenApiTypes.OBJECT}
    )
    @require_permission('dashboard.view')
    def get(self, request):
        service = StatsService()
        return Response(service.get_organization_stats())
