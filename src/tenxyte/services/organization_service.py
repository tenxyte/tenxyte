"""
OrganizationService - Business logic for organization management.

Handles:
- CRUD operations for organizations
- Parent/child hierarchy management
- Member management
- Invitation workflow
- Permission checks
"""

from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta

from ..models import (
    get_organization_model,
    get_organization_role_model,
    get_organization_membership_model,
    get_user_model,
    AuditLog,
)
from ..conf import org_settings


class OrganizationService:
    """Service for managing organizations, members, and invitations."""
    
    def __init__(self):
        self.Organization = get_organization_model()
        self.OrganizationRole = get_organization_role_model()
        self.OrganizationMembership = get_organization_membership_model()
        self.User = get_user_model()
    
    # =============================================
    # Organization CRUD
    # =============================================
    
    @transaction.atomic
    def create_organization(
        self,
        name: str,
        created_by,
        slug: str = None,
        description: str = '',
        parent_id: int = None,
        metadata: dict = None,
        max_members: int = 0
    ) -> Tuple[bool, Optional[Any], str]:
        """
        Create a new organization.
        
        Args:
            name: Organization name
            created_by: User creating the organization
            slug: URL-safe identifier (auto-generated if not provided)
            description: Optional description
            parent_id: Parent organization ID for hierarchy
            metadata: Custom JSON metadata
            max_members: Maximum members (0 = unlimited)
            
        Returns:
            Tuple[success, organization, error_message]
        """
        try:
            # Generate slug if not provided
            if not slug:
                slug = slugify(name)
                # Ensure uniqueness
                base_slug = slug
                counter = 1
                while self.Organization.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
            
            # Check parent if provided
            parent = None
            if parent_id:
                try:
                    parent = self.Organization.objects.get(id=parent_id)
                    
                    # Check depth limit
                    if not parent.can_add_child():
                        return False, None, f'Maximum organization depth ({org_settings.ORG_MAX_DEPTH}) reached'
                    
                except self.Organization.DoesNotExist:
                    return False, None, 'Parent organization not found'
            
            # Create organization
            organization = self.Organization.objects.create(
                name=name,
                slug=slug,
                description=description,
                parent=parent,
                metadata=metadata or {},
                max_members=max_members or org_settings.ORG_MAX_MEMBERS,
                created_by=created_by
            )
            
            # Get or create 'owner' role
            owner_role, _ = self.OrganizationRole.objects.get_or_create(
                code='owner',
                defaults={
                    'name': 'Owner',
                    'description': 'Organization owner with full access',
                    'is_system': True,
                    'permissions': [
                        'org.*',  # All permissions
                    ]
                }
            )
            
            # Assign creator as owner
            self.OrganizationMembership.objects.create(
                user=created_by,
                organization=organization,
                role=owner_role,
                status='active'
            )
            
            # Audit log
            self._audit_log('organization_created', created_by, {
                'organization_id': organization.id,
                'organization_name': organization.name,
                'slug': organization.slug,
                'parent_id': parent_id
            })
            
            return True, organization, ''
            
        except Exception as e:
            return False, None, f'Error creating organization: {str(e)}'
    
    def get_organization(self, slug: str = None, org_id: int = None) -> Optional[Any]:
        """
        Get an organization by slug or ID.
        
        Args:
            slug: Organization slug
            org_id: Organization ID
            
        Returns:
            Organization instance or None
        """
        try:
            if slug:
                return self.Organization.objects.get(slug=slug, is_active=True)
            elif org_id:
                return self.Organization.objects.get(id=org_id, is_active=True)
            return None
        except self.Organization.DoesNotExist:
            return None
    
    @transaction.atomic
    def update_organization(
        self,
        organization,
        user,
        **updates
    ) -> Tuple[bool, str]:
        """
        Update an organization.
        
        Args:
            organization: Organization instance
            user: User performing the update
            **updates: Fields to update
            
        Returns:
            Tuple[success, error_message]
        """
        # Check permission
        if not user.has_org_role(organization, 'owner') and not user.has_org_role(organization, 'admin'):
            return False, 'Insufficient permissions to update organization'
        
        # Validate max_members against current active member count
        if 'max_members' in updates:
            new_max = updates['max_members']
            if new_max > 0:
                current_count = organization.get_member_count()
                if new_max < current_count:
                    return False, (
                        f'Cannot set max_members to {new_max}: '
                        f'organization already has {current_count} active members'
                    )
        
        allowed_fields = ['name', 'description', 'metadata', 'max_members']
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(organization, field, value)
        
        organization.save()
        
        # Audit log
        self._audit_log('organization_updated', user, {
            'organization_id': organization.id,
            'updates': updates
        })
        
        return True, ''
    
    @transaction.atomic
    def delete_organization(
        self,
        organization,
        user
    ) -> Tuple[bool, str]:
        """
        Delete an organization (soft delete).
        
        Args:
            organization: Organization instance
            user: User performing the deletion
            
        Returns:
            Tuple[success, error_message]
        """
        # Only owner can delete
        if not user.has_org_role(organization, 'owner', check_inheritance=False):
            return False, 'Only the owner can delete an organization'
        
        # Check for children
        if organization.children.exists():
            return False, 'Cannot delete organization with child organizations'
        
        # Soft delete
        organization.is_active = False
        organization.save()
        
        # Audit log
        self._audit_log('organization_deleted', user, {
            'organization_id': organization.id,
            'organization_name': organization.name
        })
        
        return True, ''
    
    # =============================================
    # Hierarchy Management
    # =============================================
    
    def get_organization_tree(self, organization) -> Dict[str, Any]:
        """
        Get the complete organization tree.
        
        Args:
            organization: Root organization
            
        Returns:
            Dictionary representing the tree
        """
        def build_tree(org):
            return {
                'id': org.id,
                'name': org.name,
                'slug': org.slug,
                'depth': org.depth,
                'is_root': org.is_root,
                'member_count': org.get_member_count(),
                'children': [build_tree(child) for child in org.children.filter(is_active=True)]
            }
        
        root = organization.get_root()
        return build_tree(root)
    
    def move_organization(
        self,
        organization,
        new_parent_id: int,
        user
    ) -> Tuple[bool, str]:
        """
        Move an organization to a new parent.
        
        Args:
            organization: Organization to move
            new_parent_id: New parent organization ID (None for root)
            user: User performing the move
            
        Returns:
            Tuple[success, error_message]
        """
        # Check permission
        if not user.has_org_role(organization, 'owner', check_inheritance=False):
            return False, 'Only the owner can move an organization'
        
        # Get new parent
        new_parent = None
        if new_parent_id:
            try:
                new_parent = self.Organization.objects.get(id=new_parent_id)
                
                # Prevent circular reference
                if organization.id == new_parent.id:
                    return False, 'Cannot move organization to itself'
                
                # Check if new_parent is a descendant
                descendants = organization.get_descendants(include_self=True)
                if new_parent in descendants:
                    return False, 'Cannot move organization to its own descendant'
                
                # Check depth limit
                if not new_parent.can_add_child():
                    return False, 'Maximum depth reached for new parent'
                
            except self.Organization.DoesNotExist:
                return False, 'New parent organization not found'
        
        # Move
        organization.parent = new_parent
        organization.save()
        
        # Audit log
        self._audit_log('organization_moved', user, {
            'organization_id': organization.id,
            'old_parent_id': organization.parent.id if organization.parent else None,
            'new_parent_id': new_parent_id
        })
        
        return True, ''
    
    # =============================================
    # Member Management
    # =============================================
    
    def add_member(
        self,
        organization,
        user_to_add,
        role_code: str,
        added_by,
        status: str = 'active'
    ) -> Tuple[bool, Optional[Any], str]:
        """
        Add a member to an organization.
        
        Args:
            organization: Organization instance
            user_to_add: User to add
            role_code: Role code to assign
            added_by: User performing the action
            status: Membership status (default: 'active')
            
        Returns:
            Tuple[success, membership, error_message]
        """
        # Check permission
        if not added_by.has_org_permission(organization, 'org.members.invite'):
            return False, None, 'Insufficient permissions to add members'
        
        # Check member limit
        if organization.is_at_member_limit():
            return False, None, 'Organization has reached its member limit'
        
        # Get role
        try:
            role = self.OrganizationRole.objects.get(code=role_code)
        except self.OrganizationRole.DoesNotExist:
            return False, None, f'Role {role_code} not found'
        
        # Check if already member
        if self.OrganizationMembership.objects.filter(
            user=user_to_add,
            organization=organization
        ).exists():
            return False, None, 'User is already a member'
        
        # Create membership
        membership = self.OrganizationMembership.objects.create(
            user=user_to_add,
            organization=organization,
            role=role,
            status=status,
            invited_by=added_by,
            invited_at=timezone.now()
        )
        
        # Audit log
        self._audit_log('member_added', added_by, {
            'organization_id': organization.id,
            'user_id': user_to_add.id,
            'role_code': role_code
        })
        
        return True, membership, ''
    
    def update_member_role(
        self,
        organization,
        user_to_update,
        new_role_code: str,
        updated_by
    ) -> Tuple[bool, str]:
        """
        Update a member's role in an organization.
        
        Args:
            organization: Organization instance
            user_to_update: User whose role to update
            new_role_code: New role code
            updated_by: User performing the update
            
        Returns:
            Tuple[success, error_message]
        """
        # Check permission
        if not updated_by.has_org_permission(organization, 'org.members.manage'):
            return False, 'Insufficient permissions to manage members'
        
        # Cannot change owner role
        if user_to_update.has_org_role(organization, 'owner', check_inheritance=False):
            return False, 'Cannot change owner role'
        
        # Get membership
        membership = user_to_update.get_org_membership(organization)
        if not membership:
            return False, 'User is not a member'
        
        # Get new role
        try:
            new_role = self.OrganizationRole.objects.get(code=new_role_code)
        except self.OrganizationRole.DoesNotExist:
            return False, f'Role {new_role_code} not found'
        
        # Update
        old_role_code = membership.role.code
        membership.role = new_role
        membership.save()
        
        # Audit log
        self._audit_log('member_role_updated', updated_by, {
            'organization_id': organization.id,
            'user_id': user_to_update.id,
            'old_role': old_role_code,
            'new_role': new_role_code
        })
        
        return True, ''
    
    def remove_member(
        self,
        organization,
        user_to_remove,
        removed_by
    ) -> Tuple[bool, str]:
        """
        Remove a member from an organization.
        
        Args:
            organization: Organization instance
            user_to_remove: User to remove
            removed_by: User performing the removal
            
        Returns:
            Tuple[success, error_message]
        """
        # Check permission
        if not removed_by.has_org_permission(organization, 'org.members.remove'):
            return False, 'Insufficient permissions to remove members'
        
        # Cannot remove owner
        if user_to_remove.has_org_role(organization, 'owner', check_inheritance=False):
            return False, 'Cannot remove organization owner'
        
        # Get membership
        membership = user_to_remove.get_org_membership(organization)
        if not membership:
            return False, 'User is not a member'
        
        # Remove
        membership.delete()
        
        # Audit log
        self._audit_log('member_removed', removed_by, {
            'organization_id': organization.id,
            'user_id': user_to_remove.id
        })
        
        return True, ''
    
    def get_members(self, organization, status: str = 'active') -> List[Any]:
        """
        Get all members of an organization.
        
        Args:
            organization: Organization instance
            status: Filter by status (default: 'active')
            
        Returns:
            List of memberships
        """
        query = self.OrganizationMembership.objects.filter(organization=organization)
        
        if status:
            query = query.filter(status=status)
        
        return query.select_related('user', 'role').order_by('-created_at')
    
    # =============================================
    # Invitation Management
    # =============================================
    
    @transaction.atomic
    def create_invitation(
        self,
        organization,
        email: str,
        role_code: str,
        invited_by,
        expires_in_days: int = 7
    ) -> Tuple[bool, Optional[Any], str]:
        """
        Create an invitation to join an organization.
        
        Args:
            organization: Organization instance
            email: Email of invitee
            role_code: Role to assign
            invited_by: User sending invitation
            expires_in_days: Days until expiration
            
        Returns:
            Tuple[success, invitation, error_message]
        """
        from ..models.organization import AbstractOrganizationInvitation
        
        # Check permission
        if not invited_by.has_org_permission(organization, 'org.members.invite'):
            return False, None, 'Insufficient permissions to invite members'
        
        # Check member limit
        if organization.is_at_member_limit():
            return False, None, 'Organization has reached its member limit'
        
        # Get role
        try:
            role = self.OrganizationRole.objects.get(code=role_code)
        except self.OrganizationRole.DoesNotExist:
            return False, None, f'Role {role_code} not found'
        
        # Check if user already a member
        try:
            user = self.User.objects.get(email=email)
            if user.is_org_member(organization):
                return False, None, 'User is already a member'
        except self.User.DoesNotExist:
            pass  # OK, user doesn't exist yet
        
        # Cancel existing pending invitations for this email
        from ..models import OrganizationInvitation
        OrganizationInvitation.objects.filter(
            organization=organization,
            email=email,
            status='pending'
        ).update(status='expired')
        
        # Create invitation
        invitation = OrganizationInvitation.create_invitation(
            organization=organization,
            email=email,
            role=role,
            invited_by=invited_by,
            expires_in_days=expires_in_days
        )
        
        # Audit log
        self._audit_log('invitation_created', invited_by, {
            'organization_id': organization.id,
            'email': email,
            'role_code': role_code,
            'invitation_id': invitation.id
        })
        
        # TODO: Send invitation email
        
        return True, invitation, ''
    
    # =============================================
    # Utility Methods
    # =============================================
    
    def initialize_system_roles(self):
        """
        Initialize system organization roles (owner, admin, member, viewer).
        
        Returns:
            List of created roles
        """
        system_roles = [
            {
                'code': 'owner',
                'name': 'Owner',
                'description': 'Organization owner with full access',
                'is_system': True,
                'permissions': ['org.*']
            },
            {
                'code': 'admin',
                'name': 'Admin',
                'description': 'Administrator with management permissions',
                'is_system': True,
                'permissions': [
                    'org.members.invite',
                    'org.members.manage',
                    'org.members.remove',
                    'org.settings.read',
                    'org.settings.write'
                ]
            },
            {
                'code': 'member',
                'name': 'Member',
                'description': 'Regular member with basic access',
                'is_system': True,
                'is_default': True,
                'permissions': [
                    'org.read',
                    'org.members.read'
                ]
            },
            {
                'code': 'viewer',
                'name': 'Viewer',
                'description': 'Read-only access',
                'is_system': True,
                'permissions': [
                    'org.read'
                ]
            }
        ]
        
        created_roles = []
        for role_data in system_roles:
            role, created = self.OrganizationRole.objects.get_or_create(
                code=role_data['code'],
                defaults=role_data
            )
            created_roles.append(role)
        
        return created_roles
    
    def _audit_log(self, action: str, user, details: Dict[str, Any] = None):
        """Create an audit log entry."""
        AuditLog.objects.create(
            action=action,
            user=user,
            ip_address='system',
            details=details or {}
        )
