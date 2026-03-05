"""
Throttling (rate limiting) pour l'authentification.

Protege contre:
- Brute force sur login/password
- Spam d'inscriptions
- Abus de reset password
- Abus d'OTP
"""

from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache


class IPBasedThrottle(SimpleRateThrottle):
    """Throttle base sur l'adresse IP."""

    def get_cache_key(self, request, view):
        ip = get_client_ip(request)
        return f"throttle_{self.scope}_{ip}"


class LoginThrottle(IPBasedThrottle):
    """
    Rate limit pour les tentatives de login.
    Tres restrictif car cible principale des attaques brute force.

    5 tentatives par minute
    20 tentatives par heure
    """

    scope = "login"
    rate = "5/min"


class LoginHourlyThrottle(IPBasedThrottle):
    """Rate limit horaire pour login."""

    scope = "login_hourly"
    rate = "20/hour"


class RegisterThrottle(IPBasedThrottle):
    """
    Rate limit pour les inscriptions.
    Evite le spam de comptes.

    3 inscriptions par heure par IP
    10 inscriptions par jour par IP
    """

    scope = "register"
    rate = "3/hour"


class RegisterDailyThrottle(IPBasedThrottle):
    """Rate limit journalier pour inscription."""

    scope = "register_daily"
    rate = "10/day"


class PasswordResetThrottle(IPBasedThrottle):
    """
    Rate limit pour les demandes de reset password.

    3 demandes par heure
    10 demandes par jour
    """

    scope = "password_reset"
    rate = "3/hour"


class PasswordResetDailyThrottle(IPBasedThrottle):
    """Rate limit journalier pour password reset."""

    scope = "password_reset_daily"
    rate = "10/day"


class OTPRequestThrottle(IPBasedThrottle):
    """
    Rate limit pour les demandes d'OTP.

    5 demandes par heure
    """

    scope = "otp_request"
    rate = "5/hour"


class OTPVerifyThrottle(IPBasedThrottle):
    """
    Rate limit pour la verification d'OTP.
    Evite le brute force sur les codes OTP.

    5 tentatives par 10 minutes
    """

    scope = "otp_verify"
    rate = "5/min"


class RefreshTokenThrottle(IPBasedThrottle):
    """
    Rate limit pour le refresh de token.
    Plus permissif car usage legitime frequent.

    30 par minute
    """

    scope = "refresh"
    rate = "30/min"


class MagicLinkRequestThrottle(IPBasedThrottle):
    """
    Rate limit pour les demandes de magic link.
    Evite le spam d'emails.

    3 demandes par heure par IP
    """

    scope = "magic_link_request"
    rate = "3/hour"


class MagicLinkVerifyThrottle(IPBasedThrottle):
    """
    Rate limit pour la verification de magic link.
    Evite le brute force sur les tokens.

    10 tentatives par minute par IP
    """

    scope = "magic_link_verify"
    rate = "10/min"


# ============== Throttle avec blocage progressif ==============


class ProgressiveLoginThrottle(SimpleRateThrottle):
    """
    Throttle progressif pour login.
    Augmente le temps de blocage apres chaque echec.
    """

    scope = "progressive_login"

    def get_cache_key(self, request, view):
        ip = get_client_ip(request)
        return f"progressive_login_{ip}"

    def get_rate(self):
        """Rate dynamique basee sur le nombre d'echecs."""
        return "5/min"  # Base rate

    def throttle_failure(self):
        """Appele quand la requete est throttlee."""
        pass

    @classmethod
    def record_failure(cls, request):
        """Enregistre un echec de login pour augmenter le blocage."""
        ip = get_client_ip(request)
        cache_key = f"login_failures_{ip}"
        failures = cache.get(cache_key, 0)
        # Augmente le temps de cache exponentiellement
        timeout = min(60 * (2**failures), 3600)  # Max 1 heure
        cache.set(cache_key, failures + 1, timeout)

    @classmethod
    def reset_failures(cls, request):
        """Reset les echecs apres un login reussi."""
        ip = get_client_ip(request)
        cache_key = f"login_failures_{ip}"
        cache.delete(cache_key)


# ============== Simple Throttle Rules ==============


class SimpleThrottleRule(SimpleRateThrottle):
    """
    Throttle generique base sur les settings TENXYTE_SIMPLE_THROTTLE_RULES.

    Permet de throttle n'importe quelle route sans creer de classe custom.

    Usage dans settings.py:
        TENXYTE_SIMPLE_THROTTLE_RULES = {
            '{API_PREFIX}/products/': '100/hour',
            '{API_PREFIX}/search/': '30/min',
            '{API_PREFIX}/upload/': '5/hour',
        }

    Les URLs sont matchees par prefix: '{API_PREFIX}/products/' matchera
    '{API_PREFIX}/products/', '{API_PREFIX}/products/123/', etc.
    Pour un match exact, terminer par '$': '{API_PREFIX}/health/$'
    """

    scope = "simple_rule"

    def __init__(self):
        # Ne pas appeler super().__init__() qui tente de resoudre le rate via scope
        self.rate = None
        self.num_requests = None
        self.duration = None

    def _get_rules(self):
        """Recupere les regles depuis les settings."""
        from django.conf import settings

        return getattr(settings, "TENXYTE_SIMPLE_THROTTLE_RULES", {})

    def _match_path(self, request_path):
        """
        Trouve la regle qui matche le path de la requete.
        Retourne (pattern, rate) ou (None, None).
        Les regles les plus longues (plus specifiques) sont testees en premier.
        """
        rules = self._get_rules()
        if not rules:
            return None, None

        # Trier par longueur decroissante pour matcher le plus specifique d'abord
        sorted_rules = sorted(rules.items(), key=lambda x: len(x[0]), reverse=True)

        for pattern, rate in sorted_rules:
            if pattern.endswith("$"):
                # Match exact (sans le $)
                if request_path == pattern[:-1] or request_path == pattern[:-1].rstrip("/"):
                    return pattern, rate
            else:
                # Match par prefix
                if request_path.startswith(pattern):
                    return pattern, rate

        return None, None

    def get_cache_key(self, request, view):
        pattern, rate = self._match_path(request.path)
        if not pattern:
            return None  # Pas de regle → pas de throttle

        # Stocker le rate pour allow_request
        self.rate = rate
        self.num_requests, self.duration = self.parse_rate(rate)

        # Cle de cache basee sur IP + pattern
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        # Nettoyer le pattern pour la cle de cache
        safe_pattern = pattern.replace("/", "_").strip("_$")
        return f"throttle_simple_{safe_pattern}_{ip}"

    def allow_request(self, request, view):
        _, rate = self._match_path(request.path)
        if not rate:
            return True  # Pas de regle → autoriser

        # Initialiser rate AVANT super() car DRF verifie self.rate is None en premier
        self.rate = rate
        self.num_requests, self.duration = self.parse_rate(rate)
        return super().allow_request(request, view)


# ============== Helpers ==============


def get_client_ip(request) -> str:
    """Récupère l'adresse IP réelle du client.

    Utilise TENXYTE_NUM_PROXIES pour déterminer de manière sûre l'IP client
    à partir de l'en-tête X-Forwarded-For si l'application est derrière des proxies.
    Si TENXYTE_TRUSTED_PROXIES est défini, vérifie en plus que le proxy direct
    est de confiance.

    Returns:
        IP client sous forme de string.
    """
    from .conf import auth_settings

    num_proxies = getattr(auth_settings, "NUM_PROXIES", 0)
    trusted = getattr(auth_settings, "TRUSTED_PROXIES", [])

    remote_addr = request.META.get("REMOTE_ADDR", "")
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for and num_proxies > 0:
        # Validate that REMOTE_ADDR is in TRUSTED_PROXIES
        # SECURITY VULN-003: If TRUSTED_PROXIES is empty, always reject X-Forwarded-For to prevent spoofing
        if not trusted:
            import logging

            logging.getLogger("tenxyte.security").warning(
                "X-Forwarded-For header rejected: TENXYTE_TRUSTED_PROXIES is empty but TENXYTE_NUM_PROXIES > 0. "
                "Configure trusted proxies to enable secure IP resolution behind a reverse proxy."
            )
            return remote_addr

        is_trusted = False
        import ipaddress

        try:
            remote_ip = ipaddress.ip_address(remote_addr)
            for trusted_entry in trusted:
                try:
                    network = ipaddress.ip_network(trusted_entry, strict=False)
                    if remote_ip in network:
                        is_trusted = True
                        break
                except ValueError:
                    continue
        except ValueError:
            pass

        if not is_trusted:
            import logging

            logging.getLogger("tenxyte.security").warning(
                "X-Forwarded-For header rejected: REMOTE_ADDR %s is not in TRUSTED_PROXIES.", remote_addr
            )
            return remote_addr

        # Sécurité F-05 : Extraire la bonne IP selon le nombre de proxies de confiance.
        # X-Forwarded-For est une liste : client, proxy1, proxy2...
        # L'IP la plus sûre (insérée par le premier proxy sous notre contrôle)
        # est à l'index -num_proxies.
        proxies = [ip.strip() for ip in x_forwarded_for.split(",")]
        if len(proxies) >= num_proxies:
            return proxies[-num_proxies]
        else:
            return proxies[0]  # Fallback to the first if there are fewer proxies than num_proxies

    return remote_addr or "127.0.0.1"
