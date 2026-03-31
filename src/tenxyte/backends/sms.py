"""
Backends SMS pour l'envoi de codes OTP.
"""

import logging
from abc import ABC, abstractmethod

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
        masked = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "****"
        logger.info(f"[SMS Console] To: {masked}")
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
                "[Twilio] Credentials not configured. " "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER"
            )

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Envoie le SMS via Twilio."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.error("[Twilio] Missing credentials")
            return False

        try:
            import twilio.rest
            from twilio.base.exceptions import TwilioRestException

            client = twilio.rest.Client(self.account_sid, self.auth_token)

            result = client.messages.create(body=message, from_=self.from_number, to=phone_number)

            masked = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "****"
            logger.info(f"[Twilio] SMS sent to {masked} | SID: {result.sid}")
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


class NGHBackend(BaseSMSBackend):
    """
    Backend NGH Corp - envoie les SMS via l'API NGH Corp.

    Requiert:
    - Settings: NGH_API_KEY, NGH_API_SECRET, NGH_SENDER_ID
    """

    API_URL = "https://extranet.nghcorp.net/api/send-sms"

    def __init__(self):
        from ..conf import auth_settings

        self.api_key = auth_settings.NGH_API_KEY
        self.api_secret = auth_settings.NGH_API_SECRET
        self.sender_id = auth_settings.NGH_SENDER_ID

        if not all([self.api_key, self.api_secret, self.sender_id]):
            logger.warning("[NGH] Credentials not configured. " "Set NGH_API_KEY, NGH_API_SECRET, NGH_SENDER_ID")

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Envoie le SMS via l'API NGH Corp."""
        if not all([self.api_key, self.api_secret, self.sender_id]):
            logger.error("[NGH] Missing credentials")
            return False

        try:
            import json
            import http.client

            # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected
            conn = http.client.HTTPSConnection("extranet.nghcorp.net")
            payload = json.dumps(
                {
                    "from": self.sender_id,
                    "to": phone_number,
                    "text": message,
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                }
            )
            headers = {"Content-Type": "application/json"}

            conn.request("POST", "/api/send-sms", payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))

            if data.get("status") == 200:
                masked = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "****"
                logger.info(
                    f"[NGH] SMS sent to {masked} | "
                    f"MessageID: {data.get('messageid')} | "
                    f"Credits: {data.get('credits')}"
                )
                return True
            else:
                logger.error(f"[NGH] Failed to send SMS: " f"{data.get('status')} - {data.get('status_desc')}")
                return False

        except Exception as e:
            logger.error(f"[NGH] Unexpected error: {e}")
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
