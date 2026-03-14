import pytest
import warnings
from django.core.exceptions import ImproperlyConfigured
from tenxyte.apps import TenxyteConfig
from unittest.mock import patch

class TestTenxyteConfig:
    def test_config_attributes(self):
        """Test basic configuration attributes."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        assert config.name == 'tenxyte'
        assert config.verbose_name == 'Tenxyte Authentication'
        assert config.default_auto_field == 'django.db.models.BigAutoField'

    @pytest.mark.django_db
    def test_ready_method(self):
        """Test the ready method calls all expected functions."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch.object(config, '_check_production_cache') as mock_cache, \
             patch.object(config, '_check_production_security_settings') as mock_security:
            
            config.ready()
            
            mock_cache.assert_called_once()
            mock_security.assert_called_once()

    @pytest.mark.django_db
    def test_ready_signals_import_failure(self):
        """Test ready method handles signals import failure gracefully."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch.object(config, '_check_production_cache'), \
             patch.object(config, '_check_production_security_settings'), \
             patch('builtins.__import__') as mock_import:
            
            mock_import.side_effect = ImportError("No module named 'signals'")
            
            # Should not raise an exception
            config.ready()

    @pytest.mark.django_db
    def test_startup_locmemcache_warning(self):
        # R8: verify the warning is correctly emitted if LocMemCache is present
        # with DEBUG=False and rate limiting enabled.
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        # We need a LocMemCache
        from django.core.cache.backends.locmem import LocMemCache
        dummy_cache = LocMemCache('dummy', {})
        
        from unittest.mock import PropertyMock
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.RATE_LIMITING_ENABLED', new_callable=PropertyMock, return_value=True), \
             patch('django.core.cache.cache', dummy_cache):
             
             with warnings.catch_warnings(record=True) as w:
                 warnings.simplefilter('always')
                 config._check_production_cache()
                 
                 assert len(w) == 1
                 assert issubclass(w[-1].category, RuntimeWarning)
                 assert 'LocMemCache detected with rate limiting enabled in production' in str(w[-1].message)

    def test_startup_locmemcache_no_warning_in_debug(self):
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        from django.core.cache.backends.locmem import LocMemCache
        dummy_cache = LocMemCache('dummy', {})
        
        from unittest.mock import PropertyMock
        with patch('django.conf.settings.DEBUG', True), \
             patch('tenxyte.conf.TenxyteSettings.RATE_LIMITING_ENABLED', new_callable=PropertyMock, return_value=True), \
             patch('django.core.cache.cache', dummy_cache):
             
             with warnings.catch_warnings(record=True) as w:
                 warnings.simplefilter('always')
                 config._check_production_cache()
                 
                 assert len(w) == 0

    def test_startup_locmemcache_no_warning_rate_limiting_disabled(self):
        """Test no warning when rate limiting is disabled."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        from django.core.cache.backends.locmem import LocMemCache
        dummy_cache = LocMemCache('dummy', {})
        
        from unittest.mock import PropertyMock
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.RATE_LIMITING_ENABLED', new_callable=PropertyMock, return_value=False), \
             patch('django.core.cache.cache', dummy_cache):
             
             with warnings.catch_warnings(record=True) as w:
                 warnings.simplefilter('always')
                 config._check_production_cache()
                 
                 assert len(w) == 0

    def test_startup_locmemcache_exception_handling(self):
        """Test that exceptions in cache check don't block startup."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings') as mock_settings:
            mock_settings.DEBUG = False
            mock_settings.side_effect = Exception("Unexpected error")
            
            # Should not raise an exception
            config._check_production_cache()

    def test_startup_locmemcache_cache_import_exception(self):
        """Test that cache import exceptions are handled gracefully."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.RATE_LIMITING_ENABLED', True), \
             patch('django.core.cache.cache', side_effect=Exception("Cache import error")):
            
            # Should not raise an exception
            config._check_production_cache()

    def test_startup_locmemcache_isinstance_exception(self):
        """Test that isinstance check exceptions are handled gracefully."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.RATE_LIMITING_ENABLED', True), \
             patch('django.core.cache.cache', 'not_an_object'), \
             patch('builtins.isinstance', side_effect=Exception("Isinstance error")):
            
            # Should not raise an exception
            config._check_production_cache()

    def test_production_security_jwt_auth_disabled(self):
        """Test error when JWT auth is disabled in production."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', False):
            
            with pytest.raises(ImproperlyConfigured) as exc_info:
                config._check_production_security_settings()
            
            assert "TENXYTE_JWT_AUTH_ENABLED=False is forbidden in production" in str(exc_info.value)

    def test_production_security_application_auth_disabled(self):
        """Test error when application auth is disabled in production."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.APPLICATION_AUTH_ENABLED', False):
            
            with pytest.raises(ImproperlyConfigured) as exc_info:
                config._check_production_security_settings()
            
            assert "TENXYTE_APPLICATION_AUTH_ENABLED=False is forbidden in production" in str(exc_info.value)

    def test_production_security_cors_wildcard_with_credentials(self):
        """Test error when CORS wildcard is combined with credentials in production."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.APPLICATION_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOW_ALL_ORIGINS', True), \
             patch('django.conf.settings.CORS_ALLOW_CREDENTIALS', True, create=True):
            
            with pytest.raises(ImproperlyConfigured) as exc_info:
                config._check_production_security_settings()
            
            assert "CORS_ALLOW_ALL_ORIGINS=True combined with CORS_ALLOW_CREDENTIALS=True" in str(exc_info.value)

    def test_production_security_ssl_redirect_warning(self):
        """Test warning when SSL redirect is disabled in production."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.APPLICATION_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOW_ALL_ORIGINS', False), \
             patch('django.conf.settings.SECURE_SSL_REDIRECT', False):
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                config._check_production_security_settings()
                
                assert len(w) == 1
                assert issubclass(w[-1].category, RuntimeWarning)
                assert "SECURE_SSL_REDIRECT is False in production" in str(w[-1].message)

    def test_production_security_cors_wildcard_error(self):
        """Test error when CORS wildcard is used in production."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.APPLICATION_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOW_ALL_ORIGINS', False), \
             patch('django.conf.settings.SECURE_SSL_REDIRECT', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOWED_ORIGINS', ['*', 'https://example.com']):
            
            with pytest.raises(ImproperlyConfigured) as exc_info:
                config._check_production_security_settings()
            
            assert "Wildcard '*' in TENXYTE_CORS_ALLOWED_ORIGINS is forbidden in production" in str(exc_info.value)

    def test_debug_mode_jwt_disabled_warning(self):
        """Test warning when JWT is disabled in debug mode."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', True), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', False):
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                config._check_production_security_settings()
                
                assert len(w) == 1
                assert issubclass(w[-1].category, RuntimeWarning)
                assert "JWT authentication is DISABLED" in str(w[-1].message)

    def test_debug_mode_no_warnings(self):
        """Test no warnings in debug mode with proper settings."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', True), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True):
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                config._check_production_security_settings()
                
                assert len(w) == 0

    def test_production_security_all_checks_pass(self):
        """Test all security checks pass in production with proper settings."""
        import os
        from types import ModuleType
        mock_module = ModuleType('tenxyte')
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]
        config = TenxyteConfig("tenxyte", mock_module)
        
        with patch('django.conf.settings.DEBUG', False), \
             patch('tenxyte.conf.TenxyteSettings.JWT_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.APPLICATION_AUTH_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOW_ALL_ORIGINS', False), \
             patch('django.conf.settings.SECURE_SSL_REDIRECT', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ENABLED', True), \
             patch('tenxyte.conf.TenxyteSettings.CORS_ALLOWED_ORIGINS', ['https://example.com']):
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                config._check_production_security_settings()
                
                assert len(w) == 0
