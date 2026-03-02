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

