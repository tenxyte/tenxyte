"""
Service Magic Link pour l'authentification sans mot de passe.
"""
import logging
from typing import Optional, Tuple, Dict, Any

from ..models import get_user_model, get_application_model
from ..models.magic_link import MagicLinkToken
from ..conf import auth_settings
from .auth_service import AuthService
from .email_service import EmailService

User = get_user_model()
Application = get_application_model()

logger = logging.getLogger(__name__)


class MagicLinkService:
    """
    Gère la génération, l'envoi et la validation des magic links.
    """

    def __init__(self):
        self.auth_service = AuthService()
        self.email_service = EmailService()

    def request_magic_link(
        self,
        email: str,
        application: Optional[Application] = None,
        ip_address: str = None,
        device_info: str = '',
        app_name: str = 'Tenxyte',
        validation_url: str = None
    ) -> Tuple[bool, str]:
        """
        Génère un magic link et l'envoie par email.

        Returns:
            (success: bool, error: str)
        """
        if not auth_settings.MAGIC_LINK_ENABLED:
            return False, 'Magic link authentication is not enabled'

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe ou non (sécurité)
            logger.info(f"Magic link requested for unknown email: {email}")
            return True, ''

        # Invalider les anciens tokens non utilisés de cet utilisateur
        MagicLinkToken.objects.filter(
            user=user,
            is_used=False,
            application=application
        ).update(is_used=True)

        # Générer le nouveau token
        expiry_minutes = auth_settings.MAGIC_LINK_EXPIRY_MINUTES
        token_instance, raw_token = MagicLinkToken.generate(
            user=user,
            application=application,
            ip_address=ip_address,
            user_agent=device_info,
            expiry_minutes=expiry_minutes
        )

        # Envoyer l'email
        sent = self.email_service.send_magic_link_email(
            to_email=user.email,
            token=raw_token,
            first_name=getattr(user, 'first_name', ''),
            expiry_minutes=expiry_minutes,
            app_name=app_name,
            validation_url=validation_url
        )

        if not sent:
            logger.error(f"Failed to send magic link email to {user.email}")
            return False, 'Failed to send magic link email'

        return True, ''

    def verify_magic_link(
        self,
        token: str,
        application: Optional[Application] = None,
        ip_address: str = None,
        device_info: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Valide un magic link et retourne des tokens JWT si valide.

        Returns:
            (success: bool, data: dict | None, error: str)
        """
        if not auth_settings.MAGIC_LINK_ENABLED:
            return False, None, 'Magic link authentication is not enabled'

        token_instance = MagicLinkToken.get_valid(token, ip_address=ip_address, user_agent=device_info)
        if not token_instance:
            return False, None, 'Invalid or expired magic link. Note: Magic links must be opened on the same device that requested them.'

        user = token_instance.user

        if not user.is_active:
            return False, None, 'Account is disabled'

        if user.is_account_locked():
            return False, None, 'Account is locked'

        # Consommer le token (single-use)
        token_instance.consume()

        # Générer les tokens JWT
        jwt_data = self.auth_service.generate_tokens_for_user(
            user=user,
            application=application or token_instance.application,
            ip_address=ip_address,
            device_info=device_info
        )

        # Sérialiser les données de l'utilisateur
        from ..serializers.auth_serializers import UserSerializer
        user_serializer = UserSerializer(user)
        user_data = user_serializer.data

        # Combiner les tokens JWT et les données utilisateur
        response_data = {
            **jwt_data,  # access, refresh, etc.
            'user': user_data
        }

        return True, response_data, ''
