"""
Classes d'authentification DRF pour JWT.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .services.jwt_service import JWTService
from .models import get_user_model

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    """
    Authentification JWT pour Django REST Framework.

    Lit le token du header Authorization et retourne l'utilisateur.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None  # Pas de token, passer au prochain authenticator

        token = auth_header[7:]
        jwt_service = JWTService()
        payload = jwt_service.decode_token(token)

        if not payload:
            raise AuthenticationFailed('Token invalide ou expiré')

        # Vérifier l'application si présente
        if hasattr(request, 'application') and request.application:
            if str(request.application.id) != payload.get('app_id'):
                raise AuthenticationFailed('Token ne correspond pas à l\'application')

        # Récupérer l'utilisateur
        try:
            user = User.objects.get(id=payload.get('user_id'))
        except User.DoesNotExist:
            raise AuthenticationFailed('Utilisateur non trouvé')

        if not user.is_active:
            raise AuthenticationFailed('Compte utilisateur inactif')

        if user.is_account_locked():
            raise AuthenticationFailed('Compte utilisateur verrouillé')

        # Stocker le payload pour usage ultérieur
        request.jwt_payload = payload

        return (user, token)

    def authenticate_header(self, request):
        return 'Bearer'


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Extension OpenAPI pour documenter l'authentification JWT.
    """
    target_class = 'tenxyte.authentication.JWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
