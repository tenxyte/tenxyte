"""
Django settings for the ephemeral Tenxyte instance used by CI to run the AIRS Conformance
Suite against a real server (spec z_aud_2, task 4.4). Not used by any other test — the main
test suite has its own settings at tests/integration/django/settings.py.

Deliberately close to that file, but with the full middleware stack (including
AgentTokenMiddleware, which the unit test settings omit since unit tests instantiate it
directly) and every AIRS Conformance Level turned on, so the suite can exercise `guards` and
`budget` in addition to `core`/`hitl`/`trace`.
"""

import os

SECRET_KEY = "conformance-ephemeral-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "drf_spectacular",
    "tenxyte",
]

AUTH_USER_MODEL = "tenxyte.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "tenxyte.middleware.RequestIDMiddleware",
    "tenxyte.middleware.ApplicationAuthMiddleware",
    "tenxyte.middleware.AgentTokenMiddleware",
    "tenxyte.middleware.PIIRedactionMiddleware",
]

ROOT_URLCONF = "spec.airs.conformance.tenxyte_ci.urls"

# No application-key layer for this ephemeral instance — the suite is invoked with no
# --airs-app-key/--airs-app-secret, matching this setting.
TENXYTE_APPLICATION_AUTH_ENABLED = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("AIRS_CI_DB_PATH", os.path.join(os.path.dirname(__file__), "_ephemeral.sqlite3")),
    }
}

TENXYTE_USER_MODEL = "tenxyte.User"
TENXYTE_APPLICATION_MODEL = "tenxyte.Application"
TENXYTE_ROLE_MODEL = "tenxyte.Role"
TENXYTE_PERMISSION_MODEL = "tenxyte.Permission"
TENXYTE_ORGANIZATION_MODEL = "tenxyte.Organization"
TENXYTE_ORGANIZATION_ROLE_MODEL = "tenxyte.OrganizationRole"
TENXYTE_ORGANIZATION_MEMBERSHIP_MODEL = "tenxyte.OrganizationMembership"
TENXYTE_ORGANIZATIONS_ENABLED = True
TENXYTE_API_VERSION = 1
TENXYTE_BASE_URL = "http://127.0.0.1:8811"

TENXYTE_JWT_ACCESS_TOKEN_LIFETIME = 3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME = 86400 * 7
TENXYTE_JWT_SECRET_KEY = "conformance-ephemeral-jwt-secret-not-for-production"
TENXYTE_TOTP_ISSUER = "AIRSConformance"
TENXYTE_SMS_BACKEND = "tenxyte.backends.sms.ConsoleBackend"
TENXYTE_EMAIL_BACKEND = "tenxyte.backends.email.ConsoleBackend"

# Every AIRS Conformance Level enabled, so the suite's guards/budget modules run for real.
TENXYTE_AIRS_ENABLED = True
TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED = True
TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
TENXYTE_AUDIT_LOGGING_ENABLED = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["tenxyte.authentication.JWTAuthentication"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [],
}

SPECTACULAR_SETTINGS = {"SECURITY": [{"jwtAuth": []}]}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}

USE_TZ = True
