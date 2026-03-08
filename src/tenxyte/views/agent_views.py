from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from tenxyte.models.agent import AgentToken, AgentPendingAction
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.models.base import get_application_model
from django.utils import timezone
from tenxyte.conf import auth_settings
from django.core.exceptions import PermissionDenied

# ---------------------------------------------------------------------------
# Shared inline serializers for schema documentation
# ---------------------------------------------------------------------------
_AgentTokenOut = dict(
    id=serializers.IntegerField(),
    agent_id=serializers.CharField(),
    status=serializers.CharField(),
    expires_at=serializers.DateTimeField(),
    created_at=serializers.DateTimeField(),
    organization=serializers.CharField(allow_null=True),
    current_request_count=serializers.IntegerField(),
)

_ErrorOut = dict(
    error=serializers.CharField(),
    code=serializers.CharField(required=False),
)


class AgentTokenListCreateView(APIView):
    """
    GET /ai/tokens/
    POST /ai/tokens/
    Liste les AgentTokens actifs ou en crée un nouveau.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Liste les tokens agent de l'utilisateur",
        description="Retourne tous les AgentTokens créés par l'utilisateur authentifié. "
        "Si X-Org-Slug est fourni, filtre les tokens liés à cette organisation.",
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation pour filtrer les tokens (multi-tenant context)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="AgentTokenList",
                fields={**_AgentTokenOut},
                many=True,
            )
        },
    )
    def get(self, request):
        tokens = AgentToken.objects.filter(triggered_by=request.user).order_by("-created_at")
        result = []
        for t in tokens:
            result.append(
                {
                    "id": t.id,
                    "agent_id": t.agent_id,
                    "status": t.status,
                    "expires_at": t.expires_at.isoformat(),
                    "created_at": t.created_at.isoformat(),
                    "organization": t.organization.slug if t.organization else None,
                    "current_request_count": t.current_request_count,
                }
            )
        return JsonResponse(result, safe=False)

    @extend_schema(
        tags=["AI Agents"],
        summary="Crée un nouveau token agent (AIRS)",
        description=(
            "Crée un AgentToken avec des permissions limitées pour un agent IA. "
            "Le token utilise le scheme AgentBearer pour s'identifier. "
            "Nécessite que AIRS_ENABLED soit True dans la configuration. "
            "Le contexte organisationnel peut être fourni via le header X-Org-Slug "
            "ou via le champ 'organization' dans le corps de la requête."
        ),
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation (multi-tenant context) — alternatif au champ organization du body",
            ),
        ],
        request=inline_serializer(
            name="AgentTokenCreateRequest",
            fields={
                "agent_id": serializers.CharField(help_text="Identifiant de l'agent (ex: 'my-bot-v1')"),
                "expires_in": serializers.IntegerField(required=False, help_text="Durée de validité en secondes"),
                "permissions": serializers.ListField(
                    child=serializers.CharField(),
                    required=False,
                    help_text="Liste des permissions demandées",
                ),
                "organization": serializers.CharField(
                    required=False, help_text="Slug organisation (alternatif à X-Org-Slug header)"
                ),
                "budget_limit_usd": serializers.FloatField(required=False, help_text="Budget max en USD"),
                "circuit_breaker": serializers.DictField(required=False),
                "dead_mans_switch": serializers.DictField(required=False),
            },
        ),
        responses={
            201: inline_serializer(
                name="AgentTokenCreated",
                fields={
                    "id": serializers.IntegerField(),
                    "token": serializers.CharField(help_text="Token brut AgentBearer (secret, à stocker)"),
                    "agent_id": serializers.CharField(),
                    "status": serializers.CharField(),
                    "expires_at": serializers.DateTimeField(),
                },
            ),
            400: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
            403: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
        examples=[
            OpenApiExample(
                name="create_minimal",
                summary="Token minimal",
                description="Créer un token avec seulement l'identifiant agent (durée et permissions par défaut).",
                request_only=True,
                value={
                    "agent_id": "my-bot-v1",
                },
            ),
            OpenApiExample(
                name="create_full",
                summary="Token complet avec budget et circuit-breaker",
                description="Créer un token avec permissions, budget max, et circuit-breaker configuré.",
                request_only=True,
                value={
                    "agent_id": "finance-agent-v2",
                    "expires_in": 3600,
                    "permissions": ["read:reports", "write:invoices"],
                    "organization": "acme-corp",
                    "budget_limit_usd": 5.00,
                    "circuit_breaker": {
                        "max_requests": 100,
                        "window_seconds": 60,
                    },
                },
            ),
            OpenApiExample(
                name="create_success",
                summary="Token créé avec succès",
                response_only=True,
                status_codes=["201"],
                value={
                    "id": 7,
                    "token": "AgentBearer eyJ...",
                    "agent_id": "my-bot-v1",
                    "status": "active",
                    "expires_at": "2024-01-20T15:00:00Z",
                },
            ),
            OpenApiExample(
                name="permission_denied",
                summary="Permission refusée",
                response_only=True,
                status_codes=["403"],
                value={
                    "error": "Agent not allowed to request this permission",
                    "code": "PERMISSION_DENIED",
                },
            ),
        ],
    )
    def post(self, request):
        if not getattr(auth_settings, "AIRS_ENABLED", True):
            return JsonResponse({"error": "AIRS is disabled"}, status=400)

        data = request.data
        agent_id = data.get("agent_id", "unknown")
        expires_in = data.get("expires_in")
        permissions_requested = data.get("permissions", [])
        # Resolve organization slug: body field takes precedence, header is the fallback
        organization_slug = data.get("organization") or request.headers.get("X-Org-Slug")
        budget_limit_usd = data.get("budget_limit_usd")

        # Requires application
        application = getattr(request, "application", None)
        if not application:
            Application = get_application_model()
            app = Application.objects.filter(is_active=True).first()
            if not app:
                return JsonResponse({"error": "Application context required"}, status=400)
            application = app

        organization = None
        if organization_slug:
            try:
                from tenxyte.models.base import get_organization_model

                Organization = get_organization_model()
                organization = Organization.objects.get(slug=organization_slug, is_active=True)
            except Exception:
                return JsonResponse({"error": "Organization not found"}, status=404)

        service = AgentTokenService()

        try:
            token = service.create(
                triggered_by=request.user,
                application=application,
                granted_permissions=permissions_requested,
                expires_in=expires_in,
                agent_id=agent_id,
                organization=organization,
                circuit_breaker=data.get("circuit_breaker"),
                dead_mans_switch=data.get("dead_mans_switch"),
                budget_limit_usd=budget_limit_usd,
            )
        except PermissionDenied as e:
            return JsonResponse({"error": str(e), "code": "PERMISSION_DENIED"}, status=403)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Error creating agent token: {e}", exc_info=True)
            return JsonResponse({"error": "An unexpected error occurred."}, status=400)

        return JsonResponse(
            {
                "id": token.id,
                "token": token.raw_token if hasattr(token, "raw_token") and token.raw_token else token.token,
                "agent_id": token.agent_id,
                "status": token.status,
                "expires_at": token.expires_at.isoformat(),
            },
            status=201,
        )


class AgentTokenDetailView(APIView):
    """
    GET /ai/tokens/{id}/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Détails d'un token agent",
        description="Retourne les détails d'un AgentToken appartenant à l'utilisateur.",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID du token agent")],
        responses={
            200: inline_serializer("AgentTokenDetail", fields={**_AgentTokenOut}),
            404: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
    )
    def get(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        return JsonResponse(
            {
                "id": t.id,
                "agent_id": t.agent_id,
                "status": t.status,
                "expires_at": t.expires_at.isoformat(),
                "created_at": t.created_at.isoformat(),
                "organization": t.organization.slug if t.organization else None,
                "current_request_count": t.current_request_count,
            }
        )


class AgentTokenRevokeView(APIView):
    """
    POST /ai/tokens/{id}/revoke/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Révoque un token agent",
        description="Révoque immédiatement un AgentToken. Le token ne pourra plus être utilisé.",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID du token agent")],
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            404: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
    )
    def post(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        AgentTokenService().revoke(t, revoked_by=request.user)
        return JsonResponse({"status": "revoked"})


class AgentTokenSuspendView(APIView):
    """
    POST /ai/tokens/{id}/suspend/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Suspend un token agent",
        description="Suspend temporairement un AgentToken (raison: MANUAL).",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID du token agent")],
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            404: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
    )
    def post(self, request, pk):
        try:
            t = AgentToken.objects.get(pk=pk, triggered_by=request.user)
        except AgentToken.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        AgentTokenService().suspend(t, reason=AgentToken.SuspendedReason.MANUAL)
        return JsonResponse({"status": "suspended"})


class AgentTokenHeartbeatView(APIView):
    """
    POST /ai/tokens/{id}/heartbeat/
    Called by the agent itself using the AgentBearer token.
    """

    @extend_schema(
        tags=["AI Agents"],
        summary="Heartbeat d'un token agent",
        description=(
            "Signal de vie envoyé par l'agent. "
            "Utilise le scheme `AgentBearer <token>` dans l'en-tête Authorization. "
            "Renouvelle le dead man's switch si configuré."
        ),
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID du token agent"),
            OpenApiParameter(
                name="Authorization",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                description="AgentBearer <raw_token>",
                required=True,
            ),
        ],
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            401: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
            403: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
    )
    def post(self, request, pk):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("AgentBearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        raw_token = auth[12:]
        service = AgentTokenService()
        token, error = service.validate(raw_token)

        if error or str(token.id) != str(pk):
            return JsonResponse({"error": "Unauthorized or token mismatch"}, status=403)

        service.send_heartbeat(token)
        return JsonResponse({"status": "ok"})


class AgentTokenRevokeAllView(APIView):
    """
    POST /ai/tokens/revoke-all/
    Coupe-circuit nucléaire.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Révoque tous les tokens agent (coupe-circuit)",
        description=(
            "Révoque immédiatement TOUS les AgentTokens actifs de l'utilisateur. " "Action de coupe-circuit d'urgence."
        ),
        responses={
            200: inline_serializer(
                "AgentRevokeAllOk",
                fields={
                    "status": serializers.CharField(),
                    "count": serializers.IntegerField(help_text="Nombre de tokens révoqués"),
                },
            ),
        },
    )
    def post(self, request):
        count = AgentTokenService().revoke_all_for_user(request.user)
        return JsonResponse({"status": "revoked", "count": count})


class AgentPendingActionListView(APIView):
    """
    GET /ai/pending-actions/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Liste les actions en attente de validation HITL",
        description=(
            "Retourne les AgentPendingActions non-confirmées et non-expirées "
            "des agents de l'utilisateur. HITL = Human-In-The-Loop. "
            "Si X-Org-Slug est fourni, filtre les actions relatives aux tokens de cette organisation."
        ),
        parameters=[
            OpenApiParameter(
                name="X-Org-Slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Slug de l'organisation pour filtrer les actions (multi-tenant context)",
            ),
        ],
        responses={
            200: inline_serializer(
                "AgentPendingActionList",
                fields={
                    "id": serializers.IntegerField(),
                    "agent_id": serializers.CharField(),
                    "permission": serializers.CharField(),
                    "endpoint": serializers.CharField(),
                    "payload": serializers.DictField(allow_null=True),
                    "confirmation_token": serializers.CharField(),
                    "expires_at": serializers.DateTimeField(),
                    "created_at": serializers.DateTimeField(),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        actions = AgentPendingAction.objects.filter(
            agent_token__triggered_by=request.user,
            confirmed_at__isnull=True,
            denied_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")

        result = []
        for a in actions:
            result.append(
                {
                    "id": a.id,
                    "agent_id": a.agent_token.agent_id,
                    "permission": a.permission_requested,
                    "endpoint": a.endpoint,
                    "payload": a.payload,
                    "confirmation_token": a.confirmation_token,
                    "expires_at": a.expires_at.isoformat(),
                    "created_at": a.created_at.isoformat(),
                }
            )
        return JsonResponse(result, safe=False)


class AgentPendingActionConfirmView(APIView):
    """
    POST /ai/pending-actions/confirm/
    Body: {"token": "..."}
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Confirme une action agent en attente (HITL)",
        description="Approuve une action agent en attente via son confirmation_token. "
        "Le token est reçu par l'humain (email, webhook, etc.) lorsque l'agent "
        "demande une validation. Une fois confirmé, l'agent peut poursuivre l'action.",
        request=inline_serializer(
            "AgentConfirmRequest", fields={"token": serializers.CharField(help_text="Confirmation token de l'action")}
        ),
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            400: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
        examples=[
            OpenApiExample(
                name="confirm_action",
                summary="Confirmer une action agent",
                description="Approuver une action en fournissant son confirmation_token.",
                request_only=True,
                value={
                    "token": "hitl_a1b2c3d4e5f6...",
                },
            ),
            OpenApiExample(
                name="confirm_success",
                summary="Action confirmée",
                response_only=True,
                status_codes=["200"],
                value={
                    "status": "confirmed",
                },
            ),
            OpenApiExample(
                name="invalid_or_expired",
                summary="Token invalide ou expiré",
                response_only=True,
                status_codes=["400"],
                value={
                    "error": "Invalid or expired token",
                },
            ),
        ],
    )
    def post(self, request, token=None):
        passed_token = request.data.get("token") if hasattr(request, "data") else request.POST.get("token")
        if not passed_token and token:
            passed_token = token  # Fallback for backward compatibility if still passed in URL temporarily

        if not passed_token:
            return JsonResponse({"error": "Token is required in the request body."}, status=400)

        service = AgentTokenService()
        action = service.confirm_pending_action(passed_token, confirmed_by=request.user)
        if not action or action.agent_token.triggered_by != request.user:
            return JsonResponse({"error": "Invalid or expired token"}, status=400)

        return JsonResponse({"status": "confirmed"})


class AgentPendingActionDenyView(APIView):
    """
    POST /ai/pending-actions/deny/
    Body: {"token": "..."}
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Agents"],
        summary="Refuse une action agent en attente (HITL)",
        description="Refuse une action agent en attente via son confirmation_token. "
        "Le token est reçu par l'humain lorsque l'agent demande une validation. "
        "Une fois refusée, l'agent est notifié que l'action est bloquée.",
        request=inline_serializer(
            "TokenRequest", fields={"token": serializers.CharField(help_text="Confirmation token de l'action")}
        ),
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            400: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
        },
        examples=[
            OpenApiExample(
                name="deny_action",
                summary="Refuser une action agent",
                description="Refuser une action en fournissant son confirmation_token.",
                request_only=True,
                value={
                    "token": "hitl_a1b2c3d4e5f6...",
                },
            ),
            OpenApiExample(
                name="deny_success",
                summary="Action refusée",
                response_only=True,
                status_codes=["200"],
                value={
                    "status": "denied",
                },
            ),
            OpenApiExample(
                name="invalid_or_expired",
                summary="Token invalide ou expiré",
                response_only=True,
                status_codes=["400"],
                value={
                    "error": "Invalid or expired token",
                },
            ),
        ],
    )
    def post(self, request, token=None):
        passed_token = request.data.get("token") if hasattr(request, "data") else request.POST.get("token")
        if not passed_token and token:
            passed_token = token  # Fallback for backward compatibility

        if not passed_token:
            return JsonResponse({"error": "Token is required in the request body."}, status=400)

        service = AgentTokenService()
        action = service.deny_pending_action(passed_token, denied_by=request.user)
        if not action or action.agent_token.triggered_by != request.user:
            return JsonResponse({"error": "Invalid or expired token"}, status=400)

        return JsonResponse({"status": "denied"})


class AgentTokenReportUsageView(APIView):
    """
    POST /ai/tokens/{id}/report-usage/
    """

    @extend_schema(
        tags=["AI Agents"],
        summary="Rapporte l'usage d'un token agent (coûts LLM)",
        description=(
            "Rapporte la consommation LLM d'une session agent. "
            "Utilise AgentBearer dans Authorization. "
            "Si le budget est dépassé, le token est suspendu automatiquement."
        ),
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="ID du token agent"),
            OpenApiParameter(
                "Authorization",
                OpenApiTypes.STR,
                OpenApiParameter.HEADER,
                description="AgentBearer <raw_token>",
                required=True,
            ),
        ],
        request=inline_serializer(
            "AgentReportUsageRequest",
            fields={
                "cost_usd": serializers.FloatField(help_text="Coût en USD de la session"),
                "prompt_tokens": serializers.IntegerField(help_text="Tokens prompt consommés"),
                "completion_tokens": serializers.IntegerField(help_text="Tokens completion consommés"),
            },
        ),
        responses={
            200: inline_serializer("AgentSuccessResponse", fields={"status": serializers.CharField()}),
            401: inline_serializer("AgentErrorResponse", fields={**_ErrorOut}),
            403: inline_serializer(
                "AgentReportUsageBudget", fields={"error": serializers.CharField(), "status": serializers.CharField()}
            ),
        },
        examples=[
            OpenApiExample(
                name="report_usage",
                summary="Rapporter une session LLM",
                description="Indique le coût et les tokens consommés lors de la dernière action de l'agent.",
                request_only=True,
                value={
                    "cost_usd": 0.042,
                    "prompt_tokens": 1250,
                    "completion_tokens": 450,
                },
            ),
            OpenApiExample(
                name="report_success",
                summary="Rapport accepté",
                response_only=True,
                status_codes=["200"],
                value={
                    "status": "ok",
                },
            ),
            OpenApiExample(
                name="budget_exceeded",
                summary="Budget dépassé (Token suspendu)",
                response_only=True,
                status_codes=["403"],
                value={
                    "error": "Budget exceeded",
                    "status": "suspended",
                },
            ),
            OpenApiExample(
                name="unauthorized",
                summary="Non autorisé ou token invalide",
                response_only=True,
                status_codes=["401"],
                value={
                    "error": "Unauthorized",
                },
            ),
        ],
    )
    def post(self, request, pk):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("AgentBearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        raw_token = auth[12:]
        service = AgentTokenService()
        token, error = service.validate(raw_token)

        if error or str(token.id) != str(pk):
            return JsonResponse({"error": "Unauthorized or token mismatch"}, status=403)

        data = request.data
        cost_usd = float(data.get("cost_usd", 0.0))
        prompt_tokens = int(data.get("prompt_tokens", 0))
        completion_tokens = int(data.get("completion_tokens", 0))

        success = service.report_usage(token, cost_usd, prompt_tokens, completion_tokens)

        if not success:
            return JsonResponse({"error": "Budget exceeded", "status": "suspended"}, status=403)

        return JsonResponse({"status": "ok"})
