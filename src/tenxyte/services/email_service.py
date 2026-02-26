"""
Service d'envoi d'emails pour Tenxyte.

Utilise le système de mail Django par défaut.
L'utilisateur configure son backend dans settings.py:

    # SMTP standard
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'your-email@gmail.com'
    EMAIL_HOST_PASSWORD = 'your-app-password'
    DEFAULT_FROM_EMAIL = 'noreply@yourapp.com'

    # Ou avec django-anymail pour SendGrid, Mailgun, SES, etc.
    EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
    ANYMAIL = {'SENDGRID_API_KEY': 'your-api-key'}
"""

import logging
from typing import Optional, Dict, Any

from django.conf import settings

from ..backends.email import get_email_backend

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service de haut niveau pour l'envoi d'emails.

    Fournit des méthodes pratiques pour les cas d'usage courants:
    - Envoi de code OTP
    - Email de bienvenue
    - Réinitialisation de mot de passe
    - Notifications de sécurité
    """

    def __init__(self):
        self.backend = get_email_backend()

    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envoie un email simple.

        Args:
            to_email: Adresse email du destinataire
            subject: Sujet de l'email
            message: Contenu texte
            html_message: Contenu HTML (optionnel)
            context: Variables pour le template (optionnel)

        Returns:
            True si l'envoi a réussi
        """
        return self.backend.send_email(
            to_email=to_email,
            subject=subject,
            message=message,
            html_message=html_message,
            context=context
        )

    def send_otp_email(
        self,
        to_email: str,
        code: str,
        otp_type: str = 'verification',
        validity_minutes: int = 15,
        app_name: str = 'Tenxyte'
    ) -> bool:
        """
        Envoie un code OTP par email.

        Args:
            to_email: Adresse email du destinataire
            code: Le code OTP
            otp_type: Type d'OTP (verification, password_reset, login)
            validity_minutes: Durée de validité en minutes
            app_name: Nom de l'application

        Returns:
            True si l'envoi a réussi
        """
        subjects = {
            'verification': f'{app_name} - Code de vérification',
            'email_verification': f'{app_name} - Vérifiez votre email',
            'password_reset': f'{app_name} - Réinitialisation du mot de passe',
            'login': f'{app_name} - Code de connexion',
        }

        subject = subjects.get(otp_type, f'{app_name} - Votre code')

        message = f"""
Bonjour,

Votre code de vérification est: {code}

Ce code est valide pendant {validity_minutes} minutes.

Si vous n'avez pas demandé ce code, ignorez cet email.

Cordialement,
L'équipe {app_name}
"""

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Votre code de vérification</h2>
        <p>Bonjour,</p>
        <p>Voici votre code de vérification:</p>
        <div style="background: #f8f9fa; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #2c3e50;">{code}</span>
        </div>
        <p style="color: #666; font-size: 14px;">
            Ce code est valide pendant <strong>{validity_minutes} minutes</strong>.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            Si vous n'avez pas demandé ce code, ignorez cet email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            Cordialement,<br>
            L'équipe {app_name}
        </p>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            message=message.strip(),
            html_message=html_message
        )

    def send_welcome_email(
        self,
        to_email: str,
        first_name: str = '',
        app_name: str = 'Tenxyte'
    ) -> bool:
        """
        Envoie un email de bienvenue.

        Args:
            to_email: Adresse email du destinataire
            first_name: Prénom de l'utilisateur
            app_name: Nom de l'application

        Returns:
            True si l'envoi a réussi
        """
        greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

        subject = f"Bienvenue sur {app_name}!"

        message = f"""
{greeting},

Bienvenue sur {app_name}!

Votre compte a été créé avec succès.

Cordialement,
L'équipe {app_name}
"""

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Bienvenue sur {app_name}!</h2>
        <p>{greeting},</p>
        <p>Votre compte a été créé avec succès.</p>
        <p>Vous pouvez maintenant vous connecter et profiter de tous nos services.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            Cordialement,<br>
            L'équipe {app_name}
        </p>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            message=message.strip(),
            html_message=html_message
        )

    def send_password_changed_email(
        self,
        to_email: str,
        first_name: str = '',
        app_name: str = 'Tenxyte'
    ) -> bool:
        """
        Envoie une notification de changement de mot de passe.

        Args:
            to_email: Adresse email du destinataire
            first_name: Prénom de l'utilisateur
            app_name: Nom de l'application

        Returns:
            True si l'envoi a réussi
        """
        greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

        subject = f"{app_name} - Mot de passe modifié"

        message = f"""
{greeting},

Votre mot de passe a été modifié avec succès.

Si vous n'êtes pas à l'origine de cette modification, contactez-nous immédiatement.

Cordialement,
L'équipe {app_name}
"""

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Mot de passe modifié</h2>
        <p>{greeting},</p>
        <p>Votre mot de passe a été modifié avec succès.</p>
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; color: #856404;">
                <strong>Important:</strong> Si vous n'êtes pas à l'origine de cette modification,
                contactez-nous immédiatement.
            </p>
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            Cordialement,<br>
            L'équipe {app_name}
        </p>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            message=message.strip(),
            html_message=html_message
        )

    def send_security_alert_email(
        self,
        to_email: str,
        alert_type: str,
        details: Dict[str, Any] = None,
        first_name: str = '',
        app_name: str = 'Tenxyte'
    ) -> bool:
        """
        Envoie une alerte de sécurité.

        Args:
            to_email: Adresse email du destinataire
            alert_type: Type d'alerte (new_login, session_revoked, account_locked)
            details: Détails supplémentaires (ip, device, etc.)
            first_name: Prénom de l'utilisateur
            app_name: Nom de l'application

        Returns:
            True si l'envoi a réussi
        """
        greeting = f"Bonjour {first_name}" if first_name else "Bonjour"
        details = details or {}

        alerts = {
            'new_login': {
                'subject': f"{app_name} - Nouvelle connexion détectée",
                'message': "Une nouvelle connexion a été détectée sur votre compte."
            },
            'session_revoked': {
                'subject': f"{app_name} - Session révoquée",
                'message': "Une session a été révoquée sur votre compte."
            },
            'account_locked': {
                'subject': f"{app_name} - Compte verrouillé",
                'message': "Votre compte a été temporairement verrouillé suite à plusieurs tentatives de connexion échouées."
            },
            'device_limit': {
                'subject': f"{app_name} - Limite d'appareils atteinte",
                'message': "Vous avez atteint la limite d'appareils autorisés."
            }
        }

        alert = alerts.get(alert_type, {
            'subject': f"{app_name} - Alerte de sécurité",
            'message': "Une activité inhabituelle a été détectée sur votre compte."
        })

        ip_info = f"\nAdresse IP: {details.get('ip', 'Inconnue')}" if 'ip' in details else ""
        device_info = f"\nAppareil: {details.get('device', 'Inconnu')}" if 'device' in details else ""

        message = f"""
{greeting},

{alert['message']}
{ip_info}{device_info}

Si cette activité ne vous est pas familière, nous vous recommandons de changer votre mot de passe.

Cordialement,
L'équipe {app_name}
"""

        return self.send_email(
            to_email=to_email,
            subject=alert['subject'],
            message=message.strip()
        )
    
    def send_magic_link_email(
        self,
        to_email: str,
        token: str,
        first_name: str = '',
        expiry_minutes: int = 15,
        app_name: str = 'Tenxyte',
        validation_url: str = None
    ) -> bool:
        """
        Envoie un magic link par email.

        Args:
            to_email: Adresse email du destinataire
            token: Le token brut (non hashé) à inclure dans le lien
            first_name: Prénom de l'utilisateur
            expiry_minutes: Durée de validité en minutes
            app_name: Nom de l'application

        Returns:
            True si l'envoi a réussi
        """
        from django.conf import settings as django_settings

        from ..conf import auth_settings
        
        greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

        verify_url = f"{validation_url}?token={token}"

        subject = f"{app_name} - Votre lien de connexion"

        message = f"""
{greeting},

Cliquez sur le lien ci-dessous pour vous connecter à {app_name}:

{verify_url}

Ce lien est valide pendant {expiry_minutes} minutes et ne peut être utilisé qu'une seule fois.

Si vous n'avez pas demandé ce lien, ignorez cet email.

Cordialement,
L'équipe {app_name}
"""

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Votre lien de connexion</h2>
        <p>{greeting},</p>
        <p>Cliquez sur le bouton ci-dessous pour vous connecter à <strong>{app_name}</strong>:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}"
               style="background: #3498db; color: white; padding: 14px 28px; text-decoration: none;
                      border-radius: 6px; font-size: 16px; font-weight: bold; display: inline-block;">
                Se connecter
            </a>
        </div>
        <p style="color: #666; font-size: 14px;">
            Ou copiez ce lien dans votre navigateur:<br>
            <a href="{verify_url}" style="color: #3498db; word-break: break-all;">{verify_url}</a>
        </p>
        <p style="color: #666; font-size: 14px;">
            Ce lien est valide pendant <strong>{expiry_minutes} minutes</strong>
            et ne peut être utilisé qu'une seule fois.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            Si vous n'avez pas demandé ce lien, ignorez cet email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            Cordialement,<br>
            L'équipe {app_name}
        </p>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            message=message.strip(),
            html_message=html_message
        )

    def send_account_deletion_confirmation(self, deletion_request) -> bool:
        """
        Envoyer l'email de confirmation de demande de suppression.
        
        Args:
            deletion_request: L'objet AccountDeletionRequest
            
        Returns:
            True si envoyé avec succès
        """
        from django.urls import reverse
        from django.contrib.sites.shortcuts import get_current_site
        
        from ..conf import auth_settings
        
        try:
            site = get_current_site(None)
            domain = f"https://{site.domain}" if site.domain else "https://yourapp.com"
            base_url = auth_settings.BASE_URL
            api_prefix = auth_settings.API_PREFIX
            
            confirmation_url = f"{base_url}{api_prefix}/auth/confirm-account-deletion/"
            confirmation_url_with_token = f"{confirmation_url}?token={deletion_request.confirmation_token}"
            
            context = {
                'user': deletion_request.user,
                'confirmation_url': confirmation_url_with_token,
                'grace_period_days': getattr(settings, 'TENXYTE_ACCOUNT_DELETION_GRACE_PERIOD_DAYS', 30),
                'ip_address': deletion_request.ip_address,
                'site_name': getattr(settings, 'SITE_NAME', 'Tenxyte'),
                'requested_at': deletion_request.requested_at,
                'reason': deletion_request.reason
            }
            
            subject = f"Action requise : Confirmez votre demande de suppression de compte"
            
            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject=subject,
                template_name='emails/account_deletion_confirmation.html',
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error sending account deletion confirmation: {e}")
            return False
    
    def send_account_deletion_confirmed(self, deletion_request) -> bool:
        """
        Envoyer l'email de confirmation de période de grâce.
        
        Args:
            deletion_request: L'objet AccountDeletionRequest
            
        Returns:
            True si envoyé avec succès
        """
        from django.urls import reverse
        from django.contrib.sites.shortcuts import get_current_site
        from django.utils import timezone
        
        try:
            site = get_current_site(None)
            domain = f"https://{site.domain}" if site.domain else "https://yourapp.com"
            
            from ..conf import auth_settings
            base_url = auth_settings.BASE_URL
            api_prefix = auth_settings.API_PREFIX
            
            # URL d'annulation (à implémenter dans les vues)
            cancel_url = f"{base_url}{api_prefix}/auth/cancel-account-deletion/"
            
            days_remaining = 0
            if deletion_request.grace_period_ends_at:
                days_remaining = (deletion_request.grace_period_ends_at - timezone.now()).days
            
            context = {
                'user': deletion_request.user,
                'cancel_url': cancel_url,
                'days_remaining': max(0, days_remaining),
                'grace_period_ends_at': deletion_request.grace_period_ends_at,
                'requested_at': deletion_request.requested_at,
                'reason': deletion_request.reason,
                'ip_address': deletion_request.ip_address,
                'site_name': getattr(settings, 'SITE_NAME', 'Tenxyte'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com')
            }
            
            subject = f"Votre demande de suppression de compte est confirmée"
            
            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject=subject,
                template_name='emails/account_deletion_confirmed.html',
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error sending account deletion confirmed: {e}")
            return False
    
    def send_account_deletion_completed(self, deletion_request) -> bool:
        """
        Envoyer l'email de notification de suppression effectuée.
        
        Args:
            deletion_request: L'objet AccountDeletionRequest
            
        Returns:
            True si envoyé avec succès
        """
        try:
            context = {
                'user_email': deletion_request.user.email,
                'requested_at': deletion_request.requested_at,
                'confirmed_at': deletion_request.confirmed_at,
                'completed_at': deletion_request.completed_at,
                'processed_by': str(deletion_request.processed_by) if deletion_request.processed_by else 'System',
                'reason': deletion_request.reason,
                'anonymization_token': deletion_request.user.anonymization_token,
                'site_name': getattr(settings, 'SITE_NAME', 'Tenxyte'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com')
            }
            
            subject = f"Votre compte a été supprimé"
            
            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject=subject,
                template_name='emails/account_deletion_completed.html',
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error sending account deletion completed: {e}")
            return False
    
    def send_deletion_request_rejected(self, deletion_request) -> bool:
        """
        Envoyer l'email de rejet de demande de suppression.
        
        Args:
            deletion_request: L'objet AccountDeletionRequest
            
        Returns:
            True si envoyé avec succès
        """
        from django.contrib.sites.shortcuts import get_current_site
        
        try:
            site = get_current_site(None)
            base_url = f"https://{site.domain}" if site.domain else "https://yourapp.com"
            login_url = f"{base_url}/login/"
            
            context = {
                'user': deletion_request.user,
                'login_url': login_url,
                'requested_at': deletion_request.requested_at,
                'reason': deletion_request.reason,
                'admin_notes': deletion_request.admin_notes,
                'site_name': getattr(settings, 'SITE_NAME', 'Tenxyte'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com')
            }
            
            subject = f"Votre demande de suppression de compte a été rejetée"
            
            return self._send_template_email(
                to_email=deletion_request.user.email,
                subject=subject,
                template_name='emails/account_deletion_rejected.html',
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error sending deletion request rejected: {e}")
            return False
    
    def _send_template_email(self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]) -> bool:
        """
        Envoyer un email à partir d'un template HTML.
        
        Args:
            to_email: Email du destinataire
            subject: Sujet de l'email
            template_name: Nom du template
            context: Contexte pour le template
            
        Returns:
            True si envoyé avec succès
        """
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        
        try:
            # Rendre le template HTML
            html_content = render_to_string(template_name, context)
            
            # Créer l'email
            email = EmailMultiAlternatives(
                subject=subject,
                body=self._generate_text_alternative(html_content),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tenxyte.com'),
                to=[to_email]
            )
            
            # Ajouter la version HTML
            email.attach_alternative(html_content, "text/html")
            
            # Envoyer
            email.send()
            
            logger.info(f"Template email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending template email to {to_email}: {e}")
            return False
    
    def _generate_text_alternative(self, html_content: str) -> str:
        """
        Générer une version texte alternative à partir du HTML.
        
        Args:
            html_content: Contenu HTML
            
        Returns:
            Version texte
        """
        import re
        
        # Supprimer les balises HTML et convertir en texte
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
