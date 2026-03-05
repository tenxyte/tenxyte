from django.conf import settings
from .presets import SECURE_MODE_PRESETS
import warnings
from django.core.exceptions import ImproperlyConfigured

class BaseSettingsMixin:

    def _get(self, name: str, default):
        """
        Résout la valeur d'un setting en appliquant la priorité :
        settings.py > preset > défaut.

        Args:
            name: Nom du setting SANS le préfixe TENXYTE_ (ex: 'JWT_ACCESS_TOKEN_LIFETIME')
            default: Valeur par défaut si ni settings.py ni preset ne définissent la valeur
        """
        from .presets import VALID_SECURE_MODES, SECURE_MODE_PRESETS
        django_key = f'TENXYTE_{name}'

        # 1. Valeur explicite dans settings.py — priorité absolue
        if hasattr(settings, django_key):
            return getattr(settings, django_key)

        # 2. Preset du mode actif
        mode = getattr(settings, 'TENXYTE_SHORTCUT_SECURE_MODE', None)
        # Auto-activate development preset in DEBUG mode (zero-config DX)
        if mode is None and getattr(settings, 'DEBUG', False):
            mode = 'development'
        if mode is not None:
            if mode not in VALID_SECURE_MODES:
                import warnings
                warnings.warn(
                    f"TENXYTE_SHORTCUT_SECURE_MODE='{mode}' is invalid. "
                    f"Valid values: {sorted(VALID_SECURE_MODES)}. Falling back to defaults.",
                    UserWarning,
                    stacklevel=3,
                )
            else:
                preset = SECURE_MODE_PRESETS[mode]
                if name in preset:
                    return preset[name]

        # 3. Défaut conf.py
        return default

    @property
    def BASE_URL(self):
        """URL de base de l'API."""
        return self._get('BASE_URL', 'http://127.0.0.1:8000')



    @property
    def API_VERSION(self):
        """Version de l'API (ex: 1)."""
        return self._get('API_VERSION', 1)

    @property
    def API_PREFIX(self):
        """Prefixe de l'API (ex: /api/v1)."""
        prefix = self._get('API_PREFIX', f'/api/v{self.API_VERSION}')
        # S'assurer que ça commence par / mais ne finit pas par /
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        return prefix.rstrip('/')

    # =============================================
    # JWT Settings
    # =============================================

    @property
    def EXEMPT_PATHS(self):
        """Chemins exemptés de l'authentification par application (match par préfixe)."""
        return self._get('EXEMPT_PATHS', ['/admin/', f'{self.API_PREFIX}/health/', f'{self.API_PREFIX}/docs/'])

    @property
    def EXACT_EXEMPT_PATHS(self):
        """Chemins exemptés de l'authentification par application (match exact)."""
        return self._get('EXACT_EXEMPT_PATHS', [f'{self.API_PREFIX}/'])

    # =============================================
    # Session & Device Limits
    # =============================================

    @property
    def SIMPLE_THROTTLE_RULES(self):
        """
        Règles de throttling simples par URL.
        Permet de throttle n'importe quelle route sans créer de classe custom.

        Format: { 'url_prefix': 'rate' }
        - Prefix match par défaut: '{API_PREFIX}/products/' matche '{API_PREFIX}/products/123/'
        - Match exact avec '$': '{API_PREFIX}/health/$'
        - Rates: 'X/sec', 'X/min', 'X/hour', 'X/day'

        Exemple:
            TENXYTE_SIMPLE_THROTTLE_RULES = {
                '{API_PREFIX}/products/': '100/hour',
                '{API_PREFIX}/search/': '30/min',
                '{API_PREFIX}/upload/': '5/hour',
            }

        Nécessite d'ajouter 'tenxyte.throttles.SimpleThrottleRule' dans
        REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'].
        """
        return self._get('SIMPLE_THROTTLE_RULES', {})

    # =============================================
    # Audit Logging
    # =============================================

    @property
    def ORG_ROLE_INHERITANCE(self):
        """
        Enable role inheritance in organization hierarchy.
        If True, roles propagate down from parent to children.
        Default: True
        """
        return self._get('ORG_ROLE_INHERITANCE', True)

    @property
    def ORG_MAX_DEPTH(self):
        """
        Maximum depth of organization hierarchy.
        Default: 5 levels
        """
        return self._get('ORG_MAX_DEPTH', 5)

    @property
    def ORG_MAX_MEMBERS(self):
        """
        Default maximum members per organization (0 = unlimited).
        Can be overridden per organization.
        Default: 0 (unlimited)
        """
        return self._get('ORG_MAX_MEMBERS', 0)

