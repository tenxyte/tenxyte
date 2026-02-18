"""
Throttling (rate limiting) pour l'authentification.

Protege contre:
- Brute force sur login/password
- Spam d'inscriptions
- Abus de reset password
- Abus d'OTP
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle
from django.core.cache import cache


class IPBasedThrottle(SimpleRateThrottle):
    """Throttle base sur l'adresse IP."""

    def get_cache_key(self, request, view):
        # Recuperer l'IP reelle (derriere proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return f"throttle_{self.scope}_{ip}"


class LoginThrottle(IPBasedThrottle):
    """
    Rate limit pour les tentatives de login.
    Tres restrictif car cible principale des attaques brute force.

    5 tentatives par minute
    20 tentatives par heure
    """
    scope = 'login'
    rate = '5/min'


class LoginHourlyThrottle(IPBasedThrottle):
    """Rate limit horaire pour login."""
    scope = 'login_hourly'
    rate = '20/hour'


class RegisterThrottle(IPBasedThrottle):
    """
    Rate limit pour les inscriptions.
    Evite le spam de comptes.

    3 inscriptions par heure par IP
    10 inscriptions par jour par IP
    """
    scope = 'register'
    rate = '3/hour'


class RegisterDailyThrottle(IPBasedThrottle):
    """Rate limit journalier pour inscription."""
    scope = 'register_daily'
    rate = '10/day'


class PasswordResetThrottle(IPBasedThrottle):
    """
    Rate limit pour les demandes de reset password.

    3 demandes par heure
    10 demandes par jour
    """
    scope = 'password_reset'
    rate = '3/hour'


class PasswordResetDailyThrottle(IPBasedThrottle):
    """Rate limit journalier pour password reset."""
    scope = 'password_reset_daily'
    rate = '10/day'


class OTPRequestThrottle(IPBasedThrottle):
    """
    Rate limit pour les demandes d'OTP.

    5 demandes par heure
    """
    scope = 'otp_request'
    rate = '5/hour'


class OTPVerifyThrottle(IPBasedThrottle):
    """
    Rate limit pour la verification d'OTP.
    Evite le brute force sur les codes OTP.

    5 tentatives par 10 minutes
    """
    scope = 'otp_verify'
    rate = '5/min'


class RefreshTokenThrottle(IPBasedThrottle):
    """
    Rate limit pour le refresh de token.
    Plus permissif car usage legitime frequent.

    30 par minute
    """
    scope = 'refresh'
    rate = '30/min'


class GoogleAuthThrottle(IPBasedThrottle):
    """
    Rate limit pour l'auth Google.

    10 par minute
    """
    scope = 'google_auth'
    rate = '10/min'


# ============== Throttle avec blocage progressif ==============

class ProgressiveLoginThrottle(SimpleRateThrottle):
    """
    Throttle progressif pour login.
    Augmente le temps de blocage apres chaque echec.
    """
    scope = 'progressive_login'

    def get_cache_key(self, request, view):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return f"progressive_login_{ip}"

    def get_rate(self):
        """Rate dynamique basee sur le nombre d'echecs."""
        return '5/min'  # Base rate

    def throttle_failure(self):
        """Appele quand la requete est throttlee."""
        pass

    @classmethod
    def record_failure(cls, request):
        """Enregistre un echec de login pour augmenter le blocage."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        cache_key = f"login_failures_{ip}"
        failures = cache.get(cache_key, 0)
        # Augmente le temps de cache exponentiellement
        timeout = min(60 * (2 ** failures), 3600)  # Max 1 heure
        cache.set(cache_key, failures + 1, timeout)

    @classmethod
    def reset_failures(cls, request):
        """Reset les echecs apres un login reussi."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        cache_key = f"login_failures_{ip}"
        cache.delete(cache_key)


# ============== Simple Throttle Rules ==============

class SimpleThrottleRule(SimpleRateThrottle):
    """
    Throttle generique base sur les settings TENXYTE_SIMPLE_THROTTLE_RULES.

    Permet de throttle n'importe quelle route sans creer de classe custom.

    Usage dans settings.py:
        TENXYTE_SIMPLE_THROTTLE_RULES = {
            '/api/v1/products/': '100/hour',
            '/api/v1/search/': '30/min',
            '/api/v1/upload/': '5/hour',
        }

    Les URLs sont matchees par prefix: '/api/v1/products/' matchera
    '/api/v1/products/', '/api/v1/products/123/', etc.
    Pour un match exact, terminer par '$': '/api/v1/health/$'
    """
    scope = 'simple_rule'

    def __init__(self):
        # Ne pas appeler super().__init__() qui tente de resoudre le rate via scope
        self.rate = None
        self.num_requests = None
        self.duration = None

    def _get_rules(self):
        """Recupere les regles depuis les settings."""
        from django.conf import settings
        return getattr(settings, 'TENXYTE_SIMPLE_THROTTLE_RULES', {})

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
            if pattern.endswith('$'):
                # Match exact (sans le $)
                if request_path == pattern[:-1] or request_path == pattern[:-1].rstrip('/'):
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
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Nettoyer le pattern pour la cle de cache
        safe_pattern = pattern.replace('/', '_').strip('_$')
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

def get_client_ip(request):
    """Recupere l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
