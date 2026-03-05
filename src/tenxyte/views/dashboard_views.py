"""
Dashboard views — Admin dashboard statistics endpoints.

All endpoints require `dashboard.view` permission.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..services.stats_service import StatsService
from ..decorators import require_permission


class DashboardGlobalView(APIView):
    """
    GET {API_PREFIX}/auth/dashboard/stats/
    Cross-module aggregate stats for admin panel.
    """

    @extend_schema(
        tags=["Dashboard"],
        summary="Tableau de bord global",
        description="Retourne les statistiques agrégées cross-modules pour le tableau de bord admin. "
        "Les données varient selon le contexte organisationnel (X-Org-Slug) et les permissions. "
        "Inclut les métriques utilisateurs, authentification, applications, sécurité, et RGPD. "
        "Les graphiques couvrent les 7 derniers jours avec comparaisons période précédente.",
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                description="Slug organisation pour filtrer les données par organisation",
                required=False,
            ),
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=["7d", "30d", "90d"],
                description="Période d'analyse (par défaut: 7d)",
                required=False,
            ),
            OpenApiParameter(
                name="compare",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Inclure comparaison avec période précédente",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_users": {"type": "integer"},
                            "active_users": {"type": "integer"},
                            "total_organizations": {"type": "integer"},
                            "total_applications": {"type": "integer"},
                            "active_sessions": {"type": "integer"},
                            "pending_deletions": {"type": "integer"},
                        },
                    },
                    "trends": {
                        "type": "object",
                        "properties": {
                            "user_growth": {"type": "number"},
                            "login_success_rate": {"type": "number"},
                            "application_usage": {"type": "number"},
                            "security_incidents": {"type": "number"},
                        },
                    },
                    "organization_context": {
                        "type": "object",
                        "properties": {
                            "current_org": {"type": "object", "nullable": True},
                            "user_role": {"type": "string"},
                            "accessible_orgs": {"type": "integer"},
                            "org_specific_stats": {"type": "object"},
                        },
                    },
                    "quick_actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "count": {"type": "integer"},
                                "priority": {"type": "string"},
                            },
                        },
                    },
                    "charts": {
                        "type": "object",
                        "properties": {
                            "daily_logins": {"type": "array"},
                            "user_registrations": {"type": "array"},
                            "security_events": {"type": "array"},
                        },
                    },
                },
            }
        },
        examples=[
            OpenApiExample(
                name="global_dashboard", summary="Dashboard global admin", value={"period": "7d", "compare": True}
            ),
            OpenApiExample(
                name="org_dashboard",
                summary="Dashboard organisation spécifique",
                value={"X-Org-Slug": "acme-corp", "period": "30d"},
            ),
        ],
    )
    @require_permission("dashboard.view")
    def get(self, request):
        service = StatsService()
        return Response(service.get_global_stats())


class DashboardAuthView(APIView):
    """
    GET {API_PREFIX}/auth/dashboard/auth/
    Detailed authentication statistics.
    """

    @extend_schema(
        tags=["Dashboard"],
        summary="Stats d'authentification",
        description="Login stats, méthodes, registrations, tokens, top failure reasons, graphiques 7j.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_permission("dashboard.view")
    def get(self, request):
        service = StatsService()
        return Response(service.get_auth_stats())


class DashboardSecurityView(APIView):
    """
    GET {API_PREFIX}/auth/dashboard/security/
    Security-focused statistics.
    """

    @extend_schema(
        tags=["Dashboard"],
        summary="Stats de sécurité",
        description="Audit summary, blacklisted tokens, activité suspecte, adoption 2FA.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_permission("dashboard.view")
    def get(self, request):
        service = StatsService()
        return Response(service.get_security_stats())


class DashboardGDPRView(APIView):
    """
    GET {API_PREFIX}/auth/dashboard/gdpr/
    GDPR compliance statistics.
    """

    @extend_schema(
        tags=["Dashboard"],
        summary="Stats RGPD",
        description="Demandes de suppression par statut, exports de données.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_permission("dashboard.view")
    def get(self, request):
        service = StatsService()
        return Response(service.get_gdpr_stats())


class DashboardOrganizationsView(APIView):
    """
    GET {API_PREFIX}/auth/dashboard/organizations/
    Organization statistics (only if organizations are enabled).
    """

    @extend_schema(
        tags=["Dashboard"],
        summary="Stats organisations",
        description="Organisations, membres, rôles, top organisations.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @require_permission("dashboard.view")
    def get(self, request):
        service = StatsService()
        return Response(service.get_organization_stats())
