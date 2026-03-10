import pytest
from django.test import RequestFactory
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, connection
from django.apps import apps
from django.http import HttpResponse
from unittest.mock import patch, MagicMock
from asgiref.sync import sync_to_async
import asyncio

from tenxyte.models import Organization, BaseTenantModel, Application
from tenxyte.tenant_context import (
    set_current_organization,
    get_current_organization,
    set_INTERNAL_bypass_tenant_filtering,
    get_INTERNAL_bypass_tenant_filtering,
)
from tenxyte.middleware import OrganizationContextMiddleware
from tenxyte.conf import org_settings


@pytest.fixture
def org1(db):
    return Organization.objects.create(name="Acme Corp", slug="acme")


@pytest.fixture
def org2(db):
    return Organization.objects.create(name="Stark Industries", slug="stark")


@pytest.fixture(autouse=True)
def ensure_organization_feature_enabled(settings):
    settings.TENXYTE_ORGANIZATIONS_ENABLED = True
    yield
    set_current_organization(None)
    set_INTERNAL_bypass_tenant_filtering(False)


@pytest.mark.django_db
class TestTenantContext:
    
    def test_contextvars_isolation(self, org1, org2):
        """Test that contextvars correctly store and retrieve the current org."""
        assert get_current_organization() is None
        
        set_current_organization(org1)
        assert get_current_organization() == org1
        
        set_current_organization(org2)
        assert get_current_organization() == org2
        
        set_current_organization(None)
        assert get_current_organization() is None


@pytest.mark.django_db
class TestTenantModelManager:
    # Instead of creating a dummy model, we can test the logic of TenantManager
    # by applying it to an existing model temporarily via patching or subclassing
    # However, since it requires a ForeignKey to Organization, it's easier to use Application 
    # and just mock the `organization` attribute for the test, or since Application doesn't have it,
    # we mock the manager `get_queryset` call.
    
    def test_isolation_between_tenants(self, org1, org2):
        """Test that TenantManager filters correctly by organization."""
        # We can test the manager by attaching it to a generic mock and checking filter calls
        from tenxyte.models.tenant import TenantManager
        
        manager = TenantManager()
        
        with patch('django.db.models.Manager.get_queryset') as mock_super_qs:
            # 1. Bypass enabled
            set_INTERNAL_bypass_tenant_filtering(True)
            manager.get_queryset()
            mock_super_qs.assert_called_with()
            mock_super_qs.return_value.filter.assert_not_called()
            
            # Reset
            mock_super_qs.reset_mock()
            set_INTERNAL_bypass_tenant_filtering(False)
            
            # 2. Context enabled (org1)
            set_current_organization(org1)
            manager.get_queryset()
            mock_super_qs.return_value.filter.assert_called_with(organization=org1)
            
            # Reset
            mock_super_qs.reset_mock()
            
            # 3. Context enabled (org2)
            set_current_organization(org2)
            manager.get_queryset()
            mock_super_qs.return_value.filter.assert_called_with(organization=org2)
            
            # Reset
            mock_super_qs.reset_mock()
            
            # 4. No context (should return none())
            set_current_organization(None)
            manager.get_queryset()
            mock_super_qs.return_value.none.assert_called_with()

    def test_without_tenant_filter(self):
        from tenxyte.models.tenant import TenantManager
        manager = TenantManager()
        with patch('django.db.models.Manager.get_queryset') as mock_super_qs:
            manager.without_tenant_filter()
            mock_super_qs.assert_called_with()


@pytest.mark.django_db
class TestTenantModelSave:
    
    def test_auto_assign_organization_logic(self, org1):
        """Test the logic inside BaseTenantModel.save()."""
        from tenxyte.models.tenant import BaseTenantModel
        
        class DummyModel1(BaseTenantModel):
            class Meta:
                app_label = 'dummy_tests'
                managed = False
                
        # Test assign org1
        set_current_organization(org1)
        
        instance = DummyModel1()
        instance.organization_id = None
        
        with patch('django.db.models.Model.save') as mock_super_save:
            instance.save()
            assert instance.organization == org1
            mock_super_save.assert_called_once()
        
    def test_save_without_context_fails_logic(self):
        """Test that trying to save without an org context raises ValidationError."""
        from tenxyte.models.tenant import BaseTenantModel
        
        class DummyModel2(BaseTenantModel):
            class Meta:
                app_label = 'dummy_tests'
                managed = False
                
        set_current_organization(None)
        
        instance = DummyModel2()
        instance.organization_id = None
        
        with pytest.raises(ValidationError):
            instance.save()



@pytest.mark.django_db
class TestOrganizationContextMiddleware:
    
    def test_middleware_sets_contextvars(self, org1):
        """Test that middleware correctly reads header and sets contextvars."""
        factory = RequestFactory()
        request = factory.get('/')
        request.headers = {'X-Org-Slug': org1.slug}
        
        def dummy_get_response(req):
            # Check context *during* request
            assert get_current_organization() == org1
            assert req.organization == org1
            return HttpResponse("OK")
            
        middleware = OrganizationContextMiddleware(dummy_get_response)
        
        # Initialize context to None
        set_current_organization(None)
        
        response = middleware(request)
        
        assert response.status_code == 200
        
        # Context should be cleaned up *after* request
        assert get_current_organization() is None
        
    def test_middleware_cleans_up_on_error(self, org1):
        """Test that middleware cleans up context even if view raises exception."""
        factory = RequestFactory()
        request = factory.get('/')
        request.headers = {'X-Org-Slug': org1.slug}
        
        def dummy_get_response(req):
            assert get_current_organization() == org1
            raise ValueError("Test Error")
            
        middleware = OrganizationContextMiddleware(dummy_get_response)
        
        with pytest.raises(ValueError):
            middleware(request)
            
        # Context should be cleaned up *after* exception
        assert get_current_organization() is None

