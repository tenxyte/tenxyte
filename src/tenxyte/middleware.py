from django.http import JsonResponse
from .models import Application
from .services.jwt_service import JWTService
from .conf import auth_settings


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
            return self.get_response(request)

        # Vérifier si le chemin est exempté (prefix match)
        for path in exempt_paths:
            if request.path.startswith(path):
                return self.get_response(request)

        # Récupérer les credentials de l'application
        access_key = request.headers.get('X-Access-Key')
        access_secret = request.headers.get('X-Access-Secret')

        if not access_key or not access_secret:
            return JsonResponse({
                'error': 'Missing application credentials',
                'code': 'APP_AUTH_REQUIRED'
            }, status=401)

        try:
            application = Application.objects.get(access_key=access_key, is_active=True)
            if not application.verify_secret(access_secret):
                return JsonResponse({
                    'error': 'Invalid application credentials',
                    'code': 'APP_AUTH_INVALID'
                }, status=401)

            # Attacher l'application à la requête
            request.application = application

        except Application.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid application credentials',
                'code': 'APP_AUTH_INVALID'
            }, status=401)

        return self.get_response(request)


class JWTAuthMiddleware:
    """
    Middleware pour valider le JWT (deuxième couche - optionnel)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_service = JWTService()

    def __call__(self, request):
        # Récupérer le token d'autorisation
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = self.jwt_service.decode_token(token)

            if payload:
                request.jwt_payload = payload
                request.user_id = payload.get('user_id')
            else:
                request.jwt_payload = None
                request.user_id = None
        else:
            request.jwt_payload = None
            request.user_id = None

        return self.get_response(request)
