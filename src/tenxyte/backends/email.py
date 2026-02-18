"""
Backends Email pour l'envoi d'emails.

Tenxyte utilise le système de mail Django par défaut.
L'utilisateur configure son backend Django comme d'habitude:

    # settings.py
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'your-email@gmail.com'
    EMAIL_HOST_PASSWORD = 'your-app-password'
    DEFAULT_FROM_EMAIL = 'noreply@yourapp.com'

Backends tiers supportés via django-anymail:
    pip install django-anymail[sendgrid]
    pip install django-anymail[mailgun]
    pip install django-anymail[amazon-ses]
    pip install django-anymail[postmark]
    pip install django-anymail[mailjet]
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseEmailBackend(ABC):
    """
    Backend abstrait pour l'envoi d'emails.
    """

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envoie un email.

        Args:
            to_email: Adresse email du destinataire
            subject: Sujet de l'email
            message: Contenu texte du message
            html_message: Contenu HTML du message (optionnel)
            context: Variables de contexte pour les templates (optionnel)

        Returns:
            True si l'envoi a réussi
        """
        pass


class ConsoleBackend(BaseEmailBackend):
    """
    Backend console - affiche les emails dans les logs (pour développement).
    """

    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Affiche l'email dans la console."""
        logger.info(f"[Email Console] To: {to_email}")
        logger.info(f"[Email Console] Subject: {subject}")
        logger.info(f"[Email Console] Message: {message}")
        if html_message:
            logger.info(f"[Email Console] HTML: {html_message[:200]}...")
        return True


class DjangoBackend(BaseEmailBackend):
    """
    Backend Django - utilise le système de mail Django natif.

    C'est le backend recommandé. Il utilise EMAIL_BACKEND de Django,
    ce qui permet d'utiliser n'importe quel backend compatible:
    - SMTP natif
    - SendGrid (via django-anymail)
    - Mailgun (via django-anymail)
    - Amazon SES (via django-anymail)
    - Postmark (via django-anymail)
    - Et bien d'autres...
    """

    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Envoie l'email via Django mail."""
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings
            from django.template import Template, Context
            from django.template.loader import render_to_string

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

            # Render templates if context provided
            if context:
                # Try to render message as template
                try:
                    template = Template(message)
                    message = template.render(Context(context))
                except Exception:
                    pass  # Keep original message if template fails

                if html_message:
                    try:
                        template = Template(html_message)
                        html_message = template.render(Context(context))
                    except Exception:
                        pass

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=[to_email]
            )

            # Attach HTML version if provided
            if html_message:
                email.attach_alternative(html_message, "text/html")

            email.send(fail_silently=False)

            logger.info(f"[Django Email] Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"[Django Email] Error: {e}")
            return False


class TemplateEmailBackend(DjangoBackend):
    """
    Backend avec support des templates Django.
    Permet d'utiliser des fichiers de template pour les emails.
    """

    def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envoie un email en utilisant un template Django.

        Args:
            to_email: Adresse email du destinataire
            subject: Sujet de l'email
            template_name: Nom du template (ex: 'tenxyte/emails/otp.html')
            context: Variables de contexte pour le template

        Returns:
            True si l'envoi a réussi
        """
        try:
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags

            context = context or {}
            html_message = render_to_string(template_name, context)
            text_message = strip_tags(html_message)

            return self.send_email(
                to_email=to_email,
                subject=subject,
                message=text_message,
                html_message=html_message
            )

        except Exception as e:
            logger.error(f"[Template Email] Error: {e}")
            return False


class SendGridBackend(BaseEmailBackend):
    """
    Backend SendGrid - envoie les emails via l'API SendGrid.

    Requiert:
    - pip install sendgrid
    - Settings: SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
    """

    def __init__(self):
        from ..conf import auth_settings

        self.api_key = auth_settings.SENDGRID_API_KEY
        self.from_email = auth_settings.SENDGRID_FROM_EMAIL

        if not self.api_key:
            logger.warning(
                "[SendGrid] API key not configured. "
                "Set SENDGRID_API_KEY in settings."
            )

    def send_email(self, to_email: str, subject: str, message: str,
                   html_message: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Envoie l'email via SendGrid."""
        if not self.api_key:
            logger.error("[SendGrid] Missing API key")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            mail = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=message,
                html_content=html_message or None
            )

            sg = SendGridAPIClient(self.api_key)
            response = sg.send(mail)

            logger.info(f"[SendGrid] Email sent to {to_email} | Status: {response.status_code}")
            return response.status_code in (200, 201, 202)

        except ImportError:
            logger.error("[SendGrid] Library not installed. Run: pip install tenxyte[sendgrid]")
            return False
        except Exception as e:
            logger.error(f"[SendGrid] Error: {e}")
            return False


def get_email_backend() -> BaseEmailBackend:
    """
    Factory pour obtenir le backend email configuré.

    Returns:
        Instance du backend email
    """
    from django.utils.module_loading import import_string
    from ..conf import auth_settings

    backend_path = auth_settings.EMAIL_BACKEND
    backend_class = import_string(backend_path)
    return backend_class()
