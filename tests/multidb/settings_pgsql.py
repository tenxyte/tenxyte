"""
Settings pour tests multi-DB: PostgreSQL.

Nécessite:
  - pip install psycopg2-binary
  - Variables d'environnement:
    TENXYTE_PG_HOST (défaut: localhost)
    TENXYTE_PG_PORT (défaut: 5432)
    TENXYTE_PG_NAME (défaut: tenxyte_test)
    TENXYTE_PG_USER (défaut: postgres)
    TENXYTE_PG_PASSWORD (défaut: postgres)
"""
import os
from .settings_base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('TENXYTE_PG_HOST', 'localhost'),
        'PORT': os.environ.get('TENXYTE_PG_PORT', '5432'),
        'NAME': os.environ.get('TENXYTE_PG_NAME', 'tenxyte_test'),
        'USER': os.environ.get('TENXYTE_PG_USER', 'postgres'),
        'PASSWORD': os.environ.get('TENXYTE_PG_PASSWORD', 'postgres'),
        'TEST': {
            'NAME': 'tenxyte_test',
        },
    }
}
