from functools import wraps
from django.http import JsonResponse
from tenxyte.core.jwt_service import JWTService
from tenxyte.adapters.django import get_django_settings
from tenxyte.adapters.django.cache_service import DjangoCacheService
from .models import get_user_model, get_application_model
from .conf import auth_settings

User = get_user_model()
Application = get_application_model()


def _is_request(obj):
    """Vérifie si un objet est un objet request (Django ou DRF)."""
    return hasattr(obj, "META") and hasattr(obj, "method")


def _extract_request(*args):
    """
    Extrait l'objet request des arguments.
    Gère les deux cas: fonction (request, ...) et méthode (self, request, ...).

    Returns:
        tuple: (view_instance or None, request, remaining_args)
    """
    if args and _is_request(args[0]):
        # Fonction-based view: premier arg est request
        return None, args[0], args[1:]
    elif len(args) >= 2 and _is_request(args[1]):
        # Class-based view: premier arg est self, deuxième est request
        return args[0], args[1], args[2:]
    else:
        return None, None, args


def _call_view(view_func, view_instance, request, view_args, kwargs):
    """Appelle la vue avec les bons arguments."""
    if view_instance is not None:
        return view_func(view_instance, request, *view_args, **kwargs)
    else:
        return view_func(request, *view_args, **kwargs)


def require_jwt(view_func):
    """
    Décorateur pour exiger un JWT valide.
    Fonctionne avec les fonctions ET les méthodes de classe.

    Can be disabled globally by setting in settings.py:
        TENXYTE_JWT_AUTH_ENABLED = False

    WARNING: Disabling JWT auth is dangerous and should only be used for testing.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        view_instance, request, view_args = _extract_request(*args)

        if request is None:
            return JsonResponse({"error": "Invalid request object", "code": "INVALID_REQUEST"}, status=400)

        # Skip JWT validation if disabled (DANGEROUS - for testing only)
        if not auth_settings.JWT_AUTH_ENABLED:
            request.user = None
            request.jwt_payload = None
            return _call_view(view_func, view_instance, request, view_args, kwargs)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization header required", "code": "AUTH_REQUIRED"}, status=401)

        token = auth_header[7:]
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )
        payload = jwt_service.decode_token(token)

        if not payload or not payload.is_valid:
            return JsonResponse({"error": "Invalid or expired token", "code": "TOKEN_INVALID"}, status=401)

        # Vérifier que l'application du token correspond
        application = getattr(request, "application", None)
        if application:
            if str(application.id) != payload.app_id:
                return JsonResponse(
                    {"error": "Token does not match application", "code": "TOKEN_APP_MISMATCH"}, status=401
                )

        # Récupérer l'utilisateur
        try:
            user = User.objects.get(id=payload.user_id)
            if not user.is_active:
                return JsonResponse({"error": "User account is inactive", "code": "USER_INACTIVE"}, status=401)

            if auth_settings.ACCOUNT_LOCKOUT_ENABLED and user.is_account_locked():
                return JsonResponse({"error": "User account is locked", "code": "USER_LOCKED"}, status=401)

            request.user = user
            request.jwt_payload = payload

        except User.DoesNotExist:
            return JsonResponse({"error": "User not found", "code": "USER_NOT_FOUND"}, status=401)

        return _call_view(view_func, view_instance, request, view_args, kwargs)

    return wrapper


def require_verified_email(view_func):
    """
    Décorateur pour exiger un email vérifié.
    """

    @wraps(view_func)
    @require_jwt
    def wrapper(*args, **kwargs):
        view_instance, request, view_args = _extract_request(*args)

        if not request.user.is_email_verified:
            return JsonResponse({"error": "Email verification required", "code": "EMAIL_NOT_VERIFIED"}, status=403)

        return _call_view(view_func, view_instance, request, view_args, kwargs)

    return wrapper


def require_verified_phone(view_func):
    """
    Décorateur pour exiger un téléphone vérifié.
    """

    @wraps(view_func)
    @require_jwt
    def wrapper(*args, **kwargs):
        view_instance, request, view_args = _extract_request(*args)

        if not request.user.is_phone_verified:
            return JsonResponse({"error": "Phone verification required", "code": "PHONE_NOT_VERIFIED"}, status=403)

        return _call_view(view_func, view_instance, request, view_args, kwargs)

    return wrapper


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Décorateur pour le rate limiting personnalisé.

    Can be disabled globally by setting in settings.py:
        TENXYTE_RATE_LIMITING_ENABLED = False
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            # Skip rate limiting if disabled
            if not auth_settings.RATE_LIMITING_ENABLED:
                view_instance, request, view_args = _extract_request(*args)
                return _call_view(view_func, view_instance, request, view_args, kwargs)

            from django.core.cache import cache

            view_instance, request, view_args = _extract_request(*args)

            # Identifier par IP ou user_id
            if hasattr(request, "user") and request.user and hasattr(request.user, "id"):
                identifier = f"rate_limit:{view_func.__name__}:user:{request.user.id}"
            else:
                ip = get_client_ip(request)
                identifier = f"rate_limit:{view_func.__name__}:ip:{ip}"

            # Récupérer le compteur actuel
            current = cache.get(identifier, 0)

            if current >= max_requests:
                return JsonResponse(
                    {"error": "Rate limit exceeded", "code": "RATE_LIMITED", "retry_after": window_seconds}, status=429
                )

            # Incrémenter le compteur
            cache.set(identifier, current + 1, window_seconds)

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def get_client_ip(request) -> str:
    """
    Récupère l'adresse IP du client en tenant compte des proxy de confiance.
    Utilise TENXYTE_NUM_PROXIES pour déterminer de manière sûre l'IP client
    à partir de l'en-tête X-Forwarded-For si l'application est derrière des proxies.
    Si TENXYTE_TRUSTED_PROXIES est défini, vérifie en plus que le proxy direct
    est de confiance.
    """
    from .conf import auth_settings

    num_proxies = getattr(auth_settings, "NUM_PROXIES", 0)
    trusted = getattr(auth_settings, "TRUSTED_PROXIES", [])

    remote_addr = request.META.get("REMOTE_ADDR", "")
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for and num_proxies > 0:
        # Validate that REMOTE_ADDR is in TRUSTED_PROXIES
        # SECURITY VULN-003: If TRUSTED_PROXIES is empty, always reject X-Forwarded-For to prevent spoofing
        if not trusted:
            import logging

            logging.getLogger("tenxyte.security").warning(
                "X-Forwarded-For header rejected: TENXYTE_TRUSTED_PROXIES is empty but TENXYTE_NUM_PROXIES > 0. "
                "Configure trusted proxies to enable secure IP resolution behind a reverse proxy."
            )
            return remote_addr

        is_trusted = False
        import ipaddress

        try:
            remote_ip = ipaddress.ip_address(remote_addr)
            for trusted_entry in trusted:
                try:
                    network = ipaddress.ip_network(trusted_entry, strict=False)
                    if remote_ip in network:
                        is_trusted = True
                        break
                except ValueError:
                    continue
        except ValueError:
            pass

        if not is_trusted:
            import logging

            logging.getLogger("tenxyte.security").warning(
                "X-Forwarded-For header rejected: REMOTE_ADDR %s is not in TRUSTED_PROXIES.", remote_addr
            )
            return remote_addr

        # Sécurité F-05 : Extraire la bonne IP selon le nombre de proxies de confiance.
        # X-Forwarded-For est une liste : client, proxy1, proxy2...
        # L'IP la plus sûre (insérée par le premier proxy sous notre contrôle)
        # est à l'index -num_proxies.
        proxies = [ip.strip() for ip in x_forwarded_for.split(",")]
        if len(proxies) >= num_proxies:
            return proxies[-num_proxies]
        else:
            return proxies[0]  # Fallback to the first if there are fewer proxies than num_proxies

    return remote_addr or "127.0.0.1"


def _get_permission_denied_response(default_msg: str, code: str, **kwargs):
    from .conf import auth_settings

    verbose = getattr(auth_settings, "VERBOSE_ERRORS", False)
    msg = default_msg if verbose else "Permission denied."

    response_data = {"error": msg, "code": code}
    if verbose:
        response_data.update(kwargs)

    return JsonResponse(response_data, status=403)


# ============== RBAC Decorators ==============


def require_role(role_code: str):
    """
    Décorateur pour exiger un rôle spécifique.
    Usage: @require_role('admin')
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_role(role_code):
                return _get_permission_denied_response(f"Role required: {role_code}", "ROLE_REQUIRED")

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def require_any_role(role_codes: list):
    """
    Décorateur pour exiger au moins un des rôles.
    Usage: @require_any_role(['admin', 'manager'])
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_any_role(role_codes):
                return _get_permission_denied_response(
                    f'One of these roles required: {", ".join(role_codes)}', "ROLE_REQUIRED"
                )

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def require_all_roles(role_codes: list):
    """
    Décorateur pour exiger tous les rôles.
    Usage: @require_all_roles(['admin', 'manager'])
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_all_roles(role_codes):
                return _get_permission_denied_response(
                    f'All these roles required: {", ".join(role_codes)}', "ROLES_REQUIRED"
                )

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def require_permission(permission_code: str):
    """
    Décorateur pour exiger une permission spécifique.
    Usage: @require_permission('users.create')
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_permission(permission_code):
                return _get_permission_denied_response(f"Permission required: {permission_code}", "PERMISSION_REQUIRED")

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def require_any_permission(permission_codes: list):
    """
    Décorateur pour exiger au moins une des permissions.
    Usage: @require_any_permission(['users.create', 'users.update'])
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_any_permission(permission_codes):
                return _get_permission_denied_response(
                    f'One of these permissions required: {", ".join(permission_codes)}', "PERMISSION_REQUIRED"
                )

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


def require_all_permissions(permission_codes: list):
    """
    Décorateur pour exiger toutes les permissions.
    Usage: @require_all_permissions(['users.create', 'users.delete'])
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_jwt
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            if not request.user.has_all_permissions(permission_codes):
                return _get_permission_denied_response(
                    f'All these permissions required: {", ".join(permission_codes)}', "PERMISSIONS_REQUIRED"
                )

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator


# =============================================
# Organization-Scoped Decorators (Opt-in Feature)
# =============================================


def require_org_context(view_func):
    """
    Require request.organization to be set (via X-Org-Slug header).

    Usage:
        @require_jwt
        @require_org_context
        def my_view(request): ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .conf import org_settings

        if not org_settings.ORGANIZATIONS_ENABLED:
            return JsonResponse(
                {"error": "Organizations feature is not enabled", "code": "ORG_FEATURE_DISABLED"}, status=400
            )

        if not hasattr(request, "organization") or request.organization is None:
            return JsonResponse(
                {
                    "error": "Organization context required. Please provide X-Org-Slug header.",
                    "code": "ORG_CONTEXT_REQUIRED",
                },
                status=400,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def require_org_membership(view_func):
    """
    Require user to be an active member of request.organization.
    Attaches request.org_membership.

    Usage:
        @require_jwt
        @require_org_context
        @require_org_membership
        def my_view(request): ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .conf import org_settings

        if not org_settings.ORGANIZATIONS_ENABLED:
            return JsonResponse(
                {"error": "Organizations feature is not enabled", "code": "ORG_FEATURE_DISABLED"}, status=400
            )

        # Check org context
        if not hasattr(request, "organization") or request.organization is None:
            return JsonResponse({"error": "Organization context required", "code": "ORG_CONTEXT_REQUIRED"}, status=400)

        # Check user authentication
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required", "code": "AUTHENTICATION_REQUIRED"}, status=401)

        # Check membership
        if not request.user.is_org_member(request.organization):
            return JsonResponse(
                {
                    "error": "You are not a member of this organization",
                    "code": "ORG_MEMBERSHIP_REQUIRED",
                    "organization": request.organization.slug,
                },
                status=403,
            )

        # Attach membership to request
        request.org_membership = request.user.get_org_membership(request.organization)

        return view_func(request, *args, **kwargs)

    return wrapper


def require_org_role(role_code: str, check_inheritance: bool = True):
    """
    Require user to have a specific role in request.organization.

    Args:
        role_code: Role code required (e.g., 'admin', 'owner')
        check_inheritance: Check parent organizations if enabled

    Usage:
        @require_jwt
        @require_org_context
        @require_org_role('admin')
        def my_view(request): ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .conf import org_settings

            if not org_settings.ORGANIZATIONS_ENABLED:
                return JsonResponse(
                    {"error": "Organizations feature is not enabled", "code": "ORG_FEATURE_DISABLED"}, status=400
                )

            # Check org context
            if not hasattr(request, "organization") or request.organization is None:
                return JsonResponse(
                    {"error": "Organization context required", "code": "ORG_CONTEXT_REQUIRED"}, status=400
                )

            # Check user authentication
            if not hasattr(request, "user") or not request.user.is_authenticated:
                return JsonResponse({"error": "Authentication required", "code": "AUTHENTICATION_REQUIRED"}, status=401)

            # Check role
            if not request.user.has_org_role(request.organization, role_code, check_inheritance=check_inheritance):
                return _get_permission_denied_response(
                    f'Organization role "{role_code}" required', "ORG_ROLE_REQUIRED", required_role=role_code
                )

            # Attach membership to request
            if not hasattr(request, "org_membership"):
                request.org_membership = request.user.get_org_membership(request.organization)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_org_permission(permission_code: str, check_inheritance: bool = True):
    """
    Require user to have a specific organization-level permission.

    Args:
        permission_code: Permission code (e.g., 'org.members.invite')
        check_inheritance: Check parent organizations if enabled

    Usage:
        @require_jwt
        @require_org_context
        @require_org_permission('org.members.invite')
        def my_view(request): ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .conf import org_settings

            if not org_settings.ORGANIZATIONS_ENABLED:
                return JsonResponse(
                    {"error": "Organizations feature is not enabled", "code": "ORG_FEATURE_DISABLED"}, status=400
                )

            # Check org context
            if not hasattr(request, "organization") or request.organization is None:
                return JsonResponse(
                    {"error": "Organization context required", "code": "ORG_CONTEXT_REQUIRED"}, status=400
                )

            # Check user authentication
            if not hasattr(request, "user") or not request.user.is_authenticated:
                return JsonResponse({"error": "Authentication required", "code": "AUTHENTICATION_REQUIRED"}, status=401)

            # Check permission
            if not request.user.has_org_permission(
                request.organization, permission_code, check_inheritance=check_inheritance
            ):
                return _get_permission_denied_response(
                    f'Organization permission "{permission_code}" required',
                    "ORG_PERMISSION_REQUIRED",
                    required_permission=permission_code,
                )

            # Attach membership to request
            if not hasattr(request, "org_membership"):
                request.org_membership = request.user.get_org_membership(request.organization)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_org_owner(view_func):
    """
    Shortcut decorator to require organization owner role.

    Usage:
        @require_jwt
        @require_org_context
        @require_org_owner
        def my_view(request): ...
    """
    return require_org_role("owner", check_inheritance=False)(view_func)


def require_org_admin(view_func):
    """
    Shortcut decorator to require organization admin role (with inheritance).
    Owner role also satisfies this check (owner >= admin).

    Usage:
        @require_jwt
        @require_org_context
        @require_org_admin
        def my_view(request): ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .conf import org_settings

        if not org_settings.ORGANIZATIONS_ENABLED:
            return JsonResponse(
                {"error": "Organizations feature is not enabled", "code": "ORG_FEATURE_DISABLED"}, status=400
            )

        if not hasattr(request, "organization") or request.organization is None:
            return JsonResponse({"error": "Organization context required", "code": "ORG_CONTEXT_REQUIRED"}, status=400)

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required", "code": "AUTHENTICATION_REQUIRED"}, status=401)

        is_admin = request.user.has_org_role(request.organization, "admin", check_inheritance=True)
        is_owner = request.user.has_org_role(request.organization, "owner", check_inheritance=False)
        if not (is_admin or is_owner):
            return _get_permission_denied_response(
                "Organization admin or owner role required", "ORG_ROLE_REQUIRED", required_role="admin"
            )

        if not hasattr(request, "org_membership"):
            request.org_membership = request.user.get_org_membership(request.organization)

        return view_func(request, *args, **kwargs)

    return wrapper


# =============================================
# Agent / AIRS Decorators (Phase 1)
# =============================================


def require_agent_clearance(
    permission_code: str = None, human_in_the_loop_required: bool = False, max_risk_score: int = 100
):
    """
    Décorateur pour les endpoints sensibles accessibles par les agents IA.

    Si la requête vient d'un AgentToken :
    - Vérifie que l'agent a la permission (double passe RBAC)
    - Si human_in_the_loop_required=True → retourne 202 + confirmation_token
    - Si le risk_score de l'agent > max_risk_score → refuse directement

    Si la requête vient d'un humain (JWT standard) → passe normalement.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            view_instance, request, view_args = _extract_request(*args)

            # Requête d'un agent IA
            if hasattr(request, "agent_token") and request.agent_token:
                from tenxyte.services.agent_service import AgentTokenService

                service = AgentTokenService()

                # Vérification de permission (double passe)
                if permission_code:
                    if not service.validate_permission(request.agent_token, permission_code):
                        return _get_permission_denied_response(
                            f"Agent insufficient permissions: {permission_code}", "AGENT_PERMISSION_DENIED"
                        )

                from tenxyte.conf import auth_settings

                is_hitl_required = human_in_the_loop_required
                if permission_code and permission_code in auth_settings.AIRS_CONFIRMATION_REQUIRED:
                    is_hitl_required = True

                # Human-in-the-loop obligatoire
                if is_hitl_required:
                    # Check if action is already confirmed
                    confirmation_header = request.META.get("HTTP_X_ACTION_CONFIRMATION")
                    if confirmation_header:
                        from tenxyte.models.agent import AgentPendingAction

                        action = AgentPendingAction.objects.filter(
                            confirmation_token=confirmation_header,
                            agent_token=request.agent_token,
                            confirmed_at__isnull=False,
                        ).first()
                        if action:
                            return _call_view(view_func, view_instance, request, view_args, kwargs)

                    # extract payload safely
                    payload = {}
                    if request.method in ["POST", "PUT", "PATCH"]:
                        try:
                            import json

                            if request.body:
                                payload = json.loads(request.body)
                        except Exception:
                            pass

                    pending = service.create_pending_action(
                        agent_token=request.agent_token,
                        permission=permission_code or "unknown",
                        endpoint=request.path,
                        payload=payload,
                    )
                    return JsonResponse(
                        {
                            "status": "pending_confirmation",
                            "message": "This action requires human approval.",
                            "confirmation_token": pending.confirmation_token,
                            "expires_at": pending.expires_at.isoformat(),
                        },
                        status=202,
                    )

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper

    return decorator
