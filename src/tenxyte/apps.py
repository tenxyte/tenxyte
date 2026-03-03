from django.apps import AppConfig


class TenxyteConfig(AppConfig):
    """
    Configuration de l'application Tenxyte.
    """
    name = 'tenxyte'
    verbose_name = 'Tenxyte Authentication'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Appelé quand l'application est prête.
        Import des signals et vérifications de configuration au démarrage.
        """
        # Import signals pour l'auto-création de projets par défaut
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

        # R8 Audit: Vérification du cache en production
        self._check_production_cache()

        # F-17 Audit: Vérification globale de la sécurité en production
        self._check_production_security_settings()

    def _check_production_security_settings(self):
        """
        R-02 & F-17: Prevent insecure configurations in production.
        Checks JWT authentication, wildcard CORS, and SSL redirect.
        """
        from django.conf import settings
        from .conf import auth_settings
        import warnings
        
        if not settings.DEBUG:
            from django.core.exceptions import ImproperlyConfigured
            
            if not auth_settings.JWT_AUTH_ENABLED:
                raise ImproperlyConfigured(
                    "TENXYTE_JWT_AUTH_ENABLED=False is forbidden in production. "
                    "Set DEBUG=True to use this flag."
                )
            
            if not getattr(auth_settings, 'APPLICATION_AUTH_ENABLED', True):
                raise ImproperlyConfigured(
                    "TENXYTE_APPLICATION_AUTH_ENABLED=False is forbidden in production. "
                    "Set DEBUG=True to use this flag."
                )

            if auth_settings.CORS_ALLOW_ALL_ORIGINS and getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
                raise ImproperlyConfigured(
                    "TENXYTE_CORS_ALLOW_ALL_ORIGINS=True combined with CORS_ALLOW_CREDENTIALS=True "
                    "is extremely dangerous in production."
                )
                
            # F-17 Security Checks
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                warnings.warn(
                    "SECURE_SSL_REDIRECT is False in production. "
                    "Auth tokens should only be transmitted over HTTPS.",
                    RuntimeWarning, stacklevel=2
                )
                
            if auth_settings.CORS_ENABLED and '*' in auth_settings.CORS_ALLOWED_ORIGINS:
                raise ImproperlyConfigured(
                    "Wildcard '*' in TENXYTE_CORS_ALLOWED_ORIGINS is forbidden in production. "
                    "Specify exact allowed origins."
                )
        else:
            if not auth_settings.JWT_AUTH_ENABLED:
                warnings.warn(
                    "JWT authentication is DISABLED. This is a critical security risk.",
                    RuntimeWarning, stacklevel=2
                )

    def _check_production_cache(self):
        """
        R8: Avertit si LocMemCache est utilisé avec le rate limiting en production.
        LocMemCache est local au processus — en multi-workers (Gunicorn), les limites
        sont par worker, rendant le rate limiting inefficace.
        """
        try:
            from django.conf import settings
            from .conf import auth_settings

            if settings.DEBUG or not auth_settings.RATE_LIMITING_ENABLED:
                return

            from django.core.cache import cache
            from django.core.cache.backends.locmem import LocMemCache

            if isinstance(cache, LocMemCache):
                import warnings
                warnings.warn(
                    "Tenxyte: LocMemCache detected with rate limiting enabled in production (DEBUG=False). "
                    "Rate limits are per-worker and ineffective in multi-process deployments (Gunicorn, uWSGI). "
                    "Configure a shared cache backend (Redis recommended): "
                    "CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', ...}}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        except Exception:
            pass  # Ne jamais bloquer le démarrage

