import pytest
from django.contrib.auth import get_user_model
from django.db import models

from tenxyte.models import Organization, OrganizationMembership, Application
from tenxyte.services.auth_service import AuthService
from tenxyte.services.social_auth_service import SocialAuthService
from tenxyte.conf import org_settings

User = get_user_model()


@pytest.fixture
def auth_service():
    return AuthService()


@pytest.fixture
def social_auth_service():
    return SocialAuthService()


@pytest.fixture
def test_app(db):
    app, _ = Application.create_application(name="Test App")
    return app


@pytest.fixture(autouse=True)
def setup_org_feature(settings):
    settings.TENXYTE_ORGANIZATIONS_ENABLED = True
    settings.TENXYTE_CREATE_DEFAULT_ORGANIZATION = True
    yield


@pytest.mark.django_db
class TestDefaultOrganizationOnboarding:
    
    def test_register_user_creates_default_org(self, auth_service, test_app):
        """Test that registering a new user creates a default personal workspace."""
        success, user, error = auth_service.register_user(
            email="testuser@example.com",
            password="StrongPassword123!",
            first_name="Test",
            last_name="User",
            application=test_app
        )
        
        assert success is True
        assert user is not None
        
        # Check that the organization was created
        orgs = user.get_organizations()
        assert len(orgs) == 1
        
        org = orgs[0]
        assert org.name == "Test's Workspace"
        assert org.slug.startswith("tests-workspace")
        
        # Check that the user is the owner
        assert user.is_org_owner(org) is True
        
    def test_register_user_without_first_name_creates_default_org(self, auth_service, test_app):
        """Test that registering a new user without a first name uses email prefix."""
        success, user, error = auth_service.register_user(
            email="bob.smith@example.com",
            password="StrongPassword123!",
            application=test_app
        )
        
        assert success is True
        assert user is not None
        
        # Check that the organization was created
        orgs = user.get_organizations()
        assert len(orgs) == 1
        
        org = orgs[0]
        assert org.name == "Bob.smith's Workspace"
        
    def test_disabled_feature_skips_creation(self, auth_service, test_app, settings):
        """Test that disabling the feature prevents org creation."""
        settings.TENXYTE_ORGANIZATIONS_ENABLED = False
        
        success, user, error = auth_service.register_user(
            email="disabled@example.com",
            password="StrongPassword123!",
            application=test_app
        )
        
        assert success is True
        
        # Should be empty since feature is disabled
        orgs = user.get_organizations()
        assert len(orgs) == 0
        # Also double check DB to be sure
        assert Organization.objects.filter(memberships__user=user).count() == 0

    def test_disabled_auto_creation_skips(self, auth_service, test_app, settings):
        """Test that disabling specifically the auto-creation prevents org creation."""
        settings.TENXYTE_CREATE_DEFAULT_ORGANIZATION = False
        
        success, user, error = auth_service.register_user(
            email="noauto@example.com",
            password="StrongPassword123!",
            application=test_app
        )
        
        assert success is True
        
        # Should be empty since auto creation is disabled
        orgs = user.get_organizations()
        assert len(orgs) == 0

    def test_social_auth_creates_default_org(self, social_auth_service, test_app):
        """Test that signing up via social auth creates a default personal workspace."""
        user_data = {
            'provider_user_id': 'google-id-12345',
            'email': 'social@example.com',
            'email_verified': True,
            'first_name': 'Social',
            'last_name': 'Tester',
            'avatar_url': 'http://example.com/avatar.jpg'
        }
        
        success, tokens, error = social_auth_service.authenticate(
            provider_name='google',
            user_data=user_data,
            application=test_app,
            ip_address="127.0.0.1"
        )
        
        assert success is True
        
        # Get the user that was created
        user = User.objects.get(email='social@example.com')
        
        # Check that the organization was created
        orgs = user.get_organizations()
        assert len(orgs) == 1
        
        org = orgs[0]
        assert org.name == "Social's Workspace"
        assert user.is_org_owner(org) is True
