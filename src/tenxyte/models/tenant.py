"""
Tenant-aware models and managers for Hard Multi-Tenancy.

This module provides the base classes needed to enforce data isolation
between organizations (tenants) at the ORM level.
"""

from django.db import models
from django.core.exceptions import ValidationError

from .base import AutoFieldClass
from ..conf import org_settings
from ..tenant_context import get_current_organization, get_bypass_tenant_filtering


class TenantManager(models.Manager):
    """
    Manager that automatically filters querysets by the current organization
    if the organizations feature is enabled and a current organization exists in context.
    """
    
    def get_queryset(self):
        """
        Override get_queryset to apply tenant filtering automatically.
        """
        qs = super().get_queryset()
        
        # 1. Skip if organizations feature is completely disabled globally
        if not getattr(org_settings, 'ORGANIZATIONS_ENABLED', False):
            return qs
            
        # 2. Skip if filtering is explicitly bypassed for system operations
        if get_bypass_tenant_filtering():
            return qs
            
        # 3. Apply filter if we have a current organization in the context
        current_org = get_current_organization()
        if current_org:
            return qs.filter(organization=current_org)
            
        # 4. If organizations are enabled, but we have NO context (no current_org),
        # what should we do?
        # Option A: Return empty queryset (safe, strict isolation)
        # Option B: Return all objects (unsafe, potential leak if context missing)
        # For true hard multi-tenancy, missing context means no access.
        # But we also need to consider anonymous access or global admin views.
        # We assume if the developer didn't bypass filtering, and there's no org context,
        # they shouldn't see anything.
        return qs.none()
        
    def without_tenant_filter(self):
        """
        Explicitly get a queryset without tenant filtering.
        Useful for admin interfaces or background tasks crossing organizations.
        """
        return super().get_queryset()


class BaseTenantModel(models.Model):
    """
    Abstract base model for any model that belongs to a specific organization.
    Ensures data isolation between tenants.
    """
    
    # Automatically managed primary key using the globally configured field type
    id = AutoFieldClass(primary_key=True)
    
    # The ForeignKey linking this record to its owner Organization
    # We use a string reference to avoid circular imports.
    organization = models.ForeignKey(
        'tenxyte.Organization',
        on_delete=models.CASCADE,
        related_name='%(class)s_records',
        help_text="The organization this record belongs to",
        db_index=True
    )
    
    # Use the tenant-aware manager as the default
    objects = TenantManager()
    
    # Keep the default manager available under a special name just in case
    # it's needed for pure unfiltered access
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
        
    def save(self, *args, **kwargs):
        """
        Interfere before saving to auto-assign the current organization 
        if organizations feature is enabled.
        """
        if getattr(org_settings, 'ORGANIZATIONS_ENABLED', False):
            # If the record doesn't have an organization yet
            if not getattr(self, 'organization_id', None):
                current_org = get_current_organization()
                
                # Assign the current organization automatically
                if current_org:
                    self.organization = current_org
                # If there's no organization and we're not bypassing, this is an error
                # User is trying to create data without a tenant context
                elif not get_bypass_tenant_filtering():
                    raise ValidationError("Cannot save tenant model without an active organization context.")
                    
        super().save(*args, **kwargs)
