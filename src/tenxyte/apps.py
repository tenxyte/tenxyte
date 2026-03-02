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

        # R-02 Audit: Vérification de JWT_AUTH_ENABLED
        self._check_jwt_auth_enabled()

    def _check_jwt_auth_enabled(self):
        """
        R-02: Prevent JWT_AUTH_ENABLED=False in production.
        """
        from django.conf import settings
        from .conf import auth_settings
        import warnings
        
        if not auth_settings.JWT_AUTH_ENABLED:
            if not settings.DEBUG:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured(
                    "TENXYTE_JWT_AUTH_ENABLED=False is forbidden in production. "
                    "Set DEBUG=True to use this flag."
                )
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

