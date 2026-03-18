"""
Django settings for testing Tenxyte.
"""


SECRET_KEY = 'test-secret-key-for-testing-only'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'drf_spectacular',
    'tenxyte',
]

# Custom User Model
AUTH_USER_MODEL = 'tenxyte.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'tenxyte.middleware.RequestIDMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]

ROOT_URLCONF = 'tests.integration.django.urls'

# Désactiver l'authentification d'application pour les tests
# Les tests utilisent authenticate_user() qui passe les credentials via l'API
TENXYTE_APPLICATION_AUTH_ENABLED = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Tenxyte swappable models
TENXYTE_USER_MODEL = 'tenxyte.User'
TENXYTE_APPLICATION_MODEL = 'tenxyte.Application'
TENXYTE_ROLE_MODEL = 'tenxyte.Role'
TENXYTE_PERMISSION_MODEL = 'tenxyte.Permission'
TENXYTE_ORGANIZATION_MODEL = 'tenxyte.Organization'
TENXYTE_ORGANIZATION_ROLE_MODEL = 'tenxyte.OrganizationRole'
TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL = 'tenxyte.OrganizationMembership'
TENXYTE_ORGANIZATIONS_ENABLED = True
TENXYTE_API_VERSION = 1
TENXYTE_BASE_URL = 'http://127.0.0.1:8000'

# Tenxyte Auth settings
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 86400 * 7
TENXYTE_TOTP_ISSUER = "TestApp"
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.ConsoleBackend'
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.ConsoleBackend'

# R5 Audit: JWT secret key dédié (obligatoire en production)
# Valeur de test uniquement — NE PAS UTILISER EN PRODUCTION
TENXYTE_JWT_SECRET_KEY = 'test-jwt-secret-key-for-testing-only-not-for-production'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# DRF Spectacular
SPECTACULAR_SETTINGS = {
    'SECURITY': [{'jwtAuth': []}]
}

# Logging
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
        'level': 'INFO',
    },
}

USE_TZ = True
