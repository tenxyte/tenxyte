"""
Fixtures pytest pour les tests Tenxyte.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from tenxyte.models import Application, Role, Permission


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Ensure migrations are run before tests."""
    with django_db_blocker.unblock():
        call_command('migrate', '--run-syncdb')
    yield


@pytest.fixture
def api_client():
    """Client API REST Framework."""
    return APIClient()


@pytest.fixture
def application(db):
    """Application de test."""
    app, raw_secret = Application.create_application(
        name="Test App",
        description="Application for testing"
    )
    # Stocker le secret brut pour les tests d'authentification
    app._plain_secret = raw_secret
    return app


@pytest.fixture
def user(db):
    """Utilisateur de test."""
    User = get_user_model()
    user = User.objects.create(
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.fixture
def user_with_phone(db):
    """Utilisateur avec numéro de téléphone."""
    User = get_user_model()
    user = User.objects.create(
        email="phone@example.com",
        phone_country_code="33",
        phone_number="612345678",
        first_name="Phone",
        last_name="User"
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    """Administrateur de test."""
    User = get_user_model()
    user = User.objects.create(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_active=True
    )
    user.set_password("AdminPassword123!")
    user.save()

    # Ajouter le rôle admin
    admin_role, _ = Role.objects.get_or_create(
        code="admin",
        defaults={"name": "Administrator"}
    )
    user.roles.add(admin_role)

    return user


@pytest.fixture
def permission(db):
    """Permission de test."""
    return Permission.objects.create(
        code="test.permission",
        name="Test Permission",
        description="Permission for testing"
    )


@pytest.fixture
def role(db, permission):
    """Rôle de test avec permission."""
    role = Role.objects.create(
        code="test_role",
        name="Test Role",
        description="Role for testing"
    )
    role.permissions.add(permission)
    return role


@pytest.fixture
def app_api_client(api_client, application):
    """Client API avec headers d'application (pas d'auth JWT)."""
    api_client.credentials(
        HTTP_X_ACCESS_KEY=application.access_key,
        HTTP_X_ACCESS_SECRET=application._plain_secret
    )
    return api_client


@pytest.fixture
def authenticated_client(api_client, user, application):
    """Client authentifié avec JWT + headers application."""
    from tests.integration.django.auth_service_compat import AuthService

    auth_service = AuthService()
    success, data, error = auth_service.authenticate_by_email(
        email=user.email,
        password="TestPassword123!",
        application=application,
        ip_address="127.0.0.1"
    )

    if success:
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )

    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user, application):
    """Client admin authentifié avec JWT + headers application."""
    from tests.integration.django.auth_service_compat import AuthService

    auth_service = AuthService()
    success, data, error = auth_service.authenticate_by_email(
        email=admin_user.email,
        password="AdminPassword123!",
        application=application,
        ip_address="127.0.0.1"
    )

    if success:
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )

    return api_client


@pytest.fixture
def user_with_2fa(db):
    """Utilisateur avec 2FA activé."""
    User = get_user_model()
    user = User.objects.create(
        email="2fa@example.com",
        first_name="TwoFA",
        last_name="User"
    )
    user.set_password("TestPassword123!")
    user.is_2fa_enabled = True
    user.totp_secret = "JBSWY3DPEHPK3PXP"
    user.backup_codes = [
        "hash1",
        "hash2",
        "hash3",
    ]
    user.save()
    return user
