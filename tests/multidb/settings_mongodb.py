"""
Settings pour tests multi-DB: MongoDB.

Nécessite:
  - pip install django-mongodb-backend
  - Variables d'environnement:
    TENXYTE_MONGO_HOST (défaut: localhost)
    TENXYTE_MONGO_PORT (défaut: 27017)
    TENXYTE_MONGO_NAME (défaut: tenxyte_test)
"""
import os
from .settings_base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'HOST': os.environ.get('TENXYTE_MONGO_HOST', 'localhost'),
        'PORT': int(os.environ.get('TENXYTE_MONGO_PORT', '27017')),
        'NAME': os.environ.get('TENXYTE_MONGO_NAME', 'tenxyte_test'),
    }
}

DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
