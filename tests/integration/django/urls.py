"""
URLs pour les tests.
"""
from django.urls import path, include
from tenxyte.conf import auth_settings

api_prefix = auth_settings.API_PREFIX.strip('/')

urlpatterns = [
    path(f'{api_prefix}/auth/', include('tenxyte.urls')),
]
