"""
Django settings for testing Tenxyte.
"""

import os

SECRET_KEY = 'test-secret-key-for-testing-only'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'drf_spectacular',
    'tenxyte',
]

# Custom User Model
AUTH_USER_MODEL = 'tenxyte.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'tenxyte.middleware.ApplicationAuthMiddleware',
]

ROOT_URLCONF = 'tests.urls'

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

# Tenxyte Auth settings
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 86400 * 7
TENXYTE_TOTP_ISSUER = "TestApp"
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.ConsoleBackend'
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.ConsoleBackend'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tenxyte.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
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
