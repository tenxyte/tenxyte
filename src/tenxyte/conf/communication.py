from django.conf import settings


class CommunicationSettingsMixin:

    @property
    def SMS_BACKEND(self):
        """
        Backend SMS à utiliser.
        Options:
        - 'tenxyte.backends.sms.TwilioBackend'
        - 'tenxyte.backends.sms.NGHBackend'
        - 'tenxyte.backends.sms.ConsoleBackend' (défaut, pour dev)
        """
        return self._get("SMS_BACKEND", "tenxyte.backends.sms.ConsoleBackend")

    @property
    def SMS_ENABLED(self):
        """Activer l'envoi réel de SMS."""
        return self._get("SMS_ENABLED", False)

    @property
    def SMS_DEBUG(self):
        """Mode debug SMS (log au lieu d'envoyer)."""
        return self._get("SMS_DEBUG", True)

    # =============================================
    # Email Backend
    # =============================================

    @property
    def EMAIL_BACKEND(self):
        """
        Backend email à utiliser.
        Options:
        - 'tenxyte.backends.email.DjangoBackend' (défaut, utilise EMAIL_BACKEND Django)
        - 'tenxyte.backends.email.TemplateEmailBackend' (avec support templates)
        - 'tenxyte.backends.email.ConsoleBackend' (pour dev, affiche dans les logs)
        - 'tenxyte.backends.email.SendGridBackend' (legacy, préférer django-anymail)

        Recommandé: Utilisez DjangoBackend et configurez Django mail:
            EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
            # ou avec django-anymail:
            EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
        """
        return self._get("EMAIL_BACKEND", "tenxyte.backends.email.DjangoBackend")

    # =============================================
    # Password Validation
    # =============================================

    @property
    def TWILIO_ACCOUNT_SID(self):
        """Twilio Account SID."""
        return getattr(settings, "TWILIO_ACCOUNT_SID", "")

    @property
    def TWILIO_AUTH_TOKEN(self):
        """Twilio Auth Token."""
        return getattr(settings, "TWILIO_AUTH_TOKEN", "")

    @property
    def TWILIO_PHONE_NUMBER(self):
        """Twilio Phone Number (format: +1234567890)."""
        return getattr(settings, "TWILIO_PHONE_NUMBER", "")

    # =============================================
    # NGH Corp Settings (si backend NGH) — toujours manuels
    # =============================================

    @property
    def NGH_API_KEY(self):
        """NGH Corp API Key."""
        return getattr(settings, "NGH_API_KEY", "")

    @property
    def NGH_API_SECRET(self):
        """NGH Corp API Secret."""
        return getattr(settings, "NGH_API_SECRET", "")

    @property
    def NGH_SENDER_ID(self):
        """NGH Corp Sender ID affiché comme expéditeur du SMS."""
        return getattr(settings, "NGH_SENDER_ID", "")

    # =============================================
    # SendGrid Settings (si backend SendGrid) — toujours manuels
    # =============================================

    @property
    def SENDGRID_API_KEY(self):
        """SendGrid API Key."""
        return getattr(settings, "SENDGRID_API_KEY", "")

    @property
    def SENDGRID_FROM_EMAIL(self):
        """SendGrid email expéditeur."""
        return getattr(settings, "SENDGRID_FROM_EMAIL", "noreply@example.com")

    # =============================================
    # CORS Settings
    # =============================================
