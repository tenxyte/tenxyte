from django.http import JsonResponse, HttpResponse
from .conf import auth_settings


class RequestIDMiddleware:
    """
    Middleware pour ajouter un X-Request-ID unique à chaque requête pour la traçabilité.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import uuid

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class ApplicationAuthMiddleware:
    """
    Middleware pour valider l'authentification de l'application (première couche).

    Can be disabled by setting in settings.py:
        TENXYTE_APPLICATION_AUTH_ENABLED = False
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if application auth is disabled
        if not auth_settings.APPLICATION_AUTH_ENABLED:
            request.application = None
            return self.get_response(request)

        # Get exempt paths from config
        exempt_paths = auth_settings.EXEMPT_PATHS
        exact_exempt_paths = auth_settings.EXACT_EXEMPT_PATHS

        # Vérifier si le chemin est exempté (exact match)
        if request.path in exact_exempt_paths:
            request.application = None
            return self.get_response(request)

        # Vérifier si le chemin est exempté (prefix match)
        for path in exempt_paths:
            if request.path.startswith(path):
                request.application = None
                return self.get_response(request)

        # Récupérer les credentials de l'application
        access_key = request.headers.get("X-Access-Key")
        access_secret = request.headers.get("X-Access-Secret")

        if not access_key or not access_secret:
            return JsonResponse({"error": "Missing application credentials", "code": "APP_AUTH_REQUIRED"}, status=401)

        try:
            from .models import Application  # Lazy import for faster startup

            application = Application.objects.get(access_key=access_key, is_active=True)

            # VULN-006 Mitigation: Cache successful bcrypt verifications for 60 seconds to prevent DoS
            from django.core.cache import cache
            import hashlib

            secret_hash = hashlib.sha256(access_secret.encode("utf-8")).hexdigest()
            cache_key = f"app_auth_ok_{application.id}_{secret_hash}"

            if not cache.get(cache_key):
                if not application.verify_secret(access_secret):
                    return JsonResponse(
                        {"error": "Invalid application credentials", "code": "APP_AUTH_INVALID"}, status=401
                    )
                cache.set(cache_key, True, 60)

            # Attacher l'application à la requête
            request.application = application

        except Application.DoesNotExist:
            return JsonResponse({"error": "Invalid application credentials", "code": "APP_AUTH_INVALID"}, status=401)

        return self.get_response(request)


class JWTAuthMiddleware:
    """
    Middleware pour valider le JWT (deuxième couche - optionnel)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt_service = None

    @property
    def jwt_service(self):
        """Lazy-initialize JWTService on first access."""
        if self._jwt_service is None:
            from tenxyte.core.jwt_service import JWTService
            from tenxyte.adapters.django import get_django_settings
            from tenxyte.adapters.django.cache_service import DjangoCacheService

            self._jwt_service = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
        return self._jwt_service

    def __call__(self, request):
        # Récupérer le token d'autorisation
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = self.jwt_service.decode_token(token)

            if payload and payload.is_valid:
                request.jwt_payload = payload
                request.user_id = payload.user_id
            else:
                request.jwt_payload = None
                request.user_id = None
        else:
            request.jwt_payload = None
            request.user_id = None

        return self.get_response(request)


class CORSMiddleware:
    """
    Middleware CORS intégré à Tenxyte.

    Gère les requêtes preflight (OPTIONS) et ajoute les headers CORS aux réponses.

    Activation dans settings.py:
        TENXYTE_CORS_ENABLED = True
        TENXYTE_CORS_ALLOWED_ORIGINS = ['https://example.com', 'http://localhost:3000']

    Ajoutez dans MIDDLEWARE (avant ApplicationAuthMiddleware):
        'tenxyte.middleware.CORSMiddleware',
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si CORS désactivé, passer directement
        if not auth_settings.CORS_ENABLED:
            return self.get_response(request)

        origin = request.META.get("HTTP_ORIGIN")

        # Preflight (OPTIONS)
        if request.method == "OPTIONS" and origin:
            response = HttpResponse()
            response.status_code = 200
            self._add_cors_headers(response, origin)
            return response

        response = self.get_response(request)

        if origin:
            self._add_cors_headers(response, origin)

        return response

    def _is_origin_allowed(self, origin):
        if auth_settings.CORS_ALLOW_ALL_ORIGINS:
            return True
        return origin in auth_settings.CORS_ALLOWED_ORIGINS

    def _add_cors_headers(self, response, origin):
        if not self._is_origin_allowed(origin):
            return

        response["Access-Control-Allow-Origin"] = origin
        response["Vary"] = "Origin"

        if auth_settings.CORS_ALLOW_CREDENTIALS:
            response["Access-Control-Allow-Credentials"] = "true"

        if auth_settings.CORS_EXPOSE_HEADERS:
            response["Access-Control-Expose-Headers"] = ", ".join(auth_settings.CORS_EXPOSE_HEADERS)

        # Headers spécifiques au preflight
        response["Access-Control-Allow-Methods"] = ", ".join(auth_settings.CORS_ALLOWED_METHODS)
        response["Access-Control-Allow-Headers"] = ", ".join(auth_settings.CORS_ALLOWED_HEADERS)
        response["Access-Control-Max-Age"] = str(auth_settings.CORS_MAX_AGE)


class SecurityHeadersMiddleware:
    """
    Middleware pour ajouter des headers de sécurité aux réponses.

    Activation dans settings.py:
        TENXYTE_SECURITY_HEADERS_ENABLED = True

    Headers par défaut:
        X-Content-Type-Options: nosniff
        X-Frame-Options: DENY
        Referrer-Policy: strict-origin-when-cross-origin
        Strict-Transport-Security: max-age=31536000; includeSubDomains
        Content-Security-Policy: default-src 'none'; frame-ancestors 'none'

    Personnalisation:
        TENXYTE_SECURITY_HEADERS = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        }

    Ajoutez dans MIDDLEWARE:
        'tenxyte.middleware.SecurityHeadersMiddleware',
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if auth_settings.SECURITY_HEADERS_ENABLED:
            for header, value in auth_settings.SECURITY_HEADERS.items():
                response[header] = value

        return response


class OrganizationContextMiddleware:
    """
    Middleware to attach organization context to requests (Couche 3 - opt-in).

    Active only if TENXYTE_ORGANIZATIONS_ENABLED = True.

    Reads X-Org-Slug header and attaches request.organization if found.
    Sets the global context via tenxyte.tenant_context to enforce Hard Multi-Tenancy.
    Does NOT enforce membership - that's the job of decorators.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .conf import org_settings
        from .tenant_context import set_current_organization

        # Feature disabled - skip
        if not org_settings.ORGANIZATIONS_ENABLED:
            request.organization = None
            set_current_organization(None)
            return self.get_response(request)

        # Read X-Org-Slug header
        org_slug = request.headers.get("X-Org-Slug")

        if org_slug:
            try:
                from .models import get_organization_model

                Organization = get_organization_model()

                organization = Organization.objects.get(slug=org_slug, is_active=True)
                request.organization = organization

                # Set multi-tenant context for ORM
                set_current_organization(organization)

            except Organization.DoesNotExist:
                set_current_organization(None)
                return JsonResponse(
                    {"error": "Organization not found", "code": "ORG_NOT_FOUND", "slug": org_slug}, status=404
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error loading organization in middleware: {e}", exc_info=True)
                set_current_organization(None)
                return JsonResponse(
                    {"error": "An unexpected error occurred while loading the organization.", "code": "ORG_ERROR"},
                    status=500,
                )
        else:
            # No org header - that's OK, not all endpoints need it
            request.organization = None
            set_current_organization(None)

        try:
            return self.get_response(request)
        finally:
            # Always clean up context at end of request to prevent state leakage
            # if server threads are reused
            set_current_organization(None)


class AgentTokenMiddleware:
    """
    Couche 4 AIRS: Si l'Authorization header est 'AgentBearer <token>',
    valide l'AgentToken et l'attache à request.agent_token.
    Vérifie le circuit breaker à chaque requête.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("AgentBearer "):
            request.agent_token = None
            return self.get_response(request)

        from tenxyte.conf import auth_settings

        if not getattr(auth_settings, "AIRS_ENABLED", True):
            return JsonResponse({"error": "AIRS module is disabled.", "code": "AIRS_DISABLED"}, status=403)

        raw_token = auth[12:]
        from tenxyte.services.agent_service import AgentTokenService

        service = AgentTokenService()
        agent_token, error = service.validate(raw_token)

        if error:
            return JsonResponse({"error": error, "code": f"AGENT_TOKEN_{error}"}, status=403)

        ok, suspend_reason = service.check_circuit_breaker(agent_token)
        if not ok:
            return JsonResponse(
                {
                    "error": "Agent token suspended by circuit breaker",
                    "code": "AGENT_TOKEN_SUSPENDED",
                    "reason": suspend_reason,
                },
                status=403,
            )

        request.agent_token = agent_token
        request.user = agent_token.triggered_by  # L'agent agit "en tant que" l'humain
        request.user_id = agent_token.triggered_by_id

        response = self.get_response(request)

        # Log successful mutations by agents
        if request.method in ["POST", "PUT", "PATCH", "DELETE"] and 200 <= response.status_code < 300:
            from tenxyte.models.security import AuditLog
            from tenxyte.conf import auth_settings

            prompt_trace_id = request.headers.get("X-Prompt-Trace-ID")
            if prompt_trace_id:
                # Sanitize / Validate prompt_trace_id (Max 128 chars, alphanumeric & dashes only)
                import re

                if not re.match(r"^[\w\-]{1,128}$", prompt_trace_id):
                    prompt_trace_id = None

            if auth_settings.AUDIT_LOGGING_ENABLED:
                AuditLog.log(
                    action="suspicious_activity" if request.method == "DELETE" else "agent_action",
                    user=request.user,
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    application=getattr(request, "application", None),
                    details={
                        "endpoint": request.path,
                        "method": request.method,
                        "actor": agent_token.agent_id,
                        "status_code": response.status_code,
                    },
                    agent_token=agent_token,
                    on_behalf_of=request.user,
                    prompt_trace_id=prompt_trace_id,
                )

        return response


class PIIRedactionMiddleware:
    """
    Si la requête est authentifiée via AgentToken ET que TENXYTE_AIRS_REDACT_PII=True,
    intercepte la réponse JSON et masque les champs PII configurés.
    """

    PII_FIELDS = {
        "email",
        "phone",
        "ssn",
        "date_of_birth",
        "address",
        "credit_card",
        "password",
        "totp_secret",
        "backup_codes",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only redact if request is via AgentToken
        agent_token = getattr(request, "agent_token", None)
        if not agent_token:
            return response

        from tenxyte.conf import auth_settings

        if not getattr(auth_settings, "AIRS_REDACT_PII", False):
            return response

        if response.get("Content-Type", "").startswith("application/json"):
            import json

            try:
                data = json.loads(response.content)
                data = self._redact(data)
                response.content = json.dumps(data).encode("utf-8")
            except (ValueError, TypeError):
                pass

        return response

    def _redact(self, obj):
        """Redact PII fields recursively in JSON."""
        if isinstance(obj, dict):
            return {
                k: "***REDACTED***" if str(k).lower() in self.PII_FIELDS else self._redact(v) for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._redact(item) for item in obj]
        return obj
