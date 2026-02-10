"""
Settings pour tests multi-DB: MySQL.

Nécessite:
  - pip install mysqlclient
  - Variables d'environnement:
    TENXYTE_MYSQL_HOST (défaut: localhost)
    TENXYTE_MYSQL_PORT (défaut: 3306)
    TENXYTE_MYSQL_NAME (défaut: tenxyte_test)
    TENXYTE_MYSQL_USER (défaut: root)
    TENXYTE_MYSQL_PASSWORD (défaut: root)
"""
import os
from .settings_base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.environ.get('TENXYTE_MYSQL_HOST', 'localhost'),
        'PORT': os.environ.get('TENXYTE_MYSQL_PORT', '3306'),
        'NAME': os.environ.get('TENXYTE_MYSQL_NAME', 'tenxyte_test'),
        'USER': os.environ.get('TENXYTE_MYSQL_USER', 'root'),
        'PASSWORD': os.environ.get('TENXYTE_MYSQL_PASSWORD', 'root'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'TEST': {
            'NAME': 'tenxyte_test',
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        },
    }
}
