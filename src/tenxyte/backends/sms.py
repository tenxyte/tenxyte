"""
Backends SMS pour l'envoi de codes OTP.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseSMSBackend(ABC):
    """
    Backend abstrait pour l'envoi de SMS.
    """

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Envoie un SMS.

        Args:
            phone_number: Numéro de téléphone au format international (+33612345678)
            message: Contenu du message

        Returns:
            True si l'envoi a réussi
        """
        pass


class ConsoleBackend(BaseSMSBackend):
    """
    Backend console - affiche les SMS dans les logs (pour développement).
    """

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Affiche le SMS dans la console."""
        logger.info(f"[SMS Console] To: {phone_number}")
        logger.info(f"[SMS Console] Message: {message}")
        return True


class TwilioBackend(BaseSMSBackend):
    """
    Backend Twilio - envoie les SMS via l'API Twilio.

    Requiert:
    - pip install twilio
    - Settings: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
    """

    def __init__(self):
        from ..conf import auth_settings

        self.account_sid = auth_settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_settings.TWILIO_AUTH_TOKEN
        self.from_number = auth_settings.TWILIO_PHONE_NUMBER

        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning(
                "[Twilio] Credentials not configured. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER"
            )

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Envoie le SMS via Twilio."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.error("[Twilio] Missing credentials")
            return False

        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException

            client = Client(self.account_sid, self.auth_token)

            result = client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )

            logger.info(f"[Twilio] SMS sent to {phone_number} | SID: {result.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"[Twilio] Error {e.code}: {e.msg}")
            return False
        except ImportError:
            logger.error("[Twilio] Library not installed. Run: pip install tenxyte[twilio]")
            return False
        except Exception as e:
            logger.error(f"[Twilio] Unexpected error: {e}")
            return False


def get_sms_backend() -> BaseSMSBackend:
    """
    Factory pour obtenir le backend SMS configuré.

    Returns:
        Instance du backend SMS
    """
    from django.utils.module_loading import import_string
    from ..conf import auth_settings

    backend_path = auth_settings.SMS_BACKEND
    backend_class = import_string(backend_path)
    return backend_class()
