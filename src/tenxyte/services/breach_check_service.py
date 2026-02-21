"""
Breach Password Check Service.

Uses the HaveIBeenPwned (HIBP) Pwned Passwords API with k-anonymity:
- Only the first 5 characters of the SHA-1 hash are sent to the API
- The full hash never leaves the client
- API: https://api.pwnedpasswords.com/range/{first5chars}

References:
- https://haveibeenpwned.com/API/v3#PwnedPasswords
- https://www.troyhunt.com/ive-just-launched-pwned-passwords-version-2/
"""
import hashlib
import logging
from typing import Tuple

import requests

from ..conf import auth_settings

logger = logging.getLogger(__name__)

HIBP_API_URL = 'https://api.pwnedpasswords.com/range/{prefix}'
HIBP_TIMEOUT = 5  # seconds


class BreachCheckService:
    """
    Vérifie si un mot de passe a été compromis via l'API HaveIBeenPwned.

    Utilise la technique k-anonymity:
    1. Calcule SHA-1 du mot de passe
    2. Envoie seulement les 5 premiers caractères à l'API
    3. L'API retourne tous les suffixes correspondants
    4. Compare localement le suffixe complet
    5. Le mot de passe en clair ne quitte jamais le serveur
    """

    def is_pwned(self, password: str) -> Tuple[bool, int]:
        """
        Vérifie si le mot de passe a été compromis.

        Args:
            password: Le mot de passe en clair à vérifier

        Returns:
            (is_pwned: bool, count: int)
            - is_pwned: True si le mot de passe a été trouvé dans des fuites
            - count: Nombre de fois où ce mot de passe a été vu dans des fuites
        """
        if not auth_settings.BREACH_CHECK_ENABLED:
            return False, 0

        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        try:
            response = requests.get(
                HIBP_API_URL.format(prefix=prefix),
                headers={'Add-Padding': 'true'},
                timeout=HIBP_TIMEOUT
            )
            response.raise_for_status()
        except requests.Timeout:
            logger.warning("HIBP API timeout — skipping breach check")
            return False, 0
        except requests.RequestException as e:
            logger.warning(f"HIBP API error: {e} — skipping breach check")
            return False, 0

        # Parse response: each line is "SUFFIX:COUNT"
        for line in response.text.splitlines():
            if ':' not in line:
                continue
            line_suffix, _, count_str = line.partition(':')
            if line_suffix.upper() == suffix:
                count = int(count_str.strip())
                return True, count

        return False, 0

    def check_password(self, password: str) -> Tuple[bool, str]:
        """
        Vérifie le mot de passe et retourne (ok, error_message).

        Args:
            password: Le mot de passe à vérifier

        Returns:
            (ok: bool, error: str)
            - ok: True si le mot de passe est sûr (ou si la vérification est désactivée)
            - error: Message d'erreur si compromis
        """
        if not auth_settings.BREACH_CHECK_ENABLED:
            return True, ''

        is_pwned, count = self.is_pwned(password)

        if not is_pwned:
            return True, ''

        if auth_settings.BREACH_CHECK_REJECT:
            return False, (
                f'This password has appeared in {count:,} data breaches. '
                'Please choose a different password.'
            )

        # Warn mode: return ok=True but log the warning
        logger.warning(f"User chose a pwned password (seen {count} times) — warning mode only")
        return True, ''


breach_check_service = BreachCheckService()
