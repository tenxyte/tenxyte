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
        Import des signals et configurations.
        """
        # Import signals pour l'auto-création de projets par défaut
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
