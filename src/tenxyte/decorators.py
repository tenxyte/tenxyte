from functools import wraps
from django.http import JsonResponse
from .services.jwt_service import JWTService
from .models import get_user_model, get_application_model
from .conf import auth_settings

User = get_user_model()
Application = get_application_model()


def _is_request(obj):
    """Vérifie si un objet est un objet request (Django ou DRF)."""
    return hasattr(obj, 'META') and hasattr(obj, 'method')


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
            return JsonResponse({
                'error': 'Invalid request object',
                'code': 'INVALID_REQUEST'
            }, status=400)

        # Skip JWT validation if disabled (DANGEROUS - for testing only)
        if not auth_settings.JWT_AUTH_ENABLED:
            request.user = None
            request.jwt_payload = None
            return _call_view(view_func, view_instance, request, view_args, kwargs)

        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Authorization header required',
                'code': 'AUTH_REQUIRED'
            }, status=401)

        token = auth_header[7:]
        jwt_service = JWTService()
        payload = jwt_service.decode_token(token)

        if not payload:
            return JsonResponse({
                'error': 'Invalid or expired token',
                'code': 'TOKEN_INVALID'
            }, status=401)

        # Vérifier que l'application du token correspond
        if hasattr(request, 'application') and request.application:
            if str(request.application.id) != payload.get('app_id'):
                return JsonResponse({
                    'error': 'Token does not match application',
                    'code': 'TOKEN_APP_MISMATCH'
                }, status=401)

        # Récupérer l'utilisateur
        try:
            user = User.objects.get(id=payload.get('user_id'))
            if not user.is_active:
                return JsonResponse({
                    'error': 'User account is inactive',
                    'code': 'USER_INACTIVE'
                }, status=401)

            if auth_settings.ACCOUNT_LOCKOUT_ENABLED and user.is_account_locked():
                return JsonResponse({
                    'error': 'User account is locked',
                    'code': 'USER_LOCKED'
                }, status=401)

            request.user = user
            request.jwt_payload = payload

        except User.DoesNotExist:
            return JsonResponse({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }, status=401)

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
            return JsonResponse({
                'error': 'Email verification required',
                'code': 'EMAIL_NOT_VERIFIED'
            }, status=403)

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
            return JsonResponse({
                'error': 'Phone verification required',
                'code': 'PHONE_NOT_VERIFIED'
            }, status=403)

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
            if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
                identifier = f"rate_limit:{view_func.__name__}:user:{request.user.id}"
            else:
                ip = get_client_ip(request)
                identifier = f"rate_limit:{view_func.__name__}:ip:{ip}"

            # Récupérer le compteur actuel
            current = cache.get(identifier, 0)

            if current >= max_requests:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMITED',
                    'retry_after': window_seconds
                }, status=429)

            # Incrémenter le compteur
            cache.set(identifier, current + 1, window_seconds)

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper
    return decorator


def get_client_ip(request) -> str:
    """
    Récupère l'adresse IP du client.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


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
                return JsonResponse({
                    'error': f'Role required: {role_code}',
                    'code': 'ROLE_REQUIRED'
                }, status=403)

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
                return JsonResponse({
                    'error': f'One of these roles required: {", ".join(role_codes)}',
                    'code': 'ROLE_REQUIRED'
                }, status=403)

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
                return JsonResponse({
                    'error': f'All these roles required: {", ".join(role_codes)}',
                    'code': 'ROLES_REQUIRED'
                }, status=403)

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
                return JsonResponse({
                    'error': f'Permission required: {permission_code}',
                    'code': 'PERMISSION_REQUIRED'
                }, status=403)

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
                return JsonResponse({
                    'error': f'One of these permissions required: {", ".join(permission_codes)}',
                    'code': 'PERMISSION_REQUIRED'
                }, status=403)

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
                return JsonResponse({
                    'error': f'All these permissions required: {", ".join(permission_codes)}',
                    'code': 'PERMISSIONS_REQUIRED'
                }, status=403)

            return _call_view(view_func, view_instance, request, view_args, kwargs)

        return wrapper
    return decorator
