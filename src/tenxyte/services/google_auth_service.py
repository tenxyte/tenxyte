import logging
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone
import requests

logger = logging.getLogger(__name__)

from ..models import get_user_model, get_application_model, RefreshToken
from .jwt_service import JWTService

User = get_user_model()
Application = get_application_model()


class GoogleAuthService:
    """
    Service d'authentification Google OAuth
    """

    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def __init__(self):
        self.jwt_service = JWTService()
        self.client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Vérifie un ID token Google et retourne les informations utilisateur
        """
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                self.client_id
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return None

            return {
                'google_id': idinfo['sub'],
                'email': idinfo.get('email'),
                'email_verified': idinfo.get('email_verified', False),
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture', ''),
            }
        except Exception as e:
            logger.error(f"Google token verification error: {e}")
            return None

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Échange un code d'autorisation contre des tokens
        """
        try:
            response = requests.post(self.GOOGLE_TOKEN_URL, data={
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            })

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Google token exchange error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations utilisateur depuis Google
        """
        try:
            response = requests.get(
                self.GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'google_id': data['sub'],
                    'email': data.get('email'),
                    'email_verified': data.get('email_verified', False),
                    'first_name': data.get('given_name', ''),
                    'last_name': data.get('family_name', ''),
                    'picture': data.get('picture', ''),
                }
            return None
        except Exception as e:
            logger.error(f"Google user info error: {e}")
            return None

    def authenticate_with_google(
        self,
        google_data: Dict[str, Any],
        application: Application,
        ip_address: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentifie ou crée un utilisateur via Google
        """
        google_id = google_data.get('google_id')
        email = google_data.get('email')

        if not google_id:
            return False, None, 'Invalid Google data'

        # Chercher un utilisateur existant par google_id
        user = User.objects.filter(google_id=google_id).first()

        if not user and email:
            # Chercher par email
            user = User.objects.filter(email__iexact=email).first()
            if user:
                # Lier le compte Google à l'utilisateur existant
                user.google_id = google_id
                if google_data.get('email_verified'):
                    user.is_email_verified = True
                user.save()

        if not user:
            # Créer un nouvel utilisateur
            user = User.objects.create(
                email=email.lower() if email else None,
                google_id=google_id,
                first_name=google_data.get('first_name', ''),
                last_name=google_data.get('last_name', ''),
                is_email_verified=google_data.get('email_verified', False),
                password=''  # Pas de mot de passe pour les comptes Google
            )
            # Assigner le rôle par défaut (user)
            user.assign_default_role()

        if not user.is_active:
            return False, None, 'Account is inactive'

        if user.is_account_locked():
            return False, None, 'Account is locked'

        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Générer les tokens
        refresh_token = RefreshToken.generate(
            user=user,
            application=application,
            ip_address=ip_address
        )

        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token.token
        )

        return True, {
            **tokens,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone': user.full_phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
            }
        }, ''
