"""
Test helpers for Django integration tests.

Provides utility functions for creating test tokens, users, etc.
"""


class LegacyJWTServiceWrapper:
    """
    Wrapper around core JWTService to provide legacy-compatible API for tests.
    
    This allows existing tests to work without modification while using the new core service.
    """
    
    def __init__(self):
        from tenxyte.core.jwt_service import JWTService
        from tenxyte.adapters.django import get_django_settings
        from tenxyte.adapters.django.cache_service import DjangoCacheService
        
        self._service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )
    
    def generate_token_pair(self, user_id, application_id, **kwargs):
        """Generate token pair - legacy compatible, returns dict."""
        token_pair = self._service.generate_token_pair(
            user_id=str(user_id),
            application_id=str(application_id),
            **kwargs
        )
        # Return dict for legacy compatibility
        return {
            'access_token': token_pair.access_token,
            'refresh_token': token_pair.refresh_token,
        }
    
    def generate_access_token(self, user_id, application_id, **kwargs):
        """Generate access token only - legacy compatible."""
        # Generate a dummy refresh token string if not provided
        if 'refresh_token_str' not in kwargs:
            import secrets
            kwargs['refresh_token_str'] = secrets.token_urlsafe(32)
        
        token_pair = self._service.generate_token_pair(
            user_id=str(user_id),
            application_id=str(application_id),
            **kwargs
        )
        return token_pair.access_token
    
    def decode_token(self, token):
        """Decode token - returns dict for legacy compatibility."""
        decoded = self._service.decode_token(token)
        if decoded and decoded.is_valid:
            # Convert DecodedToken to dict for legacy tests
            return {
                'user_id': decoded.user_id,
                'app_id': decoded.app_id,
                'jti': decoded.jti,
                'exp': decoded.exp,
                'type': decoded.type,
            }
        return None
    
    def is_token_valid(self, token):
        """Check if token is valid - legacy compatible."""
        decoded = self._service.decode_token(token)
        return decoded and decoded.is_valid
    
    def get_user_id_from_token(self, token):
        """Extract user_id from token - legacy compatible."""
        decoded = self.decode_token(token)
        return decoded['user_id'] if decoded else None
    
    def get_application_id_from_token(self, token):
        """Extract application_id from token - legacy compatible."""
        decoded = self.decode_token(token)
        return decoded['app_id'] if decoded else None
    
    def blacklist_token(self, token, **kwargs):
        """Blacklist token - legacy compatible."""
        # Convert 'user' to 'user_id' if present
        if 'user' in kwargs:
            user = kwargs.pop('user')
            kwargs['user_id'] = str(user.id) if user else None
        return self._service.blacklist_token(token, **kwargs)
    
    @property
    def secret_key(self):
        """Get secret key - legacy compatible."""
        return self._service.settings.jwt_secret
    
    @property
    def algorithm(self):
        """Get algorithm - legacy compatible."""
        return self._service.settings.jwt_algorithm
    
    @property
    def is_asymmetric(self):
        """Check if using asymmetric keys - legacy compatible."""
        return self._service.is_asymmetric


def get_jwt_service():
    """
    Get a legacy-compatible JWTService instance for tests.
    
    Returns:
        LegacyJWTServiceWrapper: Wrapper providing legacy API
    """
    return LegacyJWTServiceWrapper()


def JWTService():
    """Alias for get_jwt_service() to match old import style."""
    return get_jwt_service()


def create_jwt_token(user, app):
    """
    Create a JWT token pair for testing.
    
    Args:
        user: User instance
        app: Application instance
        
    Returns:
        dict: {'access_token': str, 'refresh_token': str}
    """
    import secrets
    jwt_service = get_jwt_service()
    return jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str=secrets.token_urlsafe(32),
    )


def authenticate_user(email, password, app, app_secret):
    """
    Authentifie un utilisateur via l'API REST et retourne les tokens.
    
    Remplace l'ancien AuthService.authenticate_by_email().
    
    Args:
        email: Email de l'utilisateur
        password: Mot de passe
        app: Instance Application
        app_secret: Secret de l'application
        
    Returns:
        dict: {
            'success': bool,
            'data': {'access_token': str, 'refresh_token': str, 'user': dict} ou None,
            'error': str ou None
        }
    """
    from rest_framework.test import APIClient
    import json
    
    client = APIClient()
    # Ajouter les credentials d'application dans les headers pour le middleware
    client.credentials(
        HTTP_X_APPLICATION_ID=str(app.id),
        HTTP_X_APPLICATION_SECRET=app_secret
    )
    
    response = client.post('/api/v1/auth/login/', {
        'email': email,
        'password': password
    }, format='json')
    
    # Parse response content
    if hasattr(response, 'data'):
        # DRF Response
        data = response.data
    else:
        # Django JsonResponse
        data = json.loads(response.content.decode('utf-8'))
    
    if response.status_code == 200:
        return {
            'success': True,
            'data': {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'user': data.get('user')
            },
            'error': None
        }
    else:
        return {
            'success': False,
            'data': None,
            'error': data.get('error', 'Authentication failed')
        }
