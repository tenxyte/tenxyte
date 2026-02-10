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


# ============== Helpers ==============

def get_client_ip(request):
    """Recupere l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
