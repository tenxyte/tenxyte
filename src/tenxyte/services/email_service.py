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
