"""
Tests for tenxyte.setup() helper function.
"""
from types import SimpleNamespace


class TestSetupHelper:
    """Tests for the tenxyte.setup() auto-configuration function."""

    def _make_settings(self, **kwargs):
        """Create a mock settings namespace with defaults."""
        defaults = {
            'INSTALLED_APPS': [
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
            ],
            'MIDDLEWARE': [
                'django.middleware.security.SecurityMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_setup_adds_installed_apps(self):
        """setup() adds 'rest_framework' and 'tenxyte' to INSTALLED_APPS."""
        from tenxyte import setup

        settings = self._make_settings()
        setup(settings)
        assert 'rest_framework' in settings.INSTALLED_APPS
        assert 'tenxyte' in settings.INSTALLED_APPS

    def test_setup_sets_auth_user_model(self):
        """setup() sets AUTH_USER_MODEL to 'tenxyte.User' if not set."""
        from tenxyte import setup

        settings = self._make_settings()
        setup(settings)
        assert settings.AUTH_USER_MODEL == 'tenxyte.User'

    def test_setup_sets_auth_user_model_from_default(self):
        """setup() overrides Django's default 'auth.User' model."""
        from tenxyte import setup

        settings = self._make_settings(AUTH_USER_MODEL='auth.User')
        setup(settings)
        assert settings.AUTH_USER_MODEL == 'tenxyte.User'

    def test_setup_sets_rest_framework(self):
        """setup() sets DEFAULT_AUTHENTICATION_CLASSES if not already configured."""
        from tenxyte import setup

        settings = self._make_settings()
        setup(settings)
        assert 'REST_FRAMEWORK' in dir(settings)
        assert 'tenxyte.authentication.JWTAuthentication' in settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']

    def test_setup_adds_middleware(self):
        """setup() adds ApplicationAuthMiddleware to MIDDLEWARE."""
        from tenxyte import setup

        settings = self._make_settings()
        setup(settings)
        assert 'tenxyte.middleware.ApplicationAuthMiddleware' in settings.MIDDLEWARE

    def test_setup_does_not_override_existing_auth_user_model(self):
        """setup() does not override a custom AUTH_USER_MODEL."""
        from tenxyte import setup

        settings = self._make_settings(AUTH_USER_MODEL='myapp.CustomUser')
        setup(settings)
        assert settings.AUTH_USER_MODEL == 'myapp.CustomUser'

    def test_setup_does_not_override_existing_rest_framework(self):
        """setup() does not override existing DEFAULT_AUTHENTICATION_CLASSES."""
        from tenxyte import setup

        custom_rf = {
            'DEFAULT_AUTHENTICATION_CLASSES': ['myapp.CustomAuth'],
        }
        settings = self._make_settings(REST_FRAMEWORK=custom_rf)
        setup(settings)
        assert settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] == ['myapp.CustomAuth']

    def test_setup_does_not_duplicate_installed_apps(self):
        """setup() does not add duplicates if apps already present."""
        from tenxyte import setup

        settings = self._make_settings(INSTALLED_APPS=[
            'django.contrib.admin',
            'rest_framework',
            'tenxyte',
        ])
        setup(settings)
        assert settings.INSTALLED_APPS.count('rest_framework') == 1
        assert settings.INSTALLED_APPS.count('tenxyte') == 1

    def test_setup_does_not_duplicate_middleware(self):
        """setup() does not add middleware duplicates."""
        from tenxyte import setup

        settings = self._make_settings(MIDDLEWARE=[
            'django.middleware.common.CommonMiddleware',
            'tenxyte.middleware.ApplicationAuthMiddleware',
        ])
        setup(settings)
        assert settings.MIDDLEWARE.count('tenxyte.middleware.ApplicationAuthMiddleware') == 1

    def test_setup_idempotent(self):
        """Calling setup() multiple times produces the same result."""
        from tenxyte import setup

        settings = self._make_settings()
        setup(settings)
        first_state = {
            'INSTALLED_APPS': list(settings.INSTALLED_APPS),
            'AUTH_USER_MODEL': settings.AUTH_USER_MODEL,
            'REST_FRAMEWORK': dict(settings.REST_FRAMEWORK),
            'MIDDLEWARE': list(settings.MIDDLEWARE),
        }

        setup(settings)  # Second call
        setup(settings)  # Third call

        assert settings.INSTALLED_APPS == first_state['INSTALLED_APPS']
        assert settings.AUTH_USER_MODEL == first_state['AUTH_USER_MODEL']
        assert settings.REST_FRAMEWORK == first_state['REST_FRAMEWORK']
        assert settings.MIDDLEWARE == first_state['MIDDLEWARE']

    def test_setup_empty_settings(self):
        """setup() works with completely empty settings."""
        from tenxyte import setup

        settings = SimpleNamespace()
        setup(settings)
        assert hasattr(settings, 'AUTH_USER_MODEL')
        assert hasattr(settings, 'INSTALLED_APPS')
        assert hasattr(settings, 'REST_FRAMEWORK')
        assert hasattr(settings, 'MIDDLEWARE')

    def test_setup_preserves_existing_apps_order(self):
        """setup() appends new apps at the end, preserving order."""
        from tenxyte import setup

        original_apps = ['django.contrib.admin', 'django.contrib.auth']
        settings = self._make_settings(INSTALLED_APPS=list(original_apps))
        setup(settings)
        assert settings.INSTALLED_APPS[:2] == original_apps
