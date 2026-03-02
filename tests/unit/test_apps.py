import pytest
import warnings
from django.conf import settings
from tenxyte.apps import TenxyteConfig
from unittest.mock import patch, MagicMock

class TestTenxyteConfig:
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
