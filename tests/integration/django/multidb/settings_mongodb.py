"""
Settings pour tests multi-DB: MongoDB.

Nécessite:
  - pip install django-mongodb-backend
  - Variables d'environnement:
    TENXYTE_MONGO_HOST (défaut: localhost)
    TENXYTE_MONGO_PORT (défaut: 27017)
    TENXYTE_MONGO_NAME (défaut: tenxyte_test)

Configuration MongoDB (cf. README.md):
  - Remplacer django.contrib.contenttypes → MongoContentTypesConfig
  - Retirer django.contrib.admin et django.contrib.auth
  - Retirer django.contrib.auth.middleware.AuthenticationMiddleware
"""
import os
from .settings_base import *  # noqa: F401,F403

# ─── MongoDB: Désactiver les migrations des apps Django built-in ───
# ContentType et auth.Permission utilisent AutoField (integer PK) incompatible avec ObjectId.
# On désactive leurs migrations pour éviter les erreurs. Les signaux post_migrate
# problématiques (create_permissions, create_contenttypes) sont déconnectés dans conftest.py.
MIGRATION_MODULES = {
    'contenttypes': None,
    'auth': None,
}

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'HOST': os.environ.get('TENXYTE_MONGO_HOST', 'localhost'),
        'PORT': int(os.environ.get('TENXYTE_MONGO_PORT', '27017')),
        'NAME': os.environ.get('TENXYTE_MONGO_NAME', 'tenxyte_test'),
    }
}

DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
