"""
URLs pour les tests.
"""
from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('tenxyte.urls')),
]
