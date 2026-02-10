"""
Settings de base pour les tests multi-DB.
Hérite de tests.settings et est surchargé par chaque backend.
"""
import os
import sys

# Ajouter le chemin racine du projet
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

SECRET_KEY = 'test-secret-key-for-multidb-testing'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'tenxyte',
]

AUTH_USER_MODEL = 'tenxyte.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]

ROOT_URLCONF = 'tests.urls'

# Tenxyte swappable models
TENXYTE_USER_MODEL = 'tenxyte.User'
TENXYTE_APPLICATION_MODEL = 'tenxyte.Application'
TENXYTE_ROLE_MODEL = 'tenxyte.Role'
TENXYTE_PERMISSION_MODEL = 'tenxyte.Permission'

# Tenxyte Auth settings
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 86400 * 7
TENXYTE_TOTP_ISSUER = "TestMultiDB"
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.ConsoleBackend'
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.ConsoleBackend'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

USE_TZ = True
